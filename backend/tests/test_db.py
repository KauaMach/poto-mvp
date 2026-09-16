"""Criação de chamados e idempotência.

A idempotência aqui não é detalhe de implementação: é o que permite a fila
offline do totem drenar sem medo. Se ela falhar, uma emergência vira dois
alarmes e a central despacha duas equipes.
"""

from __future__ import annotations

import json
import threading
from uuid import uuid4

import pytest

from app import config, db
from app.models import Modo, StatusChamado, TipoOcorrencia
from app.triagem.roteador import rotear


@pytest.fixture
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    db.init_db()


def evento(**extra) -> dict:
    return {
        "evento_id": str(uuid4()),
        "totem_id": "TOTEM-CCS-01",
        "tipo_ocorrencia": TipoOcorrencia.seguranca,
        "modo": Modo.normal,
        "origem_acionamento": "touch",
        **extra,
    }


@pytest.fixture
def roteamento():
    return rotear(TipoOcorrencia.seguranca)


# --- Idempotência -----------------------------------------------------------


def test_idempotencia(banco, roteamento):
    """O critério de aceitação da MVP-015: reenviar o mesmo evento devolve o
    chamado existente em vez de criar um segundo."""
    ev = evento()

    primeiro = db.criar_chamado(ev, roteamento)
    assert primeiro["_duplicado"] is False

    for _ in range(3):
        repetido = db.criar_chamado(ev, roteamento)
        assert repetido["_duplicado"] is True
        assert repetido["chamado_id"] == primeiro["chamado_id"]

    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM chamados").fetchone()[0] == 1


def test_idempotencia_sob_concorrencia(banco, roteamento):
    """O caminho rápido (consulta antes de inserir) tem uma janela de corrida.
    Quem fecha de verdade é a constraint UNIQUE — este teste prova isso com 12
    threads partindo juntas, que é o dreno da fila offline em paralelo."""
    ev = evento()
    resultados: list = []
    barreira = threading.Barrier(12)

    def tentar():
        barreira.wait()
        try:
            resultados.append(db.criar_chamado(dict(ev), roteamento))
        except Exception as erro:  # noqa: BLE001 — o teste quer ver qualquer falha
            resultados.append(erro)

    threads = [threading.Thread(target=tentar) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not [r for r in resultados if isinstance(r, Exception)]
    assert len([r for r in resultados if not r["_duplicado"]]) == 1
    assert len([r for r in resultados if r["_duplicado"]]) == 11

    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM chamados").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM estado_log").fetchone()[0] == 1


def test_eventos_distintos_criam_chamados_distintos(banco, roteamento):
    a = db.criar_chamado(evento(), roteamento)
    b = db.criar_chamado(evento(), roteamento)
    assert a["chamado_id"] != b["chamado_id"]


# --- Protocolo --------------------------------------------------------------


def test_formato_do_protocolo(banco, roteamento):
    from datetime import UTC, datetime

    c = db.criar_chamado(evento(), roteamento)
    ano = datetime.now(UTC).year
    assert c["chamado_id"] == f"CALL-{ano}-000001"


def test_protocolos_sao_sequenciais(banco, roteamento):
    ids = [db.criar_chamado(evento(), roteamento)["chamado_id"] for _ in range(3)]
    assert [i.split("-")[-1] for i in ids] == ["000001", "000002", "000003"]


def test_nenhum_marcador_temporario_sobrevive(banco, roteamento):
    """O protocolo depende do rowid, que só existe após o INSERT. O marcador
    usado nesse intervalo não pode vazar para o banco."""
    db.criar_chamado(evento(), roteamento)
    with db.conectar() as con:
        sobrou = con.execute(
            "SELECT count(*) FROM chamados WHERE chamado_id LIKE 'pendente:%'"
        ).fetchone()[0]
    assert sobrou == 0


# --- Conteúdo gravado -------------------------------------------------------


def test_grava_texto_livre(banco, roteamento):
    c = db.criar_chamado(evento(texto_livre="tem um homem me seguindo"), roteamento)
    assert c["texto_livre"] == "tem um homem me seguindo"


def test_grava_a_decisao_da_triagem_para_auditoria(banco, roteamento):
    triagem = {"fonte": "classificador", "confianca": 0.83, "tipo": "seguranca"}
    c = db.criar_chamado(evento(), roteamento, triagem)
    assert json.loads(c["triagem_json"]) == triagem


