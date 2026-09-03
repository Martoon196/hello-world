#!/usr/bin/env bash
# One-shot Caddy install for members.apexcode.uk -> betbot (127.0.0.1:8080).
# Idempotent: safe to re-run.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (this box logs in as root already)." >&2
  exit 1
fi

echo "==> Installing Caddy..."
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl >/dev/null
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  > /etc/apt/sources.list.d/caddy-stable.list
apt-get update >/dev/null
apt-get install -y caddy >/dev/null

echo "==> Writing /etc/caddy/Caddyfile..."
cat > /etc/caddy/Caddyfile <<'EOF'
members.apexcode.uk {
    reverse_proxy 127.0.0.1:8080
}
EOF

echo "==> Starting Caddy..."
systemctl enable --now caddy
systemctl reload caddy

echo "==> Restarting betbot..."
systemctl restart betbot
sleep 3

echo
echo "==> Status:"
systemctl is-active caddy betbot || true
echo
if [[ "$(systemctl is-active caddy)" == "active" && "$(systemctl is-active betbot)" == "active" ]]; then
  echo "ALL GOOD — now open https://members.apexcode.uk on your phone."
  echo "(If the padlock isn't there yet, DNS is still spreading — try again in 30-60 min.)"
else
  echo "SOMETHING'S OFF — send Claude the output above."
fi
