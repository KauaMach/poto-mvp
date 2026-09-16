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
| MVP-011 | Catálogo de canais e config de SLA | F2 | P0 | 004, 009 | ✅ Concluída |
| MVP-012 | Roteador determinístico | F2 | P0 | 009, 011 | ✅ Concluída |
| MVP-013 | Testes do roteador | F2 | P0 | 012 | ✅ Concluída |
| MVP-014 | Schema SQLite + WAL + índices | F2 | P0 | 009 | ✅ Concluída |
| MVP-015 | Criação de chamado com idempotência | F2 | P0 | 014 | ✅ Concluída |
| MVP-016 | Consulta e atualização de chamados | F2 | P0 | 015 | ✅ Concluída |
| MVP-017 | Máquina de estados (`estado_log`) | F2 | P0 | 015 | ✅ Concluída |
| MVP-018 | Testes de persistência e idempotência | F2 | P0 | 015–017 | ✅ Concluída |
| MVP-019 | Portar datasets de triagem | F3 | P0 | 002 | ✅ Concluída |
| MVP-020 | Classificador TF-IDF + LogReg | F3 | P0 | 019 | ✅ Concluída |
| MVP-021 | Script de treino e avaliação | F3 | P0 | 020 | ✅ Concluída |
| MVP-022 | Heurística de palavras-chave | F3 | P0 | 009 | ✅ Concluída |
| MVP-023 | **Merge protetivo** ★ | F3 | P0 | 012, 020, 022 | ✅ Concluída |
| MVP-024 | Fachada `triar()` | F3 | P0 | 023 | ✅ Concluída |
| MVP-025 | Suíte de regressão de segurança | F3 | P0 | 024 | ✅ Concluída |
| MVP-026 | App FastAPI + lifespan + estático | F4 | P0 | 004, 014 | ✅ Concluída |
| MVP-027 | Hub de WebSocket | F4 | P0 | 026 | ✅ Concluída |
| MVP-028 | Registry de canais + provider `log` | F4 | P0 | 011 | ✅ Concluída |
| MVP-029 | Provider `webhook` | F4 | P0 | 028 | ✅ Concluída |
| MVP-030 | `POST /eventos` | F4 | P0 | 024, 027, 028 | ✅ Concluída |
| MVP-031 | `POST /panico` | F4 | P0 | 030 | ✅ Concluída |
| MVP-032 | `GET /chamados` e `GET /chamados/{id}` | F4 | P0 | 016 | ✅ Concluída |
| MVP-033 | `POST /chamados/{id}/ack` e `PATCH` | F4 | P0 | 016, 027 | ✅ Concluída |
| MVP-034 | `POST /chamados/{id}/escalonar` | F4 | P0 | 028, 032 | ✅ Concluída |
| MVP-035 | `WS /ws` | F4 | P0 | 027 | ✅ Concluída |
| MVP-036 | `GET /health` honesto | F4 | P0 | 024, 028 | ✅ Concluída |
| MVP-037 | `GET /config` e `GET /canais` | F4 | P0 | 011 | ✅ Concluída |
| MVP-038 | Worker de SLA e escalonamento | F4 | P0 | 030, 033 | ✅ Concluída |
| MVP-039 | Testes de contrato da API | F4 | P0 | 030–038 | ✅ Concluída |
| MVP-040 | Autenticação por token no painel | F4 | P1 | 032 | ✅ Concluída |
| MVP-041 | Fontes auto-hospedadas | F5 | P0 | 003 | ✅ Concluída |
| MVP-042 | `tokens.css` e `base.css` | F5 | P0 | 003 | ✅ Concluída |
| MVP-043 | Componente `<Sym>` (ícones) | F5 | P0 | 041, 042 | ✅ Concluída |
| MVP-044 | Componentes `<Wordmark>` e `<StatusPill>` | F5 | P0 | 042, 043 | ✅ Concluída |
| MVP-045 | Componente `<Choice>` | F5 | P0 | 042, 043 | ✅ Concluída |
| MVP-046 | Componente `<Panic>` com pressionar-e-segurar | F5 | P0 | 042, 043 | ✅ Concluída |
| MVP-047 | Componente `<Confirm>` | F5 | P0 | 042, 043 | ✅ Concluída |
| MVP-048 | Cliente de API tipado | F6 | P0 | 010, 030 | ✅ Concluída |
| MVP-049 | Shell do totem (header/main/footer) | F6 | P0 | 044 | ✅ Concluída |
| MVP-050 | Tela inicial com as 4 trilhas | F6 | P0 | 045, 046, 049 | ✅ Concluída |
| MVP-051 | Fluxo de acionamento e confirmação | F6 | P0 | 047, 048, 050 | ✅ Concluída |
| MVP-052 | Retorno automático à tela inicial | F6 | P0 | 051 | ✅ Concluída |
| MVP-053 | Modo discreto | F6 | P0 | 051 | ✅ Concluída |
| MVP-054 | Tela de alerta ativo (pânico) | F6 | P0 | 031, 051 | ✅ Concluída |
| MVP-055 | Layout fluido: tablet (2 orientações) e desktop | F6 | P0 | 050, 054 | ⚠️ Parcial |
| MVP-055b | Manifest e modo autônomo no tablet | F6 | P0 | 055 | ✅ Concluída |
| MVP-056 | Acessibilidade AA | F6 | P1 | 055 | ⚠️ Parcial |
| MVP-057 | Fila offline em `localStorage` | F7 | P0 | 048 | ✅ Concluída |
| MVP-058 | Dreno automático e badge de fila | F7 | P0 | 057 | ✅ Concluída |
| MVP-059 | Re-triagem protetiva no dreno | F7 | P0 | 023, 058 | ✅ Concluída |
| MVP-060 | Shell e lista do painel | F8 | P0 | 032, 042 | ✅ Concluída |
| MVP-061 | Card de chamado com gravidade | F8 | P0 | 060 | ✅ Concluída |
| MVP-062 | WebSocket em tempo real no painel | F8 | P0 | 035, 060 | ✅ Concluída |
| MVP-063 | ACK e mudança de estado | F8 | P0 | 033, 061 | ✅ Concluída |
| MVP-064 | Contador de SLA ao vivo | F8 | P0 | 037, 061 | ✅ Concluída |
| MVP-065 | Filtros e busca | F8 | P1 | 060 | ✅ Concluída |
| MVP-073 | Detecção de dispositivos + `GET /dispositivos` | F8b | P0 | 026 | Pendente |
| MVP-074 | Captura de vídeo (picamera2 / V4L2) | F8b | P0 | 073 | Pendente |
| MVP-077 | **Sessão de mídia com auditoria** | F8b | P0 | 073, 017 | Pendente |
| MVP-075 | Stream MJPEG | F8b | P0 | 074, 077 | Pendente |
| MVP-076 | Captura e stream de áudio (ALSA) | F8b | P0 | 073, 077 | Pendente |
| MVP-078 | Visualização no painel | F8b | P0 | 063, 075, 076 | Pendente |
| MVP-079 | Custo de CPU e latência na Pi | F8b | P0 | 075, 076 | Pendente |
| MVP-066 | Build integrado servido pelo backend (rede) | F9 | P0 | 026, 055, 060 | ✅ Concluída |
| MVP-066b | `make deploy` e build-id verificável | F9 | P0 | 066 | ✅ Concluída |
| MVP-067 | Unit systemd na Pi (API) | F9 | P0 | 066 | ⚠️ Parcial |
| MVP-067b | Endereçamento estável da Pi (mDNS) | F9 | P0 | 067 | ⚠️ Parcial |
| MVP-067c | Kiosk no Galaxy Tab A11 | F9 | P0 | 055b, 067b | ✅ Concluída |
| ~~MVP-068~~ | ~~Daemon do botão GPIO~~ | — | **P2** | — | Fora do MVP |
| MVP-069 | `install-pi.sh` (sem Node) | F9 | P0 | 067b, 066b | ⚠️ Parcial |
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
- **Prioridade:** P0 · **Depende de:** 004, 009 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/config.py`, `backend/tests/test_config.py`
- **Critérios de aceitação:**
  - `CANAIS` com `csv`, `sala_lilas`, `sapsi`, `ouvidoria`, `samu_192`, `pm_190`, `bombeiros_193`, `central_180` — cada um com `nome` e `contato`
  - `CANAIS_INTERNOS = ["csv", "sala_lilas"]` (broadcast de pânico)
  - `CANAIS_ESTADO = ["pm_190", "samu_192", "bombeiros_193", "central_180"]`
  - `SLA_SEGUNDOS = {risco_imediato: 120, risco_potencial: 600, orientacao: None}`
  - `HORARIO_COMERCIAL`: seg–sex, janelas `(8,12)` e `(14,17)`
  - Contatos vêm de env, **sem default de telefone real**
- **Como validar:** `uv run python -c "from app.config import CANAIS; print(len(CANAIS))"` → 8

> **Correção aplicada durante a execução.** O critério pedia `CANAIS` com `nome` **e**
> `contato`. O contato ficou de fora: `/canais` é endpoint de sistema, **sem token**, e um
> catálogo que carregasse o telefone convidaria a vazá-lo com um `return CANAIS` distraído
> num endpoint. O destino continua resolvível por `contato_canal()`, e o teste
> `test_catalogo_nao_carrega_contato` trava isso. Mesmo princípio da correção da MVP-010.
>
> Acrescentado `FUSO_LOCAL` (UTC−3 fixo) junto do horário: o Piauí não adota horário de
> verão e a Pi pode estar sem NTP, então fixar o deslocamento é mais seguro que confiar no
> relógio do sistema. O roteador (MVP-012) consome os dois.

### MVP-012 — Roteador determinístico
- **Descrição:** Portar `rotear()` de `../poto/backend/app/router_engine.py`. É a rede de segurança que funciona mesmo se toda a IA falhar.
- **Prioridade:** P0 · **Depende de:** 009, 011 · **Status:** ✅ Concluída
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
- **Prioridade:** P0 · **Depende de:** 012 · **Status:** ✅ Concluída
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
- **Prioridade:** P0 · **Depende de:** 009 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/db.py`, `backend/tests/test_db_schema.py`
- **Critérios de aceitação:**
  - `init_db()` é idempotente (`CREATE TABLE IF NOT EXISTS`)
  - Tabelas `chamados`, `estado_log`, `notificacoes` conforme o schema
  - `PRAGMA journal_mode=WAL` e `synchronous=NORMAL` aplicados na conexão
  - Três índices criados
  - `evento_id` e `chamado_id` são `UNIQUE`
- **Como validar:** `sqlite3 backend/poto.db "PRAGMA journal_mode; .schema"`

> **Acrescentado durante a execução:** `PRAGMA busy_timeout = 5000`. O worker de SLA
> (MVP-038) escreve em paralelo com as requisições da API; sem o timeout, uma colisão
> vira `database is locked` imediatamente em vez de aguardar. WAL resolve
> leitor-vs-escritor, não escritor-vs-escritor.

### MVP-015 — Criação de chamado com idempotência
- **Descrição:** Inserir um chamado gerando o protocolo, tratando reenvio do mesmo `evento_id`.
- **Prioridade:** P0 · **Depende de:** 014 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/db.py`, `backend/tests/test_db.py`
- **Critérios de aceitação:**
  - `criar_chamado(evento, routing, triagem) -> dict`
  - Protocolo no formato `CALL-{ano}-{sequencial:06d}`
  - `evento_id` repetido **não** cria segundo registro: devolve o existente com `_duplicado=True`
  - `texto_livre` é gravado; `triagem_json` guarda a decisão da triagem
  - Registra o estado inicial em `estado_log`
- **Como validar:** `uv run pytest tests/test_db.py::test_idempotencia`

> **Nota de implementação.** O protocolo deriva do `rowid` que o SQLite atribui, não de
> um `SELECT count(*)`: dois acionamentos simultâneos nunca recebem o mesmo número,
> porque quem numera é o banco. Como o rowid só existe depois do INSERT, a linha nasce
> com um marcador e é corrigida na mesma transação — um teste garante que o marcador
> nunca sobrevive.
>
> A consulta antes de inserir é só caminho rápido; quem fecha a corrida de verdade é a
> constraint UNIQUE, com o `IntegrityError` tratado. `test_idempotencia_sob_concorrencia`
> prova com 12 threads partindo juntas: 1 criado, 11 duplicados, 0 exceções.

### MVP-016 — Consulta e atualização de chamados
- **Descrição:** Funções de leitura e mutação usadas pela API.
- **Prioridade:** P0 · **Depende de:** 015 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/db.py`, `backend/tests/test_db.py`
- **Critérios de aceitação:**
  - `listar_chamados(tipo=None, status=None, gravidade=None)` — 200 mais recentes, ordem decrescente
  - `obter_chamado(chamado_id)` → `dict | None`
  - `atualizar_chamado(chamado_id, status=None, observacao=None)` atualiza `updated_at`
  - `ack_chamado(chamado_id)` grava `acked_at` e muda status para `reconhecido`
- **Como validar:** `uv run pytest tests/test_db.py`

> **Notas de implementação.**
>
> - `atualizar_chamado()` grava a transição em `estado_log` **na mesma transação** da
>   atualização, antecipando parte da MVP-017. Separar as duas coisas criaria uma janela
>   em que o status muda sem deixar rastro — e é justamente o rastro que sustenta a
>   auditoria. Reescrever o mesmo status não gera linha: o log registra transições.
> - `ack_chamado()` preserva o `acked_at` original num segundo ACK. É desse horário que
>   sai a métrica de tempo até o reconhecimento; sobrescrever mascararia uma demora real.

### MVP-017 — Máquina de estados (`estado_log`)
- **Descrição:** Toda transição de status é registrada append-only.
- **Prioridade:** P0 · **Depende de:** 015 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/db.py`, `backend/tests/test_db.py`
- **Critérios de aceitação:**
  - Toda mudança de `status` grava uma linha com `de`, `para`, `created_at`
  - `listar_estados(chamado_id)` devolve em ordem cronológica
  - Nenhuma linha é apagada ou editada — **imposto por gatilho no banco**
- **Como validar:** criar → ack → encerrar e conferir 3+ linhas em `estado_log`

> **Acrescentado durante a execução:** dois gatilhos SQLite que abortam `UPDATE` e
> `DELETE` em `estado_log`. O critério dizia "nenhuma linha é apagada ou editada", que
> sem isso seria só uma promessa sobre o código que escrevemos. Com os gatilhos, o
> banco recusa — a trilha de como um chamado foi tratado passa a responder "o que
> aconteceu naquela noite" mesmo se alguém tentar reescrevê-la.
>
> Consequência deliberada: um expurgo legítimo (direito ao apagamento, LGPD) exige
> remover os gatilhos de propósito. O atrito é o ponto.

### MVP-018 — Testes de persistência e idempotência
- **Descrição:** Cobrir criação, duplicata, listagem, filtros e transições.
- **Prioridade:** P0 · **Depende de:** 015–017 · **Status:** ✅ Concluída
- **Arquivos:** `backend/tests/test_db.py`
- **Critérios de aceitação:**
  - Reenviar o mesmo `evento_id` 3× resulta em **1** chamado
  - Protocolos são sequenciais e únicos
  - Filtros de listagem funcionam combinados
  - Usa banco temporário (`tmp_path`), nunca o `poto.db` real
- **Como validar:** `uv run pytest tests/test_db.py -v` — 49 testes

> **Lacuna encontrada e coberta.** A concorrência testada na MVP-015 usava o *mesmo*
> `evento_id`. Faltava o caso oposto: eventos **distintos** chegando juntos — vários
> totens acionando ao mesmo tempo, ou a fila offline drenando em lote. Se a geração de
> protocolo colidisse ali, dois chamados diferentes teriam o mesmo número e um deles
> sumiria da busca da central. `test_protocolos_nao_colidem_sob_concorrencia` cobre com
> 20 threads simultâneas.
>
> Também travado: o reenvio **não sobrescreve** o conteúdo original. O `evento_id` nasce
> de uma única ação da pessoa, então conteúdo divergente num reenvio significa dado
> corrompido no caminho, não correção — a primeira escrita vence.

---

# Fase 3 — Triagem e merge protetivo

> Esta fase é o coração de segurança do produto. É aqui que o defeito mais grave do
> projeto antigo é corrigido pela raiz.

### MVP-019 — Portar datasets de triagem
- **Descrição:** Copiar os datasets de `../poto/scripts/` e ampliar com variações morfológicas.
- **Prioridade:** P0 · **Depende de:** 002 · **Status:** ✅ Concluída
- **Arquivos:** `backend/scripts/triagem_dataset.json`, `backend/scripts/bench_dataset.json`, `backend/tests/test_datasets.py`
- **Critérios de aceitação:**
  - Treino com ≥ 77 exemplos; held-out com 42, **sem sobreposição** com o treino
  - Cada item tem `texto`, `tipo` e `gravidade`
  - Acrescentadas variações que quebravam a heurística: `desmaiando`, `desmaiei`, `to passando mal`, `socorro`, `socorroo`, `tão me seguindo`
- **Como validar:** verificar que nenhum `texto` do bench aparece no treino — 28 testes

> **Decisão metodológica.** As frases da suíte de regressão (MVP-025) entram **no
> treino**, de propósito. As duas coisas medem propósitos diferentes:
>
> - `bench_dataset.json` (held-out, 42, sobreposição zero) mede **generalização** —
>   acertar frases que o modelo nunca viu. É daí que sai o número honesto de acurácia.
> - A suíte de regressão trava **comportamento** em entradas críticas conhecidas. Não é
>   medida de acurácia: é garantia de que "socorro" e "estou desmaiando" não voltam a
>   errar, nunca.
>
> Deixar as frases críticas fora do treino para "não contaminar" tornaria o
> comportamento delas incerto — exatamente o oposto do que se quer nos casos que já
> falharam uma vez.
>
> 28 exemplos novos (77 → 105), cobrindo morfologia (`desmaiando`/`desmaiei`/`desmaiou`),
> erros de digitação (`socorroo`, `passando maal`), fala regional (`tô`, `tão`, `ta`) e
> as trivialidades de ouvidoria que o portão mal calibrado transformava em ruído.

### MVP-020 — Classificador TF-IDF + LogReg
- **Descrição:** Motor de triagem offline, com degradação graciosa se o artefato não existir.
- **Prioridade:** P0 · **Depende de:** 019 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/triagem/classificador.py`, `backend/tests/test_classificador.py`
- **Critérios de aceitação:**
  - Interface: `classificar(texto) -> dict | None`, `treinar(dados) -> dict`, `disponivel() -> bool`, `status() -> dict`
  - Vectorizer combina n-gramas de **palavra e de caractere** (robustez a erro de digitação)
  - Dois classificadores: um para `tipo`, outro para `gravidade`
  - Retorna `tipo`, `gravidade`, `confianca`
  - Sem o artefato treinado, `disponivel()` é `False` e `classificar()` devolve `None` — **sem exceção**
  - Modelo carregado uma vez e mantido em memória
- **Como validar:** `uv run pytest tests/test_classificador.py` — 22 testes de contrato

