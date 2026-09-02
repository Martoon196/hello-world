#!/usr/bin/env bash
# betbot one-command server setup. Safe to re-run any time.
#
#   cd /root/betbot && git pull && bash setup.sh
#
# or on a completely fresh server:
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/Martoon196/hello-world/claude/horse-betting-bot-research-0l9lei/setup.sh)
#
set -e

REPO_URL="https://github.com/Martoon196/hello-world.git"
BRANCH="claude/horse-betting-bot-research-0l9lei"
DIR="/root/betbot"
ENV="$DIR/.env"

say()  { printf "\n\033[1;32m== %s\033[0m\n" "$*"; }
ask()  { local prompt="$1" var="$2" current
         current=$(grep -E "^$var=" "$ENV" | head -1 | cut -d= -f2-)
         if [ -n "$current" ]; then
           printf "  %s [press Enter to keep what's saved]: " "$prompt"
         else
           printf "  %s: " "$prompt"
         fi
         read -r value
         # Strip invisible control characters (Esc/arrow-key noise) and edge spaces
         value=$(printf '%s' "$value" | tr -d '[:cntrl:]' | sed 's/^ *//; s/ *$//')
         if [ -n "$value" ]; then
           python3 - "$ENV" "$var" "$value" <<'PY'
import sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines()
out, done = [], False
for line in lines:
    if line.startswith(key + "="):
        out.append(f"{key}={value}"); done = True
    else:
        out.append(line)
if not done:
    out.append(f"{key}={value}")
open(path, "w").write("\n".join(out) + "\n")
PY
         fi }

say "1/7 Installing system packages (this is quick)"
apt-get update -qq
apt-get install -y -qq git python3-venv python3.12-venv python3-pip > /dev/null

say "2/7 Getting the betbot code"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch origin "$BRANCH" -q && git -C "$DIR" checkout -q "$BRANCH" && git -C "$DIR" pull -q origin "$BRANCH"
else
  git clone -q "$REPO_URL" "$DIR"
  git -C "$DIR" checkout -q "$BRANCH"
fi
cd "$DIR"

say "3/7 Installing betbot's Python ingredients (takes a couple of minutes)"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -e "$DIR"

say "4/7 Creating the secrets file"
[ -f "$ENV" ] || cp .env.example "$ENV"
chmod 600 "$ENV"
for k in FEED_TOKEN WHATSAPP_WEBHOOK_TOKEN BFBM_RESULTS_TOKEN; do
  if ! grep -qE "^$k=.+" "$ENV"; then
    t=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
    python3 - "$ENV" "$k" "$t" <<'PY'
import sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines()
out, done = [], False
for line in lines:
    if line.startswith(key + "="):
        out.append(f"{key}={value}"); done = True
    else:
        out.append(line)
if not done:
    out.append(f"{key}={value}")
open(path, "w").write("\n".join(out) + "\n")
PY
  fi
done

say "5/7 Your five secrets (typing is VISIBLE here — paste each one and press Enter)"
echo "  (Anything already saved is kept if you just press Enter.)"
ask "Telegram api_id (the number from my.telegram.org)"      TELEGRAM_API_ID
ask "Telegram api_hash (the long jumble)"                    TELEGRAM_API_HASH
ask "Bot token (from BotFather, has a colon in it)"          TELEGRAM_BOT_TOKEN
ask "Your chat id (the number from @userinfobot)"            TELEGRAM_ADMIN_CHAT_ID
ask "Anthropic API key (starts sk-ant-)"                     ANTHROPIC_API_KEY
ask "Dashboard password (username will be 'betbot'; protects the web dashboard)" DASHBOARD_PASSWORD
echo "  Betfair (press Enter to skip any you don't have yet):"
ask "Betfair username"                                       BETFAIR_USERNAME
ask "Betfair password"                                       BETFAIR_PASSWORD
ask "Betfair app key (the DELAYED one)"                      BETFAIR_APP_KEY

say "6/7 First Telegram login (a code will arrive IN your Telegram app)"
if .venv/bin/python - <<'PY'
from telethon.sync import TelegramClient
from betbot.config import secrets
s = secrets()
c = TelegramClient(s.telegram_session_name, s.telegram_api_id, s.telegram_api_hash)
c.connect()
ok = c.is_user_authorized()
c.disconnect()
raise SystemExit(0 if ok else 1)
PY
then
  echo "  Already logged in — skipping."
else
  rm -f "$DIR"/betbot.session*
  .venv/bin/python scripts/telegram_login.py
fi

say "7/7 Making betbot run forever (starts on boot, restarts if it crashes)"
cat > /etc/systemd/system/betbot.service <<EOF
[Unit]
Description=betbot
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python -m betbot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q betbot
systemctl restart betbot
sleep 3

IP=$(curl -fsS -4 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
if systemctl is-active -q betbot; then
  say "DONE! betbot is alive 🎉"
  echo "  • Check your Telegram — the bot should have messaged you: '🟢 betbot started'"
  echo "  • Dashboard: http://$IP:8080"
  echo "  • It's in SHADOW (paper) mode — watching, not betting."
  echo "  • Useful later:  systemctl status betbot   |   journalctl -u betbot -f"
else
  say "Hmm — betbot didn't stay up. Show Claude the output of:"
  echo "  journalctl -u betbot -n 30 --no-pager"
fi
