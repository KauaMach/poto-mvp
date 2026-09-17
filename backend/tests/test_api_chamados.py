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
from app.api import chamados as chamados_api
from app.hub import hub as hub_global
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


def test_detalhe_do_panico_traz_os_canais_acionados(cliente):
    """Um registro por canal interno configurado — hoje só o CSV (COR-001)."""
    criado = entrar_em_panico(cliente)

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()

    assert sorted(n["canal"] for n in detalhe["notificacoes"]) == ["csv"]


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


# ===========================================================================
# Ações do operador: ack e PATCH
# ===========================================================================


class PainelFalso:
    def __init__(self, quebrado: bool = False):
        self.quebrado = quebrado
        self.eventos: list[tuple[str, dict]] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, mensagem: dict) -> None:
        if self.quebrado:
            raise ConnectionResetError("painel morto")
        self.eventos.append((mensagem["evento"], mensagem["dados"]))

    def nomes(self) -> list[str]:
        return [nome for nome, _ in self.eventos]

    def ultimo(self, evento: str) -> dict:
        return [d for n, d in self.eventos if n == evento][-1]


@pytest.fixture(autouse=True)
def hub_limpo():
    yield
    hub_global._clientes.clear()


@pytest.fixture
async def painel():
    p = PainelFalso()
    await hub_global.connect(p)
    return p


# --- ACK --------------------------------------------------------------------


def test_ack_muda_para_reconhecido(cliente):
    criado = acionar(cliente)

    r = cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert r.status_code == 200
    assert r.json()["status"] == StatusChamado.reconhecido


def test_ack_grava_o_horario(cliente):
    """É de `acked_at` que sai a métrica de tempo até o reconhecimento."""
    criado = acionar(cliente)

    r = cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert r.json()["acked_at"] is not None


def test_ack_registra_a_transicao(cliente):
    criado = acionar(cliente)

    cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    estados = db.listar_estados(criado["chamado_id"])
    assert estados[-1] == {
        "de": StatusChamado.notificado,
        "para": StatusChamado.reconhecido,
        "created_at": estados[-1]["created_at"],
    }


def test_ack_de_panico_e_central_recebeu(cliente):
    """`alerta_ativo` não fecha **sozinho** — mas ACK não é sozinho, é a central
    dizendo "recebi". É o que a tela do totem mostra como "Central recebeu"."""
    criado = entrar_em_panico(cliente)
    assert criado["status"] == StatusChamado.alerta_ativo

    r = cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert r.json()["status"] == StatusChamado.reconhecido


def test_segundo_ack_nao_reescreve_o_horario(cliente):
    """Dois operadores clicando não é erro. Sobrescrever o `acked_at` original
    mascararia uma demora real."""
    criado = acionar(cliente)

    primeiro = cliente.post(f"{LISTA}/{criado['chamado_id']}/ack").json()
    segundo = cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert segundo.status_code == 200
    assert segundo.json()["acked_at"] == primeiro["acked_at"]


def test_segundo_ack_nao_duplica_a_transicao(cliente):
    """`estado_log` registra transições, não toques."""
    criado = acionar(cliente)

    cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")
    cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    reconhecimentos = [
        e
        for e in db.listar_estados(criado["chamado_id"])
        if e["para"] == StatusChamado.reconhecido
    ]
    assert len(reconhecimentos) == 1


def test_ack_de_chamado_inexistente_e_404(cliente):
    assert cliente.post(f"{LISTA}/CALL-2026-999999/ack").status_code == 404


async def test_ack_avisa_o_painel(cliente, painel):
    criado = acionar(cliente)

    cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert painel.ultimo("atualizado")["status"] == StatusChamado.reconhecido


async def test_painel_morto_nao_impede_o_ack(cliente):
    criado = acionar(cliente)
    await hub_global.connect(PainelFalso(quebrado=True))

    r = cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert r.status_code == 200
    assert db.obter_chamado(criado["chamado_id"])["status"] == (
        StatusChamado.reconhecido
    )


# --- PATCH ------------------------------------------------------------------


def test_patch_muda_o_status(cliente):
    criado = acionar(cliente)

    r = cliente.patch(
        f"{LISTA}/{criado['chamado_id']}", json={"status": "em_atendimento"}
    )

    assert r.status_code == 200
    assert r.json()["status"] == StatusChamado.em_atendimento