def test_triagem_ausente_fica_nula(banco, roteamento):
    """O pânico não passa por triagem de texto."""
    c = db.criar_chamado(evento(), roteamento, None)
    assert c["triagem_json"] is None


def test_grava_o_roteamento(banco, roteamento):
    c = db.criar_chamado(evento(), roteamento)
    assert c["canal_roteado"] == "csv"
    assert c["fallback"] == "pm_190"
    assert c["gravidade"] == "risco_imediato"


def test_enums_sao_gravados_como_valor(banco, roteamento):
    """StrEnum garante que o banco recebe 'seguranca', não
    'TipoOcorrencia.seguranca'."""
    c = db.criar_chamado(evento(), roteamento)
    assert c["tipo_ocorrencia"] == "seguranca"
    assert c["modo"] == "normal"


def test_trilha_mulher_preserva_o_modo_discreto(banco):
    r = rotear(TipoOcorrencia.mulher)
    c = db.criar_chamado(
        evento(tipo_ocorrencia=TipoOcorrencia.mulher, modo=Modo.discreto), r
    )
    assert c["modo"] == "discreto"
    assert c["canal_roteado"] in {"sala_lilas", "central_180"}


# --- Estado inicial ---------------------------------------------------------


def test_status_inicial_padrao_e_roteado(banco, roteamento):
    c = db.criar_chamado(evento(), roteamento)
    assert c["status"] == StatusChamado.roteado


def test_status_inicial_pode_ser_sobrescrito(banco, roteamento):
    """O pânico nasce em alerta_ativo, que é persistente."""
    c = db.criar_chamado(evento(), roteamento, status=StatusChamado.alerta_ativo)
    assert c["status"] == "alerta_ativo"


def test_registra_o_estado_inicial_no_log(banco, roteamento):
    c = db.criar_chamado(evento(), roteamento)
    with db.conectar() as con:
        linhas = [
            dict(x)
            for x in con.execute(
                "SELECT de, para FROM estado_log WHERE chamado_id = ?",
                (c["chamado_id"],),
            )
        ]
    assert linhas == [{"de": None, "para": "roteado"}]


def test_reenvio_nao_duplica_o_estado_log(banco, roteamento):
    ev = evento()
    c = db.criar_chamado(ev, roteamento)
    db.criar_chamado(ev, roteamento)
    with db.conectar() as con:
        n = con.execute(
            "SELECT count(*) FROM estado_log WHERE chamado_id = ?", (c["chamado_id"],)
        ).fetchone()[0]
    assert n == 1


# --- Busca ------------------------------------------------------------------


def test_busca_por_evento(banco, roteamento):
    ev = evento()
    criado = db.criar_chamado(ev, roteamento)
    achado = db.buscar_por_evento(ev["evento_id"])
    assert achado["chamado_id"] == criado["chamado_id"]


def test_busca_por_evento_inexistente(banco):
    assert db.buscar_por_evento(str(uuid4())) is None


def test_timestamps_sao_preenchidos(banco, roteamento):
    c = db.criar_chamado(evento(), roteamento)
    assert c["created_at"] and c["updated_at"]
    assert c["acked_at"] is None


def test_timestamp_local_do_tablet_e_preservado(banco, roteamento):
    c = db.criar_chamado(evento(timestamp_local="2026-09-16T10:00:00-03:00"), roteamento)
    assert c["timestamp_local"] == "2026-09-16T10:00:00-03:00"


# ===========================================================================
# Consulta e atualização (MVP-016)
# ===========================================================================


@pytest.fixture
def tres_chamados(banco):
    """Um de cada trilha, criados nesta ordem."""
    criados = {}
    for tipo in (TipoOcorrencia.seguranca, TipoOcorrencia.mulher, TipoOcorrencia.ouvidoria):
        criados[tipo.value] = db.criar_chamado(
            evento(tipo_ocorrencia=tipo), rotear(tipo)
        )
    return criados


# --- obter ------------------------------------------------------------------


def test_obter_chamado(tres_chamados):
    alvo = tres_chamados["mulher"]
    assert db.obter_chamado(alvo["chamado_id"])["chamado_id"] == alvo["chamado_id"]


def test_obter_chamado_inexistente(banco):
    assert db.obter_chamado("CALL-2026-999999") is None


# --- listar -----------------------------------------------------------------


