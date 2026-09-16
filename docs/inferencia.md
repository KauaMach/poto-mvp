# Inferência: por que um classificador, e não um LLM

> Registro das medições que sustentam a decisão D3 de [ARCHITECTURE.md](../ARCHITECTURE.md).
> Medido em 16/09/2026, no PC de desenvolvimento **e** na Raspberry Pi 5 alvo.

---

## 1. O resultado

| Métrica | PC (x86_64, Py 3.14) | **Raspberry Pi 5** (aarch64, Py 3.13) |
|---|---|---|
| Acurácia de **tipo** | 88,1% (37/42) | **88,1%** (37/42) |
| Acurácia de **gravidade** | 88,1% (37/42) | **88,1%** (37/42) |
| Latência média | 4,27 ms | **6,01 ms** |
| Latência p95 | 5,99 ms | **6,14 ms** |
| Latência máxima | — | **6,86 ms** |
| Tempo de treino | 3,63 s | **1,16 s** |
| Tamanho do artefato | 450 KB | 477 KB |

Acurácia **idêntica** entre as duas arquiteturas — o modelo é determinístico e
as versões de `scikit-learn`, `scipy` e `numpy` são as mesmas nos dois lados.

A Pi treina **3× mais rápido** que o PC de desenvolvimento, o que surpreende até
lembrar que o treino é dominado por operação de matriz pequena em cache, não por
paralelismo.

---

## 2. A comparação que decidiu a arquitetura

Números do projeto de referência (`docs/inferencia.md` original), medidos no
mesmo conjunto held-out:

| Abordagem | Tipo | Gravidade | Latência | Cabe na Pi? |
|---|---|---|---|---|
| qwen2.5:0.5b | 29% | 27% | ~5.800 ms | sim |
| qwen2.5:1.5b | 45% | 48% | ~6.100 ms | sim |
| llama3.2:3b | 86% | 60% | ~2.000 ms | **não** (workstation) |
| **TF-IDF + LogReg** | **88,1%** | **88,1%** | **6 ms** | **sim** |

Duas leituras importam:

1. **Os LLMs que cabem na Pi são ruins demais para esta decisão.** 29–45% de
   acurácia numa escolha que determina se o SAMU é chamado não é aceitável.
2. **Na gravidade, o classificador ganha até do `llama3.2:3b`** — 88,1% contra
   60%. E gravidade é justamente a variável que decide urgência.

O classificador é **mil vezes mais rápido** (6 ms contra 6.000 ms) e roda offline,
sem GPU, sem servidor de modelo, num artefato de 477 KB.

---

## 3. O número que importa mais que a acurácia

Acurácia trata todos os erros como iguais. Neste produto, eles não são:

- **Superestimar** a gravidade aciona um canal mais protetivo do que o necessário.
  Custa uma notificação a mais.
- **Subestimar** a gravidade manda alguém em risco imediato para um canal de
  orientação. Custa tempo que a pessoa não tem.

Por isso a medição separa a direção do erro:

```
SUBESTIMOU     0 casos   ← direção perigosa
SUPERESTIMOU   5 casos   ← direção segura
```

**Zero subestimações** no held-out. Todos os cinco erros de gravidade que restam
protegem *mais* do que o rótulo esperava:

| Frase | Rotulado | Classificado |
|---|---|---|
| "vi dois caras estranhos rondando o estacionamento" | potencial | imediato |
| "acho que estão me seguindo desde a parada de ônibus" | potencial | imediato |
| "encontraram uma mochila abandonada suspeita no saguão" | potencial | imediato |
| "torci o pé e está inchando bastante" | potencial | imediato |
| "bati a cabeça e estou meio zonzo" | potencial | imediato |

Isso está alinhado com a regra de negócio central do projeto: *nenhuma informação
nova pode reduzir a proteção já concedida*.

> E há uma segunda rede embaixo desta: mesmo que o classificador subestimasse, o
> **merge protetivo** (MVP-023) toma o máximo entre a gravidade do roteador e a da
> triagem. Na trilha Segurança o roteador já atribui `risco_imediato`, então uma
> subestimação do classificador seria estruturalmente neutralizada.

---

## 4. Como o modelo é construído

