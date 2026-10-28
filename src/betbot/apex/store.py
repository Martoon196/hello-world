"""Data access for the Apex growth layer. Shares the single-writer Repo."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from betbot.db.repo import Repo, utcnow

SYSTEMS = ("Apex Anchor", "Apex Football Gold")
RESULTS = ("pending", "won", "lost", "void", "no_bet")
SETTLED = ("won", "lost", "void", "no_bet")

# Admin-editable settings (runtime_state keys) with their defaults.
SETTINGS = {
    "founding_remaining": "50",
    "stake_cap_pct": "3",
    "billing_portal_url": "",
    "members_telegram_invite": "",
    "yearly_member_url": "",
    "yearly_pro_url": "",
    "pro_tracker_url": "",
    "pro_debrief_url": "",
    "pro_schedule": "",
    "sunday_email_enabled": "0",
    "verdict_email_enabled": "0",
}


class ApexStore:
    def __init__(self, repo: Repo):
        self._r = repo

    # ---- settings ----

    def setting(self, key: str) -> str:
        return self._r.get_state(f"apex.{key}", SETTINGS.get(key, "")) or ""

    def set_setting(self, key: str, value: str) -> None:
        if key in SETTINGS:
            self._r.set_state(f"apex.{key}", value.strip())

    def settings(self) -> dict[str, str]:
        return {k: self.setting(k) for k in SETTINGS}

    def enabled(self, key: str) -> bool:
        return self.setting(key) == "1"

    # ---- official log ----

    def add_log_row(self, *, race_date: str, system: str, selection: str, venue: str | None,
                    event_time: str | None, market: str | None, price_x100: int | None,
                    stake_pence: int | None, stake_pct: float | None, reasoning: str | None,
                    free_pick: bool = False, result: str = "pending") -> int:
        now = utcnow()
        cur = self._r._exec(
            """INSERT INTO official_log (race_date, system, selection, venue, event_time, market,
                   price_x100, stake_pence, stake_pct, reasoning, free_pick, result,
                   created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (race_date, system, selection, venue, event_time, market, price_x100, stake_pence,
             stake_pct, reasoning, int(free_pick), result, now, now))
        return cur.lastrowid

    def settle_log_row(self, row_id: int, *, result: str, position: str | None,
                       pnl_pence: int | None) -> None:
        self._r._exec(
            "UPDATE official_log SET result=?, position=?, pnl_pence=?, updated_at=? WHERE id=?",
            (result, position, pnl_pence, utcnow(), row_id))

    def get_log_row(self, row_id: int) -> Optional[sqlite3.Row]:
        return self._r._one("SELECT * FROM official_log WHERE id=?", (row_id,))

    def log_rows(self, *, settled_only: bool = False, limit: int = 200) -> list[sqlite3.Row]:
        where = f"WHERE result IN {SETTLED}" if settled_only else ""
        return self._r._all(
            f"SELECT * FROM official_log {where} ORDER BY race_date DESC, id DESC LIMIT ?", (limit,))

    def open_selections(self, today: str) -> list[sqlite3.Row]:
        return self._r._all(
            """SELECT * FROM official_log WHERE result='pending' AND race_date >= ?
               ORDER BY race_date, event_time""", (today,))

    def settled_between(self, start: str, end: str) -> list[sqlite3.Row]:
        return self._r._all(
            f"""SELECT * FROM official_log WHERE result IN {SETTLED}
                AND race_date >= ? AND race_date <= ? ORDER BY race_date, id""", (start, end))

    def log_last_updated(self) -> Optional[str]:
        row = self._r._one("SELECT MAX(updated_at) AS u FROM official_log")
        return row["u"] if row else None

    # ---- page views (cookieless) ----

    def count_view(self, *, path: str, referrer: str | None, utm_source: str | None,
                   utm_medium: str | None, utm_campaign: str | None) -> None:
        ref_domain = ""
        if referrer:
            host = (urlparse(referrer).hostname or "").lower()
            ref_domain = "" if host.endswith("apexcode.uk") else host[:80]
        self._r._exec(
            """INSERT INTO page_views (day, path, ref_domain, utm_source, utm_medium, utm_campaign, views)
               VALUES (?,?,?,?,?,?,1)
               ON CONFLICT(day, path, ref_domain, utm_source, utm_medium, utm_campaign)
               DO UPDATE SET views = views + 1""",
            (date.today().isoformat(), (path or "/")[:100], ref_domain,
             (utm_source or "")[:60], (utm_medium or "")[:60], (utm_campaign or "")[:60]))

    def views_since(self, days: int) -> int:
        since = (date.today() - timedelta(days=days - 1)).isoformat()
        row = self._r._one("SELECT COALESCE(SUM(views),0) AS n FROM page_views WHERE day >= ?", (since,))
        return row["n"]

    def top_sources(self, days: int, limit: int = 8) -> list[sqlite3.Row]:
        since = (date.today() - timedelta(days=days - 1)).isoformat()
        return self._r._all(
            """SELECT CASE WHEN utm_source != '' THEN utm_source
                           WHEN ref_domain != '' THEN ref_domain ELSE '(direct)' END AS source,
                      SUM(views) AS views
               FROM page_views WHERE day >= ? GROUP BY source ORDER BY views DESC LIMIT ?""",
            (since, limit))

    # ---- funnel ----

    def funnel(self) -> dict:
        def n(sql: str, params=()) -> int:
            return self._r._one(sql, params)["n"]
        week = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        month = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        paid = self._r._all(
            """SELECT tier, billing_period, COUNT(*) AS n FROM members
               WHERE tier != 'paddock' AND status IN ('active','trialing')
               GROUP BY tier, billing_period ORDER BY tier""")
        return {
            "views_7": self.views_since(7),
            "views_30": self.views_since(30),
            "paddock_total": n("""SELECT COUNT(*) AS n FROM members WHERE tier='paddock'
                                  AND consent_at IS NOT NULL AND unsubscribed_at IS NULL"""),
            "paddock_7": n("SELECT COUNT(*) AS n FROM members WHERE consent_at >= ?", (week,)),
            "paddock_30": n("SELECT COUNT(*) AS n FROM members WHERE consent_at >= ?", (month,)),
            "unsubscribed": n("SELECT COUNT(*) AS n FROM members WHERE unsubscribed_at IS NOT NULL"),
            "paid": paid,
            "paid_total": sum(r["n"] for r in paid),
        }

    # ---- founder wall ----

    def add_founder(self, display_name: str, joined_label: str | None, line: str | None) -> int:
        cur = self._r._exec(
            "INSERT INTO founder_wall (display_name, joined_label, line, created_at) VALUES (?,?,?,?)",
            (display_name.strip(), joined_label, line, utcnow()))
        return cur.lastrowid

    def set_founder_approved(self, founder_id: int, approved: bool) -> None:
        self._r._exec("UPDATE founder_wall SET approved=? WHERE id=?", (int(approved), founder_id))

    def delete_founder(self, founder_id: int) -> None:
        self._r._exec("DELETE FROM founder_wall WHERE id=?", (founder_id,))

    def founders(self, approved_only: bool = True) -> list[sqlite3.Row]:
        where = "WHERE approved=1" if approved_only else ""
        return self._r._all(f"SELECT * FROM founder_wall {where} ORDER BY id")
