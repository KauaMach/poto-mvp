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
| [MEL-001](#mel-001--videochamada-da-central-para-o-totem-durante-o-pânico) | Videochamada da central para o totem, durante o pânico | Melhoria | Alta (pós-MVP) | Proposto |
| [MEL-002](#mel-002--https-só-necessário-para-o-caminho-b-da-mel-001) | HTTPS: só necessário para o Caminho B da MEL-001 | Melhoria | Baixa | Proposto |
| [MEL-003](#mel-003--rota-explícita-totem-em-vez-de-a-raiz-ser-o-totem-por-padrão) | Rota explícita `/totem`, em vez de a raiz ser o totem por padrão | Melhoria | Média | ✅ **Implementado** (18/09) |

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

## MEL-001 — Videochamada da central para o totem, durante o pânico

**Tipo:** Melhoria · **Prioridade sugerida:** Alta (pós-MVP) · **Levantado por:** Kaua, 18/09

> **Esta entrada foi reescrita em 18/09.** A primeira versão concluía que o recurso estava
> *bloqueado* por HTTPS. **Estava errada** — a conclusão vinha de eu ter assumido que a
> câmera do operador só poderia ser capturada pelo navegador dele. Não é o caso. A análise
> corrigida está abaixo; o erro fica registrado porque foi ele que quase enterrou uma ideia
> viável.

### O fluxo que se quer

1. A pessoa aperta o **pânico** no totem.
2. A central recebe o alerta (já acontece hoje, por WebSocket, em ~200 ms).
3. O operador decide e clica em **"Iniciar videochamada"**.
4. **O rosto do operador aparece na tela do totem** — a pessoa vê e ouve alguém.

O objetivo não é vigilância nem diagnóstico: é **a pessoa não se sentir sozinha** enquanto
o socorro não chega. Isso importa para o desenho, porque muda o que é "bom o suficiente":
não precisa ser 30 fps em HD; precisa ter um rosto humano e uma voz.

### O que já existe, e é metade do caminho

O sistema **já faz o sentido inverso**. Desde a MVP-073/078, o operador vê e ouve a pessoa,
pela câmera e microfone da Pi, sob sessão auditada.

```
HOJE:      Pi (câmera/mic) ──MJPEG/WAV──> central      ✅ funciona e está medido
FALTANDO:  central (webcam) ─────────────> totem
```

E o desenho pedido **espelha exatamente** o que já está construído:

| hoje (MVP-077/078) | a videochamada |
|---|---|
| operador clica "Ver câmera" | operador clica "Iniciar videochamada" |
| `POST /chamados/{id}/midia` → sessão | `POST /chamados/{id}/chamada` → sessão |
| Pi → central | central → totem |
| sessão expira em 10 min, auditada | **a mesma** máquina de sessão e auditoria |

Ou seja: a MVP-077 (sessão + auditoria + expiração) é reaproveitada **inteira**, invertendo
só a direção do fluxo. E a tela onde o vídeo apareceria — o **alerta ativo** — já existe,
já fica aberta durante todo o pânico e já tem WebSocket ligado.

### A assimetria que destrava tudo, e que eu havia perdido

| | precisa de contexto seguro (HTTPS)? |
|---|---|
| **Capturar** câmera/mic no navegador (`getUserMedia`) | **Sim** |
| **Tocar** vídeo/áudio (`<img>`, `<audio>`, `<video>`) | **Não** — funciona em HTTP puro |

**O totem só precisa tocar.** Ele não captura nada — a Pi já captura a pessoa. Então
**o lado do totem não tem bloqueio nenhum**: é o mesmo `<img>` de MJPEG que a central já
usa hoje, na direção inversa.

O bloqueio existe **só** para capturar a câmera do operador. E aí está o erro da primeira
versão desta entrada: eu assumi que isso teria que ser no navegador dele.

### Dois caminhos para a captura na central

**Caminho A — agente local na máquina da central. Não precisa de HTTPS.**

Um programa pequeno rodando na mesa da central (como o `picamera2` roda na Pi) captura a
webcam do operador e envia os quadros por HTTP para a Pi, que retransmite em MJPEG. Não
usa `getUserMedia`, não usa WebRTC, não precisa de certificado.

É **a mesma filosofia que o projeto já adotou**: captura fora do navegador, transporte em
MJPEG simples (`PLAN.md §4`, decisão de mídia). O custo é instalar algo na máquina da
central — um computador institucional e controlado, o que é bem menos invasivo que
provisionar certificado em cada tablet.

**Caminho B — `getUserMedia` no navegador do operador.** Nada para instalar na central, e
abre a porta para WebRTC de verdade (full-duplex, latência baixa) depois. **Este** é o que
exige [MEL-002](#mel-002--https-só-necessário-para-o-caminho-b-da-mel-001).

Recomendação: **Caminho A**, por não exigir HTTPS nem tocar em nada que já funciona (o
kiosk em tela cheia do tablet, por exemplo, é sensível a certificado autoassinado).

### Decisões de produto que precedem o código

- **Um sentido ou dois?** A pessoa precisa **ser vista** pelo operador nessa chamada, ou
  basta ela **ver e ouvir** o operador? Se um sentido bastar, o trabalho cai bastante — e o
  outro sentido **já existe** (a central já vê e ouve a pessoa pela Pi). Para "me sentir
  mais segura", suspeito que ver alguém do outro lado já resolva.
- **Áudio.** Rosto sem voz é comunicação pela metade. O áudio do operador segue o mesmo
  caminho do vídeo; o áudio da pessoa **já chega** à central hoje.
- **Privacidade do operador.** Diferente da câmera da Pi (equipamento institucional fixo,
  sob aviso), aqui é a câmera **pessoal** de quem atende. A auditoria da MVP-077 registra
  "quem olhou a câmera de quem" — aqui seria "quem apareceu na tela de quem", e o rastro
  tem que ser igualmente honesto. Vale ser opt-in por chamado.
- **O totem é um Galaxy Tab A11 de 8,7".** Tocar vídeo ao vivo ali compete com o que ele já
  faz. A MVP-079 mediu o custo do outro sentido (2,5% de CPU na Pi); o custo **no tablet**
  não foi medido.

### Por que fica para depois do MVP

Não por bloqueio — isso foi retirado. Por **tamanho**: agente novo na central, endpoints
novos, player novo na tela de alerta, áudio, e a trilha de auditoria do lado do operador.
É o volume de várias tasks da Fase 8b somadas, e o MVP fecha antes disso.

---

## MEL-002 — HTTPS: só necessário para o Caminho B da MEL-001

**Tipo:** Melhoria · **Prioridade sugerida:** Baixa · **Depende de:** nada ·
**Bloqueia:** apenas o **Caminho B** da MEL-001 (não a MEL-001 inteira)

> **Corrigido em 18/09.** Esta entrada dizia "pré-requisito de MEL-001" e "bloqueia
> MEL-001". Não bloqueia: o Caminho A da MEL-001 (agente local na central) dispensa HTTPS
> por completo. HTTPS só é necessário se a captura for feita **no navegador** do operador.

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
**Status:** ✅ **Implementado em 18/09, pela Opção A** (raiz redireciona). Ver
"Como ficou", no fim desta entrada.

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

### Como ficou

- **`frontend/src/rotas.ts` (novo)** — `rotaAtual(caminho, dev)` saiu do `App.tsx` para um
  módulo próprio. Duas razões: um módulo que exporta componente **e** função perde o fast
  refresh do Vite (mesmo motivo de `retorno.ts` e `statusAlerta.ts`), e receber o caminho
  como **argumento** em vez de ler `window.location` por dentro a torna verificável sem
  navegador.
- **`/totem` é checado explicitamente**, no mesmo padrão de `/painel`. O fallback para o
  totem **ficou**, e agora é deliberado: num aparelho de corredor, uma URL digitada errado
  deve terminar na tela de pedir ajuda, não num 404.
- **`GET /` devolve 307 para `/totem`**, no backend. Redirect no servidor e não
  `location.replace` no cliente: não há piscada antes do JavaScript carregar, e funciona
  mesmo que o bundle falhe. Registrado **antes** do `_montar_frontend`, porque o estático é
  montado em `/` e casaria com a rota — no Starlette a ordem de registro é a ordem de
  resolução.
- **307 e não 301.** Um permanente fica gravado no navegador e em cada tablet, e voltar
  atrás exigiria limpar o cache de aparelho por aparelho. As opções B e C acima continuam
  abertas; um 301 as fecharia para economizar um salto de HTTP.
- **`manifest.webmanifest`**: `start_url` passou a `/totem`. O `scope` **fica em `/`** de
  propósito — ele precisa cobrir a raiz para que o redirect aconteça *dentro* do app
  instalado, sem abrir o Chrome por sair do escopo.
- **`docs/setup-tablet.md` e `docs/roteiro-teste.md`** atualizados. O documento do tablet
  diz explicitamente que um aparelho já configurado na raiz **não precisa ser refeito**.

### O teste que a MEL-003 exigiu, e por que ele olha o código-fonte

`frontend/scripts/verificar-rotas.mjs` (novo, entra no `npm run lint`): 12 casos de
caminho → rota, nos dois valores de `dev`.

Só que há uma armadilha aqui, e vale registrar: **apagar a linha
`if (limpo === CAMINHO_TOTEM)` não muda saída nenhuma** — o fallback devolve `"totem"` de
qualquer jeito. Um teste que só compare entrada e saída passaria com a correção desfeita.
O que distingue uma rota explícita de um fallback é o código, não o resultado. Então o
script tem uma asserção sobre **a fonte** de `rotas.ts`, e diz isso abertamente em vez de
fingir que a saída prova. Ele também confere que `CAMINHO_TOTEM` não divergiu do caminho
para onde o backend redireciona.

Verificado por mutação: apagar a checagem explícita quebra 1 verificação; divergir o
`CAMINHO_TOTEM` quebra 1; remover o redirect quebra 3 testes de backend; trocar 307 por
301 quebra 2.

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
