"""Provider `webhook` — WhatsApp de verdade, via Evolution API ou n8n.

Faz um `POST {number, text, meta}` para `POTO_NOTIF_WEBHOOK_URL`. Quem traduz
isso em mensagem de WhatsApp é o serviço do outro lado; o P.O.T.O não fala com
a Meta, não guarda sessão de WhatsApp e não depende de biblioteca de terceiro
para isso. Trocar de intermediário é trocar uma URL.

O princípio que governa este arquivo: **avisar é importante, mas registrar é
mais.** O chamado já está no banco quando `enviar` é chamada. Nenhuma falha
daqui — DNS, TLS, 502, timeout, endpoint errado — pode virar exceção e fazer o
acionamento de uma emergência parecer que não aconteceu.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from .. import config

logger = logging.getLogger("poto.notificacao")

# Teto total da tentativa, em segundos.
#
# Aplicado com `asyncio.wait_for` e não só pelo `timeout` do httpx porque o
# número do httpx é **por fase** (conectar, escrever, ler, esperar no pool):
# 10.0 ali significa até ~40 s no pior caso. No caminho de uma emergência o que
# importa é o total, então o teto é explícito.
TIMEOUT = 10.0

# Quanto da resposta do webhook entra no `detalhe` gravado em `notificacoes`.
# O suficiente para depurar ("instance not found", "invalid number"), pouco o
# bastante para não transformar a tabela de auditoria em lixeira de HTML.
LIMITE_DETALHE = 200


class WebhookProvider:
    """Entrega a notificação por HTTP.

    `transport` existe para o teste injetar um `httpx.MockTransport` — assim a
    suíte exercita o caminho real do provider, incluindo o tratamento de status
    e de exceção, sem rede.
    """

    nome = "webhook"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def enviar(
        self, destino: str, mensagem: str, meta: dict
    ) -> tuple[bool, str]:
        url = config.NOTIF_WEBHOOK_URL
        if not url:
            # Provider selecionado sem URL. **Não** cai para o `log`: isso faria
            # `/health` dizer "webhook" enquanto nada sai. Falha explícita, que
            # fica gravada em `notificacoes` e visível no painel.
            logger.warning("provider webhook selecionado sem POTO_NOTIF_WEBHOOK_URL")
            return False, "webhook sem URL configurada"

        corpo = {"number": destino, "text": mensagem, "meta": meta}

        try:
            return await asyncio.wait_for(self._postar(url, corpo), TIMEOUT)
        except TimeoutError:
            return False, f"timeout de {TIMEOUT:.0f}s"
        except httpx.HTTPError as erro:
            # Rede, DNS, TLS, URL malformada. `HTTPError` cobre a família toda.
            return False, f"{type(erro).__name__}: {erro}"
        except Exception as erro:
            # Nada escapa daqui. Ver o princípio no topo do módulo.
            logger.exception("falha inesperada no webhook")
            return False, f"erro inesperado: {erro!r}"

    async def _postar(self, url: str, corpo: dict) -> tuple[bool, str]:
        # Cliente por chamada: são dezenas de acionamentos por dia, e um cliente
        # de módulo sobreviveria ao fim do event loop entre testes.
        #
        # `follow_redirects` fica no default (False) de propósito: seguir um 3xx
        # mandaria o token e o payload para um host que ninguém configurou.
        async with httpx.AsyncClient(
            timeout=TIMEOUT, transport=self._transport
        ) as cliente:
            r = await cliente.post(url, json=corpo, headers=_cabecalhos())

        if r.is_success:
            return True, f"HTTP {r.status_code}"
        return False, f"HTTP {r.status_code}: {r.text[:LIMITE_DETALHE]}"


def _cabecalhos() -> dict[str, str]:
    """Autenticação do webhook, quando configurada.

    O token vai nos dois cabeçalhos usuais porque os dois destinos previstos
    divergem: a Evolution API espera `apikey`, e n8n (como quase todo o resto)
    espera `Authorization: Bearer`. Mandar ambos faz o provider funcionar com
    qualquer um dos dois sem configuração extra — vão para o mesmo endpoint, já
    escolhido pelo operador, então não há exposição nova.
    """
    if not config.NOTIF_WEBHOOK_TOKEN:
        return {}
    return {
        "apikey": config.NOTIF_WEBHOOK_TOKEN,
        "Authorization": f"Bearer {config.NOTIF_WEBHOOK_TOKEN}",
    }