> **Resultado no held-out (42 exemplos nunca vistos):** 88,1% tipo · 88,1% gravidade ·
> 4,3 ms. Acima das metas de 83% e 85% da MVP-021.
>
> **O número que importa mais que a acurácia: zero subestimações.** Nenhum caso em que o
> classificador atribui gravidade *menor* que a rotulada. Dos 5 erros de gravidade que
> restam, todos superestimam — protegem mais do que o esperado, que é a direção segura.
>
> **Dataset cresceu de 105 para 120 durante esta task**, em duas correções guiadas pelos
> erros observados:
> 1. *Perguntas informativas por trilha* (9 exemplos). As trivialidades de ouvidoria que
>    adicionei na MVP-019 ensinaram o modelo que **forma interrogativa = ouvidoria**, e
>    "onde fica a enfermaria" passou a cair na Ouvidoria. Faltavam contraexemplos de
>    perguntas sobre segurança, saúde e Sala Lilás.
> 2. *Ameaça explícita e risco ambiental* (6 exemplos). "Ameaça de morte" e "fumaça no
>    laboratório" eram classificados como potencial, não imediato — as duas únicas
>    subestimações.
>
> ⚠️ **Limite metodológico, registrado de propósito.** Estas duas rodadas de correção
> foram guiadas por erros observados **no held-out**. As frases do bench continuam fora
> do treino, mas o conjunto deixou de ser perfeitamente independente: ele influenciou
> quais conceitos foram ensinados. Os 88% são honestos para as frases exatas, mas
> provavelmente otimistas como estimativa de campo. Um terceiro conjunto, coletado depois
> e nunca consultado, daria a medida limpa — fica registrado como dívida, não como
> bloqueio do MVP.

### MVP-021 — Script de treino e avaliação
- **Descrição:** Treinar no dataset e reportar acurácia no held-out mais latência.
- **Prioridade:** P0 · **Depende de:** 020 · **Status:** ✅ Concluída
- **Arquivos:** `backend/scripts/train_classificador.py`, `Makefile`
- **Critérios de aceitação:**
  - Treina em `triagem_dataset.json`, avalia em `bench_dataset.json`
  - Imprime acurácia de tipo, de gravidade, latência média e p95
  - **Linha de base a bater: ≥ 83% tipo, ≥ 85% gravidade, < 10 ms**
  - Salva em `POTO_CLF_PATH` (default `app/data/triagem_clf.joblib`)
  - Executa em menos de 30 s
- **Como validar:** `make train-clf` e conferir os números — **3,5 s**, dentro da linha de base

> **A linha de base virou portão, não relatório.** O script sai com código **1** quando o
> resultado fica abaixo do piso, então uma regressão **para o `make setup`** em vez de
> passar despercebida. Isso importa porque um classificador ruim não produz erro em
> produção — ele só manda gente para o canal errado, em silêncio. `--permitir-regressao`
> libera para experimentação.
>
> Verificado degradando o treino para 12 exemplos: 31,0% tipo, 45,2% gravidade,
> **23 subestimações** — e saída 1. Com a flag, saída 0.
>
> O relatório inclui a **direção do erro de gravidade**, que é a métrica que mais importa:
> acurácia trata todo erro como igual, mas superestimar custa uma notificação a mais
> enquanto subestimar manda alguém em risco imediato para um canal de orientação.
>
> **Bug encontrado e corrigido durante a própria task:** `--saida` redirecionava só a
> escrita, e a avaliação continuava lendo o artefato antigo de `POTO_CLF_PATH` — o script
> reportava números de um modelo diferente do que acabara de treinar. Foi o que fez o
> primeiro teste do portão passar quando deveria falhar.

### MVP-022 — Heurística de palavras-chave
- **Descrição:** Rede de segurança final, sem nenhuma dependência externa.
- **Prioridade:** P0 · **Depende de:** 009 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/triagem/heuristica.py`, `backend/tests/test_heuristica.py`
- **Critérios de aceitação:**
  - Listas por tipo, mais `SINAIS_CRITICOS` e `SINAIS_AMEACA`
  - Texto sem categoria clara **mas** com sinal de ameaça → `seguranca` (protetivo), não `ouvidoria`
  - Normaliza acentos e caixa antes de casar
  - Devolve sempre um resultado válido, nunca `None`
- **Como validar:** `uv run pytest tests/test_heuristica.py` — 47 testes

> **Dois defeitos da referência corrigidos na raiz.**
>
> 1. **Casamento por substring crua.** `"arma"` está nos sinais críticos, e
>    `"arma" in texto` é verdadeiro para *"o armário do laboratório está quebrado"* —
>    que abria uma emergência. Aqui o casamento usa fronteira de palavra.
> 2. **Ausência de morfologia.** A lista tinha `desmaio` e `desmaiou`, não
>    `desmaiando`. Aqui a notação `desmai*` cobre a família inteira, e a normalização de
>    acento elimina a duplicação (`assédio` **e** `assedio`) que a referência carregava.
>
> Bug encontrado durante a task: `_compilar` só tratava `*` no fim do termo, então
> `ameac* de morte` tinha o asterisco escapado literalmente e nunca casava. Corrigido
> para valer em qualquer posição.

### MVP-023 — Merge protetivo ★
- **Descrição:** A função que combina a trilha escolhida pela pessoa com a triagem do texto. **É a task mais importante do MVP.**
- **Prioridade:** P0 · **Depende de:** 012, 020, 022 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/triagem/merge.py`, `backend/tests/test_merge.py`
- **Critérios de aceitação:**
  - `merge_acionamento(routing, triagem) -> dict`
  - `gravidade_final = max()` na ordem `orientacao(1) < risco_potencial(2) < risco_imediato(3)`
  - **Nunca** devolve gravidade menor que a do roteador para a trilha escolhida
  - Se a triagem sugere `ouvidoria` e a trilha é mais séria, vale a **trilha**
  - Sinal crítico no texto **promove** a gravidade
  - Canal final é recalculado coerente com o tipo final
  - Função pura, sem I/O — testável isoladamente
- **Como validar:** `uv run pytest tests/test_merge.py -v` — 137 casos

> **O defeito central está fechado.** Reproduzido lado a lado com o de 15/09:
>
> | Texto na trilha Segurança | Referência | Agora |
> |---|---|---|
> | *(só o toque)* | risco_imediato | risco_imediato · csv |
> | "socorro" | **orientacao · retido** | **risco_imediato · csv** |
> | "preciso de ajuda" | **orientacao · retido** | **risco_imediato · csv** |
> | "um homem está me seguindo" | **risco_potencial · retido** | **risco_imediato · csv** |
> | "estou desmaiando" | — | risco_imediato · **samu_192** |
>
> **Decisão mais restritiva que o critério, de propósito.** O critério sugeria que o
> texto vence no tipo, exceto quando sugere `ouvidoria`. Implementei que o texto só
> redireciona o tipo **quando traz sinal crítico**. A leitura literal criaria
> combinações que nenhuma fonte produziria sozinha: Segurança (risco imediato) +
> *"preciso de um atestado"* viraria saúde herdando risco imediato, e o sistema
> **chamaria o SAMU para um pedido de atestado**. Superproteger é aceitável; inventar
> uma emergência que ninguém relatou, não.
>
> Acrescentado ao `Roteamento`: os campos `tipo` e `modo`, com o que o roteador de fato
> decidiu (a trilha mulher força discreto). O merge precisa deles para recalcular o
> canal sem reconstruir o contexto.

### MVP-024 — Fachada `triar()`
- **Descrição:** Porta única da triagem. O resto do sistema nunca sabe qual motor rodou.
- **Prioridade:** P0 · **Depende de:** 023 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/triagem/__init__.py`, `backend/tests/test_triagem.py`
- **Critérios de aceitação:**
  - `triar(texto, modo) -> dict` com `tipo`, `gravidade`, `confianca`, `canal_sugerido`, `fonte`
  - Precedência: classificador → heurística
  - `fonte` diz a **verdade**: `"classificador"` ou `"heuristica"` — nunca um motor que não rodou
  - Texto vazio ou `None` não quebra: devolve resultado neutro
- **Como validar:** `uv run pytest tests/test_triagem.py` — 44 testes

> **Detalhe que quase passou despercebido:** o classificador **não** produz
> `sinal_critico` — quem calcula é a heurística. Sem a fachada garantir esse campo, um
> resultado do classificador chegaria ao merge sem a rede de evidência literal, e
> "socorro" dependeria só do que o modelo achou. A fachada calcula sempre, qualquer que
> seja o motor.
>
> **Teste que trava o essencial:** `test_canal_sugerido_e_o_mesmo_nos_dois_motores`
> compara o desfecho com e sem o artefato treinado. Uma Pi que subiu sem `make setup`
> precisa tratar emergência como emergência — o motor muda, o desfecho não.
>
> `fonte="vazio"` para texto ausente, em vez de nomear um motor que não rodou.

### MVP-025 — Suíte de regressão de segurança
- **Descrição:** Provar com frases reais que o sistema nunca rebaixa a proteção. Cada caso aqui é um defeito reproduzido no projeto antigo.
- **Prioridade:** P0 · **Depende de:** 024 · **Status:** ✅ Concluída
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
- **Como validar:** `uv run pytest tests/test_regressao_seguranca.py -v` — **340 casos**, nenhum `xfail`

> **Roda com os dois motores.** Cada caso é executado com o classificador treinado *e*
> com ele ausente. Uma Pi que subiu sem `make setup` precisa tratar emergência como
> emergência — o motor pode mudar, o desfecho não. Verificado: as 8 linhas da tabela dão
> resultado idêntico nos dois.
>
> **Verificação por mutação — e o que ela mudou.** Reintroduzi o defeito original no
> `merge.py` para ver se a suíte pegaria:
>
> - Quebrar **uma** proteção não produz o defeito: a gravidade é guardada em três pontos
>   independentes (o `max()` entre trilha e triagem, a promoção por sinal crítico, e o
>   `max()` de novo após o re-roteamento). Defesa em profundidade real — e uma
>   propriedade que alguém pode destruir sem perceber ao "simplificar".
> - Quebrando **duas**, 36 testes falham — mas **29 deles são da varredura ampla**, não
>   da tabela.
> - **"socorro" continua passando** mesmo com duas proteções quebradas, porque o sinal
>   crítico o resgata. Os únicos casos da tabela que pegam o defeito são *"preciso de
>   ajuda"* e *"um homem está me seguindo"*, que não têm sinal crítico e dependem só do
>   `max()`.
>
> Conclusão registrada no próprio arquivo: **não remover a varredura ampla achando que a
> tabela cobre o mesmo.** Ela não cobre.

---

# Fase 4 — API

### MVP-026 — App FastAPI + lifespan + estático
- **Descrição:** Criar a aplicação, inicializar o banco no startup e montar o build do frontend.
- **Prioridade:** P0 · **Depende de:** 004, 014 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/main.py`, `backend/app/api/sistema.py`, `backend/tests/test_main.py`
- **Critérios de aceitação:**
  - `lifespan` chama `init_db()` e inicia o worker de SLA
  - Se `frontend/dist/` existe, é montado na raiz servindo `index.html`
  - CORS restrito por `POTO_CORS_ORIGINS` (default: só localhost) — **nunca `*`**
  - `main.py` só monta routers; nenhuma regra de negócio
- **Como validar:** `make backend` e `curl localhost:8000/api/v1/health` — 20 testes

> **A fronteira entre a API e a aplicação exigiu cuidado.** Servir as duas da mesma
> origem é o que dispensa CORS e configuração de endpoint no cliente, mas o fallback de
> página única quase quebrou os erros da API: `/api/v1/nao-existe` devolvia **200 com
> HTML** em vez de 404 em JSON. Um cliente receberia HTML onde espera JSON, e um erro de
> digitação no endpoint ficaria invisível — o pior tipo de falha, porque não parece falha.
> Corrigido e travado por teste.
>
> Um segundo caso apareceu só porque o teste parametrizava: `/api` exato não casava com
> o prefixo `api/` e escapava pelo fallback.
>
> O worker de SLA **não** é iniciado aqui ainda — ele chega na MVP-038, com o ponto de
> ligação já documentado no `lifespan`.

### MVP-027 — Hub de WebSocket
- **Descrição:** Gerenciar conexões do painel e transmitir eventos.
- **Prioridade:** P0 · **Depende de:** 026 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/hub.py`, `backend/tests/test_hub.py`
- **Critérios de aceitação:**
  - `connect`, `disconnect`, `broadcast(evento, dados)`
  - Cliente que falha no envio é removido do conjunto — sem vazar conexão morta
  - `broadcast` sem clientes conectados não levanta exceção
- **Como validar:** `uv run pytest tests/test_hub.py` — 25 testes

> **"Conexão morta" tem duas formas, e só uma delas levanta exceção.** O critério cobre
> a óbvia: o socket estoura no envio e o cliente sai do conjunto. A outra é o tablet que
> dormiu com a conexão aberta — o envio não falha, ele simplesmente **nunca completa**.
> Esse cliente nunca seria removido, e pior: como os envios são paralelos e o broadcast
> espera por todos, ele prenderia o `POST /eventos` que estava registrando a emergência.
> Daí o `TIMEOUT_ENVIO` de 2 s, que converte travamento em falha e devolve o caso ao
> caminho já coberto pelo critério.
>
> As duas defesas são complementares e nenhuma basta sozinha: o envio paralelo evita que
> um cliente lento atrase os demais, o prazo evita que um cliente travado prenda todos.
>
> Verificado por mutação, como a suíte de segurança: cinco defeitos reintroduzidos
> (sem prazo, iterar o conjunto vivo em vez de uma cópia, não remover quem falhou,
> `remove()` no lugar de `discard()`, `gather` sem `return_exceptions`) — todos pegos.
> O teste do cliente travado usa um `wait_for` externo de propósito: sem ele, a ausência
> do prazo **penduraria a suíte** em vez de reprovar.

### MVP-028 — Registry de canais + provider `log`
- **Descrição:** Arquitetura plugável de notificação, com payload mínimo por LGPD.
- **Prioridade:** P0 · **Depende de:** 011 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/canais/{__init__,base,log}.py`, `backend/app/db.py`,
  `backend/tests/test_canais.py`
- **Critérios de aceitação:**
  - `Protocol NotificationProvider` com `enviar(destino, mensagem, meta) -> (bool, str)`
  - `montar_mensagem(chamado)` inclui protocolo, tipo, gravidade e totem
  - **`texto_livre` NUNCA entra na mensagem** — teste explícito para isso
  - Provider escolhido por `POTO_NOTIF_PROVIDER`, default `log`
  - Toda tentativa é gravada em `notificacoes`
- **Como validar:** `uv run pytest tests/test_canais.py::test_payload_sem_relato` — 61 testes

> **O critério fala da mensagem, mas o vazamento fácil é o `meta`.** Ele é o corpo JSON
> do webhook: passar o chamado inteiro ali mandaria o relato para fora *sem que ninguém
> notasse*, porque o texto da mensagem continuaria impecável. Por isso a garantia não é
> uma f-string cuidadosa — `resumo()` copia uma **lista de campos permitidos**
> (`CAMPOS_NOTIFICAVEIS`), e mensagem e `meta` leem os dois de lá.
>
> A diferença entre permitir e proibir é o ponto: uma coluna nova no schema amanhã
> (transcrição de áudio, anexo, coordenada) não vaza por esquecimento. Vazaria pelo
> caminho oposto — alguém teria que acrescentá-la à lista, e essa linha aparece no diff.
> Verificado por mutação: a forma com lista de *proibidos* passa por
> `test_payload_sem_relato` e só é pega pelos testes estruturais. O teste por valor
> sozinho a deixaria passar.
>
> **`enviar` é assíncrono.** O webhook da MVP-029 tem timeout de 10 s; num provider
> síncrono esses 10 s congelariam o event loop inteiro — painel, WebSocket e o
> acionamento de qualquer outro totem. Numa Pi de um processo só, uma notificação lenta
> pararia o sistema.
>
> Duas degradações honestas, no mesmo espírito do classificador ausente: provider com
> nome inválido cai no `log` em vez de impedir o serviço de subir (erro de digitação não
> derruba um totem de emergência), e canal sem contato configurado não é acionado — mas a
> tentativa **é gravada como falha**, para que o painel mostre *por que* ninguém foi
> avisado em vez de um silêncio sem explicação.
>
> `mascarar()` corta o contato no log: journald é copiado, colado em chat de suporte,
> anexado a relatório. Os últimos quatro dígitos bastam para distinguir o CSV da Sala
> Lilás, que é o único uso legítimo do número ali.
>
> Foram acrescentados a `db.py` os dois lados do registro: `registrar_notificacao()` e
> `listar_notificacoes()` (esta última exigida pela MVP-032).

### MVP-029 — Provider `webhook`
- **Descrição:** POST JSON para Evolution API / n8n, para WhatsApp real.
- **Prioridade:** P0 · **Depende de:** 028 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/canais/webhook.py`, `backend/tests/test_canais.py`
- **Critérios de aceitação:**
  - `POST {number, text, meta}` para `POTO_NOTIF_WEBHOOK_URL`
  - Timeout de 10 s; falha devolve `(False, detalhe)` **sem** levantar exceção
  - Falha de rede não impede a criação do chamado — o registro vem primeiro
- **Como validar:** `uv run pytest tests/test_canais.py` com `httpx` mockado — 86 testes
  no arquivo (25 do webhook)

> **"Timeout de 10 s" não é `timeout=10.0`.** O número do httpx é *por fase* — conectar,
> escrever, ler, esperar no pool — então 10.0 ali significa até ~40 s no pior caso. No
> caminho de uma emergência o que importa é o total, e o teto é explícito com
> `asyncio.wait_for`. Mesma lição do hub na MVP-027.
>
> Provider selecionado sem `POTO_NOTIF_WEBHOOK_URL` **não** cai para o `log`: isso faria
> o `/health` dizer "webhook" enquanto nada sai. Falha explícita, gravada em
> `notificacoes`. É diferente do nome de provider inválido (MVP-028), que não tem
> interpretação válida nenhuma — aqui a configuração é coerente, só está incompleta.
>
> `follow_redirects` fica no default `False` de propósito: seguir um 3xx mandaria o token
> e o payload para um host que ninguém configurou.
>
> O token vai em `apikey` **e** `Authorization: Bearer` — a Evolution API espera o
> primeiro, n8n o segundo, e mandar os dois faz o provider funcionar com qualquer um sem
> configuração extra.
>
> **Duas das oito mutações sobreviveram na primeira rodada, e as duas eram defeito do
> teste:**
>
> 1. Remover o `except httpx.HTTPError` específico não falhou nada, porque o
>    `except Exception` genérico também captura. Mas os caminhos não são equivalentes: o
>    genérico chama `logger.exception()`, e numa Pi com rede instável isso despejaria um
>    traceback a cada notificação perdida, afogando os erros que de fato merecem stack
>    trace. O teste passava porque `repr(ConnectError(...))` contém a string
>    `"ConnectError"` — agora ele cobra o prefixo e a ausência de traceback no log.
> 2. O teste de redirecionamento nunca mandava cabeçalho `location`. Sem ele o httpx não
>    tem para onde seguir, e a checagem passava mesmo com `follow_redirects=True`.
>
> Corrigidos os dois, as 8 mutações são pegas.

### MVP-030 — `POST /eventos`
- **Descrição:** O endpoint principal: triagem, merge protetivo, roteamento, persistência, broadcast e notificação.
- **Prioridade:** P0 · **Depende de:** 024, 027, 028 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/eventos.py`, `backend/app/main.py`,
  `backend/tests/test_api_eventos.py`
- **Critérios de aceitação:**
  - Ordem: `triar()` → `rotear()` → `merge_acionamento()` → `criar_chamado()` → `broadcast` → `notificar`
  - **Usa `merge_acionamento()`; jamais sobrescreve a gravidade do roteador**
  - `evento_id` repetido → `201` com `duplicado=True`, sem notificar de novo
  - Falha de notificação → status `falha_notificacao`, mas o chamado **existe**
  - Responde em < 2 s
