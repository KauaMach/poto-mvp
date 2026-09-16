# P.O.T.O MVP — Arquitetura

> Decisões técnicas e desenho do Totem de Segurança. Complementa o [PLAN.md](PLAN.md).

---

## 1. Visão geral

A tela do totem é um **Samsung Galaxy Tab A11** (8.7", 1340×800). Um tablet não aceita
entrada HDMI — ele não pode ser monitor da Pi. Logo o tablet é um **cliente de rede**: ele
abre o Chrome apontando para a Pi, que serve tanto a aplicação quanto a API.

```
        ┌─────────────────────────────┐
        │   SAMSUNG GALAXY TAB A11    │  8.7" · 1340×800
        │   Chrome + fixação de tela  │  (kiosk do Android)
        │   http://poto.local:8000    │
        └──────────────┬──────────────┘
                       │ WiFi / LAN — o app vem da Pi, então MESMA ORIGEM
                       ▼
┌────────────────────── RASPBERRY PI 5 ─────────────────────────────┐
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │        poto-api.service — uvicorn + FastAPI  :8000           │ │
│  │                                                              │ │
│  │   /            React build estático (Vite)                   │ │
│  │   /painel      mesma aplicação, outra rota                   │ │
│  │   /api/v1      REST + WebSocket                              │ │
│  │      │                                                       │ │
│  │      ├─► TRIAGEM ──► classificador (3 ms) → heurística       │ │
│  │      │                        ↓                              │ │
│  │      ├─► MERGE PROTETIVO ◄── única fonte da verdade          │ │
│  │      │   trilha ⊕ texto = o MAIS protetivo de cada dimensão  │ │
│  │      │                                                       │ │
│  │      ├─► ROTEADOR     tipo × modo × horário                  │ │
│  │      ├─► SQLite       poto.db (WAL)                          │ │
│  │      ├─► CANAIS       log · webhook                          │ │
│  │      ├─► SLA loop     30 s                                   │ │
│  │      └─► MÍDIA        captura local, sob demanda da central   │ │
│  └────────────────────────────▲─────────────────────────────────┘ │
│                               │ picamera2 / V4L2 · ALSA           │
│                   [ Câmera CSI/USB ]  [ Microfone ]               │
│                                                                   │
│   Headless: sem monitor, sem GPIO. 1 serviço systemd.             │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │ LAN
                                  │  • REST + WS (chamados)
                                  │  • MJPEG (vídeo)  ── sob demanda
                                  ▼
                ┌──────────────────────────────┐      webhook
                │  PAINEL — notebook/desktop   │ ───────────────► WhatsApp
                │  mesmo build, rota /painel   │            CSV / Sala Lilás
                └──────────────────────────────┘
```

**Um servidor serve tudo.** O React é compilado para estático e montado pelo FastAPI. O
tablet e o notebook da central carregam a **mesma aplicação da mesma origem** — então
continua não havendo CORS nem proxy em produção. O que muda em relação a um totem com
tela acoplada:

| | Tela acoplada à Pi | **Tablet como cliente (adotado)** |
|---|---|---|
| Origem | `localhost` | `http://poto.local:8000` |
| CORS | dispensável | dispensável (mesma origem) |
| Contexto seguro | sim, de graça | **não** — `localhost` não se aplica |
| Câmera / microfone | funcionam sem HTTPS | exigiriam **HTTPS** (TLS em LAN) |
| Kiosk | Chromium + systemd | **fixação de tela do Android** |
| Rede | irrelevante | **dependência operacional** |

O contexto seguro é o ponto que decide **de quem** são a câmera e o microfone. Ver D7:
no MVP eles são da **Pi**, capturados no servidor, e por isso não passam por navegador
nenhum — o bloqueio de `getUserMedia` fica irrelevante. A câmera do tablet continua
inviável sem TLS, e por isso é P2.

A dependência de rede é o custo real desta topologia: se o WiFi entre tablet e Pi cair, o
tablet **continua operando pela fila offline** (§7, F4) e drena quando a rede voltar. O
totem não vira enfeite — mas o painel não acende em tempo real enquanto isso.

---

## 2. Decisões técnicas

### D1 — React compilado para estático, servido pelo FastAPI

Um kiosk não tem SEO, não tem usuários remotos e não se beneficia de SSR. Next.js cobraria
um processo Node permanente na Pi por zero benefício. Vite produz arquivos estáticos que o
FastAPI monta com uma linha — e, servindo a aplicação da mesma origem da API, o tablet e o
notebook da central não precisam de CORS nem de configuração de endpoint.

> **Armadilha herdada:** no projeto antigo o build gerava só os `.js` e nunca copiava o
> HTML, então `/app` respondia 404 e o modo kiosk nunca funcionou. Com Vite isso não se
> repete — `vite build` emite o `index.html` com os assets já referenciados. A task
> MVP-066 verifica isso explicitamente.

### D1c — A Pi executa, não compila

O frontend é construído na máquina de desenvolvimento e enviado pronto por `rsync`
(`make deploy`). **Node não é instalado na Pi.** Três razões, em ordem de peso:

1. **O toolchain é binário nativo por arquitetura.** Vite 8 usa Rolldown, e o ecossistema
   ao redor é Rust compilado: `@rolldown/binding-linux-x64`, `lightningcss-linux-x64`,
   `@oxlint/binding-linux-x64`. Na Pi o npm instalaria as variantes `arm64` — binários
   **diferentes** dos usados nos testes. Construindo num lugar só, o artefato que roda é
   literalmente o que foi validado.
2. **A assimetria é de 600×:** 133 MB e 700 arquivos de ferramenta para produzir 220 KB e
   2 arquivos de resultado. A Pi serve os 220 KB e nunca precisa saber que TypeScript existe.
3. **Deploy de 1 segundo em vez de 3 minutos**, sem exigir internet na Pi — o rsync vai pela
   LAN. Na véspera da apresentação, isso é a diferença entre testar 10 ajustes e testar 100.

O cenário "só tenho a Pi" não existe na prática: o notebook que roda o painel está presente
por definição na demonstração.

**O risco que isso cria, e como é fechado.** Separar build de execução abre a porta para
servir um artefato velho — alterar o código, esquecer de reconstruir, enviar a versão
anterior, e depurar por uma hora um bug que já estava corrigido. Duas travas:

- `make deploy` faz build **e** envio na mesma ação: não há como enviar sem reconstruir.
- O `/health` expõe o build-id do frontend, então dá para confirmar qual artefato está no ar.

**Isto também é o que escala.** Com dez totens, construir em cada um multiplica o tempo e a
chance de um divergir. O caminho natural adiante — CI compila, publica o artefato, o deploy
busca — já tem exatamente esta forma.

### D1b — Layout fluido, orientação-consciente

A tela do totem é um tablet de **8.7"**, que é pequeno. Considerando DPR entre 1,5 e 2, o
viewport CSS fica aproximadamente:

| Contexto | Viewport CSS aproximado | Restrição dominante |
|---|---|---|
| Tab A11 retrato | ~530 × 890 | largura estreita |
| Tab A11 paisagem | ~890 × 530 | **altura curta** |
| Notebook / desktop | 1280 × 800 e acima | nenhuma |

> O valor exato depende da densidade que o Android reporta. A task MVP-055 exige medir
> `window.innerWidth/innerHeight` **no aparelho** e ajustar — não se projeta contra um
> número suposto.

O caso difícil é a **paisagem**: ~530px de altura precisam acomodar cabeçalho, título,
quatro alvos de toque e o botão de pânico. Com o cartão de 168px do design original, duas
linhas já consomem 336px + espaçamentos — não cabe.

A solução não é reduzir alvos de toque (são intocáveis, ≥64px). É **mudar o arranjo da
grade conforme a orientação**:

```css
/* base — retrato e telas estreitas: 2×2 */
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); }

/* paisagem curta (tablet deitado): 4 em linha, cartões mais baixos */
@media (orientation: landscape) and (max-height: 620px) {
  .grid   { grid-template-columns: repeat(4, 1fr); gap: var(--space-sm); }
  .choice { min-height: 120px; padding: 16px 12px; }
  .choice .sym { font-size: 40px; }   /* xl → lg */
}

/* desktop: volta ao 2×2 do design original, centrado */
@media (min-width: 1024px) and (min-height: 700px) {
  .grid { grid-template-columns: 1fr 1fr; max-width: 720px; margin-inline: auto; }
}

/* muito estreito: coluna única */
@media (max-width: 480px) { .grid { grid-template-columns: 1fr; } }
```

Três princípios que tornam isso robusto sem multiplicar breakpoints:

1. **Consultar altura, não só largura.** O que quebra em paisagem é a altura; `max-height`
   é o gatilho correto, e funciona igual num notebook com janela baixa.
2. **`dvh`, não `vh`.** A barra de endereço do Chrome no Android entra e sai; `100vh`
   estoura a tela e cria rolagem. `100dvh` acompanha.
3. **`clamp()` no lugar de degraus.** Título, espaçamentos e ícones escalam continuamente
   entre tablet e desktop — menos breakpoints, menos casos para testar.

O painel da central segue o caminho oposto: nasce para desktop e só precisa não quebrar
se alguém abrir no tablet.

### D2 — SQLite com WAL, sem ORM

Volume real: dezenas de registros por dia, um dispositivo. SQLite dá transação, arquivo
único e zero configuração. `PRAGMA journal_mode=WAL` faz a leitura do painel não bloquear
a escrita do totem; `synchronous=NORMAL` poupa o cartão SD.

Acesso por SQL direto via `sqlite3` da stdlib, em um módulo `db.py` com funções nomeadas.
Sem ORM porque o esquema é pequeno e estável — e porque isso torna uma migração futura
para Postgres uma troca de driver, não uma reescrita.

### D3 — Classificador especializado, não LLM

Medido no mesmo held-out de 42 exemplos:

| Abordagem | Acurácia tipo | Acurácia gravidade | Latência | Cabe na Pi? |
|---|---|---|---|---|
| qwen2.5:0.5b | 29% | 27% | ~5800 ms | sim |
| qwen2.5:1.5b | 45% | 48% | ~6100 ms | sim |
| llama3.2:3b | 86% | 60% | ~2000 ms | não (workstation) |
| **TF-IDF + LogReg** | **83,3%** | **85,7%** | **3,3 ms** | **sim** |

Os LLMs que cabem na Pi são ruins demais para decidir se chama o SAMU; os bons não cabem.
TF-IDF com n-gramas de **palavra + caractere** tolera erro de digitação e variação
morfológica — é o que faz "socorroo", "tão me seguindo" e "passando maal" caírem no lugar
certo com apenas 77 exemplos rotulados.

### D4 — Merge protetivo é a única fonte da verdade

O defeito mais grave do projeto antigo: a gravidade do roteador era **sobrescrita** pela
gravidade inferida do texto, sem proteção. Resultado reproduzido: "socorro" na trilha
Segurança virava `orientacao` e ficava retido aguardando operador.

No MVP existe **uma única função**:

```python
def merge_acionamento(trilha: Routing, triagem: Triagem) -> Decisao:
    """Combina a trilha escolhida pela pessoa com a triagem do texto.
    Em CADA dimensão (tipo, gravidade, canal) vence o MAIS protetivo.
    Nunca o mais recente, nunca o mais confiante."""
```

Regras invioláveis:

1. `gravidade_final = max(trilha, triagem)` na ordem `orientacao < risco_potencial < risco_imediato`
2. Um sinal crítico no texto **promove**, nunca rebaixa
3. Se a triagem sugerir `ouvidoria` mas a trilha for mais séria, **vale a trilha**
4. O mesmo vale no dreno da fila offline: evento enfileirado como `ouvidoria` com texto
   grave é **re-triado e promovido** na chegada

Toda a suíte de regressão (MVP-019) existe para provar que esta função nunca rebaixa.

### D5 — Notificação com payload mínimo (LGPD)

A notificação externa carrega **protocolo, tipo, gravidade e totem**. O relato **nunca
sai** — quem precisa do conteúdo consulta o painel. Não é só conformidade: uma mensagem
interceptada não pode expor o depoimento de uma vítima.

### D5b — Pânico virtual exige pressionar e segurar

No MVP o pânico é um botão na interface, não um arcade físico. Isso muda o problema: um
botão físico exige força deliberada, enquanto um botão em tela pública dispara com um roçar
de mão — e cada disparo faz broadcast **real** para CSV e Sala Lilás.

A resposta é **1000 ms de pressão contínua**, com anel de progresso e vibração ao completar.
Soltar antes cancela sem enviar nada.

Por que não as alternativas:

| Opção | Problema |
|---|---|
| Toque simples (comportamento do POTO antigo) | Alarme falso por toque acidental; num totem de parede isso é questão de tempo |
| Toque + tela de confirmação | Insere uma **decisão** no pior momento possível. Contradiz "≤ 2 toques" e o princípio de que a tela de emergência não pede escolha nenhuma |

Um segundo é curto o bastante para não custar nada numa emergência real, e longo o bastante
para que nenhum contato acidental o alcance. O anel preenchendo também comunica que o
sistema está respondendo — informação que um toque instantâneo não dá.

### D7 — Mídia capturada no servidor e transmitida em MJPEG

A câmera e o microfone estão fisicamente na Pi, e a Pi é headless. Isso muda tudo em
relação ao projeto antigo: lá, o Chromium rodava **na própria Pi**, em `localhost`, e a
câmera era acessada por `getUserMedia()` como se fosse um webcam de desktop. Com o
navegador no tablet, **nenhum navegador enxerga os periféricos da Pi**.

Logo a captura vira código Python no backend:

| Fonte | Biblioteca | Saída |
|---|---|---|
| Câmera CSI (Pi Camera Module) | `picamera2` | frames JPEG direto do ISP |
| Câmera USB (UVC) | V4L2 | frames JPEG |
| Microfone (USB ou array) | ALSA (`sounddevice` / `arecord`) | PCM |

**Transporte: MJPEG sobre HTTP** (`multipart/x-mixed-replace`). No painel isso é
literalmente `<img src="/api/v1/midia/camera/{id}/stream">` — sem WebRTC, sem sinalização,
sem STUN/TURN, sem biblioteca. Latência na LAN fica em centenas de milissegundos.

Por que não H.264: **a Raspberry Pi 5 removeu o encoder H.264 por hardware** que a Pi 4
tinha. Codificar H.264 nela é em CPU, competindo com a API e a triagem. JPEG sai do ISP
quase de graça. Gasta-se mais banda — irrelevante numa LAN — e poupa-se o processador.

Áudio segue o mesmo princípio de simplicidade: stream HTTP em chunks consumido por um
`<audio>` no painel, sem Web Audio API. Se o streaming contínuo se mostrar instável, o
fallback documentado é clipe curto sob demanda.

> **Privacidade não é detalhe aqui.** Uma câmera e um microfone permanentemente ativos num
> totem de campus seriam abuso. A regra do sistema: a captura **só inicia quando a central
> solicita**, sempre vinculada a um chamado ativo, e **toda ativação é registrada na
> auditoria** (quem abriu, quando, por quanto tempo). Não existe stream sem chamado.

### D6 — systemd, não Docker

Uma unit, `Restart=always`. Sem GPIO no MVP, a Pi não tem dependência de hardware nenhuma:
é um servidor Linux pequeno rodando um processo. Docker cobraria boot e RAM por zero
ganho, e uma camada a mais para depurar às vésperas da apresentação.

> Isso também dá liberdade de implantação: sem amarra de hardware, o mesmo backend roda
> numa Pi, num mini-PC ou numa VM sem mudar uma linha. A Pi continua sendo a escolha por
> custo, consumo e por já estar prevista para receber o GPIO depois.

---

## 3. Estrutura de pastas

```
poto-mvp/
├── README.md  PLAN.md  ARCHITECTURE.md  TASKS.md  CLAUDE.md
├── Makefile
├── deploy/
│   ├── poto-api.service
│   └── install-pi.sh
├── docs/
│   ├── setup-tablet.md       kiosk do Android no Galaxy Tab A11
│   ├── viewports.md          medidas reais do aparelho
│   ├── aceite-mvp.md  roteiro-demo.md
│
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py            cria o app, monta routers e o estático
│   │   ├── config.py          env + catálogo de canais + SLA
│   │   ├── db.py              SQLite: schema, WAL, funções de acesso
│   │   ├── models.py          enums + contratos Pydantic
│   │   ├── hub.py             WebSocket: broadcast para o painel
│   │   ├── sla.py             worker de SLA e escalonamento
│   │   │
│   │   ├── api/               SÓ HTTP — valida, chama, devolve
│   │   │   ├── eventos.py       /eventos  /panico
│   │   │   ├── chamados.py      /chamados/*  /ack
│   │   │   └── sistema.py       /health  /config  /canais
│   │   │
│   │   ├── triagem/           DECIDE O QUE É a ocorrência
│   │   │   ├── __init__.py      fachada: triar(texto, modo)
│   │   │   ├── heuristica.py    palavras-chave (rede de segurança)
│   │   │   ├── classificador.py TF-IDF + LogReg
│   │   │   ├── merge.py       ★ MERGE PROTETIVO
│   │   │   └── roteador.py      tipo × modo × horário
│   │   │
│   │   ├── canais/            DECIDE COMO AVISAR
│   │   │   ├── __init__.py      registry + enviar()
│   │   │   ├── base.py          Protocol + montar_mensagem()
│   │   │   ├── log.py  webhook.py
│   │   │
│   │   ├── midia/             CÂMERA E MICROFONE DA PI
│   │   │   ├── __init__.py      registro de dispositivos + detecção
│   │   │   ├── camera.py        picamera2 (CSI) · V4L2 (USB)
│   │   │   ├── microfone.py     ALSA
│   │   │   └── sessao.py        ativação por chamado + auditoria
│   │   │
│   │   └── data/
│   │       └── triagem_clf.joblib   (gerado por make setup)
│   ├── scripts/
│   │   ├── train_classificador.py
│   │   ├── triagem_dataset.json     77 exemplos de treino
│   │   └── bench_dataset.json       42 exemplos held-out
│   └── tests/
│
└── frontend/
    ├── package.json  vite.config.ts  tsconfig.json
    ├── index.html
    ├── public/fonts/          ★ Michroma, Inter, Material Symbols (locais)
    └── src/
        ├── main.tsx  App.tsx
        ├── estilos/           tokens.css  base.css
        ├── comum/             api.ts  fila.ts  ws.ts  tipos.ts  config.ts
        ├── componentes/       Choice · Panic · StatusPill · Wordmark ·
        │                      Confirm · Sym · Card · Chip
        ├── totem/             Totem.tsx · telas/{Home,Confirmacao,AlertaAtivo}.tsx
        └── painel/            Painel.tsx · ListaChamados.tsx · CardChamado.tsx
```

| Pasta | Responsabilidade |
|---|---|
| `api/` | Só HTTP: validar entrada, chamar caso de uso, devolver contrato. Sem regra de negócio. |
| `triagem/` | Decidir **o que é** a ocorrência. A única porta é `triar()`. |
| `canais/` | Decidir **como avisar**. Cada provider é um arquivo com uma função. |
| `midia/` | Câmera e microfone da Pi. Isolado por ser o único ponto com dependência de hardware. |
| `componentes/` | Identidade visual do POTO em React. Nenhuma regra de negócio. |

> Não há `hardware/` no MVP. Quando o botão físico entrar, ele volta como um pacote com um
> daemon que só faz `POST /panico` — processo separado, sem tocar no backend.

---

## 4. Modelo de domínio

```python
TipoOcorrencia  = seguranca | mulher | saude | ouvidoria
Modo            = normal | discreto
OrigemAcionamento = touch | botao_fisico | panico
Gravidade       = risco_imediato | risco_potencial | orientacao
StatusChamado   = recebido | roteado | notificado | alerta_ativo
                | reconhecido | em_atendimento | encerrado
                | escalonado | falha_notificacao | cancelado
```

### Tabela de roteamento (determinística, sem IA)

| Trilha | Horário comercial | Fora do expediente | Fallback | Gravidade | Discreto |
|---|---|---|---|---|---|
| **Segurança** | CSV / PREUNI | CSV / PREUNI | PM 190 | `risco_imediato` | não |
| **Mulher** | Sala Lilás | Central 180 | 180 → PM 190 | `risco_potencial` | **sempre** |
| **Saúde — emergência** | SAMU 192 | SAMU 192 | CSV | `risco_imediato` | não |
| **Saúde — apoio** | SAPSI / PRAEC | Ouvidoria | Ouvidoria | `orientacao` | não |
| **Ouvidoria** | Ouvidoria | Ouvidoria | Ouvidoria | `orientacao` | não |

Horário comercial: seg–sex, 08–12 e 14–17, fuso de Teresina (UTC−3, sem horário de verão).
Encaminhar para uma sala vazia às 2h da manhã é o mesmo que não encaminhar.

### SLA por gravidade

| Gravidade | Prazo para ACK | Ao estourar |
|---|---|---|
| `risco_imediato` | 120 s | escalona para o fallback |
| `risco_potencial` | 600 s | escalona para o fallback |
| `orientacao` | — | não escalona |

---

## 5. Banco de dados

```sql
CREATE TABLE chamados (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id       TEXT UNIQUE NOT NULL,   -- CALL-2026-000001
  evento_id        TEXT UNIQUE NOT NULL,   -- UUID do totem → IDEMPOTÊNCIA
  totem_id         TEXT NOT NULL,
  tipo_ocorrencia  TEXT NOT NULL,
  modo             TEXT NOT NULL,
  origem_acionamento TEXT NOT NULL,
  gravidade        TEXT NOT NULL,
  canal_roteado    TEXT NOT NULL,
  fallback         TEXT,
  status           TEXT NOT NULL,
  texto_livre      TEXT,                   -- fica só aqui; nunca sai na notificação
  triagem_json     TEXT,                   -- auditável: o que a triagem decidiu
  observacao       TEXT,
  timestamp_local  TEXT,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL,
  acked_at         TEXT
);

CREATE TABLE estado_log (            -- máquina de estados, append-only
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id TEXT NOT NULL,
  de         TEXT,
  para       TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE notificacoes (          -- quem foi acionado, por qual canal, com que resultado
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id TEXT NOT NULL,
  canal      TEXT NOT NULL,
  destino    TEXT NOT NULL,
  provider   TEXT NOT NULL,
  sucesso    INTEGER NOT NULL,
  mensagem   TEXT,
  detalhe    TEXT,
  escalonamento INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_notif_chamado  ON notificacoes(chamado_id);
CREATE INDEX idx_estado_chamado ON estado_log(chamado_id);
CREATE INDEX idx_chamados_status ON chamados(status);

PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
```

**Relacionamentos**

```
chamados 1 ──── N estado_log     (por chamado_id)
chamados 1 ──── N notificacoes
totem_id 1 ──── N chamados       (string livre; sem tabela de totens no MVP)
```

**Idempotência.** `evento_id` é `UNIQUE`. O totem gera um UUID **antes** de enviar; se o
POST for repetido (dreno duplo da fila offline, retry de rede), o `INSERT` colide e o
servidor devolve o chamado existente com `duplicado: true`. Drenar a fila duas vezes
nunca gera dois alarmes de emergência.

**Protocolo.** `CALL-{ano}-{sequencial:06d}`, derivado do `id`.

> **Pendência LGPD (fora do MVP, bloqueia piloto real):** não há política de retenção
> para `chamados`. Um caso de violência contra a mulher fica no cartão SD indefinidamente.
> Definir antes de qualquer instalação em campo.

---

## 6. API

Prefixo `/api/v1`. Todos os contratos em `models.py`.

### Acionamento — abertos, sem credencial

> Um totem em pânico não pode falhar por autenticação.

| Método | Rota | Objetivo | Entrada | Saída |
|---|---|---|---|---|
| `POST` | `/eventos` | Acionar uma trilha | `evento_id`, `totem_id`, `tipo_ocorrencia`, `modo`, `origem_acionamento`, `texto_livre?`, `timestamp_local?` | `chamado_id`, `status`, `canal_roteado`, `gravidade`, `instrucao_totem`, `duplicado` |
| `POST` | `/panico` | Alerta com broadcast paralelo | `evento_id`, `totem_id`, `modo` | `chamado_id`, `status`, `gravidade`, `resultados[]`, `escalonamento_disponivel[]` |

`instrucao_totem` = `{ mensagem_tela, feedback_sonoro, tela_neutra }` — é o backend que
decide se a tela é neutra e se há som, não o frontend. O modo discreto não pode depender
de o cliente lembrar de aplicá-lo.

### Central — exigem `X-POTO-Token` (P1)

| Método | Rota | Objetivo | Entrada | Saída |
|---|---|---|---|---|
| `GET` | `/chamados` | Listar para o painel | `?tipo&status&gravidade` | `Chamado[]` (200 mais recentes) |
| `GET` | `/chamados/{id}` | Detalhe | — | Chamado + notificações + estados |
| `POST` | `/chamados/{id}/ack` | Operador reconhece | — | Chamado atualizado |
| `PATCH` | `/chamados/{id}` | Mudar estado / observação | `{status?, observacao?}` | Chamado atualizado |
| `POST` | `/chamados/{id}/escalonar` | Acionar autoridade do estado | `{canal}` | `{sucesso, detalhe}` |
| `WS` | `/ws` | Eventos ao vivo | — | `{evento, dados}` |

Eventos do WebSocket: `novo_chamado`, `atualizado`, `conectado`, `ping`.

### Mídia — exigem token; toda ativação é auditada

| Método | Rota | Objetivo | Entrada | Saída |
|---|---|---|---|---|
| `GET` | `/dispositivos` | Listar câmeras e microfones disponíveis | — | `[{id, tipo, nome, dono, status, capacidades}]` |
| `POST` | `/chamados/{id}/midia` | **Abrir** sessão de captura para um chamado | `{dispositivo_id}` | `{sessao_id, stream_url, expira_em}` |
| `DELETE` | `/chamados/{id}/midia` | Encerrar a sessão | — | `{ok}` |
| `GET` | `/midia/camera/{id}/stream` | Stream MJPEG | `?sessao=` | `multipart/x-mixed-replace` |
| `GET` | `/midia/microfone/{id}/stream` | Stream de áudio | `?sessao=` | `audio/wav` em chunks |

Regras que o desenho impõe:

- **Não existe stream sem chamado ativo.** O `stream_url` só responde com uma `sessao_id`
  válida, emitida para um chamado que não está encerrado.
- **Toda abertura e fechamento vira linha de auditoria** — quem, quando, qual dispositivo,
  por quanto tempo.
- A sessão **expira sozinha** (default 10 min) — ninguém deixa uma câmera aberta por
  esquecimento.

### Sistema

| Método | Rota | Objetivo | Saída |
|---|---|---|---|
| `GET` | `/health` | Diagnóstico **honesto** | `{status, triagem: {modo, classificador_carregado}, notificacao, banco, midia: {camera, microfone}}` |
| `GET` | `/config` | Constantes que o front precisa | `{sla, canais, canais_estado, totem_offline_seg}` |
| `GET` | `/canais` | Catálogo de canais | `{canal: {nome, contato}}` |

> **`/health` não mente.** No projeto antigo ele reportava `modo: "agentes"` mesmo sem
> classificador e sem LLM — só a heurística rodava, e não havia como perceber. Aqui
> `modo` reflete o motor que **de fato** executou: `classificador` ou `heuristica`.

> **`/config` existe para matar duplicação.** No projeto antigo o frontend repetia
> `VALIDACAO_SLA_SEG = 90`, `SLA_SEG`, `CANAIS_ESTADO` e `TOTEM_OFFLINE_SEG` em
> `painel.ts` — mudar o `.env` produzia um painel que mentia sobre prazos.

---

## 7. Fluxos

### F1 — Acionamento por trilha (o caminho principal, ≤ 2 toques)

```
Tela inicial "Como podemos ajudar?"
   └─ toque em [Saúde] [Segurança] [Assédio/Sala Lilás] [Outros]
        → POST /eventos { evento_id: uuid, ... }
        → triar(texto)            classificador → heurística
        → rotear(tipo, modo, hora)     canal + fallback + gravidade
        → MERGE PROTETIVO         o mais protetivo de cada dimensão
        → db.criar_chamado()      idempotente → CALL-2026-000001
        → hub.broadcast()         painel acende em < 1 s
        → canais.enviar()         webhook / log
        → 201 { chamado_id, gravidade, instrucao_totem }
        → Tela de confirmação: mensagem + PROTOCOLO
        → retorno automático: 9 s · 12 s se crítico · 5 s se discreto
```

### F2 — Pânico

```
[PÂNICO] na tela  (origem_acionamento: "panico")
   → POST /panico → broadcast PARALELO p/ CSV + Sala Lilás
   → status = alerta_ativo   (PERSISTENTE — não fecha sozinho)
   → Tela de alerta: pulso, protocolo grande, cronômetro correndo
   → estado ao vivo por WS: "Aguardando central" → "Central recebeu"
                            → "Atendimento a caminho"
   → botões de escalonamento manual [PM 190] [SAMU 192] [Bombeiros 193] [180]
      ⤷ registram o acionamento humano; NÃO robo-discam
```

### F3 — Modo discreto (trilha mulher)

```
[Assédio / Sala Lilás]
   → tela NEUTRA · SEM som · SEM protocolo visível
   → "Seu pedido foi registrado. Aguarde atendimento."
   → retorno ao início em 5 s
   → roteamento: comercial → Sala Lilás · fora → Central 180
```

Se o agressor está a três metros, uma tela que anuncia "Sala Lilás acionada" transforma o
socorro em risco. Por isso `tela_neutra` e `feedback_sonoro` vêm do **backend**.

### F4 — Offline

```
Rede cai → POST falha → evento entra na fila (localStorage)
   → confirmação IMEDIATA na tela (a pessoa não percebe diferença)
   → badge "N na fila" no header
   → rede volta → dreno automático → servidor deduplica por evento_id
```

### F5 — Central

```
Card acende por WS (< 1 s)
   → [ACK] → totem reflete "A central recebeu seu alerta"
   → muda estado: em_atendimento → encerrado
```

### F5b — Ver e ouvir o local (sob demanda)

```
Operador, num chamado ATIVO, clica em [Ver câmera]
   → GET /dispositivos            lista o que a Pi tem
   → POST /chamados/{id}/midia    { dispositivo_id } → sessao_id
   → auditoria: "camera_aberta por operador às HH:MM"
   → <img src="/midia/camera/{id}/stream?sessao=…">   MJPEG ao vivo
   ⋮
   → DELETE /chamados/{id}/midia  OU expiração automática em 10 min
   → auditoria: "camera_fechada · duração 3m12s"
```

A captura **nunca** está ligada por padrão. Sem chamado ativo e sem sessão, os endpoints de
stream respondem `403`.

### F6 — SLA

```
notificado + sem ACK + risco_imediato  → 120 s → escalona p/ fallback
notificado + sem ACK + risco_potencial → 600 s → escalona p/ fallback
```

O timeout nunca resolve a favor do silêncio.

---

## 8. Implantação

### Na Raspberry Pi — um serviço

| Unidade | Papel | Depende de | Restart |
|---|---|---|---|
| `poto-api.service` | uvicorn + FastAPI + aplicação estática | `network-online.target` | `always` |

Só isso. Não há unit de kiosk (o navegador roda no tablet) nem de GPIO (o pânico é virtual
no MVP). A Pi opera **headless**, sem monitor, teclado ou periférico — o que reduz consumo,
tempo de boot e superfície de falha.

### Endereçamento — o tablet precisa achar a Pi

O tablet abre uma URL fixa. Duas formas de garantir que ela nunca mude:

1. **mDNS** — `avahi-daemon` na Pi publica `poto.local`. Funciona sem configurar o
   roteador; é o caminho padrão.
2. **IP estático** — reserva por DHCP no roteador ou `dhcpcd.conf` na Pi. É o plano B se
   o mDNS falhar na rede do campus.

O `install-pi.sh` configura o mDNS e imprime **as duas** URLs no final, para que o tablet
possa ser apontado para qualquer uma.

### No tablet — kiosk do Android

Android não tem flags de linha de comando; o equivalente ao `--kiosk` é:

1. **Fixação de tela** (*Screen pinning*, em Configurações → Segurança) trava o Chrome em
   primeiro plano e exige PIN para sair. É nativo, sem app de terceiro.
2. **Adicionar à tela inicial** a partir do Chrome — abre em modo autônomo, sem barra de
   endereço, usando o `manifest.webmanifest` com `display: "fullscreen"` e
   `orientation: "any"`.
3. Configurações do aparelho: **tempo de tela desligada = nunca**, brilho fixo, rotação
   automática conforme a instalação, notificações silenciadas.

> A aplicação declara `display: "fullscreen"` e **não** trava orientação no manifest — o
> layout se adapta às duas (§2, D1b).

---

## 9. Como a arquitetura evolui

```python
# app/main.py — o único lugar que muda ao adicionar um módulo
app.include_router(eventos.router)          # ← MVP
app.include_router(chamados.router)         # ← MVP
# app.include_router(universidade.router)   # ← futuro
# app.include_router(acesso.router)         # ← futuro
```

| Evolução | Reaproveita | Acrescenta |
|---|---|---|
| **Serviços universitários** | Totem, kiosk, design system, offline | `modulos/universidade/` + menu na home. Nenhuma mudança no núcleo de segurança. |
| **Check-in / check-out** | Idempotência, SQLite, painel, WS | `modulos/acesso/` + tabela `acessos` + leitor QR/NFC |
| **Botão de pânico físico** | `POST /panico` já existe e é agnóstico de origem; `origem_acionamento` já prevê `botao_fisico` | `hardware/gpio_panico.py` como daemon separado + uma unit systemd. **Nenhuma mudança no backend.** |
| **Controle de acesso** | Tudo do check-in + token do painel | Cadastro de pessoas, relé via GPIO — mesmo padrão do daemon de pânico |
| **Monitoramento** | Heartbeats, liveness, WS | `modulos/monitoramento/` + sensores como processos separados que só fazem HTTP |
| **Multi-totem / NOC** | `totem_id` já está em todo registro | Trocar SQLite por Postgres **quando** passar de ~10 totens: sem ORM, é troca de driver |
| **Voz, vídeo, GSM** | Registry de `canais/`, fachada `triar()` | Cada um entra como um arquivo a mais |
| **IA mais forte** | Fachada `triar()` + merge protetivo | Trocar o motor dentro de `triagem/` — o resto do sistema não sabe qual rodou |

**O princípio que sustenta tudo:** o roteador determinístico e o merge protetivo não
dependem de módulo nenhum. Qualquer coisa nova — um leitor de crachá, um sensor, um LLM
melhor — entra **em volta** do núcleo de segurança, nunca dentro dele.
