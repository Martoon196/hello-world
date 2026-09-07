"""Re-pricing of tips parked overnight because the market was still asleep."""
from datetime import datetime, timedelta, timezone


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _park(repo, tip_id, *, start_in_minutes: int, abort_reason: str = "STAKE_BELOW_MIN") -> int:
    start = _iso(datetime.now(timezone.utc) + timedelta(minutes=start_in_minutes))
    repo.set_tip_match(tip_id, market_id="1.234", selection_id=42, event_name="Goodwood",
                       market_start_time=start, match_score=100, side="BACK")
    bet_id = repo.insert_bet(tip_id=tip_id, state="ABORTED", side="BACK", stake_cents=0,
                             stake_pct=0.02, bankroll_at_stake_cents=100000,
                             tipped_price_cents=156, validated_price_cents=150,
                             price_floor_cents=None, expires_at=start,
                             abort_reason=abort_reason)
    # Backdate the attempt: it happened "last night", well past the cool-off.
    repo._exec("UPDATE bets SET approved_at=? WHERE id=?",
               (_iso(datetime.now(timezone.utc) - timedelta(hours=10)), bet_id))
    return bet_id


def test_parked_tip_repriced_inside_window(repo, tip_id):
    _park(repo, tip_id, start_in_minutes=30)
    assert repo.tips_to_reprice() == [tip_id]


def test_parked_tip_waits_until_near_the_off(repo, tip_id):
    _park(repo, tip_id, start_in_minutes=180)
    assert repo.tips_to_reprice() == []


def test_fresh_abort_respects_cooloff(repo, tip_id):
    bet_id = _park(repo, tip_id, start_in_minutes=30)
    repo._exec("UPDATE bets SET approved_at=? WHERE id=?",
               (_iso(datetime.now(timezone.utc)), bet_id))
    assert repo.tips_to_reprice() == []


def test_other_abort_reasons_stay_dead(repo, tip_id):
    _park(repo, tip_id, start_in_minutes=30, abort_reason="PRICE_COLLAPSE")
    assert repo.tips_to_reprice() == []
