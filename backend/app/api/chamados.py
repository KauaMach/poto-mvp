"""Leitura do painel da central: `GET /chamados` e `GET /chamados/{id}`.

O lado oposto do acionamento. Enquanto `/eventos` e `/panico` são abertos e
escrevem, estas rotas são de leitura e pertencem à central — exigirão
`X-POTO-Token` (MVP-040).

**É a fronteira mais sensível da API.** O que sai daqui inclui o relato de quem
pediu ajuda, o histórico de quem foi acionado e a trilha original de cada
chamado. Quem atende precisa de tudo isso; qualquer outra pessoa, de nada. Por
isso os contratos de `models.py` são lista de campos permitidos, e o `destino`
das notificações sai mascarado.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException

from .. import config, db
from ..canais.log import mascarar
from ..models import (
    ChamadoDetalhe,
    ChamadoOut,
    EstadoOut,
    Gravidade,
    NotificacaoOut,
    StatusChamado,
    TipoOcorrencia,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["central"])


@router.get("/chamados", response_model=list[ChamadoOut])
def listar(
    tipo: TipoOcorrencia | None = None,
    status: StatusChamado | None = None,
    gravidade: Gravidade | None = None,
) -> list[ChamadoOut]:
    """Os chamados mais recentes, com filtros combináveis.

    Os filtros são tipados pelos enums do domínio, então um valor inválido
    devolve **422** em vez de lista vazia. A diferença importa: uma lista vazia
    por causa de `?status=reconhecidos` (no plural, por engano) diria ao
    operador que não há chamados — um falso negativo num painel de emergência.
    """
    return [
        ChamadoOut.model_validate(linha)
        for linha in db.listar_chamados(tipo, status, gravidade)
    ]


@router.get("/chamados/{chamado_id}", response_model=ChamadoDetalhe)
def detalhar(chamado_id: str) -> ChamadoDetalhe:
    """Um chamado com sua história completa: notificações e transições."""
    chamado = db.obter_chamado(chamado_id)
    if chamado is None:
        raise HTTPException(status_code=404, detail="chamado não encontrado")

    return ChamadoDetalhe(
        **ChamadoOut.model_validate(chamado).model_dump(),
        triagem=_triagem(chamado),
        notificacoes=[
            _notificacao(n) for n in db.listar_notificacoes(chamado_id)
        ],
        estados=[EstadoOut.model_validate(e) for e in db.listar_estados(chamado_id)],
    )


def _notificacao(linha: dict) -> NotificacaoOut:
    """Uma tentativa de acionamento, com o contato reduzido ao que basta.

    O destino completo não sai da API. Ver `NotificacaoOut` em `models.py`.
    """
    return NotificacaoOut(
        canal=linha["canal"],
        nome=config.nome_canal(linha["canal"]),
        destino=mascarar(linha["destino"]),
        provider=linha["provider"],
        sucesso=linha["sucesso"],
        mensagem=linha["mensagem"],
        detalhe=linha["detalhe"],
        escalonamento=linha["escalonamento"],
        created_at=linha["created_at"],
    )


def _triagem(chamado: dict) -> dict | None:
    """Decodifica o registro de auditoria da triagem.

    Devolve `None` se o conteúdo estiver corrompido, em vez de derrubar a
    leitura: um `triagem_json` ilegível é perda de informação diagnóstica, não
    razão para esconder o chamado do operador que precisa atendê-lo.
    """
    bruto = chamado.get("triagem_json")
    if not bruto:
        return None
    try:
        decodificado = json.loads(bruto)
    except (json.JSONDecodeError, TypeError):
        logger.warning("%s: triagem_json ilegível", chamado["chamado_id"])
        return None
    return decodificado if isinstance(decodificado, dict) else None
