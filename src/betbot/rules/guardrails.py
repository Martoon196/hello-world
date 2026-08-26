"""Guardrails: each rule is a small function taking a RuleContext and returning a RuleResult.

Outcomes: PASS (continue), WARN (continue but notify), ABORT (no bet, with reason).
The engine runs them in a fixed order and logs every outcome to guardrail_events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    PASS = "pass"
    WARN = "warn"
    ABORT = "abort"


class AbortReason(str, Enum):
    KILL_SWITCH = "KILL_SWITCH"
    NOT_WHITELISTED = "NOT_WHITELISTED"
    LOW_PARSE_CONFIDENCE = "LOW_PARSE_CONFIDENCE"
    MATCH_FAILED = "MATCH_FAILED"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    DUPLICATE = "DUPLICATE"
    NON_RUNNER = "NON_RUNNER"
    RACE_IN_PAST = "RACE_IN_PAST"
    TOO_CLOSE_TO_OFF = "TOO_CLOSE_TO_OFF"
    MAX_BETS_PER_DAY = "MAX_BETS_PER_DAY"
    MAX_EXPOSURE = "MAX_EXPOSURE"
    DAILY_LOSS_BREAKER = "DAILY_LOSS_BREAKER"
    LIQUIDITY_TOO_LOW = "LIQUIDITY_TOO_LOW"
    STAKE_BELOW_MIN = "STAKE_BELOW_MIN"
    PRICE_COLLAPSE = "PRICE_COLLAPSE"
    MARKET_SUSPENDED = "MARKET_SUSPENDED"
    MANUAL = "MANUAL"


@dataclass
class RuleResult:
    rule: str
    outcome: Outcome
    reason: AbortReason | None = None
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleContext:
    """Everything the guardrails need, assembled by the engine."""
    # tip / source
    tip_id: int
    source_row: Any            # sqlite3.Row from sources
    parse_confidence: float
    side: str
    tipped_price_cents: int | None
    # market / prices (filled after matching)
    market_start_time: datetime | None = None
    market_status: str = "OPEN"
    inplay: bool = False
    runner_status: str = "ACTIVE"
    available_price_cents: int | None = None
    available_size_cents: int | None = None
    # account state
    bankroll_cents: int = 0
    bets_today: int = 0
    open_exposure_cents: int = 0
    realized_pnl_today_cents: int = 0
    kill_switch_on: bool = False
    # config
    cfg: Any = None            # Tunables
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def check_kill_switch(ctx: RuleContext) -> RuleResult:
    if ctx.kill_switch_on:
        return RuleResult("kill_switch", Outcome.ABORT, AbortReason.KILL_SWITCH, "kill switch is on")
    return RuleResult("kill_switch", Outcome.PASS)


def check_confidence(ctx: RuleContext) -> RuleResult:
    minimum = ctx.cfg.parsing.min_confidence
    if ctx.parse_confidence < minimum:
        return RuleResult("parse_confidence", Outcome.ABORT, AbortReason.LOW_PARSE_CONFIDENCE,
                          f"parse confidence {ctx.parse_confidence:.2f} < {minimum:.2f}",
                          {"confidence": ctx.parse_confidence, "min": minimum})
    return RuleResult("parse_confidence", Outcome.PASS, detail={"confidence": ctx.parse_confidence})


def check_runner_active(ctx: RuleContext) -> RuleResult:
    if ctx.runner_status == "REMOVED":
        return RuleResult("non_runner", Outcome.ABORT, AbortReason.NON_RUNNER, "runner removed (non-runner)")
    if ctx.market_status == "SUSPENDED":
        return RuleResult("non_runner", Outcome.ABORT, AbortReason.MARKET_SUSPENDED, "market suspended")
    return RuleResult("non_runner", Outcome.PASS)


def check_timing(ctx: RuleContext) -> RuleResult:
    if ctx.inplay or (ctx.market_start_time and ctx.market_start_time <= ctx.now):
        return RuleResult("timing", Outcome.ABORT, AbortReason.RACE_IN_PAST, "race already off/in-play")
    if ctx.market_start_time:
        seconds_to_off = (ctx.market_start_time - ctx.now).total_seconds()
        cutoff = ctx.cfg.limits.too_close_to_off_seconds
        if seconds_to_off < cutoff:
            return RuleResult("timing", Outcome.ABORT, AbortReason.TOO_CLOSE_TO_OFF,
                              f"{seconds_to_off:.0f}s to off < {cutoff}s cutoff",
                              {"seconds_to_off": seconds_to_off})
    return RuleResult("timing", Outcome.PASS)


def check_circuit_breakers(ctx: RuleContext) -> RuleResult:
    lim = ctx.cfg.limits
    if ctx.bets_today >= lim.max_bets_per_day:
        return RuleResult("circuit_breaker", Outcome.ABORT, AbortReason.MAX_BETS_PER_DAY,
                          f"{ctx.bets_today} bets today >= max {lim.max_bets_per_day}")
    loss_limit = int(ctx.bankroll_cents * lim.daily_loss_limit_pct)
    if -ctx.realized_pnl_today_cents >= loss_limit > 0:
        return RuleResult("circuit_breaker", Outcome.ABORT, AbortReason.DAILY_LOSS_BREAKER,
                          f"daily loss {-ctx.realized_pnl_today_cents/100:.2f} hit limit {loss_limit/100:.2f}",
                          {"pnl_today_cents": ctx.realized_pnl_today_cents, "limit_cents": loss_limit})
    exposure_limit = int(ctx.bankroll_cents * lim.max_open_exposure_pct)
    if ctx.open_exposure_cents >= exposure_limit > 0:
        return RuleResult("circuit_breaker", Outcome.ABORT, AbortReason.MAX_EXPOSURE,
                          f"open exposure {ctx.open_exposure_cents/100:.2f} >= limit {exposure_limit/100:.2f}",
                          {"exposure_cents": ctx.open_exposure_cents, "limit_cents": exposure_limit})
    return RuleResult("circuit_breaker", Outcome.PASS)


def check_price(ctx: RuleContext) -> RuleResult:
    """The floor+notify rule. Runs LAST, on the freshest snapshot.

    - price collapsed below floor -> ABORT (the value is gone)
    - drifted down but >= floor  -> WARN: bet anyway, notify with P&L impact
    - at/above tipped price      -> PASS (drift up = good news, engine still notifies)
    """
    if ctx.available_price_cents is None:
        return RuleResult("price", Outcome.ABORT, AbortReason.LIQUIDITY_TOO_LOW,
                          "no price available on the exchange")
    if ctx.tipped_price_cents is None:
        return RuleResult("price", Outcome.PASS, message="no tipped price; taking market price",
                          detail={"available": ctx.available_price_cents})

    floor_pct = ctx.source_row["price_floor_pct"]
    if floor_pct is None:
        floor_pct = ctx.cfg.price_rule.default_floor_pct
    floor_cents = int(ctx.tipped_price_cents * (1 - floor_pct)) if floor_pct else None
    detail = {"tipped": ctx.tipped_price_cents, "available": ctx.available_price_cents,
              "floor": floor_cents}

    if floor_cents is not None and ctx.available_price_cents < floor_cents:
        return RuleResult("price", Outcome.ABORT, AbortReason.PRICE_COLLAPSE,
                          f"price collapsed: tipped {ctx.tipped_price_cents/100:.2f}, "
                          f"available {ctx.available_price_cents/100:.2f} < floor {floor_cents/100:.2f}",
                          detail)
    if ctx.available_price_cents < ctx.tipped_price_cents:
        return RuleResult("price", Outcome.WARN, message="price drifted against us (still above floor)",
                          detail=detail)
    return RuleResult("price", Outcome.PASS, detail=detail)
