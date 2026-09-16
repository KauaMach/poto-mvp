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

-- Append-only imposto pelo banco, não por disciplina de quem escreve o código.
-- `estado_log` é a memória de como um chamado foi tratado; se ela puder ser
-- reescrita, não serve para responder "o que aconteceu naquela noite".
--
-- Para um expurgo legítimo (direito ao apagamento, LGPD), os gatilhos precisam
-- ser removidos de propósito — que é exatamente o atrito desejado.
CREATE TRIGGER IF NOT EXISTS estado_log_sem_update
BEFORE UPDATE ON estado_log
BEGIN SELECT RAISE(ABORT, 'estado_log é append-only'); END;

CREATE TRIGGER IF NOT EXISTS estado_log_sem_delete
BEFORE DELETE ON estado_log
BEGIN SELECT RAISE(ABORT, 'estado_log é append-only'); END;
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


def obter_chamado(chamado_id: str) -> dict | None:
    with conectar() as con:
        linha = con.execute(
            "SELECT * FROM chamados WHERE chamado_id = ?", (chamado_id,)
        ).fetchone()
    return _dict(linha)


# Teto de uma listagem do painel. O volume real de um totem é de dezenas de
# registros por dia; 200 cobre semanas de operação sem paginação.
LIMITE_LISTAGEM = 200


def listar_chamados(
    tipo: str | None = None,
    status: str | None = None,
    gravidade: str | None = None,
    *,
    limite: int = LIMITE_LISTAGEM,
) -> list[dict]:
    """Lista para o painel, mais recentes primeiro, com filtros combináveis.

    Ordena por `id` e não por `created_at`: é a chave primária, já indexada, e
    monotônica com a criação. Priorizar críticos no topo é decisão de
    apresentação e fica no painel, não aqui.
    """
    clausulas, valores = [], []
    for coluna, valor in (
        ("tipo_ocorrencia", tipo),
        ("status", status),
        ("gravidade", gravidade),
    ):
        if valor:
            clausulas.append(f"{coluna} = ?")
            valores.append(str(valor))

    onde = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""
    with conectar() as con:
        linhas = con.execute(
            f"SELECT * FROM chamados {onde} ORDER BY id DESC LIMIT ?",
            (*valores, limite),
        ).fetchall()
    return [dict(x) for x in linhas]


ESCALONAVEIS = (StatusChamado.notificado, StatusChamado.falha_notificacao)


def pendentes_de_ack() -> list[dict]:
    """Chamados que ninguém reconheceu e que ainda podem escalonar (MVP-038).

    Dois status, e o segundo é uma extensão deliberada do critério, que fala só
    de `notificado`:

    - `notificado` — alguém foi avisado e não respondeu;
    - `falha_notificacao` — **ninguém foi avisado**, porque o canal falhou.

    Deixar o segundo fora faria o pior caso receber menos atenção que o normal:
    um chamado sobre o qual nenhuma mensagem saiu ficaria esperando para sempre.
    O princípio em `config.SLA_SEGUNDOS` é o oposto — o silêncio humano nunca
    arquiva um chamado.

    `alerta_ativo` **não** entra: é persistente por decisão de projeto, e mudar
    seu status seria rebaixar o alerta que mantém o cronômetro do totem correndo.

    Ordena por `id` ASC: o mais antigo é o que está esperando há mais tempo.
    """
    marcadores = ",".join("?" * len(ESCALONAVEIS))
    with conectar() as con:
        linhas = con.execute(
            f"""SELECT * FROM chamados
                WHERE status IN ({marcadores}) AND acked_at IS NULL
                ORDER BY id""",
            tuple(str(s) for s in ESCALONAVEIS),
        ).fetchall()
    return [dict(x) for x in linhas]


