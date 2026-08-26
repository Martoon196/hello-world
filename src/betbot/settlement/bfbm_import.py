"""BFBM bet-log import endpoint.

A Windows Task Scheduler task on the BFBM VPS POSTs the bet-log CSV here every
30-60 minutes (see docs/bfbm-setup.md). We key rows back to our bets via the
tip_NNNNN marker we put in the feed's Notes column, which BFBM echoes in its
logs. Column names vary across BFBM versions, so the parser is header-driven
and tolerant.
"""
from __future__ import annotations

import csv
import hmac
import io
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from betbot.config import secrets
from betbot.db.repo import Repo
from betbot.settlement.reconciler import PlacementFact, Reconciler

log = logging.getLogger(__name__)

TIP_MARKER = re.compile(r"tip_(\d{1,10})")


def _cents(value: str) -> int | None:
    try:
        return int(round(float(value.replace(",", ".").replace("€", "").replace("£", "").strip()) * 100))
    except (ValueError, AttributeError):
        return None


def parse_bfbm_csv(body: str) -> list[PlacementFact]:
    """Header-driven parse: find the tip marker anywhere in the row, plus
    matched price/stake columns by fuzzy header name."""
    facts: list[PlacementFact] = []
    reader = csv.DictReader(io.StringIO(body))
    if not reader.fieldnames:
        return facts
    headers = {h.lower().strip(): h for h in reader.fieldnames}

    def col(row: dict, *needles: str) -> str | None:
        for lower, original in headers.items():
            if all(n in lower for n in needles):
                return row.get(original)
        return None

    for row in reader:
        marker = TIP_MARKER.search(" ".join(str(v) for v in row.values() if v))
        if not marker:
            continue
        price = _cents(col(row, "price") or col(row, "odds") or "")
        stake = _cents(col(row, "size") or col(row, "stake") or "")
        if price is None or stake is None:
            continue
        pnl = _cents(col(row, "profit") or "")
        facts.append(PlacementFact(
            tip_id=int(marker.group(1)),
            matched_price_cents=price,
            matched_stake_cents=stake,
            net_pnl_cents=pnl,
        ))
    return facts


def build_bfbm_results_router(repo: Repo, reconciler: Reconciler) -> APIRouter:
    router = APIRouter()

    @router.post("/ingest/bfbm-results")
    async def ingest(request: Request, token: str = "") -> PlainTextResponse:
        expected = secrets().bfbm_results_token
        if not expected or not hmac.compare_digest(token, expected):
            return PlainTextResponse("not found", status_code=404)
        body = (await request.body()).decode("utf-8", errors="replace")
        facts = parse_bfbm_csv(body)
        applied = await reconciler.apply_placement_facts(facts)
        log.info("bfbm results import: %d rows, %d applied", len(facts), applied)
        return PlainTextResponse(f"applied {applied} of {len(facts)}")

    return router