def test_lista_mais_recentes_primeiro(tres_chamados):
    ids = [c["chamado_id"] for c in db.listar_chamados()]
    assert ids == sorted(ids, reverse=True)


def test_lista_vazia_quando_nao_ha_chamados(banco):
    assert db.listar_chamados() == []


@pytest.mark.parametrize(
    "filtro,valor,esperado",
    [
        ("tipo", "mulher", 1),
        ("tipo", "seguranca", 1),
        ("tipo", "saude", 0),
        ("status", "roteado", 3),
        ("status", "encerrado", 0),
        ("gravidade", "risco_imediato", 1),
        ("gravidade", "orientacao", 1),
    ],
)
def test_filtros_da_listagem(tres_chamados, filtro, valor, esperado):
    assert len(db.listar_chamados(**{filtro: valor})) == esperado


def test_filtros_combinam(tres_chamados):
    assert len(db.listar_chamados(tipo="seguranca", status="roteado")) == 1
    assert len(db.listar_chamados(tipo="seguranca", status="encerrado")) == 0


def test_listagem_respeita_o_limite(banco):
    for _ in range(5):
        db.criar_chamado(evento(), rotear(TipoOcorrencia.seguranca))
    assert len(db.listar_chamados(limite=2)) == 2


# --- atualizar --------------------------------------------------------------


def test_atualiza_status(tres_chamados):
    alvo = tres_chamados["seguranca"]
    atualizado = db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.notificado)
    assert atualizado["status"] == "notificado"


def test_atualizar_mexe_no_updated_at(tres_chamados):
    alvo = tres_chamados["seguranca"]
    atualizado = db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.notificado)
    assert atualizado["updated_at"] >= alvo["updated_at"]


def test_atualiza_observacao_sem_mexer_no_status(tres_chamados):
    alvo = tres_chamados["seguranca"]
    atualizado = db.atualizar_chamado(alvo["chamado_id"], observacao="sem resposta do CSV")
    assert atualizado["observacao"] == "sem resposta do CSV"
    assert atualizado["status"] == alvo["status"]


def test_atualizar_chamado_inexistente_devolve_none(banco):
    assert db.atualizar_chamado("CALL-2026-999999", status="encerrado") is None


def test_toda_troca_de_status_deixa_rastro(tres_chamados):
    """Não existe mudar o estado sem registrar a transição."""
    alvo = tres_chamados["seguranca"]
    db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.notificado)
    db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.em_atendimento)
    db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.encerrado)

    with db.conectar() as con:
        trilha = [
            (r["de"], r["para"])
            for r in con.execute(
                "SELECT de, para FROM estado_log WHERE chamado_id = ? ORDER BY id",
                (alvo["chamado_id"],),
            )
        ]
    assert trilha == [
        (None, "roteado"),
        ("roteado", "notificado"),
        ("notificado", "em_atendimento"),
        ("em_atendimento", "encerrado"),
    ]


def test_reescrever_o_mesmo_status_nao_gera_linha(tres_chamados):
    """O log registra transições, não toques."""
    alvo = tres_chamados["seguranca"]
    db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.roteado)

    with db.conectar() as con:
        n = con.execute(
            "SELECT count(*) FROM estado_log WHERE chamado_id = ?",
            (alvo["chamado_id"],),
        ).fetchone()[0]
    assert n == 1


# --- ack --------------------------------------------------------------------


def test_ack_marca_reconhecido_e_carimba_o_horario(tres_chamados):
    alvo = tres_chamados["seguranca"]
    ack = db.ack_chamado(alvo["chamado_id"])
    assert ack["status"] == "reconhecido"
    assert ack["acked_at"] is not None


def test_segundo_ack_nao_reescreve_o_horario_original(tres_chamados):
    """`acked_at` alimenta a métrica de tempo até o reconhecimento.
    Sobrescrever mascararia uma demora real."""
    alvo = tres_chamados["seguranca"]
    primeiro = db.ack_chamado(alvo["chamado_id"])
    db.atualizar_chamado(alvo["chamado_id"], status=StatusChamado.em_atendimento)
    segundo = db.ack_chamado(alvo["chamado_id"])
    assert segundo["acked_at"] == primeiro["acked_at"]


def test_ack_em_chamado_inexistente_devolve_none(banco):
    assert db.ack_chamado("CALL-2026-999999") is None
