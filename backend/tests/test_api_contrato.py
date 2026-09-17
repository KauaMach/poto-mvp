"""Contrato da API — a invariante de segurança exercitada por HTTP.

`test_regressao_seguranca.py` cobre a mesma regra chamando funções. Este arquivo
a cobre **como um cliente real a exerce**: pelo Pydantic, pelo SQLite, pelo hub e
pelos canais. A diferença importa porque o defeito original do projeto de
referência não estava na lógica de merge — estava no endpoint, que chamava a
lógica certa e depois sobrescrevia o resultado.

A varredura central é a matriz completa **trilha × modo × texto**. Ela não
verifica um valor esperado por caso: verifica uma *desigualdade* — a gravidade
final nunca é menor que a da trilha escolhida. Uma tabela de valores esperados
precisaria ser reescrita a cada ajuste do classificador; a desigualdade vale
para sempre, e é exatamente o que o projeto promete.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import criar_app
from app.models import Gravidade, Modo, TipoOcorrencia
from app.triagem.merge import RANK_GRAVIDADE
from app.triagem.roteador import rotear

EVENTOS = "/api/v1/eventos"
PANICO = "/api/v1/panico"

# Textos escolhidos para cobrir as formas de "informação nova" que já causaram
# rebaixamento em algum momento: pedido de ajuda curto, relato grave, assunto de
# outra trilha, trivialidade e vazio.
TEXTOS = {
    "vazio": None,
    "em_branco": "   ",
    "socorro": "socorro",
    "pedido_de_ajuda": "preciso de ajuda",
    "perseguicao": "um homem está me seguindo",
    "ameaca_de_morte": "ele disse que vai me matar",
    "saude_critica": "estou desmaiando e sangrando muito",
    "trivial": "preciso de um atestado",
    "burocracia": "quero saber o horário da biblioteca",
    "medo_vago": "estou com medo",
    "ruido": "asdf qwer zxcv",
}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    """Banco temporário por teste — critério explícito da MVP-039."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setattr(config, "FRONTEND_DIST", str(tmp_path / "sem-dist"))
    monkeypatch.setattr(config, "PAINEL_TOKEN", "")
    monkeypatch.setattr(
        config,
        "_CONTATOS",
        {c: f"5586{i:09d}" for i, c in enumerate(config.CANAIS)},
    )
    monkeypatch.setattr(config, "CONTACT_OVERRIDE", "")
    monkeypatch.setattr(config, "NOTIF_PROVIDER", "log")
    with TestClient(criar_app()) as c:
        yield c


def acionar(cliente, tipo, modo=None, texto=None) -> dict:
    corpo = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": str(tipo),
    }
    if modo is not None:
        corpo["modo"] = str(modo)
    if texto is not None:
        corpo["texto_livre"] = texto
    r = cliente.post(EVENTOS, json=corpo)
    assert r.status_code == 201, r.text
    return r.json()


def rank(gravidade: str) -> int:
    return RANK_GRAVIDADE[Gravidade(gravidade)]


# ===========================================================================
# A matriz: trilha × modo × texto — a gravidade NUNCA cai
# ===========================================================================


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("modo", list(Modo))
@pytest.mark.parametrize("nome_texto", list(TEXTOS))
def test_gravidade_nunca_cai(cliente, tipo, modo, nome_texto):
    """44 combinações por HTTP. A invariante do projeto, inteira.

    A referência é a gravidade que o **roteador determinístico** dá para a
    trilha escolhida — a proteção que a pessoa obteve só por tocar o botão.
    Nenhum texto pode reduzi-la.
    """
    piso = rotear(tipo, modo)["gravidade"]

    resposta = acionar(cliente, tipo, modo, TEXTOS[nome_texto])

    assert rank(resposta["gravidade"]) >= rank(piso), (
        f"trilha {tipo} + {nome_texto!r} rebaixou {piso} -> "
        f"{resposta['gravidade']}"
    )


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("nome_texto", list(TEXTOS))
def test_gravidade_persistida_nunca_cai(cliente, tipo, nome_texto):
    """A mesma invariante **no banco**, não só na resposta. O painel e o worker
    de SLA leem de lá — uma resposta correta com um registro rebaixado faria a
    central tratar a emergência pela gravidade errada."""
    piso = rotear(tipo)["gravidade"]

    resposta = acionar(cliente, tipo, texto=TEXTOS[nome_texto])

    persistido = db.obter_chamado(resposta["chamado_id"])
    assert rank(persistido["gravidade"]) >= rank(piso)


