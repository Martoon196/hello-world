import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from betbot.db.database import migrate  # noqa: E402
from betbot.db.repo import Repo  # noqa: E402


@pytest.fixture
def repo() -> Repo:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    r = Repo(conn)
    r.seed_bankroll_if_empty(100000)  # EUR 1,000
    return r


@pytest.fixture
def source(repo: Repo):
    source_id = repo.add_source("telegram", "-100123", None, "Test Tipster",
                                is_whitelisted=True, stake_multiplier=1.0, price_floor_pct=0.20)
    return repo._one("SELECT * FROM sources WHERE id=?", (source_id,))


@pytest.fixture
def tip_id(repo: Repo, source) -> int:
    raw_id = repo.insert_raw_message(
        source_id=source["id"], platform="telegram", platform_message_id="1",
        is_edit=False, message_text="2.35 Kempton - Silver Dancer back at 4.5",
        image_path=None, content_hash="abc123")
    return repo.insert_tip(
        raw_message_id=raw_id, source_id=source["id"], course="Kempton",
        race_time_local="14:35", horse_name="Silver Dancer", side="BACK",
        tipped_price_cents=450, rating="2pts", parse_confidence=0.95,
        parse_model="claude-sonnet-5", parse_raw_json="{}")
