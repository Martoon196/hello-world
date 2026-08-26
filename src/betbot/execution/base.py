"""The executor boundary. v1 = BFBM feed; v2 = flumine/API. Nothing upstream knows which."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ApprovedBet:
    bet_id: int
    tip_id: int
    market_id: str
    selection_id: int
    selection_name: str
    course: str
    market_start_time: datetime
    side: str                    # BACK | LAY
    stake_cents: int
    min_price_cents: int | None  # our floor, published as BFBM's min price
    expires_at: datetime


class Executor(ABC):
    name: str

    @abstractmethod
    def publish(self, bet: ApprovedBet) -> None:
        """Hand the bet to the execution layer (v1: mark servable in the feed)."""

    @abstractmethod
    def cancel(self, bet_id: int) -> None:
        """Withdraw a not-yet-placed bet (v1: expire the feed row)."""