@pytest.mark.parametrize("nome_texto", list(TEXTOS))
def test_seguranca_nunca_sai_de_risco_imediato(cliente, nome_texto):
    """A trilha onde o defeito original se manifestou: "socorro" rebaixava o
    chamado de `risco_imediato` para `orientacao`, e pedir ajuda tornava o
    sistema menos responsivo do que ficar calado."""
    resposta = acionar(cliente, TipoOcorrencia.seguranca, texto=TEXTOS[nome_texto])
    assert resposta["gravidade"] == Gravidade.risco_imediato


@pytest.mark.parametrize("nome_texto", list(TEXTOS))
def test_trilha_mulher_sempre_discreta(cliente, nome_texto):
    """Modo discreto nunca é revogado por texto. Se o agressor está a três
    metros, uma tela que anuncia "Sala Lilás acionada" transforma o socorro em
    risco."""
    resposta = acionar(
        cliente, TipoOcorrencia.mulher, Modo.normal, TEXTOS[nome_texto]
    )
    assert resposta["instrucao_totem"]["tela_neutra"] is True
    assert resposta["instrucao_totem"]["feedback_sonoro"] is False


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
def test_modo_discreto_pedido_e_respeitado(cliente, tipo):
    """Em qualquer trilha: quem pede discrição recebe discrição. O inverso — a
    trilha `mulher` ignorando um `modo=normal` — é o teste acima."""
    resposta = acionar(cliente, tipo, Modo.discreto)
    assert resposta["instrucao_totem"]["tela_neutra"] is True


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
def test_sinal_critico_promove_qualquer_trilha(cliente, tipo):
    """A rede embaixo da rede: evidência literal de emergência no texto eleva
    qualquer trilha a risco imediato, inclusive a ouvidoria."""
    resposta = acionar(cliente, tipo, texto="socorro, ele disse que vai me matar")
    assert resposta["gravidade"] == Gravidade.risco_imediato


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
def test_texto_trivial_nao_desvia_a_trilha(cliente, tipo):
    """O caso que `_tipo_final` restringe de propósito: sem sinal crítico, o
    texto não redireciona o tipo. Sem essa restrição, "preciso de um atestado"
    numa trilha de Segurança chamaria o SAMU."""
    resposta = acionar(cliente, tipo, texto="quero saber o horário da biblioteca")

    persistido = db.obter_chamado(resposta["chamado_id"])
    assert persistido["tipo_ocorrencia"] == tipo


# ===========================================================================
# Idempotência por HTTP
# ===========================================================================


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
def test_reenvio_nao_duplica(cliente, tipo):
    """É o que permite a fila offline drenar sem medo. Se falhar, uma emergência
    vira dois alarmes e a central despacha duas equipes."""
    corpo = {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": str(tipo),
        "texto_livre": "socorro",
    }

    respostas = [cliente.post(EVENTOS, json=corpo) for _ in range(3)]

    assert [r.status_code for r in respostas] == [201, 201, 201]
    assert [r.json()["duplicado"] for r in respostas] == [False, True, True]
    assert len({r.json()["chamado_id"] for r in respostas}) == 1
    assert len(db.listar_chamados()) == 1


def test_reenvio_de_panico_nao_duplica(cliente):
    corpo = {"evento_id": str(uuid4()), "totem_id": "T"}

    respostas = [cliente.post(PANICO, json=corpo) for _ in range(3)]

    assert [r.json()["duplicado"] for r in respostas] == [False, True, True]
    assert len(db.listar_chamados()) == 1


def test_reenvio_nao_notifica_de_novo(cliente):
    corpo = {
        "evento_id": str(uuid4()),
        "totem_id": "T",
        "tipo_ocorrencia": "seguranca",
    }

    cliente.post(EVENTOS, json=corpo)
    cliente.post(EVENTOS, json=corpo)

    chamado_id = db.listar_chamados()[0]["chamado_id"]
    assert len(db.listar_notificacoes(chamado_id)) == 1


