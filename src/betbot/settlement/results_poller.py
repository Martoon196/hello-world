"""Scheduled job: settle CONSUMED bets from delayed-key market results.

Zero dependency on BFBM: when a market goes CLOSED, runner status
(WINNER/LOSER/REMOVED) gives the result. If BFBM's export hasn't provided
matched actuals yet, the reconciler settles ESTIMATED and flags for review.
Also expires stale PUBLISHED rows (feed never downloaded before the off).
"""
from __future__ import annotations

import asyncio
import logging

from betbot.db.repo import Repo
from betbot.settlement.reconciler import Reconciler, SettlementFact

log = logging.getLogger(__name__)


async def poll_results(repo: Repo, betfair, reconciler: Reconciler) -> None:
    repo.beat("results_poller")

    for bet_id in repo.expire_stale_published():
        log.info("bet %s expired (never consumed before off)", bet_id)

    open_bets = repo.bets_in_state("CONSUMED")
    markets: dict[str, list] = {}
    for bet in open_bets:
        tip = repo.get_tip(bet["tip_id"])
        if tip and tip["market_id"]:
            markets.setdefault(tip["market_id"], []).append((bet, tip))

    for market_id, bet_tips in markets.items():
        try:
            result = await asyncio.to_thread(betfair.market_result, market_id)
        except Exception:
            log.exception("result poll failed for market %s", market_id)
            continue
        if result is None:   # market not CLOSED yet
            continue
        for bet, tip in bet_tips:
            status = result.get(tip["selection_id"])
            if status == "WINNER":
                runner_result = "WON"
            elif status == "LOSER":
                runner_result = "LOST"
            elif status == "REMOVED":
                runner_result = "VOID"
            else:
                log.warning("market %s closed but selection %s status=%s",
                            market_id, tip["selection_id"], status)
                continue
            await reconciler.settle_from_result(SettlementFact(bet_id=bet["id"], result=runner_result))
