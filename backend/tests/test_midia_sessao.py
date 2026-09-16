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


# ===========================================================================
# Stream MJPEG (MVP-075)
# ===========================================================================
#
# **Os testes de entrega exercitam o gerador diretamente, não pelo
# `TestClient`.** Duas razões, e a segunda é a que importa:
#
# 1. O `TestClient` roda a aplicação **no mesmo processo**, e sair de um
#    `iter_bytes()` não sinaliza desconexão ao ASGI. Um stream é infinito por
#    natureza, então o teste **pendura** — foi o que aconteceu na primeira
#    versão deste arquivo, e levou três tentativas para eu perceber.
# 2. A propriedade que importa é o *ciclo de vida do gerador*: fechar a câmera
#    quando o cliente sai, quando a sessão expira e quando a captura falha.
#    Isso se verifica pedindo frames ao gerador e controlando o
#    `is_disconnected`; pelo cliente HTTP seria indireto e frágil.
#
# As recusas (403) continuam pelo `TestClient`: elas respondem **antes** de
# abrir qualquer stream, então não há o que pendurar.

JPEG = b"\xff\xd8" + b"x" * 40 + b"\xff\xd9"


class RequisicaoFalsa:
    """Requisição que se desconecta depois de N verificações."""

    def __init__(self, desconecta_em: int | None = None) -> None:
        self.desconecta_em = desconecta_em
        self.verificacoes = 0

    async def is_disconnected(self) -> bool:
        self.verificacoes += 1
        if self.desconecta_em is None:
            return False
        return self.verificacoes > self.desconecta_em


@pytest.fixture
def camera_falsa(monkeypatch):
    """Câmera de mentira que conta aberturas e fechamentos.

    O que se cobra não é a imagem — é o **ciclo de vida**. O bug encontrado na
    Pi real foi exatamente aqui.

    **A fixture guarda uma referência ao gerador de propósito.** Sem isso estes
    testes eram *vazios* quanto ao ponto principal: eu removi o `frames.close()`
    do `_multipart` e os 52 testes continuaram passando, porque o refcount do
    CPython finaliza o gerador ao fim da função e o `finally` roda sozinho. O
    teste media a limpeza do interpretador, não a do código — e a linha que ele
    devia proteger é justamente a que impede a câmera de travar.

    Descoberto ao aplicar a mesma mutação no caminho de áudio (MVP-076), que
    tinha o mesmo defeito herdado desta fixture.

    Segurar a referência também é fiel ao mundo real: uma exceção mantém o frame
    do gerador vivo pelo traceback, e é aí que a câmera fica presa.
    """
    from app.midia import camera as mod

    estado: dict = {"abertas": 0, "fechadas": 0, "geradores": []}

    def abrir(_id):
        estado["abertas"] += 1

        def frames():
            try:
                while True:
                    yield JPEG
            finally:
                estado["fechadas"] += 1

        gerador = frames()
        estado["geradores"].append(gerador)
        return gerador

    monkeypatch.setattr(mod, "abrir", abrir)
    return estado


# --- Recusas (pelo cliente HTTP) --------------------------------------------


def test_stream_sem_sessao_e_403(cliente):
    """O critério que a task manda testar explicitamente."""
    assert cliente.get("/api/v1/midia/camera/csi:0/stream").status_code == 403


def test_stream_com_sessao_inventada_e_403(cliente):
    r = cliente.get("/api/v1/midia/camera/csi:0/stream?sessao=nao-existe")
    assert r.status_code == 403


def test_stream_com_sessao_de_outro_dispositivo_e_403(cliente):
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")

    r = cliente.get(f"/api/v1/midia/camera/csi:0/stream?sessao={s.sessao_id}")

    assert r.status_code == 403


def test_stream_com_sessao_expirada_e_403(cliente):
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    s.expira_em = time.monotonic() - 1

    r = cliente.get(f"/api/v1/midia/camera/csi:0/stream?sessao={s.sessao_id}")

    assert r.status_code == 403


def test_403_nao_abre_a_camera(cliente, camera_falsa):
    """A recusa acontece **antes** da captura. Abrir e depois recusar ligaria a
    câmera para quem não tem autorização — mesmo por um instante, e a auditoria
    não registraria."""
    cliente.get("/api/v1/midia/camera/csi:0/stream?sessao=xyz")

    assert camera_falsa["abertas"] == 0


