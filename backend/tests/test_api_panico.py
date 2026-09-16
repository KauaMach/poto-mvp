"""`POST /panico` — o alerta imediato.

Três coisas separam o pânico do acionamento por trilha, e cada uma tem razão
própria:

1. **Não passa por triagem de texto.** Não há texto, e não haveria tempo de
   escrever. É crítico por definição, não por inferência.
2. **Aciona os canais internos em paralelo.** Sequencial, o segundo esperaria o
   primeiro; num pânico os dois precisam saber junto.
3. **Nasce em `alerta_ativo`**, o único estado que não fecha sozinho — nem pelo
   sucesso da notificação, nem pela falha dela. Só ação humana na central o tira
   de lá.

E há uma restrição que vem de o endpoint ser **aberto**: nada que saia daqui
pode revelar contato institucional. Duas seções no fim cuidam disso.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import canais, config, db
from app.hub import hub as hub_global
from app.main import criar_app
from app.models import Gravidade, Modo, StatusChamado, TipoOcorrencia

ROTA = "/api/v1/panico"

# Números de mentira, mas com a forma de um contato real: é o que um webhook
# ecoaria de volta numa mensagem de erro.
CONTATO_CSV = "5586999990001"
CONTATO_LILAS = "5586999990002"


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(
        config, "_CONTATOS", {"csv": CONTATO_CSV, "sala_lilas": CONTATO_LILAS}
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")


@pytest.fixture
def cliente(ambiente):
    with TestClient(criar_app()) as c:
        yield c


@pytest.fixture(autouse=True)
def hub_limpo():
    yield
    hub_global._clientes.clear()


class PainelFalso:
    def __init__(self):
        self.eventos: list[tuple[str, dict]] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, mensagem: dict) -> None:
        self.eventos.append((mensagem["evento"], mensagem["dados"]))

    def nomes(self) -> list[str]:
        return [nome for nome, _ in self.eventos]


@pytest.fixture
async def painel():
    p = PainelFalso()
    await hub_global.connect(p)
    return p


def corpo(**extra) -> dict:
    return {"evento_id": str(uuid4()), "totem_id": "TOTEM-CCS-01", **extra}


def acionar(cliente, **extra):
    return cliente.post(ROTA, json=corpo(**extra))


# ===========================================================================
# Crítico por definição
# ===========================================================================


def test_panico_e_risco_imediato(cliente):
    r = acionar(cliente)
    assert r.status_code == 201
    assert r.json()["gravidade"] == Gravidade.risco_imediato


def test_panico_e_registrado_como_seguranca(cliente):
    r = acionar(cliente)
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["tipo_ocorrencia"] == TipoOcorrencia.seguranca


def test_origem_e_panico(cliente):
    r = acionar(cliente)
    chamado = db.obter_chamado(r.json()["chamado_id"])
    assert chamado["origem_acionamento"] == "panico"


def test_panico_nao_guarda_relato(cliente):
    """Não há campo de texto no contrato e não haveria tempo de escrever."""
    r = acionar(cliente)
    assert db.obter_chamado(r.json()["chamado_id"])["texto_livre"] is None


def test_texto_enviado_por_engano_e_descartado(cliente):
    """`PanicoIn` não tem `texto_livre`. Um cliente que mandar o campo não
    recebe erro — o pânico não pode falhar por payload extra — mas o valor não
    é guardado nem triado."""
    r = cliente.post(ROTA, json=corpo(texto_livre="isto não deveria ser triado"))

    assert r.status_code == 201
    assert db.obter_chamado(r.json()["chamado_id"])["texto_livre"] is None


def test_panico_gera_protocolo(cliente):
    """O protocolo é o que a tela mostra grande, e é por ele que a pessoa e a
    central se encontram."""
    assert acionar(cliente).json()["chamado_id"].startswith("CALL-")


# ===========================================================================
# `alerta_ativo` é persistente
# ===========================================================================


def test_status_nasce_alerta_ativo(cliente):
    r = acionar(cliente)
    assert r.json()["status"] == StatusChamado.alerta_ativo
    assert db.obter_chamado(r.json()["chamado_id"])["status"] == (
        StatusChamado.alerta_ativo
    )


def test_notificacao_bem_sucedida_nao_fecha_o_alerta(cliente):
    """A diferença central em relação a `/eventos`, onde o sucesso leva a
    `notificado`. Um pânico não é resolvido por alguém ter sido avisado: só por
    ação humana na central."""
    r = acionar(cliente)

    notificacoes = db.listar_notificacoes(r.json()["chamado_id"])
    assert all(n["sucesso"] for n in notificacoes)
    assert db.obter_chamado(r.json()["chamado_id"])["status"] == (
        StatusChamado.alerta_ativo
    )


def test_falha_de_notificacao_nao_rebaixa_o_alerta(cliente, monkeypatch):
    """Nem a falha o tira de lá. Um pânico cujo aviso não saiu é **mais** grave,
    não menos — e é exatamente quando os botões de escalonamento importam."""

    async def sempre_falha(*args, **kwargs):
        return False, "webhook fora do ar"

    monkeypatch.setattr(canais, "notificar", sempre_falha)

    r = acionar(cliente)

    assert r.json()["status"] == StatusChamado.alerta_ativo
    assert db.obter_chamado(r.json()["chamado_id"])["status"] == (
        StatusChamado.alerta_ativo
    )


def test_estado_inicial_registrado_no_log(cliente):
    r = acionar(cliente)
    estados = db.listar_estados(r.json()["chamado_id"])
    assert estados[0]["para"] == StatusChamado.alerta_ativo


# ===========================================================================
# Broadcast paralelo
# ===========================================================================


def test_os_dois_canais_internos_sao_acionados(cliente):
    r = acionar(cliente)

    canais_acionados = [
        n["canal"] for n in db.listar_notificacoes(r.json()["chamado_id"])
    ]
    assert sorted(canais_acionados) == sorted(config.CANAIS_INTERNOS)


def test_resultados_trazem_os_dois_canais(cliente):
    resultados = acionar(cliente).json()["resultados"]

    assert [r["canal"] for r in resultados] == list(config.CANAIS_INTERNOS)
    assert all(r["sucesso"] for r in resultados)


def test_resultados_trazem_o_nome_legivel(cliente):
    """A tela mostra "CSV / PREUNI", não "csv"."""
    resultados = acionar(cliente).json()["resultados"]
    assert {r["nome"] for r in resultados} == {"CSV / PREUNI", "Sala Lilás"}


async def test_canais_sao_acionados_em_paralelo(cliente, monkeypatch):
    """Prova por sincronização, não por cronômetro.

    A barreira só libera quando **os dois** acionamentos chegam nela. Numa
    implementação sequencial o primeiro esperaria para sempre — o `wait_for`
    converte isso em falha em vez de travar a suíte.
    """
    barreira = asyncio.Barrier(2)

    async def notificar_sincronizado(chamado, canal, **kwargs):
        await asyncio.wait_for(barreira.wait(), timeout=2.0)
        return True, "ok"

    monkeypatch.setattr(canais, "notificar", notificar_sincronizado)

    resultados = acionar(cliente).json()["resultados"]

    assert all(r["sucesso"] for r in resultados), (
        "os dois canais não chegaram juntos na barreira — acionamento sequencial"
    )


def test_falha_de_um_canal_nao_impede_o_outro(cliente, monkeypatch):
    """Num pânico, ficar sem o CSV porque a Sala Lilás está mal configurada
    seria o pior resultado possível."""
    monkeypatch.setattr(config, "_CONTATOS", {"csv": CONTATO_CSV})

    resultados = acionar(cliente).json()["resultados"]

    por_canal = {r["canal"]: r["sucesso"] for r in resultados}
    assert por_canal == {"csv": True, "sala_lilas": False}


def test_provider_que_estoura_nao_derruba_o_panico(cliente, monkeypatch):
    async def estoura(chamado, canal, **kwargs):
        raise RuntimeError("bug no caminho da notificação")

    monkeypatch.setattr(canais, "notificar", estoura)

    r = acionar(cliente)

    assert r.status_code == 201
    assert all(not x["sucesso"] for x in r.json()["resultados"])
    assert db.obter_chamado(r.json()["chamado_id"])["status"] == (
        StatusChamado.alerta_ativo
    )


def test_todos_os_canais_falharem_nao_apaga_o_chamado(cliente, monkeypatch):
    monkeypatch.setattr(config, "_CONTATOS", {})

    r = acionar(cliente)

    assert r.status_code == 201
    assert db.obter_chamado(r.json()["chamado_id"]) is not None
    assert len(db.listar_notificacoes(r.json()["chamado_id"])) == 2


async def test_central_e_avisada(cliente, painel):
    r = acionar(cliente)
    assert painel.nomes() == ["novo_chamado"]
    assert painel.eventos[0][1]["chamado_id"] == r.json()["chamado_id"]


async def test_painel_morto_nao_impede_o_panico(cliente):
    class PainelQuebrado(PainelFalso):
        async def send_json(self, mensagem):
            raise ConnectionResetError("painel morto")

    await hub_global.connect(PainelQuebrado())

    assert acionar(cliente).status_code == 201


# ===========================================================================
# Escalonamento manual
# ===========================================================================


def test_escalonamento_oferece_as_quatro_autoridades(cliente):
    opcoes = acionar(cliente).json()["escalonamento_disponivel"]
    assert [o["canal"] for o in opcoes] == config.CANAIS_ESTADO


def test_escalonamento_tem_nome_legivel(cliente):
    opcoes = acionar(cliente).json()["escalonamento_disponivel"]
    assert {o["nome"] for o in opcoes} == {
        "Polícia Militar",
        "SAMU",
        "Corpo de Bombeiros",
        "Central de Atendimento à Mulher",
    }


def test_escalonamento_nao_e_acionado_automaticamente(cliente):
    """O sistema **oferece** as autoridades do estado; não disca para elas. As
    notificações do pânico são só as dos canais internos — robo-discar 190 ou
    192 por acionamento automático seria irresponsável."""
    r = acionar(cliente)

    canais_acionados = {
        n["canal"] for n in db.listar_notificacoes(r.json()["chamado_id"])
    }
    assert canais_acionados.isdisjoint(config.CANAIS_ESTADO)


# ===========================================================================
# O endpoint é ABERTO: nada revela contato institucional
# ===========================================================================


def test_escalonamento_nao_expoe_destino(cliente):
    """O contrato em `models.py` é explícito: `CanalOpcao` não tem `destino`.
    Devolver o telefone aqui entregaria os contatos institucionais a qualquer um
    que alcance a API."""
    opcoes = acionar(cliente).json()["escalonamento_disponivel"]
    assert all(set(o) == {"canal", "nome"} for o in opcoes)


def test_resultado_nao_expoe_destino(cliente):
    resultados = acionar(cliente).json()["resultados"]
    assert all(set(r) == {"canal", "nome", "sucesso", "detalhe"} for r in resultados)


def test_nenhum_contato_aparece_na_resposta(cliente):
    resposta = acionar(cliente).text
    assert CONTATO_CSV not in resposta
    assert CONTATO_LILAS not in resposta


def test_detalhe_da_falha_nao_repassa_a_resposta_do_webhook(cliente, monkeypatch):
    """O vazamento sutil que o endpoint aberto cria.

    O `detalhe` do provider carrega o corpo da resposta do webhook (MVP-029), e
    esse corpo pode ecoar o número discado — `{"error": "invalid number
    5586..."}` é uma resposta plausível da Evolution API. Repassá-lo aqui
    entregaria o contato institucional a qualquer um que alcance a API.

    O detalhe real continua em `notificacoes`, atrás do token do painel.
    """

    async def falha_com_eco(chamado, canal, **kwargs):
        return False, f'HTTP 400: {{"error": "invalid number {CONTATO_CSV}"}}'

    monkeypatch.setattr(canais, "notificar", falha_com_eco)

    resposta = acionar(cliente)

    assert CONTATO_CSV not in resposta.text
    assert all(not r["sucesso"] for r in resposta.json()["resultados"])
    assert all(r["detalhe"] for r in resposta.json()["resultados"])


def test_detalhe_e_nulo_no_sucesso(cliente):
    resultados = acionar(cliente).json()["resultados"]
    assert all(r["detalhe"] is None for r in resultados)


def test_detalhe_completo_fica_no_banco(cliente, monkeypatch):
    """A informação não é perdida, só não sai pelo endpoint aberto. O operador
    do painel precisa do detalhe real para saber o que consertar."""
    monkeypatch.setattr(config, "_CONTATOS", {})

    r = acionar(cliente)

    detalhes = [n["detalhe"] for n in db.listar_notificacoes(r.json()["chamado_id"])]
    assert all("sem contato" in d for d in detalhes)


# ===========================================================================
# Idempotência
# ===========================================================================


def test_reenvio_devolve_o_mesmo_protocolo(cliente):
    dados = corpo()

    primeiro = cliente.post(ROTA, json=dados)
    segundo = cliente.post(ROTA, json=dados)

    assert segundo.status_code == 201
    assert segundo.json()["duplicado"] is True
    assert segundo.json()["chamado_id"] == primeiro.json()["chamado_id"]


def test_primeiro_panico_nao_e_duplicado(cliente):
    assert acionar(cliente).json()["duplicado"] is False


def test_reenvio_nao_aciona_de_novo(cliente):
    """Duplo toque no botão de pânico é o caso mais provável de todos. Acionar
    duas vezes faria a central despachar duas equipes."""
    dados = corpo()

    cliente.post(ROTA, json=dados)
    cliente.post(ROTA, json=dados)
    cliente.post(ROTA, json=dados)

    chamado_id = db.listar_chamados()[0]["chamado_id"]
    assert len(db.listar_notificacoes(chamado_id)) == 2
    assert len(db.listar_chamados()) == 1


def test_reenvio_reconstroi_os_resultados(cliente):
    """A tela pode estar recarregando depois de perder a conexão e precisa saber
    o que já aconteceu — devolver `resultados` vazio a faria parecer que nenhum
    canal foi acionado."""
    dados = corpo()

    primeiro = cliente.post(ROTA, json=dados)
    segundo = cliente.post(ROTA, json=dados)

    assert segundo.json()["resultados"] == primeiro.json()["resultados"]


def test_reenvio_reconstroi_falhas_tambem(cliente, monkeypatch):
    monkeypatch.setattr(config, "_CONTATOS", {"csv": CONTATO_CSV})
    dados = corpo()

    cliente.post(ROTA, json=dados)
    segundo = cliente.post(ROTA, json=dados)

    por_canal = {r["canal"]: r["sucesso"] for r in segundo.json()["resultados"]}
    assert por_canal == {"csv": True, "sala_lilas": False}


def test_reenvio_ainda_oferece_escalonamento(cliente):
    dados = corpo()

    cliente.post(ROTA, json=dados)
    segundo = cliente.post(ROTA, json=dados)

    assert len(segundo.json()["escalonamento_disponivel"]) == 4


async def test_reenvio_nao_avisa_a_central_de_novo(cliente, painel):
    dados = corpo()

    cliente.post(ROTA, json=dados)
    cliente.post(ROTA, json=dados)

    assert painel.nomes().count("novo_chamado") == 1


def test_panicos_distintos_geram_chamados_distintos(cliente):
    assert acionar(cliente).json()["chamado_id"] != acionar(cliente).json()["chamado_id"]


# ===========================================================================
# Contrato de entrada
# ===========================================================================


def test_evento_id_ausente_e_rejeitado(cliente):
    assert cliente.post(ROTA, json={"totem_id": "T"}).status_code == 422


def test_evento_id_malformado_e_rejeitado(cliente):
    r = cliente.post(ROTA, json={"evento_id": "nao-e-uuid", "totem_id": "T"})
    assert r.status_code == 422


def test_totem_ausente_e_rejeitado(cliente):
    assert cliente.post(ROTA, json={"evento_id": str(uuid4())}).status_code == 422


def test_relogio_desregulado_nao_impede_o_panico(cliente):
    r = acionar(cliente, timestamp_local="qualquer coisa")
    assert r.status_code == 201


def test_modo_discreto_e_preservado(cliente):
    """Quem toca pânico dentro da trilha discreta continua em modo discreto — a
    notificação avisa quem vai atender que a abordagem precisa ser silenciosa."""
    r = acionar(cliente, modo="discreto")
    assert db.obter_chamado(r.json()["chamado_id"])["modo"] == Modo.discreto


def test_panico_nao_exige_credencial(cliente):
    """Um totem em pânico não pode falhar por autenticação. Este teste existe
    para que uma exigência de token adicionada por engano (MVP-040) apareça
    aqui."""
    r = cliente.post(ROTA, json=corpo())
    assert r.status_code == 201
