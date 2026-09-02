"""Membership data layer. Shares the single-writer Repo connection/lock."""
from __future__ import annotations

import secrets as pysecrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from betbot.db.repo import Repo, utcnow

MAGIC_LINK_TTL_MINUTES = 30
SESSION_TTL_DAYS = 30
ACTIVE_STATUSES = ("active", "trialing")


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class MembersRepo:
    def __init__(self, repo: Repo):
        self._r = repo
        self.conn = repo.conn

    # ---- members ----

    def get_member(self, member_id: int) -> Optional[sqlite3.Row]:
        return self._r._one("SELECT * FROM members WHERE id=?", (member_id,))

    def get_member_by_email(self, email: str) -> Optional[sqlite3.Row]:
        return self._r._one("SELECT * FROM members WHERE email=? COLLATE NOCASE", (email.strip(),))

    def get_member_by_feed_token(self, token: str) -> Optional[sqlite3.Row]:
        return self._r._one("SELECT * FROM members WHERE feed_token=?", (token,))

    def get_member_by_stripe_customer(self, customer_id: str) -> Optional[sqlite3.Row]:
        return self._r._one("SELECT * FROM members WHERE stripe_customer_id=?", (customer_id,))

    def list_members(self) -> list[sqlite3.Row]:
        return self._r._all("SELECT * FROM members ORDER BY created_at DESC")

    def create_member(self, email: str, *, name: str | None = None, tier: str = "paddock",
                      billing_period: str = "free", status: str = "active",
                      stripe_customer_id: str | None = None,
                      stripe_subscription_id: str | None = None) -> int:
        now = utcnow()
        cur = self._r._exec(
            """INSERT INTO members (email, name, tier, billing_period, status,
                                    stripe_customer_id, stripe_subscription_id,
                                    feed_token, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (email.strip(), name, tier, billing_period, status, stripe_customer_id,
             stripe_subscription_id, pysecrets.token_hex(24), now, now))
        return cur.lastrowid

    def update_member(self, member_id: int, **fields: Any) -> None:
        allowed = {"name", "tier", "billing_period", "status", "delivery_mode",
                   "stripe_customer_id", "stripe_subscription_id"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields) + ", updated_at=?"
        self._r._exec(f"UPDATE members SET {sets} WHERE id=?",
                      (*fields.values(), utcnow(), member_id))

    def upsert_member_from_billing(self, email: str, *, tier: str, billing_period: str,
                                   status: str, stripe_customer_id: str | None = None,
                                   stripe_subscription_id: str | None = None,
                                   name: str | None = None) -> int:
        member = None
        if stripe_customer_id:
            member = self.get_member_by_stripe_customer(stripe_customer_id)
        if member is None:
            member = self.get_member_by_email(email)
        if member is None:
            return self.create_member(email, name=name, tier=tier, billing_period=billing_period,
                                      status=status, stripe_customer_id=stripe_customer_id,
                                      stripe_subscription_id=stripe_subscription_id)
        self.update_member(member["id"], tier=tier, billing_period=billing_period, status=status,
                           stripe_customer_id=stripe_customer_id or member["stripe_customer_id"],
                           stripe_subscription_id=stripe_subscription_id or member["stripe_subscription_id"])
        return member["id"]

    def rotate_feed_token(self, member_id: int) -> str:
        token = pysecrets.token_hex(24)
        self._r._exec("UPDATE members SET feed_token=?, updated_at=? WHERE id=?",
                      (token, utcnow(), member_id))
        return token

    # ---- tiers & features (the switchable tools) ----

    def list_tiers(self) -> list[sqlite3.Row]:
        return self._r._all("SELECT * FROM tiers ORDER BY rank")

    def list_features(self) -> list[sqlite3.Row]:
        return self._r._all("SELECT * FROM features ORDER BY key")

    def tier_feature_map(self) -> dict[str, set[str]]:
        rows = self._r._all("SELECT tier, feature_key FROM tier_features WHERE enabled=1")
        out: dict[str, set[str]] = {}
        for row in rows:
            out.setdefault(row["tier"], set()).add(row["feature_key"])
        return out

    def set_tier_feature(self, tier: str, feature_key: str, enabled: bool) -> None:
        self._r._exec(
            """INSERT INTO tier_features (tier, feature_key, enabled) VALUES (?,?,?)
               ON CONFLICT(tier, feature_key) DO UPDATE SET enabled=excluded.enabled""",
            (tier, feature_key, int(enabled)))

    def member_overrides(self, member_id: int) -> dict[str, bool]:
        rows = self._r._all("SELECT feature_key, enabled FROM member_features WHERE member_id=?",
                            (member_id,))
        return {r["feature_key"]: bool(r["enabled"]) for r in rows}

    def set_member_feature(self, member_id: int, feature_key: str, enabled: bool | None) -> None:
        """enabled True/False sets an override; None clears it (back to tier default)."""
        if enabled is None:
            self._r._exec("DELETE FROM member_features WHERE member_id=? AND feature_key=?",
                          (member_id, feature_key))
        else:
            self._r._exec(
                """INSERT INTO member_features (member_id, feature_key, enabled) VALUES (?,?,?)
                   ON CONFLICT(member_id, feature_key) DO UPDATE SET enabled=excluded.enabled""",
                (member_id, feature_key, int(enabled)))

    def features_for(self, member: sqlite3.Row) -> set[str]:
        """Effective entitlements: tier defaults, then per-member overrides. Inactive = nothing."""
        if member["status"] not in ACTIVE_STATUSES:
            return set()
        granted = set(self.tier_feature_map().get(member["tier"], set()))
        for key, enabled in self.member_overrides(member["id"]).items():
            (granted.add if enabled else granted.discard)(key)
        return granted

    # ---- magic links & sessions ----

    def create_magic_link(self, member_id: int) -> str:
        token = pysecrets.token_urlsafe(32)
        self._r._exec(
            "INSERT INTO magic_links (token, member_id, expires_at, created_at) VALUES (?,?,?,?)",
            (token, member_id,
             _ts(datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_TTL_MINUTES)), utcnow()))
        return token

    def consume_magic_link(self, token: str) -> Optional[int]:
        row = self._r._one("SELECT * FROM magic_links WHERE token=?", (token,))
        if row is None or row["used"] or row["expires_at"] <= utcnow():
            return None
        self._r._exec("UPDATE magic_links SET used=1 WHERE token=?", (token,))
        return row["member_id"]

    def create_session(self, member_id: int) -> str:
        token = pysecrets.token_urlsafe(32)
        self._r._exec(
            "INSERT INTO sessions (token, member_id, expires_at, created_at) VALUES (?,?,?,?)",
            (token, member_id,
             _ts(datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)), utcnow()))
        return token

    def session_member(self, token: str) -> Optional[sqlite3.Row]:
        row = self._r._one(
            """SELECT m.* FROM sessions s JOIN members m ON m.id = s.member_id
               WHERE s.token=? AND s.expires_at > ?""", (token, utcnow()))
        return row

    def delete_session(self, token: str) -> None:
        self._r._exec("DELETE FROM sessions WHERE token=?", (token,))

    # ---- member feed accounting ----

    def log_member_feed(self, member_id: int, remote_ip: str | None, rows_served: int) -> None:
        self._r._exec(
            "INSERT INTO member_feed_downloads (member_id, at, remote_ip, rows_served) VALUES (?,?,?,?)",
            (member_id, utcnow(), remote_ip, rows_served))
