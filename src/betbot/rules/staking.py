"""Stake calculation: flat % of current bankroll with caps and liquidity clamp."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StakeResult:
    stake_cents: int
    stake_pct: float
    clamped_by: str | None = None  # 'absolute_cap' | 'liquidity' | None
    below_minimum: bool = False


def compute_stake(*, bankroll_cents: int, base_pct: float, source_multiplier: float,
                  absolute_max_cents: int, min_stake_cents: int,
                  liquidity_max_pct: float, available_size_cents: int | None) -> StakeResult:
    pct = base_pct * source_multiplier
    stake = int(round(bankroll_cents * pct))
    clamped_by = None

    if stake > absolute_max_cents:
        stake = absolute_max_cents
        clamped_by = "absolute_cap"

    if available_size_cents is not None:
        liquidity_cap = int(available_size_cents * liquidity_max_pct)
        if stake > liquidity_cap:
            stake = liquidity_cap
            clamped_by = "liquidity"

    return StakeResult(
        stake_cents=stake,
        stake_pct=pct,
        clamped_by=clamped_by,
        below_minimum=stake < min_stake_cents,
    )