def test_eventos_distintos_nao_colidem(cliente):
    """O caso oposto da idempotência, e o que a corrida de protocolo protege:
    vários eventos **distintos** chegando juntos recebem protocolos únicos."""
    ids = {
        acionar(cliente, TipoOcorrencia.seguranca)["chamado_id"] for _ in range(10)
    }
    assert len(ids) == 10


# ===========================================================================
# Banco temporário por teste
# ===========================================================================


def test_banco_comeca_vazio(cliente):
    """A fixture dá um banco novo por teste. Sem isso, a ordem de execução
    passaria a importar e uma falha ficaria irreprodutível."""
    assert cliente.get("/api/v1/chamados").json() == []


def test_primeiro_protocolo_do_banco(cliente):
    assert acionar(cliente, TipoOcorrencia.seguranca)["chamado_id"] == (
        "CALL-2026-000001"
    )


# ===========================================================================
# O ciclo completo, como a demonstração o exercita
# ===========================================================================


def test_ciclo_de_vida_completo(cliente):
    """Acionar → ver no painel → reconhecer → atender → escalonar → encerrar.

    O roteiro da banca (MVP-072) num único teste: se isto passa, o backend faz o
    que o projeto promete de ponta a ponta.
    """
    criado = acionar(cliente, TipoOcorrencia.seguranca, texto="socorro")
    cid = criado["chamado_id"]

    assert criado["gravidade"] == Gravidade.risco_imediato
    assert [c["chamado_id"] for c in cliente.get("/api/v1/chamados").json()] == [cid]

    assert cliente.post(f"/api/v1/chamados/{cid}/ack").json()["status"] == (
        "reconhecido"
    )
    assert cliente.patch(
        f"/api/v1/chamados/{cid}", json={"status": "em_atendimento"}
    ).json()["status"] == "em_atendimento"
    assert cliente.post(
        f"/api/v1/chamados/{cid}/escalonar", json={"canal": "samu_192"}
    ).json()["canal"] == "samu_192"
    assert cliente.patch(
        f"/api/v1/chamados/{cid}",
        json={"status": "encerrado", "observacao": "equipe atendeu no local"},
    ).json()["status"] == "encerrado"

    detalhe = cliente.get(f"/api/v1/chamados/{cid}").json()
    assert [e["para"] for e in detalhe["estados"]] == [
        "roteado",
        "notificado",
        "reconhecido",
        "em_atendimento",
        "encerrado",
    ]
    assert detalhe["observacao"] == "equipe atendeu no local"
    assert detalhe["gravidade"] == Gravidade.risco_imediato


def test_ciclo_do_panico(cliente):
    criado = cliente.post(
        PANICO, json={"evento_id": str(uuid4()), "totem_id": "T"}
    ).json()
    cid = criado["chamado_id"]

    assert criado["status"] == "alerta_ativo"
    # Um resultado por canal interno configurado (COR-001 deixou só o CSV); os
    # 4 do escalonamento são as autoridades do estado, e esses não mudaram.
    assert len(criado["resultados"]) == len(config.CANAIS_INTERNOS)
    assert len(criado["escalonamento_disponivel"]) == 4

    cliente.post(f"/api/v1/chamados/{cid}/escalonar", json={"canal": "pm_190"})
    assert db.obter_chamado(cid)["status"] == "alerta_ativo"

    assert cliente.post(f"/api/v1/chamados/{cid}/ack").json()["status"] == (
        "reconhecido"
    )


def test_relato_nunca_sai_na_notificacao(cliente):
    """A garantia da MVP-028 verificada no caminho completo, com todas as
    trilhas: o relato fica no banco e não entra na mensagem enviada."""
    relato = "meu ex está me esperando na saída e disse que vai me matar"

    for tipo in TipoOcorrencia:
        criado = acionar(cliente, tipo, texto=relato)
        detalhe = cliente.get(f"/api/v1/chamados/{criado['chamado_id']}").json()

        assert detalhe["texto_livre"] == relato
        for notificacao in detalhe["notificacoes"]:
            assert relato not in (notificacao["mensagem"] or "")
