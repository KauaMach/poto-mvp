# Roteiro — subir a aplicação e testar a interface web

Para quem vai rodar o P.O.T.O na própria máquina e conferir se as duas telas
funcionam: o **totem** (quem pede ajuda) e o **painel da central** (quem atende).

Não precisa de Raspberry Pi, câmera nem microfone. Tudo aqui roda no notebook.
O último capítulo mostra o que muda na Pi.

> **Leia a seção [Duas travas antes de testar](#5-duas-travas-antes-de-testar)
> antes do primeiro acionamento.** Sem a primeira, um teste pode disparar uma
> notificação de verdade.

---

## 1. O que precisa estar instalado

| ferramenta | para quê | conferir |
|---|---|---|
| [`uv`](https://docs.astral.sh/uv/) | dependências e execução do Python | `uv --version` |
| Node 20+ e npm | build do frontend | `node --version` |
| `make` | os atalhos deste projeto | `make --version` |

Python não precisa ser instalado à mão: o `uv` resolve a versão do
`pyproject.toml`.

---

## 2. Primeira vez

```bash
cd poto-mvp
make setup
```

Isso instala as dependências do backend e do frontend e **treina o
classificador de triagem** (~88% de acurácia). Sem o classificador a aplicação
sobe igual, caindo numa heurística de palavras-chave — e o `/health` avisa que
está nesse modo, em vez de fingir que está tudo bem.

Depois, crie o arquivo de configuração:

```bash
cp backend/.env.example backend/.env
```

O `.env` não vai para o repositório. Para testar, **os valores padrão bastam**:
o provider de notificação já vem em `log`, que só registra no banco e no
console em vez de mandar mensagem para alguém.

`make help` lista todos os atalhos disponíveis.

---

## 3. Dois modos de subir, e quando usar cada um

| | `make dev` | `make build && make serve` |
|---|---|---|
| para que serve | **mexer no código** | **conferir o que vai para a Pi** |
| portas | duas: `:5173` e `:8000` | uma: `:8000` |
| quem serve as telas | Vite, com recarga ao salvar | o próprio backend, do `dist/` |
| rota `/galeria` | existe | **não existe** |
| é o que roda na Pi | não | **sim** |

### Modo desenvolvimento

```bash
make dev
```

Sobe as duas coisas de uma vez e `Ctrl+C` encerra ambas. Abra:

```
http://localhost:5173
```

O Vite repassa `/api` para a porta 8000, inclusive o WebSocket — então o painel
funciona em tempo real mesmo com o front numa porta e a API em outra.

Se preferir separado: `make backend` numa aba e `make frontend` noutra.

### Modo produção local

```bash
make build     # compila o frontend para frontend/dist
make serve     # a API passa a servir as telas também
```

O `make serve` **se recusa a subir sem o build**, com a mensagem dizendo o que
falta — em vez de subir e servir 404 em todas as telas.

Abra:

```
http://localhost:8000
```

**Este é o modo que importa antes de uma demonstração.** É o mesmo servidor, o
mesmo build e a mesma origem única da Pi. Bug que só aparece aqui existe: em
`make dev` o Vite resolve caminhos que o backend serve de outro jeito.

---

## 4. As três telas

| URL | tela | observação |
|---|---|---|
| `/` | **Totem** — "Como podemos ajudar?" | é o que o tablet mostra |
| `/painel` | **Painel da central** | é o que a central vê |
| `/galeria` | catálogo de componentes | **só em `make dev`** |

A `/galeria` é removida do build de produção pelo bundler, não escondida por
configuração: no modo `serve`, digitar `/galeria` cai no totem. É de propósito
— num totem físico ninguém deve alcançar uma tela de desenvolvimento nem
digitando a URL.

Qualquer outro caminho também cai no totem. A exceção é `/api/...`, que
continua devolvendo **404 em JSON**: um cliente que espera JSON não pode
receber HTML com status 200.

---

## 5. Duas travas antes de testar

### 5.1 A trava de contatos — leia antes do primeiro acionamento

Os canais do P.O.T.O são reais: SAMU 192, PM 190, Bombeiros 193, Central 180.
Um teste descuidado pode virar um acionamento de verdade.

Duas proteções, e vale conhecer as duas:

- **Canal sem contato configurado não é acionável.** O `.env.example` vem com
  todos os `POTO_CONTACT_*` **vazios**, sem valor padrão. É deliberado: o
  projeto de referência trazia um celular real embutido no código.
- **`POTO_CONTACT_OVERRIDE`** redireciona **todos** os canais para um único
  destino. É a trava para ensaiar com contatos preenchidos:

  ```bash
  # backend/.env
  POTO_CONTACT_OVERRIDE=5586999999999   # seu próprio número
  ```

O `/health` informa em qual estado você está:

```bash
curl -s localhost:8000/api/v1/health | python3 -m json.tool
```

Procure `contact_override_ativo` e a lista `canais_sem_contato`.

> Com `POTO_NOTIF_PROVIDER=log` (o padrão) nada sai da máquina de todo modo — a
> "notificação" é uma linha no console e uma linha na tabela `notificacoes`. A
> trava importa quando você trocar para `webhook`.

### 5.2 O token do painel precisa ficar VAZIO

```bash
# backend/.env
POTO_PAINEL_TOKEN=
```

**Com um token preenchido, o painel para de funcionar.** O backend passa a
exigir o cabeçalho `X-POTO-Token` em `/chamados` e `/ws` (MVP-040), mas o
frontend ainda não tem onde digitar esse token — a tela mostra apenas
*"Sem permissão para ver os chamados. Confira o token do painel."*, sem campo
para informá-lo.

É uma lacuna conhecida, não um erro de configuração seu: a autenticação foi
feita no backend e o lado do frontend ainda não existe. Enquanto isso:

- **testando no notebook** → deixe vazio;
- **na Pi, em rede aberta** → o `/health` avisa em `avisos` que o painel está
  liberado. Enquanto não houver o campo no frontend, a proteção prática é a
  rede: mantenha a Pi fora de rede pública.

---

## 6. Roteiro do totem

Abra `/` e siga na ordem. A coluna "esperado" é o que confirma que funcionou.

| # | o que fazer | esperado |
|---|---|---|
| 1 | Ler a tela inicial | Título "Como podemos ajudar?" e **4 opções** |
| 2 | Tocar **Emergência médica** | Tela de confirmação, com pergunta explícita |
| 3 | Confirmar | Confirmação com o **protocolo** (`CALL-2026-000001`) |
| 4 | Voltar e tocar **Segurança** | Confirma e mostra protocolo novo |
| 5 | Tocar **Assédio / Sala Lilás** | **Tela neutra**, sem dizer o que foi acionado |
| 6 | Tocar **Outros** | Caminho de ouvidoria, sem urgência |
| 7 | **Segurar** o botão "Pânico" | Barra enche; soltar antes **cancela** |
| 8 | Segurar até o fim | Tela de **alerta ativo**, que não fecha sozinha |

### O passo 5 é o teste mais importante

A trilha **Assédio / Sala Lilás** é sempre **discreta** — a tela não anuncia o
que foi acionado. Não é preferência de quem usa: é decisão do backend. Se o
agressor está a três metros, uma tela dizendo "Sala Lilás acionada" transforma
o socorro em risco.

Confirme que veio do servidor, e não do frontend:

```bash
curl -s -X POST localhost:8000/api/v1/eventos \
  -H 'Content-Type: application/json' \
  -d "{\"evento_id\":\"$(uuidgen)\",\"totem_id\":\"TESTE\",\"tipo_ocorrencia\":\"mulher\"}" \
  | python3 -m json.tool | grep -E "tela_neutra|canal"
```

Deve mostrar `"tela_neutra": true`. Medido: `canal_roteado` `sala_lilas`,
gravidade `risco_potencial`.

### O passo 7 é o segundo mais importante

O pânico exige **segurar**, não tocar. Um botão de toque único num totem de
corredor dispara sozinho com uma mochila. Soltar antes do fim tem que cancelar.

---

## 7. Roteiro do painel

Abra `/painel` **numa segunda aba**, com o totem aberto na primeira.

| # | o que fazer | esperado |
|---|---|---|
| 1 | Olhar o topo | Indicador de tempo real **ativo** (não "reconectando") |
| 2 | Ver a lista | Os chamados do capítulo 6, **mais urgente no topo** |
| 3 | Ler um cartão | Chip de gravidade com **texto**: "Imediato", "Potencial", "Orientação" |
| 4 | Ver o contador | Prazo de SLA correndo (120 s imediato / 600 s potencial) |
| 5 | Filtrar **Precisam de mim** | Só os que ainda não foram reconhecidos |
| 6 | Filtrar **Já resolvidos** | Só encerrados e cancelados |
| 7 | Buscar por protocolo | Aceita protocolo, totem **ou** trecho do relato |
| 8 | Reconhecer um chamado | Contador para; o cartão muda de situação |
| 9 | Abrir o detalhe | Histórico de estados, notificações e a **triagem** |

### O passo 3 e a cor

A cor **nunca** é o único sinal. Todo chip tem rótulo em texto — cerca de 8%
dos homens têm alguma deficiência na percepção de vermelho e verde, e um painel
que informa só por cor não informa para eles.

### O passo 9 e a auditoria

O detalhe mostra o que a máquina inferiu **e** qual trilha a pessoa tocou:

```json
"triagem": {
  "tipo": "seguranca", "gravidade": "risco_imediato",
  "confianca": 0.533, "fonte": "classificador",
  "trilha_escolhida": "seguranca"
}
```

É o que responde "por que este chamado foi para o CSV?" meses depois. A regra
que governa isso: **nenhuma informação nova pode reduzir a proteção já
concedida** — o texto livre pode agravar um chamado, nunca rebaixá-lo.

---

## 8. Testar o tempo real

Com as duas abas abertas, lado a lado:

1. Acione uma trilha no **totem**.
2. O chamado aparece no **painel** sem recarregar a página.
3. Mude a situação no painel e veja o cartão atualizar.

Se quiser conferir por fora do navegador:

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

> O caminho é `/api/v1/ws` — **sem** `/painel` no fim. Um caminho errado recebe
> uma recusa de handshake (403).

---

## 9. Testar sem rede — a fila do totem

O que este teste prova: **um totem sem internet ainda aceita um pedido de
socorro.** É o cenário mais provável num corredor de universidade.

1. Abra o totem e o DevTools (F12).
2. Aba **Network** → marque **Offline**.
3. Acione uma trilha.
4. A confirmação aparece **na hora**, com aviso de `· 1 na fila` — sem
   ampulheta e **sem mensagem de erro técnico**.
5. Desmarque **Offline**.
6. Em até 15 s a fila esvazia sozinha e o chamado aparece no painel.
7. Confira que apareceu **um** chamado, não dois.

O passo 7 é o que se está testando de verdade. Cada acionamento carrega um
`evento_id` gerado no tablet, e o servidor usa isso como chave de idempotência
— reenviar o mesmo evento devolve o mesmo protocolo em vez de abrir um segundo
chamado para a mesma emergência.

Verificado: a garantia sobrevive até a um `kill -9` no serviço, porque a chave
mora no SQLite e não na memória do processo.

---

## 10. Conferir pela API, sem a interface

Útil para criar dados de teste rápido ou isolar se um problema é da tela ou do
servidor.

```bash
API=http://localhost:8000/api/v1

# estado do serviço, e o que está faltando configurar
curl -s $API/health | python3 -m json.tool

# as 4 trilhas de uma vez
for t in seguranca mulher saude ouvidoria; do
  curl -s -X POST $API/eventos -H 'Content-Type: application/json' \
    -d "{\"evento_id\":\"$(uuidgen)\",\"totem_id\":\"TESTE\",\"tipo_ocorrencia\":\"$t\"}" \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["chamado_id"], d["canal_roteado"], d["gravidade"])'
done

# pânico
curl -s -X POST $API/panico -H 'Content-Type: application/json' \
  -d "{\"evento_id\":\"$(uuidgen)\",\"totem_id\":\"TESTE\"}" | python3 -m json.tool

curl -s $API/chamados | python3 -m json.tool   # o que o painel lista
curl -s $API/canais   | python3 -m json.tool   # canais e quais estão acionáveis
```

Roteamento esperado, medido:

| trilha | canal | gravidade | tela |
|---|---|---|---|
| `seguranca` | `csv` | `risco_imediato` | normal |
| `mulher` | `sala_lilas` | `risco_potencial` | **neutra** |
| `saude` | `sapsi` | `orientacao` | normal |
| `ouvidoria` | `ouvidoria` | `orientacao` | normal |
| pânico | `csv` **e** `sala_lilas` | `risco_imediato` | alerta ativo |

> **`make seed` e `make demo-reset` ainda não funcionam.** Eles dependem de um
> script que chega na MVP-071 e avisam isso com clareza ao rodar. Até lá, o laço
> acima é a forma de popular o banco. Para zerar:
> `rm -f backend/poto.db*` e suba de novo.

---

## 11. Na Raspberry Pi

A Pi **não compila** o frontend: o build é feito no notebook e enviado pronto.

```bash
make deploy PI_HOST=raspoto@10.13.60.159   # constrói e envia por rsync
make build-id PI_HOST=raspoto@10.13.60.159 # o que a Pi serve é o que eu construí?
```

O `build-id` responde a pergunta que trava uma demonstração: *"a correção está
na Pi ou eu esqueci de enviar?"*. Ele distingue quatro estados — Pi
inalcançável, sem build, build velho e build igual.

Numa Pi nova, `bash deploy/install-pi.sh` faz tudo (pacotes, `uv`, venv,
classificador, serviço systemd) e imprime as duas URLs no fim. É idempotente:
rodar duas vezes conserta um estado meio-configurado.

```bash
sudo systemctl status poto-api        # o serviço
sudo journalctl -u poto-api -f        # os logs ao vivo
```

Medidos na Pi: **31 s** do `reboot` até a API responder, e **4,8 s** para o
systemd reerguer o serviço depois de um `kill -9`.

### As duas URLs, e por que são duas

```
http://RaspPoto.local:8000     (mDNS — preferido)
http://10.13.60.159:8000       (IP — plano B)
```

**O `.local` só resolve de dentro da mesma rede da Pi.** mDNS é link-local por
desenho: o pacote vai com TTL 1 e não atravessa roteador. Medido na UFPI — o
segmento da Pi tem mDNS funcionando, com 26 vizinhos anunciando, e mesmo assim
`RaspPoto.local` não resolve de outro segmento do campus.

Consequência prática: **coloque o tablet na mesma rede da Pi.** Se ele cair em
outro segmento, só a URL por IP funciona. Confira no local, com o tablet na
mão — não na véspera.

---

## 12. Quando não funciona

| sintoma | causa provável | o que fazer |
|---|---|---|
| Painel: "Sem permissão para ver os chamados" | `POTO_PAINEL_TOKEN` preenchido | Deixe vazio — [§5.2](#52-o-token-do-painel-precisa-ficar-vazio) |
| Painel carrega mas nada chega em tempo real | WebSocket bloqueado | Veja o console do navegador; confira o indicador do topo |
| WebSocket recusado com 403 | caminho errado | É `/api/v1/ws`, sem `/painel` |
| `/` ou `/painel` dão 404 | subiu com `make backend`, que não serve as telas | `make build` + `make serve`, ou use `make dev` na `:5173` |
| `/galeria` mostra o totem | você está em modo produção | Use `make dev` |
| Rota de API devolve HTML | caminho fora de `/api` | Confira a URL — sob `/api` o 404 é JSON |
| Triagem "burra" | classificador não treinado | `make train-clf`; confira em `/health` |
| Nada é notificado | canal sem contato | Esperado com `.env` limpo — veja `canais_sem_contato` |
| `make seed` reclama | script ainda não existe | Use o laço do [§10](#10-conferir-pela-api-sem-a-interface) |
| Porta 8000 ocupada | outra instância rodando | `BACKEND_PORT=8001 make backend` |

Para ver o estado inteiro de uma vez:

```bash
curl -s localhost:8000/api/v1/health | python3 -m json.tool
```

O `/health` é honesto de propósito: ele responde `status: ok` **e** lista em
`avisos` o que está degradado. Um serviço que diz "ok" escondendo que o painel
está sem credencial é pior que um que não responde.

```bash
make test    # 1618 testes do backend
make lint    # ruff no backend, oxlint no frontend
```

---

## Referências

- [`../TASKS.md`](../TASKS.md) — as tarefas, com a decisão de projeto de cada uma
- [`aceite-mvp.md`](aceite-mvp.md) — roteiro de resiliência, com os números medidos
- [`setup-tablet.md`](setup-tablet.md) — travar o tablet no modo kiosk
- `/docs` na aplicação rodando — API interativa (Swagger)
