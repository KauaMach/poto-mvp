"""Merge protetivo — a invariante central do sistema.

Se um teste deste arquivo quebrar, alguém em risco recebe menos proteção do que
pediu. É o arquivo mais importante da suíte.

A regra que todos eles verificam, de ângulos diferentes: **nenhuma informação
nova pode reduzir a proteção já concedida.**
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.config import FUSO_LOCAL
from app.models import Gravidade, TipoOcorrencia
from app.triagem import heuristica
from app.triagem.merge import RANK_GRAVIDADE, mais_protetiva, merge_acionamento
from app.triagem.roteador import rotear

QUARTA_MANHA = datetime(2026, 9, 16, 10, 0, tzinfo=FUSO_LOCAL)
QUARTA_MADRUGADA = datetime(2026, 9, 16, 2, 0, tzinfo=FUSO_LOCAL)
HORARIOS = [QUARTA_MANHA, QUARTA_MADRUGADA]


def triar(texto: str) -> dict:
    """Usa a heurística: determinística, sem depender do artefato treinado."""
    return heuristica.classificar(texto)


def acionar(tipo: TipoOcorrencia, texto: str | None = None, *, agora=QUARTA_MANHA):
    """Simula o caminho completo de um acionamento com texto."""
    routing = rotear(tipo, agora=agora)
    triagem = triar(texto) if texto else None
    return routing, merge_acionamento(routing, triagem, texto=texto, agora=agora)


# ===========================================================================
# A invariante
# ===========================================================================


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("agora", HORARIOS)
@pytest.mark.parametrize(
    "texto",
    [
        "socorro",
        "preciso de ajuda",
        "um homem está me seguindo perto do bloco 7",
        "estou desmaiando",
        "queria sugerir mais bancos no pátio",
        "onde fica a secretaria",
        "perdi minha carteirinha",
        "asdfghjkl",
        "obrigado pelo atendimento de ontem",
        "quero elogiar a biblioteca",
    ],
)
def test_texto_nunca_rebaixa_a_gravidade(tipo, texto, agora):
    """A matriz completa: 4 trilhas × 10 textos × 2 horários.

    Nenhuma combinação pode produzir gravidade menor que a da trilha sozinha.
    """
    routing, decisao = acionar(tipo, texto, agora=agora)
    assert (
        RANK_GRAVIDADE[Gravidade(decisao["gravidade"])]
        >= RANK_GRAVIDADE[Gravidade(routing["gravidade"])]
    ), f"{tipo} + {texto!r} rebaixou {routing['gravidade']} → {decisao['gravidade']}"


# ===========================================================================
# Os casos reproduzidos no projeto de referência
# ===========================================================================
#
# Cada um destes foi verificado errando em 15/09/2026, no repositório
# gutoportelaa/poto. A gravidade era sobrescrita sem proteção em main.py:183-185.


@pytest.mark.parametrize(
    "texto",
    ["socorro", "preciso de ajuda", "um homem está me seguindo perto do bloco 7"],
)
def test_defeito_original_da_trilha_seguranca(texto):
    """Lá isto virava `orientacao` ou `risco_potencial` e o chamado ficava
    retido aguardando operador. Pedir ajuda tornava o sistema menos responsivo
    do que ficar calado."""
    _, decisao = acionar(TipoOcorrencia.seguranca, texto)
    assert decisao["gravidade"] == Gravidade.risco_imediato
    assert decisao["canal_roteado"] == "csv"


def test_socorro_e_o_caso_emblematico():
    """A palavra mais direta que existe para pedir ajuda não pode ser a que
    reduz a urgência."""
    _, decisao = acionar(TipoOcorrencia.seguranca, "socorro")
    assert decisao["gravidade"] == Gravidade.risco_imediato


# ===========================================================================
# Promoção: informação nova pode elevar
# ===========================================================================


def test_sinal_critico_promove_a_gravidade():
    """Trilha de saúde sem emergência nasce em `orientacao`. O texto revela que
    é emergência e a decisão sobe."""
    routing, decisao = acionar(TipoOcorrencia.saude, "estou desmaiando")
    assert routing["gravidade"] == Gravidade.orientacao
    assert decisao["gravidade"] == Gravidade.risco_imediato
    assert decisao["canal_roteado"] == "samu_192"


def test_sinal_critico_redireciona_a_trilha():
    """Quem toca Segurança e escreve "estou desmaiando" precisa do SAMU, não
    do CSV — o texto revelou uma emergência de outra natureza."""
    _, decisao = acionar(TipoOcorrencia.seguranca, "estou desmaiando")
    assert decisao["tipo"] == TipoOcorrencia.saude
    assert decisao["canal_roteado"] == "samu_192"
    assert decisao["gravidade"] == Gravidade.risco_imediato


def test_ouvidoria_promovida_por_texto_grave():
    routing, decisao = acionar(TipoOcorrencia.ouvidoria, "tem um homem armado aqui")
    assert routing["gravidade"] == Gravidade.orientacao
    assert decisao["gravidade"] == Gravidade.risco_imediato


# ===========================================================================
# Não promoção indevida
# ===========================================================================


def test_texto_trivial_nao_redireciona_a_trilha():
    """Ouvidoria nunca toma o lugar de uma trilha mais séria."""
    _, decisao = acionar(TipoOcorrencia.seguranca, "queria sugerir mais bancos")
    assert decisao["tipo"] == TipoOcorrencia.seguranca
    assert decisao["canal_roteado"] == "csv"


def test_texto_sem_sinal_critico_nao_muda_o_tipo():
    """Restrição deliberada, mais estrita que "o texto sempre vence".

    Deixar o texto redirecionar livremente criaria combinações que nenhuma das
    fontes produziria sozinha: Segurança (risco imediato) + "preciso de um
    atestado" viraria saúde com risco imediato, e o sistema chamaria o SAMU
    para um pedido de atestado.
    """
    _, decisao = acionar(TipoOcorrencia.seguranca, "preciso de um atestado, como faço?")
    assert decisao["tipo"] == TipoOcorrencia.seguranca
    assert decisao["canal_roteado"] != "samu_192"


def test_trivialidade_em_ouvidoria_continua_orientacao():
    """Superproteger tem custo: um painel cheio de emergências falsas esconde
    a real."""
    _, decisao = acionar(TipoOcorrencia.ouvidoria, "queria sugerir mais bancos no pátio")
    assert decisao["gravidade"] == Gravidade.orientacao
    assert decisao["canal_roteado"] == "ouvidoria"


# ===========================================================================
# Modo discreto
# ===========================================================================


@pytest.mark.parametrize(
    "texto",
    ["estou desmaiando", "socorro", "tem um homem armado", "queria sugerir bancos"],
)
@pytest.mark.parametrize("agora", HORARIOS)
def test_discricao_nunca_e_revogada(texto, agora):
    """Mesmo quando o texto redireciona o tipo, a tela continua neutra. Se o
    agressor está perto, revelar o canal acionado transforma socorro em risco."""
    _, decisao = acionar(TipoOcorrencia.mulher, texto, agora=agora)
    assert decisao["instrucao"].tela_neutra is True
    assert decisao["instrucao"].feedback_sonoro is False


def test_mensagem_discreta_nao_vaza_o_canal():
    _, decisao = acionar(TipoOcorrencia.mulher, "estou desmaiando")
    msg = decisao["instrucao"].mensagem_tela.lower()
    for palavra in ["samu", "lilás", "lilas", "polícia", "policia", "180"]:
        assert palavra not in msg


# ===========================================================================
# Sem triagem
# ===========================================================================


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
def test_sem_texto_devolve_o_roteamento_intacto(tipo):
    """O caminho do toque puro e do pânico: não há informação nova a incorporar."""
    routing = rotear(tipo, agora=QUARTA_MANHA)
    assert merge_acionamento(routing, None) == routing


# ===========================================================================
# Coerência do resultado
# ===========================================================================


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("texto", ["socorro", "estou desmaiando", "asdfgh", "obrigado"])
def test_canal_e_coerente_com_o_tipo_final(tipo, texto):
    """Canal apontando para o CSV num chamado que virou emergência de saúde
    seria incoerência silenciosa."""
    from app.config import CANAIS

    _, decisao = acionar(tipo, texto)
    esperado = rotear(
        decisao["tipo"],
        decisao["modo"],
        emergencia=decisao["gravidade"] == Gravidade.risco_imediato,
        agora=QUARTA_MANHA,
    )
    assert decisao["canal_roteado"] == esperado["canal_roteado"]
    assert decisao["canal_roteado"] in CANAIS
    assert decisao["fallback"] in CANAIS


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("texto", ["socorro", "asdfgh", "estou desmaiando"])
def test_resultado_mantem_o_contrato_do_roteamento(tipo, texto):
    _, decisao = acionar(tipo, texto)
    assert set(decisao) == {
        "tipo", "modo", "canal_roteado", "fallback",
        "gravidade", "instrucao", "horario_comercial",
    }


# ===========================================================================
# mais_protetiva
# ===========================================================================


@pytest.mark.parametrize(
    "a,b,esperado",
    [
        ("orientacao", "risco_imediato", "risco_imediato"),
        ("risco_imediato", "orientacao", "risco_imediato"),
        ("risco_potencial", "orientacao", "risco_potencial"),
        ("orientacao", "orientacao", "orientacao"),
        ("risco_imediato", "risco_imediato", "risco_imediato"),
    ],
)
def test_mais_protetiva(a, b, esperado):
    assert mais_protetiva(a, b) == esperado


def test_mais_protetiva_e_comutativa():
    """Se a ordem dos argumentos importasse, a proteção dependeria de qual
    fonte foi consultada primeiro."""
    for a in Gravidade:
        for b in Gravidade:
            assert mais_protetiva(a, b) == mais_protetiva(b, a)
