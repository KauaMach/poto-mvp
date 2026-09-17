"""Autenticação do painel — duas fronteiras com exigências opostas.

A assimetria é a decisão inteira desta task:

- `/eventos` e `/panico` **abertos**. Token expirado, arquivo de configuração
  errado, relógio fora de sincronia — nada disso pode ficar entre uma pessoa em
  perigo e o registro do pedido de socorro.
- `/chamados*` e `/ws` **fechados**. É por eles que saem o relato de quem pediu
  ajuda, o histórico de acionamentos e a trilha original de cada chamado.

Metade destes testes existe para que uma mudança futura não inverta isso por
descuido: fechar o acionamento é tão grave quanto abrir o painel.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.deps import CABECALHO, token_valido
from app.main import criar_app

TOKEN = "token-de-teste-do-painel"
CABECALHOS = {CABECALHO: TOKEN}


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(config, "_CONTATOS", {"csv": "5586999990001"})
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    monkeypatch.setattr(config, "PAINEL_TOKEN", TOKEN)


@pytest.fixture
def cliente(ambiente):
    with TestClient(criar_app()) as c:
        yield c


@pytest.fixture
def sem_token(monkeypatch):
    """Modo desenvolvimento: `POTO_PAINEL_TOKEN` vazio."""
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")


def criar_chamado(cliente) -> dict:
    r = cliente.post(
        "/api/v1/eventos",
        json={
            "evento_id": str(uuid4()),
            "totem_id": "TOTEM-CCS-01",
            "tipo_ocorrencia": "seguranca",
            "texto_livre": "um homem está me seguindo",
        },
    )
    assert r.status_code == 201
    return r.json()


# ===========================================================================
# O acionamento NUNCA exige credencial
# ===========================================================================


def test_eventos_continua_aberto(cliente):
    """Com token configurado e nenhum enviado. Um totem em pânico não pode
    falhar por credencial."""
    r = cliente.post(
        "/api/v1/eventos",
        json={
            "evento_id": str(uuid4()),
            "totem_id": "T",
            "tipo_ocorrencia": "seguranca",
        },
    )
    assert r.status_code == 201


def test_panico_continua_aberto(cliente):
    r = cliente.post(
        "/api/v1/panico", json={"evento_id": str(uuid4()), "totem_id": "T"}
    )
    assert r.status_code == 201


def test_token_errado_nao_bloqueia_o_acionamento(cliente):
    """O caso perverso: um tablet com token velho em cache. Ele **não** pode
    perder a capacidade de pedir socorro por causa disso."""
    r = cliente.post(
        "/api/v1/eventos",
        json={
            "evento_id": str(uuid4()),
            "totem_id": "T",
            "tipo_ocorrencia": "seguranca",
        },
        headers={CABECALHO: "token-vencido"},
    )
    assert r.status_code == 201


@pytest.mark.parametrize("rota", ["/api/v1/health", "/api/v1/config", "/api/v1/canais"])
def test_endpoints_de_sistema_ficam_abertos(cliente, rota):
    """O totem consulta `/config` antes de qualquer autenticação, e `/health` é
    o que se usa para descobrir que o resto caiu."""
    assert cliente.get(rota).status_code == 200


# ===========================================================================
# O painel exige credencial
# ===========================================================================


@pytest.mark.parametrize(
    ("metodo", "rota", "corpo"),
    [
        ("get", "/api/v1/chamados", None),
        ("get", "/api/v1/chamados/CALL-2026-000001", None),
        ("post", "/api/v1/chamados/CALL-2026-000001/ack", None),
        ("patch", "/api/v1/chamados/CALL-2026-000001", {"status": "encerrado"}),
        (
            "post",
            "/api/v1/chamados/CALL-2026-000001/escalonar",
            {"canal": "samu_192"},
        ),
    ],
)
def test_rota_da_central_sem_token_e_401(cliente, metodo, rota, corpo):
    r = getattr(cliente, metodo)(rota, **({"json": corpo} if corpo else {}))
    assert r.status_code == 401


def test_401_e_nao_403(cliente):
    """O cliente **pode** se autenticar, só não o fez ainda — e o cabeçalho na
    resposta diz qual usar."""
    r = cliente.get("/api/v1/chamados")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == CABECALHO


def test_token_correto_libera(cliente):
    assert cliente.get("/api/v1/chamados", headers=CABECALHOS).status_code == 200


@pytest.mark.parametrize(
    "enviado", ["errado", "", "token-de-teste-do-paine", "token-de-teste-do-painell"]
)
def test_token_incorreto_e_401(cliente, enviado):
    """Inclusive prefixo e sufixo do token válido — é o que um ataque de
    tempo tentaria construir."""
    r = cliente.get("/api/v1/chamados", headers={CABECALHO: enviado})
    assert r.status_code == 401


def test_chamado_nao_vaza_antes_da_autenticacao(cliente):
    """A propriedade que importa: o 401 vem **antes** de qualquer leitura. Uma
    resposta que diferenciasse 404 de 401 já diria a um estranho quais
    protocolos existem."""
    criado = criar_chamado(cliente)

    r = cliente.get(f"/api/v1/chamados/{criado['chamado_id']}")

    assert r.status_code == 401
    assert criado["chamado_id"] not in r.text


def test_relato_nao_sai_sem_credencial(cliente):
    criar_chamado(cliente)
    assert "um homem está me seguindo" not in cliente.get("/api/v1/chamados").text


# ===========================================================================
# WebSocket
# ===========================================================================


def test_ws_sem_token_e_recusado(cliente):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with cliente.websocket_connect("/api/v1/ws") as ws:
            ws.receive_json()


def test_ws_com_token_no_cabecalho(cliente):
    with cliente.websocket_connect("/api/v1/ws", headers=CABECALHOS) as ws:
        assert ws.receive_json()["evento"] == "conectado"


def test_ws_com_token_na_query(cliente):
    """O navegador não deixa definir cabeçalhos num `new WebSocket()`. A troca é
    consciente: query string aparece em log de acesso, e por isso o cabeçalho
    tem precedência."""
    with cliente.websocket_connect(f"/api/v1/ws?token={TOKEN}") as ws:
        assert ws.receive_json()["evento"] == "conectado"


def test_ws_com_token_errado_na_query(cliente):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with cliente.websocket_connect("/api/v1/ws?token=errado") as ws:
            ws.receive_json()


def test_ws_recusado_nao_entra_no_hub(cliente):
    """A autorização vem **antes** do `connect`. Um cliente sem credencial não
    pode entrar no hub nem por um instante, ou um broadcast concorrente lhe
    entregaria o relato de um chamado."""
    from starlette.websockets import WebSocketDisconnect

    from app.hub import hub

    try:
        with cliente.websocket_connect("/api/v1/ws"):
            pass
    except WebSocketDisconnect:
        pass

    assert len(hub) == 0


def test_ws_recusado_nao_derruba_o_servidor(cliente):
    from starlette.websockets import WebSocketDisconnect

    for _ in range(3):
        try:
            with cliente.websocket_connect("/api/v1/ws"):
                pass
        except WebSocketDisconnect:
            pass

    assert cliente.get("/api/v1/health").status_code == 200


# ===========================================================================
# Modo desenvolvimento
# ===========================================================================


def test_sem_token_configurado_libera(cliente, sem_token, caplog):
    """Exigir credencial antes de existir uma faria `make backend` não servir
    para nada."""
    import logging

    with caplog.at_level(logging.WARNING):
        r = cliente.get("/api/v1/chamados")

    assert r.status_code == 200
    assert "POTO_PAINEL_TOKEN" in caplog.text


def test_sem_token_configurado_libera_o_ws(cliente, sem_token):
    with cliente.websocket_connect("/api/v1/ws") as ws:
        assert ws.receive_json()["evento"] == "conectado"


def test_liberacao_e_avisada_no_health(cliente, sem_token):
    """O aviso no log some no scroll. O `/health` é onde alguém procura antes de
    colocar em operação — e é o que impede o modo desenvolvimento de chegar à
    produção sem ninguém notar."""
    avisos = cliente.get("/api/v1/health").json()["avisos"]
    assert any("PAINEL_TOKEN" in a or "sem credencial" in a for a in avisos)


# ===========================================================================
# Comparação em tempo constante
# ===========================================================================


def test_comparacao_e_em_tempo_constante():
    """`secrets.compare_digest` e não `==`: a comparação ingênua sai no primeiro
    byte diferente, e a diferença de tempo permite descobrir o token um
    caractere por vez. É a mesma rede local de onde vem o tablet — e de onde
    viria quem quisesse ler os relatos.

    Inspeciona o **bytecode**, não o texto do fonte. A primeira versão fazia
    `"compare_digest" in inspect.getsource(...)` e era vazia: o docstring da
    própria função cita `secrets.compare_digest`, então o texto casava mesmo com
    a comparação trocada por `==`. Verificado por mutação.
    """
    assert "compare_digest" in token_valido.__code__.co_names


def test_token_valido_com_token_configurado(monkeypatch):
    monkeypatch.setattr(config, "PAINEL_TOKEN", TOKEN)
    assert token_valido(TOKEN) is True
    assert token_valido("errado") is False
    assert token_valido(None) is False


def test_token_valido_sem_token_configurado(monkeypatch):
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")
    assert token_valido(None) is True
    assert token_valido("qualquer") is True


# ===========================================================================
# O canal do totem — COR-002
# ===========================================================================
#
# `/ws/chamado/{id}` é **aberto de propósito**: o totem não tem token (o
# frontend não tem onde digitá-lo). O que torna isso aceitável é o payload —
# só `chamado_id` e `status`. Quem inventar um protocolo recebe um status, não
# um relato.


def test_ws_do_totem_nao_exige_token(cliente):
    """Se exigisse, a tela de alerta ativo perderia o status ao vivo — e o
    totem passaria a reconectar em laço durante um pânico."""
    cid = criar_chamado_para_ws(cliente)

    with cliente.websocket_connect(f"/api/v1/ws/chamado/{cid}") as ws:
        assert ws.receive_json()["evento"] == "conectado"


def test_ws_do_totem_recusa_chamado_inexistente(cliente):
    """Aceitar para depois fechar deixaria o totem reconectando contra um id
    errado. A recusa vem antes do handshake."""
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with cliente.websocket_connect("/api/v1/ws/chamado/CALL-9999-999999"):
            pass


def test_ws_do_totem_nao_entrega_relato(cliente):
    """A garantia que justifica o canal ser aberto.

    Mesmo conectado sem credencial nenhuma, e mesmo pedindo um chamado que
    existe, o que chega é a projeção — não o relato.
    """
    cid = criar_chamado_para_ws(cliente, texto="meu ex está me seguindo")

    with cliente.websocket_connect(f"/api/v1/ws/chamado/{cid}") as ws:
        ws.receive_json()  # conectado
        cliente.post(f"/api/v1/chamados/{cid}/ack", headers=CABECALHOS)
        evento = ws.receive_json()

    # `stream_url` entrou na allowlist na MEL-006 (vem `None` aqui). O que este
    # teste protege é o que **não** está na lista, e o relato é o campo que
    # importa: ele sai para o painel de propósito e não pode sair para um
    # aparelho de corredor.
    assert set(evento["dados"]) == {
        "chamado_id",
        "status",
        "stream_url",
        "audio_url",
    }
    assert "me seguindo" not in json.dumps(evento, ensure_ascii=False)


def criar_chamado_para_ws(cliente, texto: str | None = None) -> str:
    corpo = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": "seguranca",
    }
    if texto:
        corpo["texto_livre"] = texto
    return cliente.post("/api/v1/eventos", json=corpo).json()["chamado_id"]
