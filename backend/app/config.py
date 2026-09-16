"""Configuração por variáveis de ambiente (12-factor).

Este módulo só **lê** o ambiente; ele não carrega arquivos `.env`. Quem fornece
as variáveis é:

  - desenvolvimento → `uvicorn --env-file backend/.env` (ver Makefile)
  - produção na Pi  → `EnvironmentFile=` na unit systemd

Assim não há dependência extra e o comportamento é o mesmo nos dois ambientes.
Partindo de `backend/.env.example`, copie para `backend/.env` e ajuste.
"""

from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

# backend/
BASE_DIR = Path(__file__).resolve().parent.parent


def _int(nome: str, padrao: int) -> int:
    try:
        return int(os.getenv(nome, "").strip() or padrao)
    except ValueError:
        return padrao


def _lista(nome: str, padrao: str) -> list[str]:
    bruto = os.getenv(nome, "").strip() or padrao
    return [item.strip() for item in bruto.split(",") if item.strip()]


# --- Persistência ----------------------------------------------------------
DB_PATH = os.getenv("POTO_DB_PATH", "").strip() or str(BASE_DIR / "poto.db")

# --- Triagem ---------------------------------------------------------------
# Artefato do classificador (TF-IDF + LogReg), gerado por `make setup`.
# Ausente, a triagem cai na heurística — e `/health` diz isso (MVP-036).
CLF_PATH = os.getenv("POTO_CLF_PATH", "").strip() or str(
    BASE_DIR / "app" / "data" / "triagem_clf.joblib"
)

# --- Frontend estático (o backend serve a aplicação em produção) -----------
FRONTEND_DIST = os.getenv("POTO_FRONTEND_DIST", "").strip() or str(
    BASE_DIR.parent / "frontend" / "dist"
)

# --- Notificação -----------------------------------------------------------
NOTIF_PROVIDER = (os.getenv("POTO_NOTIF_PROVIDER", "") or "log").strip().lower()
NOTIF_WEBHOOK_URL = os.getenv("POTO_NOTIF_WEBHOOK_URL", "").strip()
NOTIF_WEBHOOK_TOKEN = os.getenv("POTO_NOTIF_WEBHOOK_TOKEN", "").strip()

# --- SLA -------------------------------------------------------------------
SLA_CHECK_INTERVAL = _int("POTO_SLA_CHECK_INTERVAL", 30)

# Intervalo com que o totem tenta drenar a fila offline (MVP-058). Exposto em
# `/config` para que o frontend não o duplique: é uma constante de domínio —
# quanto tempo é aceitável um acionamento ficar retido no aparelho — e não uma
# preferência de interface.
TOTEM_OFFLINE_SEG = _int("POTO_TOTEM_OFFLINE_SEG", 15)

# --- Segurança -------------------------------------------------------------
# Exigido no painel (/chamados*, /ws). Vazio = modo desenvolvimento: libera e
# registra aviso. Os endpoints de acionamento (/eventos, /panico) NUNCA exigem
# token — um totem em pânico não pode falhar por credencial.
PAINEL_TOKEN = os.getenv("POTO_PAINEL_TOKEN", "").strip()

# Nunca "*": o tablet e o painel carregam a aplicação da própria origem do
# backend, então não precisam de CORS. A lista existe só para desenvolvimento,
# onde o Vite serve na 5173.
CORS_ORIGINS = _lista(
    "POTO_CORS_ORIGINS", "http://localhost:5173,http://localhost:8000"
)

# --- Catálogo de canais ----------------------------------------------------
# Só metadado de exibição. O contato NÃO mora aqui de propósito: `/canais` é um
# endpoint de sistema, sem token, e um dicionário que carregasse o telefone
# convidaria a vazá-lo por acidente (`return CANAIS` num endpoint e pronto).
# Quem resolve destino é `contato_canal()`, logo abaixo.
CANAIS: dict[str, dict[str, str]] = {
    "csv": {"nome": "CSV / PREUNI"},
    "sala_lilas": {"nome": "Sala Lilás"},
    "sapsi": {"nome": "SAPSI / PRAEC"},
    "ouvidoria": {"nome": "Ouvidoria UFPI"},
    "samu_192": {"nome": "SAMU"},
    "pm_190": {"nome": "Polícia Militar"},
    "bombeiros_193": {"nome": "Corpo de Bombeiros"},
    "central_180": {"nome": "Central de Atendimento à Mulher"},
}