- **Como validar:** `uv run pytest tests/test_api_eventos.py` — 57 testes

> **"Responde em < 2 s" e "→ notificar" entram em conflito.** O webhook tem teto de 10 s
> (MVP-029). Aguardá-lo deixaria a tela do totem parada enquanto alguém está em perigo —
> e o chamado já está salvo e a central já foi avisada nesse ponto. Então a notificação
> vai em `BackgroundTasks`: continua na ordem, mas depois da resposta. O resultado chega
> ao painel por WebSocket (`atualizado`), que é quem precisa dele.
>
> Consequência assumida: o `status` da resposta é o de antes da notificação (`roteado`).
> A tela do totem não depende dele — o protocolo já é definitivo.
>
> **O tipo e o modo gravados são os decididos, não os pedidos.** A trilha `mulher` chega
> como `normal` e é gravada como `discreto`; um texto com sinal crítico de saúde numa
> trilha de segurança é gravado como `saude`. É o que o painel mostra e quem responde
> precisa ver. A intenção original não se perde: `trilha_escolhida` entra no
> `triagem_json`, que é o registro de auditoria do merge — sem ele, "por que este chamado
> foi para o SAMU?" não teria resposta meses depois.
>
> **Assimetria deliberada de payload.** A notificação externa nunca leva o relato
> (MVP-028); o broadcast para o painel leva. Quem atende precisa dele para decidir como
> responder, e o painel está dentro da fronteira de confiança — o grupo de WhatsApp não
> está. Isto torna a autenticação do `WS /ws` (MVP-035) obrigatória, não opcional:
> **a MVP-040 não pode ser cortada sem que o `/ws` fique aberto com o relato.**
>
> Reenvio não tem efeito colateral nenhum: não notifica, não avisa a central de novo. Um
> reenvio é a mesma emergência, e reanunciá-la faria o operador achar que há dois
> chamados. A instrução de tela é recalculada — ela é apresentação, não domínio, e o
> roteador é determinístico.
>
> **Uma das nove mutações sobreviveu, e era defeito do teste.** Aguardar a notificação em
> vez de agendá-la passava os 56 testes, inclusive o que eu acreditava provar o "< 2 s"
> pela divergência entre o `status` da resposta e o do banco. Mas ao aguardar, o
> dicionário em mão continua o de `criar_chamado`, ainda em `roteado` — a divergência
> acontece nos dois desenhos. A prova real é observar **quando o corpo sai pelo ASGI**:
> o teste chama a aplicação crua, sem `TestClient`, e cobra a ordem
> `["resposta enviada", "notificar"]`. Corrigido, as 9 mutações são pegas — inclusive a
> reintrodução do defeito original (gravidade do texto sobrescrevendo a do roteador), que
> derruba 5 testes.

### MVP-031 — `POST /panico`
- **Descrição:** Broadcast paralelo para os canais internos, com status persistente.
- **Prioridade:** P0 · **Depende de:** 030 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/eventos.py`, `backend/tests/test_api_panico.py`
- **Critérios de aceitação:**
  - Roteia como `seguranca` + `emergencia=True`, **sem passar por triagem de texto**
  - Aciona `CANAIS_INTERNOS` em paralelo (`asyncio.gather`)
  - Status final `alerta_ativo` — persistente, não fecha sozinho
  - Devolve `escalonamento_disponivel` com os 4 canais do estado
  - Idempotente por `evento_id`
- **Como validar:** `uv run pytest tests/test_api_panico.py` — 42 testes

> **Ao contrário de `/eventos`, aqui a notificação é aguardada.** Não é inconsistência: a
> resposta carrega `resultados`, e é por eles que a tela decide se oferece os botões de
> escalonamento. Como os canais correm em paralelo, o teto é o de um provider e não a
> soma dos dois.
>
> **`alerta_ativo` não se move.** Nem pelo sucesso da notificação (que em `/eventos`
> levaria a `notificado`), nem pela falha dela. Um pânico cujo aviso não saiu é *mais*
> grave, não menos — e é exatamente quando o escalonamento manual importa. Por isso o
> status é fixado no `criar_chamado` e o resultado da notificação não o toca.
>
> **O endpoint é aberto, e isso cria um vazamento sutil.** O `detalhe` do provider
> carrega o corpo da resposta do webhook (MVP-029), que pode ecoar o número discado —
> `{"error": "invalid number 5586..."}` é resposta plausível da Evolution API. Repassá-lo
> entregaria os contatos institucionais a qualquer um que alcance a API. A resposta usa
> `FALHA_GENERICA`; o detalhe real fica em `notificacoes`, atrás do token do painel.
>
> Reenvio reconstrói `resultados` do banco em vez de devolver lista vazia: a tela pode
> estar recarregando depois de perder a conexão, e uma lista vazia a faria parecer que
> nenhum canal foi acionado.
>
> **O paralelismo é provado por sincronização, não por cronômetro.** Uma `asyncio.Barrier`
> de duas vagas só libera quando os dois acionamentos chegam nela; numa implementação
> sequencial o primeiro esperaria para sempre, e o `wait_for` converte isso em falha em
> vez de travar a suíte.
>
> Duas notas honestas sobre cobertura:
>
> 1. **`emergencia=True` é inobservável na trilha `seguranca`.** `rotear(seguranca)`
>    devolve resultado idêntico com e sem a flag — ela só afeta a trilha de saúde. O
>    parâmetro é passado por clareza de contrato, mas nenhum teste pode distinguir sua
>    presença. O que é testável, e está testado, é a consequência: `risco_imediato`.
> 2. **O descarte de `texto_livre` tem duas camadas independentes** — `PanicoIn` não
>    declara o campo (e o Pydantic ignora extras) *e* `_registro_panico` fixa `None`.
>    Quebrar só uma não falha teste nenhum; as duas juntas falham. Não remover nenhuma
>    das duas acreditando que a outra cobre.

### MVP-032 — `GET /chamados` e `GET /chamados/{id}`
- **Descrição:** Leitura para o painel.
- **Prioridade:** P0 · **Depende de:** 016 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/chamados.py`, `backend/app/models.py`,
  `backend/app/main.py`, `backend/tests/test_api_chamados.py`
- **Critérios de aceitação:**
  - Filtros `tipo`, `status`, `gravidade` combináveis
  - Detalhe inclui `notificacoes` e `estados`
  - `404` para id inexistente
- **Como validar:** `curl "localhost:8000/api/v1/chamados?gravidade=risco_imediato"` —
  42 testes

> **Filtro com valor inválido devolve 422, não lista vazia.** Os parâmetros são tipados
> pelos enums do domínio de propósito. A diferença importa mais do que parece: uma lista
> vazia por causa de `?status=reconhecidos` (no plural, o erro de digitação plausível)
> diria ao operador que **não há chamados** — falso negativo num painel de emergência.
>
> Faltavam os contratos de leitura em `models.py`; foram acrescentados `ChamadoOut`,
> `ChamadoDetalhe`, `NotificacaoOut` e `EstadoOut`. São **lista de campos permitidos**,
> pelo mesmo motivo do `resumo()` da MVP-028: uma coluna nova no schema não passa a sair
> pela API por esquecimento. Ficam de fora `id` (rowid interno), `evento_id` (chave de
> idempotência do totem, sem uso para quem atende) e `triagem_json` — que sai no detalhe
> já **decodificado**, como `triagem`, porque string de JSON dentro de JSON é só má API.
>
> **O `destino` sai mascarado (`…0001`).** A MVP-040 é P1, ou seja, cortável. Se a
> autenticação do painel atrasar, uma rota de leitura aberta não pode ser o caminho para
> enumerar os contatos institucionais de toda a universidade. Os últimos dígitos bastam
> para o operador conferir qual número foi usado; o contato completo continua no banco.
>
> `triagem_json` ilegível devolve `triagem: null` e **serve o chamado assim mesmo**.
> Perder informação diagnóstica é ruim; esconder do operador um chamado que ele precisa
> atender é pior.
>
> Um dos testes estava vazio e a verificação pegou: `GET /chamados/../../etc/passwd` é
> normalizado pelo cliente para `/api/etc/passwd` e **nunca chega à rota** — estava
> exercitando o fallback de SPA da MVP-026, não o detalhe. Trocado por identificadores
> que de fato chegam lá (tentativa de injeção de SQL, espaços), com a asserção que dá
> valor ao caso: a listagem seguinte continua íntegra.

### MVP-033 — `POST /chamados/{id}/ack` e `PATCH`
- **Descrição:** Operador reconhece e movimenta o chamado.
- **Prioridade:** P0 · **Depende de:** 016, 027 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/chamados.py`, `backend/app/api/eventos.py`,
  `backend/app/models.py`, `backend/tests/test_api_chamados.py`
- **Critérios de aceitação:**
  - `ack` grava `acked_at`, muda para `reconhecido` e faz broadcast `atualizado`
  - `PATCH` aceita `status` e `observacao`, registrando em `estado_log`
  - Ambos devolvem o chamado atualizado
- **Como validar:** `uv run pytest tests/test_api_chamados.py` — 75 testes no arquivo
  (33 desta task)

> **Não há máquina de estados restringindo as transições, e isso é decisão, não
> esquecimento.** A regra que protege o sistema — nada rebaixa a proteção já concedida —
> vale para a *inferência automática*, não para o julgamento humano. O operador precisa
> poder cancelar um trote, encerrar um chamado resolvido por telefone ou reabrir um que
> voltou; uma tabela de transições permitidas travaria alguém no meio de uma emergência
> por um caso que ninguém previu. O que garante responsabilidade é o rastro, não a
> proibição: `estado_log` é append-only por gatilho de banco (MVP-015), e a MVP-040
> acrescenta a credencial que diz *quem* mexeu.
>
> **ACK vale para pânico.** `alerta_ativo` não fecha *sozinho* — mas ACK não é sozinho,
> é a central dizendo "recebi", o que a tela do totem mostra como *"Central recebeu"*
> (ARCHITECTURE.md §7 F2). Dois operadores clicando devolve 200 e não reescreve o
> `acked_at` original, de onde sai a métrica de tempo até o reconhecimento.
>
> **Aproveitada a oportunidade para unificar o formato do WebSocket com o do REST.** Os
> `broadcast` de `/eventos` e `/panico` mandavam a linha crua do SQLite — com `id`,
> `evento_id` e `triagem_json` — enquanto `GET /chamados` manda `ChamadoOut`. Como esta
> task acrescentava dois pontos de broadcast, os cinco passaram a usar
> `models.para_painel()`. Sem isso o painel teria que lidar com dois formatos para a
> mesma coisa, e o tipo declarado no frontend mentiria sobre um deles (custo que
> apareceria só na Fase 8). De quebra, o payload do WebSocket herda a lista de campos
> permitidos — é a rota com mais chance de ficar sem autenticação se a MVP-040 atrasar.
>
> Um teste meu falhou e estava errado: comparei o resultado de um `PATCH` vazio com o
> `status` da resposta de `/eventos`, que nasce defasada de propósito (`roteado`, antes
> da notificação em segundo plano). O no-op corretamente devolve o estado atual.
>
> **Nota de cobertura:** `test_gravidade_nunca_muda_por_acao_do_operador` é protegido por
> **três** camadas independentes — o contrato não declara o campo, o endpoint não o
> repassa e `db.atualizar_chamado` não o aceita. Quebrar uma ou duas não falha teste
> nenhum; só as três juntas. Não remover nenhuma acreditando que as outras cobrem.

### MVP-034 — `POST /chamados/{id}/escalonar`
- **Descrição:** Acionamento manual de autoridade do estado, sem encerrar o alerta.
- **Prioridade:** P0 · **Depende de:** 028, 032 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/chamados.py`
- **Critérios de aceitação:**
  - Aceita só canais de `CANAIS_ESTADO`; outro valor → `422`
  - **Registra o acionamento humano; não robo-disca**
  - Grava em `notificacoes` com `escalonamento=1`
  - Não rebaixa `alerta_ativo`
- **Como validar:** `uv run pytest tests/test_api_chamados.py::test_escalonar` — 16 testes

> **"Não robo-disca" é sobre quem inicia, não sobre o que sai.** O endpoint *notifica* o
> canal — é por isso que `CANAIS_ESTADO` tem contato configurável e que
> `POTO_CONTACT_OVERRIDE` existe para "impedir acionar 190/192/193/180 de verdade durante
> os ensaios": se nada fosse enviado, não haveria o que impedir. O que a regra garante é
> que **nenhum caminho automático** chega aqui: nem a triagem, nem o roteador, nem
> `/eventos`, nem `/panico`. As autoridades são *oferecidas* na tela e só saem daqui por
> um POST explícito. Há teste cobrindo isso de fora, com os contatos do estado
> configurados e prontos para receber.
>
> Com contato ausente — que é o default, porque nenhum contato tem valor padrão — nada
> sai do prédio, mas o registro da decisão humana acontece de todo modo: é o registro de
> que alguém acionou a PM às 3h12, ainda que pelo próprio telefone.
>
> Canal interno rejeitado com 422 não é burocracia: um `csv` acionado por aqui entraria no
> histórico marcado como decisão humana de escalonamento, contaminando a única distinção
> que o registro faz entre o que o sistema decidiu e o que uma pessoa decidiu.
>
> Escalonar **não** é idempotente, ao contrário do acionamento: duas tentativas de chamar
> o SAMU são dois fatos distintos no histórico.

### MVP-035 — `WS /ws`
- **Descrição:** Canal de tempo real do painel.
- **Prioridade:** P0 · **Depende de:** 027 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/chamados.py`
- **Critérios de aceitação:**
  - Envia `conectado` ao abrir
  - Transmite `novo_chamado` e `atualizado`
  - `ping` a cada 30 s para manter viva
  - Desconexão não derruba o servidor nem vaza memória
- **Como validar:** `websocat ws://localhost:8000/api/v1/ws` e disparar um evento —
  14 testes
- **Arquivos (além do previsto):** `backend/app/hub.py`

> **O `ping` obrigou uma mudança no hub.** O uvicorn já manda ping de *protocolo*, mas o
> navegador não expõe isso ao JavaScript: a API WebSocket não avisa sobre pong. Sem ping
> de aplicação, o painel não distingue "nada aconteceu nos últimos dez minutos" de "a
> conexão morreu e eu não sei" — na tela os dois estados são idênticos e significam o
> oposto.
>
> Só que o pingador é um **segundo remetente** no mesmo socket, ao lado do `broadcast`.
> Envios simultâneos num WebSocket intercalam frames e o que chega ao navegador é lixo: a
> conexão morre e o operador para de receber alertas. O hub passou a ter um **cadeado de
> escrita por cliente** — que fecha também a lacuna de dois acionamentos simultâneos, e
> serializa só as escritas de um socket, não clientes diferentes (um painel lento não pode
> atrasar os outros, que é a garantia da MVP-027).
>
> O ping roda em tarefa própria e **não** dentro do laço com `wait_for`: cancelar o
> `receive` a cada 30 s para dar a vez ao ping é o que faz uma implementação perder a
> mensagem de desconexão e deixar conexão morta no hub.
>
> O canal é de leitura. Mensagem do cliente é ignorada de propósito — aceitar comandos
> por aqui criaria uma via de escrita sem contrato, sem 422 e sem o 404 dos endpoints
> REST.
>
> **Duas lições da verificação por mutação:**
>
> 1. Ao remover o `conectado`, a rodada **pendurou** em vez de acusar: o `receive_json` do
>    `TestClient` bloqueia para sempre. Os testes de WS passaram a usar um recebedor com
>    prazo, construído sobre o mesmo portal do anyio que o `TestClient` usa por dentro.
>    Mesma lição do teto de envio na MVP-027: o teste tem que reprovar, não travar.
> 2. `test_mensagem_do_cliente_e_ignorada` passava pela **ordem errada** — mandava o
>    comando antes de o chamado existir, então um endpoint que obedecesse não teria o que
>    reconhecer. Corrigido para citar o id real de um chamado já criado.
>
> `pingador.cancel()` é redundante para a correção e mantido de propósito: `_pingar` já
> para sozinho quando `hub.enviar` devolve `False`. A diferença é de tempo — sem o cancel,
> cada painel desconectado deixa uma tarefa dormindo até 30 s. Removê-lo não falha teste
> nenhum; está documentado no código.

### MVP-036 — `GET /health` honesto
- **Descrição:** Diagnóstico que reflete a realidade — corrige o defeito em que o antigo afirmava usar IA sem usar.
- **Prioridade:** P0 · **Depende de:** 024, 028 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/sistema.py`
- **Critérios de aceitação:**
  - `triagem.modo` é `classificador` **somente** se o artefato está carregado; senão `heuristica`
  - Reporta provider de notificação e se o banco responde
  - Campo `avisos[]` alerta quando a triagem está degradada
  - Expõe o **build-id do frontend**, para conferir se o artefato servido é o esperado
    (mitiga o risco de artefato velho — ver MVP-066b)
- **Como validar:** renomear o `.joblib`, reiniciar, e conferir que `/health` diz
  `heuristica` — 28 testes
- **Arquivos:** `backend/app/api/sistema.py`, `backend/tests/test_api_sistema.py`

> Cada campo é **lido da realidade** no momento da pergunta: o artefato é carregado, o
> banco é consultado, o arquivo do build é aberto. Nenhum deles repete uma configuração de
> volta — que era o defeito do projeto de referência, onde a triagem carimbava
> `fonte: "agentes"` sem nenhum LLM ter respondido.
>
> `status` fica `"ok"` enquanto o serviço responde: é sinal de vida, e uma sonda de
> monitoramento precisa dele estável. A degradação vive em `avisos`, e cada aviso nomeia a
> causa **e** a saída (`rode make setup`, `POTO_NOTIF_WEBHOOK_URL`) — um diagnóstico que só
> diz "degradado" obriga a ir ler o código.
>
> Coberto o caso que a formulação do critério deixa passar: `CLF_PATH` apontando para um
> arquivo que **existe mas não é um modelo**. O artefato existe e o modo ainda assim cai
> para `heuristica`, porque o campo pergunta ao classificador se ele carregou.
>
> `POTO_CONTACT_OVERRIDE` ativo virou aviso, não erro: em bancada é o comportamento
> desejado. O que não pode é chegar à operação real sem ninguém notar que todo acionamento
> está sendo desviado para um número de teste.
>
> **Correção ao plano da MVP-066b:** o arquivo de build-id era listado como
> `frontend/build-id`, fora do `dist/`. O deploy envia `dist/` por rsync, então um
> build-id fora dessa pasta **não viajaria com o artefato** — daria para ter um `dist/`
> velho servindo com um build-id novo, que é precisamente o bug silencioso que o build-id
> existe para detectar. Ele passou a ser lido de `dist/build-id`, e a MVP-066b deve
> gravá-lo ali.
>
> Build-id vazio conta como ausente: um arquivo criado por build que falhou no meio faria
> a comparação com o build-id local passar por engano.

### MVP-037 — `GET /config` e `GET /canais`
- **Descrição:** Expor ao frontend as constantes que ele não deve duplicar.
- **Prioridade:** P0 · **Depende de:** 011 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/sistema.py`, `backend/app/config.py`,
  `backend/tests/test_api_sistema.py`
