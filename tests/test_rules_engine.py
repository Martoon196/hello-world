"""Table-driven tests: every guardrail's pass/warn/abort cases, plus the engine end-to-end."""
from datetime import datetime, timedelta, timezone

import pytest

from betbot.config import tunables
from betbot.rules import engine, guardrails as g
from betbot.rules.staking import compute_stake

NOW = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)
START = NOW + timedelta(hours=1)


def make_ctx(source, tip_id=1, **overrides) -> g.RuleContext:
    defaults = dict(
        tip_id=tip_id, source_row=source, parse_confidence=0.95, side="BACK",
        tipped_price_cents=450, market_start_time=START, market_status="OPEN",
        inplay=False, runner_status="ACTIVE", available_price_cents=450,
        available_size_cents=500000, bankroll_cents=100000, bets_today=0,
        open_exposure_cents=0, realized_pnl_today_cents=0, kill_switch_on=False,
        cfg=tunables(), now=NOW,
    )
    defaults.update(overrides)
    return g.RuleContext(**defaults)


GUARDRAIL_CASES = [
    # (rule fn, overrides, expected outcome, expected abort reason)
    (g.check_kill_switch, {}, g.Outcome.PASS, None),
    (g.check_kill_switch, {"kill_switch_on": True}, g.Outcome.ABORT, g.AbortReason.KILL_SWITCH),
    (g.check_confidence, {}, g.Outcome.PASS, None),
    (g.check_confidence, {"parse_confidence": 0.5}, g.Outcome.ABORT, g.AbortReason.LOW_PARSE_CONFIDENCE),
    (g.check_runner_active, {}, g.Outcome.PASS, None),
    (g.check_runner_active, {"runner_status": "REMOVED"}, g.Outcome.ABORT, g.AbortReason.NON_RUNNER),
    (g.check_runner_active, {"market_status": "SUSPENDED"}, g.Outcome.ABORT, g.AbortReason.MARKET_SUSPENDED),
    (g.check_timing, {}, g.Outcome.PASS, None),
    (g.check_timing, {"inplay": True}, g.Outcome.ABORT, g.AbortReason.RACE_IN_PAST),
    (g.check_timing, {"market_start_time": NOW - timedelta(minutes=5)}, g.Outcome.ABORT, g.AbortReason.RACE_IN_PAST),
    (g.check_timing, {"market_start_time": NOW + timedelta(seconds=60)}, g.Outcome.ABORT, g.AbortReason.TOO_CLOSE_TO_OFF),
    (g.check_circuit_breakers, {}, g.Outcome.PASS, None),
    (g.check_circuit_breakers, {"bets_today": 15}, g.Outcome.ABORT, g.AbortReason.MAX_BETS_PER_DAY),
    (g.check_circuit_breakers, {"realized_pnl_today_cents": -10000}, g.Outcome.ABORT, g.AbortReason.DAILY_LOSS_BREAKER),
    (g.check_circuit_breakers, {"open_exposure_cents": 25000}, g.Outcome.ABORT, g.AbortReason.MAX_EXPOSURE),
    # Price rule: pass at/above tipped, warn between floor and tipped, abort below floor
    (g.check_price, {}, g.Outcome.PASS, None),
    (g.check_price, {"available_price_cents": 500}, g.Outcome.PASS, None),
    (g.check_price, {"available_price_cents": 400}, g.Outcome.WARN, None),
    (g.check_price, {"available_price_cents": 300}, g.Outcome.ABORT, g.AbortReason.PRICE_COLLAPSE),
    (g.check_price, {"available_price_cents": None}, g.Outcome.ABORT, g.AbortReason.LIQUIDITY_TOO_LOW),
    (g.check_price, {"tipped_price_cents": None}, g.Outcome.PASS, None),
]


@pytest.mark.parametrize("rule,overrides,expected,reason", GUARDRAIL_CASES)
def test_guardrail(source, rule, overrides, expected, reason):
    result = rule(make_ctx(source, **overrides))
    assert result.outcome is expected
    assert result.reason == reason


