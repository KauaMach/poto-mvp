"""Captura de áudio — MVP-076.

`abrir(id)` devolve um gerador de blocos PCM de 16 kHz mono, e a rota de stream
os embrulha num WAV.

**`arecord`, não `sounddevice`.** O segundo é binding de PortAudio, uma
biblioteca C que não vem no pacote pip: na Pi real o import morre com
`OSError: PortAudio library not found`, e resolver exigiria `libportaudio2` do
apt. O `arecord` faz parte do `alsa-utils`, que já está instalado, e o critério
da task aceita os dois. Medido na Pi: 2 s de captura → 64.044 bytes, que é
exatamente o esperado para 16 kHz × 16 bit × mono mais o cabeçalho.

**O compartilhamento é diferente do da câmera, e a diferença importa.** Em
`camera.py` cada assinante pede um frame e recebe o mais recente — dois
operadores olham a mesma imagem sem se atrapalhar. Áudio não funciona assim:
é um fluxo contínuo de amostras, e dois consumidores lendo do mesmo pipe
receberiam cada um metade das amostras. Os dois ouviriam picado.

Por isso aqui há **uma thread leitora e uma fila por assinante**: o `arecord`
é aberto uma vez (o dispositivo ALSA é exclusivo) e cada bloco é copiado para
todas as filas. É o que permite dois operadores ouvirem o mesmo microfone em
vez de um deles receber "device busy".
"""

from __future__ import annotations

import logging
import queue
import shutil
import struct
import subprocess
import threading
from collections.abc import Iterator

from . import obter

logger = logging.getLogger(__name__)

# Voz não precisa de mais. 16 kHz é o padrão de telefonia de banda larga, e
# cobre a inteligibilidade da fala com metade dos bytes de 44,1 kHz.
TAXA = 16000
CANAIS = 1
BITS = 16
BYTES_POR_AMOSTRA = BITS // 8 * CANAIS

# 3200 bytes = exatamente 100 ms a 16 kHz mono 16 bit.
#
# O tamanho do bloco **é** o piso da latência: o primeiro som só sai depois de
# o bloco encher. 100 ms é imperceptível numa escuta de corredor e mantém o
# overhead de HTTP em menos de 1% do tráfego. Blocos de 1 s dariam 1 s de
# atraso garantido, e o critério da task é medir o atraso falando perto do
# microfone.
BLOCO = 3200

# Quantos blocos um assinante lento pode acumular antes de começar a perder.
# 50 blocos = 5 s de áudio ≈ 160 KB. Sem teto, um painel com a aba em segundo
# plano (que o navegador desacelera) faria a fila crescer até a memória acabar.
FILA_MAX = 50


class MicrofoneIndisponivel(RuntimeError):
    """O dispositivo não existe, não abriu, ou não é um microfone."""