def test_patch_grava_a_observacao(cliente):
    criado = acionar(cliente)

    r = cliente.patch(
        f"{LISTA}/{criado['chamado_id']}", json={"observacao": "ligou, ninguém atendeu"}
    )

    assert r.json()["observacao"] == "ligou, ninguém atendeu"


def test_patch_aceita_os_dois_campos_juntos(cliente):
    criado = acionar(cliente)

    r = cliente.patch(
        f"{LISTA}/{criado['chamado_id']}",
        json={"status": "encerrado", "observacao": "resolvido no local"},
    )

    assert r.json()["status"] == StatusChamado.encerrado
    assert r.json()["observacao"] == "resolvido no local"


def test_patch_registra_a_transicao(cliente):
    criado = acionar(cliente)

    cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"status": "em_atendimento"})

    assert db.listar_estados(criado["chamado_id"])[-1]["para"] == (
        StatusChamado.em_atendimento
    )


def test_patch_so_de_observacao_nao_gera_transicao(cliente):
    """Anotar não é movimentar. `estado_log` é a história dos estados."""
    criado = acionar(cliente)
    antes = len(db.listar_estados(criado["chamado_id"]))

    cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"observacao": "anotação"})

    assert len(db.listar_estados(criado["chamado_id"])) == antes


def test_patch_com_o_mesmo_status_nao_duplica(cliente):
    criado = acionar(cliente)
    antes = len(db.listar_estados(criado["chamado_id"]))

    cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"status": "notificado"})

    assert len(db.listar_estados(criado["chamado_id"])) == antes


def test_patch_vazio_e_no_op(cliente):
    """Corpo vazio é PATCH válido: devolve o chamado como está.

    A comparação é contra o estado **no banco**, não contra a resposta de
    `/eventos`: aquela é montada antes da notificação em segundo plano
    (MVP-030), então já nasce defasada de propósito.
    """
    criado = acionar(cliente)
    antes = db.obter_chamado(criado["chamado_id"])
    estados_antes = db.listar_estados(criado["chamado_id"])

    r = cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={})

    assert r.status_code == 200
    assert r.json()["status"] == antes["status"]
    assert r.json()["observacao"] == antes["observacao"]
    assert db.listar_estados(criado["chamado_id"]) == estados_antes


@pytest.mark.parametrize("status", ["resolvido", "RECONHECIDO", "", "ack"])
def test_patch_com_status_invalido_e_422(cliente, status):
    criado = acionar(cliente)
    r = cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"status": status})
    assert r.status_code == 422


def test_patch_com_observacao_longa_demais_e_422(cliente):
    criado = acionar(cliente)
    r = cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"observacao": "a" * 2001})
    assert r.status_code == 422


def test_patch_de_chamado_inexistente_e_404(cliente):
    r = cliente.patch(f"{LISTA}/CALL-2026-999999", json={"status": "encerrado"})
    assert r.status_code == 404


async def test_patch_avisa_o_painel(cliente, painel):
    criado = acionar(cliente)

    cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"status": "encerrado"})

    assert painel.ultimo("atualizado")["status"] == StatusChamado.encerrado


# --- Julgamento humano não é restringido ------------------------------------


@pytest.mark.parametrize(
    "destino",
    [
        StatusChamado.cancelado,
        StatusChamado.encerrado,
        StatusChamado.alerta_ativo,
        StatusChamado.recebido,
    ],
)
def test_operador_pode_mover_para_qualquer_estado(cliente, destino):
    """**Não há máquina de estados, de propósito.**

    A regra que protege o sistema — nada rebaixa a proteção já concedida — vale
    para a *inferência automática*, não para o julgamento humano. O operador
    precisa poder cancelar um trote, encerrar um chamado resolvido por telefone
    ou reabrir um que voltou; uma tabela de transições permitidas travaria
    alguém no meio de uma emergência por um caso que ninguém previu.

    O que garante responsabilidade é o rastro, não a proibição.
    """
    criado = entrar_em_panico(cliente)

    r = cliente.patch(f"{LISTA}/{criado['chamado_id']}", json={"status": destino})

    assert r.status_code == 200
    assert r.json()["status"] == destino