def test_cabecalhos_impedem_cache(cliente, camera_falsa):
    """Um proxy guardando frames de câmera seria inútil (a imagem muda) e
    indesejável (a imagem é de um chamado)."""
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    resposta = api_midia.stream_camera(RequisicaoFalsa(), "csi:0", s.sessao_id)

    assert "no-store" in resposta.headers["cache-control"]
    assert resposta.headers["x-accel-buffering"] == "no"
    assert "multipart/x-mixed-replace" in resposta.media_type
    assert "boundary=frame" in resposta.media_type


# --- Entrega e ciclo de vida (pelo gerador) ---------------------------------


async def coletar(gerador, n: int) -> bytes:
    """Consome até `n` partes e fecha, como o navegador faria."""
    saida = b""
    try:
        async for pedaco in gerador:
            saida += pedaco
            if saida.count(b"--frame") >= n:
                break
    finally:
        await gerador.aclose()
    return saida


async def test_stream_entrega_partes_multipart(cliente, camera_falsa):
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    corpo = await coletar(api_midia._multipart(RequisicaoFalsa(), "csi:0", s), 2)

    assert corpo.count(b"--frame") >= 2
    assert corpo.count(b"\xff\xd8") >= 2
    assert b"Content-Type: image/jpeg" in corpo
    assert f"Content-Length: {len(JPEG)}".encode() in corpo


async def test_fechar_o_gerador_libera_a_camera(cliente, camera_falsa):
    """**O bug que a Pi real revelou.**

    Com gerador síncrono, o Starlette roda o stream num threadpool e o
    desconecte deixa o gerador bloqueado dentro da captura: o `finally` não
    executa e a câmera fica presa até o processo morrer. Verificado na Pi:
    depois de um `curl` interrompido, abrir a câmera de outro processo falhava
    com `RuntimeError: Camera __init__ sequence did not complete`.

    Com gerador assíncrono o Starlette chama `aclose()`, e é isso que este
    teste exerce.
    """
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    await coletar(api_midia._multipart(RequisicaoFalsa(), "csi:0", s), 1)

    assert camera_falsa["abertas"] == 1
    assert camera_falsa["fechadas"] == 1, "a câmera ficou presa"


async def test_desconexao_do_cliente_encerra_o_stream(cliente, camera_falsa):
    """O caminho **normal** de encerramento de um MJPEG: o operador fecha a aba.

    Sem checar `is_disconnected`, o stream só pararia na próxima falha de
    escrita — um frame depois, e com a câmera ainda rodando.
    """
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    requisicao = RequisicaoFalsa(desconecta_em=2)

    partes = [p async for p in api_midia._multipart(requisicao, "csi:0", s)]

    assert len(partes) == 2, "o stream não parou no desconecte"
    assert camera_falsa["fechadas"] == 1


async def test_expiracao_encerra_o_stream_em_curso(cliente, camera_falsa):
    """A sessão é checada **a cada frame**, não só na abertura.

    Sem isso, um stream aberto no minuto 9 continuaria entregando vídeo por
    horas: o prazo de 10 minutos existe para limitar a duração, e checar uma
    vez só o tornaria decorativo.
    """
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")
    gerador = api_midia._multipart(RequisicaoFalsa(), "csi:0", s)

    primeira = await anext(gerador)
    assert primeira.count(b"--frame") == 1

    s.expira_em = time.monotonic() - 1

    with pytest.raises(StopAsyncIteration):
        await anext(gerador)
    assert camera_falsa["fechadas"] == 1


async def test_falha_da_camera_no_meio_libera(cliente, monkeypatch):
    """Câmera desconectada durante o stream. Encerrar é o certo: o `<img>` do
    painel mostra a última imagem e o operador percebe que congelou."""
    from app.api import midia as api_midia
    from app.midia import camera as mod

    estado = {"fechadas": 0}

    def abrir(_id):
        try:
            yield JPEG
            raise mod.CameraIndisponivel("cabo arrancado")
        finally:
            estado["fechadas"] += 1

    monkeypatch.setattr(mod, "abrir", abrir)
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    partes = [p async for p in api_midia._multipart(RequisicaoFalsa(), "csi:0", s)]

    assert len(partes) == 1
    assert estado["fechadas"] == 1


