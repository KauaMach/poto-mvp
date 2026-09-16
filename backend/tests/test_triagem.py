"""Fachada `triar()` — a porta única da triagem.

Dois grupos de teste aqui. O primeiro verifica o contrato e a honestidade da
`fonte`. O segundo, mais importante, verifica que **o resultado dos casos
críticos não depende de qual motor rodou**: se a Pi subir sem o artefato
treinado, "socorro" continua sendo emergência.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import config
from app.models import Gravidade, Modo, TipoOcorrencia
from app.triagem import classificador, motor_ativo, triar

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture(autouse=True)
def cache_limpo():
    classificador._cache.update(caminho=None, modelo=None, tentado=False)
    yield
    classificador._cache.update(caminho=None, modelo=None, tentado=False)


@pytest.fixture
def sem_classificador(tmp_path, monkeypatch):
    """Simula a Pi que subiu sem `make setup`."""
    monkeypatch.setattr(config, "CLF_PATH", str(tmp_path / "ausente.joblib"))


@pytest.fixture(scope="session")
def artefato(tmp_path_factory):
    destino = tmp_path_factory.mktemp("clf") / "t.joblib"
    dados = json.loads((SCRIPTS / "triagem_dataset.json").read_text(encoding="utf-8"))
    classificador.treinar(dados, caminho=str(destino))
    return str(destino)


@pytest.fixture
def com_classificador(artefato, monkeypatch):
    monkeypatch.setattr(config, "CLF_PATH", artefato)


# --- Contrato ---------------------------------------------------------------


CAMPOS = {"tipo", "gravidade", "confianca", "canal_sugerido", "sinal_critico", "fonte"}


@pytest.mark.parametrize("texto", ["socorro", "queria sugerir bancos", "", None, "   "])
def test_contrato_completo_em_qualquer_entrada(texto, com_classificador):
    assert set(triar(texto)) == CAMPOS


@pytest.mark.parametrize("texto", ["socorro", "asdfgh", "", None])
def test_rotulos_pertencem_ao_dominio(texto, com_classificador):
    from app.config import CANAIS

    r = triar(texto)
    assert r["tipo"] in {t.value for t in TipoOcorrencia}
    assert r["gravidade"] in {g.value for g in Gravidade}
    assert r["canal_sugerido"] in CANAIS


@pytest.mark.parametrize("texto", [None, "", "   ", "\n\t"])
def test_texto_vazio_devolve_resultado_neutro(texto, com_classificador):
    r = triar(texto)
    assert r["tipo"] == TipoOcorrencia.ouvidoria
    assert r["gravidade"] == Gravidade.orientacao
    assert r["sinal_critico"] is False


def test_texto_vazio_nao_finge_que_um_motor_rodou():
    """`fonte` seria desonesta ao nomear um motor que não executou."""
    assert triar("")["fonte"] == "vazio"


# --- Honestidade da fonte ---------------------------------------------------


def test_fonte_diz_classificador_quando_ele_roda(com_classificador):
    assert triar("tem um cara armado")["fonte"] == "classificador"
    assert motor_ativo() == "classificador"


def test_fonte_diz_heuristica_quando_nao_ha_artefato(sem_classificador):
    """O projeto de referência carimbava "agentes" mesmo sem LLM nenhum ter
    respondido, e não havia como perceber que a triagem estava degradada."""
    assert triar("tem um cara armado")["fonte"] == "heuristica"
    assert motor_ativo() == "heuristica"


def test_motor_ativo_acompanha_a_disponibilidade(tmp_path, monkeypatch, artefato):
    monkeypatch.setattr(config, "CLF_PATH", str(tmp_path / "nada.joblib"))
    assert motor_ativo() == "heuristica"
    monkeypatch.setattr(config, "CLF_PATH", artefato)
    assert motor_ativo() == "classificador"


# --- Sinal crítico vale em qualquer motor -----------------------------------


@pytest.mark.parametrize(
    "texto",
    ["socorro", "estou desmaiando", "estou sangrando muito", "me ameaçaram de morte"],
)
def test_sinal_critico_vale_mesmo_com_o_classificador(texto, com_classificador):
    """O classificador não produz `sinal_critico` — quem calcula é a heurística.
    Sem isto, um resultado dele chegaria ao merge sem a rede de evidência
    literal."""
    assert triar(texto)["sinal_critico"] is True


@pytest.mark.parametrize("texto", ["socorro", "estou desmaiando", "estou sangrando muito"])
def test_sinal_critico_vale_sem_o_classificador(texto, sem_classificador):
    assert triar(texto)["sinal_critico"] is True


# --- O resultado não depende do motor ---------------------------------------


CASOS_CRITICOS = [
    ("socorro", Gravidade.risco_imediato),
    ("estou desmaiando", Gravidade.risco_imediato),
    ("to passando mal", Gravidade.risco_imediato),
    ("tem um cara armado no estacionamento", Gravidade.risco_imediato),
    ("estou sangrando muito", Gravidade.risco_imediato),
]


@pytest.mark.parametrize("texto,gravidade", CASOS_CRITICOS)
def test_emergencia_com_classificador(texto, gravidade, com_classificador):
    assert triar(texto)["gravidade"] == gravidade


@pytest.mark.parametrize("texto,gravidade", CASOS_CRITICOS)
def test_emergencia_sem_classificador(texto, gravidade, sem_classificador):
    """A Pi que subiu sem `make setup` precisa tratar emergência como
    emergência. O motor muda; o desfecho, não."""
    assert triar(texto)["gravidade"] == gravidade


@pytest.mark.parametrize("texto", ["socorro", "estou desmaiando", "to passando mal"])
def test_canal_sugerido_e_o_mesmo_nos_dois_motores(
    texto, artefato, tmp_path, monkeypatch
):
    monkeypatch.setattr(config, "CLF_PATH", artefato)
    classificador._cache.update(caminho=None, modelo=None, tentado=False)
    com = triar(texto)["canal_sugerido"]

    monkeypatch.setattr(config, "CLF_PATH", str(tmp_path / "ausente.joblib"))
    classificador._cache.update(caminho=None, modelo=None, tentado=False)
    sem = triar(texto)["canal_sugerido"]

    assert com == sem, f"{texto!r}: classificador→{com}, heurística→{sem}"


# --- Modo -------------------------------------------------------------------


def test_modo_discreto_afeta_o_canal_sugerido(com_classificador):
    """Trilha mulher fora do expediente vai para a central estadual; a
    sugestão precisa refletir o mesmo roteamento do resto do sistema."""
    from datetime import datetime

    from app.config import FUSO_LOCAL

    madrugada = datetime(2026, 9, 16, 2, 0, tzinfo=FUSO_LOCAL)
    r = triar("sofri assédio", Modo.discreto, agora=madrugada)
    assert r["canal_sugerido"] in {"central_180", "csv", "samu_192", "pm_190"}


# --- Robustez ---------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    ["a" * 2000, "🚨🚨🚨", "SOCORRO!!!", "  socorro  ", "<script>alert(1)</script>"],
)
def test_entradas_incomuns_nao_quebram(texto, com_classificador):
    r = triar(texto)
    assert r["tipo"] in {t.value for t in TipoOcorrencia}


def test_artefato_corrompido_cai_na_heuristica(tmp_path, monkeypatch):
    ruim = tmp_path / "corrompido.joblib"
    ruim.write_bytes(b"nao sou um modelo")
    monkeypatch.setattr(config, "CLF_PATH", str(ruim))

    r = triar("socorro")
    assert r["fonte"] == "heuristica"
    assert r["gravidade"] == Gravidade.risco_imediato