- **Critérios de aceitação:**
  - `/config` devolve `sla`, `canais_estado`, `totem_offline_seg`
  - `/canais` devolve o catálogo com nomes legíveis
  - **Nenhum valor de SLA ou lista de canais fica hardcoded no frontend**
- **Como validar:** `grep -rn "120\|600" frontend/src/` não encontra prazos de SLA —
  verificado, e 13 testes

> **Correção ao plano.** A tabela de rotas em ARCHITECTURE.md §6 previa `/canais`
> devolvendo `{nome, contato}`. Mas `/canais` é endpoint de **sistema, sem credencial** —
> o totem o consulta antes de qualquer autenticação — e devolver o telefone ali entregaria
> os contatos institucionais de toda a universidade a qualquer um que alcance a API. O
> `config.py` já havia tomado a decisão do outro lado: `CANAIS` guarda só `nome`
> justamente para que um `return CANAIS` descuidado não pudesse vazar nada. Implementado
> sem `contato`, e a tabela foi corrigida.
>
> `orientacao` aparece no `sla` com valor **nulo**, não omitida: `null` ali é informação —
> diz ao painel que aquele nível não escalona, em vez de deixá-lo inferir por omissão.
>
> `canais_estado` é **lista**, não objeto: a ordem é a dos botões na tela de alerta ativo.
> Num objeto JSON a ordem não é garantida pelo contrato, e o frontend teria que reordenar,
> duplicando a decisão que este endpoint existe para centralizar.
>
> Faltava `TOTEM_OFFLINE_SEG` em `config.py`; acrescentado com default 15 s (o intervalo
> de dreno da MVP-058) e documentado no `.env.example`.

### MVP-038 — Worker de SLA e escalonamento
- **Descrição:** Loop que escalona chamados sem ACK no prazo.
- **Prioridade:** P0 · **Depende de:** 030, 033 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/sla.py`
- **Critérios de aceitação:**
  - Roda a cada `POTO_SLA_CHECK_INTERVAL` (default 30 s)
  - `notificado` sem ACK além do prazo → notifica o `fallback`, status `escalonado`, broadcast
  - `orientacao` nunca escalona
  - Escalona **uma única vez** por chamado
  - Exceção no loop não derruba o worker
- **Como validar:** `uv run pytest tests/test_sla.py` com prazos reduzidos — 41 testes
- **Arquivos:** `backend/app/sla.py`, `backend/app/db.py`, `backend/app/main.py`,
  `backend/tests/test_sla.py`

> **Extensão deliberada do critério: `falha_notificacao` também escalona.** O critério
> fala só de `notificado` — alguém foi avisado e não respondeu. Mas `falha_notificacao`
> significa que **ninguém** foi avisado, porque o canal falhou. Deixá-lo fora faria o pior
> caso receber menos atenção que o normal: um chamado sobre o qual nenhuma mensagem saiu
> ficaria esperando para sempre. O princípio em `config.SLA_SEGUNDOS` é o oposto — o
> silêncio humano nunca arquiva um chamado.
>
> **`alerta_ativo` não entra.** É persistente por decisão de projeto, e mudar seu status
> rebaixaria o alerta que mantém o cronômetro do totem correndo. O pânico já nasce com
> broadcast paralelo e escalonamento manual na tela, então tem redundância própria.
>
> **O escalonamento de SLA grava `escalonamento=0`.** A coluna significa "uma pessoa
> decidiu isto" (MVP-034), e o escalonamento automático é o oposto: acontece *porque*
> nenhuma pessoa agiu. Confundir os dois tornaria "quem decidiu?" — a única pergunta que a
> coluna existe para responder — insolúvel. O que registra o escalonamento automático é a
> transição para `escalonado` no `estado_log`.
>
> Mede a partir de `created_at`, nunca de `timestamp_local`: um tablet com a hora
> adiantada faria o chamado nascer "já atrasado"; com a hora atrasada, ele nunca
> escalonaria. `created_at` ilegível **não** escalona — acionar a PM por não saber
> interpretar um dado corrompido seria pior que esperar.
>
> Chamado sem `fallback` configurado muda de status de todo modo: o prazo estourou e isso
> é fato. Deixá-lo em `notificado` faria a varredura tentar de novo para sempre e
> esconderia do painel que o prazo venceu.
>
> O laço **dorme antes de varrer**: quando o serviço acabou de subir, nada pode ter
> estourado prazo ainda. O `lifespan` cancela o worker no encerramento — sem isso um
> `reload` em desenvolvimento deixaria workers acumulados varrendo o mesmo banco.
>
> **Nota de cobertura:** `acked_at IS NULL` na consulta é redundante com a checagem de
> status no caminho comum, e uma mutação o revelou. Ele importa num cenário real: o
> operador reabrir um chamado já reconhecido (o `PATCH` da MVP-033 não restringe
> transições de propósito). Como `acked_at` é gravado uma vez só e nunca reescrito, é ele
> que garante o critério na leitura mais forte — o escalonamento automático acontece no
> máximo uma vez na vida de um chamado. Há teste cobrindo isso agora.

### MVP-039 — Testes de contrato da API
- **Descrição:** Cobertura ponta a ponta com `TestClient`.
- **Prioridade:** P0 · **Depende de:** 030–038 · **Status:** ✅ Concluída
- **Arquivos:** `backend/tests/test_api_*.py`
- **Critérios de aceitação:**
  - Cada trilha × modo × com/sem texto verifica que a gravidade **nunca cai**
  - Idempotência verificada via HTTP
  - Banco temporário por teste
  - `make test` verde de ponta a ponta
- **Como validar:** `make test` — **1539 testes**
- **Arquivos:** `backend/tests/test_api_contrato.py` (178 testes), mais
  `test_api_eventos.py`, `test_api_panico.py`, `test_api_chamados.py`,
  `test_api_sistema.py`, `test_api_auth.py`, `test_sla.py`

> **A matriz não verifica valores esperados; verifica uma desigualdade.** Para cada uma
> das 44 combinações trilha × modo × texto, a asserção é que a gravidade final **nunca é
> menor** que a que o roteador determinístico dá para a trilha escolhida. Uma tabela de
> valores esperados precisaria ser reescrita a cada ajuste do classificador; a
> desigualdade vale para sempre, e é exatamente o que o projeto promete.
>
> A mesma invariante é cobrada **no banco**, não só na resposta: o painel e o worker de
> SLA leem de lá, e uma resposta correta com um registro rebaixado faria a central tratar
> a emergência pela gravidade errada.
>
> Este arquivo cobre por HTTP o que `test_regressao_seguranca.py` cobre chamando funções.
> A diferença importa porque o defeito original do projeto de referência **não estava na
> lógica de merge** — estava no endpoint, que chamava a lógica certa e depois sobrescrevia
> o resultado.

### MVP-040 — Autenticação por token no painel
- **Descrição:** Fechar a leitura e escrita do painel, mantendo o acionamento aberto.
- **Prioridade:** P1 · **Depende de:** 032 · **Status:** ✅ Concluída
- **Arquivos:** `backend/app/api/deps.py`
- **Critérios de aceitação:**
  - `X-POTO-Token` comparado a `POTO_PAINEL_TOKEN`
  - Exigido em `/chamados*`, `/ws`
  - **`/eventos` e `/panico` permanecem abertos** — um totem em pânico não falha por credencial
  - Sem token configurado, loga aviso e libera (modo desenvolvimento)
- **Como validar:** `curl localhost:8000/api/v1/chamados` → `401` — 31 testes
- **Arquivos:** `backend/app/api/deps.py`, `backend/app/api/chamados.py`,
  `backend/app/api/sistema.py`, `backend/tests/test_api_auth.py`

> A dependência fica **no router**, não em cada rota: é o que faz uma rota nova nascer
> protegida. Esquecer de decorar um endpoint ali expõe o relato de alguém — o default
> precisa ser fechado.
>
> **O `/ws` fica num router separado**, sem a dependência: uma `HTTPException` não tem
> tradução num handshake de WebSocket, e o cliente receberia um erro sem explicação. A
> autorização acontece dentro do handshake e recusa com **1008** (violação de política),
> que é o código que o navegador entrega ao `onclose` e o painel pode exibir. Ela roda
> **antes** do `hub.connect`: um cliente sem credencial não pode entrar no hub nem por um
> instante, ou um broadcast concorrente lhe entregaria o relato de um chamado.
>
> O navegador não deixa definir cabeçalhos num `new WebSocket()`, então o `/ws` também
> aceita `?token=`. A troca é consciente: query string aparece em log de acesso, e por isso
> o cabeçalho tem precedência.
>
> `secrets.compare_digest` e não `==`: a comparação ingênua sai no primeiro byte diferente,
> e a diferença de tempo permite descobrir o token um caractere por vez. É a mesma rede
> local de onde vem o tablet — e de onde viria quem quisesse ler os relatos.
>
> O modo desenvolvimento passou a ser reportado pelo `/health` (`seguranca.painel_protegido`
> + aviso), não só no log: **o aviso no log some no scroll**, e o `/health` é onde alguém
> procura antes de colocar em operação. O token em si nunca aparece ali — um diagnóstico
> que devolvesse a credencial para provar que ela existe seria a forma mais direta possível
> de vazá-la.

---

# Fase 5 — Design system

### MVP-041 — Fontes auto-hospedadas
- **Descrição:** Baixar Michroma, Inter e Material Symbols para `public/fonts/`. No projeto antigo vinham de CDN e quebravam offline — inclusive **todos os ícones dos botões**.
- **Prioridade:** P0 · **Depende de:** 003 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/public/fonts/`, `frontend/src/estilos/fontes.css`,
  `frontend/src/main.tsx`, `frontend/index.html`
- **Critérios de aceitação:**
  - `.woff2` locais de Michroma 400, Inter 400/500/600/700 e Material Symbols Rounded
  - `@font-face` com `font-display: swap`
  - **Zero referência a `fonts.googleapis.com` ou `fonts.gstatic.com`**
- **Como validar:** DevTools → Network offline → recarregar: tipografia e ícones intactos;
  `grep -rn "googleapis" frontend/` vazio — **verificado, 0 hits**

> **164 KB, não 916.** A primeira baixa ingênua — pedir Inter 400/500/600/700 e o
> Material Symbols completo — deu 916 KB. Duas descobertas cortaram 82%:
>
> 1. **Inter é variable font.** Pedir os quatro pesos separadamente traz o *mesmo arquivo*
>    quatro vezes (confirmado por `md5sum`: quatro hashes idênticos). `wght@400..700`
>    devolve um arquivo por subset, com toda a faixa de pesos.
> 2. **`icon_names=` subseta o Material Symbols.** A família completa tem 363 KB para
>    ~3.000 glifos; pedindo os sete que o `<Sym>` usa, são **2,3 KB**.
>
> Só os subsets `latin` e `latin-ext` — português não usa cirílico, grego nem vietnamita.
> Os `unicode-range` são preservados: sem eles o navegador baixaria os dois arquivos
> sempre, em vez de escolher.
>
> O `@font-face` ficou em `fontes.css` e não em `base.css` como o plano previa: o bloco é
> longo e mecânico, e `base.css` (MVP-042) é onde moram decisões de design. Separar evita
> as duas tasks disputando o mesmo arquivo.
>
> **O que o offline quebrava era pior do que tipografia.** Sem rede, texto cai para a fonte
> do sistema — tolerável. Mas Material Symbols funciona por *ligadura*: os botões das
> trilhas ficariam sem `stethoscope`, `shield` e `female`, e o de pânico sem `emergency`.
> Ícone ausente numa tela de socorro é um botão que ninguém identifica.
>
> `index.html` ganhou `preload` das três fontes da primeira tela — sem isso os ícones
> chegam depois do primeiro paint e os botões piscam vazios.
>
> Nota: o domínio do CDN não aparece em comentário nenhum, de propósito. A validação desta
> task é um `grep` por ele; um comentário que o citasse tornaria o grep inútil como
> verificação.

### MVP-042 — `tokens.css` e `base.css`
- **Descrição:** Portar literalmente os tokens do POTO (PLAN.md §6).
- **Prioridade:** P0 · **Depende de:** 003 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/estilos/tokens.css`, `base.css`,
  `frontend/scripts/verificar-tokens.mjs`, `frontend/package.json`
- **Critérios de aceitação:**
  - Todos os tokens de cor, raio, espaço, tipografia, sombra e `--touch: 64px`
  - Valores hex **idênticos** aos de PLAN.md §6
  - `base.css` define reset, `body` com `--paper`, foco `outline: 3px var(--rust)`
  - `@media (prefers-reduced-motion: reduce)` desliga animações
- **Como validar:** `npm run check-tokens` — **32 valores conferem**, automatizado

> **A comparação virou script, não conferência manual.** Fazer isso à mão uma vez não
> protege nada: o risco real é a **deriva** — alguém ajustando um hex meses depois e a
> interface deixando de ser a identidade aprovada sem que ninguém note. O script lê o
> PLAN.md §6 como fonte da verdade em vez de copiar os valores para dentro de si (uma
> cópia teria exatamente o problema que ela existiria para resolver) e roda junto do
> `npm run lint`. Verificado que pega deriva de verdade: trocar `--rust` por `#d0402b`
> reprova.
>
> A comparação é **semântica, não textual**: `rgba(20,15,5,.05)` e
> `rgba(20, 15, 5, 0.05)` são a mesma cor, e travar nessa diferença faria o script cobrar
> a formatação do documento em vez da identidade visual. A normalização é pequena de
> propósito — espaço, caixa e zero à esquerda de decimal, nada além.
>
> Sem dependência nova: o projeto não tem nem planeja runner de teste no frontend, e
> acrescentar um por causa de 30 linhas seria desproporcional.
>
> Decisões do `base.css` que o critério não lista mas a interface exige:
>
> - `touch-action: manipulation` em botões. Sem isso o navegador interpreta
>   toque-e-arraste como rolagem e **cancelaria a pressão de 1 s do `<Panic>`** (MVP-046)
>   no meio do gesto.
> - `user-select: none` no `body`: nenhuma tela do totem tem texto para selecionar, e um
>   toque mantido abriria o menu de seleção sobre o botão.
> - `min-height/min-width: var(--touch)` em todo controle, para que um componente que
>   esqueça de declarar ainda respeite o mínimo.
> - `.tabular` para protocolo e cronômetro: sem largura fixa de dígito o
>   `CALL-2026-000001` muda de largura a cada número e o cronômetro "pula".
>
> **`prefers-reduced-motion` usa `0.01ms`, não `0`.** Com duração zero alguns navegadores
> não disparam `transitionend`/`animationend`, e código que espera o evento travaria. Não
> é preferência estética: movimento pode desencadear náusea e enxaqueca em quem tem
> desordem vestibular, e num totem de emergência a pessoa já pode estar em sofrimento.

### MVP-043 — Componente `<Sym>` (ícones)
- **Descrição:** Wrapper de Material Symbols Rounded com os tamanhos do POTO.
- **Prioridade:** P0 · **Depende de:** 041, 042 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/componentes/Sym.tsx`, `frontend/src/estilos/fontes.css`
- **Critérios de aceitação:**
  - Tamanhos `xs:18 · sm:22 · md:28 · lg:40 · xl:56`
  - Glifos: `stethoscope`, `shield`, `female`, `info`, `emergency`, `check`, `arrow_back`
  - `aria-hidden="true"` (o rótulo textual carrega o significado)
- **Como validar:** conferido contra `../poto-pitch/capturas-de-tela/Tela-Totem.png` —
  `stethoscope`, `shield` e `female` em ferrugem, `info` em `--muted`, `emergency` no
  pânico

> **As 7 ligaduras foram verificadas dentro do arquivo de 2,3 KB**, não assumidas. A fonte
> é servida subsetada por nome (MVP-041), e se um glifo faltasse o nome apareceria
> **escrito na tela** em vez do desenho — Material Symbols funciona por ligadura. A
> inspeção (com `fontTools`, num venv descartável) mostrou 30 glifos: 7 ícones, as 21
> letras usadas nos nomes, `space` e `.notdef`; e as 7 ligaduras mapeando para
> `uniE5C4`/`uniE5CA`/`uniE1EB`/`uniE590`/`uniE88E`/`uniE75B`/`uniF805`.
>
> Na primeira tentativa a verificação disse "0 ligaduras" e quase aceitei que o subset as
> tinha descartado. Era erro meu: o GSUB usa `LookupType 7` — substituição de **extensão**
> — e a tabela real está dentro de `ExtSubTable`, que eu não desembrulhava.
>
> **O tipo `GlifoSym` enumera os glifos de propósito**, em vez de aceitar `string`: pedir
> um ícone fora do subset é um erro silencioso em tempo de execução (o nome renderiza como
> texto), e o tipo o transforma em erro de compilação. O acoplamento com a lista de
> `icon_names=` está documentado nos dois arquivos.
>
> `aria-hidden` sem exceção, e não `aria-label`: quem carrega o significado é o rótulo
> textual ao lado. Um label aqui faria o leitor de tela anunciar a mesma coisa duas vezes.
>
> Duas armadilhas de ligadura tratadas no estilo inline: `text-transform: none` — um
> `uppercase` herdado de rótulo em caixa-alta transformaria `shield` em `SHIELD`, que não é
> ligadura nenhuma e viraria a palavra na tela — e `letter-spacing: normal`, que pela mesma
> razão não pode herdar tracking.
>
> `opsz` acompanha o tamanho em vez de ficar fixo: os glifos são desenhados numa grade
> óptica, e um ícone de 56px com a espessura de traço de 18px fica frágil.

### MVP-044 — `<Wordmark>` e `<StatusPill>`
- **Descrição:** Marca e indicador de conectividade do header.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/componentes/{Wordmark,StatusPill}.tsx`,
  `frontend/src/comum/useOnline.ts`
- **Critérios de aceitação:**
  - Wordmark: Michroma 16px, `letter-spacing: .14em`, UPPERCASE, **pontos em `--rust`**
  - Clicar no wordmark volta à tela inicial
  - StatusPill: ponto 8px — verde `--ok` online, ferrugem `--rust` offline
  - Mostra `· N na fila` quando há eventos pendentes
- **Como validar:** alternar online/offline no DevTools e observar a mudança; markup
  conferido por renderização no servidor (pontos em `--rust`, ponto 8px trocando
  `--ok`/`--rust`, `· N na fila` com `.tabular`)

> **Clicar no wordmark não é navegação, é saída de emergência de interface.** Num totem de
> parede, alguém que entrou numa trilha por engano — ou que precisa que a tela pare de
> mostrar o que está mostrando — toca a marca. É o gesto mais aprendido que existe na web,
> e por isso vale mais que um botão "voltar" explícito.
>
> O texto é montado letra por letra porque os pontos precisam de cor própria; um
> `aria-label` cobre o custo, sem o qual o leitor de tela soletraria quatro `span`
> separados. A marca também anula o `min-height: var(--touch)` do `base.css` e cresce por
> `padding`: o mínimo de 64px esticaria o header inteiro.
>
> **O que o `StatusPill` comunica não é "tem internet".** É *"o que você tocar chega agora
> ou fica guardado"* — e é por isso que o contador `· N na fila` é a única informação
> acionável ali. A tela inicial não é lugar para alarmar sobre rede quando o sistema
> continua funcionando offline.
>
> `aria-live="polite"` e não `assertive`: interromper o leitor de tela no meio de uma
> trilha de socorro para anunciar "offline" seria pior que esperar a pausa. E cor não é o
> único sinal — o texto diz "Online"/"Offline" ao lado do ponto.
>
> **`navigator.onLine` responde a pergunta errada** e o `useOnline` documenta isso: ele
> diz se a interface de rede está ativa, não se o backend responde. Num totem no wi-fi da
> universidade com o roteador fora do ar, devolve `true`. Aceitável para o MVP porque o
> sinal verdadeiro é o resultado do POST, tratado pela fila offline (MVP-057) — o
> indicador é dica, e o contador de fila é o dado real.

