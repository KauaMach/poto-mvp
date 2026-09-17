# Correções e melhorias — backlog pós-MVP

Este documento é diferente do [`TASKS.md`](../TASKS.md). Lá estão as 82 tasks que
**definem o escopo do MVP** — o que precisa existir para a demonstração. Aqui ficam
**candidatos a correção ou melhoria** encontrados depois: em testes, em uso real na
Pi, ou levantados pelo Kaua durante a revisão. Nada aqui é implementado
automaticamente — é registro para virar task quando for priorizado.

Quando um item daqui for aprovado para entrar no escopo, ele vira uma task normal
com ID `MVP-0XX` no `TASKS.md`, com critérios de aceitação. O ID usado aqui (`COR-`
ou `MEL-`) fica como referência cruzada.

**Legenda de status:** `Proposto` · `Aprovado — vira task` · `Rejeitado` (com motivo)
**Tipo:** `Correção` (o sistema faz algo errado) · `Melhoria` (o sistema funciona, mas
poderia fazer mais ou melhor)

---

## Resumo

| ID | Item | Tipo | Prioridade sugerida | Status |
|---|---|---|---|---|
| [COR-001](#cor-001--pânico-não-deveria-acionar-a-sala-lilás-automaticamente) | Pânico não deveria acionar a Sala Lilás automaticamente | Correção | Alta | Proposto |
| [MEL-001](#mel-001--canal-de-vídeo-bidirecional-da-central-para-o-totem) | Canal de vídeo bidirecional da central para o totem | Melhoria | A discutir | Proposto |
| [MEL-002](#mel-002--pré-requisito-de-mel-001-servir-a-aplicação-por-https) | Pré-requisito de MEL-001: servir a aplicação por HTTPS | Melhoria | A discutir | Proposto |

---

## COR-001 — Pânico não deveria acionar a Sala Lilás automaticamente

**Tipo:** Correção · **Prioridade sugerida:** Alta · **Levantado por:** Kaua, 18/09

### Comportamento atual

O botão de pânico do totem (`POST /panico`) aciona **dois canais em paralelo, sempre**:

```python
# backend/app/config.py
CANAIS_INTERNOS = ["csv", "sala_lilas"]
```

```python
# backend/app/api/eventos.py — _acionar_em_paralelo()
canais_internos = list(config.CANAIS_INTERNOS)
retornos = await asyncio.gather(
    *(canais.notificar(chamado, canal) for canal in canais_internos),
    return_exceptions=True,
)
```

Todo pânico — não importa o motivo — soa ao mesmo tempo para o **CSV/PREUNI**
(segurança patrimonial da UFPI) e para a **Sala Lilás** (atendimento a assédio e
violência contra a mulher).

### Por que isso é um problema

O botão de pânico é genérico: *"preciso de ajuda agora"*. Pode ser um assalto, uma
emergência médica, uma briga, um princípio de incêndio, alguém passando mal —
**nenhum texto acompanha o pânico** (`_registro_panico` fixa `texto_livre=None` de
propósito), então o sistema não tem nenhum sinal de que o caso é sobre violência de
gênero.

Acionar a Sala Lilás automaticamente em **todo** pânico:

- **desperdiça um recurso especializado e de capacidade limitada** em casos que não
  são da alçada dela, atrasando a resposta dela no caso em que a situação for
  realmente de violência de gênero;
- **pode confundir a equipe que atende.** Ela recebe uma notificação de pânico sem
  nenhum contexto e pode mobilizar presumindo assédio, quando o caso é outro;
- **é redundante com uma trilha que já existe para isso.** A trilha *"Assédio / Sala
  Lilás"* do totem já aciona a Sala Lilás especificamente, em modo discreto
  (`app/triagem/roteador.py`, `TipoOcorrencia.mulher`) — quem precisa desse canal já
  tem um caminho dedicado e mais apropriado (a tela não denuncia o que foi acionado).

O pânico acionando a Sala Lilás por padrão não cobre uma lacuna: ele **duplica** o
que a trilha dedicada já resolve melhor, e ainda paga o custo de mobilizar o canal
errado nos outros casos.

### Onde mexer

| arquivo | o quê |
|---|---|
| `backend/app/config.py` | `CANAIS_INTERNOS` deixa de incluir `"sala_lilas"` |
| `backend/app/api/eventos.py` | nenhuma mudança de lógica — `_acionar_em_paralelo` já itera sobre `CANAIS_INTERNOS`, então tirar o canal da lista basta |
| `backend/tests/test_api_panico.py` | **4 testes afirmam o comportamento atual e quebrariam**: `test_os_dois_canais_internos_sao_acionados`, `test_resultados_trazem_os_dois_canais`, `test_resultados_trazem_o_nome_legivel` (espera `{"CSV / PREUNI", "Sala Lilás"}`), `test_falha_de_um_canal_nao_impede_o_outro` (espera dois canais nos resultados). Precisam ser reescritos para refletir só o CSV — e vale manter um teste que prove que a Sala Lilás **não** é chamada, para a garantia ficar explícita e não apenas ausente |

### O que não muda

- **A trilha "Assédio / Sala Lilás" continua acionando a Sala Lilás normalmente** —
  essa é a via correta para esse caso, e ela já existe.
- **`escalonamento_disponivel`** (os 4 botões de autoridade externa na tela de alerta
  — PM, SAMU, Bombeiros, Central 180) não muda: continuam manuais, continuam os
  mesmos quatro.
- O pânico continua acionando **o CSV**, que é segurança geral e faz sentido para
  qualquer emergência dentro do campus.

### Alternativa considerada e não recomendada

Manter os dois canais, mas deixar que o CSV (humano, no local) decida se aciona a
Sala Lilás. Rejeitada como primeira escolha porque a Sala Lilás já é acionável pela
trilha dedicada — manter o pânico chamando os dois só reintroduz o problema por
outro caminho, com a diferença de que agora depende de alguém lembrar de repassar.

---

## MEL-001 — Canal de vídeo bidirecional da central para o totem

**Tipo:** Melhoria · **Prioridade sugerida:** a discutir · **Levantado por:** Kaua, 18/09

### A ideia

Quando a central abre a câmera de um chamado ativo (MVP-078), ela só **recebe**
vídeo — vê o corredor pela câmera da Pi. A pergunta é se dá para inverter também: a
central **mostrar sua própria câmera na tela do totem**, para estabelecer um canal de
comunicação direto — o operador aparecendo ao vivo para quem está pedindo ajuda,
como uma chamada de vídeo.

### Resposta curta

Tecnicamente plausível e desejável, mas **é um recurso novo, não um ajuste** — do
tamanho de várias tasks da Fase 8b somadas — e **está bloqueado por uma decisão de
arquitetura que precisa ser tomada antes** (ver MEL-002). Não é "só ligar o
microfone ao contrário".

### Por que não é simples

**1. Hoje o caminho é de mão única, por desenho.** A câmera e o microfone que a
central vê são capturados **no servidor** (`picamera2`/V4L2 e ALSA, na própria Pi) —
não no navegador de ninguém. É por isso que funciona sem WebRTC: o Python já tem o
hardware em mãos e serve MJPEG puro (`ARCHITECTURE.md`, `PLAN.md §6`). A câmera do
**operador** está no PC dele, não na Pi — o servidor não tem acesso a ela. Capturá-la
exige o **navegador** do operador, com `getUserMedia`.

**2. `getUserMedia` exige contexto seguro, e o sistema roda em HTTP puro.** Por
decisão deliberada do projeto (evitar TLS/certificados numa demonstração em rede
local — `PLAN.md §8`), a aplicação inteira serve em `http://`, nunca `https://`. Os
navegadores só liberam `getUserMedia` em **contexto seguro**: HTTPS, ou
`localhost`/`127.0.0.1`. A tela da central roda em `http://<ip-da-pi>:8000/painel`,
que não é nem uma coisa nem outra — **o navegador recusaria o pedido de câmera do
operador antes mesmo de qualquer código deste projeto rodar.** Ver [MEL-002](#mel-002--pré-requisito-de-mel-001-servir-a-aplicação-por-https).

**3. WebRTC foi explicitamente deixado de fora do escopo do MVP.** O `PLAN.md` lista
"WebRTC P2P" entre o que foi cortado por complexidade, e o `TASKS.md` classifica
"Mídia avançada (WebRTC P2P, gravação, monitoramento oculto)" como **P2 — fora do
MVP**. Um canal bidirecional de vídeo de verdade normalmente se constrói com WebRTC
(sinalização + ICE/STUN, opcionalmente TURN). Reabrir esse escopo é uma decisão de
projeto, não um detalhe de implementação.

### Dois caminhos possíveis, se for adiante

**Caminho A — Retransmissão de quadros, no mesmo estilo do que já existe.**
Consistente com a filosofia atual (MJPEG sobre HTTP simples, sem sinalização):

- o navegador da central captura a própria câmera com `getUserMedia` e desenha
  quadros num `<canvas>` a alguns fps;
- envia cada quadro por `POST` (ex.: `POST /midia/central/{chamado_id}/quadro`);
- o backend guarda o quadro mais recente em memória (o mesmo padrão de `_Captura`
  de `camera.py`) e serve como MJPEG num novo
  `GET /midia/central/{chamado_id}/stream`;
- o totem consome isso num `<img>`, do mesmo jeito que a central hoje consome a
  câmera da Pi.

Prós: nenhuma biblioteca nova, mesma arquitetura, mesmo modelo mental. Contras: não
é uma chamada de vídeo de verdade — é uma sequência de fotos a poucos fps, com
atraso maior que vídeo ao vivo. Ainda **exige resolver o bloqueio de contexto
seguro** (item 2 acima), porque `getUserMedia` roda no navegador do operador de
qualquer forma.

**Caminho B — WebRTC de verdade.** Vídeo e áudio full-duplex, latência baixa,
experiência de chamada de verdade. Precisa de um canal de sinalização (o hub de
WebSocket que já existe poderia carregar SDP/ICE) e, dependendo da rede,
possivelmente um servidor TURN. É o esforço maior dos dois, mas é o que de fato
entrega "chamada de vídeo". Também depende de resolver o contexto seguro — a
exigência do navegador é a mesma para `getUserMedia` em WebRTC.

**Nos dois caminhos, o pré-requisito é o mesmo: [MEL-002](#mel-002--pré-requisito-de-mel-001-servir-a-aplicação-por-https).**

### Considerações que vão além da engenharia

- **Áudio.** Um vídeo sem áudio da central conversando é comunicação pela metade.
  Precisa de um canal de áudio simétrico (o totem já tem microfone? hoje não — só a
  Pi captura áudio, para a central ouvir).
- **Privacidade do operador.** Diferente de captar a Pi (equipamento institucional
  fixo, já sob aviso de auditoria), aqui é a câmera **pessoal** do operador. Vale
  decidir se isso é opt-in por chamado, e como fica registrado na auditoria de mídia
  (a MVP-077 audita "quem olhou a câmera de quem" — aqui seria "quem apareceu na tela
  de quem", e o rastro tem que ser igualmente honesto).
- **O totem é o Galaxy Tab A11 do corredor.** Mostrar vídeo ao vivo ali significa
  competir por CPU e banda com o que o totem já faz (acionar chamados, mostrar
  status). Vale medir antes de assumir que cabe.

---

## MEL-002 — Pré-requisito de MEL-001: servir a aplicação por HTTPS

**Tipo:** Melhoria · **Prioridade sugerida:** a discutir · **Depende de:** nada ·
**Bloqueia:** MEL-001

### O problema

O projeto serve tudo em `http://` por decisão deliberada — simplicidade de
demonstração numa rede local, sem certificado para gerenciar (`PLAN.md §8`). Isso é
correto para o que o MVP faz hoje: nenhuma tela usa `getUserMedia`, `getDisplayMedia`
nem qualquer API que exija contexto seguro.

MEL-001 muda isso: captar a câmera do operador **no navegador dele** exige contexto
seguro, e a tela da central não roda em `localhost` (ela é acessada de outro
computador, pela rede, usando o IP ou o nome mDNS da Pi).

### Caminhos possíveis

| opção | o que exige | contras |
|---|---|---|
| **TLS autoassinado** (ex.: via Caddy na frente do uvicorn, ou `mkcert`) | gerar e distribuir o certificado para os aparelhos confiarem nele | mais uma peça de infraestrutura para manter; "aceitar certificado não confiável" é atrito na primeira vez em cada aparelho |
| **A central rodar só em `localhost`** | nada de certificado | impraticável — a central é operada de um computador separado da Pi, não do próprio servidor |
| **Um app nativo para o operador**, fora do navegador | maior esforço de desenvolvimento | contorna a regra do navegador por completo, mas é um cliente novo para manter |

Nenhuma é trivial, e a escolha aqui **decide o teto do MEL-001**. Vale registrar como
decisão separada antes de estimar o esforço de MEL-001 inteiro.

---

## Como usar este documento

1. Ao encontrar um problema ou uma ideia de melhoria fora do escopo do MVP corrente,
   acrescente uma entrada aqui — não pule direto para o código.
2. Toda entrada tem: o que é hoje, por que incomoda ou por que ajudaria, onde no
   código isso vive, e o que precisaria mudar (inclusive testes que quebrariam).
3. Quando for priorizada, vira task numerada no `TASKS.md`, com os critérios de
   aceitação de lá — e esta entrada é marcada `Aprovado — vira task MVP-0XX`.
4. Se for descartada, marca-se `Rejeitado` com o motivo, para não ser reaberta sem
   contexto.
