"""Rotas da central: leitura dos chamados e as ações do operador.

O lado oposto do acionamento. Enquanto `/eventos` e `/panico` são abertos e
escrevem sozinhos, estas rotas pertencem à central e exigem `X-POTO-Token`
(MVP-040) — a dependência está no router, para que uma rota nova nasça
protegida.

**É a fronteira mais sensível da API.** O que sai daqui inclui o relato de quem
pediu ajuda, o histórico de quem foi acionado e a trilha original de cada
chamado. Quem atende precisa de tudo isso; qualquer outra pessoa, de nada. Por
isso os contratos de `models.py` são lista de campos permitidos, e o `destino`
das notificações sai mascarado.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from .. import canais, config, db
from ..canais.log import mascarar
from ..hub import hub
from ..midia import sessao as sessoes_midia
from ..models import (
    CanalResultado,
    ChamadoDetalhe,
    ChamadoOut,
    ChamadoUpdate,
    EscalonamentoIn,
    EstadoOut,
    Gravidade,
    NotificacaoOut,
    StatusChamado,
    TipoOcorrencia,
    para_painel,
)
from .deps import autorizar_websocket, exigir_token

logger = logging.getLogger(__name__)

# `dependencies` no router e não em cada rota: é o que faz uma rota nova nascer
# protegida. Esquecer de decorar um endpoint aqui expõe o relato de alguém — o
# default precisa ser fechado.
#
# O `/ws` fica **fora** deste router, logo abaixo: uma dependência que levanta
# `HTTPException` não tem tradução num handshake de WebSocket.
router = APIRouter(tags=["central"], dependencies=[Depends(exigir_token)])

# Sem a dependência de token: a autorização acontece dentro do handshake.
router_ws = APIRouter(tags=["central"])


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

    # Encerrar o chamado encerra a mídia (MVP-077). Deixar a câmera aberta
    # depois de o atendimento acabar seria exatamente a vigilância que a sessão
    # existe para impedir — e ninguém lembraria de fechar à mão.
    if chamado["status"] in (StatusChamado.encerrado, StatusChamado.cancelado):
        fechadas = sessoes_midia.fechar_do_chamado(
            chamado_id, f"chamado {chamado['status']}"
        )
        if fechadas:
            logger.info("%s: %d sessão(ões) de mídia encerrada(s)", chamado_id, fechadas)

    await _avisar(chamado)
    return ChamadoOut.model_validate(chamado)


async def _avisar(chamado: dict) -> None:
    """Transmite o chamado atualizado para os painéis conectados.

    Sempre, mesmo quando nada mudou de fato. Um `atualizado` repetido é inócuo
    para um painel que renderiza estado, e dá nova chance a quem tinha acabado
    de reconectar e perdeu o anterior.
    """
    await hub.broadcast("atualizado", para_painel(chamado))


# ===========================================================================
# Escalonamento manual
# ===========================================================================


@router.post("/chamados/{chamado_id}/escalonar", response_model=CanalResultado)
async def escalonar(chamado_id: str, pedido: EscalonamentoIn) -> CanalResultado:
    """Aciona uma autoridade do estado por decisão de um humano na central.

    **O sistema nunca chega aqui sozinho.** Não há caminho automático para
    `CANAIS_ESTADO`: nem a triagem, nem o roteador, nem `/eventos`, nem
    `/panico` acionam PM, SAMU, Bombeiros ou o 180 — eles são *oferecidos* na
    tela (`escalonamento_disponivel`) e só saem daqui por um POST explícito.
    Acionar o 190 por classificação automática seria irresponsável, e é o tipo
    de decisão que a máquina não toma.

    O registro fica com `escalonamento=1`, separando para sempre a decisão
    humana do encaminhamento automático no histórico do chamado.

    **Não mexe no status.** Um pânico escalonado continua em `alerta_ativo`:
    chamar a PM não resolve a emergência, e rebaixar o alerta aqui apagaria da
    tela do totem justamente o estado que mantém o cronômetro correndo.
    """
    if pedido.canal not in config.CANAIS_ESTADO:
        # Só as quatro autoridades do estado. Um canal interno acionado por aqui
        # entraria no histórico marcado como decisão humana de escalonamento,
        # contaminando a única distinção que o registro faz entre o que o
        # sistema decidiu e o que uma pessoa decidiu.
        raise HTTPException(
            status_code=422,
            detail=(
                f"canal {pedido.canal!r} não é de escalonamento; "
                f"permitidos: {config.CANAIS_ESTADO}"
            ),
        )

    chamado = db.obter_chamado(chamado_id)
    if chamado is None:
        raise HTTPException(status_code=404, detail="chamado não encontrado")

    sucesso, detalhe = await canais.notificar(
        chamado, pedido.canal, escalonamento=True
    )
    return CanalResultado(
        canal=pedido.canal,
        nome=config.nome_canal(pedido.canal),
        sucesso=sucesso,
        detalhe=detalhe,
    )


# ===========================================================================
# WS /ws — o canal de tempo real do painel
# ===========================================================================

# Intervalo do ping de aplicação.
#
# O uvicorn já manda ping de **protocolo**, mas o navegador não expõe isso ao
# JavaScript: a API WebSocket não avisa sobre pong. Sem um ping no nível da
# aplicação, o painel não tem como distinguir "nada aconteceu nos últimos dez
# minutos" de "a conexão morreu e eu não sei". Num painel de emergência, os
# dois estados parecem idênticos na tela e significam o oposto.
INTERVALO_PING = 30.0


@router_ws.websocket("/ws")
async def painel_ao_vivo(websocket: WebSocket) -> None:
    """Mantém o painel em tempo real.

    O `hub` faz a transmissão; esta função só cuida do ciclo de vida de uma
    conexão. Ela não lê nada de útil do cliente — o painel é um consumidor — mas
    **precisa** ficar bloqueada num `receive`: é assim que a desconexão chega.
    """
    # Antes do `connect`, que é quem aceita o handshake: um cliente sem
    # credencial não pode entrar no hub nem por um instante, ou um broadcast
    # concorrente lhe entregaria o relato de um chamado.
    if not await autorizar_websocket(websocket):
        return

    await hub.connect(websocket)

    # O ping em tarefa própria, e não dentro do laço com `wait_for`: cancelar um
    # `receive` a cada 30 s para dar a vez ao ping é o que faz uma implementação
    # perder a mensagem de desconexão e deixar a conexão morta no hub.
    pingador = asyncio.create_task(_pingar(websocket))
    try:
        await hub.enviar(websocket, "conectado", _dados_da_conexao())
        while True:
            # Bloqueia até o cliente desconectar. Qualquer coisa que o painel
            # mande é ignorada de propósito: este canal é de leitura, e aceitar
            # comandos por aqui criaria uma via de escrita sem as validações
            # dos endpoints REST.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("conexão de painel encerrada com erro", exc_info=True)
    finally:
        # O `disconnect` é o que importa: sem ele o hub guarda uma conexão morta
        # e todo broadcast seguinte tenta escrever nela.
        #
        # O `cancel` é redundante **para a correção** e mantido de propósito —
        # verificado por mutação: removê-lo não falha teste nenhum, porque
        # `_pingar` também para sozinho quando `hub.enviar` devolve `False`.
        # A diferença é de tempo: sem o cancel, cada painel desconectado deixa
        # uma tarefa dormindo até 30 s antes de descobrir isso. Num tablet em
        # wi-fi instável, reconectando a cada minuto, elas acumulam.
        pingador.cancel()
        hub.disconnect(websocket)


async def _pingar(websocket: WebSocket) -> None:
    """Manda `ping` enquanto a conexão viver.

    Para sozinho quando o envio falha: `hub.enviar` devolve `False` e já removeu
    o cliente. Assim a tarefa não fica girando contra um socket morto mesmo se
    alguém esquecer o `cancel()`.
    """
    while True:
        await asyncio.sleep(INTERVALO_PING)
        if not await hub.enviar(websocket, "ping", {}):
            return


def _dados_da_conexao() -> dict:
    """O que o painel precisa saber no instante em que conecta.

    `paineis` inclui quem acabou de entrar. É o que permite a tela mostrar
    "2 operadores conectados" — e perceber que ninguém mais está olhando.
    """
    return {"paineis": len(hub), "servidor": db.agora_iso()}