### MVP-045 — Componente `<Choice>`
- **Descrição:** O botão-cartão das trilhas — o elemento mais importante da interface.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/componentes/Choice.tsx`, `frontend/src/estilos/base.css`
- **Critérios de aceitação:**
  - `min-height: 168px`, `padding: 28px 16px`, borda `1.5px var(--line)`, raio `var(--r-lg)`
  - Ícone 56px em `--rust`; variante `muted` usa `--muted`
  - Rótulo em Michroma 13px, `letter-spacing: .04em`, centrado
  - Hover → borda `--rust` + fundo `--rust-soft`; active → `scale(.97)`
  - Alvo de toque ≥ 64px; foco visível
- **Como validar:** comparação lado a lado com
  `../poto-pitch/capturas-de-tela/Tela-Totem.png` — conferido: três trilhas em ferrugem,
  "Outros" em `--muted`, grade 2×2

> **A cor do ícone é informação, não decoração.** Três trilhas usam ferrugem; "Outros" usa
> `--muted`. É a regra 60/30/10 dizendo que aquela trilha não é emergência, e é o que a
> captura de referência mostra. Quem chega com pressa precisa que as três opções urgentes
> se destaquem da quarta.
>
> **`:hover` ficou guardado por `@media (hover: hover)`.** Num tablet o navegador emula
> hover *depois* do toque, e sem a guarda o cartão ficaria grudado em destaque até o
> próximo toque em outro lugar — a tela mentiria sobre qual trilha está selecionada.
>
> Hover, active e a grade vivem em CSS e não em estilo inline porque pseudo-classes e
> media queries não existem em `style`. As medidas ficam no `style` do componente, junto do
> código que as usa, já que vêm de PLAN.md §6.
>
> `transition` lista as três propriedades em vez de usar `all`: com `all` a cor do texto e
> o raio da borda também animariam, e esses devem ser instantâneos.
>
> `maxWidth: 18ch` no rótulo — sem isso "Assédio / Sala Lilás" quebra em três linhas e
> desalinha o cartão em relação ao vizinho da grade.
>
> `desabilitado` existe para o envio em curso (MVP-050): sem ele, dois toques rápidos
> geram dois chamados, e a idempotência do backend só protege reenvios do **mesmo**
> `evento_id` — dois toques geram dois ids distintos.

### MVP-046 — Componente `<Panic>` com pressionar-e-segurar
- **Descrição:** Botão de pânico — sempre o elemento de maior peso visual da tela. Como é
  virtual (não físico), precisa de intenção deliberada: **segurar por 1 s**. Um botão de
  toque simples numa tela pública dispara com um roçar de mão, e cada disparo faz broadcast
  real para CSV e Sala Lilás.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/componentes/Panic.tsx`,
  `frontend/src/comum/useMovimentoReduzido.ts`, `frontend/src/estilos/base.css`
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
  que **nenhum** chamado foi criado — pela galeria de componentes (MVP-047)

> **Esforço físico em vez de decisão cognitiva.** O desenho alternativo — uma tela de "tem
> certeza?" — seria pior: ela pede uma decisão de quem está em pânico. Segurar é algo que o
> corpo faz; confirmar é algo que a cabeça faz, e a cabeça é justamente o que está ocupado.
> Daí também o critério de **não** abrir tela de confirmação.
>
> **A barra de progresso não é enfeite.** Sem realimentação, quem segura 400 ms e não vê
> nada concluir que o botão não funciona — e solta. É o que torna o requisito de 1 s
> viável.
>
> `scaleX` em vez de `width`: transforma na GPU e não provoca relayout a cada 16 ms. E a
> barra **não tem transição**, de propósito — uma transição faria o preenchimento continuar
> avançando depois de a pessoa soltar, e o botão pareceria ter disparado sem ter.
>
> **Erro corrigido durante a implementação.** A primeira versão tratava
> `prefers-reduced-motion` em CSS, com `transform: scaleX(var(--panic-degrau))` — e eu
> nunca definia a variável. A barra ficaria em `scaleX(0)`, ou seja **invisível**: a falha
> exata que o degrau existe para evitar. Quantizar exige conhecer o progresso, então a
> decisão passou para o componente (`useMovimentoReduzido`, quatro degraus de 25%).
> Desligar a animação não serve; ela precisa continuar avançando, só em saltos.
>
> `pointercancel` é tratado porque é o que dispara quando o sistema toma o gesto — uma
> notificação chegando, o navegador decidindo que é rolagem. Sem ele o botão ficaria preso
> em "pressionando" para sempre. `onPointerLeave` cobre o dedo escorregando para fora, e
> `onBlur` o foco saindo no meio de uma pressão por teclado.
>
> `acionar` fica num `ref` atualizado a cada render: sem isso, um `onAcionar` recriado pelo
> pai entraria nas dependências do `useCallback` e **cancelaria a pressão em curso**.
>
> `limpar()` roda **antes** de `acionar()`: se o callback levantar, o botão não pode ficar
> preso em "pressionando" com um timer rodando. E o `useEffect` de desmontagem existe
> porque a tela troca ao acionar qualquer trilha — o timer precisa morrer com o componente.
>
> `navigator.vibrate` vai dentro de `try` e com `?.`: a API não existe em iOS nem em
> desktop, e alguns navegadores lançam se chamada sem gesto do usuário. Vibração é conforto,
> não requisito.

### MVP-047 — Componente `<Confirm>`
- **Descrição:** Tela de confirmação nas três variantes: neutra, padrão e crítica.
- **Prioridade:** P0 · **Depende de:** 042, 043 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/componentes/Confirm.tsx`, `frontend/src/Galeria.tsx`,
  `frontend/src/App.tsx`
- **Critérios de aceitação:**
  - Marca circular com ✓, título e protocolo em tabular
  - Variante `critico`: fundo `--rust`, texto branco
  - Variante `neutral`: fundo `--paper`, ícone `--muted`, **sem protocolo**
  - Aviso de offline em faixa `--rust-soft`
- **Como validar:** `make frontend` → `/galeria` — as três variantes lado a lado

> **A variante `neutral` recebe o protocolo e não o mostra.** Não é que o protocolo falte:
> ele é deliberadamente ocultado. Se o agressor está a três metros, um protocolo na tela
> transforma o socorro em risco. Quem decide isso é o backend, pelo
> `instrucao_totem.tela_neutra` — o frontend nunca escolhe ser discreto. A marca também
> vai em `--muted` e não em ferrugem: nada nessa tela pode chamar atenção de quem olha por
> cima do ombro.
>
> A faixa de offline fica em `--rust-soft` **inclusive na variante crítica**, onde o fundo
> já é ferrugem: o aviso precisa se destacar do fundo, não combinar com ele.
>
> `role="status"` + `aria-live="polite"` para o leitor de tela anunciar a confirmação sem
> que a pessoa precise procurá-la. E o protocolo em `.tabular`, porque ele é lido em voz
> alta para a central e copiado à mão — dígitos de largura variável atrapalham os dois.
>
> **Acrescentada uma galeria de componentes em `/galeria`.** Quatro tasks desta fase pedem
> validação visual ("conferir contra `Tela-Totem.png`", "comparação lado a lado",
> "renderizar as três variantes lado a lado", "tocar 5× rápido e confirmar que nada foi
> criado"). Sem um lugar onde tudo apareça junto, cada conferência exigiria montar uma tela
> descartável e nenhuma ficaria repetível. A galeria inclui o registro de acionamentos, que
> é como se verifica o critério do `<Panic>`.
>
> A rota é **só de desenvolvimento**, e isso foi medido, não presumido. A primeira versão
> usava `import` estático guardado por `import.meta.env.DEV` e eu escrevi no comentário que
> o bundler removeria o módulo. **Estava errado:** o bundle cresceu 11,7 KB e a string da
> galeria estava lá — um bundler não descarta um módulo só porque o único uso está atrás de
> um `if` falso. Corrigido com `lazy(() => import(...))` dentro do guarda; o bundle voltou
> a 220,11 KB e a galeria não aparece no `dist/`.

---

# Fase 6 — Telas do totem

### MVP-048 — Cliente de API tipado
- **Descrição:** Camada única de acesso ao backend, com tipos derivados dos contratos.
- **Prioridade:** P0 · **Depende de:** 010, 030 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/comum/{api.ts,tipos.ts}`, `frontend/src/vite-env.d.ts`
- **Critérios de aceitação:**
  - `novoEvento()` gera `evento_id` com `crypto.randomUUID()` **antes** do envio
  - `enviarEvento()`, `listarChamados()`, `ackChamado()`, `obterConfig()`
  - Base da API derivada de `location.origin` (dev usa proxy do Vite)
  - Erro de rede levanta exceção tipada para a fila tratar
- **Como validar:** `npm run build` sem erro de tipo — verificado

> **O `evento_id` nascer no cliente é o ponto mais importante do arquivo.** Ele é a chave
> de idempotência: um evento que falhou, ficou na fila e foi reenviado carrega o **mesmo**
> id, e o backend devolve o chamado existente em vez de criar um segundo alarme para a
> mesma emergência. Gerar o id no momento do envio quebraria isso — cada tentativa teria
> um id novo e a fila multiplicaria o chamado.
>
> **`crypto.randomUUID` exige contexto seguro**, e na rede local da universidade o totem
> roda em **HTTP**, onde a API não existe. Há fallback com `crypto.getRandomValues`
> montando um UUID v4 à mão: o que importa é unicidade, não unicidade criptográfica.
>
> **Dois tipos de erro, porque o tratamento é oposto.** `ErroRede` (rede caiu, DNS,
> timeout) é candidato a enfileirar e reenviar; `ErroApi` (422, 404) significa que o envio
> **chegou e foi recusado**, e reenviar o mesmo payload falharia igual. Sem a distinção, a
> fila offline entraria em laço com um payload inválido.
>
> `AbortController` com teto de 8 s: `fetch` sem sinal de abortar espera o timeout do
> sistema operacional, que pode passar de um minuto. Um totem não pode ficar preso nisso.
>
> O corpo de erro é lido como texto e só depois decodificado — um 502 de proxy devolve
> HTML, e sem isso um erro de servidor viraria erro de parsing, confundindo o diagnóstico.
>
> Os tipos são escritos à mão e não gerados do OpenAPI: gerar exigiria um passo de build
> acoplado a um backend rodando, e a Pi **não compila** o frontend (D1c). O preço é que a
> divergência só apareceria em execução; a mitigação são os testes de contrato da MVP-039,
> que cobram a forma das respostas pelo lado do servidor.
>
> `TOTEM_ID` vem de `VITE_POTO_TOTEM_ID` e não fixo no código: dois totens não poderiam
> coexistir, e o painel precisa saber **de onde** veio o chamado para despachar a equipe ao
> lugar certo.
>
> Nota de ferramenta: o `tsconfig` liga `erasableSyntaxOnly`, que proíbe propriedades
> declaradas no construtor — a garantia de que apagar os tipos basta para rodar. As classes
> de erro usam campos explícitos.

### MVP-049 — Shell do totem
- **Descrição:** As três zonas de DESIGN.md §12: header, main centralizado, footer.
- **Prioridade:** P0 · **Depende de:** 044 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/totem/Shell.tsx`, `frontend/src/estilos/totem.css`
- **Critérios de aceitação:**
  - `max-width: 960px`, `padding: clamp(20px, 4vw, 48px)`, `min-height: 100dvh`
  - Header: wordmark à esquerda, status à direita
  - Main: `flex: 1`, centralizado vertical e horizontalmente
  - Footer: `margin-top: auto`
  - `overflow: hidden` e `user-select: none` (kiosk)
- **Como validar:** abrir em 1280×800 sem barra de rolagem — a verificação nas quatro
  resoluções é o critério da MVP-055, que mede no aparelho real

> Ficou em `Shell.tsx` e não em `Totem.tsx` como o plano previa: `Totem.tsx` é o contêiner
> de **fluxo** (MVP-051), e misturar layout com máquina de estados tornaria os dois piores
> de ler. O shell é puramente apresentação e recebe tudo por prop.
>
> **`100dvh` e não `100vh`.** No Chrome do Android a barra de endereço entra e sai, e
> `100vh` mede a altura *sem* ela — o rodapé ficaria abaixo da borda visível justamente
> enquanto a barra está presente, que é o estado inicial antes de a pessoa rolar (e num
> kiosk ela nunca rola).
>
> **`overflow: hidden` é uma afirmação, não uma proteção.** Se o conteúdo não cabe, o
> layout está errado e precisa ser corrigido (MVP-055); esconder com rolagem mascararia o
> problema, e num totem ninguém descobre que precisa rolar.
>
> Três `min-height: 0` que não estão no critério e sem os quais o rodapé é cortado em
> paisagem: um filho de flex container não encolhe abaixo do seu conteúdo por default, e
> combinado com o `overflow: hidden` do shell isso empurra o footer para fora da área
> visível. É exatamente o caso difícil que a MVP-055 nomeia — ~530px de altura útil na
> paisagem do Tab A11.
>
> O CSS ficou em `totem.css` separado do `base.css`: o painel da central tem tabela longa e
> **precisa** rolar, e não pode herdar `overflow: hidden`.
>
> `fundo` e `semCromo` como props existem para a tela de alerta ativo (MVP-054), que é
> ferrugem inteira e ocupa a tela sem header nem rodapé.

### MVP-050 — Tela inicial com as 4 trilhas
- **Descrição:** "Como podemos ajudar?" com a grade 2×2 e o pânico no rodapé.
- **Prioridade:** P0 · **Depende de:** 045, 046, 049 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/totem/telas/Home.tsx`, `frontend/src/totem/trilhas.ts`,
  `frontend/src/totem/Totem.tsx`, `frontend/src/App.tsx`, `frontend/src/estilos/totem.css`
- **Critérios de aceitação:**
  - Título em Michroma `clamp(28px, 4.5vw, 44px)`
  - Trilhas na ordem: Emergência médica · Segurança · Assédio/Sala Lilás · Outros
  - "Outros" com variante `muted`; "Assédio/Sala Lilás" dispara `modo: discreto`
  - Grade `1fr 1fr`, `gap: 16px`; 1 coluna abaixo de 560px
  - **Todo o fluxo principal em ≤ 2 toques**
- **Como validar:** abrir e conferir contra `Tela-Totem.png` — ordem, cores e título
  verificados por renderização: `Emergência médica · Segurança · Assédio / Sala Lilás ·
  Outros`, com `info` em `--muted` e as outras três em ferrugem

> **Dois toques, e o segundo já é a confirmação.** Não há tela intermediária de
> detalhamento, não há "tem certeza?", não há formulário. O `texto_livre` existe no
> contrato do backend e é opcional de propósito — quem está em emergência não digita.
>
> A tabela de trilhas ficou em `trilhas.ts` e não espalhada no JSX: a **ordem é a ordem da
> tela** e precisa de um lugar só. Ela não é arbitrária — médica e segurança primeiro
> porque são as mais frequentes e as de maior gravidade; "Outros" por último porque é o
> destino de quem não se encaixa nas três.
>
> **O `modo: "discreto"` enviado daqui é intenção, não decisão.** O roteador força discreto
> na trilha `mulher` de qualquer jeito (MVP-012, e a MVP-030 grava o modo *decidido*).
> Mandá-lo do cliente só evita que o primeiro quadro da confirmação apareça no modo errado
> enquanto a resposta não chegou — a garantia continua sendo do backend.
>
> `max-width: 20ch` no título: sem isso "Como podemos ajudar?" quebra em três linhas no
> tablet em retrato e empurra a grade para baixo do rodapé.
>
> O pânico não é uma quinta trilha. Ele fica no rodapé e é o único elemento em ferrugem
> cheia da tela (regra 60/30/10) porque é o caminho de quem **não consegue nem escolher**.

### MVP-051 — Fluxo de acionamento e confirmação
- **Descrição:** Toque → POST → tela de confirmação com protocolo.
- **Prioridade:** P0 · **Depende de:** 047, 048, 050 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/totem/Totem.tsx`,
  `frontend/src/totem/telas/Confirmacao.tsx`, `frontend/src/comum/beep.ts`
- **Critérios de aceitação:**
  - Estado de carregamento durante o POST; botões desabilitados (sem duplo toque)
  - Confirmação usa `instrucao_totem` **do backend**, não lógica do cliente
  - `feedback_sonoro` toca um beep de 660 Hz por 0,12 s
  - Erro de rede não trava a tela — cai na fila (MVP-057)
  - Do toque à confirmação em < 2 s
- **Como validar:** acionar cada trilha e conferir o chamado no banco — verificado com
  respostas **reais** do backend:
  `saude→padrao` · `seguranca→critico` · `mulher(normal)→neutral, som=false` ·
  `ouvidoria→padrao`

> **O cliente não decide nada sobre a ocorrência.** Ele coleta o toque, manda, e obedece ao
> `instrucao_totem` que volta — mensagem, som e discrição são todos do backend. Se
> decidisse aqui, a garantia de modo discreto passaria a depender de o frontend lembrar de
> aplicá-la, que é exatamente a dependência que a MVP-030 tirou do cliente.
>
> A verificação confirmou isso na prática: `mulher` enviado como `modo: normal` volta com
> `tela_neutra: true` e `feedback_sonoro: false`. O roteador forçou discreto.
>
> **`varianteDe` checa discreto ANTES de crítico**, e a ordem é a decisão mais delicada do
> arquivo. A trilha mulher chega com gravidade alta; inverter faria um pedido discreto
> virar uma tela vermelha anunciando emergência para quem estiver olhando por cima do
> ombro.
>
> `setEstado({tela: "enviando"})` acontece **antes de qualquer `await`**: dois toques
> rápidos gerariam dois `evento_id` distintos, e a idempotência do backend só protege
> reenvios do **mesmo** id.
>
> **O beep é gerado por oscilador, não por arquivo.** Um `.mp3` é mais um recurso para
> carregar e para faltar offline, e tem latência de decodificação — o oscilador sai no
> mesmo quadro do toque, que é o que faz a realimentação parecer resposta e não eco. O
> contexto de áudio é criado **uma vez**: um por beep esgotaria o limite do navegador e o
> som pararia de sair depois de algumas dezenas de acionamentos — numa demonstração,
> exatamente no meio. Envelope curto em vez de liga/desliga seco, senão o corte abrupto
> produz um clique que soa como defeito.
>
> Erro de rede mostra aviso **abaixo** das trilhas, não num modal: a pessoa precisa poder
> tocar novamente sem fechar nada. E um totem preso numa tela de carregamento é pior do que
> um totem que admite a falha.

### MVP-052 — Retorno automático à tela inicial
- **Descrição:** O totem sempre volta sozinho ao repouso.
- **Prioridade:** P0 · **Depende de:** 051 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/totem/telas/Confirmacao.tsx`,
  `frontend/src/totem/Totem.tsx`, `frontend/scripts/verificar-prazos.mjs`
- **Critérios de aceitação:**
  - **5 s** discreto · **12 s** crítico · **9 s** demais
  - Timer limpo ao desmontar (sem vazamento)
  - Alerta ativo de pânico **não** tem retorno automático — é persistente
