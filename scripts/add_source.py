"""Register a tip source (whitelist entry).

Usage:
  python scripts/add_source.py telegram -1001234567890 "Tipster John VIP" --whitelist
  python scripts/add_source.py whatsapp "Johns Tips Group" "John WhatsApp" --whitelist --multiplier 0.5 --floor 0.2
  python scripts/add_source.py --list
"""
from __future__ import annotations

import argparse

from betbot.config import secrets
from betbot.db.database import connect, migrate
from betbot.db.repo import Repo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("platform", nargs="?", choices=["telegram", "whatsapp"])
    ap.add_argument("chat_id", nargs="?")
    ap.add_argument("display_name", nargs="?")
    ap.add_argument("--sender", default=None, help="restrict to one sender id (default: any in chat)")
    ap.add_argument("--whitelist", action="store_true")
    ap.add_argument("--multiplier", type=float, default=1.0)
    ap.add_argument("--floor", type=float, default=None, help="price floor pct, e.g. 0.2 (blank = global default)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    conn = connect(secrets().betbot_db_path)
    migrate(conn)
    repo = Repo(conn)

    if args.list or not args.platform:
        for s in repo.list_sources():
            wl = "WHITELISTED" if s["is_whitelisted"] else "not whitelisted"
            print(f"[{s['id']}] {s['platform']} {s['chat_id']} sender={s['sender_id']} "
                  f"'{s['display_name']}' {wl} x{s['stake_multiplier']} floor={s['price_floor_pct']}")
        return

    source_id = repo.add_source(args.platform, args.chat_id, args.sender, args.display_name,
                                is_whitelisted=args.whitelist, stake_multiplier=args.multiplier,
                                price_floor_pct=args.floor)
    print(f"added source {source_id}")


if __name__ == "__main__":
    main()
