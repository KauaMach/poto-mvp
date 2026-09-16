# P.O.T.O MVP — Backlog de Tasks

> 81 tasks ordenadas por dependência de execução. Nenhuma task depende de algo ainda não
> implementado. Ver [PLAN.md](PLAN.md) para escopo e [ARCHITECTURE.md](ARCHITECTURE.md)
> para as decisões técnicas.
>
> **Hardware alvo:** tela do totem = **Samsung Galaxy Tab A11** (8.7", 1340×800), rodando
> Chrome contra a Raspberry Pi 5 na rede local. Painel da central = notebook/desktop.
> A mesma aplicação atende os dois, com layout fluido.
>
> **Câmera e microfone são da Pi**, capturados no servidor (a Pi é headless — nenhum
> navegador os enxerga) e transmitidos em MJPEG **só sob demanda da central**. Câmera e
> microfone do tablet são P2: exigiriam TLS na LAN.

**Prioridades:** `P0` obrigatória para o MVP · `P1` importante, pode ser simplificada ·
`P2` pós-MVP (listada aqui só para não ser esquecida — **não implementar agora**).

**Legenda de status:** `Pendente` · `Em andamento` · `Concluída` · `Bloqueada`

---

## Backlog resumido

| ID | Task | Fase | Prio | Depende de | Status |
|---|---|---|---|---|---|
| MVP-001 | Estrutura de diretórios do projeto | F1 | P0 | — | ✅ Concluída |
| MVP-002 | Scaffold do backend (FastAPI + uv) | F1 | P0 | 001 | ✅ Concluída |
| MVP-003 | Scaffold do frontend (React + Vite + TS) | F1 | P0 | 001 | ✅ Concluída |
| MVP-004 | `.env.example` e carregamento de config | F1 | P0 | 002 | ✅ Concluída |
| MVP-005 | `.gitignore` | F1 | P0 | 001 | ✅ Concluída |
| MVP-006 | Lint e formatação (ruff + oxlint) | F1 | P1 | 002, 003 | ✅ Concluída |
| MVP-007 | Makefile com alvos de desenvolvimento | F1 | P0 | 002, 003 | ✅ Concluída |
| MVP-008 | Commit inicial e push | F1 | P0 | 001–007 | ✅ Concluída |
| MVP-009 | Enums do domínio | F2 | P0 | 002 | ✅ Concluída |
| MVP-010 | Contratos Pydantic de entrada e saída | F2 | P0 | 009 | ✅ Concluída |
| MVP-011 | Catálogo de canais e config de SLA | F2 | P0 | 004, 009 | Pendente |
| MVP-012 | Roteador determinístico | F2 | P0 | 009, 011 | Pendente |
| MVP-013 | Testes do roteador | F2 | P0 | 012 | Pendente |
| MVP-014 | Schema SQLite + WAL + índices | F2 | P0 | 009 | Pendente |
| MVP-015 | Criação de chamado com idempotência | F2 | P0 | 014 | Pendente |
| MVP-016 | Consulta e atualização de chamados | F2 | P0 | 015 | Pendente |
| MVP-017 | Máquina de estados (`estado_log`) | F2 | P0 | 015 | Pendente |
| MVP-018 | Testes de persistência e idempotência | F2 | P0 | 015–017 | Pendente |
| MVP-019 | Portar datasets de triagem | F3 | P0 | 002 | Pendente |
| MVP-020 | Classificador TF-IDF + LogReg | F3 | P0 | 019 | Pendente |
| MVP-021 | Script de treino e avaliação | F3 | P0 | 020 | Pendente |
| MVP-022 | Heurística de palavras-chave | F3 | P0 | 009 | Pendente |
| MVP-023 | **Merge protetivo** | F3 | P0 | 012, 020, 022 | Pendente |
| MVP-024 | Fachada `triar()` | F3 | P0 | 023 | Pendente |
| MVP-025 | Suíte de regressão de segurança | F3 | P0 | 024 | Pendente |
| MVP-026 | App FastAPI + lifespan + estático | F4 | P0 | 004, 014 | Pendente |
| MVP-027 | Hub de WebSocket | F4 | P0 | 026 | Pendente |
| MVP-028 | Registry de canais + provider `log` | F4 | P0 | 011 | Pendente |
| MVP-029 | Provider `webhook` | F4 | P0 | 028 | Pendente |
| MVP-030 | `POST /eventos` | F4 | P0 | 024, 027, 028 | Pendente |
| MVP-031 | `POST /panico` | F4 | P0 | 030 | Pendente |
| MVP-032 | `GET /chamados` e `GET /chamados/{id}` | F4 | P0 | 016 | Pendente |
| MVP-033 | `POST /chamados/{id}/ack` e `PATCH` | F4 | P0 | 016, 027 | Pendente |
| MVP-034 | `POST /chamados/{id}/escalonar` | F4 | P0 | 028, 032 | Pendente |
| MVP-035 | `WS /ws` | F4 | P0 | 027 | Pendente |
| MVP-036 | `GET /health` honesto | F4 | P0 | 024, 028 | Pendente |
| MVP-037 | `GET /config` e `GET /canais` | F4 | P0 | 011 | Pendente |
| MVP-038 | Worker de SLA e escalonamento | F4 | P0 | 030, 033 | Pendente |
| MVP-039 | Testes de contrato da API | F4 | P0 | 030–038 | Pendente |
| MVP-040 | Autenticação por token no painel | F4 | P1 | 032 | Pendente |
| MVP-041 | Fontes auto-hospedadas | F5 | P0 | 003 | Pendente |
| MVP-042 | `tokens.css` e `base.css` | F5 | P0 | 003 | Pendente |
| MVP-043 | Componente `<Sym>` (ícones) | F5 | P0 | 041, 042 | Pendente |
| MVP-044 | Componentes `<Wordmark>` e `<StatusPill>` | F5 | P0 | 042, 043 | Pendente |
| MVP-045 | Componente `<Choice>` | F5 | P0 | 042, 043 | Pendente |
| MVP-046 | Componente `<Panic>` com pressionar-e-segurar | F5 | P0 | 042, 043 | Pendente |
| MVP-047 | Componente `<Confirm>` | F5 | P0 | 042, 043 | Pendente |
| MVP-048 | Cliente de API tipado | F6 | P0 | 010, 030 | Pendente |
| MVP-049 | Shell do totem (header/main/footer) | F6 | P0 | 044 | Pendente |
| MVP-050 | Tela inicial com as 4 trilhas | F6 | P0 | 045, 046, 049 | Pendente |
| MVP-051 | Fluxo de acionamento e confirmação | F6 | P0 | 047, 048, 050 | Pendente |
| MVP-052 | Retorno automático à tela inicial | F6 | P0 | 051 | Pendente |
| MVP-053 | Modo discreto | F6 | P0 | 051 | Pendente |
| MVP-054 | Tela de alerta ativo (pânico) | F6 | P0 | 031, 051 | Pendente |
| MVP-055 | Layout fluido: tablet (2 orientações) e desktop | F6 | P0 | 050, 054 | Pendente |
| MVP-055b | Manifest e modo autônomo no tablet | F6 | P0 | 055 | Pendente |
| MVP-056 | Acessibilidade AA | F6 | P1 | 055 | Pendente |
| MVP-057 | Fila offline em `localStorage` | F7 | P0 | 048 | Pendente |
| MVP-058 | Dreno automático e badge de fila | F7 | P0 | 057 | Pendente |
| MVP-059 | Re-triagem protetiva no dreno | F7 | P0 | 023, 058 | Pendente |
| MVP-060 | Shell e lista do painel | F8 | P0 | 032, 042 | Pendente |
| MVP-061 | Card de chamado com gravidade | F8 | P0 | 060 | Pendente |
| MVP-062 | WebSocket em tempo real no painel | F8 | P0 | 035, 060 | Pendente |
| MVP-063 | ACK e mudança de estado | F8 | P0 | 033, 061 | Pendente |
| MVP-064 | Contador de SLA ao vivo | F8 | P0 | 037, 061 | Pendente |
| MVP-065 | Filtros e busca | F8 | P1 | 060 | Pendente |
| MVP-073 | Detecção de dispositivos + `GET /dispositivos` | F8b | P0 | 026 | Pendente |
| MVP-074 | Captura de vídeo (picamera2 / V4L2) | F8b | P0 | 073 | Pendente |
| MVP-077 | **Sessão de mídia com auditoria** | F8b | P0 | 073, 017 | Pendente |
| MVP-075 | Stream MJPEG | F8b | P0 | 074, 077 | Pendente |
| MVP-076 | Captura e stream de áudio (ALSA) | F8b | P0 | 073, 077 | Pendente |
| MVP-078 | Visualização no painel | F8b | P0 | 063, 075, 076 | Pendente |
| MVP-079 | Custo de CPU e latência na Pi | F8b | P0 | 075, 076 | Pendente |
| MVP-066 | Build integrado servido pelo backend (rede) | F9 | P0 | 026, 055, 060 | Pendente |
| MVP-067 | Unit systemd na Pi (API) | F9 | P0 | 066 | Pendente |
| MVP-067b | Endereçamento estável da Pi (mDNS) | F9 | P0 | 067 | Pendente |
| MVP-067c | Kiosk no Galaxy Tab A11 | F9 | P0 | 055b, 067b | Pendente |
| ~~MVP-068~~ | ~~Daemon do botão GPIO~~ | — | **P2** | — | Fora do MVP |
| MVP-069 | `install-pi.sh` | F9 | P0 | 067b | Pendente |
| MVP-070 | Teste de resiliência (Pi + tablet) | F9 | P0 | 069, 067c | Pendente |
| MVP-071 | Seed e `make demo-reset` | F10 | P0 | 066 | Pendente |
| MVP-072 | Roteiro de demo e plano B | F10 | P0 | 070, 071 | Pendente |

---

# Fase 1 — Fundação do projeto

### MVP-001 — Estrutura de diretórios do projeto
- **Descrição:** Criar a árvore de pastas definida em ARCHITECTURE.md §3, com `backend/`, `frontend/`, `deploy/` e `backend/tests/`.
- **Prioridade:** P0 · **Depende de:** — · **Status:** ✅ Concluída
- **Arquivos:** raiz do repositório
- **Critérios de aceitação:**
  - Existem `backend/app/{api,triagem,canais,midia,data}` e `backend/{scripts,tests}`
  - Existem `frontend/src/{estilos,comum,componentes,totem,painel}` e `frontend/public/fonts`
  - Existe `deploy/` e `docs/`
  - Todo pacote Python tem `__init__.py`
- **Como validar:** `find . -type d -not -path '*/.git/*' | sort` reproduz a árvore de ARCHITECTURE.md §3

### MVP-002 — Scaffold do backend (FastAPI + uv)
- **Descrição:** Inicializar o projeto Python com `uv`, declarando as dependências mínimas.
- **Prioridade:** P0 · **Depende de:** 001 · **Status:** ✅ Concluída
- **Arquivos:** `backend/pyproject.toml`
- **Critérios de aceitação:**
  - `dependencies` contém exatamente: `fastapi`, `uvicorn[standard]`, `pydantic`, `httpx`, `scikit-learn`, `joblib`
  - `scikit-learn` é dependência **obrigatória**, não extra — é o motor da triagem
  - Extra `dev`: `pytest`, `pytest-asyncio`, `ruff`
  - Extra `midia`: **apenas `sounddevice`** — ver nota abaixo sobre o `picamera2`
  - `requires-python = ">=3.11"`
  - Nenhuma menção a langgraph, langchain, pyserial ou faster-whisper
- **Como validar:** `cd backend && uv sync && uv run python -c "import fastapi, sklearn; print('ok')"`

> **Correção aplicada durante a execução.** O critério original mandava declarar
> `picamera2` no extra `midia`. Está errado: verificado na Pi, o `picamera2` vem do
> **apt** (`python3-picamera2`), porque depende de `python3-libcamera` — um binding C++
> compilado que **não existe no PyPI**. Declará-lo como dependência pip faria
> `uv sync --extra midia` falhar na Pi.
>
> O caminho correto, que a MVP-069 (`install-pi.sh`) precisa seguir:
> ```bash
> sudo apt install -y python3-picamera2
> uv venv --system-site-packages --python /usr/bin/python3
> uv sync --extra midia
> ```
> O `--python /usr/bin/python3` é obrigatório: o `picamera2` do apt está instalado para o
> Python do sistema (3.13 na Pi), então um Python baixado pelo uv não o enxergaria nem
> com `--system-site-packages`.

### MVP-003 — Scaffold do frontend (React + Vite + TS)
- **Descrição:** Inicializar a aplicação React com Vite e TypeScript, configurada para gerar build estático em `dist/`.
- **Prioridade:** P0 · **Depende de:** 001 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`
- **Critérios de aceitação:**
  - `npm run dev` sobe em `:5173` com proxy de `/api` para `:8000`
  - `npm run build` gera `dist/index.html` **com os assets referenciados**
  - `base: "/"` no `vite.config.ts` — ver nota abaixo (o critério original pedia `"./"`)
  - Nenhuma dependência de UI kit (sem MUI, Chakra, Tailwind) — a identidade é própria
- **Como validar:** `cd frontend && npm run build && ls dist/index.html dist/assets/`

> **Correção aplicada durante a execução.** O critério original pedia `base: "./"`, com a
> justificativa de "servir de qualquer prefixo". Servimos sempre da **raiz**, e nesse
> cenário a base relativa é pior: na rota `/painel/` (com barra final) os assets
> resolveriam para `/painel/assets/…` e a página quebraria. Com `base: "/"` o caminho é
> `/assets/…` em qualquer rota — verificado em `/`, `/painel` e `/painel/`.
>
> Também trocado `eslint` por **`oxlint`**, que é o linter que o scaffold atual do Vite
> traz por padrão (mais rápido, escrito em Rust). Isso antecipa parte da MVP-006.

### MVP-004 — `.env.example` e carregamento de config
- **Descrição:** Definir todas as variáveis de ambiente com defaults seguros e um módulo `config.py` que as lê.
- **Prioridade:** P0 · **Depende de:** 002 · **Status:** ✅ Concluída
- **Arquivos:** `backend/.env.example`, `backend/app/config.py`
- **Critérios de aceitação:**
  - Variáveis: `POTO_DB_PATH`, `POTO_NOTIF_PROVIDER`, `POTO_NOTIF_WEBHOOK_URL`, `POTO_CONTACT_*`, `POTO_SLA_CHECK_INTERVAL`, `POTO_PAINEL_TOKEN`, `POTO_CORS_ORIGINS`, `POTO_CLF_PATH`
  - **Nenhum número de telefone real como default** — os contatos são obrigatórios via env
  - `.env` está no `.gitignore`; `.env.example` está versionado
- **Como validar:** `grep -E '^POTO_CONTACT' backend/.env.example` mostra placeholders, não números

### MVP-005 — `.gitignore`
- **Descrição:** Ignorar artefatos de build, venv, banco local e segredos.
- **Prioridade:** P0 · **Depende de:** 001 · **Status:** ✅ Concluída
- **Arquivos:** `.gitignore`
- **Critérios de aceitação:**
  - Ignora `backend/.venv/`, `__pycache__/`, `*.pyc`, `backend/poto.db*`, `frontend/node_modules/`, `frontend/dist/`, `.env`
  - Ignora `backend/app/data/*.joblib` — o artefato é gerado pelo `make setup`, não versionado
- **Como validar:** `make setup && git status --short` não lista nenhum artefato gerado

### MVP-006 — Lint e formatação
- **Descrição:** Configurar ruff no backend e oxlint no frontend (o scaffold do Vite já traz oxlint; eslint seria uma dependência a mais pelo mesmo resultado).
- **Prioridade:** P1 · **Depende de:** 002, 003 · **Status:** ✅ Concluída
- **Arquivos:** `backend/pyproject.toml` (`[tool.ruff]`), `frontend/.oxlintrc.json`
- **Critérios de aceitação:** `make lint` roda ambos e sai com código 0 num projeto limpo
- **Como validar:** `make lint`

### MVP-007 — Makefile com alvos de desenvolvimento
- **Descrição:** Centralizar os comandos do projeto num Makefile autodocumentado.
- **Prioridade:** P0 · **Depende de:** 002, 003 · **Status:** ✅ Concluída
- **Arquivos:** `Makefile`
- **Critérios de aceitação:**
  - Alvos: `setup`, `dev`, `backend`, `frontend`, `build`, `test`, `lint`, `train-clf`, `seed`, `demo-reset`, `clean`
  - `make setup` instala backend e frontend **e treina o classificador**
  - `make dev` sobe backend (:8000) e frontend (:5173) juntos
  - `make help` lista os alvos com descrição
- **Como validar:** `make help` e, em pasta limpa, `make setup && make dev`

### MVP-008 — Commit inicial e push
- **Descrição:** Primeiro commit do scaffold no repositório `KauaMach/poto-mvp`.
- **Prioridade:** P0 · **Depende de:** 001–007 · **Status:** ✅ Concluída
- **Critérios de aceitação:**
  - `git config user.name` e `user.email` estão configurados **antes** do commit
  - O autor do commit é a identidade do desenvolvedor
  - **Nenhuma linha de atribuição a IA** na mensagem (ver `CLAUDE.md`)
  - `git push -u origin main` conclui
- **Como validar:** `git log -1 --format='%an <%ae>%n%B'` — autor correto, sem `Co-Authored-By`

> **Fase 1 validada num clone limpo do GitHub**, não só na máquina de desenvolvimento:
> `git clone` → `make setup` → `make build` → `make lint` (exit 0) → `config.py` carrega
> → `git status` continua vazio (nenhum artefato gerado vaza para o repositório).
> Isso fecha o item 1 da Definition of Done do PLAN.md.

---

# Fase 2 — Núcleo de domínio

### MVP-009 — Enums do domínio
- **Descrição:** Portar de `../poto/backend/app/models.py` os enums que definem a linguagem do sistema.
- **Prioridade:** P0 · **Depende de:** 002 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/models.py`
- **Critérios de aceitação:**
  - `TipoOcorrencia`, `Modo`, `OrigemAcionamento`, `Gravidade`, `StatusChamado` com os valores literais de ARCHITECTURE.md §4
  - Todos são `StrEnum` — ver nota abaixo (o critério original pedia `str, Enum`)
- **Como validar:** `uv run python -c "from app.models import Gravidade; print(list(Gravidade))"`

> **Correção aplicada durante a execução.** O critério pedia `class X(str, Enum)`, que é
> como o projeto de referência fazia. O ruff apontou (UP042) e estava certo por um motivo
> que importa: com essa forma, `str(Gravidade.risco_imediato)` devolve
> `"Gravidade.risco_imediato"`, não o valor — e o mesmo vale para f-strings. Bastaria um
> `str(...)` no caminho até o SQLite ou até a mensagem de notificação para gravar lixo
> em silêncio. `StrEnum` (Python 3.11+, que já exigimos) devolve o valor em qualquer
> contexto de string. A intenção do critério — serializar direto em JSON — é atendida
> igual, com uma classe de bug a menos.
>
> Também **não** foram portados `pendente_validacao` nem o enum `NivelRisco`: o portão
> de validação humana ficou fora do escopo do MVP, o que contorna de vez o defeito de
> calibração que o diagnóstico encontrou no projeto de referência.

### MVP-010 — Contratos Pydantic de entrada e saída
- **Descrição:** Modelos de request/response da API.
- **Prioridade:** P0 · **Depende de:** 009 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/models.py`, `backend/tests/test_models.py`
- **Critérios de aceitação:**
  - `EventoIn` (`evento_id`, `totem_id`, `tipo_ocorrencia`, `modo`, `origem_acionamento`, `texto_livre?`, `timestamp_local?`)
  - `EventoOut` (`chamado_id`, `status`, `canal_roteado`, `gravidade`, `instrucao_totem`, `duplicado`)
  - `InstrucaoTotem` (`mensagem_tela`, `feedback_sonoro`, `tela_neutra`)
  - `PanicoIn`, `PanicoOut`, `ChamadoUpdate`, `EscalonamentoIn`
  - `evento_id` validado como UUID
- **Como validar:** `uv run pytest tests/test_models.py`

> **Decisões tomadas durante a execução.**
>
> 1. **`destino` removido de `CanalOpcao` e `CanalResultado`.** O projeto de referência
>    expunha o telefone do canal na resposta de `/panico` — que é um endpoint **aberto**,
>    sem credencial, por decisão de projeto. Isso entregaria os contatos institucionais
>    (CSV, Sala Lilás) a qualquer um que alcance a API. O destino efetivo continua
>    registrado em `notificacoes`, atrás do token do painel.
> 2. **`evento_id` é `UUID`, não `str`.** A idempotência inteira depende dele: uma chave
>    malformada criaria um segundo chamado para a mesma emergência no reenvio.
> 3. **`timestamp_local` continua `str`, não `datetime`.** É diagnóstico. Um tablet com o
>    relógio dessincronizado não pode fazer um pedido de socorro falhar com 422 — o
>    horário autoritativo é o `created_at` do servidor.
> 4. **`firmware_versao`, `assinatura` e `ValidacaoIn` não foram portados** — fora do
>    escopo do MVP.

### MVP-011 — Catálogo de canais e config de SLA
- **Descrição:** Definir os 8 canais institucionais, os grupos de pânico e os prazos de SLA.
- **Prioridade:** P0 · **Depende de:** 004, 009 · **Status:** Pendente
- **Arquivos:** `backend/app/config.py`
- **Critérios de aceitação:**
  - `CANAIS` com `csv`, `sala_lilas`, `sapsi`, `ouvidoria`, `samu_192`, `pm_190`, `bombeiros_193`, `central_180` — cada um com `nome` e `contato`
  - `CANAIS_INTERNOS = ["csv", "sala_lilas"]` (broadcast de pânico)
  - `CANAIS_ESTADO = ["pm_190", "samu_192", "bombeiros_193", "central_180"]`
  - `SLA_SEGUNDOS = {risco_imediato: 120, risco_potencial: 600, orientacao: None}`
  - `HORARIO_COMERCIAL`: seg–sex, janelas `(8,12)` e `(14,17)`
  - Contatos vêm de env, **sem default de telefone real**
- **Como validar:** `uv run python -c "from app.config import CANAIS; print(len(CANAIS))"` → 8

### MVP-012 — Roteador determinístico
- **Descrição:** Portar `rotear()` de `../poto/backend/app/router_engine.py`. É a rede de segurança que funciona mesmo se toda a IA falhar.
- **Prioridade:** P0 · **Depende de:** 009, 011 · **Status:** Pendente
- **Arquivos:** `backend/app/triagem/roteador.py`
- **Critérios de aceitação:**
  - Assinatura `rotear(tipo, modo, *, emergencia=False, agora=None) -> dict`
  - Retorna `canal_roteado`, `fallback`, `gravidade`, `instrucao`, `horario_comercial`
  - Implementa integralmente a tabela de ARCHITECTURE.md §4
  - Trilha `mulher` força `discreto = True` **sempre**, independente do parâmetro
  - Fuso fixo UTC−3 (Teresina, sem horário de verão)
  - `agora` injetável para teste determinístico
- **Como validar:** `uv run pytest tests/test_roteador.py`

### MVP-013 — Testes do roteador
- **Descrição:** Cobrir a matriz completa tipo × modo × horário.
- **Prioridade:** P0 · **Depende de:** 012 · **Status:** Pendente
- **Arquivos:** `backend/tests/test_roteador.py`
- **Critérios de aceitação:**
  - Segurança → `csv`, fallback `pm_190`, `risco_imediato`, em qualquer horário
  - Mulher em horário comercial → `sala_lilas`; fora → `central_180`
  - Mulher → `tela_neutra=True` e `feedback_sonoro=False` **sempre**
  - Saúde com `emergencia=True` → `samu_192`; sem → `sapsi` (comercial) ou `ouvidoria` (fora)
  - Ouvidoria → `ouvidoria`, `orientacao`
  - Pelo menos um teste com `agora` em fim de semana
- **Como validar:** `uv run pytest tests/test_roteador.py -v` — todos verdes

### MVP-014 — Schema SQLite + WAL + índices
- **Descrição:** Criar o banco com as três tabelas, os PRAGMAs e os índices de ARCHITECTURE.md §5.
- **Prioridade:** P0 · **Depende de:** 009 · **Status:** Pendente
- **Arquivos:** `backend/app/db.py`
- **Critérios de aceitação:**
  - `init_db()` é idempotente (`CREATE TABLE IF NOT EXISTS`)
  - Tabelas `chamados`, `estado_log`, `notificacoes` conforme o schema
  - `PRAGMA journal_mode=WAL` e `synchronous=NORMAL` aplicados na conexão
  - Três índices criados
  - `evento_id` e `chamado_id` são `UNIQUE`
- **Como validar:** `sqlite3 backend/poto.db "PRAGMA journal_mode; .schema"`

### MVP-015 — Criação de chamado com idempotência
- **Descrição:** Inserir um chamado gerando o protocolo, tratando reenvio do mesmo `evento_id`.
- **Prioridade:** P0 · **Depende de:** 014 · **Status:** Pendente
- **Arquivos:** `backend/app/db.py`
- **Critérios de aceitação:**
  - `criar_chamado(evento, routing, triagem) -> dict`
  - Protocolo no formato `CALL-{ano}-{sequencial:06d}`
  - `evento_id` repetido **não** cria segundo registro: devolve o existente com `_duplicado=True`
  - `texto_livre` é gravado; `triagem_json` guarda a decisão da triagem
  - Registra o estado inicial em `estado_log`
- **Como validar:** `uv run pytest tests/test_db.py::test_idempotencia`

### MVP-016 — Consulta e atualização de chamados
- **Descrição:** Funções de leitura e mutação usadas pela API.
- **Prioridade:** P0 · **Depende de:** 015 · **Status:** Pendente
- **Arquivos:** `backend/app/db.py`
- **Critérios de aceitação:**
  - `listar_chamados(tipo=None, status=None, gravidade=None)` — 200 mais recentes, ordem decrescente
  - `obter_chamado(chamado_id)` → `dict | None`
  - `atualizar_chamado(chamado_id, status=None, observacao=None)` atualiza `updated_at`
  - `ack_chamado(chamado_id)` grava `acked_at` e muda status para `reconhecido`
- **Como validar:** `uv run pytest tests/test_db.py`

### MVP-017 — Máquina de estados (`estado_log`)
- **Descrição:** Toda transição de status é registrada append-only.
- **Prioridade:** P0 · **Depende de:** 015 · **Status:** Pendente
- **Arquivos:** `backend/app/db.py`
- **Critérios de aceitação:**
  - Toda mudança de `status` grava uma linha com `de`, `para`, `created_at`
  - `listar_estados(chamado_id)` devolve em ordem cronológica
  - Nenhuma linha é apagada ou editada
- **Como validar:** criar → ack → encerrar e conferir 3+ linhas em `estado_log`

### MVP-018 — Testes de persistência e idempotência
- **Descrição:** Cobrir criação, duplicata, listagem, filtros e transições.
- **Prioridade:** P0 · **Depende de:** 015–017 · **Status:** Pendente
- **Arquivos:** `backend/tests/test_db.py`
- **Critérios de aceitação:**
  - Reenviar o mesmo `evento_id` 3× resulta em **1** chamado
  - Protocolos são sequenciais e únicos
  - Filtros de listagem funcionam combinados
  - Usa banco temporário (`tmp_path`), nunca o `poto.db` real
- **Como validar:** `uv run pytest tests/test_db.py -v`

---

# Fase 3 — Triagem e merge protetivo

> Esta fase é o coração de segurança do produto. É aqui que o defeito mais grave do
> projeto antigo é corrigido pela raiz.

### MVP-019 — Portar datasets de triagem
- **Descrição:** Copiar os datasets de `../poto/scripts/` e ampliar com variações morfológicas.
- **Prioridade:** P0 · **Depende de:** 002 · **Status:** Pendente
- **Arquivos:** `backend/scripts/triagem_dataset.json`, `backend/scripts/bench_dataset.json`
- **Critérios de aceitação:**
  - Treino com ≥ 77 exemplos; held-out com 42, **sem sobreposição** com o treino
  - Cada item tem `texto`, `tipo` e `gravidade`
  - Acrescentadas variações que quebravam a heurística: `desmaiando`, `desmaiei`, `to passando mal`, `socorro`, `socorroo`, `tão me seguindo`
- **Como validar:** verificar que nenhum `texto` do bench aparece no treino

### MVP-020 — Classificador TF-IDF + LogReg
- **Descrição:** Motor de triagem offline, com degradação graciosa se o artefato não existir.
- **Prioridade:** P0 · **Depende de:** 019 · **Status:** Pendente
- **Arquivos:** `backend/app/triagem/classificador.py`
- **Critérios de aceitação:**
  - Interface: `classificar(texto) -> dict | None`, `treinar(dados) -> dict`, `disponivel() -> bool`, `status() -> dict`
  - Vectorizer combina n-gramas de **palavra e de caractere** (robustez a erro de digitação)
  - Dois classificadores: um para `tipo`, outro para `gravidade`
  - Retorna `tipo`, `gravidade`, `confianca`
  - Sem o artefato treinado, `disponivel()` é `False` e `classificar()` devolve `None` — **sem exceção**
  - Modelo carregado uma vez e mantido em memória
- **Como validar:** `uv run pytest tests/test_classificador.py`

### MVP-021 — Script de treino e avaliação
- **Descrição:** Treinar no dataset e reportar acurácia no held-out mais latência.
- **Prioridade:** P0 · **Depende de:** 020 · **Status:** Pendente
- **Arquivos:** `backend/scripts/train_classificador.py`
- **Critérios de aceitação:**
  - Treina em `triagem_dataset.json`, avalia em `bench_dataset.json`
  - Imprime acurácia de tipo, de gravidade, latência média e p95
  - **Linha de base a bater: ≥ 83% tipo, ≥ 85% gravidade, < 10 ms**
  - Salva em `POTO_CLF_PATH` (default `app/data/triagem_clf.joblib`)
  - Executa em menos de 30 s
- **Como validar:** `make train-clf` e conferir os números

### MVP-022 — Heurística de palavras-chave
- **Descrição:** Rede de segurança final, sem nenhuma dependência externa.
- **Prioridade:** P0 · **Depende de:** 009 · **Status:** Pendente
- **Arquivos:** `backend/app/triagem/heuristica.py`
- **Critérios de aceitação:**
  - Listas por tipo, mais `SINAIS_CRITICOS` e `SINAIS_AMEACA`
  - Texto sem categoria clara **mas** com sinal de ameaça → `seguranca` (protetivo), não `ouvidoria`
  - Normaliza acentos e caixa antes de casar
  - Devolve sempre um resultado válido, nunca `None`
- **Como validar:** `uv run pytest tests/test_heuristica.py`

### MVP-023 — Merge protetivo ★
- **Descrição:** A função que combina a trilha escolhida pela pessoa com a triagem do texto. **É a task mais importante do MVP.**
- **Prioridade:** P0 · **Depende de:** 012, 020, 022 · **Status:** Pendente
- **Arquivos:** `backend/app/triagem/merge.py`
- **Critérios de aceitação:**
  - `merge_acionamento(routing, triagem) -> dict`
  - `gravidade_final = max()` na ordem `orientacao(1) < risco_potencial(2) < risco_imediato(3)`
  - **Nunca** devolve gravidade menor que a do roteador para a trilha escolhida
  - Se a triagem sugere `ouvidoria` e a trilha é mais séria, vale a **trilha**
  - Sinal crítico no texto **promove** a gravidade
  - Canal final é recalculado coerente com o tipo final
  - Função pura, sem I/O — testável isoladamente
- **Como validar:** `uv run pytest tests/test_merge.py -v`

### MVP-024 — Fachada `triar()`
- **Descrição:** Porta única da triagem. O resto do sistema nunca sabe qual motor rodou.
- **Prioridade:** P0 · **Depende de:** 023 · **Status:** Pendente
- **Arquivos:** `backend/app/triagem/__init__.py`
- **Critérios de aceitação:**
  - `triar(texto, modo) -> dict` com `tipo`, `gravidade`, `confianca`, `canal_sugerido`, `fonte`
  - Precedência: classificador → heurística
  - `fonte` diz a **verdade**: `"classificador"` ou `"heuristica"` — nunca um motor que não rodou
  - Texto vazio ou `None` não quebra: devolve resultado neutro
- **Como validar:** `uv run pytest tests/test_triagem.py`

### MVP-025 — Suíte de regressão de segurança
- **Descrição:** Provar com frases reais que o sistema nunca rebaixa a proteção. Cada caso aqui é um defeito reproduzido no projeto antigo.
- **Prioridade:** P0 · **Depende de:** 024 · **Status:** Pendente
- **Arquivos:** `backend/tests/test_regressao_seguranca.py`
- **Critérios de aceitação — cada linha é um teste:**

  | Trilha | Texto | Resultado exigido |
  |---|---|---|
  | seguranca | *(sem texto)* | `risco_imediato` · `csv` |
  | seguranca | "socorro" | `risco_imediato` · **nunca** `orientacao` |
  | seguranca | "preciso de ajuda" | `risco_imediato` · **nunca** rebaixado |
  | seguranca | "um homem está me seguindo perto do bloco 7" | `risco_imediato` |
  | saude | "estou desmaiando" | `risco_imediato` · `samu_192` |
  | saude | "to passando mal" | `risco_imediato` · `samu_192` |
  | seguranca | "tem um cara armado no estacionamento" | `risco_imediato` · `csv` |
  | mulher | *(qualquer texto)* | `tela_neutra=True` · `feedback_sonoro=False` |
  | ouvidoria | "sugerir mais bancos no pátio" | `orientacao` · `ouvidoria` |

  - **Teste-invariante:** para toda trilha × texto do conjunto, a gravidade final é `>=` a gravidade que o roteador daria para a trilha sozinha
- **Como validar:** `uv run pytest tests/test_regressao_seguranca.py -v` — nenhum `xfail`

---

# Fase 4 — API

### MVP-026 — App FastAPI + lifespan + estático
- **Descrição:** Criar a aplicação, inicializar o banco no startup e montar o build do frontend.
- **Prioridade:** P0 · **Depende de:** 004, 014 · **Status:** Pendente
- **Arquivos:** `backend/app/main.py`
- **Critérios de aceitação:**
  - `lifespan` chama `init_db()` e inicia o worker de SLA
  - Se `frontend/dist/` existe, é montado na raiz servindo `index.html`
  - CORS restrito por `POTO_CORS_ORIGINS` (default: só localhost) — **nunca `*`**
  - `main.py` só monta routers; nenhuma regra de negócio
- **Como validar:** `make backend` e `curl localhost:8000/api/v1/health`

### MVP-027 — Hub de WebSocket
- **Descrição:** Gerenciar conexões do painel e transmitir eventos.
- **Prioridade:** P0 · **Depende de:** 026 · **Status:** Pendente
- **Arquivos:** `backend/app/hub.py`
- **Critérios de aceitação:**
  - `connect`, `disconnect`, `broadcast(evento, dados)`
  - Cliente que falha no envio é removido do conjunto — sem vazar conexão morta
  - `broadcast` sem clientes conectados não levanta exceção
- **Como validar:** `uv run pytest tests/test_hub.py`

### MVP-028 — Registry de canais + provider `log`
- **Descrição:** Arquitetura plugável de notificação, com payload mínimo por LGPD.
- **Prioridade:** P0 · **Depende de:** 011 · **Status:** Pendente
- **Arquivos:** `backend/app/canais/{__init__,base,log}.py`
- **Critérios de aceitação:**
  - `Protocol NotificationProvider` com `enviar(destino, mensagem, meta) -> (bool, str)`
  - `montar_mensagem(chamado)` inclui protocolo, tipo, gravidade e totem
  - **`texto_livre` NUNCA entra na mensagem** — teste explícito para isso
  - Provider escolhido por `POTO_NOTIF_PROVIDER`, default `log`
  - Toda tentativa é gravada em `notificacoes`
- **Como validar:** `uv run pytest tests/test_canais.py::test_payload_sem_relato`

### MVP-029 — Provider `webhook`
- **Descrição:** POST JSON para Evolution API / n8n, para WhatsApp real.
- **Prioridade:** P0 · **Depende de:** 028 · **Status:** Pendente
- **Arquivos:** `backend/app/canais/webhook.py`
- **Critérios de aceitação:**
  - `POST {number, text, meta}` para `POTO_NOTIF_WEBHOOK_URL`
  - Timeout de 10 s; falha devolve `(False, detalhe)` **sem** levantar exceção
  - Falha de rede não impede a criação do chamado — o registro vem primeiro
- **Como validar:** `uv run pytest tests/test_canais.py` com `httpx` mockado

### MVP-030 — `POST /eventos`
- **Descrição:** O endpoint principal: triagem, merge protetivo, roteamento, persistência, broadcast e notificação.
- **Prioridade:** P0 · **Depende de:** 024, 027, 028 · **Status:** Pendente
- **Arquivos:** `backend/app/api/eventos.py`
- **Critérios de aceitação:**
  - Ordem: `triar()` → `rotear()` → `merge_acionamento()` → `criar_chamado()` → `broadcast` → `notificar`
  - **Usa `merge_acionamento()`; jamais sobrescreve a gravidade do roteador**
  - `evento_id` repetido → `201` com `duplicado=True`, sem notificar de novo
  - Falha de notificação → status `falha_notificacao`, mas o chamado **existe**
  - Responde em < 2 s
- **Como validar:** `uv run pytest tests/test_api_eventos.py`

### MVP-031 — `POST /panico`
- **Descrição:** Broadcast paralelo para os canais internos, com status persistente.
- **Prioridade:** P0 · **Depende de:** 030 · **Status:** Pendente
- **Arquivos:** `backend/app/api/eventos.py`
- **Critérios de aceitação:**
  - Roteia como `seguranca` + `emergencia=True`, **sem passar por triagem de texto**
  - Aciona `CANAIS_INTERNOS` em paralelo (`asyncio.gather`)
  - Status final `alerta_ativo` — persistente, não fecha sozinho
  - Devolve `escalonamento_disponivel` com os 4 canais do estado
  - Idempotente por `evento_id`
- **Como validar:** `uv run pytest tests/test_api_panico.py`

### MVP-032 — `GET /chamados` e `GET /chamados/{id}`
- **Descrição:** Leitura para o painel.
- **Prioridade:** P0 · **Depende de:** 016 · **Status:** Pendente
- **Arquivos:** `backend/app/api/chamados.py`
- **Critérios de aceitação:**
  - Filtros `tipo`, `status`, `gravidade` combináveis
  - Detalhe inclui `notificacoes` e `estados`
  - `404` para id inexistente
- **Como validar:** `curl "localhost:8000/api/v1/chamados?gravidade=risco_imediato"`

### MVP-033 — `POST /chamados/{id}/ack` e `PATCH`
- **Descrição:** Operador reconhece e movimenta o chamado.
- **Prioridade:** P0 · **Depende de:** 016, 027 · **Status:** Pendente
- **Arquivos:** `backend/app/api/chamados.py`
- **Critérios de aceitação:**
  - `ack` grava `acked_at`, muda para `reconhecido` e faz broadcast `atualizado`
  - `PATCH` aceita `status` e `observacao`, registrando em `estado_log`
  - Ambos devolvem o chamado atualizado
- **Como validar:** `uv run pytest tests/test_api_chamados.py`

### MVP-034 — `POST /chamados/{id}/escalonar`
- **Descrição:** Acionamento manual de autoridade do estado, sem encerrar o alerta.
- **Prioridade:** P0 · **Depende de:** 028, 032 · **Status:** Pendente
- **Arquivos:** `backend/app/api/chamados.py`
- **Critérios de aceitação:**
  - Aceita só canais de `CANAIS_ESTADO`; outro valor → `422`
  - **Registra o acionamento humano; não robo-disca**
  - Grava em `notificacoes` com `escalonamento=1`
  - Não rebaixa `alerta_ativo`
- **Como validar:** `uv run pytest tests/test_api_chamados.py::test_escalonar`

### MVP-035 — `WS /ws`
- **Descrição:** Canal de tempo real do painel.
- **Prioridade:** P0 · **Depende de:** 027 · **Status:** Pendente
- **Arquivos:** `backend/app/api/chamados.py`
- **Critérios de aceitação:**
  - Envia `conectado` ao abrir
  - Transmite `novo_chamado` e `atualizado`
  - `ping` a cada 30 s para manter viva
  - Desconexão não derruba o servidor nem vaza memória
- **Como validar:** `websocat ws://localhost:8000/api/v1/ws` e disparar um evento

### MVP-036 — `GET /health` honesto
- **Descrição:** Diagnóstico que reflete a realidade — corrige o defeito em que o antigo afirmava usar IA sem usar.
- **Prioridade:** P0 · **Depende de:** 024, 028 · **Status:** Pendente
- **Arquivos:** `backend/app/api/sistema.py`
- **Critérios de aceitação:**
  - `triagem.modo` é `classificador` **somente** se o artefato está carregado; senão `heuristica`
  - Reporta provider de notificação e se o banco responde
  - Campo `avisos[]` alerta quando a triagem está degradada
- **Como validar:** renomear o `.joblib`, reiniciar, e conferir que `/health` diz `heuristica`

### MVP-037 — `GET /config` e `GET /canais`
- **Descrição:** Expor ao frontend as constantes que ele não deve duplicar.
- **Prioridade:** P0 · **Depende de:** 011 · **Status:** Pendente
- **Arquivos:** `backend/app/api/sistema.py`
- **Critérios de aceitação:**
  - `/config` devolve `sla`, `canais_estado`, `totem_offline_seg`
  - `/canais` devolve o catálogo com nomes legíveis
  - **Nenhum valor de SLA ou lista de canais fica hardcoded no frontend**
- **Como validar:** `grep -rn "120\|600" frontend/src/` não encontra prazos de SLA

### MVP-038 — Worker de SLA e escalonamento
- **Descrição:** Loop que escalona chamados sem ACK no prazo.
- **Prioridade:** P0 · **Depende de:** 030, 033 · **Status:** Pendente
- **Arquivos:** `backend/app/sla.py`
- **Critérios de aceitação:**
  - Roda a cada `POTO_SLA_CHECK_INTERVAL` (default 30 s)
  - `notificado` sem ACK além do prazo → notifica o `fallback`, status `escalonado`, broadcast
  - `orientacao` nunca escalona
  - Escalona **uma única vez** por chamado
  - Exceção no loop não derruba o worker
- **Como validar:** `uv run pytest tests/test_sla.py` com prazos reduzidos

### MVP-039 — Testes de contrato da API
- **Descrição:** Cobertura ponta a ponta com `TestClient`.
- **Prioridade:** P0 · **Depende de:** 030–038 · **Status:** Pendente
- **Arquivos:** `backend/tests/test_api_*.py`
- **Critérios de aceitação:**
  - Cada trilha × modo × com/sem texto verifica que a gravidade **nunca cai**
  - Idempotência verificada via HTTP
  - Banco temporário por teste
  - `make test` verde de ponta a ponta
- **Como validar:** `make test`

### MVP-040 — Autenticação por token no painel
- **Descrição:** Fechar a leitura e escrita do painel, mantendo o acionamento aberto.
- **Prioridade:** P1 · **Depende de:** 032 · **Status:** Pendente
- **Arquivos:** `backend/app/api/deps.py`
- **Critérios de aceitação:**
  - `X-POTO-Token` comparado a `POTO_PAINEL_TOKEN`
  - Exigido em `/chamados*`, `/ws`
  - **`/eventos` e `/panico` permanecem abertos** — um totem em pânico não falha por credencial
  - Sem token configurado, loga aviso e libera (modo desenvolvimento)
- **Como validar:** `curl localhost:8000/api/v1/chamados` → `401`

---

# Fase 5 — Design system

### MVP-041 — Fontes auto-hospedadas
- **Descrição:** Baixar Michroma, Inter e Material Symbols para `public/fonts/`. No projeto antigo vinham de CDN e quebravam offline — inclusive **todos os ícones dos botões**.
- **Prioridade:** P0 · **Depende de:** 003 · **Status:** Pendente
- **Arquivos:** `frontend/public/fonts/`, `frontend/src/estilos/base.css`
- **Critérios de aceitação:**
  - `.woff2` locais de Michroma 400, Inter 400/500/600/700 e Material Symbols Rounded
  - `@font-face` com `font-display: swap`
  - **Zero referência a `fonts.googleapis.com` ou `fonts.gstatic.com`**
- **Como validar:** DevTools → Network offline → recarregar: tipografia e ícones intactos; `grep -rn "googleapis" frontend/` vazio

### MVP-042 — `tokens.css` e `base.css`
- **Descrição:** Portar literalmente os tokens do POTO (PLAN.md §6).
- **Prioridade:** P0 · **Depende de:** 003 · **Status:** Pendente
- **Arquivos:** `frontend/src/estilos/tokens.css`, `base.css`
- **Critérios de aceitação:**
  - Todos os tokens de cor, raio, espaço, tipografia, sombra e `--touch: 64px`
  - Valores hex **idênticos** aos de PLAN.md §6
  - `base.css` define reset, `body` com `--paper`, foco `outline: 3px var(--rust)`
  - `@media (prefers-reduced-motion: reduce)` desliga animações
- **Como validar:** comparar `tokens.css` com PLAN.md §6, valor a valor

### MVP-043 — Componente `<Sym>` (ícones)
- **Descrição:** Wrapper de Material Symbols Rounded com os tamanhos do POTO.
- **Prioridade:** P0 · **Depende de:** 041, 042 · **Status:** Pendente
- **Arquivos:** `frontend/src/componentes/Sym.tsx`
- **Critérios de aceitação:**
  - Tamanhos `xs:18 · sm:22 · md:28 · lg:40 · xl:56`
  - Glifos: `stethoscope`, `shield`, `female`, `info`, `emergency`, `check`, `arrow_back`
  - `aria-hidden="true"` (o rótulo textual carrega o significado)
- **Como validar:** renderizar os 4 ícones das trilhas e conferir contra `Tela-Totem.png`

### MVP-044 — `<Wordmark>` e `<StatusPill>`
- **Descrição:** Marca e indicador de conectividade do header.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** Pendente
- **Arquivos:** `frontend/src/componentes/{Wordmark,StatusPill}.tsx`
- **Critérios de aceitação:**
  - Wordmark: Michroma 16px, `letter-spacing: .14em`, UPPERCASE, **pontos em `--rust`**
  - Clicar no wordmark volta à tela inicial
  - StatusPill: ponto 8px — verde `--ok` online, ferrugem `--rust` offline
  - Mostra `· N na fila` quando há eventos pendentes
- **Como validar:** alternar online/offline no DevTools e observar a mudança

### MVP-045 — Componente `<Choice>`
- **Descrição:** O botão-cartão das trilhas — o elemento mais importante da interface.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** Pendente
- **Arquivos:** `frontend/src/componentes/Choice.tsx`
- **Critérios de aceitação:**
  - `min-height: 168px`, `padding: 28px 16px`, borda `1.5px var(--line)`, raio `var(--r-lg)`
  - Ícone 56px em `--rust`; variante `muted` usa `--muted`
  - Rótulo em Michroma 13px, `letter-spacing: .04em`, centrado
  - Hover → borda `--rust` + fundo `--rust-soft`; active → `scale(.97)`
  - Alvo de toque ≥ 64px; foco visível
- **Como validar:** comparação lado a lado com `../poto-pitch/capturas-de-tela/Tela-Totem.png`

### MVP-046 — Componente `<Panic>` com pressionar-e-segurar
- **Descrição:** Botão de pânico — sempre o elemento de maior peso visual da tela. Como é
  virtual (não físico), precisa de intenção deliberada: **segurar por 1 s**. Um botão de
  toque simples numa tela pública dispara com um roçar de mão, e cada disparo faz broadcast
  real para CSV e Sala Lilás.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** Pendente
- **Arquivos:** `frontend/src/componentes/Panic.tsx`
- **Critérios de aceitação — visual:**
  - Largura total, cápsula (`--r-pill`), fundo `--rust`, texto branco
  - `min-height: 64px`, Michroma 14px UPPERCASE `letter-spacing: .1em`
  - Ícone `emergency` 32px branco; hover → `--rust-d`
- **Critérios de aceitação — acionamento:**
  - Dispara somente após **1000 ms** de pressão contínua
  - Anel/barra de progresso preenchendo durante a pressão — o usuário vê que está funcionando
  - Soltar antes de completar **cancela** e volta ao estado inicial, **sem enviar nada**
  - `navigator.vibrate(200)` ao completar (com guarda: a API pode não existir)
  - Funciona com `pointerdown`/`pointerup` (cobre toque e mouse), com `pointercancel` tratado
  - Rótulo muda para "Segure para acionar" enquanto pressionado
  - Acessível por teclado: `Enter`/`Espaço` mantidos pressionados têm o mesmo efeito
  - `prefers-reduced-motion`: o anel vira degraus discretos em vez de animação contínua
  - **Não** abre tela de confirmação — nada que exija decisão na emergência
- **Como validar:** segurar 1 s e ver o chamado; tocar rapidamente 5× seguidas e confirmar
  que **nenhum** chamado foi criado

### MVP-047 — Componente `<Confirm>`
- **Descrição:** Tela de confirmação nas três variantes: neutra, padrão e crítica.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** Pendente
- **Arquivos:** `frontend/src/componentes/Confirm.tsx`
- **Critérios de aceitação:**
  - Marca circular com ✓, título e protocolo em tabular
  - Variante `critico`: fundo `--rust`, texto branco
  - Variante `neutral`: fundo `--paper`, ícone `--muted`, **sem protocolo**
  - Aviso de offline em faixa `--rust-soft`
- **Como validar:** renderizar as três variantes lado a lado

---

# Fase 6 — Telas do totem

### MVP-048 — Cliente de API tipado
- **Descrição:** Camada única de acesso ao backend, com tipos derivados dos contratos.
- **Prioridade:** P0 · **Depende de:** 010, 030 · **Status:** Pendente
- **Arquivos:** `frontend/src/comum/{api.ts,tipos.ts}`
- **Critérios de aceitação:**
  - `novoEvento()` gera `evento_id` com `crypto.randomUUID()` **antes** do envio
  - `enviarEvento()`, `listarChamados()`, `ackChamado()`, `obterConfig()`
  - Base da API derivada de `location.origin` (dev usa proxy do Vite)
  - Erro de rede levanta exceção tipada para a fila tratar
- **Como validar:** `npm run build` sem erro de tipo

### MVP-049 — Shell do totem
- **Descrição:** As três zonas de DESIGN.md §12: header, main centralizado, footer.
- **Prioridade:** P0 · **Depende de:** 044 · **Status:** Pendente
- **Arquivos:** `frontend/src/totem/Totem.tsx`
- **Critérios de aceitação:**
  - `max-width: 960px`, `padding: clamp(20px, 4vw, 48px)`, `min-height: 100dvh`
  - Header: wordmark à esquerda, status à direita
  - Main: `flex: 1`, centralizado vertical e horizontalmente
  - Footer: `margin-top: auto`
  - `overflow: hidden` e `user-select: none` (kiosk)
- **Como validar:** abrir em 1280×800 sem barra de rolagem

### MVP-050 — Tela inicial com as 4 trilhas
- **Descrição:** "Como podemos ajudar?" com a grade 2×2 e o pânico no rodapé.
- **Prioridade:** P0 · **Depende de:** 045, 046, 049 · **Status:** Pendente
- **Arquivos:** `frontend/src/totem/telas/Home.tsx`
- **Critérios de aceitação:**
  - Título em Michroma `clamp(28px, 4.5vw, 44px)`
  - Trilhas na ordem: Emergência médica · Segurança · Assédio/Sala Lilás · Outros
  - "Outros" com variante `muted`; "Assédio/Sala Lilás" dispara `modo: discreto`
  - Grade `1fr 1fr`, `gap: 16px`; 1 coluna abaixo de 560px
  - **Todo o fluxo principal em ≤ 2 toques**
- **Como validar:** abrir e conferir contra `Tela-Totem.png`

### MVP-051 — Fluxo de acionamento e confirmação
- **Descrição:** Toque → POST → tela de confirmação com protocolo.
- **Prioridade:** P0 · **Depende de:** 047, 048, 050 · **Status:** Pendente
- **Arquivos:** `frontend/src/totem/Totem.tsx`
- **Critérios de aceitação:**
  - Estado de carregamento durante o POST; botões desabilitados (sem duplo toque)
  - Confirmação usa `instrucao_totem` **do backend**, não lógica do cliente
  - `feedback_sonoro` toca um beep de 660 Hz por 0,12 s
  - Erro de rede não trava a tela — cai na fila (MVP-057)
  - Do toque à confirmação em < 2 s
- **Como validar:** acionar cada trilha e conferir o chamado no banco

### MVP-052 — Retorno automático à tela inicial
- **Descrição:** O totem sempre volta sozinho ao repouso.
- **Prioridade:** P0 · **Depende de:** 051 · **Status:** Pendente
- **Arquivos:** `frontend/src/totem/telas/Confirmacao.tsx`
- **Critérios de aceitação:**
  - **5 s** discreto · **12 s** crítico · **9 s** demais
  - Timer limpo ao desmontar (sem vazamento)
  - Alerta ativo de pânico **não** tem retorno automático — é persistente
- **Como validar:** cronometrar cada variante

### MVP-053 — Modo discreto
- **Descrição:** A trilha mulher não pode deixar rastro na tela.
- **Prioridade:** P0 · **Depende de:** 051 · **Status:** Pendente
- **Arquivos:** `frontend/src/totem/telas/Confirmacao.tsx`
- **Critérios de aceitação — verificados na tela:**
  - Mensagem genérica "Seu pedido foi registrado. Aguarde atendimento."
  - **Sem protocolo visível**
  - **Sem som** (`feedback_sonoro: false`)
  - Sem menção a "Sala Lilás", "denúncia" ou ao canal acionado
  - Retorno em 5 s
  - Decidido pelo backend via `tela_neutra`, não por condicional no cliente
- **Como validar:** acionar a trilha e inspecionar o DOM — nenhuma dessas palavras presente

### MVP-054 — Tela de alerta ativo (pânico)
- **Descrição:** Estado persistente com cronômetro e escalonamento manual.
- **Prioridade:** P0 · **Depende de:** 031, 051 · **Status:** Pendente
- **Arquivos:** `frontend/src/totem/telas/AlertaAtivo.tsx`
- **Critérios de aceitação:**
  - Fundo `--rust`, ícone pulsante, protocolo grande em tabular
  - Cronômetro `MM:SS` desde o acionamento
  - Status ao vivo por WS: "Aguardando central" → "Central recebeu" → "Atendimento a caminho"
  - 4 botões de escalonamento; cada um vira ✓ verde inline após acionar
  - **Não sai sozinho** — só pelo botão "Voltar ao início"
- **Como validar:** acionar pânico, dar ACK no painel e ver o status mudar no totem

### MVP-055 — Layout fluido: tablet (duas orientações) e desktop
- **Descrição:** A tela do totem é um **Galaxy Tab A11 de 8.7" (1340×800)** e precisa
  funcionar em retrato e paisagem, sem deixar de funcionar no desktop. O caso difícil é a
  paisagem: sobram ~530px de **altura** para cabeçalho, título, 4 alvos e o pânico.
- **Prioridade:** P0 · **Depende de:** 050, 054 · **Status:** Pendente
- **Arquivos:** `frontend/src/estilos/{base,totem}.css`
- **Critérios de aceitação:**
  - **Medir primeiro:** registrar `window.innerWidth/innerHeight` reais do Tab A11 nas
    duas orientações e anotar em `docs/viewports.md`. Não projetar contra número suposto.
  - **Sem rolagem** na tela inicial em: tablet retrato, tablet paisagem, 1280×800 e 1920×1080
  - Grade adapta o arranjo por orientação:
    - retrato e desktop → **2×2**
    - `(orientation: landscape) and (max-height: 620px)` → **4 colunas**, cartão com
      `min-height: 120px`, ícone `lg` (40px) em vez de `xl`
    - `max-width: 480px` → 1 coluna
  - **Alvos de toque ≥ 64px em todos os casos** — nunca reduzidos para caber
  - `100dvh` em vez de `100vh` (a barra do Chrome no Android entra e sai)
  - `clamp()` no título, espaçamentos e ícones — escala contínua tablet→desktop
  - `touch-action: manipulation` (sem zoom por duplo toque)
  - Painel (`/painel`) não quebra se aberto no tablet
- **Como validar:** no aparelho real, nas duas orientações, com `document.body.scrollHeight
  === window.innerHeight`; e no DevTools em 1280×800 e 1920×1080

### MVP-055b — Manifest e modo autônomo no tablet
- **Descrição:** Fazer o Chrome abrir a aplicação em tela cheia, sem barra de endereço.
- **Prioridade:** P0 · **Depende de:** 055 · **Status:** Pendente
- **Arquivos:** `frontend/public/manifest.webmanifest`, `index.html`
- **Critérios de aceitação:**
  - `display: "fullscreen"`, `orientation: "any"` (o layout se adapta — não travar)
  - `theme_color: "#C0392B"`, `background_color: "#FBF9F6"`, ícones 192 e 512
  - "Adicionar à tela inicial" abre sem barra de endereço
  - `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`
- **Como validar:** adicionar à tela inicial no Tab A11 e abrir pelo ícone

### MVP-056 — Acessibilidade AA
- **Descrição:** Contraste, foco e semântica.
- **Prioridade:** P1 · **Depende de:** 055 · **Status:** Pendente
- **Arquivos:** `frontend/src/componentes/*`
- **Critérios de aceitação:**
  - Contraste AA em todos os pares de cor
  - `aria-label` nos 4 botões de trilha e no pânico
  - Foco visível em todos os interativos
  - **Cor nunca é o único sinal** — gravidade tem cor + rótulo + ícone
- **Como validar:** Lighthouse Accessibility ≥ 95 e navegação só por teclado

---

# Fase 7 — Operação offline

### MVP-057 — Fila offline em `localStorage`
- **Descrição:** O totem não pode parar porque a rede parou.
- **Prioridade:** P0 · **Depende de:** 048 · **Status:** Pendente
- **Arquivos:** `frontend/src/comum/fila.ts`
- **Critérios de aceitação:**
  - Falha de POST enfileira o evento **com o `evento_id` já gerado**
  - `enfileirar()`, `pendentes()`, `drenar()`
  - Confirmação **imediata** na tela — a pessoa não percebe diferença
  - `localStorage` cheio ou bloqueado não quebra a aplicação
- **Como validar:** desligar o backend, acionar 3 trilhas, conferir 3 itens na fila

### MVP-058 — Dreno automático e badge de fila
- **Descrição:** Reenvio ao voltar a conectividade.
- **Prioridade:** P0 · **Depende de:** 057 · **Status:** Pendente
- **Arquivos:** `frontend/src/comum/fila.ts`, `StatusPill.tsx`
- **Critérios de aceitação:**
  - Dreno no evento `online` e a cada 15 s
  - Badge "N na fila" visível no header
  - Item drenado com sucesso sai da fila; falha permanece
  - Dreno é serial (não dispara N requisições simultâneas)
- **Como validar:** religar o backend e ver a fila esvaziar sozinha

### MVP-059 — Re-triagem protetiva no dreno
- **Descrição:** Fechar a versão offline do defeito de rebaixamento. No projeto antigo, conversa sem rede virava sempre `ouvidoria`.
- **Prioridade:** P0 · **Depende de:** 023, 058 · **Status:** Pendente
- **Arquivos:** `backend/app/api/eventos.py`
- **Critérios de aceitação:**
  - Evento drenado com `texto_livre` passa por `merge_acionamento()` na chegada
  - Evento enfileirado como `ouvidoria` com texto grave é **promovido**
  - Idempotência preservada: re-envio do mesmo `evento_id` não duplica
- **Como validar:** enfileirar `{tipo: ouvidoria, texto: "socorro tem um homem me seguindo"}`, drenar, e verificar promoção

---

# Fase 8 — Painel da central

### MVP-060 — Shell e lista do painel
- **Descrição:** Visão operacional dos chamados.
- **Prioridade:** P0 · **Depende de:** 032, 042 · **Status:** Pendente
- **Arquivos:** `frontend/src/painel/Painel.tsx`, `ListaChamados.tsx`
- **Critérios de aceitação:**
  - Rota `/painel` no mesmo build
  - Carrega `GET /chamados` no mount
  - Mais recentes primeiro; críticos no topo
  - Estado vazio com mensagem clara
- **Como validar:** `make seed` e abrir `/painel`

### MVP-061 — Card de chamado com gravidade
- **Descrição:** O cartão que o operador lê em um relance.
- **Prioridade:** P0 · **Depende de:** 060 · **Status:** Pendente
- **Arquivos:** `frontend/src/painel/CardChamado.tsx`
- **Critérios de aceitação:**
  - **Borda esquerda de 5px** na cor da gravidade: `--crit` · `--warn` · `--info`
  - Protocolo em tabular, tipo, canal roteado, horário, totem
  - Chip de status legível
  - Gravidade tem cor **+ rótulo** (nunca só cor)
- **Como validar:** conferir contra `../poto-pitch/capturas-de-tela/Tela-Central-painel.png`

### MVP-062 — WebSocket em tempo real
- **Descrição:** O painel acende sozinho, sem recarregar.
- **Prioridade:** P0 · **Depende de:** 035, 060 · **Status:** Pendente
- **Arquivos:** `frontend/src/comum/ws.ts`
- **Critérios de aceitação:**
  - `novo_chamado` insere o card no topo em **< 1 s**
  - `atualizado` atualiza o card no lugar, sem piscar a lista
  - Reconexão automática com backoff
  - Indicador de conexão do WS visível
- **Como validar:** totem e painel em duas abas; acionar e cronometrar

### MVP-063 — ACK e mudança de estado
- **Descrição:** Ações do operador.
- **Prioridade:** P0 · **Depende de:** 033, 061 · **Status:** Pendente
- **Arquivos:** `frontend/src/painel/CardChamado.tsx`
- **Critérios de aceitação:**
  - Botão "Reconhecer" chama `/ack` e some após sucesso
  - Seletor de estado: `em_atendimento`, `encerrado`
  - Mudança reflete no totem via WS (visível no alerta ativo)
  - Botão desabilitado durante a requisição
- **Como validar:** dar ACK e ver o totem mudar para "A central recebeu seu alerta"

### MVP-064 — Contador de SLA ao vivo
- **Descrição:** O prazo correndo na tela — o fail-safe visível.
- **Prioridade:** P0 · **Depende de:** 037, 061 · **Status:** Pendente
- **Arquivos:** `frontend/src/painel/CardChamado.tsx`
- **Critérios de aceitação:**
  - "Responder em M:SS" regressivo, atualizando a cada segundo
  - Prazos vindos de `GET /config` — **não hardcoded**
  - Ao estourar, faixa "SLA expirado"
  - Sem contador em `orientacao`
- **Como validar:** criar chamado crítico e observar até estourar os 120 s

### MVP-065 — Filtros e busca
- **Descrição:** Encontrar um chamado entre muitos.
- **Prioridade:** P1 · **Depende de:** 060 · **Status:** Pendente
- **Arquivos:** `frontend/src/painel/Painel.tsx`
- **Critérios de aceitação:**
  - Filtros por gravidade e status, com contadores
  - Busca por protocolo ou totem
  - Filtros combináveis; botão de limpar
- **Como validar:** com 20 chamados semeados, filtrar e conferir

---

# Fase 8b — Câmera e microfone da Pi

> A câmera e o microfone estão na Pi, que é headless — nenhum navegador os enxerga. A
> captura é **server-side**, transmitida em MJPEG, e **só existe sob demanda da central**,
> vinculada a um chamado ativo. Ver ARCHITECTURE.md D7.

### MVP-073 — Detecção de dispositivos e `GET /dispositivos`
- **Descrição:** Descobrir no boot quais câmeras e microfones a Pi tem e expor a lista.
- **Prioridade:** P0 · **Depende de:** 026 · **Status:** Pendente
- **Arquivos:** `backend/app/midia/__init__.py`, `backend/app/api/midia.py`
- **Critérios de aceitação:**
  - Detecta câmera CSI (via `picamera2`) e câmeras USB (via `/dev/video*`)
  - Detecta entradas de áudio via ALSA
  - `GET /dispositivos` devolve `[{id, tipo, nome, dono, status, capacidades}]`
  - `dono` é o identificador da Pi — o campo já existe para, no futuro, listar dispositivos de outros aparelhos
  - **Sem hardware nenhum, devolve lista vazia** e a API sobe normalmente (degradação graciosa)
- **Como validar:** `curl localhost:8000/api/v1/dispositivos` com e sem câmera plugada

### MVP-074 — Captura de vídeo
- **Descrição:** Abstrair as duas origens possíveis de câmera atrás de uma interface só.
- **Prioridade:** P0 · **Depende de:** 073 · **Status:** Pendente
- **Arquivos:** `backend/app/midia/camera.py`
- **Critérios de aceitação:**
  - Interface única `abrir(id) -> gerador de frames JPEG`
  - `CameraCSI` com `picamera2` (JPEG direto do ISP) e `CameraUSB` com V4L2
  - Resolução e FPS configuráveis (default **640×480 a 10 fps** — suficiente e barato)
  - Liberar a câmera ao encerrar; nunca deixar o dispositivo travado
  - Duas sessões simultâneas no mesmo dispositivo **compartilham** um único capturador
- **Como validar:** `uv run pytest tests/test_camera.py` com captura falsa; na Pi, capturar 10 frames

### MVP-075 — Stream MJPEG
- **Descrição:** Entregar o vídeo ao painel sem WebRTC nem biblioteca.
- **Prioridade:** P0 · **Depende de:** 074, 077 · **Status:** Pendente
- **Arquivos:** `backend/app/api/midia.py`
- **Critérios de aceitação:**
  - `GET /midia/camera/{id}/stream` com `multipart/x-mixed-replace; boundary=frame`
  - Renderiza em `<img src="…">` sem nenhum JavaScript
  - Cliente desconectado encerra o gerador (sem vazar thread nem processo)
  - **Sem `sessao` válida → `403`**
  - Latência na LAN abaixo de 1 s
- **Como validar:** abrir a URL no navegador e ver imagem ao vivo; fechar a aba e confirmar que a captura para

### MVP-076 — Captura e stream de áudio
- **Descrição:** Ouvir o local do totem durante um chamado.
- **Prioridade:** P0 · **Depende de:** 073, 077 · **Status:** Pendente
- **Arquivos:** `backend/app/midia/microfone.py`
- **Critérios de aceitação:**
  - Captura ALSA (`sounddevice` ou `arecord`), 16 kHz mono — voz não precisa de mais
  - `GET /midia/microfone/{id}/stream` em `audio/wav` por chunks, tocável num `<audio>`
  - **Sem `sessao` válida → `403`**
  - **Fallback documentado:** se o streaming contínuo se mostrar instável, clipe de 15 s sob demanda
- **Como validar:** abrir o stream no painel e ouvir; medir atraso falando perto do microfone

### MVP-077 — Sessão de mídia com auditoria ★
- **Descrição:** O controle que impede a câmera de virar vigilância. **Nenhum stream existe fora disso.**
- **Prioridade:** P0 · **Depende de:** 073, 017 · **Status:** Pendente
- **Arquivos:** `backend/app/midia/sessao.py`, `backend/app/api/midia.py`
- **Critérios de aceitação:**
  - `POST /chamados/{id}/midia {dispositivo_id}` → `{sessao_id, stream_url, expira_em}`
  - **Recusa** (`409`) se o chamado estiver `encerrado` ou `cancelado`
  - Sessão **expira sozinha em 10 min**; renovação exige nova requisição
  - `DELETE /chamados/{id}/midia` encerra imediatamente
  - **Abertura e fechamento gravam linha de auditoria** com dispositivo, operador e duração
  - Sem sessão, os endpoints de stream devolvem `403` — **testado explicitamente**
- **Como validar:** `uv run pytest tests/test_midia_sessao.py` — inclui o teste de que não há stream sem chamado ativo

### MVP-078 — Visualização no painel
- **Descrição:** O operador escolhe o dispositivo e vê/ouve, dentro do chamado.
- **Prioridade:** P0 · **Depende de:** 063, 075, 076 · **Status:** Pendente
- **Arquivos:** `frontend/src/painel/MidiaChamado.tsx`
- **Critérios de aceitação:**
  - Botão "Ver câmera" só aparece em chamado **ativo** e com dispositivo disponível
  - Seletor lista o que veio de `GET /dispositivos`, com status
  - Vídeo em `<img>`, áudio em `<audio>`; indicador visível de **AO VIVO**
  - Fechar o painel ou o chamado encerra a sessão (`DELETE`)
  - Sem dispositivo disponível, mensagem clara — não um quadro preto
- **Como validar:** abrir um chamado ativo, ver a imagem, fechar e confirmar na auditoria as duas linhas

### MVP-079 — Custo de CPU e latência na Pi
- **Descrição:** Provar que a mídia não compete com o núcleo. A Pi 5 **não tem encoder H.264 por hardware** — é por isso que o transporte é MJPEG.
- **Prioridade:** P0 · **Depende de:** 075, 076 · **Status:** Pendente
- **Arquivos:** `docs/aceite-mvp.md`
- **Critérios de aceitação:**
  - Com 1 stream de vídeo ativo: **CPU da Pi abaixo de 50%** e temperatura estável
  - Acionar uma trilha **durante** um stream ativo continua respondendo em < 2 s
  - Latência de vídeo medida (cronômetro filmado) abaixo de 1 s
  - Se estourar: reduzir para 320×240 ou 5 fps e registrar o novo limite
- **Como validar:** `htop` na Pi durante 5 min de stream, com acionamentos em paralelo

---

# Fase 9 — Raspberry Pi

### MVP-066 — Build integrado servido pelo backend
- **Descrição:** Um processo só. **Aqui se verifica explicitamente o defeito que quebrou o kiosk do projeto antigo.**
- **Prioridade:** P0 · **Depende de:** 026, 055, 060 · **Status:** Pendente
- **Arquivos:** `Makefile`, `backend/app/main.py`
- **Critérios de aceitação:**
  - `make build` gera `frontend/dist/` **com `index.html`, CSS, JS e fontes**
  - `GET /` → **200** com a aplicação (não 404, não JSON)
  - `GET /painel` → 200
  - Fontes carregam de `/fonts/`
  - Funciona **sem** o servidor de desenvolvimento do Vite
  - uvicorn em `--host 0.0.0.0`: **acessível de outro dispositivo da rede**, não só de `localhost`
- **Como validar:** `make build && make backend`, depois `curl -o /dev/null -w "%{http_code}" http://<ip-da-pi>:8000/` → `200` **de outra máquina**

### MVP-067 — Unit systemd na Pi
- **Descrição:** Um único serviço que sobe sozinho no boot. Sem unit de kiosk (o navegador
  roda no tablet) e sem unit de GPIO (o pânico é virtual). A Pi opera **headless**.
- **Prioridade:** P0 · **Depende de:** 066 · **Status:** Pendente
- **Arquivos:** `deploy/poto-api.service`
- **Critérios de aceitação:**
  - uvicorn **sem `--reload`**, `--host 0.0.0.0` (o tablet precisa alcançar)
  - `Restart=always`, `RestartSec=3`, `EnvironmentFile`, `After=network-online.target`
  - Funciona com a Pi sem monitor, teclado ou periférico conectado
  - `journalctl -u poto-api` mostra os logs da aplicação
- **Como validar:** `systemctl status poto-api` após reboot, com a Pi headless

### MVP-067b — Endereçamento estável da Pi
- **Descrição:** O tablet abre uma URL fixa; ela não pode mudar a cada reboot.
- **Prioridade:** P0 · **Depende de:** 067 · **Status:** Pendente
- **Arquivos:** `deploy/install-pi.sh`
- **Critérios de aceitação:**
  - `avahi-daemon` instalado e ativo; hostname `poto` → `poto.local` resolve
  - IP estático documentado como plano B (reserva DHCP ou `dhcpcd.conf`)
  - O script imprime **as duas** URLs ao final
  - `curl http://poto.local:8000/api/v1/health` responde de outro dispositivo da rede
- **Como validar:** do tablet, abrir `http://poto.local:8000` e carregar a aplicação

### MVP-067c — Kiosk no Galaxy Tab A11
- **Descrição:** Travar o tablet na aplicação, sem barra de endereço e sem sair por acidente.
- **Prioridade:** P0 · **Depende de:** 055b, 067b · **Status:** Pendente
- **Arquivos:** `docs/setup-tablet.md`
- **Critérios de aceitação — documentados passo a passo:**
  - Aplicação adicionada à tela inicial, abrindo em tela cheia
  - **Fixação de tela** (Configurações → Segurança) ativa, com PIN para sair
  - Tempo de tela desligada = **nunca**; brilho fixo
  - Notificações silenciadas; assistente de voz e gestos de navegação desativados
  - Reiniciar o tablet e retomar a aplicação em ≤ 5 toques documentados
- **Como validar:** entregar o tablet a alguém e confirmar que não consegue sair da aplicação sem o PIN

### ~~MVP-068 — Daemon do botão GPIO~~ → movida para P2
- **Motivo:** o pânico no MVP é **virtual, na interface web** (MVP-046 e MVP-054). O botão
  físico sai do escopo.
- **O que fica preparado:** `POST /panico` é agnóstico de origem e o enum
  `OrigemAcionamento` já tem `botao_fisico`. O daemon entra depois como processo separado
  (`hardware/gpio_panico.py` + uma unit systemd) **sem tocar no backend**.
- **Status:** Fora do MVP

### MVP-069 — `install-pi.sh`
- **Descrição:** Script idempotente que transforma uma Pi limpa num totem.
- **Prioridade:** P0 · **Depende de:** 067, 068 · **Status:** Pendente
- **Arquivos:** `deploy/install-pi.sh`
- **Critérios de aceitação:**
  - Instala dependências de apt, `uv`, Node e `avahi-daemon`
  - Roda `make setup` e `make build`
  - Copia as duas units, `systemctl enable --now`
  - Cria `.env` a partir do exemplo se não existir
  - **Imprime ao final as URLs** (`http://poto.local:8000` e `http://<ip>:8000`) para apontar o tablet
  - **Idempotente**: rodar duas vezes não quebra nada
- **Como validar:** executar 2× numa Pi limpa e, do tablet, abrir a URL impressa

### MVP-070 — Teste de resiliência (Pi + tablet)
- **Descrição:** Provar que o conjunto se recupera sozinho, incluindo a queda de rede que
  esta topologia introduz.
- **Prioridade:** P0 · **Depende de:** 069 · **Status:** Pendente
- **Arquivos:** `docs/aceite-mvp.md`
- **Critérios de aceitação:**
  - `reboot` da Pi → API respondendo em **< 60 s**; o tablet **reconecta sozinho** sem toque
  - `kill -9` no `poto-api` → systemd reergue em < 10 s
  - Corte de energia → `poto.db` íntegro (WAL)
  - 30 min de operação contínua sem degradar nem o tablet apagar a tela
  - **WiFi desligado no tablet** → acionamento continua funcionando pela fila; ao religar,
    drena sem duplicar
  - **Pi desligada com o tablet aberto** → totem não trava nem mostra erro técnico; enfileira
  - Tablet reiniciado → volta à aplicação seguindo `docs/setup-tablet.md`
- **Como validar:** executar o roteiro com cronômetro e registrar os tempos

---

# Fase 10 — Demonstração

### MVP-071 — Seed e `make demo-reset`
- **Descrição:** Voltar ao estado inicial entre ensaios.
- **Prioridade:** P0 · **Depende de:** 066 · **Status:** Pendente
- **Arquivos:** `backend/app/seed.py`, `Makefile`
- **Critérios de aceitação:**
  - `make seed` cria chamados de exemplo cobrindo as 3 gravidades
  - `make demo-reset` limpa o banco, semeia e reinicia os serviços
  - Executa em < 10 s
- **Como validar:** `make demo-reset` e conferir o painel

### MVP-072 — Roteiro de demo e plano B
- **Descrição:** Cinco minutos ensaiados, com contingência.
- **Prioridade:** P0 · **Depende de:** 070, 071 · **Status:** Pendente
- **Arquivos:** `docs/roteiro-demo.md`
- **Critérios de aceitação:**
  - Roteiro: (1) Saúde → SAMU · (2) Mulher → tela neutra · (3) Pânico → broadcast + escalonamento · (4) Offline → fila → dreno · (5) Painel: ACK + SLA
  - Executado **3× seguidas** sem intervenção de teclado
  - Plano B documentado: tudo em `localhost` com `POTO_NOTIF_PROVIDER=log` projetado
  - Checklist de bancada: fonte 27 W, HDMI, botão, extensão, **cartão SD reserva**
- **Como validar:** ensaio cronometrado, 3 execuções registradas

---

## Fora do MVP (P2 — não implementar agora)

Registrados para não serem esquecidos nem confundidos com escopo atual:

| Tema | Itens |
|---|---|
| **Hardware** | **Botão de pânico físico (GPIO 17)** — o endpoint `POST /panico` e o enum `botao_fisico` já existem; falta só o daemon e a unit |
| **Mídia do tablet** | **Câmera e microfone do tablet** — exigem TLS na LAN com CA instalada no aparelho. O campo `dono` em `/dispositivos` já prevê múltiplas origens |
| **Conversação** | Chat de texto, conversa por voz multi-turno, STT (Whisper local), TTS (Piper) |
| **IA** | LLM local ou remoto, LangGraph, Ollama, Hailo-8L |
| **Mídia avançada** | WebRTC P2P, gravação e retenção de evidência, monitoramento oculto persistente |
| **Canais** | SIMCom A7670SA (GSM/2G), Twilio (voz/SMS), Telegram, LoRa, MQTT, sirene |
| **Central** | Auditoria com linha do tempo, métricas com gráficos, frota multi-totem, NOC |
| **Dados** | Política de retenção LGPD, expurgo automático, caixa-preta forense |
| **Produto** | Check-in/check-out, serviços universitários, controle de acesso, monitoramento institucional |