class _Captura:
    """Um `arecord` compartilhado por várias sessões.

    Como na câmera, o contador de assinantes libera o dispositivo **quando o
    último sai**. A diferença é o que fica no meio: aqui uma thread lê o pipe
    sem parar e distribui cópias, porque o consumidor não pode ditar o ritmo de
    uma captura em tempo real — o ALSA continua produzindo amostras, e quem não
    as retira a tempo provoca overrun.
    """

    def __init__(self, dispositivo_id: str) -> None:
        self.dispositivo_id = dispositivo_id
        self._trava = threading.Lock()
        self._filas: list[queue.Queue[bytes | None]] = []
        self._proc: subprocess.Popen[bytes] | None = None
        self._leitor: threading.Thread | None = None
        self._erro: str | None = None

    # --- ciclo de vida -----------------------------------------------------

    def entrar(self) -> queue.Queue[bytes | None]:
        """Registra um assinante e devolve a fila dele."""
        fila: queue.Queue[bytes | None] = queue.Queue(maxsize=FILA_MAX)
        with self._trava:
            if not self._filas:
                self._iniciar()
            self._filas.append(fila)
        return fila

    def sair(self, fila: queue.Queue[bytes | None]) -> None:
        with self._trava:
            if fila in self._filas:
                self._filas.remove(fila)
            if not self._filas:
                self._parar()

    def _iniciar(self) -> None:
        """Abre o `arecord` e sobe a thread leitora. Chamado com a trava."""
        disp = obter(self.dispositivo_id)
        if disp is None or disp["tipo"] != "microfone":
            raise MicrofoneIndisponivel(
                f"{self.dispositivo_id} não é um microfone disponível"
            )
        if not shutil.which("arecord"):
            raise MicrofoneIndisponivel("arecord ausente: sem captura de áudio")

        device = str(disp["capacidades"]["device"])
        self._erro = None
        try:
            self._proc = subprocess.Popen(
                _comando(device),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as erro:
            raise MicrofoneIndisponivel(f"falha ao abrir {device}: {erro!r}") from erro

        self._leitor = threading.Thread(
            target=self._ler, name=f"mic-{self.dispositivo_id}", daemon=True
        )
        self._leitor.start()

    def _parar(self) -> None:
        """Encerra o `arecord`. Chamado com a trava."""
        proc, self._proc = self._proc, None
        if proc is None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Um `arecord` que ignora SIGTERM mantém o dispositivo ALSA preso, e
            # o sintoma é "o microfone parou de funcionar" na sessão seguinte.
            proc.kill()
            proc.wait(timeout=2)
        logger.info("microfone %s liberado", self.dispositivo_id)

    # --- thread leitora ----------------------------------------------------

    def _ler(self) -> None:
        """Lê o pipe do `arecord` e copia cada bloco para todas as filas.

        Roda numa thread própria porque a leitura é bloqueante e o ritmo é do
        hardware, não do consumidor: se ninguém retirasse as amostras, o ALSA
        acusaria overrun e a captura sairia picada.
        """
        proc = self._proc
        assert proc is not None and proc.stdout is not None
        try:
            while True:
                # `read(BLOCO)` e não `read1`: o contrato aqui é bloco cheio, e
                # um bloco parcial desalinharia as amostras de 16 bit — o
                # sintoma é chiado, não silêncio.
                dados = proc.stdout.read(BLOCO)
                if not dados:
                    break
                self._distribuir(dados)
        except (OSError, ValueError):
            # Pipe fechado pelo `_parar`. Caminho normal de saída.
            pass
        finally:
            self._erro = self._motivo(proc)
            # `None` é o sentinela de fim: quem está esperando na fila acorda
            # em vez de ficar pendurado até o timeout.
            self._distribuir(None)

    def _distribuir(self, dados: bytes | None) -> None:
        with self._trava:
            filas = list(self._filas)
        for fila in filas:
            try:
                fila.put_nowait(dados)
            except queue.Full:
                # Assinante lento: **descarta o mais antigo** e insere o novo.
                #
                # Áudio ao vivo é o caso em que a amostra velha não tem valor:
                # quem está ouvindo quer o som de agora, e entregar 5 s de
                # atraso acumulado seria pior que um estalo. O contrário —
                # descartar o novo — faria o atraso crescer para sempre.
                try:
                    fila.get_nowait()
                    fila.put_nowait(dados)
                except (queue.Empty, queue.Full):
                    pass

    def _motivo(self, proc: subprocess.Popen[bytes]) -> str | None:
        """O que o `arecord` reclamou, se reclamou.

        Sem isto, um dispositivo ocupado ou um formato recusado viram "stream
        vazio" — e o operador vê um player mudo sem nenhuma pista do motivo.
        """
        # **`wait` antes de ler `returncode`.** O atributo só é preenchido por
        # `wait`/`poll`: consultá-lo direto devolve `None` mesmo num processo já
        # morto, e o motivo do erro se perdia inteiro. Encontrado pelo teste do
        # "device busy", que não levantava nada.
        # **`wait` antes de ler `returncode`.** O atributo só é preenchido por
        # `wait`/`poll`: consultá-lo direto devolve `None` mesmo num processo já
        # morto, e o motivo do erro se perdia inteiro. Encontrado pelo teste do
        # "device busy", que não levantava nada.
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            return None

        if proc.returncode in (0, None, -15):  # -15 = SIGTERM, encerramento nosso
            return None
        saida = b""
        if proc.stderr is not None:
            try:
                saida = proc.stderr.read() or b""
            except (OSError, ValueError):
                pass
        texto = saida.decode(errors="replace").strip().splitlines()
        return texto[-1] if texto else f"arecord saiu com {proc.returncode}"

    @property
    def erro(self) -> str | None:
        return self._erro

    @property
    def assinantes(self) -> int:
        return len(self._filas)


def _comando(device: str) -> list[str]:
    """A linha de comando do `arecord`.

    `-t raw` e o cabeçalho WAV montado aqui, em vez de `-t wav`: num pipe o
    `arecord` não pode voltar atrás para escrever o tamanho, então ele grava um
    valor que não corresponde ao que vai sair. Montando o cabeçalho é explícito
    o que o navegador recebe (ver `cabecalho_wav`).

    `--buffer-time` curto porque o buffer do ALSA entra inteiro na latência: o
    padrão de meio segundo somaria 500 ms ao atraso que a task manda medir.
    """
    return [
        "arecord",
        "-D", device,
        "-f", "S16_LE",
        "-r", str(TAXA),
        "-c", str(CANAIS),
        "-t", "raw",
        "--buffer-time=200000",
        "--period-time=50000",
        "-q",
        "-",
    ]


# Um `_Captura` por dispositivo, criado na primeira abertura e mantido: o objeto
# é leve; o `arecord` só roda enquanto há assinante.
_capturas: dict[str, _Captura] = {}
_trava_registro = threading.Lock()


def _captura_de(dispositivo_id: str) -> _Captura:
    with _trava_registro:
        if dispositivo_id not in _capturas:
            _capturas[dispositivo_id] = _Captura(dispositivo_id)
        return _capturas[dispositivo_id]


# --- WAV --------------------------------------------------------------------

# Sentinela de "não sei o tamanho".
#
# Um WAV declara no cabeçalho quantos bytes vêm — e num stream ao vivo isso é
# desconhecido por definição. A convenção, a mesma que o `ffmpeg` usa ao
# escrever num pipe, é declarar o máximo de 32 bits e deixar o player parar
# quando a conexão fechar.
#
# O custo é conhecido e aceito: o player mostra uma duração absurda e a barra de
# progresso não significa nada. Para escuta ao vivo isso não atrapalha, e é o
# que permite tocar num `<audio src="…">` sem uma linha de JavaScript — a mesma
# escolha do MJPEG no `<img>` (MVP-075).
TAMANHO_DESCONHECIDO = 0xFFFFFFFF


def cabecalho_wav(tamanho_dados: int = TAMANHO_DESCONHECIDO) -> bytes:
    """Cabeçalho RIFF/WAVE de 44 bytes para PCM 16 kHz mono 16 bit."""
    taxa_bytes = TAXA * BYTES_POR_AMOSTRA
    riff = (
        tamanho_dados
        if tamanho_dados == TAMANHO_DESCONHECIDO
        else tamanho_dados + 36
    )
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", riff, b"WAVE",
        b"fmt ", 16,          # tamanho do bloco fmt
        1,                     # 1 = PCM sem compressão
        CANAIS,
        TAXA,
        taxa_bytes,            # bytes por segundo
        BYTES_POR_AMOSTRA,     # alinhamento de bloco
        BITS,
        b"data", tamanho_dados,
    )


