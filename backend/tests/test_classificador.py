"""Classificador de triagem.

Estes testes cobrem o **contrato** (interface, degradação graciosa, cache). A
acurácia é medida pelo script de treino contra o held-out, não aqui: teste
unitário não é lugar de métrica de modelo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import config
from app.triagem import classificador as clf

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture(autouse=True)
def cache_limpo():
    """O cache é global e sobreviveria entre testes."""
    clf._cache.update(caminho=None, modelo=None, tentado=False)
    yield
    clf._cache.update(caminho=None, modelo=None, tentado=False)


@pytest.fixture
def sem_artefato(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CLF_PATH", str(tmp_path / "nao-existe.joblib"))


@pytest.fixture(scope="session")
def artefato_treinado(tmp_path_factory):
    """Treina uma vez para toda a sessão — são alguns segundos."""
    destino = tmp_path_factory.mktemp("clf") / "triagem.joblib"
    dados = json.loads((SCRIPTS / "triagem_dataset.json").read_text(encoding="utf-8"))
    clf.treinar(dados, caminho=str(destino))
    return str(destino)


@pytest.fixture
def treinado(artefato_treinado, monkeypatch):
    monkeypatch.setattr(config, "CLF_PATH", artefato_treinado)


# --- Degradação graciosa ----------------------------------------------------


def test_sem_artefato_nao_esta_disponivel(sem_artefato):
    assert clf.disponivel() is False


def test_sem_artefato_classificar_devolve_none(sem_artefato):
    """`None` é o sinal para cair na heurística. Levantar exceção aqui
    derrubaria o acionamento de quem está pedindo socorro."""
    assert clf.classificar("socorro") is None


def test_artefato_corrompido_nao_levanta_excecao(tmp_path, monkeypatch):
    ruim = tmp_path / "corrompido.joblib"
    ruim.write_bytes(b"isto nao e um modelo")
    monkeypatch.setattr(config, "CLF_PATH", str(ruim))

    assert clf.disponivel() is False
    assert clf.classificar("socorro") is None


@pytest.mark.parametrize("entrada", [None, "", "   ", "\n"])
def test_texto_vazio_devolve_none(treinado, entrada):
    assert clf.classificar(entrada) is None


# --- Contrato ---------------------------------------------------------------


def test_classificar_devolve_os_campos_do_contrato(treinado):
    r = clf.classificar("tem um cara armado no estacionamento")
    assert set(r) >= {"tipo", "gravidade", "confianca"}


def test_rotulos_pertencem_ao_dominio(treinado):
    from app.models import Gravidade, TipoOcorrencia

    r = clf.classificar("estou passando muito mal")
    assert r["tipo"] in {t.value for t in TipoOcorrencia}
    assert r["gravidade"] in {g.value for g in Gravidade}


def test_confianca_e_probabilidade(treinado):
    r = clf.classificar("socorro")
    assert 0.0 <= r["confianca"] <= 1.0
    assert 0.0 <= r["confianca_gravidade"] <= 1.0


def test_disponivel_com_artefato(treinado):
    assert clf.disponivel() is True


# --- Cache ------------------------------------------------------------------


def test_modelo_fica_em_memoria(treinado):
    """Carregar do disco a cada acionamento desperdiçaria o ganho de latência
    que justifica esta abordagem."""
    clf.classificar("socorro")
    assert clf._cache["modelo"] is not None
    primeiro = clf._cache["modelo"]
    clf.classificar("outra frase qualquer")
    assert clf._cache["modelo"] is primeiro


def test_cache_se_refaz_quando_o_caminho_muda(treinado, tmp_path, monkeypatch):
    assert clf.disponivel() is True
    monkeypatch.setattr(config, "CLF_PATH", str(tmp_path / "outro.joblib"))
    assert clf.disponivel() is False


def test_ausencia_do_artefato_nao_e_reconsultada(sem_artefato):
    """Insistir no disco a cada acionamento custaria I/O no caminho crítico."""
    clf.classificar("socorro")
    assert clf._cache["tentado"] is True


# --- Treino -----------------------------------------------------------------


def test_treinar_salva_e_relata(tmp_path):
    destino = tmp_path / "novo.joblib"
    dados = json.loads((SCRIPTS / "triagem_dataset.json").read_text(encoding="utf-8"))
    r = clf.treinar(dados, caminho=str(destino))

    assert destino.is_file()
    assert r["amostras"] == len(dados)
    assert r["tamanho_kb"] > 0


def test_treinar_invalida_o_cache(tmp_path, monkeypatch):
    """Sem isso, o modelo recém-treinado só entraria em uso no próximo boot."""
    destino = tmp_path / "novo.joblib"
    monkeypatch.setattr(config, "CLF_PATH", str(destino))
    assert clf.disponivel() is False  # popula o cache com "não existe"

    dados = json.loads((SCRIPTS / "triagem_dataset.json").read_text(encoding="utf-8"))
    clf.treinar(dados, caminho=str(destino))
    assert clf.disponivel() is True


def test_treinar_cria_o_diretorio(tmp_path):
    destino = tmp_path / "sub" / "dir" / "m.joblib"
    dados = json.loads((SCRIPTS / "triagem_dataset.json").read_text(encoding="utf-8"))
    clf.treinar(dados, caminho=str(destino))
    assert destino.is_file()


# --- Status -----------------------------------------------------------------


def test_status_sem_artefato(sem_artefato):
    s = clf.status()
    assert s["disponivel"] is False
    assert s["artefato_existe"] is False


def test_status_com_artefato(treinado):
    """O /health precisa reportar o que de fato está carregado. O projeto de
    referência dizia usar IA sem estar usando, e não havia como perceber."""
    s = clf.status()
    assert s["disponivel"] is True
    assert s["artefato_existe"] is True
    assert s["meta"]["amostras"] > 0
    assert s["meta"]["treinado_em"]


# --- Robustez a erro de digitação -------------------------------------------


@pytest.mark.parametrize(
    "certo,torto",
    [
        ("socorro", "socorroo"),
        ("estou passando mal", "estou passando maal"),
        ("estou desmaiando", "estou desmaindo"),
    ],
)
def test_erro_de_digitacao_nao_muda_a_trilha(treinado, certo, torto):
    """É para isto que servem os n-gramas de caractere: quem digita em pânico
    erra, e errar não pode mudar para onde o pedido vai."""
    assert clf.classificar(certo)["tipo"] == clf.classificar(torto)["tipo"]
