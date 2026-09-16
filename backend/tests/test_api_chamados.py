"""`GET /chamados` e `GET /chamados/{id}` — a leitura do painel.

A fronteira mais sensível da API. O que sai daqui inclui o relato de quem pediu
ajuda, o histórico de quem foi acionado e a trilha original de cada chamado —
tudo que quem atende precisa, e nada que mais ninguém deveria ver.

Duas famílias de teste, portanto. Uma cobra que o operador receba o suficiente
para trabalhar; a outra, que o contorno do contrato seja **lista de campos
permitidos** e não "tudo menos o que eu lembrei de tirar".
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import criar_app
from app.models import Gravidade, StatusChamado, TipoOcorrencia

LISTA = "/api/v1/chamados"
RELATO = "ele está me esperando na saída do bloco"
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


def acionar(cliente, **extra) -> dict:
    """Cria um chamado pelo caminho real, não escrevendo no banco à mão."""
    r = cliente.post(
        "/api/v1/eventos",
        json={
            "evento_id": str(uuid4()),
            "totem_id": "TOTEM-CCS-01",
            "tipo_ocorrencia": "seguranca",
            **extra,
        },
    )
    assert r.status_code == 201
    return r.json()


def entrar_em_panico(cliente, **extra) -> dict:
    r = cliente.post(
        "/api/v1/panico",
        json={"evento_id": str(uuid4()), "totem_id": "TOTEM-BC-02", **extra},
    )
    assert r.status_code == 201
    return r.json()


# ===========================================================================
# Lista
# ===========================================================================


def test_lista_vazia_quando_nao_ha_chamados(cliente):
    r = cliente.get(LISTA)
    assert r.status_code == 200
    assert r.json() == []


def test_lista_traz_o_chamado_criado(cliente):
    criado = acionar(cliente)

    lista = cliente.get(LISTA).json()

    assert [c["chamado_id"] for c in lista] == [criado["chamado_id"]]


def test_mais_recentes_primeiro(cliente):
    """O painel mostra o topo da lista. Um chamado novo no fim da fila seria
    invisível justamente quando mais importa."""
    primeiro = acionar(cliente)
    segundo = acionar(cliente)

    lista = cliente.get(LISTA).json()

    assert [c["chamado_id"] for c in lista] == [
        segundo["chamado_id"],
        primeiro["chamado_id"],
    ]


# --- Filtros ----------------------------------------------------------------


def test_filtro_por_tipo(cliente):
    acionar(cliente, tipo_ocorrencia="seguranca")
    acionar(cliente, tipo_ocorrencia="ouvidoria")

    lista = cliente.get(f"{LISTA}?tipo=ouvidoria").json()

    assert len(lista) == 1
    assert lista[0]["tipo_ocorrencia"] == TipoOcorrencia.ouvidoria


def test_filtro_por_status(cliente):
    acionar(cliente)
    entrar_em_panico(cliente)

    lista = cliente.get(f"{LISTA}?status=alerta_ativo").json()

    assert len(lista) == 1
    assert lista[0]["status"] == StatusChamado.alerta_ativo


def test_filtro_por_gravidade(cliente):
    acionar(cliente, tipo_ocorrencia="seguranca")
    acionar(cliente, tipo_ocorrencia="ouvidoria")

    lista = cliente.get(f"{LISTA}?gravidade=orientacao").json()

    assert len(lista) == 1
    assert lista[0]["gravidade"] == Gravidade.orientacao


def test_filtros_combinados(cliente):
    """O caso de uso real do painel: "o que é de segurança e ainda não foi
    reconhecido?"."""
    acionar(cliente, tipo_ocorrencia="seguranca")
    acionar(cliente, tipo_ocorrencia="ouvidoria")
    entrar_em_panico(cliente)

    lista = cliente.get(f"{LISTA}?tipo=seguranca&status=alerta_ativo").json()

    assert len(lista) == 1
    assert lista[0]["origem_acionamento"] == "panico"


def test_filtros_que_nao_casam_devolvem_vazio(cliente):
    acionar(cliente, tipo_ocorrencia="ouvidoria")
    assert cliente.get(f"{LISTA}?tipo=ouvidoria&gravidade=risco_imediato").json() == []


@pytest.mark.parametrize(
    "consulta",
    [
        "tipo=incendio",
        "status=reconhecidos",  # plural, o erro de digitação plausível
        "gravidade=grave",
        "status=RECONHECIDO",
    ],
)
def test_filtro_invalido_e_rejeitado(cliente, consulta):
    """**422, não lista vazia.** A diferença importa: vazio por causa de um erro
    de digitação diria ao operador que não há chamados — falso negativo num
    painel de emergência."""
    acionar(cliente)
    assert cliente.get(f"{LISTA}?{consulta}").status_code == 422


