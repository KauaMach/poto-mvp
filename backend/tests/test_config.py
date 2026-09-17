"""Catálogo de canais, prazos de SLA e horário de funcionamento.

Estes testes travam invariantes que, se quebrados, levam um chamado para o
lugar errado ou vazam contato institucional — não são testes de formatação.
"""

from __future__ import annotations

import importlib

import pytest

from app import config
from app.models import Gravidade


@pytest.fixture
def config_com_env(monkeypatch):
    """Recarrega o módulo com variáveis de ambiente controladas.

    `config` lê o ambiente no import, então trocar env depois não teria efeito
    sem o reload.
    """

    def _carregar(**env):
        for chave, valor in env.items():
            monkeypatch.setenv(chave, valor)
        return importlib.reload(config)

    yield _carregar
    importlib.reload(config)  # restaura para os demais testes


# --- Catálogo ---------------------------------------------------------------


def test_catalogo_tem_os_oito_canais():
    assert set(config.CANAIS) == {
        "csv",
        "sala_lilas",
        "sapsi",
        "ouvidoria",
        "samu_192",
        "pm_190",
        "bombeiros_193",
        "central_180",
    }


def test_todo_canal_tem_nome_legivel():
    for canal, meta in config.CANAIS.items():
        assert meta.get("nome"), f"{canal} sem nome"


def test_catalogo_nao_carrega_contato():
    """`/canais` é endpoint de sistema, sem token. Um catálogo que carregasse
    o telefone convidaria a vazá-lo com um `return CANAIS`."""
    for meta in config.CANAIS.values():
        assert "contato" not in meta


def test_catalogo_e_contatos_nao_divergem():
    """Se um canal entrar no catálogo e não no mapa de contatos (ou o
    contrário), ele vira inacionável ou invisível — em silêncio."""
    assert set(config.CANAIS) == set(config._CONTATOS)


def test_nome_canal_degrada_para_a_chave():
    assert config.nome_canal("samu_192") == "SAMU"
    assert config.nome_canal("canal_inexistente") == "canal_inexistente"


# --- Grupos -----------------------------------------------------------------


def test_broadcast_de_panico_aciona_os_canais_internos():
    """Só o CSV (COR-001).

    A Sala Lilás saiu daqui porque o pânico não diz qual é a emergência — e
    mobilizar um serviço especializado sem saber o motivo atrasa a resposta dele
    no caso que é de fato da alçada dele. A trilha `mulher` continua acionando a
    Sala Lilás, que é o caminho dedicado e discreto.
    """
    assert config.CANAIS_INTERNOS == ["csv"]
    assert "sala_lilas" not in config.CANAIS_INTERNOS


def test_sala_lilas_segue_no_catalogo_e_com_contato():
    """Tirá-la do broadcast de pânico não é tirá-la do sistema.

    Ela continua no catálogo de canais e continua sendo destino da trilha
    `mulher` — se este teste falhar junto com o de cima, alguém removeu o canal
    em vez de removê-lo do pânico.
    """
    assert "sala_lilas" in config.CANAIS
    assert "sala_lilas" in config._CONTATOS


def test_escalonamento_manual_oferece_as_autoridades_do_estado():
    assert config.CANAIS_ESTADO == ["pm_190", "samu_192", "bombeiros_193", "central_180"]


@pytest.mark.parametrize("grupo", ["CANAIS_INTERNOS", "CANAIS_ESTADO"])
def test_grupos_so_referenciam_canais_do_catalogo(grupo):
    for canal in getattr(config, grupo):
        assert canal in config.CANAIS, f"{canal} não existe no catálogo"


def test_interno_e_estado_nao_se_sobrepoem():
    """O broadcast automático não pode alcançar 190/192: essas só entram por
    acionamento humano explícito."""
    assert not set(config.CANAIS_INTERNOS) & set(config.CANAIS_ESTADO)


# --- SLA --------------------------------------------------------------------


def test_prazos_de_sla():
    assert config.SLA_SEGUNDOS["risco_imediato"] == 120
    assert config.SLA_SEGUNDOS["risco_potencial"] == 600
    assert config.SLA_SEGUNDOS["orientacao"] is None


def test_sla_aceita_lookup_pelo_enum():
    """Gravidade é StrEnum, então indexa o dicionário sem conversão."""
    assert config.SLA_SEGUNDOS[Gravidade.risco_imediato] == 120


def test_toda_gravidade_tem_entrada_no_sla():
    for g in Gravidade:
        assert g.value in config.SLA_SEGUNDOS


# --- Horário ----------------------------------------------------------------


def test_expediente_e_de_segunda_a_sexta():
    assert config.HORARIO_COMERCIAL["dias"] == {0, 1, 2, 3, 4}


def test_expediente_tem_intervalo_de_almoco():
    assert config.HORARIO_COMERCIAL["janelas"] == [(8, 12), (14, 17)]


def test_fuso_e_fixo_em_utc_menos_3():
    """O Piauí não adota horário de verão, e a Pi pode estar sem NTP. Fixar o
    deslocamento é mais seguro que confiar no relógio do sistema."""
    assert config.FUSO_LOCAL.utcoffset(None).total_seconds() == -3 * 3600


# --- Contatos ---------------------------------------------------------------


def test_nenhum_contato_tem_default(config_com_env):
    """O projeto de referência trazia um celular real embutido no código,
    acionável por qualquer um na rede."""
    c = config_com_env()
    assert c.canais_sem_contato() == sorted(c.CANAIS)


def test_contato_vem_do_ambiente(config_com_env):
    c = config_com_env(POTO_CONTACT_SAMU="192")
    assert c.contato_canal("samu_192") == "192"
    assert "samu_192" not in c.canais_sem_contato()


def test_override_redireciona_todos_os_canais(config_com_env):
    """Trava de bancada: impede discar 190/192/193/180 de verdade nos ensaios."""
    c = config_com_env(POTO_CONTACT_PM="190", POTO_CONTACT_OVERRIDE="5586900000000")
    assert c.contato_canal("pm_190") == "5586900000000"
    assert c.contato_canal("samu_192") == "5586900000000"
    assert c.canais_sem_contato() == []
