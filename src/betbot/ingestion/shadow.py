"""Shadow (paper-trading) mode: the full pipeline runs, bets are recorded and
settled against real results, but nothing is ever served to BFBM.

Shadow is ON by default — going live is an explicit act.
"""
from __future__ import annotations

from betbot.db.repo import Repo

KEY = "shadow_mode"


def is_shadow_on(repo: Repo) -> bool:
    return repo.get_state(KEY, "on") == "on"


def set_shadow(repo: Repo, on: bool) -> None:
    repo.set_state(KEY, "on" if on else "off")
