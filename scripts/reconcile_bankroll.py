"""Manual bankroll adjustment (deposit / withdrawal / correction vs real Betfair balance).

Usage:
  python scripts/reconcile_bankroll.py deposit 500        # EUR 500 in
  python scripts/reconcile_bankroll.py withdrawal 200     # EUR 200 out
  python scripts/reconcile_bankroll.py manual_adjustment -12.34 "sync with Betfair balance"
"""
from __future__ import annotations

import sys

from betbot.config import secrets
from betbot.db.database import connect, migrate
from betbot.db.repo import Repo

VALID = {"deposit", "withdrawal", "manual_adjustment"}


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in VALID:
        sys.exit(__doc__)
    reason = sys.argv[1]
    amount = float(sys.argv[2])
    if reason == "withdrawal":
        amount = -abs(amount)
    note = sys.argv[3] if len(sys.argv) > 3 else None
    conn = connect(secrets().betbot_db_path)
    migrate(conn)
    repo = Repo(conn)
    balance = repo.append_ledger(delta_cents=int(round(amount * 100)), reason=reason, note=note)
    print(f"ok — {reason} {amount:+.2f}, bankroll now €{balance / 100:.2f}")


if __name__ == "__main__":
    main()
