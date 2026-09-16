# Conectando por SSH na Raspberry Pi — passo a passo comentado

> Registro didático de como a conexão `ssh poto-pi` foi estabelecida neste projeto,
> explicando o **porquê** de cada comando, não só o quê. Serve como referência para
> configurar o acesso a qualquer novo dispositivo (uma segunda Pi, um servidor, etc.).

---

## 1. O que o SSH realmente resolve

SSH decide duas perguntas de confiança **independentes**, e é fácil confundir as duas:

```
   Seu computador                              Servidor (a Pi)
        │                                            │
        │   1) "Este servidor é mesmo quem diz       │
        │       ser, ou é um impostor na rede?"       │
        │◄──────────────────────────────────────────►│   verificado pela
        │                                            │   CHAVE DO HOST
        │                                            │
        │   2) "Eu sou realmente o usuário            │
        │       autorizado a entrar aqui?"            │
        │─────────────────────────────────────────────►   verificado pela
        │                                            │   SUA CHAVE (par de chaves)
```

- **Chave do host** — pertence ao servidor. Prova que "192.168.0.239 é mesmo a Pi que
  você espera", não um impostor respondendo naquele IP.
- **Seu par de chaves** — pertence a você. Prova "eu sou o usuário que tem permissão de
  entrar", sem nunca revelar uma senha pela rede.

As seções abaixo resolvem uma pergunta de cada vez, na ordem em que fizemos.

---

## 2. Antes de tudo: o SSH precisa estar ligado na Pi

Desde 2016 o Raspberry Pi OS vem com o serviço SSH **desabilitado por padrão** (motivo
de segurança — evita que qualquer Pi na internet aceite conexão com a senha padrão
antiga). Se você nunca conectou numa Pi específica, é bem provável que precise habilitar
primeiro.

**Com acesso físico (monitor + teclado na Pi):**

```bash
sudo raspi-config
# → 3 Interface Options → I2 SSH → Yes
```

ou, mais direto, sem menu:

```bash
sudo systemctl enable --now ssh
```

**Sem acesso físico, Pi ainda não ligada:** retire o cartão SD, coloque em outro
computador, e crie um arquivo **vazio** chamado `ssh` (sem extensão) na partição `boot`.
Na primeira inicialização, o Raspberry Pi OS detecta esse arquivo, habilita o SSH
sozinho e o remove.

> No nosso caso a Pi (`RaspPoto`) já tinha o SO instalado e o SSH ativo — só faltava o
> primeiro acesso.

---

## 3. Gerar seu par de chaves (só uma vez, serve para qualquer servidor)

```bash
ssh-keygen -t ed25519 -C "seu-email@exemplo.com" -f ~/.ssh/id_ed25519 -N ""
```

| Parte do comando | O que faz |
|---|---|
| `-t ed25519` | algoritmo de chave — moderno, rápido, chave pequena |
| `-C "..."` | um comentário só para identificar a chave depois (aparece em `ssh-add -l`) |
| `-f ~/.ssh/id_ed25519` | onde salvar |
| `-N ""` | **sem senha na chave** — trade-off de conveniência por segurança (ver §7) |

Isso cria dois arquivos ligados matematicamente:

| Arquivo | Nome | Quem pode ver |
|---|---|---|
| `~/.ssh/id_ed25519` | chave **privada** | **ninguém além de você** — nunca sai desta máquina |
| `~/.ssh/id_ed25519.pub` | chave **pública** | qualquer um — é feita para ser distribuída |

A mágica da criptografia assimétrica: qualquer servidor com a sua chave **pública**
consegue conferir uma assinatura feita pela sua chave **privada**, sem que a privada
jamais trafegue pela rede. Você prova quem é sem revelar o segredo.

### Carregar a chave no agente

```bash
ssh-add ~/.ssh/id_ed25519
```

O `ssh-agent` é um processo que já roda em background na sua sessão. Ele guarda a
chave privada descriptografada em memória, então o SSH não precisa pedir a senha da
chave toda vez que você conecta em algo — ele consulta o agente.

```bash
ssh-add -l
# 256 SHA256:x7/GW... kaua.mach.dev@gmail.com (ED25519)
```

Se aparecer "The agent has no identities", a chave existe mas não foi carregada — rode
o `ssh-add` de novo.

---

## 4. Confiar na chave do host (a Pi)

Antes de mandar qualquer coisa, o SSH quer confirmar que o dispositivo respondendo em
`192.168.0.239` é realmente a sua Pi.

