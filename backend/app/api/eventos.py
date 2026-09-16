"""Acionamento: `POST /eventos` (trilha) e `POST /panico` (alerta imediato).

Os dois endpoints abertos do sistema. **Nenhum dos dois exige credencial**, por
decisão de projeto: um totem em pânico não pode falhar por autenticação.

`/eventos` é o caminho principal, e é aqui que tudo que as fases anteriores
construíram se encontra, na ordem que o projeto fixou:

    triar() → rotear() → merge_acionamento() → criar_chamado() → broadcast → notificar

A ordem não é arbitrária. Cada passo depende do anterior, e os dois últimos
estão nessa sequência por causa do tempo: o painel precisa acender em menos de
um segundo, e a notificação externa pode levar até dez. Inverter faria a
central esperar pelo WhatsApp.

`/panico` reaproveita quase tudo, e as diferenças estão documentadas na segunda
metade do arquivo.

**Este arquivo não decide nada sobre gravidade.** Ele chama `merge_acionamento()`
e obedece. O defeito que originou o módulo de merge estava exatamente num
endpoint como este, que sobrescrevia a gravidade do roteador com a inferida do
texto — e fazia a palavra "socorro" rebaixar um chamado.

Por serem abertos, os dois têm uma restrição a mais: **nada que saia daqui pode
revelar contato institucional.** Ver `FALHA_GENERICA`, mais abaixo.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks

from .. import canais, config, db
from ..hub import hub
from ..models import (
    CanalOpcao,
    CanalResultado,
    EventoIn,
    EventoOut,
    Gravidade,
    InstrucaoTotem,
    OrigemAcionamento,
    PanicoIn,
    PanicoOut,
    StatusChamado,
    TipoOcorrencia,
    para_painel,
)
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
    await hub.broadcast("novo_chamado", para_painel(chamado))

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
            await hub.broadcast("atualizado", para_painel(atualizado))
    except Exception:
        logger.exception("%s: erro ao notificar em segundo plano", chamado["chamado_id"])


# ===========================================================================
# POST /panico
# ===========================================================================
#
# O pânico difere do acionamento por trilha em três pontos, e cada um tem uma
# razão diferente:
#
#   1. Não passa por triagem de texto. Não há texto — e não haveria tempo de
#      escrever. É crítico por definição, não por inferência.
#   2. Aciona os canais internos em PARALELO. Sequencial, o segundo canal
#      esperaria o primeiro; num pânico os dois precisam saber junto.
#   3. Nasce em `alerta_ativo`, o único estado que não fecha sozinho. Um pânico
#      só sai desse estado por ação humana na central.


@router.post("/panico", status_code=201, response_model=PanicoOut)
async def panico(evento: PanicoIn) -> PanicoOut:
    """Alerta imediato, com broadcast paralelo para os canais internos.

    Ao contrário de `/eventos`, aqui a notificação **é aguardada**: a resposta
    carrega `resultados`, e é por eles que a tela decide se oferece os botões de
    escalonamento manual. Os dois canais correm em paralelo, então o teto é o de
    um provider, não a soma.
    """
    routing = rotear(TipoOcorrencia.seguranca, evento.modo, emergencia=True)

    # Sem triagem: `merge_acionamento` com `triagem=None` devolve o roteamento
    # intacto. Passar por aqui de todo modo mantém uma única porta para a
    # decisão final — não existe caminho no sistema que a contorne.
    decisao = merge_acionamento(routing)

    chamado = db.criar_chamado(
        _registro_panico(evento, decisao),
        decisao,
        status=StatusChamado.alerta_ativo,
    )

    if chamado["_duplicado"]:
        # Reenvio de um pânico. Não aciona de novo, mas reconstrói `resultados`
        # do banco: a tela pode estar recarregando depois de perder a conexão e
        # precisa saber o que já aconteceu.
        return _resposta_panico(chamado, _resultados_gravados(chamado), duplicado=True)

    await hub.broadcast("novo_chamado", para_painel(chamado))
    resultados = await _acionar_em_paralelo(chamado)

    return _resposta_panico(chamado, resultados)


def _registro_panico(evento: PanicoIn, decisao: Roteamento) -> dict:
    """O pânico é sempre `seguranca`, sempre origem `panico`, nunca tem relato."""
    return {
        "evento_id": str(evento.evento_id),
        "totem_id": evento.totem_id,
        "tipo_ocorrencia": decisao["tipo"],
        "modo": decisao["modo"],
        "origem_acionamento": OrigemAcionamento.panico,
        "texto_livre": None,
        "timestamp_local": evento.timestamp_local,
    }


async def _acionar_em_paralelo(chamado: dict) -> list[CanalResultado]:
    """Aciona `CANAIS_INTERNOS` ao mesmo tempo, contendo a falha de cada um.

    `return_exceptions=True` pelo mesmo motivo do hub: a falha de um canal não
    pode impedir que o outro seja acionado **nem** que seja registrado. Num
    pânico, ficar sem o CSV porque a Sala Lilás está mal configurada seria o
    pior resultado possível.
    """
    canais_internos = list(config.CANAIS_INTERNOS)
    retornos = await asyncio.gather(
        *(canais.notificar(chamado, canal) for canal in canais_internos),
        return_exceptions=True,
    )

    resultados = []
    for canal, retorno in zip(canais_internos, retornos, strict=True):
        if isinstance(retorno, BaseException):
            logger.exception(
                "%s: erro ao acionar %s", chamado["chamado_id"], canal, exc_info=retorno
            )
            sucesso = False
        else:
            sucesso, _ = retorno
        resultados.append(
            CanalResultado(
                canal=canal,
                nome=config.nome_canal(canal),
                sucesso=sucesso,
                detalhe=None if sucesso else FALHA_GENERICA,
            )
        )
    return resultados


# O que a tela vê quando um canal não foi acionado.
#
# Genérico de propósito. `/panico` é um endpoint ABERTO — sem credencial, porque
# um totem em pânico não pode falhar por autenticação — e o detalhe real vem do
# provider, que repassa o corpo da resposta do webhook. Esse corpo pode ecoar o
# número que foi discado ("invalid number 5586..."), e devolvê-lo aqui entregaria
# os contatos institucionais a qualquer um que alcance a API. O detalhe completo
# fica em `notificacoes`, atrás do token do painel.
FALHA_GENERICA = "não foi possível acionar este canal"


def _resultados_gravados(chamado: dict) -> list[CanalResultado]:
    """Reconstrói `resultados` das notificações já registradas."""
    return [
        CanalResultado(
            canal=n["canal"],
            nome=config.nome_canal(n["canal"]),
            sucesso=n["sucesso"],
            detalhe=None if n["sucesso"] else FALHA_GENERICA,
        )
        for n in db.listar_notificacoes(chamado["chamado_id"])
        if not n["escalonamento"]
    ]


def _resposta_panico(
    chamado: dict, resultados: list[CanalResultado], *, duplicado: bool = False
) -> PanicoOut:
    return PanicoOut(
        chamado_id=chamado["chamado_id"],
        status=chamado["status"],
        gravidade=chamado["gravidade"],
        resultados=resultados,
        escalonamento_disponivel=_escalonamento_disponivel(),
        duplicado=duplicado,
    )


def _escalonamento_disponivel() -> list[CanalOpcao]:
    """As autoridades do estado, oferecidas para acionamento MANUAL.

    O sistema nunca disca para elas sozinho: registra que um humano acionou.
    Robo-discar 190 ou 192 por classificação automática seria irresponsável — e
    é o tipo de decisão que a máquina não toma.

    Sem `destino`: o contrato em `models.py` é explícito, e este endpoint é
    aberto.
    """
    return [
        CanalOpcao(canal=canal, nome=config.nome_canal(canal))
        for canal in config.CANAIS_ESTADO
    ]
