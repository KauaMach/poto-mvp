"""Roteamento determinístico — a rede de segurança.

Cada teste aqui corresponde a uma linha da tabela de ARCHITECTURE.md §4. Se um
deles quebrar, alguém em risco vai para o canal errado.

O relógio é sempre injetado: teste que depende da hora em que roda é teste que
passa de manhã e falha à noite.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.config import FUSO_LOCAL
from app.models import Gravidade, Modo, TipoOcorrencia
from app.triagem.roteador import em_horario_comercial, rotear

# Referências fixas. 16/09/2026 é uma quarta-feira; 19/09/2026, um sábado.
QUARTA_MANHA = datetime(2026, 9, 16, 10, 0, tzinfo=FUSO_LOCAL)
QUARTA_TARDE = datetime(2026, 9, 16, 15, 0, tzinfo=FUSO_LOCAL)
QUARTA_ALMOCO = datetime(2026, 9, 16, 12, 30, tzinfo=FUSO_LOCAL)
QUARTA_MADRUGADA = datetime(2026, 9, 16, 2, 0, tzinfo=FUSO_LOCAL)
QUARTA_NOITE = datetime(2026, 9, 16, 22, 0, tzinfo=FUSO_LOCAL)
SABADO_MANHA = datetime(2026, 9, 19, 10, 0, tzinfo=FUSO_LOCAL)
DOMINGO_TARDE = datetime(2026, 9, 20, 15, 0, tzinfo=FUSO_LOCAL)

FORA_DO_EXPEDIENTE = [QUARTA_ALMOCO, QUARTA_MADRUGADA, QUARTA_NOITE, SABADO_MANHA, DOMINGO_TARDE]
NO_EXPEDIENTE = [QUARTA_MANHA, QUARTA_TARDE]


# --- Janela de expediente ---------------------------------------------------


@pytest.mark.parametrize("quando", NO_EXPEDIENTE)
def test_dentro_do_expediente(quando):
    assert em_horario_comercial(quando) is True


@pytest.mark.parametrize("quando", FORA_DO_EXPEDIENTE)
def test_fora_do_expediente(quando):
    assert em_horario_comercial(quando) is False


def test_fim_de_semana_nao_e_expediente_mesmo_no_horario():
    """Sábado às 10h cai dentro da janela (8–12), mas não é dia útil."""
    assert em_horario_comercial(SABADO_MANHA) is False


@pytest.mark.parametrize(
    "hora,esperado",
    [
        (7, False),   # antes de abrir
        (8, True),    # abre
        (11, True),
        (12, False),  # almoço
        (13, False),
        (14, True),   # reabre
        (16, True),
        (17, False),  # fecha
    ],
)
def test_bordas_das_janelas(hora, esperado):
    quando = datetime(2026, 9, 16, hora, 0, tzinfo=FUSO_LOCAL)
    assert em_horario_comercial(quando) is esperado


# --- Segurança --------------------------------------------------------------


@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_seguranca_vai_para_o_csv_em_qualquer_horario(quando):
    """O CSV atende 24h. A trilha de segurança nunca muda de destino."""
    r = rotear(TipoOcorrencia.seguranca, agora=quando)
    assert r["canal_roteado"] == "csv"
    assert r["fallback"] == "pm_190"
    assert r["gravidade"] is Gravidade.risco_imediato


def test_seguranca_nao_e_discreta():
    r = rotear(TipoOcorrencia.seguranca, agora=QUARTA_MANHA)
    assert r["instrucao"].tela_neutra is False
    assert r["instrucao"].feedback_sonoro is True


# --- Mulher -----------------------------------------------------------------


@pytest.mark.parametrize("quando", NO_EXPEDIENTE)
def test_mulher_no_expediente_vai_para_a_sala_lilas(quando):
    r = rotear(TipoOcorrencia.mulher, agora=quando)
    assert r["canal_roteado"] == "sala_lilas"
    assert r["fallback"] == "central_180"


@pytest.mark.parametrize("quando", FORA_DO_EXPEDIENTE)
def test_mulher_fora_do_expediente_vai_para_a_central_180(quando):
    """A Sala Lilás não atende de madrugada. Encaminhar para uma sala vazia é
    o mesmo que não encaminhar."""
    r = rotear(TipoOcorrencia.mulher, agora=quando)
    assert r["canal_roteado"] == "central_180"
    assert r["fallback"] == "pm_190"


@pytest.mark.parametrize("modo", [Modo.normal, Modo.discreto])
@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_mulher_e_sempre_discreta(modo, quando):
    """Sem opção de desligar, em nenhum horário, nem quando o cliente pede
    `normal`. Se o agressor está a três metros, uma tela que anuncia
    "Sala Lilás acionada" transforma o socorro em risco."""
    r = rotear(TipoOcorrencia.mulher, modo, agora=quando)
    assert r["instrucao"].tela_neutra is True
    assert r["instrucao"].feedback_sonoro is False


@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_tela_da_trilha_mulher_nao_entrega_nada(quando):
    """A mensagem não pode citar o canal acionado nem a palavra denúncia."""
    msg = rotear(TipoOcorrencia.mulher, agora=quando)["instrucao"].mensagem_tela.lower()
    for palavra in ["lilás", "lilas", "denúncia", "denuncia", "180", "polícia", "policia"]:
        assert palavra not in msg


def test_mulher_tem_gravidade_de_risco_potencial():
    r = rotear(TipoOcorrencia.mulher, agora=QUARTA_MANHA)
    assert r["gravidade"] is Gravidade.risco_potencial


# --- Saúde ------------------------------------------------------------------


@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_saude_em_emergencia_chama_o_samu_em_qualquer_horario(quando):
    r = rotear(TipoOcorrencia.saude, emergencia=True, agora=quando)
    assert r["canal_roteado"] == "samu_192"
    assert r["fallback"] == "csv"
    assert r["gravidade"] is Gravidade.risco_imediato


@pytest.mark.parametrize("quando", NO_EXPEDIENTE)
def test_saude_de_apoio_no_expediente_vai_para_o_sapsi(quando):
    r = rotear(TipoOcorrencia.saude, agora=quando)
    assert r["canal_roteado"] == "sapsi"
    assert r["gravidade"] is Gravidade.orientacao


@pytest.mark.parametrize("quando", FORA_DO_EXPEDIENTE)
def test_saude_de_apoio_fora_do_expediente_fica_na_ouvidoria(quando):
    r = rotear(TipoOcorrencia.saude, agora=quando)
    assert r["canal_roteado"] == "ouvidoria"
    assert r["fallback"] == "ouvidoria"


def test_emergencia_de_saude_nao_depende_do_expediente():
    """Mal-estar às 3h da manhã de domingo continua sendo SAMU."""
    r = rotear(TipoOcorrencia.saude, emergencia=True, agora=DOMINGO_TARDE)
    assert r["canal_roteado"] == "samu_192"


# --- Ouvidoria --------------------------------------------------------------


@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_ouvidoria_e_sempre_ouvidoria(quando):
    r = rotear(TipoOcorrencia.ouvidoria, agora=quando)
    assert r["canal_roteado"] == "ouvidoria"
    assert r["fallback"] == "ouvidoria"
    assert r["gravidade"] is Gravidade.orientacao


# --- Invariantes ------------------------------------------------------------


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("modo", list(Modo))
@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_toda_combinacao_produz_roteamento_completo(tipo, modo, quando):
    """A matriz inteira: nenhuma combinação pode devolver campo vazio."""
    r = rotear(tipo, modo, agora=quando)
    assert r["canal_roteado"]
    assert r["fallback"]
    assert r["gravidade"] in list(Gravidade)
    assert r["instrucao"].mensagem_tela
    assert isinstance(r["horario_comercial"], bool)


@pytest.mark.parametrize("tipo", list(TipoOcorrencia))
@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_canais_roteados_existem_no_catalogo(tipo, quando):
    """Roteamento para um canal fora do catálogo seria um chamado perdido."""
    from app.config import CANAIS

    r = rotear(tipo, agora=quando)
    assert r["canal_roteado"] in CANAIS
    assert r["fallback"] in CANAIS


@pytest.mark.parametrize("quando", NO_EXPEDIENTE + FORA_DO_EXPEDIENTE)
def test_modo_discreto_pedido_pelo_cliente_e_respeitado(quando):
    """Qualquer trilha pode ser discreta a pedido; a mulher já é por padrão."""
    r = rotear(TipoOcorrencia.seguranca, Modo.discreto, agora=quando)
    assert r["instrucao"].tela_neutra is True
    assert r["instrucao"].feedback_sonoro is False


def test_relogio_padrao_e_usado_quando_agora_nao_e_passado():
    """Sem `agora`, usa o relógio real no fuso fixo — não deve explodir."""
    r = rotear(TipoOcorrencia.seguranca)
    assert r["canal_roteado"] == "csv"
