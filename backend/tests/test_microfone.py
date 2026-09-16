"""Captura de áudio — MVP-076.

Ao contrário de `test_camera.py`, estes testes **não** substituem o subprocesso
por um dublê: eles trocam só a linha de comando do `arecord` por um Python que
escreve PCM na saída. O caminho exercitado é o de verdade — `Popen`, pipe,
thread leitora, fila por assinante e encerramento.

Foi escolha deliberada, porque os dois erros que doem aqui vivem exatamente
nessa mecânica:

- **Um `arecord` órfão prende o dispositivo ALSA.** O sintoma é a sessão
  seguinte falhar com "device busy", e só reiniciar o serviço resolve.
- **Dois ouvintes no mesmo pipe recebem metade das amostras cada.** Diferente
  do vídeo, em que o assinante pede "o frame mais recente", áudio é fluxo
  contínuo: sem uma fila por assinante, os dois ouvem picado — e picado é
  difícil de distinguir de "o microfone é ruim".

O hardware foi verificado à parte, na Pi (números na nota da task).
"""

from __future__ import annotations

import struct
import subprocess
import sys
import time

import pytest

from app.midia import microfone

# Um bloco de silêncio do tamanho que o módulo usa.
SILENCIO = b"\x00" * microfone.BLOCO


def _gerador_pcm(blocos: int, intervalo: float = 0.0) -> list[str]:
    """Uma linha de comando que escreve `blocos` blocos de PCM e termina.

    Faz o papel do `arecord` sem exigir placa de som — o que importa para o
    módulo é um processo que escreve bytes num pipe e pode ser terminado.
    """
    programa = (
        "import sys, time\n"
        f"for _ in range({blocos}):\n"
        f"    sys.stdout.buffer.write(b'\\x00' * {microfone.BLOCO})\n"
        "    sys.stdout.buffer.flush()\n"
        f"    time.sleep({intervalo})\n"
    )
    return [sys.executable, "-c", programa]


def _gerador_infinito() -> list[str]:
    """Escreve para sempre. Serve para testar o encerramento."""
    programa = (
        "import sys, time\n"
        "while True:\n"
        f"    sys.stdout.buffer.write(b'\\x00' * {microfone.BLOCO})\n"
        "    sys.stdout.buffer.flush()\n"
        "    time.sleep(0.01)\n"
    )
    return [sys.executable, "-c", programa]


def _falha(mensagem: str) -> list[str]:
    """Um processo que reclama no stderr e sai com erro, como o `arecord` faz
    quando o dispositivo está ocupado ou o formato é recusado."""
    programa = f"import sys; sys.stderr.write({mensagem!r}); sys.exit(1)"
    return [sys.executable, "-c", programa]


DISPOSITIVO = {
    "id": "alsa:2,0",
    "tipo": "microfone",
    "nome": "Falso — Captura",
    "dono": "teste",
    "status": "disponivel",
    "capacidades": {"origem": "alsa", "device": "plughw:2,0"},
}


@pytest.fixture(autouse=True)
def registro_limpo(monkeypatch):
    """Zera o registro global de capturadores entre testes.

    Um capturador por dispositivo é mantido entre chamadas (o objeto é leve),
    então sem limpar um teste herdaria o processo e o contador do anterior.
    """
    monkeypatch.setattr(microfone, "_capturas", {})
    monkeypatch.setattr(microfone, "obter", lambda _id: dict(DISPOSITIVO))
    monkeypatch.setattr(microfone.shutil, "which", lambda _nome: "/usr/bin/arecord")


@pytest.fixture
def pcm(monkeypatch):
    """Instala um gerador de PCM no lugar do `arecord`."""

    def instalar(comando: list[str]):
        monkeypatch.setattr(microfone, "_comando", lambda _device: comando)

    return instalar


# ---------------------------------------------------------------------------
# Cabeçalho WAV
# ---------------------------------------------------------------------------
#
# É o que o navegador lê antes da primeira amostra. Um campo errado aqui não dá
# erro: dá áudio em velocidade errada ou chiado, que é bem mais difícil de
# diagnosticar que uma falha.

CAMPOS = "<4sI4s4sIHHIIHH4sI"


