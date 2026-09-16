"""Sessão de mídia — o controle que impede a câmera de virar vigilância.

**Este arquivo é a task.** A MVP-077 não é sobre fazer a câmera funcionar; é
sobre garantir que ela só funcione dentro de limites, e são estes testes que
transformam a garantia em algo verificável.

A afirmação que o projeto faz é: *nenhum stream existe fora de uma sessão
válida, vinculada a um chamado ativo, com prazo, auditada nas duas pontas.*
Cada teste aqui fecha um caminho pelo qual a mídia deixaria de ser socorro e
passaria a ser observação.
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import criar_app
from app.midia import sessao as sessoes

CAMERA = {
    "id": "csi:0",
    "tipo": "camera",
    "nome": "Câmera CSI (imx219)",
    "dono": "RaspPoto",
    "status": "disponivel",
    "capacidades": {"origem": "csi", "indice": 0, "rotacao": 180},
}
MICROFONE = {
    "id": "alsa:2,0",
    "tipo": "microfone",
    "nome": "USB Composite Device — USB Audio",
    "dono": "RaspPoto",
    "status": "disponivel",
    "capacidades": {"origem": "alsa", "device": "plughw:2,0"},
}


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")
    monkeypatch.setattr(
        config, "_CONTATOS", {c: "5586999990001" for c in config.CANAIS}
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")

    # Hardware falso: `sessao.py` faz `from . import obter`, então o patch é no
    # atributo do módulo que o usa — patchear `app.midia.obter` não o alcança
    # (lição da MVP-074).
    dispositivos = {CAMERA["id"]: CAMERA, MICROFONE["id"]: MICROFONE}
    monkeypatch.setattr(sessoes, "obter", lambda i: dispositivos.get(i))

    # Sessões vivem em memória e o dicionário é global.
    monkeypatch.setattr(sessoes, "_sessoes", {})
    db.init_db()


@pytest.fixture
def cliente():
    with TestClient(criar_app()) as c:
        yield c


def criar_chamado(cliente, tipo: str = "seguranca") -> str:
    r = cliente.post(
        "/api/v1/eventos",
        json={
            "evento_id": str(uuid4()),
            "totem_id": "TOTEM-CCS-01",
            "tipo_ocorrencia": tipo,
        },
    )
    assert r.status_code == 201
    return r.json()["chamado_id"]


# ===========================================================================
# A garantia central: sem chamado ativo, não há mídia
# ===========================================================================


def test_abrir_com_chamado_ativo(cliente):
    cid = criar_chamado(cliente)

    r = cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"})

    assert r.status_code == 201
    corpo = r.json()
    assert corpo["sessao_id"]
    assert corpo["expira_em"] == 600
    assert corpo["stream_url"].startswith("/api/v1/midia/camera/csi:0/stream?sessao=")


@pytest.mark.parametrize("status", ["encerrado", "cancelado"])
def test_chamado_encerrado_recusa_com_409(cliente, status):
    """**O caminho que transformaria o histórico numa lista de pretextos.**

    Um atendimento concluído não justifica olhar o corredor. 409 e não 403: o
    chamado existe e a credencial está certa — o que não pode é o estado.
    """
    cid = criar_chamado(cliente)
    cliente.patch(f"/api/v1/chamados/{cid}", json={"status": status})

    r = cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"})

    assert r.status_code == 409
    assert status in r.json()["detail"]


def test_chamado_inexistente_e_404(cliente):
    """404 e não 409: a distinção diz ao painel se o dado dele está velho ou se
    o pedido era inválido."""
    r = cliente.post(
        "/api/v1/chamados/CALL-2026-999999/midia", json={"dispositivo_id": "csi:0"}
    )
    assert r.status_code == 404


def test_dispositivo_inexistente_e_404(cliente):
    """Uma câmera desconectada entre a listagem no painel e o pedido."""
    cid = criar_chamado(cliente)
    r = cliente.post(
        f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:99"}
    )
    assert r.status_code == 404


def test_nao_existe_midia_sem_chamado(cliente):
    """Não há rota para "ver a câmera do totem" como ação independente.

    A mídia é sempre **deste** chamado. Este teste trava a ausência da rota: se
    alguém acrescentar `POST /midia/camera/csi:0/abrir`, ele falha.
    """
    for rota in (
        "/api/v1/midia/camera/csi:0/abrir",
        "/api/v1/midia/abrir",
        "/api/v1/midia/sessao",
    ):
        assert cliente.post(rota, json={}).status_code in (404, 405)


# ===========================================================================
# Validação de sessão — o 403 que o critério manda testar explicitamente
# ===========================================================================


def test_validar_sem_sessao_e_403():
    with pytest.raises(sessoes.SessaoRecusada) as erro:
        sessoes.validar("inventada", "csi:0")
    assert erro.value.status == 403


def test_sessao_expirada_e_403(cliente, monkeypatch):
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    # Envelhece a sessão em vez de esperar 10 minutos.
    s.expira_em = time.monotonic() - 1

    with pytest.raises(sessoes.SessaoRecusada) as erro:
        sessoes.validar(s.sessao_id, "csi:0")
    assert erro.value.status == 403
    assert "expirada" in erro.value.detalhe


def test_sessao_da_camera_nao_autoriza_o_microfone(cliente):
    """**Áudio é mais invasivo que imagem**, e uma sessão de vídeo não pode
    virar escuta. Sem esta checagem, um único pedido de câmera daria acesso ao
    som do local."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    with pytest.raises(sessoes.SessaoRecusada) as erro:
        sessoes.validar(s.sessao_id, "alsa:2,0")
    assert erro.value.status == 403