def atualizar_chamado(
    chamado_id: str,
    *,
    status: str | None = None,
    observacao: str | None = None,
) -> dict | None:
    """Atualiza estado e/ou observação. Devolve `None` se o chamado não existe.

    Toda troca de status vira uma linha em `estado_log`, na mesma transação da
    atualização — não existe mudar o estado sem deixar rastro. Reescrever o
    mesmo status não gera linha: o log registra transições, não toques.
    """
    with conectar() as con:
        atual = con.execute(
            "SELECT * FROM chamados WHERE chamado_id = ?", (chamado_id,)
        ).fetchone()
        if atual is None:
            return None

        campos, valores = [], []
        agora = agora_iso()

        if status is not None and str(status) != atual["status"]:
            campos.append("status = ?")
            valores.append(str(status))
            con.execute(
                "INSERT INTO estado_log (chamado_id, de, para, created_at) VALUES (?,?,?,?)",
                (chamado_id, atual["status"], str(status), agora),
            )
        if observacao is not None:
            campos.append("observacao = ?")
            valores.append(observacao)

        if campos:
            campos.append("updated_at = ?")
            valores.append(agora)
            con.execute(
                f"UPDATE chamados SET {', '.join(campos)} WHERE chamado_id = ?",
                (*valores, chamado_id),
            )

        linha = con.execute(
            "SELECT * FROM chamados WHERE chamado_id = ?", (chamado_id,)
        ).fetchone()
    return _dict(linha)


def listar_estados(chamado_id: str) -> list[dict]:
    """A história do chamado, em ordem cronológica.

    Ordena por `id` e não por `created_at`: duas transições no mesmo instante
    (o relógio tem resolução finita) precisam sair na ordem em que de fato
    aconteceram, e é o `id` que preserva isso.
    """
    with conectar() as con:
        linhas = con.execute(
            "SELECT de, para, created_at FROM estado_log "
            "WHERE chamado_id = ? ORDER BY id",
            (chamado_id,),
        ).fetchall()
    return [dict(x) for x in linhas]


def registrar_notificacao(
    chamado_id: str,
    canal: str,
    destino: str,
    provider: str,
    sucesso: bool,
    *,
    mensagem: str | None = None,
    detalhe: str | None = None,
    escalonamento: bool = False,
) -> None:
    """Grava uma tentativa de acionamento — inclusive as que falharam.

    **Toda** tentativa entra aqui, e é de propósito: quando alguém pergunta
    "por que ninguém apareceu naquela noite", a resposta precisa estar no
    banco. Registrar só os sucessos deixaria o silêncio indistinguível de
    nunca ter tentado.

    É também onde o `destino` fica. Ele não aparece em resposta de endpoint
    aberto (ver `models.py`); mora nesta tabela, atrás do token do painel.
    """
    with conectar() as con:
        con.execute(
            """INSERT INTO notificacoes
               (chamado_id, canal, destino, provider, sucesso, mensagem,
                detalhe, escalonamento, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                chamado_id,
                canal,
                destino,
                provider,
                int(sucesso),
                mensagem,
                detalhe,
                int(escalonamento),
                agora_iso(),
            ),
        )


def listar_notificacoes(chamado_id: str) -> list[dict]:
    """Tentativas de acionamento de um chamado, em ordem cronológica.

    Ordena por `id` pelo mesmo motivo de `listar_estados`: um broadcast de
    pânico dispara canais em paralelo e grava tudo no mesmo instante.
    """
    with conectar() as con:
        linhas = con.execute(
            "SELECT * FROM notificacoes WHERE chamado_id = ? ORDER BY id",
            (chamado_id,),
        ).fetchall()
    return [_notificacao(x) for x in linhas]


def _notificacao(linha: sqlite3.Row) -> dict:
    """Converte os `INTEGER` de flag do SQLite em `bool`.

    O SQLite não tem booleano. Devolver `0`/`1` aqui faria o Pydantic da API
    expor `sucesso: 0` — e um `if notificacao["sucesso"]` continuaria correto,
    então o erro só apareceria na tela do painel.
    """
    dados = dict(linha)
    dados["sucesso"] = bool(dados["sucesso"])
    dados["escalonamento"] = bool(dados["escalonamento"])
    return dados


def ack_chamado(chamado_id: str) -> dict | None:
    """Operador reconhece o chamado: para o relógio do SLA.

    `acked_at` é gravado só na primeira vez. Um segundo ACK não reescreve o
    horário original — é dele que sai a métrica de tempo até o reconhecimento,
    e sobrescrever mascararia uma demora real.
    """
    with conectar() as con:
        atual = con.execute(
            "SELECT * FROM chamados WHERE chamado_id = ?", (chamado_id,)
        ).fetchone()
        if atual is None:
            return None
        primeiro_ack = atual["acked_at"] is None

    chamado = atualizar_chamado(chamado_id, status=StatusChamado.reconhecido)
    if primeiro_ack:
        with conectar() as con:
            con.execute(
                "UPDATE chamados SET acked_at = ? WHERE chamado_id = ?",
                (agora_iso(), chamado_id),
            )
        chamado = obter_chamado(chamado_id)
    return chamado
