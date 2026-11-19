#!/usr/bin/env bash
# Dùng: bash 01_ssh.sh <IP> <PORT>   (lấy ở Connect -> SSH over exposed TCP)
# Chạy lại mỗi khi pod Start lại hoặc đổi pod, vì IP/PORT thay đổi.
set -euo pipefail
IP=${1:-${IP:?Dùng: bash 01_ssh.sh <IP> <PORT>}}; PORT=${2:-${PORT:?Dùng: bash 01_ssh.sh <IP> <PORT>}}
cat > ~/.ssh/runpod-p1p2.conf <<CONF
Host runpod-p1p2
  HostName $IP
  Port $PORT
  User root
  IdentityFile ~/.ssh/runpod_ed25519
  ServerAliveInterval 30
CONF
chmod 600 ~/.ssh/runpod-p1p2.conf
grep -qxF 'Include ~/.ssh/runpod-p1p2.conf' ~/.ssh/config 2>/dev/null ||
  { printf 'Include ~/.ssh/runpod-p1p2.conf\n%s' "$(cat ~/.ssh/config 2>/dev/null)" > ~/.ssh/config.new && mv ~/.ssh/config.new ~/.ssh/config; chmod 600 ~/.ssh/config; }
ssh runpod-p1p2 'nvidia-smi --query-gpu=name,memory.total --format=csv; df -h /workspace'