def test_sessao_valida_passa(cliente):
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    assert sessoes.validar(s.sessao_id, "csi:0").sessao_id == s.sessao_id


def test_sessao_id_nao_e_adivinhavel(cliente):
    """O id vai na URL do stream. Um sequencial deixaria adivinhar a sessão do
    vizinho — e a sessão É a autorização."""
    cid = criar_chamado(cliente)
    ids = {sessoes.abrir(cid, "csi:0").sessao_id for _ in range(5)}

    assert len(ids) == 5
    assert all(len(i) >= 20 for i in ids)


# ===========================================================================
# Expiração
# ===========================================================================


def test_duracao_e_dez_minutos():
    """Curto o bastante para que esquecer não signifique vigiar."""
    assert sessoes.DURACAO_SEG == 600


def test_expiracao_audita_o_fechamento(cliente):
    """Sem isto, a auditoria mostraria uma câmera **aberta para sempre**."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    s.expira_em = time.monotonic() - 1

    with pytest.raises(sessoes.SessaoRecusada):
        sessoes.validar(s.sessao_id, "csi:0")

    acoes = [x["acao"] for x in db.listar_auditoria_midia(cid)]
    assert acoes == ["abertura", "expiracao"]


def test_limpar_expiradas_audita_sem_ninguem_tentar(cliente):
    """A varredura existe para a sessão que **ninguém tentou usar** depois de
    expirar: sem ela, ficaria sem linha de fechamento."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    s.expira_em = time.monotonic() - 1

    assert sessoes.limpar_expiradas() == 1
    assert sessoes.limpar_expiradas() == 0  # idempotente
    assert [x["acao"] for x in db.listar_auditoria_midia(cid)] == [
        "abertura",
        "expiracao",
    ]


def test_ativas_ignora_expiradas(cliente):
    cid = criar_chamado(cliente)
    viva = sessoes.abrir(cid, "csi:0")
    morta = sessoes.abrir(cid, "alsa:2,0")
    morta.expira_em = time.monotonic() - 1

    assert [s.sessao_id for s in sessoes.ativas()] == [viva.sessao_id]


# ===========================================================================
# Fechamento e auditoria
# ===========================================================================


def test_delete_encerra_imediatamente(cliente):
    cid = criar_chamado(cliente)
    s = cliente.post(
        f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"}
    ).json()

    r = cliente.delete(f"/api/v1/chamados/{cid}/midia?sessao={s['sessao_id']}")

    assert r.status_code == 204
    with pytest.raises(sessoes.SessaoRecusada):
        sessoes.validar(s["sessao_id"], "csi:0")


def test_delete_sem_sessao_fecha_todas(cliente):
    """O painel chama isto ao fechar o detalhe, quando pode haver vídeo **e**
    áudio abertos juntos."""
    cid = criar_chamado(cliente)
    cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"})
    cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "alsa:2,0"})
    assert len(sessoes.ativas()) == 2

    assert cliente.delete(f"/api/v1/chamados/{cid}/midia").status_code == 204

    assert sessoes.ativas() == []


def test_fechar_duas_vezes_nao_quebra(cliente):
    """O painel manda o `DELETE` e o navegador reenvia no `beforeunload`."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    assert sessoes.fechar(s.sessao_id) is True
    assert sessoes.fechar(s.sessao_id) is False
    assert cliente.delete(f"/api/v1/chamados/{cid}/midia").status_code == 204


def test_abertura_e_fechamento_gravam_auditoria(cliente):
    """O critério: dispositivo, operador e duração."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0", operador="op4")
    time.sleep(0.01)
    sessoes.fechar(s.sessao_id, "teste")

    linhas = db.listar_auditoria_midia(cid)

    assert [x["acao"] for x in linhas] == ["abertura", "fechamento"]
    assert linhas[0]["dispositivo"] == "Câmera CSI (imx219)"
    assert linhas[0]["operador"] == "op4"
    assert linhas[0]["dispositivo_id"] == "csi:0"
    assert linhas[1]["duracao_seg"] is not None
    assert linhas[1]["motivo"] == "teste"


