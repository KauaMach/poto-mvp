"""Videochamada da central para o totem — MEL-004.

O sentido que faltava: a central já vê e ouve a pessoa (MVP-073/078); aqui a
imagem do operador vai para a tela de quem apertou o pânico, para ela **ver
alguém do outro lado** enquanto espera.

O que estes testes cobram, em ordem de importância:

1. **A sessão manda.** Sem sessão de chamada não há publicação nem stream — e
   uma sessão de *câmera* não serve, porque ela autoriza o contrário (a central
   ver o local, não aparecer nele).
2. **A auditoria é a mesma.** Uma câmera de operador aparecendo na tela de
   alguém merece o mesmo rastro que a câmera da Pi: par abertura/fechamento,
   com duração.
3. **O repasse não acumula.** Numa chamada, quadro velho não vale nada.

O gerador do multipart é exercitado direto, e não pelo `TestClient`, pela mesma
razão do stream da câmera: o cliente roda a aplicação no mesmo processo e um
stream é infinito por natureza — sair de um `iter_bytes()` não sinaliza
desconexão ao ASGI, e o teste pendura.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import criar_app
from app.midia import sessao as sessoes
from app.midia.chamada import TAMANHO_MAXIMO, SemQuadro, repasse

JPEG = b"\xff\xd8" + b"x" * 60 + b"\xff\xd9"


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")
    monkeypatch.setattr(config, "_CONTATOS", {c: "5586999990001" for c in config.CANAIS})
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    monkeypatch.setattr(sessoes, "_sessoes", {})
    # O repasse é global como o hub: sem limpar, um teste herda o quadro do
    # anterior e "passa" mostrando imagem que não é dele.
    monkeypatch.setattr(repasse, "_atual", {})
    monkeypatch.setattr(repasse, "_novidade", {})
    db.init_db()


@pytest.fixture
def cliente():
    with TestClient(criar_app()) as c:
        yield c


def em_panico(cliente) -> str:
    return cliente.post(
        "/api/v1/panico", json={"evento_id": str(uuid4()), "totem_id": "TOTEM-CCS-01"}
    ).json()["chamado_id"]


# ---------------------------------------------------------------------------
# Abertura
# ---------------------------------------------------------------------------


def test_abrir_devolve_as_duas_urls(cliente):
    """Dois papéis, duas URLs: a central envia, o totem consome."""
    cid = em_panico(cliente)

    corpo = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()

    assert corpo["envio_url"].endswith("/quadro")
    assert corpo["stream_url"].endswith("/stream")
    assert corpo["sessao_id"] in corpo["envio_url"]
    assert corpo["expira_em"] == sessoes.DURACAO_SEG


def test_abrir_em_chamado_encerrado_e_409(cliente):
    """Mesma recusa da câmera. Um atendimento concluído não justifica abrir
    vídeo na tela de ninguém."""
    cid = em_panico(cliente)
    cliente.patch(f"/api/v1/chamados/{cid}", json={"status": "encerrado"})

    r = cliente.post(f"/api/v1/chamados/{cid}/chamada")

    assert r.status_code == 409


def test_abrir_em_chamado_inexistente_e_404(cliente):
    r = cliente.post("/api/v1/chamados/CALL-9999-999999/chamada")
    assert r.status_code == 404


def test_abertura_e_auditada(cliente):
    """Uma câmera de operador aparecendo na tela de alguém merece o mesmo
    rastro que a câmera da Pi."""
    cid = em_panico(cliente)
    cliente.post(f"/api/v1/chamados/{cid}/chamada")

    (linha,) = db.listar_auditoria_midia(cid)

    assert linha["acao"] == "abertura"
    assert linha["dispositivo_id"] == sessoes.DISPOSITIVO_CENTRAL
    assert linha["dispositivo"] == "Câmera do operador (central)"


def test_chamada_expira_junto_com_as_outras_sessoes(cliente):
    """A sessão entra no mesmo `_sessoes`, então herda a varredura da MVP-077 —
    e é isso que impede uma chamada esquecida de viver para sempre."""
    import time

    cid = em_panico(cliente)
    corpo = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()
    sessoes._sessoes[corpo["sessao_id"]].expira_em = time.monotonic() - 1

    assert sessoes.limpar_expiradas() == 1
    acoes = [linha["acao"] for linha in db.listar_auditoria_midia(cid)]
    assert acoes == ["abertura", "expiracao"]


def test_encerrar_o_chamado_encerra_a_chamada(cliente):
    """O caminho mais provável na prática: o operador resolve o atendimento e
    fecha a aba, sem encerrar a chamada explicitamente."""
    cid = em_panico(cliente)
    cliente.post(f"/api/v1/chamados/{cid}/chamada")

    cliente.patch(f"/api/v1/chamados/{cid}", json={"status": "encerrado"})

    assert sessoes.ativas() == []
    acoes = [linha["acao"] for linha in db.listar_auditoria_midia(cid)]
    assert acoes == ["abertura", "fechamento"]


# ---------------------------------------------------------------------------
# A sessão manda — sem ela não há publicação nem stream
# ---------------------------------------------------------------------------


def test_publicar_sem_sessao_e_403(cliente):
    r = cliente.post("/api/v1/midia/chamada/inventada/quadro", content=JPEG)
    assert r.status_code == 403


def test_stream_sem_sessao_e_403(cliente):
    assert cliente.get("/api/v1/midia/chamada/inventada/stream").status_code == 403


def test_sessao_de_camera_nao_publica_quadro(cliente):
    """**A garantia que separa os dois sentidos.**

    A central obtém sessão de câmera para *ver* o local. Se ela servisse para
    publicar, um pedido de ver viraria um poder de aparecer — e a auditoria
    registraria "abriu a câmera" onde na verdade apareceu na tela de alguém.
    """
    import time

    cid = em_panico(cliente)
    # Sessão de câmera criada à mão: `abrir()` exigiria um dispositivo
    # detectado, e não há hardware na suíte. O que importa é o `tipo`.
    s = sessoes.Sessao(
        sessao_id="sessao-de-camera",
        chamado_id=cid,
        dispositivo_id="csi:0",
        tipo="camera",
        operador=None,
        aberta_em=time.monotonic(),
        expira_em=time.monotonic() + 600,
    )
    sessoes._sessoes[s.sessao_id] = s

    r = cliente.post(f"/api/v1/midia/chamada/{s.sessao_id}/quadro", content=JPEG)

    assert r.status_code == 403


def test_sessao_expirada_nao_publica(cliente):
    import time

    cid = em_panico(cliente)
    corpo = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()
    sessoes._sessoes[corpo["sessao_id"]].expira_em = time.monotonic() - 1

    r = cliente.post(
        f"/api/v1/midia/chamada/{corpo['sessao_id']}/quadro", content=JPEG
    )

    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Publicação
# ---------------------------------------------------------------------------


def test_publicar_guarda_o_quadro(cliente):
    cid = em_panico(cliente)
    corpo = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()

    r = cliente.post(f"/api/v1/midia/chamada/{corpo['sessao_id']}/quadro", content=JPEG)

    assert r.status_code == 204
    assert repasse.primeiro(corpo["sessao_id"]) == JPEG


def test_quadro_vazio_e_422(cliente):
    cid = em_panico(cliente)
    corpo = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()

    r = cliente.post(f"/api/v1/midia/chamada/{corpo['sessao_id']}/quadro", content=b"")

    assert r.status_code == 422


def test_quadro_grande_demais_e_413(cliente):
    """O endpoint recebe de fora. Sem teto, um bug de laço na central enche a
    memória da Pi durante uma emergência."""
    cid = em_panico(cliente)
    corpo = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()

    r = cliente.post(
        f"/api/v1/midia/chamada/{corpo['sessao_id']}/quadro",
        content=b"x" * (TAMANHO_MAXIMO + 1),
    )

    assert r.status_code == 413
    assert repasse.primeiro(corpo["sessao_id"]) is None, "guardou apesar de recusar"


def test_quadro_grande_sem_content_length_e_413(cliente):
    """O caso que o `content-length` não cobre, e por que há **duas** checagens.

    A primeira olha o cabeçalho declarado e recusa antes de ler — é ela que
    protege a memória. Mas `content-length` é opcional: com `Transfer-Encoding:
    chunked` ele não vem, e aí só a medição do corpo já lido pega.

    Descoberto por mutação: removendo a segunda checagem, os 22 testes
    continuavam passando, porque todos mandavam o cabeçalho.
    """
    cid = em_panico(cliente)
    sid = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()["sessao_id"]

    def corpo_em_pedacos():
        # Gerador faz o httpx enviar com `chunked`, sem `content-length`.
        for _ in range(3):
            yield b"x" * (TAMANHO_MAXIMO // 2)

    r = cliente.post(
        f"/api/v1/midia/chamada/{sid}/quadro", content=corpo_em_pedacos()
    )

    assert r.status_code == 413
    assert repasse.primeiro(sid) is None


async def test_cabecalho_grande_e_recusado_SEM_ler_o_corpo(cliente):
    """Por que a checagem do `content-length` vem **antes** do `body()`.

    As duas checagens devolvem 413, então o status não distingue uma da outra —
    e por isso removendo a primeira todos os testes continuavam passando. A
    diferença é de **memória**: recusar depois de `await request.body()` já
    teria carregado o corpo inteiro na Pi, que é exatamente o que o limite
    existe para evitar.

    O que se observa aqui é o `body()` **não ser chamado**.
    """
    from fastapi import HTTPException

    from app.api import midia as api

    cid = em_panico(cliente)
    sid = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()["sessao_id"]

    class RequisicaoQueAcusa:
        headers = {"content-length": str(TAMANHO_MAXIMO + 1)}

        async def body(self):
            raise AssertionError("leu o corpo antes de recusar pelo cabeçalho")

    with pytest.raises(HTTPException) as erro:
        await api.publicar_quadro(sid, RequisicaoQueAcusa())

    assert erro.value.status_code == 413


def test_quadro_novo_substitui_o_antigo(cliente):
    """Um quadro por sessão, o mais recente. Acumular introduziria atraso
    crescente — e atraso é o que arruína a sensação de conversa."""
    cid = em_panico(cliente)
    sid = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()["sessao_id"]
    novo = b"\xff\xd8" + b"outro" + b"\xff\xd9"

    cliente.post(f"/api/v1/midia/chamada/{sid}/quadro", content=JPEG)
    cliente.post(f"/api/v1/midia/chamada/{sid}/quadro", content=novo)

    assert repasse.primeiro(sid) == novo
    assert repasse.sessoes() == 1


# ---------------------------------------------------------------------------
# O repasse em si
# ---------------------------------------------------------------------------


async def test_aguardar_acorda_com_a_publicacao():
    """Quem espera é **acordado**, não consulta em laço: consultar somaria
    latência e gastaria CPU nos intervalos em que nada chega."""
    import asyncio

    async def publicar_depois():
        await asyncio.sleep(0.01)
        repasse.publicar("s1", JPEG)

    tarefa = asyncio.create_task(publicar_depois())
    quadro = await repasse.aguardar("s1", prazo=2.0)
    await tarefa

    assert quadro == JPEG


async def test_aguardar_espera_o_PROXIMO_e_nao_devolve_o_atual():
    """Um stream que reenviasse o mesmo quadro em laço gastaria banda mostrando
    imagem parada."""
    repasse.publicar("s1", JPEG)

    with pytest.raises(SemQuadro):
        await repasse.aguardar("s1", prazo=0.05)


async def test_aguardar_sem_publicacao_levanta():
    with pytest.raises(SemQuadro):
        await repasse.aguardar("nunca-publicada", prazo=0.05)


async def test_dois_assinantes_recebem_o_mesmo_quadro():
    """O `Event` é substituído a cada publicação justamente para acordar todos.
    Reusar um só, com `clear()`, deixaria um assinante lento perder o aviso."""
    import asyncio

    a = asyncio.create_task(repasse.aguardar("s1", prazo=2.0))
    b = asyncio.create_task(repasse.aguardar("s1", prazo=2.0))
    await asyncio.sleep(0.01)
    repasse.publicar("s1", JPEG)

    assert await a == JPEG
    assert await b == JPEG


async def test_encerrar_acorda_quem_espera():
    """Sem isto, o gerador do stream ficaria pendurado até o prazo depois de a
    chamada ser encerrada."""
    import asyncio

    tarefa = asyncio.create_task(repasse.aguardar("s1", prazo=5.0))
    await asyncio.sleep(0.01)
    repasse.encerrar("s1")

    with pytest.raises(SemQuadro):
        await tarefa


# ---------------------------------------------------------------------------
# O stream (gerador exercitado direto)
# ---------------------------------------------------------------------------


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


async def test_stream_comeca_pelo_quadro_atual(cliente):
    """Quem assina depois de a central já estar enviando não deve encarar
    segundos de tela vazia esperando o próximo quadro."""
    from app.api import midia as api

    cid = em_panico(cliente)
    sid = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()["sessao_id"]
    s = sessoes._sessoes[sid]
    repasse.publicar(sid, JPEG)

    gerador = api._multipart_chamada(RequisicaoFalsa(desconecta_em=0), s)
    primeira = await anext(gerador)
    await gerador.aclose()

    assert primeira.count(b"--frame") == 1
    assert JPEG in primeira


async def test_stream_para_quando_a_central_para_de_enviar(cliente):
    """Encerrar é melhor que congelar: o `<img>` do totem mantém a última
    imagem, e insistir manteria a conexão aberta contra alguém que já foi."""
    from app.api import midia as api

    cid = em_panico(cliente)
    sid = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()["sessao_id"]
    s = sessoes._sessoes[sid]

    import app.midia.chamada as mod

    # Prazo curto para o teste não esperar os 5 s do `ESPERA_QUADRO`.
    original = mod.repasse.aguardar

    async def rapido(sessao_id, prazo=0.05):
        return await original(sessao_id, prazo=0.05)

    mod.repasse.aguardar = rapido
    try:
        partes = [p async for p in api._multipart_chamada(RequisicaoFalsa(), s)]
    finally:
        mod.repasse.aguardar = original

    assert partes == []


async def test_stream_para_na_expiracao(cliente):
    import time

    from app.api import midia as api

    cid = em_panico(cliente)
    sid = cliente.post(f"/api/v1/chamados/{cid}/chamada").json()["sessao_id"]
    s = sessoes._sessoes[sid]
    s.expira_em = time.monotonic() - 1

    partes = [p async for p in api._multipart_chamada(RequisicaoFalsa(), s)]

    assert partes == []