- **Como validar:** cronometrar cada variante; `npm run check-prazos` confere a tabela
  contra esta própria linha do TASKS.md

> **Por que os prazos são diferentes.** Discreto é o mais curto porque a tela não deve
> ficar aberta mais do que o necessário se alguém puder estar olhando por cima do ombro.
> Crítico é o mais longo porque o protocolo precisa ser lido e anotado, possivelmente por
> quem está com a mão tremendo.
>
> Os números são verificados por script, lendo **esta linha do TASKS.md** como fonte —
> mesmo princípio do `verificar-tokens.mjs`. Alguém "arredondando" os 12 s do crítico para
> 8 passaria despercebido de outro modo, e é justamente o crítico que precisa dos 12.
> Verificado que pega deriva real.
>
> **O critério do pânico persistente não estava implementado e foi corrigido aqui.** A
> MVP-051 mandava o pânico para a mesma tela de confirmação, que voltava ao repouso em 12 s
> — contradizendo `alerta_ativo`, o único estado persistente do sistema (MVP-031). Quem
> está em pânico não deve ver o totem voltar ao repouso enquanto espera: pareceria que o
> pedido foi cancelado. A prop `persistente` desliga o timer, e a MVP-054 substitui essa
> tela pela de alerta ativo completa.
>
> O `clearTimeout` na limpeza do efeito não é formalidade: sem ele, acionar duas vezes em
> sequência deixaria dois timers vivos e o segundo devolveria o totem ao início no meio da
> confirmação seguinte — ou durante um alerta ativo.
>
> `onVoltar` fica num `ref`: sem isso um callback recriado pelo pai reiniciaria o timer a
> cada render e o totem **nunca** voltaria ao repouso.

### MVP-053 — Modo discreto
- **Descrição:** A trilha mulher não pode deixar rastro na tela.
- **Prioridade:** P0 · **Depende de:** 051 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/scripts/verificar-discreto.mjs`, `frontend/package.json`
- **Critérios de aceitação — verificados na tela:**
  - Mensagem genérica "Seu pedido foi registrado. Aguarde atendimento."
  - **Sem protocolo visível**
  - **Sem som** (`feedback_sonoro: false`)
  - Sem menção a "Sala Lilás", "denúncia" ou ao canal acionado
  - Retorno em 5 s
  - Decidido pelo backend via `tela_neutra`, não por condicional no cliente
- **Como validar:** `npm run check-discreto` — **automatizado**, 9 termos proibidos
  varridos no HTML renderizado

> **A inspeção manual virou script, e aqui isso importa mais que em qualquer outra task.**
> Esta é a propriedade mais crítica da interface: se o agressor está a três metros, uma
> palavra errada na tela transforma o socorro em risco. Uma inspeção manual protege o dia
> em que foi feita; um script protege todos os dias depois.
>
> O que se verifica é o **HTML de verdade** — o componente é renderizado com
> `react-dom/server` a partir de uma resposta real do backend e o resultado é varrido por
> palavra proibida. Checar o código-fonte em vez do resultado deixaria passar a palavra
> chegando por caminho indireto: uma mensagem vinda da API, um rótulo herdado, um
> `aria-label`.
>
> Termos varridos: `Sala Lilás`, `Lilás`, `denúncia`/`denuncia`, `assédio`/`assedio`,
> `CALL-` (o protocolo, que a variante **recebe** e não mostra), `sala_lilas`,
> `central_180`. Verificado que pega vazamento real: fazer a variante `neutral` mostrar o
> protocolo reprova e imprime o HTML.
>
> **Há também a verificação inversa**, e ela não é cerimônia: se o componente renderizasse
> vazio, a ausência das palavras proibidas não provaria nada e o check passaria de graça. O
> script exige que a mensagem genérica esteja presente.
>
> Nenhuma dependência nova: `rolldown` já vem com o Vite 8. O bundle é gerado em
> `node_modules/.cache` e não em `/tmp` porque a resolução de módulos do Node parte da
> localização do arquivo, não do diretório de trabalho — em `/tmp` ele não acharia
> `react-dom`.

### MVP-054 — Tela de alerta ativo (pânico)
- **Descrição:** Estado persistente com cronômetro e escalonamento manual.
- **Prioridade:** P0 · **Depende de:** 031, 051 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/totem/telas/AlertaAtivo.tsx`,
  `frontend/src/comum/{useCronometro.ts,useEventosWS.ts}`,
  `frontend/src/totem/Totem.tsx`, `frontend/src/estilos/totem.css`
- **Critérios de aceitação:**
  - Fundo `--rust`, ícone pulsante, protocolo grande em tabular
  - Cronômetro `MM:SS` desde o acionamento
  - Status ao vivo por WS: "Aguardando central" → "Central recebeu" → "Atendimento a caminho"
  - 4 botões de escalonamento; cada um vira ✓ verde inline após acionar
  - **Não sai sozinho** — só pelo botão "Voltar ao início"
- **Como validar:** acionar pânico, dar ACK no painel e ver o status mudar no totem

> **O status ao vivo é o que diferencia esta tela de um cartaz.** Sem ele a pessoa não tem
> como saber se o pedido chegou, e a única coisa que resta a fazer é tocar de novo. As três
> informações respondem três perguntas de quem espera: o protocolo — "o pedido existe?";
> o cronômetro — "há quanto tempo?"; o status — "alguém já viu?".
>
> Os textos são escritos do ponto de vista de **quem espera**, não do sistema: "Central
> recebeu" e não "reconhecido". E `falha_notificacao` mostra "Aguardando central", não
> "falhou" — a pessoa não pode fazer nada sobre isso, e a informação acionável é outra: os
> botões de escalonamento logo abaixo.
>
> **O cronômetro conta a partir de um `Date`, não somando 1 por segundo.** A diferença
> aparece quando o navegador estrangula o timer (aba em segundo plano, Android economizando
> bateria): um contador incremental ficaria atrasado — e este cronômetro diz há quanto
> tempo alguém está esperando socorro. O instante é capturado **antes** do POST: num webhook
> lento a diferença chega a segundos, e é o tempo de espera real que importa.
>
> **O WebSocket filtra por `chamado_id`.** Sem isso, outro totem acionando ao mesmo tempo
> mudaria o status desta tela. A reconexão tem espera crescente até 10 s: um totem em
> alerta com a conexão caída não pode tentar a cada 100 ms — aquece o aparelho e enche o log
> do servidor durante uma emergência — mas também não pode desistir. `onerror` não é
> tratado de propósito: o navegador sempre dispara `onclose` depois dele, e tratar os dois
> agendaria duas reconexões.
>
> O botão de escalonamento marca **antes** da resposta e **não volta** em caso de falha.
> Desmarcar sugeriria "não acionei", e a pessoa tentaria de novo — mas ela já ligou, que é
> o que o botão registra (MVP-034 grava o acionamento humano mesmo sem contato
> configurado). O painel mostra o resultado real.
>
> `semCromo` esconde o header: um wordmark clicável ali daria um jeito acidental de sair de
> um estado que é persistente de propósito. O foco é branco dentro da tela — o anel de
> ferrugem do `base.css` é invisível sobre fundo ferrugem.
>
> Com movimento reduzido o pulso para mas o **anel permanece**: ele é o que distingue esta
> tela de um cartaz estático.
>
> Removida a prop `persistente` que a MVP-052 havia acrescentado ao `Confirmacao` para
> cobrir o pânico provisoriamente: com a tela real existindo, ela ficou sem consumidor, e
> prop sem consumidor apodrece.

### MVP-055 — Layout fluido: tablet (duas orientações) e desktop
- **Descrição:** A tela do totem é um **Galaxy Tab A11 de 8.7" (1340×800)** e precisa
  funcionar em retrato e paisagem, sem deixar de funcionar no desktop. O caso difícil é a
  paisagem: sobram ~530px de **altura** para cabeçalho, título, 4 alvos e o pânico.
- **Prioridade:** P0 · **Depende de:** 050, 054 · **Status:** ⚠️ Parcial — layout
  implementado; **a medição no aparelho continua em aberto**
- **Arquivos:** `frontend/src/estilos/{base,totem}.css`, `docs/viewports.md`,
  `frontend/src/Galeria.tsx`, `frontend/src/App.tsx`
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

> **O primeiro critério não foi cumprido, e é o que mantém esta task parcial.** Ele pede
> medir `innerWidth/innerHeight` no Galaxy Tab A11 — *"não projetar contra número suposto"*
> — e eu não tenho acesso ao aparelho. O que existe é `docs/viewports.md` com a
> **derivação** (1340×800 ÷ DPR 1.5 → 893×533 em paisagem), marcada como não medida, e uma
> tabela esperando os valores reais.
>
> Para que a medição seja um passo e não um projeto, a rota `/galeria` passou a mostrar
> `innerWidth`, `innerHeight`, `devicePixelRatio`, a orientação e — o que de fato responde
> o critério — se `document.body.scrollHeight <= window.innerHeight`. Abrir a galeria no
> tablet e copiar cinco linhas fecha a task.
>
> **A incerteza é o DPR.** Se for 2.0 e não 1.5, a paisagem cai de 893×533 para 670×400, e
> aí nem a grade de 4 colunas com cartão de 120 px caberia. Por isso o ponto de quebra é
> `max-height: 620px`: ele cobre com folga os 533 derivados **e** os 400 do outro cenário —
> é o que faz o layout sobreviver ao número que ainda não medi.
>
> Os pontos de quebra são por **altura disponível**, não por nome de dispositivo: uma regra
> escrita contra "tablet" erra em qualquer aparelho que não seja aquele.
>
> **Alvos de toque nunca encolhem.** O cartão baixa de 168 px para 120 px em paisagem
> apertada — ainda quase o dobro do mínimo de 64 px — e o espaço vem do ícone (56 → 40 px)
> e do `padding`, nunca do alvo. O ícone é reduzido em CSS e não por prop porque o
> componente não deve saber em que orientação está.
>
> O colapso para uma coluna mudou de 560 px para **480 px**: entre os dois a grade 2×2
> ainda cabe num telefone em paisagem, e uma coluna ali desperdiçaria metade da tela.
>
> `.poto-painel` cancela o `overflow: hidden` do shell: a lista de chamados é longa e
> precisa rolar, inclusive se o painel for aberto no tablet.

### MVP-055b — Manifest e modo autônomo no tablet
- **Descrição:** Fazer o Chrome abrir a aplicação em tela cheia, sem barra de endereço.
- **Prioridade:** P0 · **Depende de:** 055 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/public/manifest.webmanifest`, `frontend/index.html`,
  `frontend/public/icones/poto-{192,512}.png`
- **Critérios de aceitação:**
  - `display: "fullscreen"`, `orientation: "any"` (o layout se adapta — não travar)
  - `theme_color: "#C0392B"`, `background_color: "#FBF9F6"`, ícones 192 e 512
  - "Adicionar à tela inicial" abre sem barra de endereço
  - `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`
- **Como validar:** adicionar à tela inicial no Tab A11 e abrir pelo ícone — manifest
  validado por campo; a instalação depende do aparelho

> **`display: fullscreen` esconde a barra de endereço**, que num totem de parede não é
> conveniência: é superfície para alguém navegar para fora da aplicação. `display_override`
> cai para `standalone` onde `fullscreen` não é suportado — sem ele o navegador voltaria
> direto para `browser`, com a barra.
>
> **`orientation: "any"` e não travado.** Travar em paisagem pareceria proteger o layout,
> mas o layout já se adapta (MVP-055) e travar criaria um estado pior: alguém segurando o
> tablet no eixo errado veria a tela de lado, e num pedido de socorro isso é atrito
> desnecessário.
>
> Os ícones PNG são **gerados por script** em vez de acrescentar uma biblioteca de imagem:
> o desenho é um círculo de ferrugem sobre papel, o mesmo ponto que o wordmark usa nos
> separadores. Sem texto — 192 px não comporta "P.O.T.O" em Michroma de forma legível, e um
> ícone com texto ilegível é pior que um símbolo. O círculo ocupa ~58% do lado para
> sobreviver ao recorte da máscara adaptativa do Android, que corta até ~20% da borda; daí
> também a entrada `purpose: "maskable"`.

### MVP-056 — Acessibilidade AA
- **Descrição:** Contraste, foco e semântica.
- **Prioridade:** P1 · **Depende de:** 055 · **Status:** ⚠️ Parcial — contraste e
  semântica verificados; **Lighthouse e navegação por teclado pendem de navegador**
- **Arquivos:** `frontend/src/componentes/{Choice,Panic}.tsx`,
  `frontend/src/totem/telas/Home.tsx`, `frontend/scripts/verificar-contraste.mjs`
- **Critérios de aceitação:**
  - Contraste AA em todos os pares de cor
  - `aria-label` nos 4 botões de trilha e no pânico
  - Foco visível em todos os interativos
  - **Cor nunca é o único sinal** — gravidade tem cor + rótulo + ícone
- **Como validar:** Lighthouse Accessibility ≥ 95 e navegação só por teclado — **não
  executados** (exigem navegador). `npm run check-contraste` cobre os 26 pares de cor, e a
  conformidade com Label in Name foi verificada por renderização

> **O contraste é calculado, não conferido pelo Lighthouse**, por duas razões. O Lighthouse
> só vê o que está renderizado na rota que abriu: a tela de alerta ativo, as três variantes
> do `<Confirm>` e o estado desabilitado do `<Choice>` não aparecem numa passada pela tela
> inicial. E ele dá uma **nota**, não uma lista do que está errado. São 26 pares declarados
> à mão, porque só quem conhece o design sabe o que é texto (4.5:1), texto grande (3:1) ou
> apenas borda — um script varrendo o CSS não distinguiria.
>
> **Ressalva honesta sobre um dos pares.** A borda `--line` sobre branco dá **1,28:1**, e
> eu declarei o mínimo dela como 1.1 — que não é um patamar da WCAG. A justificativa é que
> a 1.4.11 se aplica a limites que **comunicam estado**, e o contorno do cartão é
> decorativo: quem carrega o significado é o rótulo e o ícone, e hover e foco usam
> ferrugem (4,52:1 e 5,17:1). Se um dia a borda passar a indicar seleção, esse par vira uma
> falha de verdade.
>
> **`aria-label` que não contém o texto visível quebra o controle por voz.** A WCAG 2.5.3
> (Label in Name) exige a contenção, e é por isso que o formato é
> `"<rótulo visível> — <complemento>"` e não uma frase reescrita: dizer "Segurança" tem que
> acionar o botão "Segurança". Verificado por renderização nos cinco controles.
>
> O campo `descricao` de `trilhas.ts` existia desde a MVP-050 e não estava sendo usado —
> agora alimenta esses rótulos. A grade ganhou `role="group"` com nome, para o leitor de
> tela anunciar o contexto que o arranjo visual dá.
>
> Foco visível vem do `base.css` (`outline: 3px var(--rust)`), com variante branca dentro do
> alerta ativo — o anel de ferrugem é invisível sobre fundo ferrugem. E cor nunca é o único
> sinal: o `StatusPill` tem texto ao lado do ponto, e a gravidade tem cor, rótulo e ícone.

---

# Fase 7 — Operação offline

### MVP-057 — Fila offline em `localStorage`
- **Descrição:** O totem não pode parar porque a rede parou.
- **Prioridade:** P0 · **Depende de:** 048 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/comum/fila.ts`, `frontend/src/totem/Totem.tsx`,
  `frontend/src/totem/telas/AlertaAtivo.tsx`, `frontend/scripts/verificar-fila.mjs`
- **Critérios de aceitação:**
  - Falha de POST enfileira o evento **com o `evento_id` já gerado**
  - `enfileirar()`, `pendentes()`, `drenar()`
  - Confirmação **imediata** na tela — a pessoa não percebe diferença
  - `localStorage` cheio ou bloqueado não quebra a aplicação
- **Como validar:** desligar o backend, acionar 3 trilhas, conferir 3 itens na fila —
  `npm run check-fila`, **13 casos**

> **A peça que faz a fila funcionar está em outro arquivo.** O `evento_id` nasce no cliente
> antes do envio (MVP-048), e é por isso que um evento pode falhar, ficar guardado horas e
> ser reenviado carregando o mesmo id — o backend devolve o chamado que já existe em vez de
> criar um segundo alarme. Sem essa decisão, a fila **multiplicaria** chamados em vez de
> salvá-los.
>
> O evento é montado **antes** do `try`: montá-lo no `catch` geraria um id novo e quebraria
> exatamente essa garantia.
>
> **`ErroRede` enfileira; `ErroApi` não.** A distinção da MVP-048 ganha consequência aqui:
> um 422 significa que o envio chegou e foi recusado, e reenfileirar entraria em laço com
> um payload que vai falhar igual. Sem a distinção, a fila giraria para sempre.
>
> **Falha de rede não é falha do acionamento.** A confirmação aparece imediata e a pessoa
> não fica sabendo que o wi-fi caiu — ela não pode decidir o que fazer a respeito disso.
>
> **A `confirmacaoLocal` é a única vez em que o frontend decide o conteúdo de uma tela de
> confirmação**, e contradiz a regra do projeto de propósito: sem resposta do servidor não
> existe `instrucao_totem`. Duas salvaguardas contêm a contradição — **sem protocolo**
> (inventar um `CALL-` local seria pior que não ter: a pessoa anotaria um número que a
> central não reconhece) e **sem som**, com mensagem genérica, porque sem `tela_neutra` do
> servidor o cliente não sabe se o caso é discreto, e um beep na trilha errada é tão
> revelador quanto um protocolo na tela. A função nem recebe o evento, para não ter acesso
> a nada que possa vazar.
>
> Um pânico offline continua sendo um pânico: a tela de alerta ativo aparece igual, sem
> WebSocket (tentar reconectar em laço numa tela de pânico só aquece o aparelho) e com os
> quatro números para ligar. Os botões marcam localmente — é o uso real deles quando não há
> sistema do outro lado: dizer quais números já foram tentados.
>
> **O limite de 50 descarta o mais antigo, não o mais novo.** Entre um pedido de dez dias
> atrás e um de agora, o de agora é o que ainda pode ser atendido.
>
> Os três modos de falha de `localStorage` são testados, não presumidos: cota estourada,
> acesso bloqueado (navegação privada) e conteúdo corrompido — inclusive um item de formato
> antigo, que é descartado em vez de derrubar a tela ao montar.

