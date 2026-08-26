"""Interactive tipster registration: lists your Telegram groups/channels and
whitelists the ones you pick as tip sources.

Stop betbot first (the Telegram session file can't be shared):
    systemctl stop betbot
    .venv/bin/python scripts/setup_sources.py
    systemctl start betbot
"""
from __future__ import annotations

import sqlite3

from telethon.sync import TelegramClient

from betbot.config import secrets
from betbot.db.database import connect, migrate
from betbot.db.repo import Repo


def main() -> None:
    s = secrets()
    conn = connect(s.betbot_db_path)
    migrate(conn)
    repo = Repo(conn)
    registered = {(row["platform"], row["chat_id"]) for row in repo.list_sources()}

    with TelegramClient(s.telegram_session_name, s.telegram_api_id, s.telegram_api_hash) as client:
        dialogs = [d for d in client.iter_dialogs() if d.is_group or d.is_channel]

        print("\nYour Telegram groups & channels:\n")
        for i, d in enumerate(dialogs, 1):
            mark = "  [TIPSTER ✔]" if ("telegram", str(d.id)) in registered else ""
            print(f"  {i:3d}. {d.name}{mark}")

        print("\nType the NUMBER of a group to register it as a tipster, then Enter.")
        print("Repeat for each one. Just press Enter on its own when you're done.\n")

        while True:
            choice = input("Number (or Enter to finish): ").strip()
            if not choice:
                break
            if not choice.isdigit() or not 1 <= int(choice) <= len(dialogs):
                print("  That's not one of the numbers above — try again.")
                continue
            d = dialogs[int(choice) - 1]
            try:
                repo.add_source("telegram", str(d.id), None, d.name, is_whitelisted=True)
                print(f"  ✔ '{d.name}' registered — its tips will now be processed.")
            except sqlite3.IntegrityError:
                print(f"  '{d.name}' is already registered.")

    print("\nDone. Registered tipsters:")
    for row in repo.list_sources():
        wl = "ACTIVE" if row["is_whitelisted"] else "not whitelisted"
        print(f"  - {row['display_name']} ({row['platform']}) [{wl}]")
    print("\nNow run:  systemctl start betbot")


if __name__ == "__main__":
    main()