# ===========================================================================
# Stream de áudio (MVP-076)
# ===========================================================================
#
# Mesma divisão de método do vídeo: as **recusas** vão pelo `TestClient`,
# porque respondem antes de abrir captura nenhuma; a **entrega** exercita o
# gerador direto, porque um stream é infinito e o `TestClient` penduraria.
#
# A garantia central aqui não é o formato do WAV — é que **a sessão da câmera
# não autoriza o microfone**. Áudio é mais invasivo que imagem: sem essa
# checagem, um único pedido de vídeo daria de graça o som do local.

WAV_BLOCO = b"\x00\x00" * 100


@pytest.fixture
def microfone_falso(monkeypatch):
    """Microfone de mentira que conta aberturas e fechamentos.

    **A fixture guarda uma referência ao gerador, e isso é o ponto.** A primeira
    versão não guardava, e por isso o teste de liberação era *vazio*: removi o
    `blocos.close()` do `_wav` e os 76 testes continuaram passando.

    O motivo é o refcount do CPython — quando `_wav` termina, a variável local
    sai de escopo, o gerador é finalizado e o `finally` roda sozinho. O teste
    media a limpeza do interpretador, não a do código.

    Segurando a referência, só um `close()` explícito executa o `finally`. E não
    é cenário artificial: é o que acontece de verdade quando uma exceção
    mantém o frame do gerador vivo pelo traceback — que é justamente o caminho
    em que o `arecord` ficaria órfão e prenderia o dispositivo ALSA.
    """
    from app.midia import microfone as mod

    estado: dict = {"abertas": 0, "fechadas": 0, "geradores": []}

    def abrir(_id, espera=5.0):
        estado["abertas"] += 1

        def blocos():
            try:
                while True:
                    yield WAV_BLOCO
            finally:
                estado["fechadas"] += 1

        gerador = blocos()
        estado["geradores"].append(gerador)
        return gerador

    monkeypatch.setattr(mod, "abrir", abrir)
    return estado


# --- Recusas ----------------------------------------------------------------


def test_audio_sem_sessao_e_403(cliente):
    """O critério que a task manda testar explicitamente."""
    assert cliente.get("/api/v1/midia/microfone/alsa:2,0/stream").status_code == 403


def test_audio_com_sessao_inventada_e_403(cliente):
    r = cliente.get("/api/v1/midia/microfone/alsa:2,0/stream?sessao=nao-existe")
    assert r.status_code == 403


def test_sessao_de_camera_nao_autoriza_o_microfone(cliente):
    """**A garantia mais importante do áudio.**

    Um pedido de vídeo não pode virar acesso ao som do local. Sem esta
    checagem, quem obtivesse uma sessão de câmera — o caminho mais banal, e o
    que o painel usa primeiro — passaria a ouvir o ambiente também.
    """
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    r = cliente.get(f"/api/v1/midia/microfone/alsa:2,0/stream?sessao={s.sessao_id}")

    assert r.status_code == 403


def test_audio_com_sessao_expirada_e_403(cliente):
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")
    s.expira_em = time.monotonic() - 1

    r = cliente.get(f"/api/v1/midia/microfone/alsa:2,0/stream?sessao={s.sessao_id}")

    assert r.status_code == 403


def test_403_nao_abre_o_microfone(cliente, microfone_falso):
    """A recusa acontece **antes** da captura.

    Abrir e depois recusar ligaria o microfone para quem não tem autorização —
    e a auditoria não registraria essa escuta.
    """
    cliente.get("/api/v1/midia/microfone/alsa:2,0/stream?sessao=xyz")

    assert microfone_falso["abertas"] == 0


def test_clipe_sem_sessao_e_403(cliente):
    """O fallback tem que ter a mesma porta que o stream.

    Um clipe liberado seria a brecha óbvia: gravaria o local em arquivo,
    justamente o caminho mais fácil de guardar e repassar.
    """
    assert cliente.get("/api/v1/midia/microfone/alsa:2,0/clipe").status_code == 403


def test_clipe_com_sessao_de_camera_e_403(cliente):
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "csi:0")

    r = cliente.get(f"/api/v1/midia/microfone/alsa:2,0/clipe?sessao={s.sessao_id}")

    assert r.status_code == 403