### MVP-058 — Dreno automático e badge de fila
- **Descrição:** Reenvio ao voltar a conectividade.
- **Prioridade:** P0 · **Depende de:** 057 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/comum/{fila.ts,useFila.ts}`,
  `frontend/src/totem/Totem.tsx`, `frontend/scripts/fila.casos.ts`
- **Critérios de aceitação:**
  - Dreno no evento `online` e a cada 15 s
  - Badge "N na fila" visível no header
  - Item drenado com sucesso sai da fila; falha permanece
  - Dreno é serial (não dispara N requisições simultâneas)
- **Como validar:** religar o backend e ver a fila esvaziar sozinha —
  `npm run check-fila`, **22 casos** (13 da fila + 9 do dreno)

> **Os dois gatilhos são ambos necessários.** O evento `online` é imediato mas mente —
> `navigator.onLine` diz que a interface de rede subiu, não que o backend responde. O
> intervalo de 15 s cobre o caso em que `online` **nunca dispara** porque o wi-fi nunca
> caiu: o que caiu foi o servidor. Sem o intervalo, um totem conectado a um backend
> reiniciado ficaria com a fila parada para sempre; sem o `online`, o dreno esperaria até
> 15 s depois de a rede voltar — longo quando alguém está esperando socorro.
>
> **O dreno é serial, e não é preferência de estilo.** 50 itens em paralelo abrem 50
> conexões de um totem que acabou de recuperar uma rede instável, e a primeira coisa que
> acontece é a rede cair de novo. Em série, a primeira falha para o dreno ali mesmo — se um
> não passou, o próximo também não vai. Verificado por mutação: trocar por
> `Promise.allSettled` derruba 5 casos.
>
> **`ErroApi` descarta o item; `ErroRede` o mantém.** Um payload recusado pelo servidor
> falharia igual a cada tentativa e **travaria a fila para sempre**, bloqueando os pedidos
> atrás dele — que podem ser válidos. É a consequência mais importante da distinção de erro
> criada na MVP-048.
>
> O item sai da fila **depois** do sucesso, nunca antes: remover antes perderia o pedido se
> o envio falhasse no meio. E a fila é relida a cada volta em vez de iterar um instantâneo,
> porque um acionamento novo durante o dreno entra na fila e um instantâneo velho o
> ignoraria — há teste para isso.
>
> A trava `drenando` existe porque o timer e o evento `online` podem disparar juntos. O
> backend deduplicaria pelo `evento_id`, mas seriam duas requisições desnecessárias numa
> rede que acabou de voltar.
>
> `drenar()` recebe os enviadores por parâmetro em vez de importar `api.ts`: a fila não
> precisa conhecer o transporte, e a inversão é o que torna o dreno testável sem rede.
>
> O badge reconta **na hora** de enfileirar, não no próximo ciclo: ele tem que aparecer no
> mesmo quadro da confirmação.
>
> Nota: `INTERVALO_DRENO_SEG = 15` duplica `POTO_TOTEM_OFFLINE_SEG` do backend porque
> **offline não há `/config`** para consultar — e é justamente offline que o dreno importa.
> O `/config` continua sendo a fonte quando há rede; a constante é o piso.

### MVP-059 — Re-triagem protetiva no dreno
- **Descrição:** Fechar a versão offline do defeito de rebaixamento. No projeto antigo, conversa sem rede virava sempre `ouvidoria`.
- **Prioridade:** P0 · **Depende de:** 023, 058 · **Status:** ✅ Concluída
- **Arquivos:** `backend/tests/test_api_dreno.py`
- **Critérios de aceitação:**
  - Evento drenado com `texto_livre` passa por `merge_acionamento()` na chegada
  - Evento enfileirado como `ouvidoria` com texto grave é **promovido**
  - Idempotência preservada: re-envio do mesmo `evento_id` não duplica
- **Como validar:** enfileirar `{tipo: ouvidoria, texto: "socorro tem um homem me
  seguindo"}`, drenar, e verificar promoção — **verificado**, promove para
  `risco_imediato` e retipa como `mulher`. 19 testes

> **Os três critérios já eram satisfeitos, e isso foi verificado antes de escrever
> qualquer código.** `/eventos` chama `merge_acionamento()` desde a MVP-030, e o merge
> promove por sinal crítico independentemente da trilha — não havia caminho novo a criar.
> O entregável desta task é, portanto, **o teste**, não a implementação.
>
> Vale um arquivo próprio porque a regressão que ele guarda é diferente. Um evento drenado
> tem três propriedades que um evento ao vivo não tem, e cada uma já quebrou algum sistema:
> chega horas depois, chega possivelmente mais de uma vez (o dreno pode falhar no meio), e
> carrega um `timestamp_local` muito anterior ao `created_at`.
>
> O risco concreto é alguém otimizando o `/eventos` no futuro e achando seguro pular a
> triagem "quando o evento é antigo", ou confiar no `timestamp_local` para rotear.
> Verificado por mutação que os testes pegam exatamente isso: o atalho
> *"evento antigo não precisa de triagem"* derruba 5 testes, e remover o merge derruba 8.
> Um evento velho **não** é menos grave — é mais, porque ninguém apareceu nesse tempo.
>
> **Lacuna documentada por teste, não escondida:** o backend não distingue um evento
> drenado de um ao vivo. O payload é byte a byte o mesmo — é isso que preserva a
> idempotência — então `origem_acionamento` vem `touch` nos dois casos. Não é falha de
> segurança (responder a uma emergência de sete horas atrás continua sendo a ação certa,
> porque ninguém sabe se a pessoa está bem); é falta de **contexto** para o operador. O
> sinal existe e é indireto: `created_at − timestamp_local`. `test_backend_nao_distingue_
> evento_drenado_de_ao_vivo` registra a lacuna para quem construir o painel na Fase 8.

---

# Fase 8 — Painel da central

### MVP-060 — Shell e lista do painel
- **Descrição:** Visão operacional dos chamados.
- **Prioridade:** P0 · **Depende de:** 032, 042 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/painel/{Painel,ListaChamados}.tsx`,
  `frontend/src/painel/{rotulos,ordenacao}.ts`, `frontend/src/estilos/painel.css`
- **Critérios de aceitação:**
  - Rota `/painel` no mesmo build
  - Carrega `GET /chamados` no mount
  - Mais recentes primeiro; críticos no topo
  - Estado vazio com mensagem clara
- **Como validar:** `make seed` e abrir `/painel` — ordenação verificada:
  `CRITICO-2min > crit-encerrado > potencial > ouv-recente > ouv-1min`

> **"Mais recentes primeiro; críticos no topo" são duas regras em conflito, e a ordem
> entre elas é a decisão.** Gravidade vence; entre iguais, o mais recente. É o que resolve
> o caso que uma lista cronológica erra: um risco imediato de dois minutos atrás empurrado
> para baixo por três dúvidas de ouvidoria que chegaram depois. Há um terceiro critério que
> o plano não pede — **aberto antes de resolvido** — porque um encerrado no topo ocupa o
> lugar de algo que ainda espera alguém.
>
> A lista é **estado local atualizado por WebSocket** (MVP-062), não recarregada em laço.
> Um `setInterval` buscando `/chamados` a cada 5 s custaria tráfego constante e ainda
> chegaria até 5 s atrasado — e o requisito é "acende em menos de 1 s". O `GET /chamados`
> acontece uma vez, no mount, como ponto de partida.
>
> `aplicar()` insere ou substitui **no lugar**, indexando por `chamado_id`: sem isso um
> `atualizado` faria a lista piscar inteira e perderia a posição de rolagem de quem está
> lendo.
>
> O erro de carga distingue `ErroApi` de falha genérica, porque a causa mais provável de um
> 401 aqui é o token do painel — e "não foi possível carregar" mandaria o operador procurar
> no lugar errado.
>
> O painel **religa a seleção de texto** que o `base.css` desliga para o kiosk: aqui se
> copia protocolo. E o `.poto-painel` cancela o `overflow: hidden` do shell do totem.
>
> `ordenar` fica em arquivo próprio: importá-la de `ListaChamados` arrastaria
> `CardChamado` → `api.ts` → `import.meta.env`, que não existe no Node e tornaria a função
> impossível de testar fora do navegador. O cartão nasce aqui como esqueleto — a leitura em
> um relance é a MVP-061, as ações a MVP-063 e o SLA a MVP-064.

### MVP-061 — Card de chamado com gravidade
- **Descrição:** O cartão que o operador lê em um relance.
- **Prioridade:** P0 · **Depende de:** 060 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/painel/CardChamado.tsx`, `frontend/src/estilos/painel.css`
- **Critérios de aceitação:**
  - **Borda esquerda de 5px** na cor da gravidade: `--crit` · `--warn` · `--info`
  - Protocolo em tabular, tipo, canal roteado, horário, totem
  - Chip de status legível
  - Gravidade tem cor **+ rótulo** (nunca só cor)
- **Como validar:** conferir contra `../poto-pitch/capturas-de-tela/Tela-Central-painel.png`

> **A borda de 5px é o que permite varrer vinte cartões sem ler nenhum** — e é justamente
> por ser tão eficiente que ela não pode vir sozinha. O chip ao lado diz "Imediato",
> "Potencial" ou "Orientação". Cor como único sinal excluiria os ~8% dos homens com alguma
> deficiência na percepção de vermelho e verde, num painel de emergência.
>
> **A lacuna que a MVP-059 documentou está resolvida aqui.** Um evento que ficou na fila
> offline chega com payload **idêntico** a um ao vivo — é isso que preserva a idempotência
> — e o único sinal disponível é a distância entre `timestamp_local` (relógio do tablet) e
> `created_at` (relógio do servidor). Sem a marca "esperou N h na fila", o operador trata um
> pedido de horas atrás como se estivesse acontecendo agora.
>
> O aviso só aparece **acima de 2 minutos**: abaixo disso a diferença é relógio
> dessincronizado, não fila. Marcar tudo transformaria o aviso em ruído, e um aviso que
> aparece sempre não é lido. E ele usa `--warn`, não `--crit`: o chamado não é mais grave,
> é mais antigo — a cor de crítico competiria com a borda de gravidade, que é o sinal
> principal.
>
> O `timestamp_local` continua sendo tratado como não confiável: serve de **indício
> visual** e nunca para rotear nem para o SLA. `Date.parse` inválido devolve `null` em vez
> de derrubar o cartão.
>
> O relato vai em itálico e entre aspas porque é a **voz de quem pediu ajuda**, não texto
> do sistema — a distinção importa quando se lê rápido.
>
> A hora é formatada no cliente: `created_at` vem em UTC e o navegador converte para o
> fuso de quem olha. É por isso que o backend não formata data — ele não sabe onde o painel
> está.

### MVP-062 — WebSocket em tempo real
- **Descrição:** O painel acende sozinho, sem recarregar.
- **Prioridade:** P0 · **Depende de:** 035, 060 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/comum/ws.ts`,
  `frontend/src/painel/{IndicadorTempoReal.tsx,Painel.tsx}`
- **Critérios de aceitação:**
  - `novo_chamado` insere o card no topo em **< 1 s**
  - `atualizado` atualiza o card no lugar, sem piscar a lista
  - Reconexão automática com backoff
  - Indicador de conexão do WS visível
- **Como validar:** totem e painel em duas abas; acionar e cronometrar — **medido:
  553,9 ms** do `POST /eventos` até o `novo_chamado` chegar ao painel (inclui triagem com
  carga do classificador, escrita no banco e broadcast)

> **A conexão em si já existia.** O `useEventosWS` foi escrito na MVP-054 para o totem
> acompanhar o próprio alerta, com reconexão de espera crescente; o painel o reusa sem
> mudança. O que faltava era a **legenda**.
>
> E a legenda não é o `StatusPill` do totem. A pergunta ali é *"o que eu tocar chega
> agora?"*; aqui é *"o que está na tela é ao vivo?"*. Num painel onde nada acontece por
> vinte minutos, **silêncio e conexão morta parecem idênticos na tela e significam o
> oposto** — o operador acharia que a noite está calma.
>
> **`atualizado` atualiza no lugar porque o formato do WS é o mesmo do REST.** Isso foi
> garantido na MVP-033, quando os cinco pontos de broadcast passaram a usar
> `models.para_painel()`. Verificado de ponta a ponta: o conjunto de campos do payload do
> WebSocket é idêntico ao de `GET /chamados`. Sem essa unificação, este handler precisaria
> de um segundo formato de `Chamado` e o tipo declarado mentiria sobre um dos dois.
>
> `conectado` e `ping` não mexem na lista — o primeiro é boas-vindas, o segundo keepalive.
> O estado da conexão vem do retorno do hook, não de contar pings.
>
> O pulso do ponto é **o único movimento do painel**, de propósito: uma tela de trabalho
> lida por horas não pode ter animação competindo com o conteúdo. Com movimento reduzido o
> pulso para mas o ponto permanece — ele carrega a cor, que é metade do sinal; o rótulo ao
> lado carrega a outra.

### MVP-063 — ACK e mudança de estado
- **Descrição:** Ações do operador.
- **Prioridade:** P0 · **Depende de:** 033, 061 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/painel/CardChamado.tsx`, `frontend/src/comum/api.ts`,
  `frontend/src/estilos/painel.css`
- **Critérios de aceitação:**
  - Botão "Reconhecer" chama `/ack` e some após sucesso
  - Seletor de estado: `em_atendimento`, `encerrado`
  - Mudança reflete no totem via WS (visível no alerta ativo)
  - Botão desabilitado durante a requisição
- **Como validar:** dar ACK e ver o totem mudar para "A central recebeu seu alerta" —
  **verificado de ponta a ponta:** pânico em `alerta_ativo` → ACK no painel →
  `atualizado` no WS → `reconhecido` → a tela do totem passa a mostrar "Central recebeu";
  e o `PATCH` para `em_atendimento` chega como "Atendimento a caminho"

> **O botão some porque a condição que o traz desaparece**, não porque guardamos "já
> cliquei": `acked_at` deixa de ser nulo e o cartão re-renderiza. Não há estado local de
> clique a manter em sincronia — o dado é a fonte, e é isso que faz o botão sumir também
> quando **outro operador** reconhece, via WebSocket.
>
> `reconhecido` **não** está no seletor de estados, e a omissão é deliberada: ele vem do
> botão "Reconhecer", que grava também o `acked_at` de onde sai a métrica de tempo até o
> reconhecimento. Oferecê-lo no seletor daria dois caminhos para a mesma transição, e um
> deles **não pararia o relógio do SLA**. `cancelado` também fica fora: marcar um pedido de
> socorro como trote merece mais atrito que um item de lista suspensa.
>
> O seletor tem `value=""` fixo em vez de espelhar o status: ele é um **disparador de
> ação**, não um espelho do estado. Mostrar o estado atual ali convidaria o operador a
> "voltar" mudando a seleção, e o rodapé já diz em que estado o chamado está.
>
> A trava acontece **antes de qualquer `await`**. Dois cliques rápidos no "Reconhecer"
> mandariam dois POST; o segundo é inofensivo (o backend preserva o `acked_at` original —
> MVP-033), mas o cartão piscaria duas vezes, e num painel de vinte cartões isso é o
> operador perdendo o lugar.
>
> Falha silenciosa é escolha: se a ação chegou, o WebSocket corrige o estado sozinho; se
> não chegou, o operador tenta de novo. Um alerta de erro seria uma caixa para fechar no
> meio de uma emergência.
>
> Alvos de 40px e não os 64px do totem: o painel é operado com mouse, e 64px
> desperdiçariam altura numa lista longa. Continua acima do mínimo de 24px da WCAG 2.5.8.

### MVP-064 — Contador de SLA ao vivo
- **Descrição:** O prazo correndo na tela — o fail-safe visível.
- **Prioridade:** P0 · **Depende de:** 037, 061 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/painel/{ContadorSLA,CardChamado}.tsx`,
  `frontend/src/estilos/painel.css`
- **Critérios de aceitação:**
  - "Responder em M:SS" regressivo, atualizando a cada segundo
  - Prazos vindos de `GET /config` — **não hardcoded**
  - Ao estourar, faixa "SLA expirado"
  - Sem contador em `orientacao`
- **Como validar:** criar chamado crítico e observar até estourar os 120 s — verificado
  com os prazos reais do `/config`: `1:54` em 5 s de vida, `0:10` em 110 s, faixa
  "SLA expirado" em 121 s; e `7:59` para um `risco_potencial` de 121 s

> **É o fail-safe visível.** O worker escalona sozinho quando o prazo estoura (MVP-038),
> mas se o operador só descobre depois, o escalonamento automático deixa de ser rede de
> segurança e passa a ser o caminho normal — e o fallback é sempre uma escolha pior que a
> resposta de quem estava de plantão.
>
> **Os prazos vêm de `GET /config`, e a razão é concreta:** escrevê-los aqui faria mudar
> 120 para 90 no backend deixar a tela mostrando o prazo antigo, e o cartão diria "faltam
> 30 s" para um chamado que o worker já escalonou. Verificado que nenhum prazo de SLA está
> escrito à mão no painel.
>
> **Conta a partir de `created_at`, o relógio do servidor** — o mesmo que o worker usa.
> Usar `timestamp_local` faria a tela e o worker discordarem sobre quando o prazo venceu, e
> a discordância apareceria como "SLA expirado" num cartão que o backend ainda considera no
> prazo.
>
> Relê `Date.now()` em vez de decrementar um contador: com a aba em segundo plano o
> navegador estrangula o `setInterval`, e um decremento ficaria atrasado — mostrando tempo
> que já passou. É a mesma decisão do cronômetro do alerta ativo (MVP-054).
>
> Duas condições para aparecer, e as duas importam: `aberto`, porque um chamado encerrado
> não tem prazo a correr; e `slaSegundos !== null`, porque `orientacao` não escalona e um
> contador ali sugeriria urgência que não existe. O `null` do `/config` é **informação** —
> diz que aquele nível não tem prazo — e não ausência de dado.
>
> O "SLA expirado" é faixa cheia e não texto solto: é a informação que não pode passar
> batida numa lista de vinte cartões.

### MVP-065 — Filtros e busca
- **Descrição:** Encontrar um chamado entre muitos.
- **Prioridade:** P1 · **Depende de:** 060 · **Status:** ✅ Concluída
- **Arquivos:** `frontend/src/painel/{filtros.ts,BarraFiltros.tsx,Painel.tsx}`,
  `frontend/src/estilos/painel.css`
- **Critérios de aceitação:**
  - Filtros por gravidade e status, com contadores
  - Busca por protocolo ou totem
  - Filtros combináveis; botão de limpar
- **Como validar:** com 20 chamados semeados, filtrar e conferir — verificado: filtro
  simples, combinação dos três, busca por protocolo, por totem, **sem acento** e no relato

> **Filtra no cliente, não no endpoint** — e o `GET /chamados` aceita filtros (MVP-032).
> Usá-los aqui seria errado por dois motivos que se somam: o WebSocket entrega chamados
> novos **sem passar pelo endpoint**, então um filtro de servidor os excluiria e o painel
> mostraria um recorte congelado no momento da última busca; e filtrar 200 objetos em
> memória é instantâneo, enquanto uma ida ao servidor por tecla digitada seria uma
> requisição por caractere. Os filtros do endpoint seguem úteis para quem consome a API de
> fora.
>
> **O recorte por situação não é o `StatusChamado` cru.** O operador pensa em "precisam de
> mim" e "já resolvidos", não nos dez estados da máquina — oferecer os dez faria ele
> escolher entre `notificado` e `escalonado` sem saber a diferença.
>
> **A busca normaliza acento.** Sem isso, procurar "seguranca" não acharia "Segurança", e
> ninguém digita cedilha com pressa. `NFD` separa o acento do caractere e o range
> `\u0300-\u036f` remove as marcas combinantes.
>
> A busca cobre o **relato**, que o critério não pede. É o caso de quem liga para a central
> dizendo "é sobre a moça que falou do estacionamento": procurar por "estacionamento" é o
> único caminho, porque o operador não tem o protocolo.
>
> **Os contadores contam a lista inteira, não a filtrada.** Eles dizem quanto existe de
> cada tipo, e é por eles que o operador decide para onde ir — contar o que já está
> filtrado mostraria zero em tudo que não é o filtro ativo.
>
> O chip ativo muda o **fundo**, não só a borda: numa barra de quatro chips a diferença de
> borda passa batida, e `aria-pressed` diz ao leitor de tela qual recorte está aplicado. E
> "Limpar filtros" só aparece quando há o que limpar — um botão sempre presente e sempre
> inerte ensina o operador a ignorá-lo.

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
- **Prioridade:** P0 · **Depende de:** 026, 055, 060 · **Status:** ✅ Concluída
- **Arquivos:** `Makefile`
- **Critérios de aceitação:**
  - `make build` gera `frontend/dist/` **com `index.html`, CSS, JS e fontes**
  - `GET /` → **200** com a aplicação (não 404, não JSON)
  - `GET /painel` → 200
  - Fontes carregam de `/fonts/`
  - Funciona **sem** o servidor de desenvolvimento do Vite
  - uvicorn em `--host 0.0.0.0`: **acessível de outro dispositivo da rede**, não só de `localhost`
  - O backend serve `dist/` **venha ele de onde vier** — build local ou artefato copiado
- **Como validar:** `make build && make serve`, depois `curl` pelo IP da rede — **feito**,
  sem servidor do Vite:
  `/` 200 html · `/painel` 200 · `/painel/` 200 · `/rota-inventada` 200 (fallback de SPA) ·
  `/api/v1/health` 200 json · `/fonts/michroma-latin.woff2` 200 font/woff2 ·
  `/manifest.webmanifest` 200 · `/icones/poto-192.png` 200 · `/api/v1/nao-existe` **404 json**

> **`make serve` existe para ser o mesmo comando que a unit systemd executa** (MVP-067).
> Dois comandos diferentes divergiriam, e a divergência apareceria só na Pi. Duas
> diferenças em relação a `make backend`, e as duas importam:
>
> - **`--host 0.0.0.0`** — sem isto o uvicorn escuta só em `127.0.0.1` e o tablet não
>   alcança. O sintoma é "funciona na Pi, não funciona no tablet", que custa meia hora até
>   alguém suspeitar do bind.
> - **sem `--reload`** — o observador de arquivos gasta CPU e memória vigiando uma árvore
>   que não muda, e um toque acidental no código reiniciaria o serviço no meio de um
>   atendimento.
>
> O último critério — *"serve `dist/` venha ele de onde vier"* — foi testado copiando o
> `dist/` para fora da árvore do projeto e subindo com `POTO_FRONTEND_DIST` apontando para
> lá, que é exatamente o estado da Pi depois de um rsync. Serve igual, e o `/health` avisa o
> que falta (naquele momento, o build-id — que a MVP-066b gera).
>
> Nota de ambiente: a verificação foi feita pelo **IP de rede desta máquina**, não por
> `localhost`. Um bind restrito a `127.0.0.1` recusaria a conexão, então o teste prova o
> `0.0.0.0`. O `curl` literalmente *de outra máquina* não foi possível: este ambiente
> bloqueia TCP de saída fora da 443 — o mesmo motivo pelo qual a Pi está inalcançável por
> SSH agora.

> **A Pi não compila o frontend.** Verificado no smoke test: o toolchain do Vite 8 é Rust
> compilado por arquitetura (`@rolldown/binding-linux-x64`, `lightningcss-linux-x64`,
> `@oxlint/binding-linux-x64`). Construir na Pi usaria binários `arm64` **diferentes** dos
> testados aqui — mesma fonte, ferramentas distintas. Construindo num lugar só, o artefato
> que roda é literalmente o que foi testado.
>
> A assimetria também pesa: **133 MB e 700 arquivos de ferramenta para produzir 220 KB e 2
> arquivos de resultado**. A Pi serve os 220 KB; nunca precisa saber que TypeScript existe.
>
> Consequência: `make deploy` (MVP-069b) constrói aqui e envia por rsync. Node não é
> instalado na Pi.

### MVP-066b — `make deploy` e build-id verificável
- **Descrição:** Um comando só que constrói e envia, mais um jeito de confirmar qual build está no ar.
- **Prioridade:** P0 · **Depende de:** 066 · **Status:** ✅ Concluída
- **Arquivos:** `Makefile`, `frontend/scripts/gravar-build-id.mjs`,
  `frontend/package.json`
- **Critérios de aceitação:**
  - `make deploy` executa **build e rsync na mesma ação** — não existe enviar sem reconstruir
  - Exclui `.venv/`, `node_modules/`, `__pycache__/`, `*.db` do envio
  - O build grava um identificador (hash do bundle) que o `/health` expõe, **dentro de
    `frontend/dist/`** — corrigido na MVP-036: o deploy envia `dist/` por rsync, e um
    build-id fora dessa pasta não viajaria com o artefato, permitindo um `dist/` velho
    servindo com build-id novo. O lado da leitura já está pronto
    (`sistema.ARQUIVO_BUILD_ID`)
  - Comparar o build-id local com o do `/health` da Pi diz se o artefato está atualizado
- **Como validar:** alterar uma string na tela, `make deploy`, e conferir que o build-id do
  `/health` da Pi mudou — o `make build-id` faz a comparação. **Os quatro estados foram
  testados** contra backends locais servindo `dist/` preparados:
  Pi inalcançável · responde sem build-id · artefato antigo · mesmo artefato

> **O build-id é hash do conteúdo do `dist/`, não a data nem o commit.** A diferença
> importa: data mudaria a cada build mesmo sem alteração nenhuma, e um identificador que
> sempre muda não distingue nada; o hash do commit não veria alterações **não commitadas**,
> que é exatamente o estado de quem está testando algo na Pi. Verificado determinístico
> (mesmo `dist/` → mesmo id) e sensível (um byte muda o id).
>
> O **nome** do arquivo entra no hash junto com o conteúdo. Sem ele, renomear sem mudar
> bytes daria o mesmo id — e o Vite nomeia os bundles por hash de conteúdo, então o nome
> carrega informação.
>
> **O `make build-id` distingue quatro estados, e não três.** A primeira versão dizia
> "artefatos DIFERENTES, rode make deploy" quando a Pi simplesmente **não respondia** — um
> diagnóstico que manda procurar no lugar errado, que é o defeito que este projeto vem
> corrigindo desde o `/health`. Agora: sem resposta diz que é falta de alcance e sugere
> rede e `systemctl`; responder sem build-id diz que o artefato chegou por outro caminho,
> sem passar pelo deploy.
>
> **`deploy: build`** — a dependência é o ponto inteiro da task: não existe enviar sem
> reconstruir. Verificado por dry-run: 172 itens, **2,3 MB**, nenhum item excluído
> escapando (`node_modules`, `.venv`, `__pycache__`, `*.pyc`, `*.db`, `.env`, `.git`), e o
> `dist/build-id` viajando junto com o artefato.
>
> `.env` fica de fora de propósito: ele tem os contatos institucionais e o token do painel,
> e cada ambiente tem o seu. Sobrescrever o da Pi com o da máquina de desenvolvimento
> apontaria a produção para os números de teste.
- **Por que existe:** é a mitigação do único risco real de separar build e execução — **artefato velho**.
  Alterar o código, esquecer de reconstruir e enviar a versão antiga é um bug silencioso que
  custa uma hora de depuração. Amarrando build e envio num comando, não dá para esquecer.

### MVP-067 — Unit systemd na Pi
- **Descrição:** Um único serviço que sobe sozinho no boot. Sem unit de kiosk (o navegador
  roda no tablet) e sem unit de GPIO (o pânico é virtual). A Pi opera **headless**.
- **Prioridade:** P0 · **Depende de:** 066 · **Status:** ⚠️ Parcial — unit escrita e
  validada; **o teste após reboot exige a Pi**
- **Arquivos:** `deploy/poto-api.service`
- **Critérios de aceitação:**
  - uvicorn **sem `--reload`**, `--host 0.0.0.0` (o tablet precisa alcançar)
  - `Restart=always`, `RestartSec=3`, `EnvironmentFile`, `After=network-online.target`
  - Funciona com a Pi sem monitor, teclado ou periférico conectado
  - `journalctl -u poto-api` mostra os logs da aplicação
- **Como validar:** `systemctl status poto-api` após reboot, com a Pi headless — **não
  executado**: a Pi está inalcançável deste ambiente (ver nota). A unit foi validada com
  `systemd-analyze verify` e as nove chaves críticas conferidas por script

> **O `systemd-analyze verify` pegou um bug real.** Eu havia posto
> `StartLimitIntervalSec` e `StartLimitBurst` em `[Service]`, e ali elas são
> **silenciosamente ignoradas** — pertencem a `[Unit]`. O teto de reinícios não existiria,
> e uma falha permanente (banco corrompido, porta ocupada) viraria laço infinito
> consumindo CPU e enchendo o journal. O sintoma seria "a Pi está lenta", não "o serviço
> está quebrado", o que manda a investigação para o lugar errado.
>
> **`After=network-online.target`, não `network.target`.** O segundo significa "a pilha de
> rede subiu"; o primeiro, "há endereço configurado". Com o `network.target`, o uvicorn
> pode tentar o bind em `0.0.0.0` antes de a interface ter IP e falhar — o `Restart=always`
> cobriria, mas o serviço nasceria com um ciclo de falha e a indisponibilidade apareceria
> justo no boot, que é quando ninguém está olhando.
>
> **`Restart=always` e não `on-failure`.** Um `systemctl stop` continua parando (o systemd
> distingue parada manual de saída do processo), mas qualquer outra saída — inclusive
> código 0 por um caminho inesperado — reergue. Um totem de emergência não pode ficar fora
> do ar porque o processo decidiu terminar.
>
> **O `ExecStart` é o mesmo comando de `make serve`**, e isso é deliberado: dois comandos
> diferentes divergiriam, e a divergência apareceria só na Pi.
>
> `EnvironmentFile` com `-` prefixado: o serviço sobe mesmo sem o `.env`. Degradado — e o
> `/health` diz exatamente o que falta (MVP-036). Um totem que se recusa a subir por falta
> de arquivo de configuração é pior que um que sobe avisando.
>
> O endurecimento é **modesto de propósito**. O serviço precisa escrever o banco, ler o
> `dist/` e — na Fase 8b — acessar a câmera CSI e o ALSA. Um sandbox agressivo quebraria a
> mídia de um jeito difícil de diagnosticar, e este é um totem numa rede local, não um
> servidor exposto.

### MVP-067b — Endereçamento estável da Pi
- **Descrição:** O tablet abre uma URL fixa; ela não pode mudar a cada reboot.
- **Prioridade:** P0 · **Depende de:** 067 · **Status:** ⚠️ Parcial — script escrito e
  executado; **o teste do tablet exige a Pi**
- **Arquivos:** `deploy/install-pi.sh`
- **Critérios de aceitação:**
  - `avahi-daemon` instalado e ativo; `<hostname>.local` resolve — **ver a correção
    abaixo: o hostname não é trocado para `poto`**
  - IP estático documentado como plano B (reserva DHCP ou `dhcpcd.conf`)
  - O script imprime **as duas** URLs ao final
  - `curl http://poto.local:8000/api/v1/health` responde de outro dispositivo da rede
- **Como validar:** do tablet, abrir `http://<hostname>.local:8000` — **não executado**
  (Pi inalcançável deste ambiente). O script foi **rodado aqui** de ponta a ponta: detectou
  o avahi ativo, resolveu o `.local`, leu IP, MAC e gateway reais, e a saída é **idêntica
  em duas execuções seguidas** (idempotente)

> **Correção ao plano: o script não troca o hostname para `poto`.** A Pi deste projeto se
> chama `RaspPoto`, e é assim que ela aparece em `docs/conexao-ssh.md` e na memória de quem
> usa. Renomear silenciosamente quebraria o acesso SSH documentado e faria a próxima
> conexão falhar sem explicação. O script trabalha com o hostname que existe e documenta o
> comando para trocar de propósito — junto do lembrete de atualizar o doc e o `PI_HOST` do
> Makefile.
>
> **As duas URLs são impressas, e o critério insiste nisso por um bom motivo.** O mDNS
> falha em dois casos reais: rede que bloqueia multicast — comum em wifi
> corporativo/universitário, que é exatamente o caso da UFPI — e cliente sem suporte.
> Imprimir só a `.local` deixaria a pessoa sem saída no momento em que ela falhasse.
>
> O plano B é **IP estável**, não "o IP atual". Um IP por DHCP muda quando o roteador
> reinicia, e aí o atalho do tablet aponta para nada. O script monta os dois caminhos com
> os valores reais lidos da máquina — reserva no roteador (preferida, porque não muda nada
> na Pi) e `nmcli` com o MAC e o gateway já preenchidos.
>
> `systemctl enable --now` é idempotente por natureza: em serviço já ativo, não faz nada. O
> `avahi-resolve` que falha é **aviso, não erro** — o daemon leva alguns segundos para
> anunciar, e o plano B continua valendo.

### MVP-067c — Kiosk no Galaxy Tab A11
- **Descrição:** Travar o tablet na aplicação, sem barra de endereço e sem sair por acidente.
- **Prioridade:** P0 · **Depende de:** 055b, 067b · **Status:** ✅ Concluída
- **Arquivos:** `docs/setup-tablet.md`
- **Critérios de aceitação — documentados passo a passo:**
  - Aplicação adicionada à tela inicial, abrindo em tela cheia
  - **Fixação de tela** (Configurações → Segurança) ativa, com PIN para sair
  - Tempo de tela desligada = **nunca**; brilho fixo
  - Notificações silenciadas; assistente de voz e gestos de navegação desativados
  - Reiniciar o tablet e retomar a aplicação em ≤ 5 toques documentados
- **Como validar:** entregar o tablet a alguém e confirmar que não consegue sair da
  aplicação sem o PIN — o documento termina com essa conferência e uma lista de 8 itens

> **O objetivo não é "abrir a aplicação".** É deixar o tablet num estado em que alguém que
> não conhece o projeto não consiga sair dela por acidente, e em que ele volte sozinho ao
> totem depois de um reinício.
>
> **O passo que de fato tranca é "Solicitar PIN para liberar".** Sem ele a fixação de tela
> é decoração: desafixar passa a ser um toque longo, e qualquer pessoa sai. O documento
> marca esse item explicitamente porque é o único cuja omissão invalida todos os outros.
>
> **A fixação não sobrevive ao reboot** — limitação do Android, não do projeto. É por isso
> que a retomada são **5 toques** e não 3: dois deles existem só para refixar. O documento
> diz isso em vez de esconder, e registra que um app de kiosk dedicado seria a saída se o
> totem for reiniciado com frequência.
>
> "Tempo de tela = nunca" não existe no One UI; o máximo é 10 minutos. O caminho real é
> **Permanecer ativo** nas Opções do desenvolvedor, que mantém a tela acesa *enquanto
> carregando* — o que casa com um aparelho de parede permanentemente no carregador.
>
> **Brilho adaptativo desligado**, e não só fixo: o automático escurece a tela num corredor
> à noite, que é exatamente quando ela mais precisa ser vista.
>
> **Rotação automática fica ligada**, contra o instinto de travar. O layout se adapta às
> duas orientações (MVP-055), e travar criaria um estado pior — alguém segurando o tablet
> no eixo errado veria a tela de lado, que num pedido de socorro é atrito desnecessário.
>
> A conferência final tem dois itens que não são de configuração e são os que provam a
> premissa do projeto: desligar o wifi e acionar uma trilha (confirma na hora, `· 1 na
> fila`), e religar (a fila esvazia sozinha em ≤ 15 s). São os mesmos dois que a
> demonstração mostra.

### ~~MVP-068 — Daemon do botão GPIO~~ → movida para P2
- **Motivo:** o pânico no MVP é **virtual, na interface web** (MVP-046 e MVP-054). O botão
  físico sai do escopo.
- **O que fica preparado:** `POST /panico` é agnóstico de origem e o enum
  `OrigemAcionamento` já tem `botao_fisico`. O daemon entra depois como processo separado
  (`hardware/gpio_panico.py` + uma unit systemd) **sem tocar no backend**.
- **Status:** Fora do MVP

### MVP-069 — `install-pi.sh`
- **Descrição:** Script idempotente que transforma uma Pi limpa num totem.
- **Prioridade:** P0 · **Depende de:** 067b · **Status:** ⚠️ Parcial — script completo e
  verificado; **a execução numa Pi limpa não foi feita**
- **Arquivos:** `deploy/install-pi.sh`
- **Critérios de aceitação:**
  - Instala `uv`, `avahi-daemon` e `python3-picamera2` (apt) — **não instala Node**
  - Cria o venv com `--system-site-packages` apontando para `/usr/bin/python3`, para o
    `picamera2` do apt ser visível, e roda `uv sync --extra midia`
  - Treina o classificador (`make train-clf`) — o artefato não é versionado
  - Copia a unit `poto-api.service` e faz `systemctl enable --now`
  - Cria `.env` a partir do exemplo se não existir
  - **Imprime ao final as URLs** (`http://poto.local:8000` e `http://<ip>:8000`) para apontar o tablet
  - **Idempotente**: rodar duas vezes não quebra nada
- **Como validar:** executar 2× numa Pi limpa e, do tablet, abrir a URL impressa — **não
  executado** (Pi inalcançável deste ambiente). Verificado: `bash -n` limpo, os **13
  critérios** conferidos por script, e a unit resultante da substituição de caminhos passa
  pelo `systemd-analyze verify` sem nenhuma reclamação

> **A unit é ajustada, não copiada.** Seus caminhos assumem `raspoto` e `~/poto-mvp`; o
> script substitui usuário, grupo, diretório e o caminho do `uv` pelos **reais**. Um
> instalador que só funciona num nome de usuário específico falha em silêncio no primeiro
> que não for — e o sintoma seria `systemctl status` dizendo "não encontrado" sobre um
> caminho que ninguém digitou. Testado aqui: a unit resultante (com `User=kz`, a raiz deste
> repositório e o `uv` real) passa pelo `systemd-analyze verify` sem avisos.
>
> **`systemctl restart` e não só `enable --now`.** Na segunda execução o serviço já está
> ativo **com o código antigo**, e `enable --now` não o reinicia — o instalador terminaria
> dizendo "ativo" sobre a versão anterior. É a forma mais fácil de um instalador idempotente
> mentir.
>
> **A conferência final pergunta ao `/health`, não ao `systemctl`.** Um serviço "ativo" com
> o banco inacessível ou o classificador ausente está de pé **e degradado**, e é exatamente
> isso que o `/health` foi feito para contar (MVP-036). O script imprime banco, modo de
> triagem, provider, estado do frontend com build-id, e a lista de avisos.
>
> Idempotência item por item, não no conjunto: pacotes conferidos com `dpkg -s` antes de
> instalar, venv só criado se ausente, `.env` **preservado** se existir (sobrescrevê-lo
> apagaria os contatos institucionais), classificador só treinado se o artefato faltar.
>
> `python3-picamera2` vem do **apt** e não do pip porque depende de `python3-libcamera`, um
> binding C++ compilado que não existe no PyPI — daí também o
> `--python /usr/bin/python3` no venv: o picamera2 do apt está instalado para o Python do
> sistema, e um Python baixado pelo uv não o enxergaria nem com
> `--system-site-packages`.

> **Node saiu da lista.** O frontend é construído na máquina de desenvolvimento e enviado
> pronto (MVP-066b). Isso poupa **133 MB e 700 arquivos** na Pi, elimina uma toolchain que
> precisaria de atualização e manutenção, e dispensa internet no momento do deploy — o rsync
> vai pela LAN.
>
> **Medido no smoke test de 16/09:** `uv sync --extra dev` levou **7,7 s** em aarch64, com
> wheels prontos e nas mesmas versões do PC de desenvolvimento (scikit-learn 1.9.1,
> scipy 1.18.1, numpy 2.5.3). O risco de compilar scipy por horas na Pi não existe.

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
