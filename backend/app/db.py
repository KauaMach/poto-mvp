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

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from . import config
from .models import StatusChamado

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


# ---------------------------------------------------------------------------
# Chamados
# ---------------------------------------------------------------------------


def _dict(linha: sqlite3.Row | None) -> dict | None:
    return dict(linha) if linha is not None else None


def _protocolo(rowid: int, quando: datetime) -> str:
    """`CALL-2026-000001`, derivado do rowid que o SQLite já atribuiu.

    Usar o rowid em vez de um `SELECT count(*)` elimina a corrida: dois
    acionamentos simultâneos nunca recebem o mesmo protocolo, porque quem
    numera é o banco. O sequencial não reinicia a cada ano — o ano no prefixo
    é para leitura humana, não é chave.
    """
    return f"CALL-{quando.year}-{rowid:06d}"


def buscar_por_evento(evento_id: str) -> dict | None:
    """Localiza um chamado pela chave de idempotência."""
    with conectar() as con:
        linha = con.execute(
            "SELECT * FROM chamados WHERE evento_id = ?", (str(evento_id),)
        ).fetchone()
    return _dict(linha)


def criar_chamado(
    evento: dict,
    routing: dict,
    triagem: dict | None = None,
    *,
    status: str = StatusChamado.roteado,
) -> dict:
    """Registra um chamado. Idempotente por `evento_id`.

    Reenviar o mesmo evento — dreno duplicado da fila offline, retry de rede,
    duplo toque — devolve o chamado que já existe, marcado com `_duplicado`,
    em vez de criar um segundo alarme para a mesma emergência.

    `evento` é um dicionário e não um modelo Pydantic porque `/panico` monta o
    seu à mão: ele não tem trilha escolhida nem texto para triar.
    """
    evento_id = str(evento["evento_id"])

    # Caminho rápido: já existe?
    if (existente := buscar_por_evento(evento_id)) is not None:
        return {**existente, "_duplicado": True}

    agora = agora_iso()
    try:
        with conectar() as con:
            # O protocolo depende do rowid, que só existe depois do INSERT.
            # Insere com um marcador único e corrige em seguida, na mesma
            # transação — quem vê o banco de fora nunca enxerga o marcador.
            cur = con.execute(
                """INSERT INTO chamados
                   (chamado_id, evento_id, totem_id, tipo_ocorrencia, modo,
                    origem_acionamento, gravidade, canal_roteado, fallback,
                    status, texto_livre, triagem_json, timestamp_local,
                    created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    f"pendente:{evento_id}",
                    evento_id,
                    evento["totem_id"],
                    str(evento["tipo_ocorrencia"]),
                    str(evento["modo"]),
                    str(evento["origem_acionamento"]),
                    str(routing["gravidade"]),
                    routing["canal_roteado"],
                    routing.get("fallback"),
                    str(status),
                    evento.get("texto_livre"),
                    json.dumps(triagem, ensure_ascii=False) if triagem else None,
                    evento.get("timestamp_local"),
                    agora,
                    agora,
                ),
            )
            rowid = cur.lastrowid
            chamado_id = _protocolo(rowid, datetime.now(UTC))
            con.execute(
                "UPDATE chamados SET chamado_id = ? WHERE id = ?", (chamado_id, rowid)
            )
            con.execute(
                "INSERT INTO estado_log (chamado_id, de, para, created_at) VALUES (?,?,?,?)",
                (chamado_id, None, str(status), agora),
            )

    except sqlite3.IntegrityError:
        # Dois acionamentos com o mesmo evento_id chegaram juntos e um perdeu a
        # corrida. A constraint UNIQUE fez o trabalho; devolvemos o vencedor.
        if (existente := buscar_por_evento(evento_id)) is not None:
            return {**existente, "_duplicado": True}
        raise

    criado = buscar_por_evento(evento_id)
    assert criado is not None  # acabou de ser inserido
    return {**criado, "_duplicado": False}
