"""`POST /eventos` — o acionamento de uma trilha.

É aqui que tudo que as fases anteriores construíram se encontra, na ordem que
o projeto fixou:

    triar() → rotear() → merge_acionamento() → criar_chamado() → broadcast → notificar

A ordem não é arbitrária. Cada passo depende do anterior, e os dois últimos
estão nessa sequência por causa do tempo: o painel precisa acender em menos de
um segundo, e a notificação externa pode levar até dez. Inverter faria a
central esperar pelo WhatsApp.

**Este arquivo não decide nada sobre gravidade.** Ele chama `merge_acionamento()`
e obedece. O defeito que originou o módulo de merge estava exatamente num
endpoint como este, que sobrescrevia a gravidade do roteador com a inferida do
texto — e fazia a palavra "socorro" rebaixar um chamado.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks

from .. import canais, db
from ..hub import hub
from ..models import EventoIn, EventoOut, Gravidade, InstrucaoTotem, StatusChamado
from ..triagem import merge_acionamento, rotear, triar
from ..triagem.roteador import Roteamento

logger = logging.getLogger(__name__)

router = APIRouter(tags=["acionamento"])


@router.post("/eventos", status_code=201, response_model=EventoOut)
async def acionar(evento: EventoIn, tarefas: BackgroundTasks) -> EventoOut:
    """Registra um acionamento e dispara o encaminhamento."""
    triagem = triar(evento.texto_livre, evento.modo)
    routing = rotear(evento.tipo_ocorrencia, evento.modo)
    decisao = merge_acionamento(routing, triagem, texto=evento.texto_livre)

    chamado = db.criar_chamado(
        _registro(evento, decisao), decisao, _auditoria(evento, triagem)
    )

    if chamado["_duplicado"]:
        # Reenvio: dreno duplicado da fila offline, retry de rede, duplo toque.
        # Nenhum efeito colateral — não avisa a central de novo, não notifica de
        # novo. Devolve o que já foi decidido, para a tela mostrar o mesmo
        # protocolo de antes.
        return _resposta(chamado, _instrucao_armazenada(chamado), duplicado=True)

    # Antes da notificação, de propósito: a central acende na hora, sem esperar
    # o webhook. O `broadcast` nunca levanta (MVP-027), então não há caminho em
    # que um painel morto impeça o acionamento de prosseguir.
    await hub.broadcast("novo_chamado", chamado)

    # Em segundo plano: a resposta precisa chegar em menos de 2 s e o webhook
    # tem teto de 10. Quem está no totem não pode ficar olhando uma tela parada
    # enquanto um serviço externo demora — o chamado já está salvo e a central
    # já foi avisada. O resultado da notificação chega ao painel por WebSocket.
    tarefas.add_task(_notificar, chamado, decisao["canal_roteado"])

    return _resposta(chamado, decisao["instrucao"])


def _registro(evento: EventoIn, decisao: Roteamento) -> dict:
    """O que vai para o banco.

    `tipo_ocorrencia` e `modo` são os **decididos**, não os pedidos. A trilha
    `mulher` chega como `normal` e é gravada como `discreto`; um texto com sinal
    crítico de saúde numa trilha de segurança é gravado como `saude`. É o que o
    painel mostra e quem responde precisa ver — a intenção original fica no
    registro de auditoria, logo abaixo.
    """
    return {
        "evento_id": str(evento.evento_id),
        "totem_id": evento.totem_id,
        "tipo_ocorrencia": decisao["tipo"],
        "modo": decisao["modo"],
        "origem_acionamento": evento.origem_acionamento,
        "texto_livre": evento.texto_livre,
        "timestamp_local": evento.timestamp_local,
    }


def _auditoria(evento: EventoIn, triagem: dict) -> dict:
    """O que a triagem achou, mais a trilha que a pessoa de fato tocou.

    Sem `trilha_escolhida` não haveria como reconstruir depois que o merge
    redirecionou um chamado — e o merge é o mecanismo mais delicado do sistema.
    Guardar isto é o que torna "por que este chamado foi para o SAMU?"
    respondível meses depois.
    """
    return {**triagem, "trilha_escolhida": str(evento.tipo_ocorrencia)}


def _resposta(
    chamado: dict, instrucao: InstrucaoTotem, *, duplicado: bool = False
) -> EventoOut:
    """Monta a resposta a partir do que foi **persistido**.

    Status, canal e gravidade vêm do chamado no banco, não da decisão em
    memória: num reenvio os dois podem divergir, e o que vale é o registro
    original (`criar_chamado` não sobrescreve).

    O `status` é o do momento da resposta. Se a notificação falhar, ele muda
    para `falha_notificacao` no banco depois — o painel recebe a mudança por
    WebSocket, e a tela do totem não depende disso: o protocolo já é definitivo.
    """
    return EventoOut(
        chamado_id=chamado["chamado_id"],
        status=chamado["status"],
        canal_roteado=chamado["canal_roteado"],
        gravidade=chamado["gravidade"],
        instrucao_totem=instrucao,
        duplicado=duplicado,
    )


def _instrucao_armazenada(chamado: dict) -> InstrucaoTotem:
    """Reconstrói a instrução de tela de um chamado que já existe.

    A instrução não é persistida — é apresentação, não domínio. Recalcular a
    partir do tipo e do modo gravados devolve a mesma tela, porque o roteador é
    determinístico. O único ponto móvel é o horário comercial, que não afeta a
    tela: ele muda canal, e o canal vem do banco.
    """
    decisao = rotear(
        chamado["tipo_ocorrencia"],
        chamado["modo"],
        emergencia=chamado["gravidade"] == Gravidade.risco_imediato,
    )
    return decisao["instrucao"]


async def _notificar(chamado: dict, canal: str) -> None:
    """Aciona o canal e reflete o resultado no estado do chamado.

    Roda depois da resposta. Uma exceção aqui é invisível para quem chamou, por
    isso nada escapa: o chamado já está salvo e a central já foi avisada, então
    falhar em silêncio é pior do que qualquer alternativa.
    """
    try:
        sucesso, detalhe = await canais.notificar(chamado, canal)
        novo_status = (
            StatusChamado.notificado if sucesso else StatusChamado.falha_notificacao
        )
        atualizado = db.atualizar_chamado(chamado["chamado_id"], status=novo_status)
        if not sucesso:
            logger.warning(
                "%s: falha ao notificar %s — %s",
                chamado["chamado_id"],
                canal,
                detalhe,
            )
        if atualizado is not None:
            # A central vê a mudança ao vivo: sem isto, um chamado cuja
            # notificação falhou ficaria parado em "roteado" no painel, e o
            # operador não saberia que precisa ligar por fora.
            await hub.broadcast("atualizado", atualizado)
    except Exception:
        logger.exception("%s: erro ao notificar em segundo plano", chamado["chamado_id"])