def nome_canal(canal: str) -> str:
    """Nome legível de um canal; devolve a própria chave se for desconhecido."""
    return CANAIS.get(canal, {}).get("nome", canal)


# Acionados em paralelo no broadcast de pânico (MVP-031).
CANAIS_INTERNOS = ["csv", "sala_lilas"]

# Autoridades do estado, oferecidas para escalonamento MANUAL na tela de alerta
# ativo. O sistema nunca disca para elas sozinho: registra que um humano
# acionou. Robo-discar 190 ou 192 por classificação automática seria
# irresponsável — e é o tipo de decisão que a máquina não toma.
CANAIS_ESTADO = ["pm_190", "samu_192", "bombeiros_193", "central_180"]

# --- Prazos de SLA ---------------------------------------------------------
# Tempo até o ACK do operador. Estourado, o chamado escalona sozinho para o
# canal de fallback (MVP-038) — o silêncio humano nunca arquiva um chamado.
# `orientacao` não escalona: não há urgência a proteger.
SLA_SEGUNDOS: dict[str, int | None] = {
    "risco_imediato": 120,
    "risco_potencial": 600,
    "orientacao": None,
}

# --- Horário de funcionamento ----------------------------------------------
# Sala Lilás e SAPSI têm expediente; CSV, SAMU, PM, Bombeiros e o 180 atendem
# 24h. Encaminhar para uma sala vazia às 2h da manhã é o mesmo que não
# encaminhar — por isso o roteador (MVP-012) consulta isto.
#
# Fuso de Teresina: UTC−3 fixo. O Piauí não adota horário de verão, e o
# horário do servidor não é confiável (a Pi pode estar sem NTP). Fixar o
# deslocamento é mais seguro que depender do relógio do sistema.
FUSO_LOCAL = timezone(timedelta(hours=-3))

HORARIO_COMERCIAL = {
    "dias": {0, 1, 2, 3, 4},  # segunda a sexta
    "janelas": [(8, 12), (14, 17)],
}


# --- Contatos dos canais ---------------------------------------------------
# SEM DEFAULT DE PROPÓSITO. O projeto de referência trazia um celular real de
# Teresina embutido no código, que seria acionado por qualquer um na rede.
# Aqui, canal sem contato configurado simplesmente não é acionável, e o
# /health aponta quais faltam.
_CONTATOS = {
    "csv": os.getenv("POTO_CONTACT_CSV", "").strip(),
    "sala_lilas": os.getenv("POTO_CONTACT_SALA_LILAS", "").strip(),
    "sapsi": os.getenv("POTO_CONTACT_SAPSI", "").strip(),
    "ouvidoria": os.getenv("POTO_CONTACT_OUVIDORIA", "").strip(),
    "samu_192": os.getenv("POTO_CONTACT_SAMU", "").strip(),
    "pm_190": os.getenv("POTO_CONTACT_PM", "").strip(),
    "bombeiros_193": os.getenv("POTO_CONTACT_BOMBEIROS", "").strip(),
    "central_180": os.getenv("POTO_CONTACT_180", "").strip(),
}

# Redireciona TODOS os destinos para um único contato. É a trava de segurança
# de bancada e de demonstração: impede discar 190/192/193/180 de verdade
# enquanto se testa. Em produção fica vazio.
CONTACT_OVERRIDE = os.getenv("POTO_CONTACT_OVERRIDE", "").strip()


def contato_canal(canal: str) -> str:
    """Destino efetivo de um canal. Vazio significa 'não configurado'."""
    if CONTACT_OVERRIDE:
        return CONTACT_OVERRIDE
    return _CONTATOS.get(canal, "")


def canais_sem_contato() -> list[str]:
    """Canais sem destino configurado — reportados por `/health`."""
    if CONTACT_OVERRIDE:
        return []
    return sorted(canal for canal, destino in _CONTATOS.items() if not destino)