```bash
ssh-keyscan -t ed25519 192.168.0.239
```

Isso **baixa** a chave pública que o servidor apresenta — mas baixar não é a mesma coisa
que confiar. Existem dois níveis de rigor, dependendo de o servidor ser público ou seu:

### Para um serviço público (ex.: GitHub) — verificação auditável

O GitHub publica os fingerprints oficiais das próprias chaves numa API. Dá para
comparar o que foi baixado com o que é publicamente conhecido, **antes** de confiar:

```bash
ssh-keygen -lf <arquivo-baixado>              # calcula o fingerprint do que foi baixado
curl -s https://api.github.com/meta \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['ssh_key_fingerprints'])"
```

Se os dois fingerprints baterem, você tem certeza matemática de que não é um impostor
no meio do caminho.

### Para um dispositivo na sua própria rede (a Pi) — TOFU

Não existe um "registro público" com o fingerprint oficial da sua Pi doméstica. Aqui a
prática padrão é **TOFU** — *trust on first use*, confiar na primeira vez:

```bash
ssh-keyscan -t ed25519 192.168.0.239 >> ~/.ssh/known_hosts
```

Você está assumindo que ninguém está interceptando sua rede local naquele instante
exato — razoável para uma rede doméstica/laboratório, onde o risco de alguém já estar
de tocaia especificamente esperando você ligar aquela Pi é próximo de zero.

> **O que esse arquivo garante daqui em diante:** da segunda conexão em diante, o SSH
> compara a chave que o servidor apresenta com a que está salva em `known_hosts`. Se for
> diferente — por exemplo, você reinstalou o SO da Pi, ou (cenário ruim) alguém está
> tentando se passar por ela — o SSH **recusa a conexão** e mostra um aviso do tipo
> `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`. Isso não é um bug: é a proteção
> funcionando. Se você mesmo reinstalou o sistema, é preciso remover a linha antiga de
> `known_hosts` para poder confiar na chave nova.

---

## 5. Autorizar sua chave na Pi

Até aqui resolvemos "a Pi é quem diz ser". Falta resolver "eu sou quem posso entrar".

```bash
ssh-copy-id raspoto@192.168.0.239
```

O que esse comando faz, por trás:

1. Pega sua chave pública (`~/.ssh/id_ed25519.pub`)
2. Conecta na Pi usando **senha** (a única forma de entrar, já que sua chave ainda não
   está autorizada lá)
3. Acrescenta o conteúdo da chave pública no arquivo
   `/home/raspoto/.ssh/authorized_keys` **da Pi**
4. A partir daí, qualquer conexão SSH que apresente a chave privada correspondente
   entra **sem pedir senha**

Ele pede a senha do usuário `raspoto` **uma única vez** — é o último momento em que essa
senha é necessária.

---

## 6. Conectar

```bash
ssh raspoto@192.168.0.239
```

Ou, testando sem interação (útil para confirmar que a chave funciona, sem cair para
pedido de senha por engano):

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 raspoto@192.168.0.239 "echo conectado"
```

`BatchMode=yes` faz o SSH **falhar** em vez de perguntar senha, caso a chave não esteja
autorizada — bom para scripts e para diagnosticar.

---

## 7. Atalho: `~/.ssh/config`

Digitar usuário, IP e caminho da chave toda vez cansa. Um bloco em `~/.ssh/config`
resolve:

```
Host poto-pi
    HostName 192.168.0.239
    User raspoto
    IdentityFile ~/.ssh/id_ed25519
```

Depois disso, a conexão inteira vira:

```bash
ssh poto-pi
```

Cada `Host` é um apelido; você pode ter quantos quiser, um por servidor.

---

## 8. E se o IP da Pi mudar?

Vai mudar — a maioria dos roteadores empresta IP por DHCP, e ele pode variar a cada
reboot ou reconexão. Duas coisas reagem de formas diferentes:

| Depende do IP? | |
|---|---|
| `~/.ssh/config` com `HostName <ip fixo>` | **sim** — quebra, `ssh poto-pi` some |
| `known_hosts` (a chave que você confia) | **não** — está ligada ao servidor de verdade, não ao endereço |

Ou seja: mudar o IP **não** dispara aquele aviso de "possível ataque, chave mudou" —
você só recebe "não consigo conectar". Ao tentar pelo IP novo, é tratado como servidor
desconhecido de novo (TOFU de novo).

### A correção: usar o nome mDNS no lugar do IP

```
Host poto-pi
    HostName RaspPoto.local     # não 192.168.0.239
    User raspoto
    IdentityFile ~/.ssh/id_ed25519
