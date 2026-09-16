"""Integridade dos datasets de triagem.

O teste mais importante aqui é o de sobreposição. Se uma frase do held-out
aparecer no treino, a acurácia medida deixa de significar "acerta frases que
nunca viu" e passa a significar "lembra do que decorou" — e a decisão de
chamar ou não o SAMU passaria a se apoiar num número inflado.
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
TIPOS = {"seguranca", "mulher", "saude", "ouvidoria"}
GRAVIDADES = {"risco_imediato", "risco_potencial", "orientacao"}


def _carregar(nome: str) -> list[dict]:
    return json.loads((SCRIPTS / nome).read_text(encoding="utf-8"))


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento — para pegar vazamento disfarçado de variação."""
    decomposto = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


@pytest.fixture(scope="module")
def treino() -> list[dict]:
    return _carregar("triagem_dataset.json")


@pytest.fixture(scope="module")
def bench() -> list[dict]:
    return _carregar("bench_dataset.json")


# --- Vazamento --------------------------------------------------------------


def test_held_out_nao_aparece_no_treino(treino, bench):
    """Sem isto, 83% de acurácia poderia ser só memorização."""
    vazados = {_normalizar(x["texto"]) for x in treino} & {
        _normalizar(x["texto"]) for x in bench
    }
    assert not vazados, f"frases do held-out presentes no treino: {vazados}"


@pytest.mark.parametrize("nome", ["triagem_dataset.json", "bench_dataset.json"])
def test_sem_duplicatas_internas(nome):
    dados = _carregar(nome)
    textos = [_normalizar(x["texto"]) for x in dados]
    repetidos = [t for t, n in Counter(textos).items() if n > 1]
    assert not repetidos, f"repetidos em {nome}: {repetidos}"


# --- Formato ----------------------------------------------------------------


@pytest.mark.parametrize("nome", ["triagem_dataset.json", "bench_dataset.json"])
def test_todo_exemplo_tem_os_tres_campos(nome):
    for item in _carregar(nome):
        assert set(item) == {"texto", "tipo", "gravidade"}, item


@pytest.mark.parametrize("nome", ["triagem_dataset.json", "bench_dataset.json"])
def test_rotulos_pertencem_ao_dominio(nome):
    """Um rótulo com erro de digitação viraria uma classe fantasma que o
    modelo aprende e nunca casa com o roteador."""
    for item in _carregar(nome):
        assert item["tipo"] in TIPOS, item
        assert item["gravidade"] in GRAVIDADES, item


@pytest.mark.parametrize("nome", ["triagem_dataset.json", "bench_dataset.json"])
def test_nenhum_texto_vazio(nome):
    for item in _carregar(nome):
        assert item["texto"].strip()


# --- Tamanho e equilíbrio ---------------------------------------------------


def test_treino_tem_pelo_menos_77_exemplos(treino):
    assert len(treino) >= 77


def test_bench_tem_42_exemplos(bench):
    assert len(bench) == 42


@pytest.mark.parametrize("rotulo", sorted(TIPOS))
def test_toda_trilha_esta_representada_no_treino(treino, rotulo):
    """Trilha sem exemplo é trilha que o classificador nunca vai prever."""
    assert Counter(x["tipo"] for x in treino)[rotulo] >= 10


@pytest.mark.parametrize("rotulo", sorted(GRAVIDADES))
def test_toda_gravidade_esta_representada_no_treino(treino, rotulo):
    assert Counter(x["gravidade"] for x in treino)[rotulo] >= 10


# --- Cobertura das falhas conhecidas ----------------------------------------
#
# Cada frase abaixo foi reproduzida errando no projeto de referência, onde a
# heurística de substring não tolerava morfologia: a lista tinha "desmaio" e
# "desmaiou", não "desmaiando", e "estou desmaiando" ia para a Ouvidoria.


@pytest.mark.parametrize(
    "fragmento,tipo_esperado",
    [
        ("desmaiando", "saude"),
        ("desmaiei", "saude"),
        ("passando mal", "saude"),
        ("socorro", "seguranca"),
        ("socorroo", "seguranca"),
        ("me seguindo", "mulher"),
    ],
)
def test_variacoes_que_quebravam_a_heuristica_estao_no_treino(
    treino, fragmento, tipo_esperado
):
    casos = [x for x in treino if fragmento in _normalizar(x["texto"])]
    assert casos, f"nenhum exemplo com {fragmento!r}"
    assert any(x["tipo"] == tipo_esperado for x in casos), (
        f"{fragmento!r} existe mas nunca rotulado como {tipo_esperado}"
    )


@pytest.mark.parametrize(
    "fragmento",
    ["desmaiando", "passando mal", "socorro", "me seguindo"],
)
def test_emergencias_conhecidas_sao_rotuladas_como_risco_imediato(treino, fragmento):
    """Rótulo errado aqui ensina o modelo a subestimar justamente os casos que
    motivaram a inclusão destas frases."""
    casos = [x for x in treino if fragmento in _normalizar(x["texto"])]
    assert all(x["gravidade"] == "risco_imediato" for x in casos), [
        x for x in casos if x["gravidade"] != "risco_imediato"
    ]
