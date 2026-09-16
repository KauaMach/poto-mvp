#!/usr/bin/env bash
#
# P.O.T.O — preparação da Raspberry Pi.
#
# Transforma uma Pi limpa num totem. **Idempotente**: rodar duas vezes não
# quebra nada, e é assim que se conserta um estado meio-configurado.
#
#   bash deploy/install-pi.sh
#
# **Node NÃO é instalado.** O frontend é construído na máquina de
# desenvolvimento e enviado pronto por `make deploy` (MVP-066b). Isso poupa
# 133 MB e 700 arquivos na Pi, elimina uma toolchain que precisaria de
# manutenção, e dispensa internet no momento do deploy — o rsync vai pela LAN.
# Ver ARCHITECTURE.md D1c.
set -euo pipefail

PORTA="${POTO_PORTA:-8000}"
# O script vive em `deploy/`; a raiz do projeto é o diretório acima.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USUARIO="$(id -un)"

# --- Saída ------------------------------------------------------------------

azul() { printf '\033[36m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
aviso(){ printf '  \033[33m!\033[0m %s\n' "$*"; }
erro() { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; }

titulo() {
  echo ""
  azul "── $* ──"
}

# --- Verificações -----------------------------------------------------------

titulo "Onde estou"

if [[ ! -r /proc/device-tree/model ]]; then
  aviso "Não parece ser uma Raspberry Pi — seguindo de todo modo."
  aviso "O script é seguro fora dela, mas o avahi e o hostname são o ponto aqui."
else
  ok "$(tr -d '\0' < /proc/device-tree/model)"
fi

# --- Pacotes do sistema -----------------------------------------------------

titulo "Pacotes do sistema"

# `picamera2` vem do **apt**, não do pip: ele depende de `python3-libcamera`,
# que é um binding C++ compilado e não existe no PyPI. Declará-lo como
# dependência pip faria o extra `midia` falhar na Pi (ver `pyproject.toml`).
APT_PACOTES=(avahi-daemon avahi-utils rsync python3-picamera2)

if command -v apt-get >/dev/null 2>&1; then
  FALTANDO=()
  for pkg in "${APT_PACOTES[@]}"; do
    dpkg -s "$pkg" >/dev/null 2>&1 || FALTANDO+=("$pkg")
  done
  if (( ${#FALTANDO[@]} )); then
    echo "  instalando: ${FALTANDO[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${FALTANDO[@]}"
    ok "instalados: ${FALTANDO[*]}"
  else
    ok "todos presentes: ${APT_PACOTES[*]}"
  fi
else
  aviso "sem apt-get — pulando pacotes do sistema"
fi

# --- uv ---------------------------------------------------------------------

titulo "uv"

if ! command -v uv >/dev/null 2>&1 && [[ ! -x "$HOME/.local/bin/uv" ]]; then
  echo "  instalando uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ok "uv instalado"
else
  ok "uv já instalado"
fi
export PATH="$HOME/.local/bin:$PATH"
ok "uv $(uv --version 2>/dev/null | awk '{print $2}')"

# --- Ambiente Python --------------------------------------------------------
#
# Duas particularidades, e as duas são obrigatórias na Pi:
#
#   --system-site-packages     para o venv enxergar o `picamera2` do apt
#   --python /usr/bin/python3  porque o picamera2 do apt está instalado para o
#                              Python do sistema; um Python baixado pelo uv não
#                              o enxergaria nem com --system-site-packages

titulo "Ambiente Python"

cd "$RAIZ/backend"

# **Não basta o venv existir: ele precisa ter sido criado com a flag.**
#
# Um venv anterior, feito sem `--system-site-packages`, fica invisível para o
# `picamera2` do apt — e o sintoma é `ModoNotFoundError: No module named
# 'picamera2'` só quando alguém tenta abrir a câmera, muito depois da
# instalação. Encontrado na Pi real: o venv existia desde uma fase anterior do
# projeto e o `uv sync --extra midia` instalava o `sounddevice` com sucesso,
# dando a impressão de que a mídia estava pronta.
#
# `pyvenv.cfg` grava a flag, então a checagem é direta.
RECRIAR=0
if [[ ! -d .venv ]]; then
  RECRIAR=1
elif ! grep -qi "^include-system-site-packages\s*=\s*true" .venv/pyvenv.cfg 2>/dev/null; then
  aviso "venv existe SEM --system-site-packages — o picamera2 do apt ficaria invisível"
  rm -rf .venv
  RECRIAR=1
fi

if (( RECRIAR )); then
  uv venv --system-site-packages --python /usr/bin/python3
  ok "venv criado com --system-site-packages"
else
  ok "venv já correto (--system-site-packages)"
fi

# Idempotente e rápido: 7,7 s medidos em aarch64 no smoke test de 16/09, com
# wheels prontos nas mesmas versões do PC de desenvolvimento.
uv sync --extra midia
ok "dependências sincronizadas"

# --- Configuração -----------------------------------------------------------

titulo "Configuração"

if [[ ! -f .env ]]; then
  cp .env.example .env
  ok ".env criado a partir do exemplo"
  aviso "PREENCHA os contatos e o POTO_PAINEL_TOKEN — o /health lista o que falta."
else
  ok ".env já existe (preservado)"
fi

# --- Classificador ----------------------------------------------------------
#
# O artefato **não é versionado** (~2 MB de modelo binário que mudariam a cada
# treino). Sem ele a triagem cai na heurística de palavras-chave e o `/health`
# diz isso — mas com ele são 88% de acurácia em vez de palavras soltas.

titulo "Classificador de triagem"

if [[ -f app/data/triagem_clf.joblib ]]; then
  ok "artefato já treinado (apague para retreinar)"
else
  uv run python scripts/train_classificador.py
  ok "classificador treinado"
fi

# --- Serviço ----------------------------------------------------------------

titulo "Serviço systemd"

UNIT_ORIGEM="$RAIZ/deploy/poto-api.service"
UNIT_DESTINO=/etc/systemd/system/poto-api.service

if [[ ! -f "$UNIT_ORIGEM" ]]; then
  erro "unit não encontrada em $UNIT_ORIGEM"
  exit 1
fi

# Os caminhos da unit são absolutos e assumem `raspoto`/`~/poto-mvp`. O script
# ajusta para o usuário e o diretório **reais** em vez de exigir que coincidam:
# um install que só funciona num nome de usuário específico falha em silêncio
# no primeiro que não for.
sudo sed -e "s|^User=.*|User=${USUARIO}|" \
         -e "s|^Group=.*|Group=${USUARIO}|" \
         -e "s|/home/raspoto/poto-mvp|${RAIZ}|g" \
         "$UNIT_ORIGEM" | sudo tee "$UNIT_DESTINO" >/dev/null
sudo chmod 644 "$UNIT_DESTINO"
ok "unit instalada (usuário ${USUARIO}, raiz ${RAIZ})"

sudo systemctl daemon-reload
sudo systemctl enable poto-api >/dev/null 2>&1 || true
# `restart` e não só `enable --now`: numa segunda execução o serviço já está
# ativo com o código antigo, e `enable --now` não o reiniciaria.
sudo systemctl restart poto-api

sleep 3
if systemctl is-active --quiet poto-api; then
  ok "poto-api ativo"
else
  erro "poto-api não subiu. Veja: journalctl -u poto-api -n 40"
  exit 1
fi

# --- mDNS -------------------------------------------------------------------
#
# O mDNS é o que faz `<hostname>.local` resolver sem servidor de DNS nem IP
# decorado. É a diferença entre o tablet ter um atalho que funciona sempre e
# alguém ter que redigitar um IP depois de cada reboot do roteador.

titulo "mDNS (avahi)"

# A instalação já aconteceu na seção de pacotes; aqui é só garantir que está
# de pé.
# `enable --now` é idempotente: em serviço já ativo, não faz nada.
sudo systemctl enable --now avahi-daemon >/dev/null 2>&1 || true
if systemctl is-active --quiet avahi-daemon; then
  ok "avahi-daemon ativo"
else
  erro "avahi-daemon não subiu — 'systemctl status avahi-daemon' para ver por quê."
  exit 1
fi

# --- Hostname ---------------------------------------------------------------
#
# **O script NÃO troca o hostname por padrão.** O plano original previa `poto`,
# mas a Pi deste projeto se chama `RaspPoto` e é assim que ela aparece em
# `docs/conexao-ssh.md` e na memória de quem usa. Renomear silenciosamente
# quebraria o acesso SSH documentado e faria a próxima conexão falhar sem
# explicação.
#
# Para trocar de propósito:  sudo hostnamectl set-hostname poto
# (depois, atualizar `docs/conexao-ssh.md` e o `PI_HOST` do Makefile.)

titulo "Nome na rede"

NOME="$(hostname)"
ok "hostname: ${NOME}"

if command -v avahi-resolve >/dev/null 2>&1; then
  if avahi-resolve -n "${NOME}.local" >/dev/null 2>&1; then
    ok "${NOME}.local resolve"
  else
    # Não é erro fatal: o avahi pode levar alguns segundos para anunciar, e o
    # plano B (IP) continua valendo.
    aviso "${NOME}.local ainda não resolve — o avahi anuncia em alguns segundos."
  fi
fi

# --- Plano B: IP estável ----------------------------------------------------
#
# O mDNS não atravessa roteador: 224.0.0.251 vai com TTL 1, é link-local por
# desenho. Medido na UFPI (MVP-067b): o segmento da Pi tem mDNS funcionando, com
# 26 vizinhos anunciando — mas de outro /22 do campus o `.local` não resolve, por
# mais bem configurado que o avahi esteja. Some-se o cliente sem suporte a mDNS.
# O IP é o plano B, e precisa ser **estável** — um IP por DHCP muda quando o
# roteador reinicia.

titulo "Plano B: IP estável"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -z "${IP}" ]]; then
  erro "Sem endereço IP. A Pi está conectada à rede?"
  exit 1
fi
ok "IP atual: ${IP}"

# **A máscara é lida, não presumida.** Aqui havia `/24` chumbado, e na rede desta
# Pi o prefixo é /22 (10.13.60.159/22, gateway 10.13.63.250). Com /24, o gateway
# cai FORA da sub-rede calculada e o estático não roteia — quem seguisse a
# instrução derrubaria a rede de uma Pi headless e precisaria de acesso físico
# para voltar. É o tipo de erro que só aparece em rede cujo prefixo não é /24.
CIDR="$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | grep -m1 "^${IP}/" || true)"
: "${CIDR:=${IP}/24}"

echo ""
echo "  Para fixá-lo — escolha UM:"
echo ""
echo "  a) Reserva no roteador (preferido: nada muda na Pi)"
echo "     Reservar ${IP} para o MAC $(cat /sys/class/net/$(ip route show default | awk '{print $5; exit}')/address 2>/dev/null || echo '<mac>')"
echo ""
echo "  b) Estático na Pi, via NetworkManager:"
echo "     sudo nmcli con mod \"\$(nmcli -g NAME con show --active | head -1)\" \\"
echo "       ipv4.addresses ${CIDR} ipv4.gateway $(ip route show default | awk '{print $3; exit}') \\"
echo "       ipv4.dns 1.1.1.1 ipv4.method manual"
echo "     sudo nmcli con up \"\$(nmcli -g NAME con show --active | head -1)\""

# --- URLs -------------------------------------------------------------------
#
# As **duas** URLs, e é o critério da task: a de mDNS é a que se aponta o
# tablet; a de IP é a que funciona quando o multicast não passa. Imprimir só
# uma deixaria a pessoa sem saída no momento em que a primeira falhasse.

# --- Conferência ------------------------------------------------------------
#
# Perguntar ao próprio `/health` em vez de confiar no `systemctl`: um serviço
# "ativo" com o banco inacessível ou o classificador ausente está de pé **e
# degradado**, e é exatamente isso que o `/health` foi feito para contar
# (MVP-036).

titulo "Conferência"

SAUDE="$(curl -sf --max-time 10 "http://127.0.0.1:${PORTA}/api/v1/health" || true)"
if [[ -z "$SAUDE" ]]; then
  erro "a API não respondeu em 127.0.0.1:${PORTA}."
  erro "Veja: journalctl -u poto-api -n 40"
  exit 1
fi
ok "API respondendo"

# O JSON entra por **variável de ambiente**, não por stdin, para o heredoc poder
# ser citado (<<'PY'). Aqui havia um `python3 -c '...'` cujas f-strings usavam
# `\"` para escapar as aspas — e o bash, dentro de aspas simples, não processa a
# barra, então o Python recebia a barra literal e morria com
#
#   SyntaxError: unexpected character after line continuation character
#
# em toda execução. O `|| aviso` rebaixava isso a aviso e o script saía 0, então
# a conferência ficava quieta e quebrada. `bash -n` não vê Python embutido; só
# rodar de verdade na Pi expôs.
SAUDE="$SAUDE" python3 <<'PY' || aviso "não consegui formatar o /health"
import json, os

d = json.loads(os.environ["SAUDE"])
print("    banco:    " + ("ok" if d["banco"] else "NAO RESPONDE"))
print("    triagem:  " + d["triagem"]["modo"])
print("    notif:    " + d["notificacao"]["provider"])
montado = "montado" if d["frontend"]["montado"] else "AUSENTE - rode make deploy"
print(f"    frontend: {montado}  build-id {d['frontend']['build_id'] or '-'}")
if d["avisos"]:
    print()
    print("    avisos:")
    for aviso in d["avisos"]:
        print(f"      ! {aviso}")
PY

titulo "Aponte o tablet para"

# As duas colunas alinhadas a partir das URLs **já montadas**. O cálculo
# anterior usava ${#NOME} contra uma linha que imprime "${NOME}.local", e saía
# 6 colunas curto — o ".local" não entrava na conta.
URL_MDNS="http://${NOME}.local:${PORTA}"
URL_IP="http://${IP}:${PORTA}"
LARGURA=$(( ${#URL_MDNS} > ${#URL_IP} ? ${#URL_MDNS} : ${#URL_IP} ))

echo ""
printf '    %-*s  (mDNS — preferido)\n' "$LARGURA" "$URL_MDNS"
printf '    %-*s  (IP — plano B)\n'     "$LARGURA" "$URL_IP"
echo ""
echo "  Conferir de outro dispositivo da rede — o tablet precisa estar na MESMA"
echo "  rede da Pi para o .local resolver (mDNS não passa por roteador):"
echo "    curl ${URL_MDNS}/api/v1/health"
echo "    curl ${URL_IP}/api/v1/health      (de qualquer sub-rede que alcance)"
echo ""