def test_sem_filtro_traz_tudo(cliente):
    acionar(cliente, tipo_ocorrencia="seguranca")
    acionar(cliente, tipo_ocorrencia="ouvidoria")
    entrar_em_panico(cliente)

    assert len(cliente.get(LISTA).json()) == 3


# --- O contorno do contrato -------------------------------------------------

CAMPOS_DA_LISTA = {
    "chamado_id",
    "totem_id",
    "tipo_ocorrencia",
    "modo",
    "origem_acionamento",
    "gravidade",
    "canal_roteado",
    "fallback",
    "status",
    "texto_livre",
    "observacao",
    "timestamp_local",
    "created_at",
    "updated_at",
    "acked_at",
}


def test_lista_tem_exatamente_os_campos_permitidos(cliente):
    """Lista de permitidos, não de proibidos. Uma coluna acrescentada ao schema
    amanhã não passa a sair pela API por esquecimento."""
    acionar(cliente, texto_livre=RELATO)

    assert set(cliente.get(LISTA).json()[0]) == CAMPOS_DA_LISTA


@pytest.mark.parametrize("campo", ["id", "evento_id", "triagem_json"])
def test_campos_internos_nao_saem_na_lista(cliente, campo):
    """`id` é rowid interno, `evento_id` é chave de idempotência do totem, e
    `triagem_json` sai no detalhe já decodificado."""
    acionar(cliente)
    assert campo not in cliente.get(LISTA).json()[0]


def test_relato_sai_para_o_painel(cliente):
    """A assimetria deliberada: a notificação externa nunca leva o relato
    (MVP-028), o painel leva. Quem atende precisa dele para decidir como
    responder — e é o que torna a autenticação do painel obrigatória."""
    acionar(cliente, texto_livre=RELATO)
    assert cliente.get(LISTA).json()[0]["texto_livre"] == RELATO


# ===========================================================================
# Detalhe
# ===========================================================================


def test_detalhe_traz_o_chamado(cliente):
    criado = acionar(cliente, texto_livre=RELATO)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert detalhe["chamado_id"] == criado["chamado_id"]
    assert detalhe["texto_livre"] == RELATO


