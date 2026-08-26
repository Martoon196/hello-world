"""The only module that writes to the database.

Thin, typed-ish CRUD helpers over sqlite3. A threading.Lock serializes writes
because Telethon callbacks, FastAPI handlers, and scheduler jobs all share the
one connection.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Repo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.Lock()

    def _exec(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.conn.execute(sql, tuple(params))
            self.conn.commit()
            return cur

    def _one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, tuple(params)).fetchone()

    def _all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, tuple(params)).fetchall()

    # ---- sources ----

    def find_source(self, platform: str, chat_id: str, sender_id: str | None) -> Optional[sqlite3.Row]:
        """Most-specific match wins: (chat, sender) row before (chat, any-sender) row."""
        row = self._one(
            "SELECT * FROM sources WHERE platform=? AND chat_id=? AND sender_id=? AND enabled=1",
            (platform, chat_id, sender_id),
        )
        if row:
            return row
        return self._one(
            "SELECT * FROM sources WHERE platform=? AND chat_id=? AND sender_id IS NULL AND enabled=1",
            (platform, chat_id),
        )

    def add_source(self, platform: str, chat_id: str, sender_id: str | None, display_name: str,
                   is_whitelisted: bool = False, stake_multiplier: float = 1.0,
                   price_floor_pct: float | None = None) -> int:
        cur = self._exec(
            """INSERT INTO sources (platform, chat_id, sender_id, display_name, is_whitelisted,
                                    stake_multiplier, price_floor_pct, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (platform, chat_id, sender_id, display_name, int(is_whitelisted),
             stake_multiplier, price_floor_pct, utcnow()),
        )
        return cur.lastrowid

    def list_sources(self) -> list[sqlite3.Row]:
        return self._all("SELECT * FROM sources ORDER BY display_name")

    # ---- raw messages ----

    def insert_raw_message(self, *, source_id: int | None, platform: str, platform_message_id: str | None,
                           is_edit: bool, message_text: str | None, image_path: str | None,
                           content_hash: str, status: str = "received") -> int:
        cur = self._exec(
            """INSERT INTO raw_messages (source_id, platform, platform_message_id, is_edit,
                                         received_at, message_text, image_path, content_hash, status)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (source_id, platform, platform_message_id, int(is_edit), utcnow(),
             message_text, image_path, content_hash, status),
        )
        return cur.lastrowid

    def get_raw_message(self, raw_id: int) -> Optional[sqlite3.Row]:
        return self._one("SELECT * FROM raw_messages WHERE id=?", (raw_id,))

    def set_raw_status(self, raw_id: int, status: str) -> None:
        self._exec("UPDATE raw_messages SET status=? WHERE id=?", (status, raw_id))

    def recent_duplicate_hash(self, content_hash: str, exclude_id: int, hours: int = 24) -> bool:
        row = self._one(
            """SELECT 1 FROM raw_messages
               WHERE content_hash=? AND id != ? AND status != 'skipped_duplicate'
                 AND received_at >= datetime('now', ?)""",
            (content_hash, exclude_id, f"-{hours} hours"),
        )
        return row is not None

    # ---- tips ----

    def insert_tip(self, *, raw_message_id: int, source_id: int, course: str, race_time_local: str,
                   horse_name: str, side: str, tipped_price_cents: int | None, rating: str | None,
                   parse_confidence: float, parse_model: str, parse_raw_json: str) -> int:
        cur = self._exec(
            """INSERT INTO tips (raw_message_id, source_id, course, race_time_local, horse_name, side,
                                 tipped_price_cents, rating, parse_confidence, parse_model,
                                 parse_raw_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (raw_message_id, source_id, course, race_time_local, horse_name, side,
             tipped_price_cents, rating, parse_confidence, parse_model, parse_raw_json, utcnow()),
        )
        return cur.lastrowid

    def get_tip(self, tip_id: int) -> Optional[sqlite3.Row]:
        return self._one("SELECT * FROM tips WHERE id=?", (tip_id,))

    def set_tip_match(self, tip_id: int, *, market_id: str, selection_id: int, event_name: str,
                      market_start_time: str, match_score: float, side: str) -> None:
        dedupe_key = f"{market_id}|{selection_id}|{side}"
        self._exec(
            """UPDATE tips SET market_id=?, selection_id=?, event_name=?, market_start_time=?,
                               match_score=?, dedupe_key=?, status='matched' WHERE id=?""",
            (market_id, selection_id, event_name, market_start_time, match_score, dedupe_key, tip_id),
        )

    def set_tip_status(self, tip_id: int, status: str) -> None:
        self._exec("UPDATE tips SET status=? WHERE id=?", (status, tip_id))

    def find_active_dedupe(self, dedupe_key: str, exclude_tip_id: int) -> Optional[sqlite3.Row]:
        """Another tip today with the same market/selection/side that produced (or may produce) a bet."""
        return self._one(
            """SELECT t.* FROM tips t
               WHERE t.dedupe_key=? AND t.id != ? AND t.status IN ('matched','bet_created')
                 AND t.created_at >= datetime('now','-1 day')""",
            (dedupe_key, exclude_tip_id),
        )

    # ---- bets ----

    def insert_bet(self, *, tip_id: int, state: str, side: str, stake_cents: int, stake_pct: float,
                   bankroll_at_stake_cents: int, tipped_price_cents: int | None,
                   validated_price_cents: int, price_floor_cents: int | None,
                   expires_at: str, abort_reason: str | None = None) -> int:
        cur = self._exec(
            """INSERT INTO bets (tip_id, state, side, stake_cents, stake_pct, bankroll_at_stake_cents,
                                 tipped_price_cents, validated_price_cents, price_floor_cents,
                                 approved_at, expires_at, abort_reason)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tip_id, state, side, stake_cents, stake_pct, bankroll_at_stake_cents,
             tipped_price_cents, validated_price_cents, price_floor_cents,
             utcnow(), expires_at, abort_reason),
        )
        return cur.lastrowid

    def get_bet(self, bet_id: int) -> Optional[sqlite3.Row]:
        return self._one("SELECT * FROM bets WHERE id=?", (bet_id,))

    def set_bet_state(self, bet_id: int, state: str, **stamps: str) -> None:
        sets = ", ".join(["state=?"] + [f"{k}=?" for k in stamps])
        self._exec(f"UPDATE bets SET {sets} WHERE id=?", (state, *stamps.values(), bet_id))

    def bets_in_state(self, *states: str) -> list[sqlite3.Row]:
        qs = ",".join("?" * len(states))
        return self._all(f"SELECT * FROM bets WHERE state IN ({qs})", states)

    def feed_rows(self) -> list[sqlite3.Row]:
        """Bets currently servable to BFBM: published/consumed and unexpired."""
        return self._all(
            """SELECT b.*, t.course, t.horse_name, t.market_id, t.selection_id, t.market_start_time
               FROM bets b JOIN tips t ON t.id = b.tip_id
               WHERE b.state IN ('PUBLISHED','CONSUMED') AND b.expires_at > ?""",
            (utcnow(),),
        )

    def mark_consumed(self, bet_ids: list[int]) -> None:
        now = utcnow()
        for bet_id in bet_ids:
            self._exec(
                "UPDATE bets SET state='CONSUMED', consumed_at=COALESCE(consumed_at, ?) WHERE id=? AND state='PUBLISHED'",
                (now, bet_id),
            )

    def expire_stale_published(self) -> list[int]:
        rows = self._all(
            "SELECT id FROM bets WHERE state='PUBLISHED' AND expires_at <= ?", (utcnow(),)
        )
        ids = [r["id"] for r in rows]
        for bet_id in ids:
            self._exec("UPDATE bets SET state='EXPIRED' WHERE id=?", (bet_id,))
        return ids

    def settle_bet(self, bet_id: int, *, state: str, result: str, gross_pnl_cents: int,
                   commission_cents: int, net_pnl_cents: int, settlement_source: str,
                   matched_price_cents: int | None = None, matched_stake_cents: int | None = None,
                   needs_review: bool = False) -> None:
        self._exec(
            """UPDATE bets SET state=?, result=?, gross_pnl_cents=?, commission_cents=?,
                               net_pnl_cents=?, settlement_source=?, settled_at=?,
                               matched_price_cents=COALESCE(?, matched_price_cents),
                               matched_stake_cents=COALESCE(?, matched_stake_cents),
                               needs_review=? WHERE id=?""",
            (state, result, gross_pnl_cents, commission_cents, net_pnl_cents, settlement_source,
             utcnow(), matched_price_cents, matched_stake_cents, int(needs_review), bet_id),
        )

    def set_bet_placement(self, bet_id: int, matched_price_cents: int, matched_stake_cents: int) -> None:
        self._exec(
            "UPDATE bets SET matched_price_cents=?, matched_stake_cents=? WHERE id=?",
            (matched_price_cents, matched_stake_cents, bet_id),
        )

    def bets_settled_today(self) -> list[sqlite3.Row]:
        return self._all(
            "SELECT * FROM bets WHERE settled_at >= date('now') AND net_pnl_cents IS NOT NULL"
        )

    def bets_created_today_count(self) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM bets WHERE approved_at >= date('now') AND state != 'ABORTED'"
        )
        return row["n"]

    def open_exposure_cents(self) -> int:
        row = self._one(
            "SELECT COALESCE(SUM(stake_cents),0) AS s FROM bets WHERE state IN ('PUBLISHED','CONSUMED')"
        )
        return row["s"]

    # ---- price snapshots ----

    def insert_snapshot(self, *, tip_id: int | None, market_id: str, selection_id: int,
                        snapshot_type: str, back_price_cents: int | None, back_size_cents: int | None,
                        lay_price_cents: int | None, lay_size_cents: int | None,
                        total_matched_cents: int | None) -> None:
        self._exec(
            """INSERT INTO price_snapshots (tip_id, market_id, selection_id, taken_at, snapshot_type,
                                            back_price_cents, back_size_cents, lay_price_cents,
                                            lay_size_cents, total_matched_cents)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (tip_id, market_id, selection_id, utcnow(), snapshot_type, back_price_cents,
             back_size_cents, lay_price_cents, lay_size_cents, total_matched_cents),
        )

    # ---- bankroll ----

    def current_bankroll_cents(self) -> int:
        row = self._one("SELECT balance_after_cents FROM bankroll_ledger ORDER BY id DESC LIMIT 1")
        return row["balance_after_cents"] if row else 0

    def append_ledger(self, *, delta_cents: int, reason: str, bet_id: int | None = None,
                      note: str | None = None) -> int:
        with self._lock:
            row = self.conn.execute(
                "SELECT balance_after_cents FROM bankroll_ledger ORDER BY id DESC LIMIT 1"
            ).fetchone()
            balance = (row["balance_after_cents"] if row else 0) + delta_cents
            cur = self.conn.execute(
                """INSERT INTO bankroll_ledger (at, delta_cents, balance_after_cents, reason, bet_id, note)
                   VALUES (?,?,?,?,?,?)""",
                (utcnow(), delta_cents, balance, reason, bet_id, note),
            )
            self.conn.commit()
            return balance

    def seed_bankroll_if_empty(self, opening_cents: int) -> None:
        if self._one("SELECT 1 FROM bankroll_ledger LIMIT 1") is None:
            self.append_ledger(delta_cents=opening_cents, reason="opening", note="opening bankroll")

    def realized_pnl_today_cents(self) -> int:
        row = self._one(
            """SELECT COALESCE(SUM(delta_cents),0) AS s FROM bankroll_ledger
               WHERE at >= date('now') AND reason IN ('bet_settlement','settlement_correction')"""
        )
        return row["s"]

    # ---- guardrail events ----

    def log_guardrail(self, *, tip_id: int | None, bet_id: int | None, rule: str,
                      outcome: str, detail: dict | None = None) -> None:
        self._exec(
            "INSERT INTO guardrail_events (tip_id, bet_id, rule, outcome, detail, at) VALUES (?,?,?,?,?,?)",
            (tip_id, bet_id, rule, outcome, json.dumps(detail) if detail else None, utcnow()),
        )

    # ---- feed downloads ----

    def log_feed_download(self, remote_ip: str | None, bet_ids: list[int]) -> None:
        self._exec(
            "INSERT INTO feed_downloads (at, remote_ip, rows_served, bet_ids) VALUES (?,?,?,?)",
            (utcnow(), remote_ip, len(bet_ids), json.dumps(bet_ids)),
        )

    def last_feed_download_at(self) -> str | None:
        row = self._one("SELECT at FROM feed_downloads ORDER BY id DESC LIMIT 1")
        return row["at"] if row else None

    # ---- runtime state ----

    def get_state(self, key: str, default: str | None = None) -> str | None:
        row = self._one("SELECT value FROM runtime_state WHERE key=?", (key,))
        return row["value"] if row else default

    def set_state(self, key: str, value: str) -> None:
        self._exec(
            """INSERT INTO runtime_state (key, value, updated_at) VALUES (?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, value, utcnow()),
        )

    # ---- heartbeats ----

    def beat(self, component: str, meta: str | None = None) -> None:
        self._exec(
            """INSERT INTO heartbeats (component, last_seen_at, meta) VALUES (?,?,?)
               ON CONFLICT(component) DO UPDATE SET last_seen_at=excluded.last_seen_at, meta=excluded.meta""",
            (component, utcnow(), meta),
        )

    def heartbeat_age_seconds(self, component: str) -> float | None:
        row = self._one("SELECT last_seen_at FROM heartbeats WHERE component=?", (component,))
        if not row:
            return None
        seen = datetime.strptime(row["last_seen_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - seen).total_seconds()
