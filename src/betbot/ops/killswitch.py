"""DB-backed global kill switch, toggled via Telegram command or dashboard."""
from __future__ import annotations

from betbot.db.repo import Repo

KEY = "kill_switch"


def is_kill_on(repo: Repo) -> bool:
    return repo.get_state(KEY, "off") == "on"


def set_kill(repo: Repo, on: bool) -> None:
    repo.set_state(KEY, "on" if on else "off")
