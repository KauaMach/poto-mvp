"""Esquema, PRAGMAs e constraints do SQLite.

Os testes de criação e consulta de chamados ficam em `test_db.py` (MVP-018).
Aqui só o que sustenta tudo o mais: o esquema existe, é idempotente, as
constraints de unicidade valem e a transação desfaz o que deu errado.
"""

from __future__ import annotations

import sqlite3

import pytest

from app import config, db


@pytest.fixture
def banco(tmp_path, monkeypatch):
    """Banco temporário por teste — nunca o poto.db real."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "teste.db"))
    db.init_db()
    return tmp_path / "teste.db"


def _inserir_chamado(chamado_id="CALL-2026-000001", evento_id="uuid-a"):
    with db.conectar() as con:
        con.execute(
            """INSERT INTO chamados
               (chamado_id, evento_id, totem_id, tipo_ocorrencia, modo,
                origem_acionamento, gravidade, canal_roteado, status,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                chamado_id, evento_id, "TOTEM-CCS-01", "seguranca", "normal",
                "touch", "risco_imediato", "csv", "recebido",
                db.agora_iso(), db.agora_iso(),
            ),
        )


# --- Esquema ----------------------------------------------------------------


def test_cria_as_tres_tabelas(banco):
    with db.conectar() as con:
        nomes = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert nomes == {"chamados", "estado_log", "notificacoes"}


def test_cria_os_tres_indices(banco):
    with db.conectar() as con:
        nomes = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
    assert nomes == {"idx_notif_chamado", "idx_estado_chamado", "idx_chamados_status"}


def test_init_db_e_idempotente(banco):
    """Roda no lifespan a cada start da API — não pode quebrar na segunda vez."""
    db.init_db()
    db.init_db()
    _inserir_chamado()
    db.init_db()  # com dados dentro, ainda assim seguro

    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM chamados").fetchone()[0] == 1


def test_cria_o_diretorio_do_banco_se_faltar(tmp_path, monkeypatch):
    destino = tmp_path / "sub" / "dir" / "poto.db"
    monkeypatch.setattr(config, "DB_PATH", str(destino))
    db.init_db()
    assert destino.exists()


# --- PRAGMAs ----------------------------------------------------------------


def test_wal_esta_ligado(banco):
    """Sem WAL, a leitura do painel bloquearia a escrita do totem."""
    with db.conectar() as con:
        assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_synchronous_normal(banco):
    """1 = NORMAL. Menos fsync, menos desgaste do cartão SD — seguro com WAL."""
    with db.conectar() as con:
        assert con.execute("PRAGMA synchronous").fetchone()[0] == 1


def test_busy_timeout_evita_erro_imediato_de_lock(banco):
    """O worker de SLA escreve em paralelo com a API. Sem timeout, a colisão
    viraria 'database is locked' na hora."""
    with db.conectar() as con:
        assert con.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


# --- Constraints ------------------------------------------------------------


def test_evento_id_e_unico(banco):
    """É a constraint que sustenta a idempotência: o reenvio de um evento não
    pode virar um segundo chamado para a mesma emergência."""
    _inserir_chamado(chamado_id="CALL-2026-000001", evento_id="mesmo-uuid")
    with pytest.raises(sqlite3.IntegrityError):
        _inserir_chamado(chamado_id="CALL-2026-000002", evento_id="mesmo-uuid")


def test_chamado_id_e_unico(banco):
    _inserir_chamado(chamado_id="CALL-2026-000001", evento_id="uuid-a")
    with pytest.raises(sqlite3.IntegrityError):
        _inserir_chamado(chamado_id="CALL-2026-000001", evento_id="uuid-b")


@pytest.mark.parametrize(
    "coluna", ["chamado_id", "evento_id", "totem_id", "tipo_ocorrencia", "status"]
)
def test_colunas_essenciais_sao_not_null(banco, coluna):
    with db.conectar() as con:
        info = {r["name"]: r for r in con.execute("PRAGMA table_info(chamados)")}
    assert info[coluna]["notnull"] == 1


# --- Transação --------------------------------------------------------------


def test_erro_no_meio_da_transacao_nao_deixa_residuo(banco):
    with pytest.raises(RuntimeError):
        with db.conectar() as con:
            con.execute(
                "INSERT INTO estado_log (chamado_id, para, created_at) VALUES (?,?,?)",
                ("CALL-X", "recebido", db.agora_iso()),
            )
            raise RuntimeError("falha simulada")

    with db.conectar() as con:
        assert con.execute("SELECT count(*) FROM estado_log").fetchone()[0] == 0


def test_row_factory_permite_acesso_por_nome(banco):
    _inserir_chamado()
    with db.conectar() as con:
        linha = con.execute("SELECT * FROM chamados").fetchone()
    assert linha["canal_roteado"] == "csv"
    assert linha["tipo_ocorrencia"] == "seguranca"


# --- Timestamps -------------------------------------------------------------


def test_agora_iso_e_utc_e_ordenavel():
    """UTC e não horário local: a string ordena como texto, sem ambiguidade."""
    a = db.agora_iso()
    b = db.agora_iso()
    assert a.endswith("+00:00")
    assert a <= b
