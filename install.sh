#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  printf 'Run this installer with sudo: sudo ./install.sh\n' >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  printf 'Cannot identify this operating system.\n' >&2
  exit 1
fi
# shellcheck disable=SC1091 -- validated as readable immediately above
. /etc/os-release
case "${ID:-}:${ID_LIKE:-}" in
  *debian*|*ubuntu*) ;;
  *)
    printf 'Supported systems are MX Linux, Debian, and Ubuntu. Detected: %s\n' "${PRETTY_NAME:-unknown}" >&2
    exit 1
    ;;
esac

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${LIVE_THERAPY_APP_DIR:-/opt/live-ai-therapy}"
DATA_DIR="${LIVE_THERAPY_DATA_DIR:-/var/lib/live-ai-therapy}"
CONFIG_DIR="${LIVE_THERAPY_CONFIG_DIR:-/etc/live-ai-therapy}"
ENV_FILE="$CONFIG_DIR/live-ai-therapy.env"
SERVICE_USER="live-ai-therapy"

default_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
default_ip="${default_ip:-127.0.0.1}"
if [[ $default_ip =~ ^([0-9]+\.[0-9]+\.[0-9]+)\.[0-9]+$ ]]; then
  default_cidr="${BASH_REMATCH[1]}.0/24"
else
  default_cidr="192.168.1.0/24"
fi

read -rp "Local hostname [live-therapy.local]: " APP_HOST
APP_HOST="${APP_HOST:-live-therapy.local}"
read -rp "LAN IP [$default_ip]: " LAN_IP
LAN_IP="${LAN_IP:-$default_ip}"
read -rp "LAN CIDR [$default_cidr]: " LAN_CIDR
LAN_CIDR="${LAN_CIDR:-$default_cidr}"

if [[ ! $APP_HOST =~ ^[A-Za-z0-9.-]+$ ]] || [[ ! $LAN_IP =~ ^[0-9a-fA-F:.]+$ ]] || [[ ! $LAN_CIDR =~ ^[0-9a-fA-F:./]+$ ]]; then
  printf 'Hostname, LAN IP, or CIDR contains unsupported characters.\n' >&2
  exit 1
fi

existing_value() {
  local key="$1"
  [[ -f $ENV_FILE ]] || return 0
  awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE"
}

read_secret() {
  local label="$1" key="$2" current value
  current="$(existing_value "$key")"
  if [[ -n $current ]]; then
    read -rsp "$label [press Enter to keep current]: " value
  else
    read -rsp "$label: " value
  fi
  printf '\n' >&2
  value="${value:-$current}"
  if [[ -z $value ]]; then
    printf '%s is required.\n' "$label" >&2
    exit 1
  fi
  printf '%s' "$value"
}

OPENAI_API_KEY="$(read_secret 'OpenAI API key' OPENAI_API_KEY)"
ELEVENLABS_API_KEY="$(read_secret 'ElevenLabs API key' ELEVENLABS_API_KEY)"
ELEVENLABS_VOICE_ID="$(read_secret 'ElevenLabs voice ID' ELEVENLABS_VOICE_ID)"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip rsync curl ca-certificates caddy avahi-daemon avahi-utils ufw

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA_DIR" --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -m 755 "$APP_DIR" "$CONFIG_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 700 "$DATA_DIR" "$DATA_DIR/chroma" "$DATA_DIR/audio_tmp"
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='.env' \
  --exclude='.venv/' \
  --exclude='data/' \
  --exclude='certs/' \
  --exclude='config/personas/Sandy.jpeg' \
  --exclude='config/personas/*.local.md' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  "$SOURCE_DIR/" "$APP_DIR/"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

umask 077
cat >"$ENV_FILE" <<EOF
OPENAI_API_KEY=$OPENAI_API_KEY
ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID=$ELEVENLABS_VOICE_ID
DATABASE_URL=sqlite:////var/lib/live-ai-therapy/app.db
VECTOR_DB_PATH=/var/lib/live-ai-therapy/chroma
AUDIO_TMP_PATH=/var/lib/live-ai-therapy/audio_tmp
DEBUG_STORE_AUDIO=false
MEMORY_DEBUG_ENABLED=false
GENERATED_AUDIO_TTL_SECONDS=600
PERSONA_FILE=
EOF
chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"

sed \
  -e "s|@SERVICE_USER@|$SERVICE_USER|g" \
  -e "s|@APP_DIR@|$APP_DIR|g" \
  -e "s|@ENV_FILE@|$ENV_FILE|g" \
  -e "s|@DATA_DIR@|$DATA_DIR|g" \
  "$APP_DIR/ops/live-therapy.service.template" >/etc/systemd/system/live-therapy.service
sed "s|@APP_HOST@|$APP_HOST|g" "$APP_DIR/ops/Caddyfile.template" >/etc/caddy/Caddyfile
sed \
  -e "s|@APP_HOST@|$APP_HOST|g" \
  -e "s|@LAN_IP@|$LAN_IP|g" \
  "$APP_DIR/ops/live-therapy-mdns.service.template" >/etc/systemd/system/live-therapy-mdns.service

systemctl daemon-reload
systemctl enable --now avahi-daemon live-therapy.service live-therapy-mdns.service caddy
ufw allow from "$LAN_CIDR" to any port 443 proto tcp comment 'Live AI Therapy HTTPS'
if ufw status | grep -q '^Status: active'; then
  ufw reload
fi

for _ in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8088/api/health >/dev/null; then
    break
  fi
  sleep 1
done
curl --fail --silent http://127.0.0.1:8088/api/health >/dev/null

install -d -m 755 "$APP_DIR/certs"
CA_SOURCE=/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt
if [[ -f $CA_SOURCE ]]; then
  install -m 644 "$CA_SOURCE" "$APP_DIR/certs/live-therapy-local-ca.crt"
fi

printf '\nLive AI Therapy is running at https://%s\n' "$APP_HOST"
printf 'Trust %s/certs/live-therapy-local-ca.crt on each client before granting microphone access.\n' "$APP_DIR"
printf 'If UFW was inactive, review the rule and enable it explicitly with: sudo ufw enable\n'