def test_cabecalho_tem_44_bytes():
    assert len(microfone.cabecalho_wav()) == 44


def test_cabecalho_descreve_pcm_16k_mono_16bit():
    c = struct.unpack(CAMPOS, microfone.cabecalho_wav(32000))
    (riff, tam_riff, wave, fmt, tam_fmt, formato, canais, taxa,
     taxa_bytes, alinhamento, bits, data, tam_data) = c

    assert (riff, wave, fmt, data) == (b"RIFF", b"WAVE", b"fmt ", b"data")
    assert tam_fmt == 16
    assert formato == 1, "1 = PCM sem compressão; outro valor o navegador não toca"
    assert (canais, taxa, bits) == (1, 16000, 16)
    # Estes dois são derivados, e errá-los toca o áudio na velocidade errada.
    assert taxa_bytes == 16000 * 2
    assert alinhamento == 2
    assert tam_data == 32000
    assert tam_riff == 32000 + 36


def test_cabecalho_de_stream_declara_tamanho_desconhecido():
    """Num fluxo ao vivo o tamanho é desconhecido por definição.

    A convenção — a mesma do `ffmpeg` escrevendo num pipe — é declarar o máximo
    de 32 bits e deixar o player parar quando a conexão fechar.
    """
    c = struct.unpack(CAMPOS, microfone.cabecalho_wav())
    assert c[1] == 0xFFFFFFFF, "tamanho do RIFF"
    assert c[12] == 0xFFFFFFFF, "tamanho do bloco data"


def test_cabecalho_de_clipe_nao_usa_o_sentinela():
    """O par negativo do teste acima.

    Sem ele, devolver sempre o sentinela passaria no teste de stream — e o
    clipe, que é o fallback da task, perderia a única coisa que o distingue.
    """
    c = struct.unpack(CAMPOS, microfone.cabecalho_wav(1000))
    assert c[12] == 1000
    assert c[1] == 1036


# ---------------------------------------------------------------------------
# Captura
# ---------------------------------------------------------------------------


def test_abrir_entrega_blocos_do_tamanho_declarado(pcm):
    pcm(_gerador_pcm(3))
    blocos = list(microfone.abrir("alsa:2,0"))
    assert len(blocos) == 3
    assert all(len(b) == microfone.BLOCO for b in blocos)


def test_bloco_e_100ms_de_audio():
    """O tamanho do bloco é o piso da latência: o primeiro som só sai depois de
    ele encher. A task manda medir o atraso, então o valor não é livre."""
    segundos = microfone.BLOCO / (microfone.TAXA * microfone.BYTES_POR_AMOSTRA)
    assert segundos == pytest.approx(0.1)


def test_fim_do_processo_encerra_o_gerador(pcm):
    pcm(_gerador_pcm(2))
    assert len(list(microfone.abrir("alsa:2,0"))) == 2


def test_sair_encerra_o_arecord(pcm):
    """**O teste que mais importa deste arquivo.**

    Um `arecord` que continua rodando depois de o ouvinte sair mantém o
    dispositivo ALSA preso, e a próxima sessão falha com "device busy" até
    alguém reiniciar o serviço.
    """
    pcm(_gerador_infinito())
    gerador = microfone.abrir("alsa:2,0")
    next(gerador)
    captura = microfone._capturas["alsa:2,0"]
    proc = captura._proc
    assert proc is not None and proc.poll() is None, "devia estar rodando"

    gerador.close()

    assert captura._proc is None
    assert proc.poll() is not None, "o processo do arecord ficou órfão"


def test_processo_encerra_mesmo_com_excecao_no_consumidor(pcm):
    """O `finally` tem que valer para a saída por erro, não só pela normal."""
    pcm(_gerador_infinito())
    gerador = microfone.abrir("alsa:2,0")
    next(gerador)
    proc = microfone._capturas["alsa:2,0"]._proc

    with pytest.raises(RuntimeError):
        gerador.throw(RuntimeError("consumidor explodiu"))

    assert proc is not None and proc.poll() is not None