def test_auditoria_e_exposta_na_api(cliente):
    """Auditoria que exige acesso ao servidor não é auditoria — é arquivo."""
    cid = criar_chamado(cliente)
    s = cliente.post(
        f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"}
    ).json()
    cliente.delete(f"/api/v1/chamados/{cid}/midia?sessao={s['sessao_id']}")

    r = cliente.get(f"/api/v1/chamados/{cid}/midia/auditoria")

    assert r.status_code == 200
    assert [x["acao"] for x in r.json()] == ["abertura", "fechamento"]


def test_operador_registra_o_que_o_sistema_sabe(cliente):
    """O sistema tem **um** token compartilhado (MVP-040), não contas. O campo
    guarda o endereço de quem chamou e se havia token, sem fingir identidade —
    um `operador` com nome inventado seria pior que um IP honesto."""
    cid = criar_chamado(cliente)
    cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"})

    operador = db.listar_auditoria_midia(cid)[0]["operador"]

    assert operador
    assert "token" in operador


def test_fechar_do_chamado_encerra_tudo(cliente):
    """Chamado encerrado com a câmera aberta seria justamente a vigilância que
    o módulo existe para impedir."""
    cid = criar_chamado(cliente)
    sessoes.abrir(cid, "csi:0")
    sessoes.abrir(cid, "alsa:2,0")

    assert sessoes.fechar_do_chamado(cid, "chamado encerrado") == 2
    assert sessoes.ativas() == []
    assert len(db.listar_auditoria_midia(cid)) == 4


def test_sessoes_de_chamados_distintos_nao_se_misturam(cliente):
    a = criar_chamado(cliente)
    b = criar_chamado(cliente)
    sessoes.abrir(a, "csi:0")
    sessoes.abrir(b, "csi:0")

    assert sessoes.fechar_do_chamado(a, "x") == 1
    assert len(sessoes.ativas()) == 1


# ===========================================================================
# Integração: o sistema fecha a mídia sem ninguém pedir
# ===========================================================================


@pytest.mark.parametrize("status", ["encerrado", "cancelado"])
def test_encerrar_o_chamado_fecha_a_midia(cliente, status):
    """**Ninguém lembraria de fechar à mão.**

    Este é o caminho mais provável de a câmera ficar aberta na prática: o
    operador resolve o atendimento, muda o estado e fecha a aba. Sem este
    acoplamento, a sessão só cairia 10 minutos depois — e a auditoria mostraria
    a câmera aberta durante todo esse tempo, com razão.
    """
    cid = criar_chamado(cliente)
    cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"})
    assert len(sessoes.ativas()) == 1

    cliente.patch(f"/api/v1/chamados/{cid}", json={"status": status})

    assert sessoes.ativas() == []
    linhas = db.listar_auditoria_midia(cid)
    assert [x["acao"] for x in linhas] == ["abertura", "fechamento"]
    assert status in linhas[1]["motivo"]


def test_mudar_para_em_atendimento_nao_fecha(cliente):
    """Só os estados terminais fecham. `em_atendimento` é justamente quando a
    câmera mais serve."""
    cid = criar_chamado(cliente)
    cliente.post(f"/api/v1/chamados/{cid}/midia", json={"dispositivo_id": "csi:0"})

    cliente.patch(f"/api/v1/chamados/{cid}", json={"status": "em_atendimento"})

    assert len(sessoes.ativas()) == 1


async def test_worker_de_sla_varre_sessoes_expiradas(cliente, monkeypatch):
    """A varredura pega a sessão que **ninguém tentou usar** depois de expirar.

    Roda no laço do SLA e não num timer próprio: a cadência é a mesma, e um
    segundo worker seria mais um ponto de falha para fazer o mesmo trabalho.
    """
    import asyncio

    from app import sla

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    s.expira_em = time.monotonic() - 1

    monkeypatch.setattr(config, "SLA_CHECK_INTERVAL", 0.02)
    tarefa = asyncio.create_task(sla.loop())
    try:
        limite = asyncio.get_running_loop().time() + 2.0
        while asyncio.get_running_loop().time() < limite:
            if not sessoes.ativas() and len(db.listar_auditoria_midia(cid)) == 2:
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("o worker não varreu a sessão expirada")
    finally:
        tarefa.cancel()

    assert [x["acao"] for x in db.listar_auditoria_midia(cid)] == [
        "abertura",
        "expiracao",
    ]
