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

.PHONY: help setup dev backend serve frontend build deploy build-id test lint train-clf seed demo-reset clean

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

backend: ## Sobe só a API, em modo de desenvolvimento (recarrega ao salvar)
	$(call exige,$(BACKEND)/app/main.py,MVP-026)
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT) $(ENV_FLAG)

# `serve` reproduz o modo de produção: os **mesmos argumentos de servidor** que a
# unit systemd da MVP-067 usa, que são os que mudam o comportamento observável.
#
# O que difere é a invocação: aqui `uv run uvicorn`, na unit o binário do venv
# direto (`.venv/bin/uvicorn`). Não é descuido — `uv run` sincroniza dependências
# quando o `pyproject` muda, o que é o que se quer em desenvolvimento e o oposto
# do que se quer num serviço: ele escreve em `~/.cache/uv`, que o sandbox da unit
# torna somente-leitura, e põe resolução de dependências no caminho do boot. O
# serviço falhou em laço na Pi por exatamente isso. Ver o comentário no ExecStart
# de `deploy/poto-api.service`.
#
# Duas diferenças em relação a `backend`, e as duas importam:
#
#   --host 0.0.0.0   sem isto o uvicorn escuta só em 127.0.0.1 e o tablet não
#                    alcança — o sintoma é "funciona na Pi, não funciona no
#                    tablet", que custa meia hora até alguém suspeitar do bind.
#   sem --reload     o observador de arquivos gasta CPU e memória vigiando uma
#                    árvore que não muda, e um toque acidental no código
#                    reiniciaria o serviço no meio de um atendimento.
serve: ## Sobe a API como em produção: 0.0.0.0, sem reload
	$(call exige,$(BACKEND)/app/main.py,MVP-026)
	$(call exige,$(FRONTEND)/dist/index.html,MVP-066)
	cd $(BACKEND) && uv run uvicorn app.main:app \
		--host 0.0.0.0 --port $(BACKEND_PORT) $(ENV_FLAG)

frontend: ## Sobe só o frontend em modo de desenvolvimento
	cd $(FRONTEND) && npm run dev -- --port $(FRONTEND_PORT)

build: ## Build de produção do frontend (o backend passa a servir tudo)
	cd $(FRONTEND) && npm run build
	@echo ""
	@echo "  dist/ pronto — o backend serve a aplicação e a API na mesma origem."
	@echo "  Suba com 'make serve' e abra http://$$(hostname -I 2>/dev/null | awk '{print $$1}'):$(BACKEND_PORT)"
	@echo ""

# --- Deploy para a Pi -------------------------------------------------------
#
# A Pi **não compila** o frontend. O toolchain do Vite 8 é Rust compilado por
# arquitetura, então construir lá usaria binários aarch64 diferentes dos
# testados aqui — mesma fonte, ferramentas distintas (ARCHITECTURE.md D1c).
# Construindo num lugar só, o artefato que roda é literalmente o que foi
# testado.
PI_HOST ?= raspoto@poto.local
PI_DIR  ?= ~/poto-mvp
# Só o nome do host, para o `curl` do `build-id` (o rsync precisa do usuário).
PI_NAME ?= $(lastword $(subst @, ,$(PI_HOST)))

# `build` e `rsync` no mesmo alvo, e é o ponto inteiro desta task: não existe
# enviar sem reconstruir. Alterar o código, esquecer o build e enviar a versão
# antiga é um bug silencioso que custa uma hora de depuração.
deploy: build ## Constrói e envia para a Pi (PI_HOST=usuario@host)
	@echo ""
	@echo "  build-id local: $$(cat $(FRONTEND)/dist/build-id)"
	@echo "  destino:        $(PI_HOST):$(PI_DIR)"
	@echo ""
	rsync -az --delete 		--exclude '.git/' 		--exclude '.venv/' 		--exclude 'node_modules/' 		--exclude '__pycache__/' 		--exclude '*.pyc' 		--exclude '.pytest_cache/' 		--exclude '.ruff_cache/' 		--exclude '*.db' --exclude '*.db-wal' --exclude '*.db-shm' 		--exclude '.env' 		./ $(PI_HOST):$(PI_DIR)/
	@echo ""
	@echo "  enviado. Conferir se a Pi está servindo este build:"
	@echo "    make build-id"
	@echo ""

# O único jeito de saber que a Pi está servindo o que acabou de ser enviado.
# Sem isto, "alterei e não mudou nada" manda a depuração para o lugar errado.
build-id: ## Compara o build-id local com o que a Pi está servindo
	$(call exige,$(FRONTEND)/dist/build-id,MVP-066b)
	@local=$$(cat $(FRONTEND)/dist/build-id); \
	saude=$$(curl -sf --max-time 5 http://$(PI_NAME):$(BACKEND_PORT)/api/v1/health 2>/dev/null); \
	echo ""; \
	echo "  local: $$local"; \
	if [ -z "$$saude" ]; then \
		echo "  na Pi: —"; \
		echo ""; \
		echo "  ✗ a Pi não respondeu em http://$(PI_NAME):$(BACKEND_PORT)."; \
		echo "    Isto é falta de alcance, não artefato velho: confira a rede,"; \
		echo "    o 'systemctl status poto-api' e o nome $(PI_NAME)."; \
		echo ""; \
		exit 1; \
	fi; \
	remoto=$$(echo "$$saude" | python3 -c 'import sys,json; print(json.load(sys.stdin)["frontend"]["build_id"] or "")'); \
	if [ -z "$$remoto" ]; then \
		echo "  na Pi: (sem build-id)"; \
		echo ""; \
		echo "  ✗ a Pi responde, mas o dist/ dela não tem build-id — chegou lá"; \
		echo "    por outro caminho, sem passar pelo 'make deploy'."; \
		echo ""; \
		exit 1; \
	fi; \
	echo "  na Pi: $$remoto"; \
	echo ""; \
	if [ "$$local" = "$$remoto" ]; then \
		echo "  ✓ a Pi está servindo este build"; \
		echo ""; \
	else \
		echo "  ✗ artefatos DIFERENTES — a Pi tem uma versão antiga."; \
		echo "    Rode 'make deploy'."; \
		echo ""; \
		exit 1; \
	fi

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
