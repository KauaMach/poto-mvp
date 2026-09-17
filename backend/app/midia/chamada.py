"""Repasse de quadros da central para o totem — MEL-004.

O sentido que faltava. Desde a MVP-073/078 a central vê e ouve a pessoa, pela
câmera da Pi; aqui a imagem vai no caminho inverso, para que quem apertou o
pânico **veja alguém do outro lado** enquanto espera.

**A Pi não captura nada nesta direção.** A webcam é do operador, na máquina da
central — o servidor não tem acesso a ela. Então este módulo não é um capturador
como `camera.py`: é um **repasse**. Alguém publica um quadro; quem estiver
assistindo recebe.

```
central (webcam) ──POST /quadro──> [aqui] ──GET /stream (MJPEG)──> totem
```

Três decisões, e todas vêm de ser uma chamada e não uma gravação:

- **Um quadro por sessão, o mais recente.** Sem fila. Numa conversa, quadro
  velho não vale nada: acumular introduziria atraso crescente, e o atraso é
  justamente o que arruína a sensação de estar falando com alguém. É a mesma
  escolha do `_Captura` de `camera.py`, por outro motivo.
- **Quem espera é acordado, não consulta em laço.** Um `asyncio.Event` por
  sessão, trocado a cada publicação. Consultar de 50 em 50 ms somaria latência
  e gastaria CPU à toa nos intervalos em que nada chega.
- **Teto de tamanho por quadro.** O endpoint recebe de fora. Sem limite, um
  cliente mal-comportado — ou um bug de laço na central — enche a memória da Pi
  durante uma emergência.

Nada aqui autoriza: a autorização é a sessão de `sessao.py`, e é ela que garante
que a chamada existe, está vinculada a um chamado ativo, expira em dez minutos e
deixa rastro na auditoria.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

logger = logging.getLogger(__name__)

# Teto de um quadro, em bytes.
#
# 512 KB é folgado para um JPEG de webcam em resolução de conversa (a câmera da
# Pi entrega 17 KB a 640×480, medido na MVP-079) e baixo o bastante para que um
# cliente em laço não derrube a Pi antes de alguém notar.
TAMANHO_MAXIMO = 512 * 1024

# Teto da fila de áudio, em pedaços.
#
# **Áudio é fila; vídeo é só o último.** A diferença não é estilo, é natureza do
# sinal: um quadro de vídeo antigo não vale nada — quem assiste quer a imagem de
# agora, e guardar os anteriores só somaria atraso. Já em áudio, descartar um
# pedaço é um **buraco audível** no meio de uma frase.
#
# Então o áudio acumula. Mas não sem limite: uma fila que só cresce vira atraso
# crescente, e numa conversa atraso é pior que um estalo. Cheia, **descarta o
# mais antigo** — a mesma decisão (e a mesma razão) do `microfone.py`.
#
# 50 pedaços de ~100 ms = ~5 s de áudio. É folgado para uma oscilação de rede
# local e curto o bastante para o atraso não virar eco.
FILA_AUDIO_MAX = 50

# Prazo de espera por um quadro novo, em segundos.
#
# Não é o prazo da chamada — é de quanto em quanto tempo o gerador do stream
# volta a checar se deve continuar (cliente desconectou, sessão expirou). Sem
# ele, uma central que parou de enviar deixaria o gerador pendurado para sempre
# e a sessão viveria até a varredura de expiradas passar.
ESPERA_QUADRO = 5.0


class SemQuadro(RuntimeError):
    """A central não publicou quadro nenhum dentro do prazo."""


class SemAudio(RuntimeError):
    """A central não publicou áudio nenhum dentro do prazo."""


class _Repasse:
    """O quadro mais recente de cada sessão, e o aviso de que chegou um novo."""

    def __init__(self) -> None:
        self._atual: dict[str, bytes] = {}
        self._novidade: dict[str, asyncio.Event] = {}
        # Áudio tem armazenamento próprio porque tem política própria: fila,
        # não "só o último". Ver `FILA_AUDIO_MAX`.
        self._audio: dict[str, deque[bytes]] = {}
        self._audio_novo: dict[str, asyncio.Event] = {}

    def publicar(self, sessao_id: str, jpeg: bytes) -> None:
        """Guarda o quadro e acorda quem estiver esperando.

        O `Event` é **substituído**, não reusado: o antigo é disparado para
        acordar todos os que já esperavam, e os próximos passam a esperar no
        novo. Reusar um só, com `clear()`, criaria uma corrida — entre o `set` e
        o `clear` um assinante lento perderia o aviso e ficaria esperando um
        quadro que já passou.
        """
        self._atual[sessao_id] = jpeg
        anterior = self._novidade.pop(sessao_id, None)
        self._novidade[sessao_id] = asyncio.Event()
        if anterior is not None:
            anterior.set()

    async def aguardar(self, sessao_id: str, prazo: float = ESPERA_QUADRO) -> bytes:
        """O próximo quadro desta sessão. Levanta `SemQuadro` se não vier.

        Espera **o próximo**, não devolve o atual: um stream que reenviasse o
        mesmo quadro em laço gastaria banda mostrando uma imagem parada.
        """
        evento = self._novidade.setdefault(sessao_id, asyncio.Event())
        try:
            await asyncio.wait_for(evento.wait(), prazo)
        except TimeoutError as erro:
            raise SemQuadro(
                f"nenhum quadro em {prazo:g}s — a central parou de enviar"
            ) from erro
        quadro = self._atual.get(sessao_id)
        if quadro is None:
            raise SemQuadro("quadro desapareceu entre o aviso e a leitura")
        return quadro

    def primeiro(self, sessao_id: str) -> bytes | None:
        """O quadro atual, se já houver um.

        Existe para o stream não abrir com cinco segundos de tela vazia quando a
        central já está publicando: o assinante que chega depois aproveita o
        último quadro e só então passa a esperar os próximos.
        """
        return self._atual.get(sessao_id)

    def encerrar(self, sessao_id: str) -> None:
        """Descarta quadro e áudio, e acorda quem espera, para os geradores
        poderem sair. Sem isto, os dois ficariam pendurados até o prazo."""
        self._atual.pop(sessao_id, None)
        self._audio.pop(sessao_id, None)
        for mapa in (self._novidade, self._audio_novo):
            evento = mapa.pop(sessao_id, None)
            if evento is not None:
                evento.set()

    def sessoes(self) -> int:
        """Quantas sessões têm quadro guardado. Usado em teste e diagnóstico."""
        return len(self._atual)

    # --- áudio ------------------------------------------------------------
    #
    # Separado do vídeo de propósito, e não por organização: as duas mídias
    # têm política oposta de descarte (ver `FILA_AUDIO_MAX`). Um armazenamento
    # só, com uma política só, estragaria uma das duas.

    def publicar_audio(self, sessao_id: str, pcm: bytes) -> None:
        """Enfileira um pedaço de PCM e acorda quem estiver esperando."""
        fila = self._audio.setdefault(sessao_id, deque())
        fila.append(pcm)
        # Descarta o **mais antigo** quando cheia: numa conversa ao vivo, o
        # pedaço velho não vale nada e manter a fila cheia só somaria atraso.
        while len(fila) > FILA_AUDIO_MAX:
            fila.popleft()

        anterior = self._audio_novo.pop(sessao_id, None)
        self._audio_novo[sessao_id] = asyncio.Event()
        if anterior is not None:
            anterior.set()

    async def aguardar_audio(
        self, sessao_id: str, prazo: float = ESPERA_QUADRO
    ) -> bytes:
        """O próximo trecho de PCM, juntando o que houver na fila.

        Junta em vez de devolver um pedaço por vez: se o consumidor ficou para
        trás, entregar tudo de uma vez o recoloca em dia numa escrita só. Em
        áudio isso é correto — os pedaços são contíguos, então concatenar
        **é** o sinal.
        """
        fila = self._audio.setdefault(sessao_id, deque())
        if not fila:
            evento = self._audio_novo.setdefault(sessao_id, asyncio.Event())
            try:
                await asyncio.wait_for(evento.wait(), prazo)
            except TimeoutError as erro:
                raise SemAudio(
                    f"nenhum áudio em {prazo:g}s — a central parou de enviar"
                ) from erro
        if not fila:
            raise SemAudio("fila de áudio vazia depois do aviso")

        trecho = b"".join(fila)
        fila.clear()
        return trecho

    def pedacos_de_audio(self, sessao_id: str) -> int:
        """Quantos pedaços estão na fila. Usado em teste e diagnóstico."""
        return len(self._audio.get(sessao_id, ()))


repasse = _Repasse()
