"""Montagem da aplicação: ciclo de vida, CORS e o frontend estático.

O ponto delicado aqui é a convivência entre a API e a aplicação de página
única na mesma origem. Servir as duas do mesmo lugar é o que dispensa CORS e
configuração de endpoint no cliente — mas exige que cada uma continue com o
comportamento de erro que lhe cabe.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import criar_app


@pytest.fixture
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    return tmp_path / "teste.db"


@pytest.fixture
def sem_frontend(tmp_path, monkeypatch):
    """Estado de desenvolvimento: o Vite serve na 5173, não há build."""
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "dist-inexistente"))


@pytest.fixture
def com_frontend(tmp_path, monkeypatch):
    """Simula o build enviado por `make deploy`."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<title>P.O.T.O</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("// bundle", encoding="utf-8")
    monkeypatch.setattr(config, "FRONTEND_DIST", str(dist))
    return dist


# --- Ciclo de vida ----------------------------------------------------------


def test_lifespan_cria_o_banco(banco, sem_frontend):
    """Idempotente e a cada start: uma Pi com cartão novo se reconstrói sozinha."""
    assert not banco.exists()
    with TestClient(criar_app()):
        assert banco.exists()


def test_health_responde(banco, sem_frontend):
    with TestClient(criar_app()) as cliente:
        r = cliente.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_confirma_o_banco(banco, sem_frontend):
    with TestClient(criar_app()) as cliente:
        assert cliente.get("/api/v1/health").json()["banco"] is True


def test_subir_duas_vezes_nao_quebra(banco, sem_frontend):
    for _ in range(2):
        with TestClient(criar_app()) as cliente:
            assert cliente.get("/api/v1/health").status_code == 200


# --- CORS -------------------------------------------------------------------


def test_cors_nunca_e_curinga():
    """`allow_origins=["*"]` num serviço que registra ocorrências de violência
    seria entregar a API a qualquer página da internet."""
    assert "*" not in config.CORS_ORIGINS


def test_cors_vem_da_configuracao(banco, sem_frontend, monkeypatch):
    monkeypatch.setattr(config, "CORS_ORIGINS", ["http://exemplo.local"])
    with TestClient(criar_app()) as cliente:
        r = cliente.get(
            "/api/v1/health", headers={"Origin": "http://exemplo.local"}
        )
    assert r.headers.get("access-control-allow-origin") == "http://exemplo.local"


def test_origem_desconhecida_nao_recebe_permissao(banco, sem_frontend, monkeypatch):
    monkeypatch.setattr(config, "CORS_ORIGINS", ["http://exemplo.local"])
    with TestClient(criar_app()) as cliente:
        r = cliente.get("/api/v1/health", headers={"Origin": "http://invasor.com"})
    assert "access-control-allow-origin" not in r.headers


# --- Frontend ausente -------------------------------------------------------


def test_sem_build_a_api_continua_de_pe(banco, sem_frontend):
    """Em desenvolvimento não há `dist/` — o backend não pode se recusar a subir."""
    with TestClient(criar_app()) as cliente:
        assert cliente.get("/api/v1/health").status_code == 200


# --- Frontend montado -------------------------------------------------------


