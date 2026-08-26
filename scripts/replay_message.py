"""Re-run the parser on a stored raw_message (debugging / parser tuning).

Usage: python scripts/replay_message.py <raw_message_id>
Prints the structured parse; does NOT create tips or bets.
"""
from __future__ import annotations

import sys

from betbot.config import secrets
from betbot.db.database import connect, migrate
from betbot.db.repo import Repo
from betbot.parsing.claude_parser import parse_message


def main() -> None:
    raw_id = int(sys.argv[1])
    conn = connect(secrets().betbot_db_path)
    migrate(conn)
    raw = Repo(conn).get_raw_message(raw_id)
    if raw is None:
        sys.exit(f"raw_message {raw_id} not found")
    print(f"--- raw message {raw_id} ({raw['platform']}, status={raw['status']}) ---")
    print(raw["message_text"] or f"[image: {raw['image_path']}]")
    print("--- parse ---")
    parsed = parse_message(raw["message_text"], raw["image_path"])
    print(parsed.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
