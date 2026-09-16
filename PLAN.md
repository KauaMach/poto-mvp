# P.O.T.O — Plano do MVP (Totem de Segurança)

**Alvo:** StartUFPI 2026 · Raspberry Pi 5 · demonstração presencial
**Repositório:** `KauaMach/poto-mvp` (novo, do zero)
**Referência:** `../poto/` (repo de terceiro, `gutoportelaa/poto`) — somente leitura

---

## 1. Por que este projeto existe do zero

O projeto anterior (`../poto/`) é um sistema **coerente, testado e funcional** — 49 testes
passando, roteamento determinístico impecável, auditoria madura, PWA offline. Não é um
protótipo disperso.

Mas ele não é nosso: pertence a outro repositório, carrega escopo que não cabe no MVP
(SIMCom 2G, Twilio, LLM/Ollama, WebRTC, Piper TTS, evidência em vídeo) e acumulou defeitos
de segurança de produto verificados neste ambiente:

| Verificado | Consequência |
|---|---|
| Dizer **"socorro"** na trilha Segurança rebaixa a gravidade de `risco_imediato` para `orientacao` e **retém** o chamado | Falar torna o sistema **menos** responsivo do que ficar calado |
| Artefato do classificador no `.gitignore` — clone limpo roda heurística de substring | "estou desmaiando" → **Ouvidoria**, não SAMU |
| `build.ts` nunca copia HTML/CSS para `dist/` | `GET /app/index.html` → **404**: o modo kiosk nunca existiu |
| Chat offline conclui sempre como `ouvidoria` | Emergência digitada sem rede vai para o canal menos protetivo |
| `/health` reporta `modo: agentes` sem classificador e sem Ollama | Não há como perceber que a triagem está degradada |

**Decisão:** construir limpo, **reaproveitando deliberadamente** o que é bom — a identidade
visual completa, o roteador determinístico, o modelo de domínio e o dataset de triagem —
e deixando para trás o escopo e os defeitos.

---

## 2. Objetivo do MVP

Demonstrar, ponta a ponta e sem rede externa, o conceito central do produto:

> Uma pessoa em risco toca **um botão**, o sistema **classifica**, **roteia para o canal
> certo** e **avisa a central em menos de 2 segundos** — e continua funcionando com o cabo
> de rede arrancado.

O MVP **não** é o produto completo. É a base sobre a qual o Totem de Segurança completo e,
depois, o Totem de Uso Geral serão construídos sem reescrita.

---

## 3. Escopo

### P0 — Obrigatório (define o MVP concluído)

| # | Funcionalidade |
|---|---|
| 1 | Tela inicial com **4 trilhas**: Emergência médica · Segurança · Assédio/Sala Lilás · Outros |
| 2 | **Botão de pânico virtual**, na própria interface web |
| 3 | **Triagem local**: classificador ML + heurística, com **merge protetivo** correto |
| 4 | **Roteamento determinístico** por tipo × modo × horário comercial |
| 5 | **Registro** em SQLite com idempotência por `evento_id` |
| 6 | **Notificação** por `log` e `webhook` |
| 7 | **Painel da central** em tempo real (WebSocket), com ACK e mudança de estado |
| 8 | **Tela de confirmação** com protocolo e retorno automático |
| 9 | **Modo discreto** na trilha mulher (tela neutra, sem som, sem protocolo) |
| 10 | **Fila offline** + dreno idempotente |
| 11 | **SLA + escalonamento automático** por timeout |
| 12 | **Câmera e microfone da Pi**, acionados **sob demanda pela central** e registrados na auditoria |
| 13 | **Kiosk no tablet**: tela cheia, fixação de tela, sem barra de endereço |

### P1 — Importante, pode ser simplificado

- Métricas básicas no painel (contadores, sem gráficos)
- Filtros e busca no painel
- Autenticação por token no painel
- Heartbeat de telemetria do totem

### P2 — Fora do MVP (não implementar agora)

**Botão de pânico físico (GPIO)** · **câmera e microfone do tablet** (exigem TLS na LAN) ·
**gravação e retenção de evidência** · chat de texto · conversa por voz · STT (Whisper) ·
LLM/Ollama/LangGraph · WebRTC P2P · SIMCom/2G/SMS · Twilio/PSTN · Piper TTS · Hailo ·
LoRa · MQTT · auditoria com linha do tempo · frota multi-totem · check-in/check-out ·
serviços universitários · controle de acesso.