# ---------------------------------------------------------------------------
# Compartilhamento
# ---------------------------------------------------------------------------
#
# A diferença de modelo em relação ao vídeo. Em `camera.py` cada assinante pede
# "o frame mais recente"; aqui cada um precisa de **todas** as amostras, na
# ordem, ou ouve picado.


def test_dois_ouvintes_recebem_os_mesmos_blocos(pcm):
    """Se os dois lessem do mesmo pipe, cada um pegaria metade das amostras."""
    pcm(_gerador_infinito())
    a = microfone.abrir("alsa:2,0")
    b = microfone.abrir("alsa:2,0")
    try:
        blocos_a = [next(a) for _ in range(3)]
        blocos_b = [next(b) for _ in range(3)]
        assert blocos_a == blocos_b == [SILENCIO] * 3
    finally:
        a.close()
        b.close()


def test_um_so_processo_para_dois_ouvintes(pcm):
    """O dispositivo ALSA é exclusivo: a segunda abertura falharia."""
    pcm(_gerador_infinito())
    a = microfone.abrir("alsa:2,0")
    next(a)
    proc = microfone._capturas["alsa:2,0"]._proc

    b = microfone.abrir("alsa:2,0")
    next(b)
    try:
        assert microfone._capturas["alsa:2,0"]._proc is proc
        assert microfone.assinantes("alsa:2,0") == 2
    finally:
        a.close()
        b.close()


def test_processo_cai_so_quando_o_ultimo_sai(pcm):
    """Liberar na saída do **primeiro** faria o segundo operador perder o áudio
    no instante em que o primeiro fechasse a aba."""
    pcm(_gerador_infinito())
    a = microfone.abrir("alsa:2,0")
    b = microfone.abrir("alsa:2,0")
    next(a)
    next(b)
    captura = microfone._capturas["alsa:2,0"]
    proc = captura._proc

    a.close()
    assert captura._proc is proc, "caiu com o primeiro ainda havendo ouvinte"
    assert microfone.assinantes("alsa:2,0") == 1

    b.close()
    assert captura._proc is None
    assert proc is not None and proc.poll() is not None


def test_assinantes_e_zero_para_dispositivo_nunca_aberto():
    assert microfone.assinantes("alsa:9,9") == 0


def test_ouvinte_lento_perde_o_antigo_e_nao_a_memoria(pcm):
    """Fila cheia descarta o **mais antigo**.

    Áudio ao vivo é o caso em que a amostra velha não vale nada: quem ouve quer
    o som de agora. Sem teto, uma aba em segundo plano — que o navegador
    desacelera — faria a fila crescer até a memória acabar.
    """
    pcm(_gerador_infinito())
    gerador = microfone.abrir("alsa:2,0")
    next(gerador)
    fila = microfone._capturas["alsa:2,0"]._filas[0]
    try:
        # Não retira nada e deixa a thread leitora encher bem além do teto.
        limite = time.monotonic() + 3.0
        while fila.qsize() < microfone.FILA_MAX and time.monotonic() < limite:
            time.sleep(0.02)
        assert fila.qsize() == microfone.FILA_MAX, "não encheu; teste inconcluso"

        time.sleep(0.3)  # mais blocos chegam com a fila cheia
        assert fila.qsize() <= microfone.FILA_MAX
    finally:
        gerador.close()


def test_teto_da_fila_cobre_alguns_segundos():
    """Teto pequeno demais cortaria áudio em qualquer oscilação de rede."""
    segundos = microfone.FILA_MAX * microfone.BLOCO / (
        microfone.TAXA * microfone.BYTES_POR_AMOSTRA
    )
    assert 2.0 <= segundos <= 10.0


# ---------------------------------------------------------------------------
# Falhas
# ---------------------------------------------------------------------------


def test_dispositivo_que_nao_e_microfone_e_recusado(monkeypatch):
    monkeypatch.setattr(
        microfone, "obter", lambda _id: {"tipo": "camera", "capacidades": {}}
    )
    with pytest.raises(microfone.MicrofoneIndisponivel, match="não é um microfone"):
        next(microfone.abrir("csi:0"))


def test_dispositivo_inexistente_e_recusado(monkeypatch):
    monkeypatch.setattr(microfone, "obter", lambda _id: None)
    with pytest.raises(microfone.MicrofoneIndisponivel):
        next(microfone.abrir("alsa:9,9"))