# --- Interface pública ------------------------------------------------------


def abrir(dispositivo_id: str, espera: float = 5.0) -> Iterator[bytes]:
    """Gerador de blocos PCM do dispositivo.

    Não inclui o cabeçalho WAV: quem serve decide o embrulho, e o clipe precisa
    de um cabeçalho com tamanho verdadeiro enquanto o stream não pode ter.

    O `finally` é o que impede o `arecord` de ficar rodando depois de o cliente
    sair — e um `arecord` órfão mantém o dispositivo ALSA preso, então a sessão
    seguinte falharia com "device busy".
    """
    captura = _captura_de(dispositivo_id)
    fila = captura.entrar()
    try:
        while True:
            try:
                dados = fila.get(timeout=espera)
            except queue.Empty:
                # Silêncio não é isto: um microfone em silêncio manda zeros. Sem
                # bloco nenhum por 5 s, a captura morreu.
                raise MicrofoneIndisponivel(
                    f"{dispositivo_id} não entregou áudio em {espera:g}s"
                ) from None
            if dados is None:
                if motivo := captura.erro:
                    raise MicrofoneIndisponivel(motivo)
                return
            yield dados
    finally:
        captura.sair(fila)


def clipe(dispositivo_id: str, segundos: float = 15.0) -> bytes:
    """Um WAV completo, com tamanho verdadeiro no cabeçalho.

    É o **fallback previsto pela task**: se o stream contínuo se mostrar
    instável — rede oscilando, player que não lida com tamanho desconhecido —
    um clipe sob demanda resolve o essencial, que é ouvir o local. Sendo um
    arquivo fechado, ele toca em qualquer player e pode ser baixado.

    Vem por cima do mesmo compartilhamento: pedir um clipe enquanto alguém
    escuta o stream não reabre o dispositivo.
    """
    alvo = int(TAXA * BYTES_POR_AMOSTRA * segundos)
    pedacos: list[bytes] = []
    total = 0
    for bloco in abrir(dispositivo_id):
        pedacos.append(bloco)
        total += len(bloco)
        if total >= alvo:
            break
    dados = b"".join(pedacos)[:alvo]
    return cabecalho_wav(len(dados)) + dados


def assinantes(dispositivo_id: str) -> int:
    """Quantas sessões estão ouvindo este dispositivo."""
    return _capturas[dispositivo_id].assinantes if dispositivo_id in _capturas else 0