def test_price_floor_disabled_never_blocks(repo):
    source_id = repo.add_source("telegram", "-100999", None, "No Floor", is_whitelisted=True,
                                price_floor_pct=0.0)
    src = repo._one("SELECT * FROM sources WHERE id=?", (source_id,))
    # price crashed 80% but floor disabled (0.0) -> warn, never abort
    result = g.check_price(make_ctx(src, available_price_cents=101))
    assert result.outcome is g.Outcome.WARN


def test_staking_math():
    r = compute_stake(bankroll_cents=100000, base_pct=0.02, source_multiplier=1.0,
                      absolute_max_cents=10000, min_stake_cents=200,
                      liquidity_max_pct=0.10, available_size_cents=500000)
    assert r.stake_cents == 2000 and r.clamped_by is None          # EUR 20 at EUR 1k bank

    r = compute_stake(bankroll_cents=200000, base_pct=0.02, source_multiplier=1.0,
                      absolute_max_cents=10000, min_stake_cents=200,
                      liquidity_max_pct=0.10, available_size_cents=500000)
    assert r.stake_cents == 4000                                    # scales with bankroll

    r = compute_stake(bankroll_cents=10000000, base_pct=0.02, source_multiplier=1.0,
                      absolute_max_cents=10000, min_stake_cents=200,
                      liquidity_max_pct=0.10, available_size_cents=50000000)
    assert r.stake_cents == 10000 and r.clamped_by == "absolute_cap"

    r = compute_stake(bankroll_cents=100000, base_pct=0.02, source_multiplier=1.0,
                      absolute_max_cents=10000, min_stake_cents=200,
                      liquidity_max_pct=0.10, available_size_cents=5000)
    assert r.stake_cents == 500 and r.clamped_by == "liquidity"

    r = compute_stake(bankroll_cents=5000, base_pct=0.02, source_multiplier=1.0,
                      absolute_max_cents=10000, min_stake_cents=200,
                      liquidity_max_pct=0.10, available_size_cents=500000)
    assert r.below_minimum                                          # EUR 1 < EUR 2 minimum


def test_engine_approves_and_records(repo, source, tip_id):
    ctx = make_ctx(source, tip_id=tip_id)
    decision = engine.evaluate(repo, ctx, market_id="1.234", selection_id=42,
                               selection_name="Silver Dancer", course="Kempton")
    assert decision.approved
    bet = repo.get_bet(decision.bet_id)
    assert bet["state"] == "APPROVED"
    assert bet["stake_cents"] == 2000
    assert bet["price_floor_cents"] == 360    # 450 * (1 - 0.20)
    assert repo.get_tip(tip_id)["status"] == "bet_created"
    events = repo._all("SELECT rule, outcome FROM guardrail_events WHERE tip_id=?", (tip_id,))
    assert {e["rule"] for e in events} >= {"kill_switch", "parse_confidence", "timing",
                                           "circuit_breaker", "staking", "price"}


def test_engine_abort_records_bet_and_reason(repo, source, tip_id):
    ctx = make_ctx(source, tip_id=tip_id, available_price_cents=300)   # below floor
    decision = engine.evaluate(repo, ctx, market_id="1.234", selection_id=42,
                               selection_name="Silver Dancer", course="Kempton")
    assert not decision.approved
    assert decision.abort_reason is g.AbortReason.PRICE_COLLAPSE
    bet = repo.get_bet(decision.bet_id)
    assert bet["state"] == "ABORTED" and bet["abort_reason"] == "PRICE_COLLAPSE"
    assert repo.get_tip(tip_id)["status"] == "rejected"


def test_engine_drift_warns_but_bets(repo, source, tip_id):
    ctx = make_ctx(source, tip_id=tip_id, available_price_cents=400)   # below tipped, above floor
    decision = engine.evaluate(repo, ctx, market_id="1.234", selection_id=42,
                               selection_name="Silver Dancer", course="Kempton")
    assert decision.approved
    assert any(w.rule == "price" for w in decision.warnings)
