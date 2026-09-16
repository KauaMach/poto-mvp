# Viewports do totem

> **Estado desta medição: DERIVADA, não medida.** Os números abaixo vêm de
> aritmética sobre a resolução física do aparelho, não de `window.innerWidth`
> lido nele. O critério da MVP-055 pede explicitamente o contrário — *"não
> projetar contra número suposto"* — e ele **continua em aberto** até alguém
> abrir a aplicação no Galaxy Tab A11 e preencher a tabela de baixo.
>
> A rota `/galeria` (desenvolvimento) mostra os valores reais no topo da página,
> justamente para que essa medição seja um passo e não um projeto.

## Por que isto importa

A tela do totem é um **Galaxy Tab A11 de 8,7"**, e o caso difícil não é a
largura — é a **altura em paisagem**. Sobram pouco mais de 500 px para
cabeçalho, título, quatro alvos de toque de 64 px e o botão de pânico. Projetar
a grade 2×2 nessa altura corta o rodapé, e o rodapé é onde está o pânico.

Um layout ajustado contra número errado falha de um jeito específico e ruim:
parece certo no DevTools e erra no aparelho, que é o único lugar onde importa.

## Derivação

Resolução física declarada: **1340 × 800**.

O navegador não usa pixels físicos: usa pixels de CSS, que são
`físico ÷ devicePixelRatio`. Para tablets Android desta faixa o DPR típico é
**1.5**.

| | físico | ÷ DPR 1.5 | menos barra do Chrome (~56 px) |
|---|---|---|---|
| paisagem | 1340 × 800 | **893 × 533** | 893 × ~477 |
| retrato | 800 × 1340 | **533 × 893** | 533 × ~837 |

Os ~530 px de altura em paisagem que a MVP-055 cita batem com essa conta, o que
sugere que o plano partiu da mesma derivação.

**O DPR é a incerteza.** Se for 2.0 em vez de 1.5, a paisagem cai para
670 × 400 — e aí a grade de 4 colunas com cartão de 120 px também não caberia.
É a razão de o critério pedir medição.

## Pontos de quebra implementados

Escolhidos por **altura disponível**, não por nome de dispositivo: uma regra
escrita contra "tablet" erra em qualquer aparelho que não seja aquele.

| condição | arranjo | cartão | ícone |
|---|---|---|---|
| default (retrato e desktop) | 2 × 2 | `min-height: 168px` | `xl` 56 px |
| `landscape` e `max-height: 620px` | **4 colunas** | `min-height: 120px` | `lg` 40 px |
| `max-width: 480px` | 1 coluna | `min-height: 140px` | `lg` 40 px |

O limite de 620 px cobre com folga os 533 derivados **e** os 400 do cenário de
DPR 2.0 — é o que faz o layout sobreviver ao número que ainda não medi.

**Alvos de toque nunca encolhem abaixo de 64 px.** O cartão baixa de 168 px
para 120 px, que continua quase o dobro do mínimo; o que dá o espaço é o ícone
menor e o `padding` reduzido, não o alvo.

## Tabela a preencher no aparelho

Abrir `/galeria` no Tab A11 e copiar os valores do topo da página:

| orientação | `innerWidth` | `innerHeight` | `devicePixelRatio` | rolagem? |
|---|---|---|---|---|
| retrato | | | | |
| paisagem | | | | |

Conferir também, no console:

```js
document.body.scrollHeight === window.innerHeight
```

Se for `false` na tela inicial, o layout está errado — `overflow: hidden`
esconde o problema em vez de resolvê-lo (MVP-049).