def test_sem_arecord_a_falha_e_explicita(monkeypatch):
    """A Pi tem `arecord` (vem do `alsa-utils`), mas a máquina de quem
    desenvolve pode não ter — e a mensagem precisa dizer isso."""
    monkeypatch.setattr(microfone.shutil, "which", lambda _nome: None)
    with pytest.raises(microfone.MicrofoneIndisponivel, match="arecord ausente"):
        next(microfone.abrir("alsa:2,0"))


def test_erro_do_arecord_chega_a_quem_chamou(pcm):
    """Sem isto, dispositivo ocupado viraria "stream vazio" — e o operador veria
    um player mudo sem nenhuma pista do motivo."""
    pcm(_falha("audio open error: Device or resource busy"))
    with pytest.raises(microfone.MicrofoneIndisponivel, match="Device or resource busy"):
        list(microfone.abrir("alsa:2,0"))


def test_captura_muda_nao_fica_pendurada(pcm):
    """Microfone em silêncio manda **zeros**, não nada.

    Sem bloco algum, a captura morreu — e esperar para sempre deixaria a
    conexão do painel aberta sem áudio nenhum.
    """
    pcm([sys.executable, "-c", "import time; time.sleep(30)"])
    gerador = microfone.abrir("alsa:2,0", espera=0.5)
    try:
        with pytest.raises(microfone.MicrofoneIndisponivel, match="não entregou áudio"):
            next(gerador)
    finally:
        gerador.close()


def test_arecord_que_ignora_sigterm_leva_sigkill(pcm, monkeypatch):
    """Um processo que não morre com SIGTERM manteria o ALSA preso."""
    pcm(
        [
            sys.executable,
            "-c",
            "import signal, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "while True:\n"
            f"    sys.stdout.buffer.write(b'\\x00' * {microfone.BLOCO})\n"
            "    sys.stdout.buffer.flush()\n"
            "    time.sleep(0.01)\n",
        ]
    )
    # Encurta a espera do terminate para o teste não levar 3 s.
    original = subprocess.Popen.wait

    def wait_curto(self, timeout=None):
        return original(self, timeout=0.3 if timeout == 3 else timeout)

    monkeypatch.setattr(subprocess.Popen, "wait", wait_curto)

    gerador = microfone.abrir("alsa:2,0")
    next(gerador)
    proc = microfone._capturas["alsa:2,0"]._proc
    gerador.close()
    assert proc is not None and proc.poll() is not None


# ---------------------------------------------------------------------------
# Clipe — o fallback previsto pela task
# ---------------------------------------------------------------------------


def test_clipe_tem_wav_completo_e_duracao_pedida(pcm):
    pcm(_gerador_pcm(30))
    dados = microfone.clipe("alsa:2,0", segundos=1.0)

    esperado = microfone.TAXA * microfone.BYTES_POR_AMOSTRA  # 1 s
    assert len(dados) == 44 + esperado
    assert dados[:4] == b"RIFF"
    # Tamanho **verdadeiro** no cabeçalho: é o que faz o clipe tocar em qualquer
    # player, inclusive os que não lidam com o sentinela do stream.
    assert struct.unpack("<I", dados[40:44])[0] == esperado


def test_clipe_libera_o_dispositivo(pcm):
    pcm(_gerador_infinito())
    microfone.clipe("alsa:2,0", segundos=0.2)
    assert microfone.assinantes("alsa:2,0") == 0
    assert microfone._capturas["alsa:2,0"]._proc is None


def test_clipe_nao_reabre_o_dispositivo_em_uso(pcm):
    """Pedir um clipe enquanto alguém escuta o stream não pode falhar com
    "device busy" — o compartilhamento vale para os dois caminhos."""
    pcm(_gerador_infinito())
    ouvindo = microfone.abrir("alsa:2,0")
    next(ouvindo)
    proc = microfone._capturas["alsa:2,0"]._proc
    try:
        dados = microfone.clipe("alsa:2,0", segundos=0.2)
        assert len(dados) > 44
        assert microfone._capturas["alsa:2,0"]._proc is proc
    finally:
        ouvindo.close()