```python
Pipeline([
    ("features", FeatureUnion([
        ("palavra",   TfidfVectorizer(analyzer="word",    ngram_range=(1, 2), sublinear_tf=True)),
        ("caractere", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
    ])),
    ("clf", LogisticRegression(max_iter=1000, C=4.0, class_weight="balanced")),
])
```

**Dois classificadores separados**, um para `tipo` e outro para `gravidade`. São
decisões independentes: alguém pode relatar mal-estar leve (saúde, orientação) ou
parada respiratória (saúde, risco imediato). Um classificador único sobre o par
tipo×gravidade teria 12 classes com pouquíssimos exemplos cada.

**Os n-gramas de caractere não são detalhe.** Com pouco dado rotulado, são eles
que dão robustez a erro de digitação e variação morfológica — quem digita em
pânico erra, e errar não pode mudar para onde o pedido vai:

| Escrito certo | Escrito errado | Mesma trilha? |
|---|---|---|
| socorro | socorroo | ✅ |
| estou passando mal | estou passando maal | ✅ |
| estou desmaiando | estou desmaindo | ✅ |

`class_weight="balanced"` compensa o desequilíbrio entre trilhas: sem ele, a
classe mais frequente no treino seria favorecida.

---

## 5. Evolução do dataset

O treino cresceu de 77 para 120 exemplos em três etapas, cada uma corrigindo um
problema observado — não por volume.

| Etapa | Exemplos | O que corrigiu |
|---|---|---|
| Portado da referência | 77 | base |
| **+28** morfologia e erros de digitação | 105 | `desmaiando`, `desmaiei`, `socorroo`, `tão me seguindo`, fala regional |
| **+9** perguntas informativas por trilha | 114 | o modelo aprendera que *forma interrogativa = ouvidoria* |
| **+6** ameaça explícita e risco ambiental | 120 | "ameaça de morte" e "fumaça no laboratório" saíam como potencial |

### O caso mais instrutivo

Ao adicionar trivialidades de ouvidoria ("onde fica a secretaria", "perdi minha
carteirinha"), o modelo generalizou demais e passou a mandar **qualquer pergunta**
para a Ouvidoria:

```
"qual o ramal da segurança do campus?"    seguranca → ouvidoria  ✗
"onde fica a enfermaria do campus?"       saude     → ouvidoria  ✗
"quero saber como funciona a sala lilás"  mulher    → seguranca  ✗
```

Faltavam contraexemplos: perguntas *sobre* segurança, saúde e Sala Lilás. Com 9
exemplos, a acurácia de tipo subiu de 81,0% para 88,1%.

A lição é sobre equilíbrio de conceitos, não quantidade: **ensinar uma categoria
sem ensinar suas vizinhas cria uma atração indevida.**

---

## 6. Limite metodológico

⚠️ **Registrado de propósito, porque afeta como ler os 88%.**

As duas últimas rodadas de correção foram guiadas por **erros observados no
held-out**. As frases do bench continuam fora do treino — não há vazamento
literal, e há teste que recusa qualquer sobreposição. Mas o conjunto deixou de
ser perfeitamente independente: ele influenciou *quais conceitos* foram ensinados.

Consequência prática: **88,1% é honesto para aquelas 42 frases, mas provavelmente
otimista como estimativa de campo.** A medida limpa exigiria um terceiro conjunto,
coletado depois e nunca consultado.

Fica como dívida técnica, não como bloqueio do MVP. O que protege a operação não
é o número no held-out — é a suíte de regressão de segurança (MVP-025), que trava
comportamento em entradas críticas conhecidas, e o merge protetivo, que impede
qualquer rebaixamento.

---

## 7. Reproduzir

```bash
make train-clf          # treina e reporta acurácia, latência e tamanho
```

Na Pi, pelo mesmo caminho, depois de `make deploy`:

```bash
ssh poto-pi
cd ~/poto-mvp/backend && uv run python ../scripts/train_classificador.py
```

Fontes de dados: `backend/scripts/triagem_dataset.json` (120 exemplos, treino) e
`backend/scripts/bench_dataset.json` (42 exemplos, held-out, nunca usado em
treino). A integridade dos dois — ausência de sobreposição, duplicata, rótulo
inválido — é verificada por `tests/test_datasets.py`.
