"""Hub de WebSocket — transmissão ao vivo para o painel da central.

Um único lugar guarda as conexões abertas do painel e empurra eventos para
todas elas. Quem publica (`POST /eventos`, `/panico`, o ACK do operador) chama
`broadcast` e não precisa saber quantos operadores estão olhando, nem se algum
tablet acabou de cair.

**A propriedade que importa é o isolamento.** O painel acende em menos de um
segundo (ARCHITECTURE.md §7 F1), e quem espera por esse broadcast é a requisição
que está registrando uma emergência. Então nenhum cliente pode atrapalhar os
outros: um tablet que travou, dormiu ou sumiu da rede não pode impedir que o
operador do CSV veja o chamado — nem segurar o `POST /eventos` que o originou.

Daí as duas defesas aqui: cada envio é independente dos demais (`gather`), e
cada um tem prazo (`TIMEOUT_ENVIO`). A segunda existe porque a primeira não
basta: um socket cujo par parou de ler não levanta exceção, ele simplesmente
nunca completa — e `gather` espera por todos.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Prazo de um envio antes de a conexão ser considerada morta.
#
# É generoso para uma rede local — onde o normal são microssegundos — e curto o
# bastante para não comprometer o orçamento de 1 s do painel. Sem prazo, um
# cliente que não lê mais fica pendurado para sempre: o envio não falha, e a
# conexão morta nunca sairia do conjunto.
TIMEOUT_ENVIO = 2.0


class Hub:
    """Conexões do painel, o broadcast para elas e o envio a uma só.

    Cada conexão carrega um **cadeado de escrita**. Um WebSocket não tolera
    dois envios simultâneos: as duas corrotinas escrevem frames intercalados no
    mesmo socket e o que chega ao navegador é lixo — a conexão morre e o
    operador para de receber alertas até reconectar.

    E há dois remetentes de verdade. O `ping` de keepalive (MVP-035) roda em
    tarefa própria, a cada 30 s, enquanto o `broadcast` dispara a cada
    acionamento. Dois acionamentos simultâneos, de dois totens, também se
    cruzam. O cadeado por cliente serializa as escritas de um socket sem
    serializar clientes diferentes — que é exatamente o que se quer: um painel
    lento não pode atrasar os outros.
    """

    def __init__(self) -> None:
        self._clientes: dict[WebSocket, asyncio.Lock] = {}

    def __len__(self) -> int:
        """Quantos painéis estão conectados agora."""
        return len(self._clientes)

    async def connect(self, ws: WebSocket) -> None:
        """Aceita o handshake e registra a conexão.

        O aceite fica aqui, e não no endpoint, para que não exista caminho em
        que um cliente entre no conjunto sem ter sido aceito. Se o handshake
        falhar, a exceção sobe e nada é registrado.
        """
        await ws.accept()
        self._clientes[ws] = asyncio.Lock()

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a conexão e o cadeado dela. Idempotente de propósito.

        O endpoint chama isto num `finally`, e o `broadcast` pode ter removido
        o mesmo cliente antes por falha de envio. Um `KeyError` aqui mascararia
        a exceção original que levou ao `finally`.
        """
        self._clientes.pop(ws, None)

    async def enviar(self, ws: WebSocket, evento: str, dados: dict) -> bool:
        """Envia a **um** cliente. Devolve se conseguiu.

        Usado pelo `conectado` de boas-vindas e pelo `ping` (MVP-035), que são
        dirigidos a uma conexão só. Passa pelo mesmo cadeado do broadcast — é o
        ponto inteiro de o cadeado existir.
        """
        cadeado = self._clientes.get(ws)
        if cadeado is None:
            return False
        try:
            await self._enviar(ws, cadeado, {"evento": evento, "dados": dados})
        except Exception as erro:
            logger.warning("painel removido do hub (%s): %r", evento, erro)
            self.disconnect(ws)
            return False
        return True

    async def broadcast(self, evento: str, dados: dict) -> None:
        """Envia `{evento, dados}` a todos os painéis conectados.

        Nunca levanta: com zero clientes é um no-op, e a falha de um cliente é
        contida — ele sai do conjunto e os demais recebem normalmente.
        """
        # Itera sobre uma cópia: cada `await` abaixo devolve o controle ao loop,
        # e uma desconexão nesse intervalo mutaria o dicionário durante a
        # iteração.
        destinos = list(self._clientes.items())
        if not destinos:
            return

        mensagem = {"evento": evento, "dados": dados}
        resultados = await asyncio.gather(
            *(self._enviar(ws, cadeado, mensagem) for ws, cadeado in destinos),
            return_exceptions=True,
        )

        for (ws, _), resultado in zip(destinos, resultados, strict=True):
            if isinstance(resultado, BaseException):
                # Amplo porque o objetivo é justamente que nenhuma falha de um
                # cliente escape para os outros: desconexão, socket já fechado,
                # timeout ou erro de serialização terminam todos do mesmo jeito.
                logger.warning("painel removido do hub (%s): %r", evento, resultado)
                self._clientes.pop(ws, None)

    async def _enviar(
        self, ws: WebSocket, cadeado: asyncio.Lock, mensagem: dict
    ) -> None:
        # O prazo cobre a espera pelo cadeado **e** o envio. Sem isso, um
        # cliente travado no meio de uma escrita deixaria o próximo remetente
        # esperando pelo cadeado para sempre — o travamento só teria mudado de
        # lugar.
        async with asyncio.timeout(TIMEOUT_ENVIO):
            async with cadeado:
                await ws.send_json(mensagem)


# Instância compartilhada. `POST /eventos` publica, `WS /ws` (MVP-035) consome.
hub = Hub()
