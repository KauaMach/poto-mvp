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

logger = logging.getLogger(__name__)

# Teto de um quadro, em bytes.
#
# 512 KB é folgado para um JPEG de webcam em resolução de conversa (a câmera da
# Pi entrega 17 KB a 640×480, medido na MVP-079) e baixo o bastante para que um
# cliente em laço não derrube a Pi antes de alguém notar.
TAMANHO_MAXIMO = 512 * 1024

# Prazo de espera por um quadro novo, em segundos.
#
# Não é o prazo da chamada — é de quanto em quanto tempo o gerador do stream
# volta a checar se deve continuar (cliente desconectou, sessão expirou). Sem
# ele, uma central que parou de enviar deixaria o gerador pendurado para sempre
# e a sessão viveria até a varredura de expiradas passar.
ESPERA_QUADRO = 5.0


class SemQuadro(RuntimeError):
    """A central não publicou quadro nenhum dentro do prazo."""


class _Repasse:
    """O quadro mais recente de cada sessão, e o aviso de que chegou um novo."""

    def __init__(self) -> None:
        self._atual: dict[str, bytes] = {}
        self._novidade: dict[str, asyncio.Event] = {}

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
        """Descarta o quadro e acorda quem espera, para o gerador poder sair."""
        self._atual.pop(sessao_id, None)
        evento = self._novidade.pop(sessao_id, None)
        if evento is not None:
            evento.set()

    def sessoes(self) -> int:
        """Quantas sessões têm quadro guardado. Usado em teste e diagnóstico."""
        return len(self._atual)


repasse = _Repasse()