def test_raiz_redireciona_para_o_totem(banco, com_frontend):
    """MEL-003: a raiz deixou de **ser** o totem e passou a apontar para ele.

    `follow_redirects=False` de propósito — com o padrão `True` o teste veria
    apenas o 200 do destino e passaria mesmo sem redirect nenhum.
    """
    with TestClient(criar_app()) as cliente:
        r = cliente.get("/", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "/totem"


def test_raiz_seguida_chega_no_totem(banco, com_frontend):
    """O par do teste acima: o redirect não aponta para o vazio."""
    with TestClient(criar_app()) as cliente:
        r = cliente.get("/")

    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert r.url.path == "/totem"


def test_redirect_da_raiz_e_temporario(banco, com_frontend):
    """301 ficaria **gravado** no navegador e em cada tablet, e voltar atrás
    exigiria limpar o cache de aparelho por aparelho. A MEL-003 ainda tem opções
    abertas sobre o que a raiz vira; um permanente fecharia essa porta por um
    salto de HTTP economizado."""
    with TestClient(criar_app()) as cliente:
        r = cliente.get("/", follow_redirects=False)

    assert r.status_code == 307, "não pode ser 301/308 (permanente)"


@pytest.mark.parametrize(
    "rota",
    [
        "/totem",
        "/totem/",
        # A sub-ação "Descrever por voz". Do lado do backend ela não se
        # distingue de qualquer outro caminho — quem decide é o `rotaAtual()`
        # do frontend, verificado em `frontend/scripts/verificar-rotas.mjs`.
        "/totem/voz",
        "/painel",
        "/painel/",
        "/rota-qualquer",
    ],
)
def test_rotas_da_aplicacao_recebem_o_index(banco, com_frontend, rota):
    """A aplicação é de página única: o roteamento acontece no cliente, então
    qualquer caminho desconhecido precisa entregar o index e deixar o React
    decidir. Sem isto, abrir `/painel` direto no navegador daria 404."""
    with TestClient(criar_app()) as cliente:
        r = cliente.get(rota)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_assets_sao_servidos(banco, com_frontend):
    with TestClient(criar_app()) as cliente:
        assert cliente.get("/assets/app.js").status_code == 200


# --- A fronteira entre a API e a aplicação ----------------------------------


def test_rota_de_api_inexistente_devolve_404_json(banco, com_frontend):
    """O caso que o fallback de SPA quase quebrou.

    Devolver `index.html` com 200 aqui faria um cliente receber HTML onde
    espera JSON, e mascararia erro de digitação no endpoint — o pior tipo de
    falha, porque não parece falha.
    """
    with TestClient(criar_app()) as cliente:
        r = cliente.get("/api/v1/nao-existe")
    assert r.status_code == 404
    assert "application/json" in r.headers["content-type"]
    assert "detail" in r.json()


def test_totem_e_rota_explicita_no_frontend(banco, com_frontend):
    """O backend serve o mesmo `index.html` para qualquer caminho fora de
    `/api` — então, do lado dele, `/totem` não se distingue de
    `/rota-qualquer`. Quem distingue é o `rotaAtual()` do frontend, e isso é
    verificado em `frontend/scripts/verificar-rotas.mjs`.

    Este teste existe para deixar o registro de **onde** a garantia vive, em vez
    de a ausência dela aqui parecer esquecimento.
    """
    with TestClient(criar_app()) as cliente:
        assert cliente.get("/totem").status_code == 200


@pytest.mark.parametrize("rota", ["/api/qualquer", "/api/v1/tambem-nao", "/api"])
def test_nada_sob_api_cai_no_fallback(banco, com_frontend, rota):
    with TestClient(criar_app()) as cliente:
        r = cliente.get(rota)
    assert r.status_code == 404
    assert "text/html" not in r.headers.get("content-type", "")


def test_api_funciona_com_o_frontend_montado(banco, com_frontend):
    """O estático é montado na raiz e poderia sombrear a API."""
    with TestClient(criar_app()) as cliente:
        assert cliente.get("/api/v1/health").status_code == 200


def test_docs_continuam_acessiveis(banco, com_frontend):
    with TestClient(criar_app()) as cliente:
        assert cliente.get("/docs").status_code == 200


# ---------------------------------------------------------------------------
# WebSocket em caminho desconhecido
# ---------------------------------------------------------------------------
#
# O estático montado na raiz recebe tudo que o router não casou — inclusive
# conexões WebSocket. O `StaticFiles` do Starlette abre com
# `assert scope["type"] == "http"`, então sem tratamento o resultado é um
# `AssertionError` virando 500 com traceback no log.
#
# Encontrado ao digitar `/api/v1/ws/painel` em vez de `/api/v1/ws`.


@pytest.mark.parametrize(
    "caminho",
    [
        "/api/v1/ws/painel",  # o erro de digitação que revelou o bug
        "/api/v1/ws-errado",
        "/ws",  # fora do prefixo da API
        "/qualquer-coisa",
    ],
)
def test_websocket_em_caminho_desconhecido_e_recusado(banco, com_frontend, caminho):
    """Recusa limpa, não 500.

    `WebSocketDisconnect` é como o `TestClient` reporta uma recusa de
    handshake. O que este teste protege é o **contrário**: que não venha um
    `AssertionError`, que é o que acontecia antes.
    """
    from starlette.websockets import WebSocketDisconnect

    with TestClient(criar_app()) as cliente:
        with pytest.raises(WebSocketDisconnect):
            with cliente.websocket_connect(caminho):
                pass


def test_websocket_do_painel_continua_conectando(banco, com_frontend):
    """O par positivo do teste acima.

    Sem ele, recusar **todo** WebSocket passaria pelo teste anterior — e o
    painel pararia de receber atualizações em tempo real sem nada acusar.
    """
    with TestClient(criar_app()) as cliente:
        with cliente.websocket_connect("/api/v1/ws") as ws:
            assert ws.receive_json()["evento"] == "conectado"
