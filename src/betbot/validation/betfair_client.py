"""Betfair delayed-key client: market catalogue lookup + price/result polling.

Uses betfairlightweight with interactive login. The free delayed app key is
enough for everything v1 needs (market discovery, price snapshots, settled
market status) — no live key required until we place bets ourselves in v2.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import betfairlightweight
from betfairlightweight import filters

from betbot.config import secrets, tunables

log = logging.getLogger(__name__)

HORSE_RACING_EVENT_TYPE_ID = "7"


@dataclass
class RunnerInfo:
    selection_id: int
    name: str
    status: str = "ACTIVE"


@dataclass
class MarketInfo:
    market_id: str
    event_name: str          # e.g. "Kempton 27th Aug"
    venue: str               # e.g. "Kempton"
    market_start_time: datetime
    runners: list[RunnerInfo] = field(default_factory=list)


@dataclass
class PriceInfo:
    back_price: float | None
    back_size: float | None
    lay_price: float | None
    lay_size: float | None
    total_matched: float | None
    runner_status: str
    market_status: str
    inplay: bool


class BetfairClient:
    def __init__(self):
        s = secrets()
        self.trading = betfairlightweight.APIClient(
            username=s.betfair_username,
            password=s.betfair_password,
            app_key=s.betfair_app_key,
            lightweight=False,
        )
        self._lock = threading.Lock()
        self._catalogue_cache: list[MarketInfo] = []
        self._catalogue_fetched_at: float = 0.0
        self._logged_in = False

    def _ensure_login(self) -> None:
        with self._lock:
            if not self._logged_in or self.trading.session_expired:
                self.trading.login_interactive()
                self._logged_in = True

    def keep_alive(self) -> None:
        try:
            self._ensure_login()
            self.trading.keep_alive()
        except Exception:
            log.exception("betfair keep_alive failed")
            self._logged_in = False

    def todays_win_markets(self) -> list[MarketInfo]:
        """WIN markets for today's horse racing in configured countries, cached."""
        cfg = tunables().matching
        now = time.monotonic()
        if self._catalogue_cache and now - self._catalogue_fetched_at < cfg.catalogue_cache_ttl_seconds:
            return self._catalogue_cache

        self._ensure_login()
        start = datetime.now(timezone.utc) - timedelta(minutes=30)
        end = datetime.now(timezone.utc) + timedelta(hours=24)
        market_filter = filters.market_filter(
            event_type_ids=[HORSE_RACING_EVENT_TYPE_ID],
            market_countries=cfg.countries,
            market_type_codes=["WIN"],
            market_start_time={"from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "to": end.strftime("%Y-%m-%dT%H:%M:%SZ")},
        )
        catalogues = self.trading.betting.list_market_catalogue(
            filter=market_filter,
            market_projection=["EVENT", "MARKET_START_TIME", "RUNNER_DESCRIPTION"],
            max_results=200,
            sort="FIRST_TO_START",
        )
        markets: list[MarketInfo] = []
        for cat in catalogues:
            venue = (cat.event.venue or cat.event.name or "").strip()
            markets.append(MarketInfo(
                market_id=cat.market_id,
                event_name=cat.event.name or venue,
                venue=venue,
                market_start_time=cat.market_start_time.replace(tzinfo=timezone.utc)
                    if cat.market_start_time.tzinfo is None else cat.market_start_time,
                runners=[RunnerInfo(r.selection_id, r.runner_name) for r in cat.runners],
            ))
        self._catalogue_cache = markets
        self._catalogue_fetched_at = now
        log.info("betfair catalogue refreshed: %d WIN markets", len(markets))
        return markets

    def price_for(self, market_id: str, selection_id: int) -> PriceInfo | None:
        self._ensure_login()
        books = self.trading.betting.list_market_book(
            market_ids=[market_id],
            price_projection=filters.price_projection(price_data=filters.price_data(ex_best_offers=True)),
        )
        if not books:
            return None
        book = books[0]
        for runner in book.runners:
            if runner.selection_id == selection_id:
                backs = runner.ex.available_to_back or []
                lays = runner.ex.available_to_lay or []
                return PriceInfo(
                    back_price=backs[0].price if backs else None,
                    back_size=backs[0].size if backs else None,
                    lay_price=lays[0].price if lays else None,
                    lay_size=lays[0].size if lays else None,
                    total_matched=runner.total_matched,
                    runner_status=runner.status,
                    market_status=book.status,
                    inplay=bool(book.inplay),
                )
        return None

    def market_result(self, market_id: str) -> dict[int, str] | None:
        """If the market is CLOSED, return {selection_id: WINNER|LOSER|REMOVED}; else None."""
        self._ensure_login()
        books = self.trading.betting.list_market_book(market_ids=[market_id])
        if not books or books[0].status != "CLOSED":
            return None
        return {r.selection_id: r.status for r in books[0].runners}
