.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND       := backend
FRONTEND      := frontend
BACKEND_PORT  ?= 8000
FRONTEND_PORT ?= 5173

# uvicorn só aceita --env-file se o arquivo existir.
ENV_FILE := $(BACKEND)/.env
ENV_FLAG := $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

# Alvos cujos arquivos ainda não existem nesta fase do projeto avisam em qual
# task eles chegam, em vez de estourar um erro obscuro.
define exige
	@test -e $(1) || { \
		echo ""; \
		echo "  Ainda não existe: $(1)"; \
		echo "  Chega na task $(2) — ver TASKS.md"; \
		echo ""; \
		exit 1; \
	}
endef

.PHONY: help setup dev backend frontend build test lint train-clf seed demo-reset clean

help: ## Lista os alvos disponíveis
	@echo ""
	@echo "  P.O.T.O — Totem de Segurança"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""

setup: ## Instala dependências e treina o classificador
	cd $(BACKEND) && uv sync --extra dev
	cd $(FRONTEND) && npm install
	@if [ -f $(BACKEND)/scripts/train_classificador.py ]; then \
		$(MAKE) --no-print-directory train-clf; \
	else \
		echo ""; \
		echo "  Classificador ainda não treinado: o script chega na MVP-021."; \
		echo "  Até lá a triagem usa a heurística de palavras-chave."; \
		echo ""; \
	fi
	@test -f $(ENV_FILE) || echo "  Dica: cp $(BACKEND)/.env.example $(ENV_FILE)"

dev: ## Sobe backend (:8000) e frontend (:5173) juntos
	$(call exige,$(BACKEND)/app/main.py,MVP-026)
	@echo "  backend :$(BACKEND_PORT)  ·  frontend :$(FRONTEND_PORT)  ·  Ctrl+C encerra ambos"
	@trap 'kill 0' EXIT INT TERM; \
	( cd $(BACKEND) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT) $(ENV_FLAG) ) & \
	( cd $(FRONTEND) && npm run dev -- --port $(FRONTEND_PORT) ) & \
	wait

backend: ## Sobe só a API
	$(call exige,$(BACKEND)/app/main.py,MVP-026)
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT) $(ENV_FLAG)

frontend: ## Sobe só o frontend em modo de desenvolvimento
	cd $(FRONTEND) && npm run dev -- --port $(FRONTEND_PORT)

build: ## Build de produção do frontend (o backend passa a servir tudo)
	cd $(FRONTEND) && npm run build

test: ## Roda a suíte de testes do backend
	cd $(BACKEND) && uv run pytest

lint: ## Verifica backend (ruff) e frontend (oxlint)
	cd $(BACKEND) && uv run ruff check .
	cd $(FRONTEND) && npm run lint

train-clf: ## Treina o classificador de triagem e reporta a acurácia
	$(call exige,$(BACKEND)/scripts/train_classificador.py,MVP-021)
	cd $(BACKEND) && uv run python scripts/train_classificador.py $(ARGS)

seed: ## Popula o banco com chamados de exemplo
	$(call exige,$(BACKEND)/app/seed.py,MVP-071)
	cd $(BACKEND) && uv run python -m app.seed

demo-reset: ## Zera o banco e repopula para um ensaio limpo
	$(call exige,$(BACKEND)/app/seed.py,MVP-071)
	rm -f $(BACKEND)/poto.db $(BACKEND)/poto.db-wal $(BACKEND)/poto.db-shm
	$(MAKE) --no-print-directory seed

clean: ## Remove artefatos: dist, venv, node_modules e banco local
	rm -rf $(FRONTEND)/dist $(FRONTEND)/node_modules
	rm -rf $(BACKEND)/.venv $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache
	rm -f  $(BACKEND)/poto.db $(BACKEND)/poto.db-wal $(BACKEND)/poto.db-shm
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "  limpo — rode 'make setup' para reconstruir"
