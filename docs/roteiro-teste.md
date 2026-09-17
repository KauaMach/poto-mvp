# Roteiro — subir o P.O.T.O e testar as duas interfaces

Como executar o projeto do zero e conferir que funciona: o **backend**, a
**interface do totem** (quem pede ajuda) e a **interface da central** (quem
atende).

Não precisa de Raspberry Pi, câmera nem microfone — tudo roda no notebook. O
[capítulo 13](#13-na-raspberry-pi) mostra o que muda na Pi.

> **Leia [§6 Duas travas](#6-duas-travas-antes-de-testar) antes do primeiro
> acionamento.** Sem a primeira, um teste pode disparar uma notificação real.

**Índice**

| | |
|---|---|
| [1. Pré-requisitos](#1-pré-requisitos) | [8. Roteiro da central](#8-roteiro-da-interface-da-central) |
| [2. Primeira vez](#2-primeira-vez-uma-só-vez) | [9. Tempo real](#9-testar-o-tempo-real-as-duas-juntas) |
| [3. Subir o backend](#3-subir-o-backend) | [10. Sem rede](#10-testar-sem-rede--a-fila-do-totem) |
| [4. Subir o frontend](#4-subir-o-frontend) | [11. Câmera e microfone](#11-câmera-e-microfone) |
| [5. Rotas de conexão](#5-rotas-de-conexão) | [12. Só pela API](#12-conferir-só-pela-api) |
| [6. Duas travas](#6-duas-travas-antes-de-testar) | [13. Na Raspberry Pi](#13-na-raspberry-pi) |
| [7. Roteiro do totem](#7-roteiro-da-interface-do-totem) | [14. Quando não funciona](#14-quando-não-funciona) |

---

## 1. Pré-requisitos

| ferramenta | para quê | conferir |
|---|---|---|
| [`uv`](https://docs.astral.sh/uv/) | dependências e execução do Python | `uv --version` |
| Node 20+ e npm | build do frontend | `node --version` |
| `make` | os atalhos do projeto | `make --version` |

Python não precisa ser instalado à mão: o `uv` resolve a versão do
`pyproject.toml` (3.11+).

`make help` lista todos os atalhos.

---

## 2. Primeira vez (uma só vez)

```bash
cd poto-mvp
make setup
cp backend/.env.example backend/.env
```

O `make setup` faz três coisas:

1. `uv sync --extra dev` no backend — cria `backend/.venv` e instala tudo;
2. `npm install` no frontend;
3. **treina o classificador de triagem** (`backend/app/data/triagem_clf.joblib`,
   ~88% de acurácia).

O artefato do classificador **não é versionado** — são ~2 MB de modelo binário
que mudariam a cada treino. Sem ele a aplicação sobe igual, caindo numa
heurística de palavras-chave, e o `/health` avisa que está nesse modo em vez de
fingir que está tudo bem.

O `.env` não vai para o repositório. **Para testar, os padrões bastam**: o
provider de notificação já vem em `log`, que só registra no banco e no console
em vez de mandar mensagem para alguém.

---

## 3. Subir o backend

### O que o backend é

Um processo `uvicorn` servindo FastAPI na porta **8000**. Ele guarda tudo num
SQLite (`backend/poto.db`), roda um worker de SLA em segundo plano e — se o
build do frontend existir — **serve as duas interfaces também**.

### Modo desenvolvimento

```bash
make backend
```

Equivale a `uv run uvicorn app.main:app --reload --port 8000` dentro de
`backend/`. O `--reload` reinicia ao salvar um arquivo.

Escuta só em `127.0.0.1`. Para outro aparelho alcançar, use o modo produção
(§3.3) ou passe `--host 0.0.0.0`.

### Modo produção

```bash
make build     # constrói o frontend primeiro
make serve
```

`make serve` é `uvicorn --host 0.0.0.0 --port 8000`, **sem** `--reload`. Duas
diferenças, e as duas importam:

- **`--host 0.0.0.0`** — sem isto o uvicorn escuta só em `localhost` e o tablet
  não alcança. O sintoma é "funciona na Pi, não funciona no tablet".
- **sem `--reload`** — o observador de arquivos gasta CPU vigiando uma árvore
  que não muda, e um toque acidental no código reiniciaria o serviço no meio de
  um atendimento.

O `make serve` **se recusa a subir sem o build**, dizendo o que falta, em vez de
subir e servir 404 em todas as telas.

> Na Pi, o serviço systemd chama `.venv/bin/uvicorn` direto, e não `uv run`.
> Mesmos argumentos de servidor; a invocação difere porque `uv run` precisa
> escrever em `~/.cache/uv`, que o sandbox da unit torna somente-leitura — o
> serviço falhava em laço por isso. Ver [§13](#13-na-raspberry-pi).

### Conferir que subiu

```bash
curl -s localhost:8000/api/v1/health | python3 -m json.tool
```

Resposta esperada, com os campos que importam:

```json
{
  "status": "ok",
  "banco": true,
  "triagem":  { "modo": "classificador", "artefato_existe": true },
  "notificacao": { "provider": "log" },
  "frontend": { "montado": true, "build_id": "5ffc215baa9a" },
  "seguranca": { "painel_protegido": false },
  "avisos": [ "..." ]
}
```

O `/health` é **honesto de propósito**: devolve `status: ok` **e** lista em
`avisos` o que está degradado. Um serviço que diz "ok" escondendo que a central
está sem credencial é pior que um que não responde.

| campo | o que olhar |
|---|---|
| `banco` | `true`. Se não, o SQLite não abriu |
| `triagem.modo` | `classificador` ou `heuristica` |
| `notificacao.provider` | `log` (nada sai da máquina) ou `webhook` |
| `frontend.montado` | `false` significa que não há build — só a API responde |
| `avisos` | leia sempre; é onde aparece contato faltando e central sem token |

### Porta ocupada

```bash
BACKEND_PORT=8001 make backend
```

---

## 4. Subir o frontend

### O que o frontend é

Uma aplicação React de página única. **As duas interfaces vivem no mesmo
build** — o que muda é a rota. Não há dois aplicativos.

### Modo desenvolvimento (Vite na 5173)

```bash
make frontend
```

Sobe o Vite em `http://localhost:5173`, com recarga instantânea ao salvar. O
Vite **repassa `/api` para a porta 8000**, inclusive o WebSocket:

```
/api/*  →  http://localhost:8000    (com ws: true)
```

Então a central funciona em tempo real mesmo com o front numa porta e a API em
outra. **O backend precisa estar rodando** — sem ele as telas carregam e não
têm dados.

### Modo produção (o backend serve tudo)

```bash
make build
```

Compila para `frontend/dist`. A partir daí o backend serve as telas na própria
porta 8000, e **não há proxy nem CORS** — mesma origem.

O build também grava um `build-id` dentro do `dist/`, que é como se confere
depois se a Pi está servindo a versão certa.

### Os dois juntos, num comando

```bash
make dev
```

Sobe backend (`:8000`) e frontend (`:5173`) de uma vez; `Ctrl+C` encerra ambos.

### Qual modo usar

| | `make dev` | `make build && make serve` |
|---|---|---|
| para que serve | **mexer no código** | **conferir o que vai para a Pi** |
| portas | duas: `:5173` e `:8000` | uma: `:8000` |
| quem serve as telas | Vite, com recarga | o backend, do `dist/` |
| rota `/galeria` | existe | **não existe** |
| é o que roda na Pi | não | **sim** |

**Antes de uma demonstração, use o modo produção.** É o mesmo servidor, o mesmo
build e a mesma origem única da Pi. Bug que só aparece ali existe: em `make dev`
o Vite resolve caminhos que o backend serve de outro jeito.

---

## 5. Rotas de conexão

### As telas

| URL | interface | quem usa |
|---|---|---|
| `/` | **Totem** — "Como podemos ajudar?" | o tablet no corredor |
| `/painel` | **Central** — lista de chamados | quem atende |
| `/galeria` | catálogo de componentes | só em `make dev` |

Os endereços dependem do modo:

| | totem | central |
|---|---|---|
| `make dev` | `http://localhost:5173/` | `http://localhost:5173/painel` |
| `make serve` | `http://localhost:8000/` | `http://localhost:8000/painel` |
| na Pi | `http://RaspPoto.local:8000/` | `http://RaspPoto.local:8000/painel` |

`/painel` e `/painel/` são a mesma rota. **Qualquer outro caminho cai no
totem** — é aplicação de página única e o roteamento é no cliente.

A exceção é `/api/...`, que continua devolvendo **404 em JSON**: um cliente que
espera JSON não pode receber HTML com status 200, e isso mascararia erro de
digitação no endpoint.

A `/galeria` é **removida do build de produção pelo bundler**, não escondida por
configuração: em `make serve`, digitar `/galeria` cai no totem. Num totem físico
ninguém deve alcançar uma tela de desenvolvimento, nem digitando a URL.

### A API

Todas sob o prefixo `/api/v1`. A coluna **token** diz se exige o cabeçalho
`X-POTO-Token` (ver [§6.2](#62-o-token-da-central-precisa-ficar-vazio)).

**Sistema** — aberto, é o que se consulta para diagnosticar.

| método | rota | token | para quê |
|---|---|---|---|
| `GET` | `/health` | não | estado do serviço e o que está degradado |
| `GET` | `/config` | não | constantes que o frontend não deve duplicar |
| `GET` | `/canais` | não | catálogo de canais e quais estão acionáveis |

**Acionamento** — usado pelo totem. **Nunca exige token**: um totem em pânico
não pode falhar por credencial.

| método | rota | token | para quê |
|---|---|---|---|
| `POST` | `/eventos` | não | aciona uma trilha |
| `POST` | `/panico` | não | pânico; aciona vários canais de uma vez |

**Central** — exige token. É onde está o relato de quem pediu ajuda.

| método | rota | token | para quê |
|---|---|---|---|
| `GET` | `/chamados` | **sim** | a lista que a central mostra |
| `GET` | `/chamados/{id}` | **sim** | detalhe com histórico, notificações e triagem |
| `PATCH` | `/chamados/{id}` | **sim** | muda situação e observação |
| `POST` | `/chamados/{id}/ack` | **sim** | reconhece; para o contador de SLA |
| `POST` | `/chamados/{id}/escalonar` | **sim** | aciona uma autoridade do estado |

**Tempo real**

| rota | token | para quê |
|---|---|---|
| `WS /ws` | **sim** | eventos `conectado`, `novo_chamado`, `atualizado` |

O caminho é **`/api/v1/ws`** — sem `/painel` no fim. Caminho errado recebe
recusa de handshake (403).

O navegador não deixa definir cabeçalhos num `new WebSocket()`, então o `/ws`
também aceita `?token=`. Prefira o cabeçalho quando puder — query string
aparece em log de acesso.

**Mídia** — câmera e microfone.

| método | rota | token | para quê |
|---|---|---|---|
| `GET` | `/dispositivos` | **sim** | câmeras e microfones detectados agora |
| `POST` | `/chamados/{id}/midia` | **sim** | **abre a autorização**; devolve `stream_url` |
| `DELETE` | `/chamados/{id}/midia` | **sim** | encerra imediatamente |
| `GET` | `/chamados/{id}/midia/auditoria` | **sim** | quem olhou, qual dispositivo, por quanto tempo |
| `GET` | `/midia/camera/{id}/stream` | sessão | vídeo MJPEG |
| `GET` | `/midia/microfone/{id}/stream` | sessão | áudio WAV ao vivo |
| `GET` | `/midia/microfone/{id}/clipe` | sessão | WAV fechado (fallback) |

As três últimas **não** usam token, e a razão é técnica: o vídeo vai num
`<img src="…">` e o áudio num `<audio src="…">`, e o navegador não deixa
definir cabeçalhos nesses elementos. A autorização delas é a **sessão** na query
string — token efêmero de 10 minutos, que só existe se alguém autenticado o
pediu para um chamado **ativo**. Sem sessão válida: **403**.

**Nenhum stream existe fora de uma sessão.** É o controle que separa um totem de
segurança de um equipamento de vigilância.

**Documentação interativa**

```
http://localhost:8000/docs
```

Swagger com todas as rotas, gerado do código — se divergir desta tabela, o
Swagger está certo.

---

## 6. Duas travas antes de testar

### 6.1 A trava de contatos

Os canais do P.O.T.O são reais: SAMU 192, PM 190, Bombeiros 193, Central 180.
Um teste descuidado pode virar um acionamento de verdade.

Três proteções:

- **`POTO_NOTIF_PROVIDER=log`** (o padrão) — nada sai da máquina. A
  "notificação" é uma linha no console e uma na tabela `notificacoes`.
- **Canal sem contato não é acionável.** O `.env.example` vem com todos os
  `POTO_CONTACT_*` **vazios**, sem valor padrão. É deliberado: o projeto de
  referência trazia um celular real embutido no código-fonte.
- **`POTO_CONTACT_OVERRIDE`** redireciona **todos** os canais para um destino
  único. É a trava para ensaiar com contatos preenchidos:

  ```bash
  # backend/.env
  POTO_CONTACT_OVERRIDE=5586999999999   # seu próprio número
  ```

Confira em qual estado você está:

```bash
curl -s localhost:8000/api/v1/health \
  | python3 -c 'import sys,json; d=json.load(sys.stdin)["notificacao"]; print(d["provider"], d["contact_override_ativo"], d["canais_sem_contato"])'
```

### 6.2 O token da central precisa ficar VAZIO

```bash
# backend/.env
POTO_PAINEL_TOKEN=
```

**Com um token preenchido, a interface da central para de funcionar.** O backend
passa a exigir `X-POTO-Token` em `/chamados` e `/ws`, mas o frontend **ainda não
tem onde digitar esse token**: a tela mostra apenas *"Sem permissão para ver os
chamados. Confira o token do painel."*, sem campo para informá-lo.

É lacuna conhecida, não erro de configuração de quem testa — a autenticação foi
feita no backend e o lado do frontend ainda não existe. Enquanto isso:

- **testando no notebook** → deixe vazio;
- **na Pi** → o `/health` avisa em `avisos` que a central está liberada. A
  proteção prática é a rede: mantenha a Pi fora de rede pública.

Se precisar chamar a API com token preenchido, por `curl`:

```bash
curl -s -H "X-POTO-Token: seu-token" localhost:8000/api/v1/chamados
```

---

## 7. Roteiro da interface do totem

Abra `/` e siga na ordem. A coluna "esperado" é o que confirma que funcionou.

| # | o que fazer | esperado |
|---|---|---|
| 1 | Ler a tela inicial | "Como podemos ajudar?" e **4 opções** |
| 2 | Tocar **Emergência médica** | Confirmação, com pergunta explícita |
| 3 | Confirmar | Confirmação com o **protocolo** (`CALL-2026-000001`) |
| 4 | Voltar e tocar **Segurança** | Confirma e mostra protocolo novo |
| 5 | Tocar **Assédio / Sala Lilás** | **Tela neutra**, sem dizer o que foi acionado |
| 6 | Tocar **Outros** | Caminho de ouvidoria, sem urgência |
| 7 | **Segurar** o botão "Pânico" | Barra enche; soltar antes **cancela** |
| 8 | Segurar até o fim | **Alerta ativo**, que não fecha sozinho |

### O passo 5 é o mais importante

A trilha **Assédio / Sala Lilás** é sempre **discreta** — a tela não anuncia o
que foi acionado. Não é preferência de quem usa: é decisão do backend. Se o
agressor está a três metros, uma tela dizendo "Sala Lilás acionada" transforma o
socorro em risco.

Confirme que a decisão vem do servidor, não do frontend:

```bash
curl -s -X POST localhost:8000/api/v1/eventos \
  -H 'Content-Type: application/json' \
  -d "{\"evento_id\":\"$(uuidgen)\",\"totem_id\":\"TESTE\",\"tipo_ocorrencia\":\"mulher\"}" \
  | python3 -m json.tool | grep -E "tela_neutra|canal_roteado"
```

Medido: `"canal_roteado": "sala_lilas"` e `"tela_neutra": true`.

### O passo 7 é o segundo mais importante

O pânico exige **segurar**, não tocar. Um botão de toque único num totem de
corredor dispara sozinho com uma mochila. Soltar antes do fim tem que cancelar.

---

## 8. Roteiro da interface da central

Abra `/painel` **numa segunda aba**, com o totem na primeira.

| # | o que fazer | esperado |
|---|---|---|
| 1 | Olhar o topo | Indicador de tempo real **ativo**, não "reconectando" |
| 2 | Ver a lista | Os chamados do §7, **mais urgente no topo** |
| 3 | Ler um cartão | Chip de gravidade com **texto**: "Imediato", "Potencial", "Orientação" |
| 4 | Ver o contador | Prazo de SLA correndo (120 s imediato / 600 s potencial) |
| 5 | Filtrar **Precisam de mim** | Só os que ainda não foram reconhecidos |
| 6 | Filtrar **Já resolvidos** | Só encerrados e cancelados |
| 7 | Buscar | Aceita protocolo, totem **ou** trecho do relato |
| 8 | Reconhecer um chamado | Contador para; o cartão muda de situação |
| 9 | Mudar estado → **Em atendimento** / **Encerrado** | Situação muda no cartão |
| 10 | Abrir um chamado ativo | Seletor de **câmera e microfone** |

### O passo 3 e a cor

A cor **nunca** é o único sinal. Todo chip tem rótulo em texto — cerca de 8% dos
homens têm alguma deficiência na percepção de vermelho e verde, e um painel que
informa só por cor não informa para eles.

### Não há tela de detalhe — e isso é uma lacuna, não uma decisão

**Correção a uma versão anterior deste roteiro, que mandava "abrir o
detalhe".** Esse passo não existe: o painel consome `GET /chamados` (a lista) e
nunca `GET /chamados/{id}`. Não há tela de histórico de estados, de
notificações nem da triagem.

O endpoint existe e responde completo — o que falta é a tela. Para ver o que a
máquina inferiu, hoje é pela API:

```bash
curl -s localhost:8000/api/v1/chamados/CALL-2026-000001 | python3 -m json.tool
```

```json
"triagem": {
  "tipo": "seguranca", "gravidade": "risco_imediato",
  "confianca": 0.533, "fonte": "classificador",
  "trilha_escolhida": "seguranca"
}
```

É o que responde "por que este chamado foi para o CSV?" meses depois. A regra que
governa isso: **nenhuma informação nova pode reduzir a proteção já concedida** —
o texto livre pode agravar um chamado, nunca rebaixá-lo.

### O escalonamento manual fica no TOTEM, não no painel

Outra coisa que vale saber antes de procurar botão que não existe: `POST
/chamados/{id}/escalonar` é chamado pela **tela de alerta ativo do totem**, onde
quem acionou o pânico pode tocar PM 190, SAMU 192, Bombeiros 193 ou Central 180
direto. O painel não tem esse comando.

A escalação **automática** por estouro de SLA acontece no backend, sem tela
nenhuma — é o worker da MVP-038.

---

## 9. Testar o tempo real (as duas juntas)

Com as duas abas lado a lado:

1. Acione uma trilha no **totem**.
2. O chamado aparece na **central** sem recarregar a página.
3. Mude a situação na central e veja o cartão atualizar.

Por fora do navegador:

```bash
cd backend && uv run python - <<'EOF'
import asyncio, json, websockets
async def main():
    async with websockets.connect("ws://localhost:8000/api/v1/ws") as ws:
        while True:
            print(json.loads(await ws.recv()))
asyncio.run(main())
EOF
```

O primeiro quadro é `conectado`; depois vêm `novo_chamado` e `atualizado`.

> Um chamado gera **mais de um** `atualizado`: além das mudanças do operador, a
> notificação roda em segundo plano e muda a situação por conta própria (para
> `notificado` ou `falha_notificacao`). Se você contar um evento por ação, vai
> ler os eventos desalinhados.

---

## 10. Testar sem rede — a fila do totem

O que este teste prova: **um totem sem internet ainda aceita um pedido de
socorro.** É o cenário mais provável num corredor de universidade.

1. Abra o totem e o DevTools (F12).
2. Aba **Network** → marque **Offline**.
3. Acione uma trilha.
4. A confirmação aparece **na hora**, com aviso de `· 1 na fila` — sem ampulheta
   e **sem mensagem de erro técnico**.
5. Desmarque **Offline**.
6. Em até 15 s a fila esvazia sozinha e o chamado aparece na central.
7. Confira que apareceu **um** chamado, não dois.

O passo 7 é o que se está testando de verdade. Cada acionamento carrega um
`evento_id` gerado no tablet, e o servidor usa isso como chave de idempotência —
reenviar o mesmo evento devolve o **mesmo** protocolo em vez de abrir um segundo
chamado para a mesma emergência.

Verificado: a garantia sobrevive até a um `kill -9` no serviço, porque a chave
mora no SQLite e não na memória do processo.

---

## 11. Câmera e microfone

Sem hardware, `GET /dispositivos` devolve **lista vazia** — e isso é resposta
válida, não erro. A aplicação sobe igual.

O fluxo é sempre o mesmo, e a ordem importa:

```bash
API=http://localhost:8000/api/v1

curl -s $API/dispositivos | python3 -m json.tool        # 1. o que existe

# 2. abrir a autorização para um chamado ATIVO
curl -s -X POST $API/chamados/CALL-2026-000001/midia \
  -H 'Content-Type: application/json' \
  -d '{"dispositivo_id":"csi:0"}' | python3 -m json.tool

# 3. a resposta traz stream_url pronta, com a sessão embutida
# 4. encerrar
curl -s -X DELETE $API/chamados/CALL-2026-000001/midia

# 5. conferir o rastro
curl -s $API/chamados/CALL-2026-000001/midia/auditoria | python3 -m json.tool
```

Quatro coisas que valem saber:

- **Sem sessão, os streams devolvem 403.** Nenhum stream existe fora de uma
  autorização.
- **A sessão expira sozinha em 10 minutos** e é checada a cada frame, não só na
  abertura — checar uma vez só tornaria o prazo decorativo.
- **Chamado encerrado ou cancelado recusa com 409.** Um atendimento concluído
  não justifica olhar o corredor.
- **A sessão da câmera não autoriza o microfone**, e vice-versa. Áudio é mais
  invasivo que imagem.

A auditoria grava **abertura e fechamento**, com dispositivo, operador e
duração. Append-only. Uma câmera num espaço público só é aceitável se cada
ativação deixar rastro — a diferença entre um totem de segurança e vigilância
**é** a auditabilidade.

---

## 12. Conferir só pela API

Útil para criar dados de teste rápido ou isolar se o problema é da tela ou do
servidor.

```bash
API=http://localhost:8000/api/v1

# as 4 trilhas de uma vez
for t in seguranca mulher saude ouvidoria; do
  curl -s -X POST $API/eventos -H 'Content-Type: application/json' \
    -d "{\"evento_id\":\"$(uuidgen)\",\"totem_id\":\"TESTE\",\"tipo_ocorrencia\":\"$t\"}" \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["chamado_id"], d["canal_roteado"], d["gravidade"])'
done

# pânico
curl -s -X POST $API/panico -H 'Content-Type: application/json' \
  -d "{\"evento_id\":\"$(uuidgen)\",\"totem_id\":\"TESTE\"}" | python3 -m json.tool

curl -s $API/chamados | python3 -m json.tool
curl -s $API/canais   | python3 -m json.tool
```

Roteamento esperado, medido:

| trilha | canal | gravidade | tela |
|---|---|---|---|
| `seguranca` | `csv` | `risco_imediato` | normal |
| `mulher` | `sala_lilas` | `risco_potencial` | **neutra** |
| `saude` | `sapsi` | `orientacao` | normal |
| `ouvidoria` | `ouvidoria` | `orientacao` | normal |
| pânico | `csv` **e** `sala_lilas` | `risco_imediato` | alerta ativo |

> **`make seed` e `make demo-reset` ainda não funcionam.** Dependem de um script
> que chega na MVP-071, e avisam isso com clareza ao rodar. Até lá, o laço acima
> é a forma de popular o banco. Para zerar: `rm -f backend/poto.db*` e suba de
> novo.

---

## 13. Na Raspberry Pi

A Pi **não compila** o frontend: o build é feito no notebook e enviado pronto.
Isso poupa 133 MB e uma toolchain na Pi, e dispensa internet no deploy.

```bash
make deploy PI_HOST=raspoto@<ip-da-pi>     # constrói e envia por rsync
make build-id PI_HOST=raspoto@<ip-da-pi>   # a Pi está servindo o meu build?
```

O `build-id` responde a pergunta que trava uma demonstração: *"a correção está
na Pi ou eu esqueci de enviar?"*. Distingue quatro estados — Pi inalcançável,
sem build, build velho e build igual.

Numa Pi nova, `bash deploy/install-pi.sh` faz tudo (pacotes, `uv`, venv,
classificador, serviço systemd) e imprime as duas URLs no fim. É **idempotente**:
rodar duas vezes conserta um estado meio-configurado.

```bash
sudo systemctl status poto-api      # o serviço
sudo journalctl -u poto-api -f      # os logs ao vivo
sudo systemctl restart poto-api
```

Medidos na Pi: **31 s** do `reboot` até a API responder, e **4,8 s** para o
systemd reerguer o serviço depois de um `kill -9`.

### As duas URLs, e por que são duas

```
http://RaspPoto.local:8000     (mDNS — preferido)
http://<ip-da-pi>:8000         (IP — plano B)
```

**Descubra o IP atual na própria Pi**, porque ele muda:

```bash
ssh raspoto@<ip-conhecido> 'hostname -I'
```

**O `.local` só resolve de dentro da mesma rede da Pi.** mDNS é link-local por
desenho: o pacote vai com TTL 1 e não atravessa roteador. Medido na UFPI — o
segmento da Pi tem mDNS funcionando, com 26 vizinhos anunciando, e mesmo assim
`RaspPoto.local` não resolve de outro segmento do campus.

Consequência prática: **coloque o tablet na mesma rede da Pi.** Se ele cair em
outro segmento, só a URL por IP funciona. Confira no local, com o tablet na mão
— não na véspera.

### E o IP muda — isto foi observado, não suposto

A Pi pega endereço por DHCP. Entre 16 e 17/09 ela saiu de `10.13.60.159` para
`10.13.60.129` **sozinha**, sem ninguém mexer em nada. Um dia de intervalo
bastou.

Isso significa que o "plano B" também expira: um atalho no tablet com o IP
decorado aponta para nada depois de o roteador reiniciar. Antes da
demonstração, faça **uma** das duas coisas:

- **reserva no roteador** para o MAC da Pi (preferida — nada muda na Pi); ou
- **IP estático na Pi**, com o comando que o `install-pi.sh` imprime já
  preenchido com o CIDR e o gateway reais lidos da interface.

O script imprime o MAC e o gateway no fim justamente para isso.

---

## 14. Quando não funciona

| sintoma | causa provável | o que fazer |
|---|---|---|
| Central: "Sem permissão para ver os chamados" | `POTO_PAINEL_TOKEN` preenchido | Deixe vazio — [§6.2](#62-o-token-da-central-precisa-ficar-vazio) |
| Central carrega, nada chega em tempo real | WebSocket não conectou | Veja o indicador no topo e o console do navegador |
| WebSocket recusado com 403 | caminho errado | É `/api/v1/ws`, sem `/painel` |
| `/` ou `/painel` dão 404 | subiu com `make backend`, que não serve as telas | `make build` + `make serve`, ou `make dev` na `:5173` |
| Telas carregam sem dados no `make dev` | o backend não está rodando | Suba `make backend` também, ou use `make dev` |
| `/galeria` mostra o totem | você está em modo produção | Use `make dev` |
| Rota de API devolve HTML | caminho fora de `/api` | Confira a URL — sob `/api` o 404 é JSON |
| Triagem "burra" | classificador não treinado | `make train-clf`; confira em `/health` |
| Nada é notificado | canal sem contato | Esperado com `.env` limpo — veja `canais_sem_contato` |
| `GET /dispositivos` devolve `[]` | sem câmera nem microfone | Esperado no notebook |
| Stream devolve 403 | sem sessão, expirada, ou de outro dispositivo | Abra a sessão primeiro — [§11](#11-câmera-e-microfone) |
| `make seed` reclama | script ainda não existe | Use o laço do [§12](#12-conferir-só-pela-api) |
| Porta 8000 ocupada | outra instância rodando | `BACKEND_PORT=8001 make backend` |

Para ver o estado inteiro de uma vez:

```bash
curl -s localhost:8000/api/v1/health | python3 -m json.tool
```

```bash
make test    # suíte do backend
make lint    # ruff no backend, oxlint no frontend
```

---

## Referências

- [`../TASKS.md`](../TASKS.md) — as tasks, com a decisão de projeto de cada uma
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — arquitetura, API, banco e fluxos
- [`aceite-mvp.md`](aceite-mvp.md) — roteiro de resiliência, com os números medidos
- [`setup-tablet.md`](setup-tablet.md) — travar o tablet no modo kiosk
- [`conexao-ssh.md`](conexao-ssh.md) — acesso à Pi por SSH
- `/docs` na aplicação rodando — Swagger, gerado do código
