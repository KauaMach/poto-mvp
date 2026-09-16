<h1 align="center">P.O.T.O — MVP</h1>

<p align="center">
  <em>Plataforma de Orientação, Triagem e Ouvidoria<br>
  Totem de Segurança que continua funcionando quando a internet acaba.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-uv-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-Vite%20%2B%20TS-61dafb.svg" alt="React">
  <img src="https://img.shields.io/badge/Edge-Raspberry%20Pi%205-c51a4a.svg" alt="Hardware">
</p>

---

> ### Estado atual: Fases 1 e 2 concluídas, Fase 3 em andamento
>
> **19 de 82 tasks · 307 testes passando.** Prontos: domínio, catálogo de canais,
> roteador determinístico, persistência SQLite com idempotência e máquina de estados
> append-only. Em construção: triagem e merge protetivo (Fase 3).
>
> Ainda não existem: API HTTP (Fase 4), interface (Fases 5–6) e deploy (Fase 9) — os
> alvos do Makefile que dependem deles avisam em qual task chegam. Progresso detalhado
> em [TASKS.md](TASKS.md).

---

## O que é

Alguém em situação de risco no campus — assédio, mal-estar, ameaça — toca **um botão**
no totem. O sistema classifica o pedido, **roteia para o canal certo** (segurança do
campus, Sala Lilás, SAMU, Polícia Militar) e avisa a central em menos de 2 segundos,
sem exigir que a pessoa saiba para quem ligar.

O problema real não é a falta de canais: a UFPI já tem CSV, Sala Lilás, SAPSI e Ouvidoria.
O problema é que, no momento do susto, **ninguém lembra qual número disca** — e a
hesitação custa minutos.

Duas restrições moldam quase todas as decisões técnicas deste projeto:

> **1. Se a rede cair, o totem não pode virar um enfeite.**
> **2. Nada que a pessoa digite ou fale pode reduzir a proteção que ela já pediu.**

