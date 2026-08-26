"""The guardrail pipeline: fixed rule order, full audit trail, ApprovedBet or abort.

Order (cheapest / most decisive first — whitelist & duplicates are enforced
earlier, in the ingestion pipeline, before any API spend):
  kill switch -> confidence -> non-runner/suspended -> timing -> circuit
  breakers -> staking -> price rule (last, freshest snapshot).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from betbot.db.repo import Repo
from betbot.execution.base import ApprovedBet
from betbot.rules import guardrails as g
from betbot.rules.staking import compute_stake

log = logging.getLogger(__name__)


@dataclass
class Decision:
    approved: bool
    bet_id: int | None = None
    approved_bet: ApprovedBet | None = None
    abort_reason: g.AbortReason | None = None
    abort_message: str = ""
    warnings: list[g.RuleResult] = field(default_factory=list)


RULES = [
    g.check_kill_switch,
    g.check_confidence,
    g.check_runner_active,
    g.check_timing,
    g.check_circuit_breakers,
]


def evaluate(repo: Repo, ctx: g.RuleContext, *, market_id: str, selection_id: int,
             selection_name: str, course: str) -> Decision:
    warnings: list[g.RuleResult] = []

    def record(result: g.RuleResult) -> None:
        repo.log_guardrail(tip_id=ctx.tip_id, bet_id=None, rule=result.rule,
                           outcome=result.outcome.value,
                           detail={**result.detail, "message": result.message} if result.detail or result.message else None)

    def abort(result: g.RuleResult, *, stake_cents: int = 0, stake_pct: float = 0.0,
              floor_cents: int | None = None) -> Decision:
        record(result)
        expires = (ctx.market_start_time - timedelta(seconds=ctx.cfg.feed.bet_expiry_before_off_seconds)
                   if ctx.market_start_time else ctx.now)
        bet_id = repo.insert_bet(
            tip_id=ctx.tip_id, state="ABORTED", side=ctx.side,
            stake_cents=stake_cents, stake_pct=stake_pct,
            bankroll_at_stake_cents=ctx.bankroll_cents,
            tipped_price_cents=ctx.tipped_price_cents,
            validated_price_cents=ctx.available_price_cents or 0,
            price_floor_cents=floor_cents,
            expires_at=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            abort_reason=result.reason.value if result.reason else None,
        )
        repo.set_tip_status(ctx.tip_id, "rejected")
        return Decision(approved=False, bet_id=bet_id, abort_reason=result.reason,
                        abort_message=result.message, warnings=warnings)

    for rule in RULES:
        result = rule(ctx)
        if result.outcome is g.Outcome.ABORT:
            return abort(result)
        record(result)
        if result.outcome is g.Outcome.WARN:
            warnings.append(result)

    # Staking (rule 9): % of bankroll x source multiplier, capped and liquidity-clamped.
    st_cfg = ctx.cfg.staking
    stake = compute_stake(
        bankroll_cents=ctx.bankroll_cents,
        base_pct=st_cfg.base_pct,
        source_multiplier=ctx.source_row["stake_multiplier"],
        absolute_max_cents=st_cfg.absolute_max_stake_cents,
        min_stake_cents=st_cfg.min_stake_cents,
        liquidity_max_pct=st_cfg.liquidity_max_pct,
        available_size_cents=ctx.available_size_cents,
    )
    stake_detail = {"stake_cents": stake.stake_cents, "pct": stake.stake_pct,
                    "clamped_by": stake.clamped_by}
    if stake.below_minimum:
        return abort(g.RuleResult("staking", g.Outcome.ABORT, g.AbortReason.STAKE_BELOW_MIN,
                                  f"stake {stake.stake_cents/100:.2f} below exchange minimum "
                                  f"{st_cfg.min_stake_cents/100:.2f}", stake_detail),
                     stake_cents=stake.stake_cents, stake_pct=stake.stake_pct)
    repo.log_guardrail(tip_id=ctx.tip_id, bet_id=None, rule="staking", outcome="pass",
                       detail=stake_detail)

    # Price rule (rule 10, last): floor + notify.
    price_result = g.check_price(ctx)
    floor_cents = price_result.detail.get("floor")
    if price_result.outcome is g.Outcome.ABORT:
        return abort(price_result, stake_cents=stake.stake_cents, stake_pct=stake.stake_pct,
                     floor_cents=floor_cents)
    record(price_result)
    if price_result.outcome is g.Outcome.WARN:
        warnings.append(price_result)

    expires = ctx.market_start_time - timedelta(seconds=ctx.cfg.feed.bet_expiry_before_off_seconds)
    bet_id = repo.insert_bet(
        tip_id=ctx.tip_id, state="APPROVED", side=ctx.side,
        stake_cents=stake.stake_cents, stake_pct=stake.stake_pct,
        bankroll_at_stake_cents=ctx.bankroll_cents,
        tipped_price_cents=ctx.tipped_price_cents,
        validated_price_cents=ctx.available_price_cents,
        price_floor_cents=floor_cents,
        expires_at=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    repo.set_tip_status(ctx.tip_id, "bet_created")

    approved = ApprovedBet(
        bet_id=bet_id, tip_id=ctx.tip_id, market_id=market_id, selection_id=selection_id,
        selection_name=selection_name, course=course, market_start_time=ctx.market_start_time,
        side=ctx.side, stake_cents=stake.stake_cents, min_price_cents=floor_cents,
        expires_at=expires,
    )
    return Decision(approved=True, bet_id=bet_id, approved_bet=approved, warnings=warnings)
