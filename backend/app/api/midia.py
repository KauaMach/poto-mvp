"""Mídia: dispositivos, sessões e streams.

Três grupos de rota, com exigências diferentes:

- `GET /dispositivos` (MVP-073) — o que existe para capturar.
- `POST/DELETE /chamados/{id}/midia` (MVP-077) — abre e fecha a autorização.
- `GET /midia/{tipo}/{id}/stream` (MVP-075/076) — a captura em si.

Os dois primeiros exigem `X-POTO-Token`. **O terceiro não pode**, e a razão é
técnica: o stream vai num `<img src="…">` e num `<audio src="…">`, e o navegador
não deixa definir cabeçalhos nesses elementos. A autorização dele é a
`sessao` na query string — um token de uso único, com prazo de 10 minutos,
que só existe se alguém autenticado o pediu para um chamado ativo.

É a mesma troca consciente do `/ws` (MVP-040): query string aparece em log de
acesso, e por isso o que vai ali é um token efêmero e não a credencial do
painel.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import midia
from ..midia import sessao as sessoes
from ..models import MidiaIn, MidiaOut
from .deps import CABECALHO, exigir_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["midia"], dependencies=[Depends(exigir_token)])

# Sem a dependência de token: a autorização é a `sessao` da query string.
router_stream = APIRouter(tags=["midia"])


@router.get("/dispositivos")
def dispositivos() -> list[midia.Dispositivo]:
    """Câmeras e microfones detectados agora.

    **Lista vazia é resposta válida**, não erro: a Pi pode não ter câmera
    plugada, e a API sobe igual. Um 404 ou 503 aqui faria o painel tratar
    "sem hardware" como falha do serviço.

    Detecta a cada chamada, sem cache: uma câmera USB pode ser conectada com o
    sistema no ar, e um cache faria o operador reiniciar o serviço para ela
    aparecer.
    """
    return midia.listar()


@router.post("/chamados/{chamado_id}/midia", response_model=MidiaOut, status_code=201)
def abrir_midia(chamado_id: str, pedido: MidiaIn, request: Request) -> MidiaOut:
    """Autoriza captura de um dispositivo para este chamado.

    Recusa com **409** se o chamado está encerrado ou cancelado: um atendimento
    concluído não justifica olhar o corredor, e permitir isso transformaria o
    histórico de chamados numa lista de pretextos para ligar a câmera.
    """
    try:
        s = sessoes.abrir(chamado_id, pedido.dispositivo_id, _operador(request))
    except sessoes.SessaoRecusada as recusa:
        raise HTTPException(status_code=recusa.status, detail=recusa.detalhe) from None

    return MidiaOut(
        sessao_id=s.sessao_id,
        stream_url=sessoes.url_do_stream(s),
        expira_em=sessoes.DURACAO_SEG,
        dispositivo_id=s.dispositivo_id,
        tipo=s.tipo,
    )


@router.delete("/chamados/{chamado_id}/midia", status_code=204)
def fechar_midia(chamado_id: str, sessao: str | None = None) -> None:
    """Encerra imediatamente.

    Sem `sessao`, encerra **todas** as do chamado — é o que o painel chama ao
    fechar o detalhe, quando pode haver vídeo e áudio abertos juntos.
    """
    if sessao:
        sessoes.fechar(sessao)
    else:
        sessoes.fechar_do_chamado(chamado_id, "detalhe do chamado fechado")


@router.get("/chamados/{chamado_id}/midia/auditoria")
def auditoria(chamado_id: str) -> list[dict]:
    """O rastro de acesso à mídia deste chamado.

    Exposto na API, e não só no banco, porque auditoria que exige acesso ao
    servidor não é auditoria — é arquivo. Quem fiscaliza precisa poder olhar.
    """
    return midia_auditoria(chamado_id)


def midia_auditoria(chamado_id: str) -> list[dict]:
    from .. import db

    return db.listar_auditoria_midia(chamado_id)


def _operador(request: Request) -> str | None:
    """Quem pediu a sessão.

    Hoje o sistema tem **um** token compartilhado (MVP-040), não contas
    individuais, então o melhor disponível é o endereço de quem chamou. Fica
    registrado como tal, sem fingir identidade que o sistema não tem — um campo
    `operador` com um nome inventado seria pior que um IP honesto.
    """
    quem = request.client.host if request.client else "?"
    marcado = "com token" if request.headers.get(CABECALHO.lower()) else "sem token"
    return f"{quem} ({marcado})"