A primeira explica a fila offline e o roteamento determinístico. A segunda explica o
**merge protetivo** — a decisão de arquitetura mais importante do sistema, detalhada em
[ARCHITECTURE.md §2](ARCHITECTURE.md#d4--merge-protetivo-é-a-única-fonte-da-verdade).

---

## Documentação

| Documento | Assunto |
|---|---|
| [`PLAN.md`](PLAN.md) | Escopo do MVP, stack e por que cada escolha, roadmap, riscos |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Arquitetura, decisões técnicas, API, banco, fluxos |
| [`TASKS.md`](TASKS.md) | As 82 tasks com critérios de aceitação e status |
| [`CLAUDE.md`](CLAUDE.md) | Diretrizes do projeto (autoria de commits) |
| [`docs/inferencia.md`](docs/inferencia.md) | Medições do classificador: por que não um LLM |
| [`docs/conexao-ssh.md`](docs/conexao-ssh.md) | Como conectar na Raspberry Pi por SSH |

---

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| [`uv`](https://docs.astral.sh/uv/) | ≥ 0.4 | Backend Python |
| [Node.js](https://nodejs.org) | ≥ 20 | Build do frontend — **só na máquina de desenvolvimento**, não na Pi |
| Python | ≥ 3.11 | Runtime do backend |

Não é necessário Docker, Postgres, Redis nem Ollama.

---

## Começando

```bash
git clone https://github.com/KauaMach/poto-mvp.git
cd poto-mvp

make setup     # instala backend + frontend e TREINA o classificador
make dev       # backend :8000 + frontend :5173
```

| | URL |
|---|---|
| 🖥️ Totem | http://localhost:5173/ |
| 📊 Painel da central | http://localhost:5173/painel |
| 📘 API / OpenAPI | http://localhost:8000/docs |

> `make setup` treina o classificador de triagem (105 exemplos, poucos segundos). **Não pule
> esta etapa** — sem o modelo, a triagem cai numa heurística de palavras-chave que erra
> casos críticos. O `GET /api/v1/health` diz honestamente qual motor está ativo.

### Configuração

```bash
cp backend/.env.example backend/.env
```

| Variável | Padrão | Descrição |
|---|---|---|
| `POTO_DB_PATH` | `backend/poto.db` | Caminho do SQLite |
| `POTO_NOTIF_PROVIDER` | `log` | `log` ou `webhook` |
| `POTO_NOTIF_WEBHOOK_URL` | — | Endpoint do WhatsApp (Evolution API / n8n) |
| `POTO_CONTACT_*` | — | Contato de cada canal — **obrigatório**, sem padrão |
| `POTO_PAINEL_TOKEN` | — | Token do painel; vazio libera (só desenvolvimento) |
| `POTO_SLA_CHECK_INTERVAL` | `30` | Segundos entre verificações de SLA |
| `POTO_CLF_PATH` | `backend/app/data/triagem_clf.joblib` | Artefato do classificador |

> ⚠️ **Nenhum telefone real vai versionado.** Os contatos dos canais são obrigatórios via
> variável de ambiente — o projeto anterior trazia um celular de Teresina como padrão no
> código, e ele seria acionado de verdade por qualquer um na rede.

---

## Comandos

| Comando | O que faz |
|---|---|
| `make setup` | Instala dependências e treina o classificador |
| `make dev` | Sobe backend e frontend em modo de desenvolvimento |
| `make backend` | Só a API (`:8000`) |
| `make frontend` | Só o frontend (`:5173`) |
| `make build` | Build de produção — o backend passa a servir tudo em `:8000` |
| `make deploy` | Constrói e envia para a Pi por rsync, num comando só |
| `make test` | Suíte completa (pytest) |
| `make lint` | ruff + oxlint |
| `make train-clf` | Retreina o classificador e reporta a acurácia |
| `make seed` | Chamados de exemplo |
| `make demo-reset` | Limpa o banco, semeia e reinicia os serviços |
| `make clean` | Remove `dist/`, venv e banco local |

---

## Testando

```bash
make test
```

A suíte cobre roteamento, persistência, idempotência, contratos da API e — o mais
importante — a **regressão de segurança** (`tests/test_regressao_seguranca.py`): um
conjunto de frases reais que prova que nenhuma combinação de trilha e texto reduz a
gravidade atribuída. Entre elas:

| Trilha | Texto | Exigido |
|---|---|---|
| Segurança | "socorro" | `risco_imediato` — nunca `orientacao` |
| Saúde | "estou desmaiando" | `risco_imediato` · SAMU 192 |
| Saúde | "to passando mal" | `risco_imediato` · SAMU 192 |
| Mulher | *(qualquer)* | tela neutra, sem som, sem protocolo |

Cada linha dessa tabela é um defeito reproduzido no projeto anterior.

### Fluxo ponta a ponta (manual)

1. `make dev` e abra o **totem** e o **painel** em duas abas
2. Toque numa trilha → o chamado aparece no painel em menos de 1 s
3. Dê **ACK** no painel → o totem reflete o estado
4. Deixe o SLA estourar (120 s em crítico) → observe o escalonamento automático
5. Desconecte a rede, acione uma trilha, reconecte → a fila drena **sem duplicar**

---

## Modo produção

```bash
make build      # gera frontend/dist
make backend    # o backend serve a aplicação e a API na mesma origem
```

Instalação completa na Pi:

```bash
sudo deploy/install-pi.sh
```

O script sobe **um** serviço systemd e imprime as URLs para apontar o tablet:

| Serviço | Papel |
|---|---|
| `poto-api.service` | API + aplicação estática, em `0.0.0.0:8000` |

A Pi opera **headless**, sem monitor nem periféricos — o navegador roda no tablet e o
pânico é um botão na própria interface. Configuração do tablet em
[`docs/setup-tablet.md`](docs/setup-tablet.md): adicionar à tela inicial, ativar a
**fixação de tela** do Android e desligar o tempo de tela.

---

## Hardware

| Item | Modelo |
|---|---|
| Tela do totem | **Samsung Galaxy Tab A11** — 8.7", 1340×800 |
| Servidor | Raspberry Pi 5 — 8 GB (headless) |
| Câmera | Pi Camera Module (CSI) **ou** webcam USB |
| Microfone | Array USB **ou** embutido na webcam |
| Rede | WiFi ou Ethernet entre tablet e Pi |
| Fonte | USB-C PD 27 W oficial |

```
[ Galaxy Tab A11 ]  Chrome, tela cheia
        │           (pânico é botão na interface)
        │ WiFi / LAN
        ▼
[ Raspberry Pi 5 ]  FastAPI + SQLite — headless
        │
   [ Câmera ]  [ Microfone ]   ← capturados pelo backend,
                                  transmitidos em MJPEG
```

### Câmera e microfone

Estão na **Pi**, não no tablet. Como a Pi é headless, nenhum navegador os enxerga: a
captura é feita pelo backend em Python (`picamera2`/V4L2 e ALSA) e transmitida em MJPEG,
que o painel renderiza com um `<img>` — sem WebRTC.

> **A captura nunca fica ligada.** Ela só inicia quando a central solicita, sempre
> vinculada a um chamado ativo, expira sozinha em 10 minutos e **toda ativação é registrada
> na auditoria**. Sem chamado e sem sessão, os endpoints de stream respondem `403`.

Câmera e microfone **do tablet** são P2: `getUserMedia` exige contexto seguro, e a origem
`http://poto.local:8000` não é. Entrariam só com TLS na LAN.

O tablet carrega a aplicação **da própria Pi**, então não há CORS nem endpoint para
configurar. Se a rede cair, o totem continua acionando pela fila local e drena depois.

> **Dívida conhecida:** por não ser mais `localhost`, a origem não é um contexto seguro.
> Câmera e microfone são P2 no MVP; quando entrarem, exigirão TLS na LAN.

---

## Identidade visual

O sistema de design é herdado do projeto P.O.T.O original: preto-tinta `#17150F` e
laranja-ferrugem `#C0392B` sobre papel quente `#FBF9F6`, tipografia **Michroma** (display)
+ **Inter** (corpo), cantos arredondados e alvos de toque de no mínimo 64px.

Os tokens canônicos estão em [`PLAN.md §6`](PLAN.md#6-identidade-visual--valores-canônicos)
e são portados literalmente para `frontend/src/estilos/tokens.css`.

> **Fontes e ícones são auto-hospedados.** Nada de CDN: num totem que se anuncia
> offline-first, a primeira coisa a quebrar sem internet seria a tipografia e **todos os
> ícones dos botões**.

---

## Licença

A definir.
