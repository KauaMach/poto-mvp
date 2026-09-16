"""Heurística de palavras-chave — a rede de segurança final.

O critério de julgamento aqui é diferente do classificador: a heurística não
precisa ser precisa, precisa ser **protetiva**. Errar para cima custa uma
notificação a mais; errar para baixo deixa um pedido de socorro na Ouvidoria.
"""

from __future__ import annotations

import pytest

from app.models import Gravidade, TipoOcorrencia
from app.triagem import heuristica as h

RANK = {"orientacao": 1, "risco_potencial": 2, "risco_imediato": 3}


# --- Nunca devolve None -----------------------------------------------------


@pytest.mark.parametrize("entrada", [None, "", "   ", "asdfghjkl", "123 456"])
def test_sempre_devolve_resultado_valido(entrada):
    """Ao contrário do classificador, que devolve None quando não pode opinar,
    a heurística é o último recurso e sempre precisa encaminhar."""
    r = h.classificar(entrada)
    assert r["tipo"] in {t.value for t in TipoOcorrencia}
    assert r["gravidade"] in {g.value for g in Gravidade}
    assert isinstance(r["sinal_critico"], bool)


# --- Morfologia -------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "estou desmaiando",
        "desmaiei no banheiro",
        "ela desmaiou agora",
        "acho que vou desmaiar",
    ],
)
def test_toda_a_familia_de_desmaiar_e_critica(texto):
    """O defeito exato do projeto de referência: a lista tinha `desmaio` e
    `desmaiou`, não `desmaiando`, e "estou desmaiando" ia para a Ouvidoria."""
    r = h.classificar(texto)
    assert r["tipo"] == TipoOcorrencia.saude
    assert r["gravidade"] == Gravidade.risco_imediato


@pytest.mark.parametrize(
    "texto",
    [
        "me ameacaram de morte",
        "ele me ameaçou de morte",
        "recebi ameaça de morte",
        "ameaças de morte de um aluno",
    ],
)
def test_ameaca_de_morte_em_qualquer_flexao(texto):
    assert h.tem_sinal_critico(texto) is True


@pytest.mark.parametrize("texto", ["tão me seguindo", "ta me seguindo", "me seguiu ate aqui"])
def test_variacoes_de_perseguicao(texto):
    r = h.classificar(texto)
    assert RANK[r["gravidade"]] >= RANK["risco_potencial"]


# --- Falso positivo por substring -------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "o armário do laboratório está quebrado",
        "preciso de informação sobre o armazenamento",
        "o armador do time não apareceu",
    ],
)
def test_armario_nao_dispara_emergencia(texto):
    """No projeto de referência o casamento era substring crua, e "arma" está
    nos sinais críticos — então "armário" abria uma emergência."""
    assert h.tem_sinal_critico(texto) is False


def test_arma_de_verdade_dispara():
    assert h.tem_sinal_critico("tem um cara com uma arma") is True
    assert h.tem_sinal_critico("um homem armado no corredor") is True


# --- Acentuação -------------------------------------------------------------


@pytest.mark.parametrize(
    "com,sem",
    [
        ("assédio no corredor", "assedio no corredor"),
        ("teve uma convulsão", "teve uma convulsao"),
        ("estou em pânico", "estou em panico"),
        ("me ameaçaram", "me ameacaram"),
    ],
)
def test_acento_nao_muda_o_resultado(com, sem):
    """Num tablet e sob estresse, digitar sem acento é a regra."""
    assert h.classificar(com)["tipo"] == h.classificar(sem)["tipo"]


def test_caixa_alta_nao_muda_o_resultado():
    assert h.classificar("SOCORRO")["tipo"] == h.classificar("socorro")["tipo"]


# --- Comportamento protetivo ------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "tem alguém atrás de mim",
        "estou com medo",
        "estou sozinha e tem um estranho aqui",
        "to fugindo de alguem",
    ],
)
def test_ameaca_sem_categoria_vira_seguranca_e_nao_ouvidoria(texto):
    """Sem esta regra, "tem alguém atrás de mim" seria orientação — e o pedido
    iria para um canal que não atende de madrugada."""
    r = h.classificar(texto)
    assert r["tipo"] == TipoOcorrencia.seguranca
    assert RANK[r["gravidade"]] >= RANK["risco_potencial"]


@pytest.mark.parametrize(
    "texto",
    [
        "socorro",
        "estou desmaiando",
        "to passando mal",
        "tem um cara armado",
        "tem fumaça saindo da sala",
        "sinto cheiro de gás",
        "estou sangrando muito",
    ],
)
def test_emergencias_sao_criticas(texto):
    r = h.classificar(texto)
    assert r["sinal_critico"] is True
    assert r["gravidade"] == Gravidade.risco_imediato


@pytest.mark.parametrize(
    "texto",
    [
        "queria sugerir mais bancos no pátio",
        "onde fica a secretaria do curso",
        "quero elogiar o atendimento",
        "perdi minha carteirinha",
    ],
)
def test_trivialidades_nao_viram_emergencia(texto):
    """Superproteger tem custo: enche o painel de ruído e esconde o caso real."""
    r = h.classificar(texto)
    assert r["sinal_critico"] is False
    assert r["gravidade"] == Gravidade.orientacao


# --- Confiança --------------------------------------------------------------


def test_confianca_e_modesta():
    """A heurística é fallback. Confiança alta aqui sugeriria uma certeza que
    contagem de palavras não sustenta."""
    for texto in ["socorro", "tem um cara armado com uma arma", "assédio"]:
        assert h.classificar(texto)["confianca"] <= 0.75


def test_texto_sem_sinal_tem_confianca_baixa():
    assert h.classificar("asdfgh")["confianca"] <= 0.25


# --- Tipos ------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("sofri assédio no corredor", TipoOcorrencia.mulher),
        ("meu ex-namorado está me esperando", TipoOcorrencia.mulher),
        ("teve um assalto no estacionamento", TipoOcorrencia.seguranca),
        ("estou com dor no peito", TipoOcorrencia.saude),
        ("queria fazer uma reclamação", TipoOcorrencia.ouvidoria),
    ],
)
def test_classificacao_por_trilha(texto, esperado):
    assert h.classificar(texto)["tipo"] == esperado
