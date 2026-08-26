"""One-time interactive Telegram login: creates the saved session file.

Telethon asks for your phone number (with country code, e.g. +447700900123),
then the login code Telegram sends to your Telegram app. Run via setup.sh or:
    .venv/bin/python scripts/telegram_login.py
"""
from telethon.sync import TelegramClient

from betbot.config import secrets


def main() -> None:
    s = secrets()
    if not s.telegram_api_id or not s.telegram_api_hash:
        raise SystemExit("Telegram api_id/api_hash missing from .env — run setup.sh again.")
    with TelegramClient(s.telegram_session_name, s.telegram_api_id, s.telegram_api_hash) as client:
        me = client.get_me()
        print(f"Logged in as {me.first_name} — session saved. This won't be asked again.")


if __name__ == "__main__":
    main()