def test_toda_movimentacao_fica_no_rastro(cliente):
    """A contrapartida de não restringir: `estado_log` é append-only por gatilho
    de banco (MVP-015), então o caminho inteiro é reconstruível."""
    criado = entrar_em_panico(cliente)
    cid = criado["chamado_id"]

    cliente.post(f"{LISTA}/{cid}/ack")
    cliente.patch(f"{LISTA}/{cid}", json={"status": "em_atendimento"})
    cliente.patch(f"{LISTA}/{cid}", json={"status": "encerrado"})

    assert [e["para"] for e in db.listar_estados(cid)] == [
        StatusChamado.alerta_ativo,
        StatusChamado.reconhecido,
        StatusChamado.em_atendimento,
        StatusChamado.encerrado,
    ]


def test_gravidade_nunca_muda_por_acao_do_operador(cliente):
    """O `ChamadoUpdate` não tem campo de gravidade, e é intencional: o
    encaminhamento foi decidido pelo merge protetivo. Mover o estado é
    trabalho do operador; redefinir o risco não."""
    criado = acionar(cliente, tipo_ocorrencia="seguranca")

    r = cliente.patch(
        f"{LISTA}/{criado['chamado_id']}",
        json={"status": "encerrado", "gravidade": "orientacao"},
    )

    assert r.json()["gravidade"] == Gravidade.risco_imediato
    assert db.obter_chamado(criado["chamado_id"])["gravidade"] == (
        Gravidade.risco_imediato
    )


# ===========================================================================
# O WebSocket e o REST falam a mesma língua
# ===========================================================================


async def test_payload_do_broadcast_tem_o_formato_do_rest(cliente, painel):
    """A propriedade que `para_painel()` existe para garantir.

    Sem ela o `broadcast` mandaria a linha crua do SQLite — com `id`,
    `evento_id` e `triagem_json` — enquanto `GET /chamados` manda `ChamadoOut`.
    O painel teria que lidar com dois formatos para a mesma coisa, e o tipo
    declarado no frontend mentiria sobre um dos dois.
    """
    criado = acionar(cliente, texto_livre=RELATO)

    cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    por_ws = painel.ultimo("atualizado")
    por_rest = cliente.get(f"{LISTA}").json()[0]
    assert por_ws == por_rest


async def test_broadcast_nao_carrega_campos_internos(cliente, painel):
    """De quebra, o payload do WebSocket herda a lista de campos permitidos — é
    a rota com mais chance de ficar sem autenticação se a MVP-040 atrasar."""
    acionar(cliente, texto_livre=RELATO)

    novo = painel.ultimo("novo_chamado")

    assert set(novo) == CAMPOS_DA_LISTA


async def test_broadcast_de_novo_chamado_e_de_atualizado_tem_o_mesmo_formato(
    cliente, painel
):
    criado = acionar(cliente)

    cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")

    assert set(painel.ultimo("novo_chamado")) == set(painel.ultimo("atualizado"))


async def test_broadcast_do_panico_tambem(cliente, painel):
    entrar_em_panico(cliente)
    assert set(painel.ultimo("novo_chamado")) == CAMPOS_DA_LISTA


# ===========================================================================
# MVP-034 — Escalonamento manual
# ===========================================================================


def escalonar(cliente, chamado_id, canal):
    return cliente.post(f"{LISTA}/{chamado_id}/escalonar", json={"canal": canal})


@pytest.fixture
def contatos_do_estado(monkeypatch):
    monkeypatch.setattr(
        config,
        "_CONTATOS",
        {
            "csv": CONTATO_CSV,
            "sala_lilas": CONTATO_LILAS,
            "samu_192": "192",
            "pm_190": "190",
        },
    )


def test_escalonar(cliente, contatos_do_estado):
    """O teste que a MVP-034 nomeia."""
    criado = entrar_em_panico(cliente)

    r = escalonar(cliente, criado["chamado_id"], "samu_192")

    assert r.status_code == 200
    assert r.json() == {
        "canal": "samu_192",
        "nome": "SAMU",
        "sucesso": True,
        "detalhe": r.json()["detalhe"],
    }


def test_escalonamento_e_gravado_como_humano(cliente, contatos_do_estado):
    """`escalonamento=1` separa para sempre, no histórico do chamado, o que o
    sistema decidiu do que uma pessoa decidiu."""
    criado = entrar_em_panico(cliente)

    escalonar(cliente, criado["chamado_id"], "samu_192")

    registros = db.listar_notificacoes(criado["chamado_id"])
    humanos = [n for n in registros if n["escalonamento"]]
    assert [n["canal"] for n in humanos] == ["samu_192"]


