"""Persistência em SQLite.

Uma conexão por operação, via context manager. Para o volume real de um totem
— dezenas de registros por dia num único dispositivo — o custo de abrir a
conexão é irrelevante, e isso evita toda a classe de problemas de compartilhar
conexão entre as threads do FastAPI.

Sem ORM: o esquema é pequeno, estável e escrito à mão em ARCHITECTURE.md §5.
A ausência de ORM também é o que torna uma migração futura para Postgres uma
troca de driver em vez de uma reescrita.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS chamados (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id          TEXT UNIQUE NOT NULL,   -- CALL-2026-000001
  evento_id           TEXT UNIQUE NOT NULL,   -- UUID do totem -> IDEMPOTÊNCIA
  totem_id            TEXT NOT NULL,
  tipo_ocorrencia     TEXT NOT NULL,
  modo                TEXT NOT NULL,
  origem_acionamento  TEXT NOT NULL,
  gravidade           TEXT NOT NULL,
  canal_roteado       TEXT NOT NULL,
  fallback            TEXT,
  status              TEXT NOT NULL,
  texto_livre         TEXT,                   -- fica só aqui; nunca sai na notificação
  triagem_json        TEXT,                   -- auditável: o que a triagem decidiu
  observacao          TEXT,
  timestamp_local     TEXT,
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL,
  acked_at            TEXT
);

-- Append-only: nenhuma linha é editada ou apagada. É o que permite reconstruir
-- a história de um chamado depois.
CREATE TABLE IF NOT EXISTS estado_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id  TEXT NOT NULL,
  de          TEXT,
  para        TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

-- Quem foi acionado, por qual canal, com que resultado. O `destino` mora aqui,
-- atrás do token do painel — nunca numa resposta de endpoint aberto.
CREATE TABLE IF NOT EXISTS notificacoes (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id     TEXT NOT NULL,
  canal          TEXT NOT NULL,
  destino        TEXT NOT NULL,
  provider       TEXT NOT NULL,
  sucesso        INTEGER NOT NULL,
  mensagem       TEXT,
  detalhe        TEXT,
  escalonamento  INTEGER NOT NULL DEFAULT 0,
  created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notif_chamado   ON notificacoes(chamado_id);
CREATE INDEX IF NOT EXISTS idx_estado_chamado  ON estado_log(chamado_id);
CREATE INDEX IF NOT EXISTS idx_chamados_status ON chamados(status);
"""


def agora_iso() -> str:
    """Instante atual em UTC, ISO 8601.

    UTC e não horário local: a string fica ordenável como texto e não tem
    ambiguidade. Quem exibe converte — o painel faz `new Date(s)` e mostra no
    fuso de quem olha.
    """
    return datetime.now(UTC).isoformat()


@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    """Abre uma conexão configurada, comitando ao sair sem erro."""
    caminho = Path(config.DB_PATH)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row

    # WAL: a leitura do painel deixa de bloquear a escrita do totem. A
    # propriedade fica gravada no arquivo, então só tem efeito na primeira vez.
    con.execute("PRAGMA journal_mode = WAL")
    # NORMAL em vez de FULL: menos fsync, menos desgaste do cartão SD da Pi.
    # Seguro com WAL — o risco passa a ser perder as últimas transações num
    # corte de energia, não corromper o banco.
    con.execute("PRAGMA synchronous = NORMAL")
    # O worker de SLA escreve em paralelo com as requisições da API. Sem isto,
    # uma colisão vira "database is locked" imediatamente em vez de esperar.
    con.execute("PRAGMA busy_timeout = 5000")

    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    """Cria o esquema se ainda não existir. Idempotente."""
    with conectar() as con:
        con.executescript(SCHEMA)