def test_detalhe_traz_as_notificacoes(cliente):
    criado = acionar(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert [n["canal"] for n in detalhe["notificacoes"]] == ["csv"]
    assert detalhe["notificacoes"][0]["sucesso"] is True


def test_detalhe_do_panico_traz_os_dois_canais(cliente):
    criado = entrar_em_panico(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert sorted(n["canal"] for n in detalhe["notificacoes"]) == [
        "csv",
        "sala_lilas",
    ]


def test_notificacao_traz_o_nome_legivel(cliente):
    criado = acionar(cliente)
    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()
    assert detalhe["notificacoes"][0]["nome"] == "CSV / PREUNI"


def test_detalhe_traz_os_estados(cliente):
    """A história do chamado: é o que permite responder "o que aconteceu naquela
    noite" depois."""
    criado = acionar(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    transicoes = [(e["de"], e["para"]) for e in detalhe["estados"]]
    assert transicoes == [
        (None, StatusChamado.roteado),
        (StatusChamado.roteado, StatusChamado.notificado),
    ]


def test_detalhe_traz_a_triagem_decodificada(cliente):
    """Objeto, não string de JSON dentro de JSON. É o registro de auditoria do
    merge — o que responde "por que este chamado foi para o SAMU?"."""
    criado = acionar(cliente, texto_livre="estou desmaiando, socorro")

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert isinstance(detalhe["triagem"], dict)
    assert detalhe["triagem"]["trilha_escolhida"] == "seguranca"
    assert detalhe["tipo_ocorrencia"] == TipoOcorrencia.saude


def test_panico_nao_tem_triagem(cliente):
    """Pânico não passa por triagem de texto — `null` aqui é a verdade, não
    dado faltando."""
    criado = entrar_em_panico(cliente)
    assert cliente.get(f"{LISTA}/{criado['chamado_id']}").json()["triagem"] is None


def test_detalhe_e_a_lista_mais_tres_campos(cliente):
    criado = acionar(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert set(detalhe) == CAMPOS_DA_LISTA | {"triagem", "notificacoes", "estados"}


def test_id_inexistente_e_404(cliente):
    r = cliente.get(f"{LISTA}/CALL-2026-999999")
    assert r.status_code == 404
    assert "detail" in r.json()


@pytest.mark.parametrize(
    "identificador",
    [
        "CALL-'; DROP TABLE chamados;--",
        "' OR '1'='1",
        "%2e%2e%2fetc",
        "   ",
    ],
)
def test_identificador_hostil_e_404_sem_efeito(cliente, identificador):
    """O `chamado_id` vem da URL e entra numa consulta. A consulta é
    parametrizada (`db.py` não monta SQL com interpolação), então o caso
    hostil é só um id que não existe.

    A segunda asserção é o que dá valor ao teste: se a injeção tivesse
    funcionado, a listagem depois falharia ou voltaria vazia.
    """
    acionar(cliente)

    assert cliente.get(f"{LISTA}/{identificador}").status_code == 404
    assert len(cliente.get(LISTA).json()) == 1


# ===========================================================================
# O contato institucional não sai da API
# ===========================================================================


def test_destino_sai_mascarado(cliente):
    """Os últimos dígitos bastam para o operador conferir qual número foi
    usado."""
    criado = acionar(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert detalhe["notificacoes"][0]["destino"] == "…0001"


def test_contato_completo_nao_aparece_no_detalhe(cliente):
    """Se a autenticação do painel atrasar ou for cortada (MVP-040 é P1), uma
    rota de leitura aberta não pode ser o caminho para enumerar os contatos
    institucionais de toda a universidade."""
    criado = entrar_em_panico(cliente)

    resposta = cliente.get(f"{LISTA}/{criado['chamado_id']}").text

    assert CONTATO_CSV not in resposta
    assert CONTATO_LILAS not in resposta


def test_contato_completo_continua_no_banco(cliente):
    """A informação não é perdida, só não sai pela API."""
    criado = acionar(cliente)
    assert db.listar_notificacoes(criado["chamado_id"])[0]["destino"] == CONTATO_CSV


def test_mensagem_notificada_nao_carrega_o_relato(cliente):
    """A garantia da MVP-028, verificada do outro lado: o que foi enviado está
    gravado, e continua sem o relato."""
    criado = acionar(cliente, texto_livre=RELATO)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert RELATO not in detalhe["notificacoes"][0]["mensagem"]
    assert criado["chamado_id"] in detalhe["notificacoes"][0]["mensagem"]


def test_escalonamento_marcado_no_detalhe(cliente):
    """Separa a decisão humana do encaminhamento automático. Nada do pânico é
    escalonamento — o sistema não robo-disca."""
    criado = entrar_em_panico(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert all(n["escalonamento"] is False for n in detalhe["notificacoes"])


# ===========================================================================
# Robustez da leitura
# ===========================================================================


def _corromper_triagem(chamado_id: str, valor: str) -> None:
    with db.conectar() as con:
        con.execute(
            "UPDATE chamados SET triagem_json = ? WHERE chamado_id = ?",
            (valor, chamado_id),
        )


@pytest.mark.parametrize("valor", ["{nao é json", "[1, 2, 3]", '"uma string"', "null"])
def test_triagem_ilegivel_nao_esconde_o_chamado(cliente, valor):
    """Perder informação diagnóstica é ruim; esconder do operador um chamado que
    ele precisa atender é pior. O chamado continua sendo servido, com
    `triagem: null`."""
    criado = acionar(cliente, texto_livre="socorro")
    _corromper_triagem(criado["chamado_id"], valor)

    r = cliente.get(f"{LISTA}/{criado['chamado_id']}")

    assert r.status_code == 200
    assert r.json()["triagem"] is None
    assert r.json()["gravidade"] == Gravidade.risco_imediato


def test_chamado_sem_notificacao_ainda_e_servido(cliente, monkeypatch):
    """Canal sem contato configurado: a notificação falha, mas o chamado existe e
    o operador precisa vê-lo — é justamente quando ele tem que ligar por fora."""
    monkeypatch.setattr(config, "_CONTATOS", {})
    criado = acionar(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert detalhe["status"] == StatusChamado.falha_notificacao
    assert detalhe["notificacoes"][0]["sucesso"] is False
    assert detalhe["notificacoes"][0]["destino"] == "(sem contato configurado)"


def test_muitos_chamados_respeitam_o_limite(cliente):
    """O painel carrega os 200 mais recentes — uma lista sem teto cresceria até
    travar o tablet."""
    for _ in range(5):
        acionar(cliente)

    lista = cliente.get(LISTA).json()

    assert len(lista) == 5
    assert len(cliente.get(LISTA).json()) <= db.LIMITE_LISTAGEM