def test_acionamento_automatico_continua_marcado_como_automatico(
    cliente, contatos_do_estado
):
    """A contrapartida: os canais internos do pânico não viram escalonamento."""
    criado = entrar_em_panico(cliente)

    escalonar(cliente, criado["chamado_id"], "pm_190")

    registros = db.listar_notificacoes(criado["chamado_id"])
    automaticos = {n["canal"] for n in registros if not n["escalonamento"]}
    assert automaticos == set(config.CANAIS_INTERNOS)


@pytest.mark.parametrize("canal", ["pm_190", "samu_192", "bombeiros_193", "central_180"])
def test_as_quatro_autoridades_sao_aceitas(cliente, canal):
    criado = entrar_em_panico(cliente)
    assert escalonar(cliente, criado["chamado_id"], canal).status_code == 200


@pytest.mark.parametrize("canal", ["csv", "sala_lilas", "sapsi", "ouvidoria"])
def test_canal_interno_e_rejeitado(cliente, canal):
    """Um canal interno acionado por aqui entraria no histórico marcado como
    decisão humana de escalonamento, contaminando a única distinção que o
    registro faz entre o que o sistema decidiu e o que uma pessoa decidiu."""
    criado = entrar_em_panico(cliente)
    assert escalonar(cliente, criado["chamado_id"], canal).status_code == 422


@pytest.mark.parametrize("canal", ["batman", "", "PM_190", "190"])
def test_canal_desconhecido_e_rejeitado(cliente, canal):
    criado = entrar_em_panico(cliente)
    assert escalonar(cliente, criado["chamado_id"], canal).status_code == 422


def test_canal_rejeitado_nao_grava_nada(cliente, contatos_do_estado):
    criado = entrar_em_panico(cliente)
    antes = len(db.listar_notificacoes(criado["chamado_id"]))

    escalonar(cliente, criado["chamado_id"], "csv")

    assert len(db.listar_notificacoes(criado["chamado_id"])) == antes


def test_escalonar_chamado_inexistente_e_404(cliente):
    assert escalonar(cliente, "CALL-2026-999999", "samu_192").status_code == 404


def test_escalonar_nao_rebaixa_alerta_ativo(cliente, contatos_do_estado):
    """Chamar a PM não resolve a emergência. Rebaixar o alerta aqui apagaria da
    tela do totem justamente o estado que mantém o cronômetro correndo."""
    criado = entrar_em_panico(cliente)

    escalonar(cliente, criado["chamado_id"], "pm_190")

    assert db.obter_chamado(criado["chamado_id"])["status"] == (
        StatusChamado.alerta_ativo
    )


def test_escalonar_nao_muda_status_nenhum(cliente, contatos_do_estado):
    criado = acionar(cliente)
    antes = db.obter_chamado(criado["chamado_id"])["status"]

    escalonar(cliente, criado["chamado_id"], "samu_192")

    assert db.obter_chamado(criado["chamado_id"])["status"] == antes


def test_escalonar_sem_contato_configurado_ainda_registra(cliente, monkeypatch):
    """Sem contato o sistema não tem para onde mandar — mas a decisão humana
    aconteceu e precisa constar. É o registro de que alguém acionou a PM às
    3h12, ainda que por telefone próprio."""
    monkeypatch.setattr(config, "_CONTATOS", {"csv": CONTATO_CSV})
    criado = acionar(cliente)

    r = escalonar(cliente, criado["chamado_id"], "pm_190")

    assert r.status_code == 200
    assert r.json()["sucesso"] is False
    humanos = [n for n in db.listar_notificacoes(criado["chamado_id"]) if n["escalonamento"]]
    assert [n["canal"] for n in humanos] == ["pm_190"]


def test_escalonar_duas_vezes_registra_duas(cliente, contatos_do_estado):
    """Ao contrário do acionamento, escalonar **não** é idempotente: duas
    tentativas de chamar o SAMU são dois fatos distintos no histórico."""
    criado = entrar_em_panico(cliente)

    escalonar(cliente, criado["chamado_id"], "samu_192")
    escalonar(cliente, criado["chamado_id"], "samu_192")

    humanos = [n for n in db.listar_notificacoes(criado["chamado_id"]) if n["escalonamento"]]
    assert len(humanos) == 2


