# Visão e roadmap — P.O.T.O como plataforma

Este documento é diferente dos outros três que já existem, e a diferença importa:

| documento | responde |
|---|---|
| [`PLAN.md`](../PLAN.md) | o que **está** no escopo do MVP, fechado, e por quê |
| [`ARCHITECTURE.md`](../ARCHITECTURE.md) §9 | como o código **atual** se estende tecnicamente (novos módulos, mais totens, IA mais forte) |
| [`correcoes-e-melhorias.md`](correcoes-e-melhorias.md) | backlog **tático**: bugs e melhorias pontuais encontrados no que já existe |
| **este documento** | para onde o produto vai, em fases, e o que cada fase exige revisitar nas decisões da fase anterior |

Nada aqui é escopo do MVP. `CLAUDE.md` é explícito: *"nada marcado como P2 entra antes de
todo P0 estar verde"*. Este documento não muda essa regra — ele existe para que, quando o
MVP estiver verde e a conversa for "e agora, o que vem depois", a resposta não dependa de
lembrar de cabeça uma conversa de setembro de 2026.

---

## O que a sigla sempre quis dizer

**P.O.T.O. = Plataforma de Orientação, Triagem e Ouvidoria.** Não "totem" — a palavra nem
aparece na sigla. O totem físico é o **primeiro osso** da plataforma, não o corpo inteiro.
Isso já estava certo desde o nome; o que mudou foi perceber que o MVP, sendo o primeiro
passo, acabou fixando no código várias suposições que só valem para "um totem físico, uma
instituição, ninguém logado" — e essas suposições precisam ser revisitadas, não carregadas
para sempre, à medida que a plataforma cresce.

## As três fases

```
FASE 1 (agora)          FASE 2                      FASE 3
Totem físico       →    + App de celular       →    Plataforma institucional
UFPI, emergência        mesmo domínio,              tipo SaaS — múltiplas
urgência/emergência     origem também é             instituições, cada uma
                         o bolso da pessoa           com seu próprio catálogo
```

### Fase 1 — Totem físico (o MVP atual)

Uma instituição (UFPI), um totem por corredor, foco em urgência/emergência, ninguém precisa
se identificar para pedir ajuda. É o que [`TASKS.md`](../TASKS.md) descreve e o que está
sendo construído agora. Nada neste documento antecipa ou substitui esse escopo.

### Fase 2 — Aplicativo para o celular do usuário

O mesmo domínio — as quatro trilhas, o roteador determinístico, o merge protetivo — passa a
poder ser acionado também **do celular da pessoa**, não só de um aparelho fixo instalado
pela instituição.

### Fase 3 — Plataforma institucional (modelo SaaS)

Deixa de ser "o sistema da UFPI" e passa a ser algo que outras instituições adotam, cada
uma com seus próprios canais, contatos, fluxos de ouvidoria e equipe de central — no mesmo
espírito de produtos como a **JULIA** (assistente de IA do TJPI) ou os sistemas de **BO com
reconhecimento facial** usados por segurança pública: uma plataforma, não um projeto único.

---

## O que já aguenta essa direção, sem mudar nada agora

O núcleo de domínio já foi construído agnóstico de dispositivo, e isso não foi acidente:

- **O roteador e o merge protetivo não sabem que existe um totem.** `POST /eventos` recebe
  `totem_id` como só mais um identificador de origem. A regra central — *nenhuma
  informação nova pode reduzir a proteção já concedida* — não tem nada de específico de
  hardware. O mesmo payload vindo de um app em vez de um totem físico não muda em nada essa
  lógica.
- **`ARCHITECTURE.md` §9 já previa parte da extensão técnica**: `origem_acionamento` já
  reserva o valor `botao_fisico` para um botão de pânico via GPIO que ainda não existe, e o
  documento já nomeia "multi-totem" (trocar SQLite por Postgres quando passar de ~10
  totens) e "IA mais forte" (trocar o motor dentro de `triagem/` sem o resto do sistema
  saber) como extensões que **não exigem redesenho** — só troca de peça atrás da mesma
  fachada.
- **A fachada `triar()` e o registry de canais em `canais/`** já isolam a decisão de "qual
  IA" e "qual provider de notificação" do resto do sistema. Adicionar não é reescrever.

Importante não confundir duas coisas que parecem iguais e não são: o "multi-totem" que
`ARCHITECTURE.md` já prevê é **vários totens da mesma instituição** (UFPI com totens em
vários prédios). A Fase 3 deste documento é outra coisa — **várias instituições diferentes**
na mesma plataforma, cada uma com seu próprio catálogo de canais. A primeira já tem caminho
traçado; a segunda não existe ainda em lugar nenhum do código.

---

## O que não aguenta, e por que isso é esperado num MVP de fase 1

Três suposições hoje fixas no código, cada uma correta **para a Fase 1** e que precisa ser
revisitada nas fases seguintes:

### 1. Não existe conceito de instituição/tenant

Os canais (CSV, Sala Lilás, SAPSI, Ouvidoria, SAMU, PM, Bombeiros, Central 180) são uma
constante Python fixa em `backend/app/config.py`, e cada contato vem de **uma** variável de
ambiente — uma instituição, uma instância do processo. Não há coluna de organização em
nenhuma tabela (`chamados`, `notificacoes`, `midia_auditoria`, `estado_log`).

Para a Fase 3, isso precisa sair do código e virar dado: cada instituição com seu próprio
catálogo de canais, contatos, SLA e fuso horário, e uma coluna de tenant atravessando o
schema inteiro. É trabalho real, não um parâmetro a mais — mas o *formato* da tabela de
canais já existe (`CANAIS: dict[str, dict[str, str]]`); o que falta é ela deixar de ser uma
constante e passar a ser uma linha de banco por instituição.

### 2. Não existe conta de usuário — e isso foi decisão deliberada, não lacuna

`/eventos` e `/panico` são endpoints **abertos** de propósito: um totem em pânico não pode
falhar por autenticação (`ARCHITECTURE.md`, princípio de segurança). Isso funciona porque o
totem é um aparelho institucional fixo — importa que *alguém* tocou, não *quem*.

Um app de celular muda o cálculo. Ali provavelmente se **quer** saber quem é a pessoa — para
retorno de contato, para histórico, para uma ouvidoria formal que acompanha um caso ao longo
do tempo. Hoje não existe modelo de conta, sessão de usuário nem autenticação de cidadão em
lugar nenhum do sistema — só o token único e compartilhado do painel da central
(`POTO_PAINEL_TOKEN`, MVP-040), que autentica um operador institucional, não um cidadão.

A pergunta que a Fase 2 obriga a responder, e que não precisa ser respondida agora: o
acionamento de emergência pelo app continua **sem exigir login** (mesma garantia do totem —
socorro não pode esperar uma tela de senha), mas o que vem depois disso — acompanhamento,
histórico, ouvidoria com retorno — pode exigir conta. São dois modelos de confiança
coexistindo no mesmo app, e isso é desenho de produto, não só de segurança.

### 3. O modo discreto resolve uma ameaça específica, que pode não ser a mesma no celular

A trilha "Assédio / Sala Lilás" é discreta porque o modelo de ameaça do totem é *"alguém
pode estar olhando a tela por cima do ombro, num espaço público"*. Num celular pessoal, essa
ameaça específica em geral não existe — mas outra pode: alguém que revista o aparelho da
vítima depois. É a mesma intenção de proteção, mas a UI que resolve uma ameaça não resolve a
outra automaticamente. Vale desenhar de novo, não portar direto.

---

## A tensão que vale nomear cedo: o lugar da IA

A decisão de **não** usar LLM na triagem (`PLAN.md §4`) foi justificada por uma medição
específica de hardware: os modelos que cabem numa Raspberry Pi 5 davam 29–45% de acurácia em
~6 segundos, contra 83–86% em 3,3 ms com TF-IDF + Regressão Logística. Essa medição é sobre
**rodar na Pi**, embarcado, sem rede.

Numa Fase 3 em nuvem — não mais um dispositivo embarcado — essa restrição **deixa de se
aplicar**. Faz sentido, então, perguntar se um assistente conversacional de verdade (no
espírito da JULIA do TJPI) volta a fazer sentido nas camadas de app e de central, mesmo que
o totem físico **continue** com o roteador determinístico — que é mais rápido, 100% offline
e mais previsível sob a pressão de uma emergência, e por isso não deveria ser substituído
ali de qualquer forma.

Ou seja: a resposta não é "LLM sim" ou "LLM não" para o produto inteiro — é **por camada**.
O totem physical continua determinístico porque emergência não pode depender de rede nem de
uma resposta de IA que varia. Um chat de orientação geral no app ou na central, sem pressão
de segundos, é um contexto diferente onde a mesma restrição não se aplica.

---

## O que este documento não é

- **Não é uma lista de tasks.** Quando uma dessas fases for de fato priorizada, os itens
  concretos entram no `TASKS.md` com critério de aceitação, do mesmo jeito que qualquer
  outra task.
- **Não muda a regra de `CLAUDE.md`** de que nada de P2 entra antes de todo P0 estar verde.
- **Não é uma promessa de prazo.** É contexto para decisão futura, escrito enquanto a
  conversa que o gerou ainda está fresca — o valor dele é não ter que reconstruir esse
  raciocínio do zero daqui a alguns meses.

Quando a Fase 2 for iniciada de verdade, o primeiro passo é abrir uma seção nova aqui com o
que foi decidido sobre autenticação de cidadão — porque é a decisão da qual praticamente
tudo o resto da fase depende.
