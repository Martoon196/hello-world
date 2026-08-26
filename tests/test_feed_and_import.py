"""Feed CSV rendering and BFBM bet-log CSV import parsing."""
from datetime import datetime, timedelta, timezone

from betbot.execution.bfbm_feed import render_feed_csv
from betbot.settlement.bfbm_import import parse_bfbm_csv


def test_feed_csv_shape(repo, tip_id):
    start = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo.set_tip_match(tip_id, market_id="1.234567890", selection_id=42, event_name="Kempton",
                       market_start_time=start, match_score=100, side="BACK")
    bet_id = repo.insert_bet(tip_id=tip_id, state="APPROVED", side="BACK", stake_cents=2000,
                             stake_pct=0.02, bankroll_at_stake_cents=100000,
                             tipped_price_cents=450, validated_price_cents=440,
                             price_floor_cents=360, expires_at=expires)
    repo.set_bet_state(bet_id, "PUBLISHED", published_at="2026-08-27T12:00:00Z")

    body, bet_ids = render_feed_csv(repo)
    assert bet_ids == [bet_id]
    lines = body.strip().splitlines()
    assert lines[0].startswith("RaceDate,RaceTime,Course,MarketId,SelectionId")
    row = lines[1].split(",")
    assert row[2] == "Kempton" and row[3] == "1.234567890" and row[4] == "42"
    assert row[6] == "BACK" and row[7] == "3.60" and row[8] == "20.00"
    assert row[9] == f"tip_{tip_id:05d}"


def test_bfbm_csv_parse_tolerant_headers():
    body = (
        "Bet ID,Selection,Avg. price matched,Size matched,Profit,Notes\n"
        f"111,Silver Dancer,4.2,20.00,64.00,tip_00007\n"
        "222,No Marker Horse,3.0,10.00,-10.00,manual bet\n"
    )
    facts = parse_bfbm_csv(body)
    assert len(facts) == 1
    f = facts[0]
    assert f.tip_id == 7
    assert f.matched_price_cents == 420
    assert f.matched_stake_cents == 2000


def test_bfbm_csv_parse_empty_and_garbage():
    assert parse_bfbm_csv("") == []
    assert parse_bfbm_csv("just some text\nnot,a,real,csv\n") == []
