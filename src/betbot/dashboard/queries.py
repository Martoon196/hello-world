"""CRM queries: per-tipster P&L/ROI/strike rate, drift cost, bankroll curve."""
from __future__ import annotations

import sqlite3


def per_source_stats(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT s.id, s.display_name,
               COUNT(b.id)                                            AS bets,
               SUM(CASE WHEN b.state='SETTLED_WON' THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN b.state LIKE 'SETTLED%' THEN 1 ELSE 0 END) AS settled,
               COALESCE(SUM(b.net_pnl_cents), 0)                      AS net_pnl_cents,
               COALESCE(SUM(CASE WHEN b.state LIKE 'SETTLED%' THEN b.stake_cents END), 0) AS staked_cents,
               COALESCE(SUM(CASE
                   WHEN b.state='SETTLED_WON' AND b.tipped_price_cents IS NOT NULL
                        AND b.matched_price_cents IS NOT NULL
                   THEN (b.matched_stake_cents * (b.tipped_price_cents - b.matched_price_cents)) / 100
               END), 0)                                               AS drift_cost_cents
        FROM sources s
        LEFT JOIN tips t ON t.source_id = s.id
        LEFT JOIN bets b ON b.tip_id = t.id AND b.state != 'ABORTED'
        GROUP BY s.id
        ORDER BY net_pnl_cents DESC
    """).fetchall()


def bankroll_curve(conn: sqlite3.Connection, limit: int = 500) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT at, balance_after_cents FROM bankroll_ledger ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()[::-1]


def recent_bets(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT b.*, t.horse_name, t.course, t.race_time_local, s.display_name AS source_name
        FROM bets b
        JOIN tips t ON t.id = b.tip_id
        JOIN sources s ON s.id = t.source_id
        ORDER BY b.id DESC LIMIT ?
    """, (limit,)).fetchall()


def needs_review(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT b.*, t.horse_name, t.course FROM bets b
        JOIN tips t ON t.id = b.tip_id
        WHERE b.needs_review = 1 ORDER BY b.id DESC
    """).fetchall()


def totals(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute("""
        SELECT COUNT(*)                                                AS bets,
               SUM(CASE WHEN state='SETTLED_WON' THEN 1 ELSE 0 END)    AS wins,
               SUM(CASE WHEN state LIKE 'SETTLED%' THEN 1 ELSE 0 END)  AS settled,
               COALESCE(SUM(net_pnl_cents), 0)                         AS net_pnl_cents,
               COALESCE(SUM(CASE WHEN state LIKE 'SETTLED%' THEN stake_cents END), 0) AS staked_cents
        FROM bets WHERE state != 'ABORTED'
    """).fetchone()