> O botão físico sai do MVP mas não some do desenho: `POST /panico` é o mesmo endpoint
> para qualquer origem. Um daemon GPIO na Pi entra depois como processo separado, sem
> tocar no backend — é o que o campo `origem_acionamento` já prevê (`botao_fisico`).

> **Regra de escopo:** nada de P2 entra antes de todo P0 estar verde. Se o tempo apertar,
> corta-se P1 — nunca P0.

---

## 4. Stack — e por que cada peça

| Camada | Escolha | Por quê | Alternativa descartada |
|---|---|---|---|
| **Frontend** | **React 18 + Vite + TypeScript** | Build **estático** servido pelo próprio FastAPI: um processo só na Pi, mesma origem — elimina CORS e proxy, e o tablet não precisa de endpoint configurado. Componentes tornam a identidade do POTO reutilizável sem o DOM imperativo que gerou um `painel.ts` de 735 linhas. | **Next.js**: exigiria um processo Node permanente na Pi (RAM + boot) para um kiosk que nunca precisa de SSR nem SEO |
| **Backend** | **FastAPI + Python 3.11+ (uv)** | Async nativo para o WebSocket do painel, validação por Pydantic, OpenAPI de graça. É a stack do código que vamos portar. | — |
| **Banco** | **SQLite (stdlib `sqlite3`) + WAL** | Arquivo único, zero processo, zero configuração, transacional. O volume real é de dezenas de registros/dia num único dispositivo. | **PostgreSQL**: mais um serviço para subir e manter na Pi, sem ganho no volume do MVP |
| **Triagem** | **scikit-learn — TF-IDF + Regressão Logística** | Medido no held-out: **83,3% tipo / 85,7% gravidade em 3,3 ms**, 100% offline, artefato de 426 KB, treina em segundos. | **LLM local**: os modelos que cabem na Pi dão 29–45% em ~6 s — medido, não suposto |
| **Tempo real** | **WebSocket nativo do FastAPI** | O painel precisa acender em < 1 s sem polling. Zero dependência extra. | **SSE**: unidirecional; **polling**: latência e desperdício |
| **Deploy** | **1 unit systemd na Pi**; frontend construído aqui e enviado por `rsync` | Sem GPIO e sem Node, a Pi é puramente um servidor local: um serviço, boot rápido, headless. O toolchain do Vite é binário nativo por arquitetura, então construir num lugar só garante que o artefato em produção é o mesmo que foi testado — e poupa 133 MB na Pi. | **Docker**: overhead de boot/RAM sem ganho para um processo só. **Build na Pi**: binários `arm64` diferentes dos testados, 3 min por deploy em vez de 1 s, e não escala para vários totens |
| **Tela** | **Samsung Galaxy Tab A11** (8.7", 1340×800) como cliente de rede | Um tablet não aceita entrada HDMI: ele não pode ser monitor da Pi. Abre o Chrome em `http://poto.local:8000`, carregando aplicação e API da **mesma origem**. Kiosk por fixação de tela do Android. | **Tela HDMI/touch acoplada à Pi**: daria contexto seguro de graça, mas não é o hardware disponível |
| **Mídia** | **Captura server-side na Pi** — `picamera2`/V4L2 + ALSA, transmitida em **MJPEG** | A câmera e o microfone estão na Pi, e a Pi é headless: nenhum navegador os enxerga. A captura vira código Python no backend. MJPEG é `<img src="…">` no painel — sem WebRTC, sem sinalização, sem STUN/TURN. | **Câmera do tablet via `getUserMedia`**: bloqueada sem HTTPS (ver §8). **H.264**: a Pi 5 não tem encoder por hardware |
| **Notificação** | **Registry de providers: `log`, `webhook`** | `log` para demo sem internet; `webhook` para WhatsApp real via Evolution API/n8n. Novos canais entram como um arquivo. | Twilio/SIMCom: hardware e crédito, ambos P2 |

**Sem** Redis, sem Celery, sem message broker, sem ORM, sem Kubernetes, sem microsserviços.

---

## 5. O que é reaproveitado do POTO antigo

Reaproveitar **não é copiar**: é portar deliberadamente o que provou valor.

### Portar quase intacto

| Ativo | Onde está | Por quê |
|---|---|---|
| **Sistema visual completo** | `../poto/DESIGN.md` (490 linhas) | Paleta, tipografia, curvas, escala de espaço, especificação de componentes, blueprint de layout da tela inicial. É o ativo mais valioso do projeto antigo. |
| **Tokens CSS** | `../poto/frontend/src/styles.css:3-22` | Valores hex/px exatos, já validados em tela |
| **Roteador determinístico** | `../poto/backend/app/router_engine.py` (79 linhas) | Tabela tipo × modo × horário → canal, fallback, gravidade, mensagem. Sem IA, testado, impecável. |
| **Modelo de domínio** | `../poto/backend/app/models.py` | Enums de trilha, modo, gravidade, status, origem |
| **Dataset de triagem** | `../poto/scripts/triagem_dataset.json` (77 exemplos) + `bench_dataset.json` (42 held-out) | É o que produz os 83%/86% |
| **Catálogo de canais** | `../poto/backend/app/config.py:150-174` | CSV, Sala Lilás, SAPSI, Ouvidoria, SAMU 192, PM 190, Bombeiros 193, Central 180 |

### Reescrever com a mesma linguagem visual

Componentes React equivalentes a `.choice`, `.panic`, `.status`, `.confirm`,
`.alerta-ativo`, `.screen-title` — mesmos tokens, mesmas medidas, sem o DOM imperativo.

### Deixar para trás

`agents/graph.py` (LangGraph/Ollama) · `simcom.py` · `voz.py` · `video.ts` · `voice.ts` ·
`chat.ts` · `audio.ts` · `server.ts` · providers Twilio/Telegram/SIMCom · `referencia/`.

---

## 6. Identidade visual — valores canônicos

Extraídos de `DESIGN.md §14` e `styles.css:3-22`. **Estes números vão literais para o
novo projeto.**

```css
/* cor */
--ink:#17150F;   --muted:#6F6862;  --faint:#9A938B;  --line:#E8E3DD;
--paper:#FBF9F6; --bg:#FFFFFF;
--rust:#C0392B;  --rust-d:#8F2A17; --rust-soft:#F6E7E3;
--crit:#C0392B;  --warn:#D68A2E;   --info:#9A938B;   --ok:#2F7D4F;
/* curva */
--r-xs:8px; --r-sm:10px; --r-md:14px; --r-lg:20px; --r-xl:28px; --r-pill:999px;
/* espaço (base 4) */
--space-xs:8px; --space-sm:12px; --space-md:16px; --space-lg:24px;
--space-xl:32px; --space-xxl:48px; --space-totem:64px;
/* tipografia */
--font-display:"Michroma", system-ui, sans-serif;   /* SÓ peso 400 existe */
--font-ui:"Inter", system-ui, sans-serif;
/* elevação / movimento / toque */
--shadow:0 1px 2px rgba(20,15,5,.05), 0 10px 30px rgba(20,15,5,.06);
--t-micro:120ms; --t-screen:240ms; --touch:64px;
```

**Regras que não se negociam:**

- **60/30/10** — ~60% papel, ~30% tinta, ~10% ferrugem. Ferrugem só em ação e alerta.
- **Michroma só tem peso 400.** Hierarquia vem de tamanho + tracking + caixa-alta.
  Nunca `font-weight: bold` sobre Michroma.
- **Alvos de toque ≥ 64px**; bordas de `1.5px` (não 1px); foco visível `outline: 3px --rust`.
- **Cor nunca é o único sinal** — gravidade sempre cor + rótulo + ícone.
- Ícones: **Material Symbols Rounded, FILL 0** — `stethoscope`, `shield`, `female`,
  `info`, `emergency`, `check`.
- **Fontes auto-hospedadas.** Nada de CDN: foi o que quebrou o offline do projeto antigo.

Medidas dos componentes principais (de `styles.css`):

| Componente | Especificação |
|---|---|
| `.choice` | `min-height:168px`, `padding:28px 16px`, borda `1.5px --line`, raio `--r-lg`, ícone 56px `--rust`, rótulo Michroma 13px `+.04em`; hover → borda `--rust` + fundo `--rust-soft`; active → `scale(.97)` |
| `.panic` | largura total, cápsula, `--rust`, `min-height:64px`, Michroma 14px UPPERCASE `+.1em`, ícone 32px branco |
| `.screen-title` | Michroma `clamp(28px,4.5vw,44px)`, peso 400, `line-height:1.05`, `-.02em`, centrado |
| `.grid` | 2×2, `gap:16px`; colapsa para 1 coluna < 560px |
| wordmark | Michroma 16px, `+.14em`, UPPERCASE, pontos em `--rust` |

---

## 7. Roadmap

```
       MVP                    Versão 2              Totem de Segurança         Totem de
   (este plano)                                          completo             Uso Geral
        │                         │                         │                     │
4 trilhas + pânico        Chat de texto            Voz (STT local)        Serviços da UFPI
Triagem ML local          Autenticação real        Vídeo ao vivo          Check-in/check-out
Roteamento + SLA          Métricas e gráficos      Evidência + LGPD       Controle de acesso
Painel tempo real         Frota multi-totem        Canal GSM/2G           Monitoramento
Offline + dreno           Auditoria completa       Hailo / edge TPU       Novos módulos
Kiosk na Pi 5             Retenção de dados        NOC central
```

O ponto de extensão é `app/api/` + `app/modulos/`: cada capacidade nova é um pacote com
seu próprio `APIRouter`, registrado em `main.py` por **uma linha**, reutilizando banco,
hub de WebSocket, configuração e canais. **O roteador determinístico e o merge protetivo
não dependem de módulo nenhum** — tudo que entra, entra *em volta* do núcleo de segurança,
nunca dentro dele.

---

## 8. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| **WiFi entre tablet e Pi cai** | Painel não acende em tempo real | A fila offline mantém o totem operante e drena ao reconectar (MVP-057/058). Na demo, roteador dedicado e não a rede do campus |
| **Altura de 530px em paisagem** no tablet de 8.7" | Tela inicial com rolagem | Grade muda para 4 colunas em paisagem curta; alvos ≥64px permanecem intocados (MVP-055) |
| **Contexto seguro perdido** (não é mais `localhost`) | Câmera/mic **do tablet** são inviáveis sem HTTPS | Contornado: o MVP usa só a câmera/mic **da Pi**, captura server-side, que não passa por navegador |
| **Pi 5 não tem encoder H.264 por hardware** | Vídeo em H.264 consumiria CPU da Pi | MJPEG na LAN: o ISP entrega JPEG quase de graça. Medir CPU em MVP-079 |
| **Câmera/mic sempre ligados** seriam abuso de privacidade | Risco legal e ético | Captura só inicia **sob demanda da central**, vinculada a chamado ativo, e cada ativação é auditada |
| Sem internet no local da demo | Webhook não demonstra | Plano B com `POTO_NOTIF_PROVIDER=log` projetado |
| Classificador com 77 amostras erra em gírias locais | Roteamento errado ao vivo | Suíte de regressão (MVP-025) + ampliar dataset (MVP-019) |
| Corte de energia durante a demo | Perda de dados | SQLite em WAL + `Restart=always` + cartão SD reserva |
| mDNS (`poto.local`) não resolve na rede do campus | Tablet não acha a Pi | IP estático como plano B; `install-pi.sh` imprime as duas URLs |

---

## 9. Definition of Done

O MVP está concluído quando **todos** forem verdadeiros:

1. `git clone` + `make setup` numa máquina limpa resulta em sistema funcional
2. `make test` passa 100%, incluindo a suíte de regressão de triagem
3. `GET /health` reporta honestamente o motor de triagem ativo
4. Nenhuma combinação de trilha + texto reduz a gravidade atribuída pelo roteador
5. "socorro", "estou desmaiando" e "to passando mal" roteiam para o canal correto
6. As 4 trilhas roteiam para CSV, Sala Lilás/180, SAMU/SAPSI e Ouvidoria
7. Trilha mulher: tela neutra, sem som, sem protocolo visível
8. Pânico dispara broadcast paralelo e aparece no painel em ≤ 3 s
9. Cabo de rede desconectado: acionamento funciona, fila enche, dreno não duplica
10. SLA expirado escalona automaticamente
11. `reboot` da Pi → API no ar em < 60 s; o tablet reconecta sozinho
12. Botão de pânico na tela → chamado no painel em ≤ 3 s, com broadcast paralelo
12b. Central abre a câmera da Pi num chamado ativo, vê imagem ao vivo, e a abertura e o
    fechamento aparecem na auditoria. Sem chamado ativo, o stream responde `403`
13. Zero requisições a domínios externos (fontes e ícones locais)
14. Tela inicial **sem rolagem** no Galaxy Tab A11 nas **duas orientações**, e em
    1280×800 no desktop, com alvos ≥ 64px em todos os casos
15. Roteiro de demo de 5 minutos executado 3× seguidas sem intervenção

---

## 10. Documentos

| Arquivo | Conteúdo |
|---|---|
| `PLAN.md` | Este documento — escopo, stack, roadmap |
| `ARCHITECTURE.md` | Arquitetura, decisões técnicas, API, banco, fluxos |
| `TASKS.md` | Todas as tasks do MVP com critérios de aceitação e status |
| `README.md` | Como configurar, executar e testar |
