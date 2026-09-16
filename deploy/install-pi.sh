#!/usr/bin/env bash
#
# P.O.T.O — preparação da Raspberry Pi.
#
# Nesta versão (MVP-067b) o script cuida do **endereçamento**: o tablet abre uma
# URL fixa e ela não pode mudar a cada reboot. A instalação das dependências, o
# treino do classificador e a unit systemd entram na MVP-069.
#
# Idempotente: rodar duas vezes não quebra nada.
#
#   bash deploy/install-pi.sh
#
set -euo pipefail

PORTA="${POTO_PORTA:-8000}"

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

# --- mDNS -------------------------------------------------------------------
#
# O mDNS é o que faz `<hostname>.local` resolver sem servidor de DNS nem IP
# decorado. É a diferença entre o tablet ter um atalho que funciona sempre e
# alguém ter que redigitar um IP depois de cada reboot do roteador.

titulo "mDNS (avahi)"

if ! command -v avahi-daemon >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "  instalando avahi-daemon…"
    sudo apt-get update -qq
    sudo apt-get install -y -qq avahi-daemon avahi-utils
    ok "avahi-daemon instalado"
  else
    erro "avahi-daemon ausente e sem apt-get para instalar."
    exit 1
  fi
else
  ok "avahi-daemon já instalado"
fi

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
# O mDNS falha em dois casos reais: rede que bloqueia multicast (comum em wifi
# corporativo/universitário) e cliente sem suporte. O IP é o plano B, e precisa
# ser **estável** — um IP por DHCP muda quando o roteador reinicia.

titulo "Plano B: IP estável"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -z "${IP}" ]]; then
  erro "Sem endereço IP. A Pi está conectada à rede?"
  exit 1
fi
ok "IP atual: ${IP}"

echo ""
echo "  Para fixá-lo — escolha UM:"
echo ""
echo "  a) Reserva no roteador (preferido: nada muda na Pi)"
echo "     Reservar ${IP} para o MAC $(cat /sys/class/net/$(ip route show default | awk '{print $5; exit}')/address 2>/dev/null || echo '<mac>')"
echo ""
echo "  b) Estático na Pi, via NetworkManager:"
echo "     sudo nmcli con mod \"\$(nmcli -g NAME con show --active | head -1)\" \\"
echo "       ipv4.addresses ${IP}/24 ipv4.gateway $(ip route show default | awk '{print $3; exit}') \\"
echo "       ipv4.dns 1.1.1.1 ipv4.method manual"
echo "     sudo nmcli con up \"\$(nmcli -g NAME con show --active | head -1)\""

# --- URLs -------------------------------------------------------------------
#
# As **duas** URLs, e é o critério da task: a de mDNS é a que se aponta o
# tablet; a de IP é a que funciona quando o multicast não passa. Imprimir só
# uma deixaria a pessoa sem saída no momento em que a primeira falhasse.

titulo "Aponte o tablet para"

echo ""
echo "    http://${NOME}.local:${PORTA}      (mDNS — preferido)"
echo "    http://${IP}:${PORTA}$(printf '%*s' $(( ${#NOME} - ${#IP} + 6 )) '')(IP — plano B)"
echo ""
echo "  Conferir de outro dispositivo da rede:"
echo "    curl http://${NOME}.local:${PORTA}/api/v1/health"
echo ""
