"""Autenticação do painel da central.

O sistema tem **duas fronteiras com exigências opostas**, e a assimetria é
deliberada:

- `/eventos` e `/panico` são **abertos**. Um totem em pânico não pode falhar por
  credencial. Token expirado, arquivo de configuração errado, relógio fora de
  sincronia — nada disso pode ficar entre uma pessoa em perigo e o registro do
  pedido de socorro.
- `/chamados*` e `/ws` exigem `X-POTO-Token`. É por eles que saem o relato de
  quem pediu ajuda, o histórico de acionamentos e a trilha original de cada
  chamado. Quem atende precisa de tudo isso; qualquer outra pessoa, de nada.

Sem token configurado o acesso é liberado, com aviso. É modo de
desenvolvimento: exigir credencial antes de existir uma faria `make backend`
não servir para nada. O `/health` reporta o estado, então a operação real não
chega sem ninguém notar.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import Header, HTTPException, WebSocket, status

from .. import config

logger = logging.getLogger(__name__)

CABECALHO = "X-POTO-Token"


def token_valido(recebido: str | None) -> bool:
    """Compara o token em **tempo constante**.

    `secrets.compare_digest` e não `==`: a comparação ingênua de strings sai no
    primeiro byte diferente, e a diferença de tempo permite descobrir o token um
    caractere por vez. É a mesma rede local de onde vem o tablet — e de onde
    viria quem quisesse ler os relatos.
    """
    if not config.PAINEL_TOKEN:
        return True
    if not recebido:
        return False
    return secrets.compare_digest(recebido, config.PAINEL_TOKEN)


def _sem_token_configurado() -> None:
    logger.warning(
        "POTO_PAINEL_TOKEN vazio: painel liberado sem credencial "
        "(modo desenvolvimento). Ver /health."
    )


def exigir_token(x_poto_token: str | None = Header(default=None)) -> None:
    """Dependência das rotas HTTP da central."""
    if not config.PAINEL_TOKEN:
        _sem_token_configurado()
        return
    if not token_valido(x_poto_token):
        # 401 e não 403: o cliente **pode** se autenticar, só não o fez ainda.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credencial do painel ausente ou inválida",
            headers={"WWW-Authenticate": CABECALHO},
        )


async def autorizar_websocket(websocket: WebSocket) -> bool:
    """Autoriza uma conexão de WebSocket. Devolve se pode seguir.

    Não é uma dependência do FastAPI porque `HTTPException` não tem como ser
    traduzida num handshake de WebSocket — o cliente receberia um erro sem
    explicação. Aqui o handshake é **recusado** antes do `accept()`.

    **Correção de uma afirmação anterior deste docstring.** Ele dizia que o
    navegador recebe o 1008 no `onclose` "e o painel pode exibir". Medido contra
    a Pi: não recebe. Fechar antes de aceitar faz o servidor ASGI rejeitar o
    handshake HTTP, e o cliente observa **403** — o código 1008 nunca chega, e
    num navegador o `onclose` traz 1006 (fechamento anormal), indistinguível de
    servidor fora do ar.

    O código continua certo e o docstring é que estava errado: aceitar uma
    conexão não autorizada, mesmo por um instante, é pior que recusar o
    handshake. O 1008 fica como intenção registrada no protocolo, para quem
    inspecionar o tráfego — não como sinal para o cliente.

    Consequência prática, para quem for mexer no painel depois: **não dá para
    distinguir "sem credencial" de "servidor caiu" pelo código de fechamento.**
    Hoje isso não importa, porque o `useEventosWS` ignora o código e só
    reconecta; se um dia importar, a distinção tem que vir de outro lugar — por
    exemplo um `GET /chamados` que devolve 401 antes de abrir o socket.

    O navegador não deixa definir cabeçalhos num `new WebSocket()`, então o
    token também é aceito por query string. A troca é consciente: query string
    aparece em log de acesso, e por isso o cabeçalho tem precedência — quem
    puder usá-lo, deve.
    """
    if not config.PAINEL_TOKEN:
        _sem_token_configurado()
        return True

    recebido = websocket.headers.get(CABECALHO.lower()) or websocket.query_params.get(
        "token"
    )
    if token_valido(recebido):
        return True

    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return False
