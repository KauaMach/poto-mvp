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
| [COR-001](#cor-001--pânico-não-deveria-acionar-a-sala-lilás-automaticamente) | Pânico não deveria acionar a Sala Lilás automaticamente | Correção | Alta | ✅ **Implementado** (18/09) |
| [MEL-001](#mel-001--canal-de-vídeo-bidirecional-da-central-para-o-totem) | Canal de vídeo bidirecional da central para o totem | Melhoria | A discutir | Proposto |
| [MEL-002](#mel-002--pré-requisito-de-mel-001-servir-a-aplicação-por-https) | Pré-requisito de MEL-001: servir a aplicação por HTTPS | Melhoria | A discutir | Proposto |
| [MEL-003](#mel-003--rota-explícita-totem-em-vez-de-a-raiz-ser-o-totem-por-padrão) | Rota explícita `/totem`, em vez de a raiz ser o totem por padrão | Melhoria | Média | Proposto |

---

## COR-001 — Pânico não deveria acionar a Sala Lilás automaticamente

**Tipo:** Correção · **Prioridade sugerida:** Alta · **Levantado por:** Kaua, 18/09
**Status:** ✅ **Implementado em 18/09.** `CANAIS_INTERNOS = ["csv"]`. Ver a nota da
MVP-031 no [`TASKS.md`](../TASKS.md) e a correção de estimativa no fim desta entrada.

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
| `backend/tests/test_api_panico.py` | 6 testes quebraram (ver correção de estimativa abaixo) |
| outros 4 arquivos de teste | `test_config.py`, `test_api_chamados.py`, `test_api_contrato.py`, `test_api_dreno.py` — **eu não os havia mapeado** |

### O que não muda

- **A trilha "Assédio / Sala Lilás" continua acionando a Sala Lilás normalmente** —
  essa é a via correta para esse caso, e ela já existe.
- **`escalonamento_disponivel`** (os 4 botões de autoridade externa na tela de alerta
  — PM, SAMU, Bombeiros, Central 180) não muda: continuam manuais, continuam os
  mesmos quatro.
- O pânico continua acionando **o CSV**, que é segurança geral e faz sentido para
  qualquer emergência dentro do campus.

### Correção de estimativa — eu errei o impacto nos testes

Quando escrevi esta entrada, listei **4 testes** em `test_api_panico.py` como o impacto.
Ao implementar, quebraram **10**, em **5 arquivos**:

| arquivo | quantos | o que afirmavam |
|---|---|---|
| `test_api_panico.py` | 6 | nome legível dos dois canais · barreira de paralelismo com 2 vagas · contenção de falha entre dois canais · três contagens fixas em `== 2` |
| `test_config.py` | 1 | `CANAIS_INTERNOS == ["csv", "sala_lilas"]` — a asserção canônica da lista, que eu esqueci que existia |
| `test_api_chamados.py` | 1 | o detalhe do chamado traz duas notificações |
| `test_api_contrato.py` | 1 | `len(resultados) == 2` no ciclo completo do pânico |
| `test_api_dreno.py` | 1 | `len(resultados) == 2` no pânico drenado da fila offline |

Dois deles — o de paralelismo (`asyncio.Barrier(2)`) e o de contenção de falha — não
podiam ser simplesmente "corrigidos para um canal": **com um canal não existe paralelismo
nem contenção a observar.** Passaram a injetar um segundo canal por `monkeypatch`, o que
protege o mecanismo (a lista é configuração; uma instituição pode ter dois) sem fingir que
o padrão tem dois.

As contagens fixas em `== 2` foram trocadas por `len(config.CANAIS_INTERNOS)`: era o
número literal que as tornou frágeis, e deixá-lo lá só adiaria o mesmo problema.

**Lição para as próximas entradas deste documento:** procurar a constante em todo o
`tests/`, não só no arquivo óbvio da feature. `grep -rn CANAIS_INTERNOS tests/` teria
mostrado o `test_config.py` em um segundo.

### Três testes novos, que a correção exigiu

- `test_panico_nao_aciona_a_sala_lilas` — a garantia dita de forma **positiva**. O teste
  que compara com `config.CANAIS_INTERNOS` continuaria passando se alguém devolvesse a
  Sala Lilás à lista; este falha.
- `test_trilha_mulher_continua_acionando_a_sala_lilas` — o par necessário. Sem ele,
  "a Sala Lilás nunca é acionada" passaria, e isso seria regressão grave, não correção.
- `test_sala_lilas_segue_no_catalogo_e_com_contato` — tirá-la do pânico não é tirá-la do
  sistema.

Verificado por mutação nas duas direções: devolver a Sala Lilás ao broadcast quebra 3
testes; fazer a trilha `mulher` deixar de apontar para ela quebra 1.

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

## MEL-003 — Rota explícita `/totem`, em vez de a raiz ser o totem por padrão

**Tipo:** Melhoria · **Prioridade sugerida:** Média · **Levantado por:** Kaua, 18/09

### Comportamento atual

A interface do totem vive na **raiz** (`http://RaspPoto.local:8000/`), e a central em
`/painel`. As duas rotas não são simétricas — uma é explícita, a outra é "o que sobra":

```tsx
// frontend/src/App.tsx — rotaAtual()
function rotaAtual(): Rota {
  const caminho = window.location.pathname.replace(/\/+$/, "");
  if (caminho === "/painel") return "painel";
  if (caminho === "/galeria" && import.meta.env.DEV) return "galeria";
  return "totem";  // ← qualquer coisa que não seja /painel nem /galeria
}
```

**Consequência que vale registrar:** por causa desse `return "totem"` no fim, a rota
`/totem` **já responde com a interface do totem hoje**, sem nenhuma mudança de código —
só que por acidente, do mesmo jeito que `/qualquer-coisa` também responde. Não é uma rota
intencional; é o que sobra depois de descartar `/painel` e `/galeria`. `app/main.py`
reforça isso no fallback de SPA: qualquer caminho fora de `/api` cai no `index.html`, e é
o `App.tsx` quem decide o que mostrar.

### O que fazer

Tornar `/totem` uma rota **verificada explicitamente**, no mesmo padrão de `/painel`:

```tsx
if (caminho === "/totem") return "totem";
```

E decidir o que acontece na **raiz** depois disso — esta é a parte que precisa de decisão,
não só de código:

- **Opção A — redireciona `/` para `/totem`.** Atalhos e tablets já fixados na raiz
  (ver `docs/setup-tablet.md`) continuam funcionando sem reconfiguração.
- **Opção B — a raiz para de ser o totem.** Fica livre para uso futuro (uma tela de
  entrada, por exemplo, se um dia existirem mais tipos de cliente). Quebra qualquer
  tablet já fixado na raiz até ser reconfigurado para `/totem`.
- **Opção C — as duas continuam respondendo,** raiz e `/totem` mostrando o totem, sem
  redirecionamento. Mais simples, mas mantém a assimetria que motivou o item.

Recomendação: **Opção A** — resolve a assimetria com `/painel` sem quebrar nenhum tablet já
configurado, e deixa a porta aberta para a Opção B mais adiante, quando (e se) fizer
sentido usar a raiz para outra coisa.

### Onde mexer

| arquivo | o quê |
|---|---|
| `frontend/src/App.tsx` | `rotaAtual()` passa a checar `/totem` explicitamente; decidir o que a raiz faz (ver opções acima) |
| `backend/tests/test_main.py` | `test_raiz_serve_a_aplicacao` e o parametrizado `test_rotas_da_aplicacao_recebem_o_index` testam hoje que **qualquer** caminho (inclusive a raiz) devolve o `index.html` da SPA — isso não muda no backend, ele continua servindo o mesmo arquivo para tudo fora de `/api`. O que muda é o que o `App.tsx` decide fazer com o caminho depois de carregado; vale acrescentar um teste de que `/totem` monta explicitamente o componente `Totem`, e não só "cai lá por eliminação" |
| `docs/setup-tablet.md` | a URL do atalho fixado no tablet passa a ser `http://RaspPoto.local:8000/totem` (ou o IP equivalente) — hoje o documento aponta pra raiz |
| `docs/roteiro-teste.md` | as referências a `` `/` `` como a rota do totem (tabela de telas, o passo "Abra `/`" do roteiro) passam a apontar para `/totem` |
| `frontend/scripts/verificar-discreto.mjs` e `verificar-midia.mjs` | não usam rota nenhuma (renderizam componente direto via `react-dom/server`) — não são afetados |

### O que não muda

- A interface da **central continua em `/painel`**, sem nenhuma alteração — o pedido foi
  explícito sobre isso.
- `/galeria` continua existindo só em desenvolvimento, do mesmo jeito.
- Nenhuma mudança de backend: `app/main.py` já serve o mesmo `index.html` pra qualquer
  caminho fora de `/api`, e essa parte está certa como está.

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
