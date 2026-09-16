"""Hub de WebSocket: o broadcast para o painel da central.

O que estes testes protegem não é a entrega — é o **isolamento**. Quem espera
por um `broadcast` é a requisição que está registrando uma emergência, então a
pergunta que importa a cada caso é: *um cliente ruim consegue prejudicar os
outros, ou prender quem chamou?*

Por isso quase todo teste aqui mistura um cliente problemático com um saudável
e cobra os dois resultados: o problemático sai do conjunto **e** o saudável
recebe assim mesmo.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from app.hub import Hub

# --- Dublês -----------------------------------------------------------------


class PainelFalso:
    """Painel que se comporta: aceita e guarda o que recebeu."""

    def __init__(self) -> None:
        self.aceito = False
        self.recebidas: list[dict] = []

    async def accept(self) -> None:
        self.aceito = True

    async def send_json(self, mensagem: dict) -> None:
        self.recebidas.append(mensagem)


class PainelQueFalha(PainelFalso):
    """Tablet que sumiu: o envio estoura na hora."""

    async def send_json(self, mensagem: dict) -> None:
        raise ConnectionResetError("conexão encerrada pelo par")


class PainelTravado(PainelFalso):
    """O caso traiçoeiro: o socket não falha, ele só nunca completa.

    É o tablet que dormiu com a conexão aberta. Sem prazo de envio, este
    cliente prenderia o `broadcast` para sempre — e com ele a requisição que
    registrou a emergência.
    """

    async def send_json(self, mensagem: dict) -> None:
        await asyncio.Event().wait()


@pytest.fixture
def hub() -> Hub:
    """Hub novo por teste — o do módulo é compartilhado pela aplicação."""
    return Hub()


@pytest.fixture
def prazo_curto(monkeypatch):
    """Encurta o timeout para o teste não esperar os 2 s de produção."""
    monkeypatch.setattr("app.hub.TIMEOUT_ENVIO", 0.05)


async def conectar(hub: Hub, *paineis: PainelFalso) -> None:
    for painel in paineis:
        await hub.connect(painel)


# --- Ciclo de vida da conexão -----------------------------------------------


async def test_connect_aceita_o_handshake(hub):
    painel = PainelFalso()
    await hub.connect(painel)
    assert painel.aceito is True


async def test_connect_registra_o_cliente(hub):
    await hub.connect(PainelFalso())
    assert len(hub) == 1


async def test_hub_nasce_vazio(hub):
    assert len(hub) == 0


async def test_disconnect_remove(hub):
    painel = PainelFalso()
    await hub.connect(painel)
    hub.disconnect(painel)
    assert len(hub) == 0


async def test_disconnect_duas_vezes_nao_levanta(hub):
    """O endpoint chama `disconnect` num `finally`, e o `broadcast` pode ter
    removido o mesmo cliente antes por falha de envio. Um `KeyError` aqui
    mascararia a exceção que levou ao `finally`."""
    painel = PainelFalso()
    await hub.connect(painel)
    hub.disconnect(painel)
    hub.disconnect(painel)
    assert len(hub) == 0


def test_disconnect_de_quem_nunca_conectou_nao_levanta(hub):
    hub.disconnect(PainelFalso())
    assert len(hub) == 0


# --- Broadcast --------------------------------------------------------------


async def test_broadcast_sem_clientes_nao_levanta(hub):
    """Estado normal do sistema: totem acionado de madrugada, painel fechado.
    O registro do chamado não pode falhar porque ninguém está olhando."""
    await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})


async def test_broadcast_alcanca_todos(hub):
    paineis = [PainelFalso() for _ in range(3)]
    await conectar(hub, *paineis)

    await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})

    assert all(len(p.recebidas) == 1 for p in paineis)


async def test_formato_da_mensagem(hub):
    """Contrato do WebSocket em ARCHITECTURE.md §6: `{evento, dados}`."""
    painel = PainelFalso()
    await hub.connect(painel)

    await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})

    assert painel.recebidas == [
        {"evento": "novo_chamado", "dados": {"chamado_id": "CALL-2026-000001"}}
    ]


async def test_dados_passam_intactos(hub):
    painel = PainelFalso()
    await hub.connect(painel)
    dados = {"chamado_id": "CALL-2026-000007", "gravidade": "risco_imediato"}

    await hub.broadcast("atualizado", dados)

    assert painel.recebidas[0]["dados"] == dados


async def test_broadcasts_seguidos_acumulam(hub):
    painel = PainelFalso()
    await hub.connect(painel)

    await hub.broadcast("conectado", {})
    await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})

    assert [m["evento"] for m in painel.recebidas] == ["conectado", "novo_chamado"]


# --- Cliente que falha ------------------------------------------------------


async def test_cliente_que_falha_e_removido(hub):
    ruim = PainelQueFalha()
    await hub.connect(ruim)

    await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})

    assert len(hub) == 0


async def test_falha_de_um_nao_impede_os_outros(hub):
    """A propriedade central. Se a falha de um cliente abortasse o broadcast,
    um tablet morto na sala ao lado deixaria o operador do CSV sem ver a
    emergência."""
    ruim, bom = PainelQueFalha(), PainelFalso()
    await conectar(hub, ruim, bom)

    await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})

    assert len(bom.recebidas) == 1
    assert len(hub) == 1


async def test_broadcast_com_falha_nao_propaga(hub):
    """Quem chama é o endpoint que registra a emergência: ele não pode receber
    exceção porque um painel caiu."""
    await hub.connect(PainelQueFalha())
    await hub.broadcast("novo_chamado", {})


async def test_cliente_removido_nao_recebe_de_novo(hub):
    ruim, bom = PainelQueFalha(), PainelFalso()
    await conectar(hub, ruim, bom)

    await hub.broadcast("novo_chamado", {})
    await hub.broadcast("atualizado", {})

    assert len(bom.recebidas) == 2
    assert len(hub) == 1


async def test_todos_falharem_zera_o_conjunto(hub):
    await conectar(hub, PainelQueFalha(), PainelQueFalha())

    await hub.broadcast("novo_chamado", {})
    await hub.broadcast("novo_chamado", {})

    assert len(hub) == 0


async def test_erro_de_serializacao_tambem_remove(hub):
    """Falha do lado de cá, não da rede. Ainda assim o cliente sai e o
    broadcast não estoura — caso contrário um bug de payload derrubaria o
    registro do chamado."""

    class PainelExigente(PainelFalso):
        async def send_json(self, mensagem: dict) -> None:
            raise TypeError("objeto não serializável")

    exigente, bom = PainelExigente(), PainelFalso()
    await conectar(hub, exigente, bom)

    await hub.broadcast("novo_chamado", {})

    assert len(bom.recebidas) == 1
    assert len(hub) == 1


# --- Cliente travado --------------------------------------------------------


async def test_cliente_travado_e_removido(prazo_curto, hub):
    travado = PainelTravado()
    await hub.connect(travado)

    await asyncio.wait_for(hub.broadcast("novo_chamado", {}), timeout=2.0)

    assert len(hub) == 0


async def test_cliente_travado_nao_prende_o_broadcast(prazo_curto, hub):
    """Sem o prazo de envio este teste **pendura**, por isso o `wait_for` de
    fora: ele transforma a falha em erro de teste em vez de travar a suíte."""
    travado, bom = PainelTravado(), PainelFalso()
    await conectar(hub, travado, bom)

    await asyncio.wait_for(hub.broadcast("novo_chamado", {}), timeout=2.0)

    assert len(bom.recebidas) == 1
    assert len(hub) == 1


async def test_lento_dentro_do_prazo_continua_conectado(prazo_curto, hub):
    """Prazo não é intolerância: a rede pode engasgar sem o cliente ter morrido."""

    class PainelLento(PainelFalso):
        async def send_json(self, mensagem: dict) -> None:
            await asyncio.sleep(0.01)
            await super().send_json(mensagem)

    lento = PainelLento()
    await hub.connect(lento)

    await hub.broadcast("novo_chamado", {})

    assert len(lento.recebidas) == 1
    assert len(hub) == 1


# --- Mutação do conjunto durante o broadcast --------------------------------


async def test_desconectar_durante_o_broadcast_nao_levanta(hub):
    """Cada envio devolve o controle ao loop. Se `broadcast` iterasse sobre o
    conjunto vivo, uma desconexão nesse intervalo daria `RuntimeError: Set
    changed size during iteration` — e o broadcast morreria pela metade."""
    bom = PainelFalso()

    class PainelQueDesconectaOutro(PainelFalso):
        async def send_json(self, mensagem: dict) -> None:
            hub.disconnect(bom)
            await super().send_json(mensagem)

    await conectar(hub, PainelQueDesconectaOutro(), bom)

    await hub.broadcast("novo_chamado", {})

    assert len(hub) == 1


async def test_conectar_durante_o_broadcast_nao_levanta(hub):
    novo = PainelFalso()

    class PainelQueConectaOutro(PainelFalso):
        async def send_json(self, mensagem: dict) -> None:
            await hub.connect(novo)
            await super().send_json(mensagem)

    await hub.connect(PainelQueConectaOutro())

    await hub.broadcast("novo_chamado", {})

    # O que entrou no meio do broadcast não recebe esta mensagem, mas fica
    # registrado para a próxima.
    assert len(hub) == 2
    assert novo.recebidas == []


# --- Contra um WebSocket de verdade -----------------------------------------
#
# Os dublês acima podem mentir: `accept` e `send_json` são os deles, não os do
# Starlette. Estes últimos exercem o caminho real do handshake ao frame.


@pytest.fixture
def app_com_ws(hub):
    app = FastAPI()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            hub.disconnect(websocket)

    @app.post("/disparar")
    async def disparar():
        await hub.broadcast("novo_chamado", {"chamado_id": "CALL-2026-000001"})
        return {"conectados": len(hub)}

    return app


def test_websocket_real_recebe_o_broadcast(app_com_ws, hub):
    cliente = TestClient(app_com_ws)
    with cliente.websocket_connect("/ws") as ws:
        assert cliente.post("/disparar").json()["conectados"] == 1
        assert ws.receive_json() == {
            "evento": "novo_chamado",
            "dados": {"chamado_id": "CALL-2026-000001"},
        }


def test_dois_painies_reais_recebem(app_com_ws, hub):
    cliente = TestClient(app_com_ws)
    with cliente.websocket_connect("/ws") as a, cliente.websocket_connect("/ws") as b:
        cliente.post("/disparar")
        assert a.receive_json()["evento"] == "novo_chamado"
        assert b.receive_json()["evento"] == "novo_chamado"


def test_broadcast_depois_da_desconexao_real_nao_derruba(app_com_ws, hub):
    """Desconexão não derruba o servidor (critério da MVP-035). O cliente pode
    ainda não ter sido colhido do conjunto quando o disparo acontece — o ponto
    é que o envio a um socket fechado falha contido, e a rota responde 200."""
    cliente = TestClient(app_com_ws)
    with cliente.websocket_connect("/ws"):
        pass

    assert cliente.post("/disparar").status_code == 200
    assert cliente.post("/disparar").json()["conectados"] == 0
