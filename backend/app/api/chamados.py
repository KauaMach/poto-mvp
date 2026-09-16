"""Rotas da central: leitura dos chamados e as ações do operador.

O lado oposto do acionamento. Enquanto `/eventos` e `/panico` são abertos e
escrevem sozinhos, estas rotas pertencem à central — exigirão `X-POTO-Token`
(MVP-040).

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
from ..hub import hub
from ..models import (
    ChamadoDetalhe,
    ChamadoOut,
    ChamadoUpdate,
    EstadoOut,
    Gravidade,
    NotificacaoOut,
    StatusChamado,
    TipoOcorrencia,
    para_painel,
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


# ===========================================================================
# Ações do operador
# ===========================================================================
#
# As duas primeiras rotas em que um humano move um chamado. Nenhuma delas
# valida transições de estado, e isso é decisão, não esquecimento — ver a nota
# em `atualizar`.


@router.post("/chamados/{chamado_id}/ack", response_model=ChamadoOut)
async def reconhecer(chamado_id: str) -> ChamadoOut:
    """O operador assume o chamado: para o relógio do SLA.

    Vale também para um pânico. `alerta_ativo` não fecha **sozinho** — mas ACK
    não é sozinho, é a central dizendo "recebi". É o que a tela do totem mostra
    como *"Central recebeu"* (ARCHITECTURE.md §7 F2).

    Dois operadores clicando não é erro: o segundo ACK devolve 200 e não
    reescreve o `acked_at` original (`db.ack_chamado`), de onde sai a métrica de
    tempo até o reconhecimento.
    """
    chamado = db.ack_chamado(chamado_id)
    if chamado is None:
        raise HTTPException(status_code=404, detail="chamado não encontrado")

    await _avisar(chamado)
    return ChamadoOut.model_validate(chamado)


@router.patch("/chamados/{chamado_id}", response_model=ChamadoOut)
async def atualizar(chamado_id: str, mudanca: ChamadoUpdate) -> ChamadoOut:
    """Muda estado e/ou observação.

    **Não há máquina de estados restringindo as transições, de propósito.** A
    regra que protege o sistema — nada rebaixa a proteção já concedida — vale
    para a *inferência automática*, não para o julgamento humano. Um operador
    precisa poder cancelar um trote, encerrar um chamado resolvido por telefone
    ou reabrir um que voltou, e uma tabela de transições permitidas acabaria
    travando alguém no meio de uma emergência por um caso que ninguém previu.

    O que garante a responsabilidade é o rastro, não a proibição: `estado_log`
    é append-only por gatilho de banco (MVP-015), então toda movimentação fica
    registrada. A MVP-040 acrescenta a credencial que diz *quem* mexeu.

    Corpo vazio é no-op válido: devolve o chamado como está.
    """
    chamado = db.atualizar_chamado(
        chamado_id, status=mudanca.status, observacao=mudanca.observacao
    )
    if chamado is None:
        raise HTTPException(status_code=404, detail="chamado não encontrado")

    await _avisar(chamado)
    return ChamadoOut.model_validate(chamado)


async def _avisar(chamado: dict) -> None:
    """Transmite o chamado atualizado para os painéis conectados.

    Sempre, mesmo quando nada mudou de fato. Um `atualizado` repetido é inócuo
    para um painel que renderiza estado, e dá nova chance a quem tinha acabado
    de reconectar e perdeu o anterior.
    """
    await hub.broadcast("atualizado", para_painel(chamado))
