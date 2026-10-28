#!/usr/bin/env bash
# One-shot upgrade for the members server: latest code, dependencies, the
# Paddock shared secret, restart, health check. Safe to re-run.
# Secrets (.env), the database (data/) and the Telegram session are untracked,
# so the hard reset below never touches them.
set -euo pipefail
cd /root/betbot
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "==> Fetching the latest code ($BRANCH)..."
git fetch -q origin "$BRANCH"
git reset -q --hard "origin/$BRANCH"

echo "==> Installing dependencies..."
.venv/bin/pip install -q -e /root/betbot

if ! grep -qE '^PADDOCK_SHARED_SECRET=.+' .env; then
  echo "==> Creating the Paddock shared secret..."
  t=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
  sed -i '/^PADDOCK_SHARED_SECRET=/d' .env
  echo "PADDOCK_SHARED_SECRET=$t" >> .env
fi

echo "==> Restarting betbot..."
systemctl restart betbot
sleep 6

echo
if [ "$(systemctl is-active betbot)" = "active" ] \
   && curl -fsS https://members.apexcode.uk/public/stats.json >/dev/null; then
  echo "ALL GOOD — betbot is running the new version."
else
  echo "SOMETHING'S OFF — send Claude this output plus:"
  echo "  journalctl -u betbot -n 40 --no-pager"
  exit 1
fi
echo
echo "Copy this line into apex-config.php on SiteGround (Step 2 of the instructions):"
echo
echo "define('PADDOCK_SHARED_SECRET', '$(grep '^PADDOCK_SHARED_SECRET=' .env | cut -d= -f2-)');"