def test_nenhum_caminho_automatico_aciona_o_estado(cliente, contatos_do_estado):
    """A garantia de "não robo-disca", verificada de fora: um acionamento e um
    pânico, com contatos do estado configurados e prontos para receber, e
    nenhum dos dois toca em `CANAIS_ESTADO`."""
    a = acionar(cliente, texto_livre="socorro, estou sangrando")
    b = entrar_em_panico(cliente)

    acionados = {
        n["canal"]
        for cid in (a["chamado_id"], b["chamado_id"])
        for n in db.listar_notificacoes(cid)
    }
    assert acionados.isdisjoint(config.CANAIS_ESTADO)


def test_escalonamento_aparece_no_detalhe(cliente, contatos_do_estado):
    criado = entrar_em_panico(cliente)

    escalonar(cliente, criado["chamado_id"], "central_180")

    detalhe = cliente.get(f"{LISTA}/{criado['chamado_id']}").json()
    humano = [n for n in detalhe["notificacoes"] if n["escalonamento"]][0]
    assert humano["canal"] == "central_180"
    assert humano["nome"] == "Central de Atendimento à Mulher"


# ===========================================================================
# MVP-035 — WS /ws
# ===========================================================================

WS = "/api/v1/ws"

PRAZO_WS = 2.0


def receber(ws, prazo: float = PRAZO_WS) -> dict:
    """Recebe uma mensagem do WebSocket **com prazo**.

    O `receive_json` do `TestClient` bloqueia indefinidamente quando nada
    chega. Com ele, um endpoint que deixa de enviar uma mensagem **pendura a
    suíte** em vez de reprovar — e foi exatamente o que aconteceu na verificação
    por mutação: ao remover o `conectado` do `/ws`, a rodada travou em vez de
    acusar o defeito.

    O prazo usa o mesmo portal do anyio que o `TestClient` usa por dentro, o
    que evita deixar thread pendurada quando o teste falha.
    """
    import json

    import anyio

    async def ler(rx):
        with anyio.fail_after(prazo):
            return await rx.receive()

    try:
        mensagem = ws.portal.call(ler, ws._send_rx)
    except TimeoutError:
        raise AssertionError(
            f"nenhuma mensagem no WebSocket em {prazo}s — o endpoint não enviou"
        ) from None

    if mensagem["type"] == "websocket.close":
        raise AssertionError(f"WebSocket fechado pelo servidor: {mensagem}")
    return json.loads(mensagem["text"])


def test_ws_envia_conectado_ao_abrir(cliente):
    """Primeira mensagem, antes de qualquer evento. É o que diz ao painel que o
    canal está vivo — sem ela, uma tela em branco pode ser "nada aconteceu" ou
    "não conectei", e as duas coisas parecem idênticas."""
    with cliente.websocket_connect(WS) as ws:
        assert receber(ws)["evento"] == "conectado"


def test_conectado_informa_quantos_paineis(cliente):
    """Permite a tela mostrar "2 operadores conectados" — e perceber que
    ninguém mais está olhando."""
    with cliente.websocket_connect(WS) as ws:
        dados = receber(ws)["dados"]
    assert dados["paineis"] == 1
    assert "servidor" in dados


def test_ws_recebe_novo_chamado(cliente):
    with cliente.websocket_connect(WS) as ws:
        receber(ws)  # conectado
        criado = acionar(cliente)
        mensagem = receber(ws)

    assert mensagem["evento"] == "novo_chamado"
    assert mensagem["dados"]["chamado_id"] == criado["chamado_id"]


def test_ws_recebe_atualizado(cliente):
    criado = acionar(cliente)

    with cliente.websocket_connect(WS) as ws:
        receber(ws)  # conectado
        cliente.post(f"{LISTA}/{criado['chamado_id']}/ack")
        mensagem = receber(ws)

    assert mensagem["evento"] == "atualizado"
    assert mensagem["dados"]["status"] == StatusChamado.reconhecido


def test_ws_recebe_o_relato(cliente):
    """O painel está dentro da fronteira de confiança e precisa do relato para
    decidir como responder. É o que torna a autenticação desta rota
    obrigatória, não opcional (MVP-040)."""
    with cliente.websocket_connect(WS) as ws:
        receber(ws)
        acionar(cliente, texto_livre=RELATO)
        assert receber(ws)["dados"]["texto_livre"] == RELATO