def test_sessao_de_microfone_nao_autoriza_a_camera(cliente):
    """O simétrico, e não é redundante: o `validar` compara dispositivos, e uma
    implementação que só recusasse "microfone com sessão de câmera" passaria
    pelo teste de cima e deixaria a câmera aberta."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")

    r = cliente.get(f"/api/v1/midia/camera/csi:0/stream?sessao={s.sessao_id}")

    assert r.status_code == 403


# --- Entrega ----------------------------------------------------------------


async def test_wav_comeca_pelo_cabecalho(cliente, microfone_falso):
    """O player precisa da taxa e do número de canais **antes** da primeira
    amostra. Sem o cabeçalho na frente, o navegador não toca nada."""
    from app.api import midia as api_midia
    from app.midia import microfone as mod

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")
    gerador = api_midia._wav(RequisicaoFalsa(desconecta_em=2), "alsa:2,0", s)

    primeiro = await anext(gerador)

    assert primeiro == mod.cabecalho_wav()
    assert primeiro[:4] == b"RIFF"
    assert await anext(gerador) == WAV_BLOCO
    await gerador.aclose()


async def test_desconexao_libera_o_microfone(cliente, microfone_falso):
    """**O que impede o `arecord` de ficar órfão.**

    Um `arecord` que sobrevive ao fechamento da aba mantém o dispositivo ALSA
    preso, e a próxima sessão falha com "device busy" até alguém reiniciar o
    serviço. É o mesmo bug que a câmera teve na Pi real (MVP-075).
    """
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")
    req = RequisicaoFalsa(desconecta_em=2)

    blocos = [b async for b in api_midia._wav(req, "alsa:2,0", s)]

    assert microfone_falso["abertas"] == 1
    assert microfone_falso["fechadas"] == 1, "o arecord ficaria órfão"
    assert len(blocos) >= 2  # cabeçalho + ao menos um bloco


async def test_expiracao_encerra_o_audio(cliente, microfone_falso):
    """A sessão é checada **a cada bloco**, não só na abertura.

    Checar uma vez só tornaria o prazo de 10 min decorativo: um stream aberto
    no minuto 9 seguiria entregando som por horas.
    """
    from app.api import midia as api_midia

    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")
    gerador = api_midia._wav(RequisicaoFalsa(), "alsa:2,0", s)

    await anext(gerador)  # cabeçalho
    await anext(gerador)  # um bloco

    s.expira_em = time.monotonic() - 1

    with pytest.raises(StopAsyncIteration):
        await anext(gerador)
    assert microfone_falso["fechadas"] == 1


async def test_falha_do_microfone_no_meio_libera(cliente, monkeypatch):
    """Microfone arrancado durante a escuta.

    Encerrar é o certo. **Silêncio falso é pior que erro visível** num totem de
    emergência: o operador acharia o local calmo.
    """
    from app.api import midia as api_midia
    from app.midia import microfone as mod

    estado = {"fechadas": 0}

    def abrir(_id, espera=5.0):
        try:
            yield WAV_BLOCO
            raise mod.MicrofoneIndisponivel("cabo arrancado")
        finally:
            estado["fechadas"] += 1

    monkeypatch.setattr(mod, "abrir", abrir)
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")

    blocos = [b async for b in api_midia._wav(RequisicaoFalsa(), "alsa:2,0", s)]

    assert len(blocos) == 2  # cabeçalho + o único bloco entregue
    assert estado["fechadas"] == 1


def test_audio_tambem_grava_auditoria(cliente):
    """A auditoria não distingue câmera de microfone — e não deveria.

    Uma escuta sem rastro é exatamente o que a MVP-077 existe para impedir.
    """
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")
    sessoes.fechar(s.sessao_id)

    linhas = db.listar_auditoria_midia(cid)

    assert len(linhas) == 2
    assert {linha["acao"] for linha in linhas} == {"abertura", "fechamento"}
    assert all(linha["dispositivo_id"] == "alsa:2,0" for linha in linhas)


def test_url_do_stream_de_microfone_aponta_para_o_recurso_certo(cliente):
    """O painel não monta a URL: ela vem pronta do backend, e o tipo do
    dispositivo decide o recurso."""
    cid = criar_chamado(cliente)
    s = sessoes.abrir(cid, "alsa:2,0")

    url = sessoes.url_do_stream(s)

    assert url.startswith("/api/v1/midia/microfone/alsa:2,0/stream?sessao=")
    assert "camera" not in url
