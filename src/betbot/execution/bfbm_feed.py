"""v1 executor: serve approved bets as a CSV feed that BF Bot Manager polls.

publish() flips the bet to PUBLISHED; the FastAPI router below renders all
servable rows. Rows stay servable after first consumption (BFBM dedupes
re-imports by MarketId+SelectionId, and a BFBM restart re-imports instead of
silently losing the bet) and vanish at expires_at. Every download is logged.
"""
from __future__ import annotations

import csv
import hmac
import io
import logging

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response

from betbot.config import secrets
from betbot.db.repo import Repo
from betbot.execution.base import ApprovedBet, Executor

log = logging.getLogger(__name__)

CSV_HEADER = ["RaceDate", "RaceTime", "Course", "MarketId", "SelectionId",
              "SelectionName", "BetType", "MinPrice", "Stake", "Notes"]


class FeedExecutor(Executor):
    name = "bfbm_feed"

    def __init__(self, repo: Repo):
        self.repo = repo

    def publish(self, bet: ApprovedBet) -> None:
        self.repo.set_bet_state(bet.bet_id, "PUBLISHED", published_at=self.repo_now())

    def cancel(self, bet_id: int) -> None:
        self.repo.set_bet_state(bet_id, "EXPIRED")

    def repo_now(self) -> str:
        from betbot.db.repo import utcnow
        return utcnow()


def render_feed_csv(repo: Repo) -> tuple[str, list[int]]:
    rows = repo.feed_rows()
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    bet_ids = []
    for row in rows:
        start = row["market_start_time"] or ""
        race_date, race_time = (start[:10], start[11:16]) if len(start) >= 16 else ("", "")
        min_price = f"{row['price_floor_cents'] / 100:.2f}" if row["price_floor_cents"] else ""
        writer.writerow([
            race_date, race_time, row["course"], row["market_id"], row["selection_id"],
            row["horse_name"], row["side"], min_price, f"{row['stake_cents'] / 100:.2f}",
            f"tip_{row['tip_id']:05d}",
        ])
        bet_ids.append(row["id"])
    return buf.getvalue(), bet_ids


def build_feed_router(repo: Repo) -> APIRouter:
    router = APIRouter()

    @router.get("/feed/bfbm.csv")
    def feed(request: Request, token: str = "") -> Response:
        expected = secrets().feed_token
        # 404 (not 403) on a bad token — the endpoint should look boring to scanners.
        if not expected or not hmac.compare_digest(token, expected):
            return PlainTextResponse("not found", status_code=404)
        body, bet_ids = render_feed_csv(repo)
        repo.mark_consumed(bet_ids)
        client_ip = request.client.host if request.client else None
        repo.log_feed_download(client_ip, bet_ids)
        repo.beat("bfbm_poller", meta=f"{len(bet_ids)} rows")
        return PlainTextResponse(body, media_type="text/csv")

    return router