def test_dois_paineis_recebem_o_mesmo_evento(cliente):
    with cliente.websocket_connect(WS) as a, cliente.websocket_connect(WS) as b:
        receber(a)
        receber(b)
        acionar(cliente)
        assert receber(a)["evento"] == "novo_chamado"
        assert receber(b)["evento"] == "novo_chamado"


def test_ws_registra_e_remove_do_hub(cliente):
    """Desconexão não vaza memória: o critério da MVP-035."""
    assert len(hub_global) == 0
    with cliente.websocket_connect(WS):
        assert len(hub_global) == 1
    assert len(hub_global) == 0


def test_desconexao_nao_derruba_o_servidor(cliente):
    for _ in range(3):
        with cliente.websocket_connect(WS) as ws:
            receber(ws)

    assert cliente.get("/api/v1/health").status_code == 200
    assert len(hub_global) == 0


def test_acionamento_funciona_depois_de_painel_sair(cliente):
    with cliente.websocket_connect(WS) as ws:
        receber(ws)

    assert acionar(cliente)["chamado_id"].startswith("CALL-")


def test_mensagem_do_cliente_e_ignorada(cliente):
    """Este canal é de leitura. Aceitar comandos por aqui criaria uma via de
    escrita sem as validações dos endpoints REST — nem contrato, nem 422, nem
    o 404 que distingue um chamado inexistente.

    A **ordem** aqui é o que dá valor ao teste, e a primeira versão errou nela:
    o comando era enviado antes de o chamado existir, então um endpoint que
    obedecesse não teria o que reconhecer e o teste passaria de graça.
    Verificado por mutação. Agora o chamado existe e o comando cita o id real.
    """
    criado = acionar(cliente)
    assert db.obter_chamado(criado["chamado_id"])["acked_at"] is None

    with cliente.websocket_connect(WS) as ws:
        receber(ws)  # conectado
        ws.send_text(f'{{"evento": "ack", "chamado_id": "{criado["chamado_id"]}"}}')
        ws.send_text('{"evento": "patch", "status": "encerrado"}')

        # Ida e volta pelo mesmo canal: quando este evento chega, o laço do
        # endpoint já consumiu os dois textos acima.
        outro = acionar(cliente)
        assert receber(ws)["dados"]["chamado_id"] == outro["chamado_id"]

    persistido = db.obter_chamado(criado["chamado_id"])
    assert persistido["acked_at"] is None
    assert persistido["status"] != StatusChamado.encerrado


def test_ping_mantem_a_conexao_viva(cliente, monkeypatch):
    """O uvicorn já manda ping de **protocolo**, mas o navegador não expõe isso
    ao JavaScript: a API WebSocket não avisa sobre pong. Sem um ping de
    aplicação, o painel não distingue "nada aconteceu nos últimos dez minutos"
    de "a conexão morreu e eu não sei"."""
    monkeypatch.setattr(chamados_api, "INTERVALO_PING", 0.05)

    with cliente.websocket_connect(WS) as ws:
        assert receber(ws)["evento"] == "conectado"
        assert receber(ws)["evento"] == "ping"
        assert receber(ws)["evento"] == "ping"


def test_pingador_para_quando_o_painel_sai(cliente, monkeypatch):
    """Sem cancelar o pingador, cada painel que se desconecta deixa uma tarefa
    eterna tentando escrever num socket fechado."""
    monkeypatch.setattr(chamados_api, "INTERVALO_PING", 0.05)

    with cliente.websocket_connect(WS) as ws:
        receber(ws)
        receber(ws)  # ping

    assert len(hub_global) == 0
    assert cliente.get("/api/v1/health").status_code == 200


def test_ping_nao_atropela_um_evento(cliente, monkeypatch):
    """Os dois remetentes concorrentes do mesmo socket. O cadeado do hub
    serializa as escritas; sem ele os frames se intercalariam e o JSON chegaria
    corrompido — e é este teste que perceberia, porque `receive_json` falharia
    ao decodificar."""
    monkeypatch.setattr(chamados_api, "INTERVALO_PING", 0.01)

    with cliente.websocket_connect(WS) as ws:
        receber(ws)
        for _ in range(5):
            acionar(cliente)
        eventos = [receber(ws)["evento"] for _ in range(10)]

    assert set(eventos) <= {"ping", "novo_chamado", "atualizado"}
    assert "novo_chamado" in eventos
