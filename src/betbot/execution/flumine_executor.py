"""v2 executor stub: direct Betfair API order placement via flumine/betfairlightweight.

Exists to prove the Executor interface boundary. Implementing this (plus a
clearedOrders-based settlement source) is the entire BFBM retirement path —
nothing upstream changes. Requires a live app key (one-off Betfair fee).
"""
from __future__ import annotations

from betbot.execution.base import ApprovedBet, Executor


class FlumineExecutor(Executor):
    name = "flumine"

    def publish(self, bet: ApprovedBet) -> None:
        raise NotImplementedError("v2: placeOrders via betfairlightweight with a live app key")

    def cancel(self, bet_id: int) -> None:
        raise NotImplementedError("v2: cancelOrders via betfairlightweight with a live app key")