```

Como o `avahi-daemon` da Pi reanuncia `RaspPoto.local` sempre que ela liga — apontando
para o IP que ela tiver **naquele momento** — o atalho sobrevive a qualquer troca de IP
sem precisar editar nada. **Foi o que fizemos neste projeto.**

**Só que isso exige um passo extra**, porque para o SSH o nome é uma entrada de
`known_hosts` **diferente** do IP, mesmo sendo o mesmo servidor:

```bash
# 1. confira que é de fato a mesma Pi: o fingerprint deve ser IDÊNTICO ao que já
#    confiamos via IP
ssh-keyscan -t ed25519 RaspPoto.local | ssh-keygen -lf -
grep "192.168.0.239" ~/.ssh/known_hosts | ssh-keygen -lf -

# 2. só depois de bater, adiciona a entrada do nome
ssh-keyscan -t ed25519 RaspPoto.local >> ~/.ssh/known_hosts
```

Isso importa porque, se algum dia o fingerprint **não bater**, é sinal de que outro
dispositivo está respondendo por aquele nome na rede — vale investigar antes de seguir.

> **Isso não funciona fora da sua rede local.** mDNS só resolve dentro do mesmo segmento
> de rede. Se a Pi for para outra rede (ex.: o campus, no dia da demo), o nome `.local`
> para de resolver e a única saída é ou repetir o processo com IP fixo/reserva de DHCP,
> ou usar mDNS também naquela rede — é o mesmo problema que o tablet do totem vai
> enfrentar para achar a Pi (ver `ARCHITECTURE.md`, tarefa de endereçamento estável).

---

## 10. Bônus: descobrir a Pi na rede sem saber o IP

Se você não sabe o IP, mas sabe que a Pi está ligada na mesma rede:

```bash
ping RaspPoto.local        # mDNS: Raspberry Pi OS anuncia o próprio hostname + .local
```

O `avahi-daemon` (que já vem ativo por padrão no Raspberry Pi OS) responde por esse
nome na rede local, sem precisar descobrir o IP manualmente no roteador.

---

## 11. Checklist resumido (o que fizemos, em ordem)

```
1. sudo systemctl enable --now ssh          # na Pi, uma vez (se ainda não estava ativo)
2. ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""   # gerar seu par de chaves
3. ssh-add ~/.ssh/id_ed25519                # carregar no agente
4. ssh-keyscan -t ed25519 <ip> >> ~/.ssh/known_hosts   # confiar no host (TOFU p/ LAN)
5. ssh-copy-id <usuario>@<ip>               # autorizar sua chave pública (pede senha 1x)
6. ssh <usuario>@<ip>                       # conectar, sem senha daqui em diante
7. (opcional) editar ~/.ssh/config          # criar o atalho `ssh poto-pi`
```

## 12. Erros comuns e o que significam

| Mensagem | Causa | O que fazer |
|---|---|---|
| `Permission denied (publickey,password)` | sua chave ainda não está em `authorized_keys` no servidor | rode `ssh-copy-id` |
| `Host key verification failed` | a chave do host não está em `known_hosts` (ou mudou) | `ssh-keyscan` para adicionar; se você reinstalou o SO, remova a linha antiga primeiro |
| `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` | a chave que o servidor apresenta é diferente da salva | **pare e investigue** antes de simplesmente aceitar — pode ser reinstalação legítima ou algo errado na rede |
| `ssh_askpass: exec(...): No such file or directory` | o SSH tentou abrir uma janela gráfica para confirmar algo (geralmente a chave do host), mas não há ambiente gráfico disponível | resolva a causa raiz (adicione a chave do host manualmente com `ssh-keyscan`) em vez de tentar contornar o askpass |
| `Number of key(s) added: 0` no `ssh-copy-id` | a chave já estava autorizada | nada a fazer — já funciona |

---

## Referência real deste projeto

| Item | Valor |
|---|---|
| Hostname | `RaspPoto` (`RaspPoto.local` por mDNS) |
| IP na rede local (no momento do setup) | `192.168.0.239` — pode mudar, ver §8 |
| Usuário | `raspoto` |
| Atalho configurado | `ssh poto-pi` → aponta para `RaspPoto.local`, não para o IP |
| Hardware confirmado | Raspberry Pi 5 Model B Rev 1.0, 7.9 GB RAM |
| SO | Debian 13 (trixie), kernel `6.18.39-rpi-2712`, aarch64 |
