"""Bet lifecycle + ledger tests: publish/consume/expire, settlement, estimate correction."""
from datetime import datetime, timedelta, timezone

import pytest

from betbot.settlement.reconciler import PlacementFact, Reconciler, SettlementFact


class NullNotifier:
    async def send(self, text: str) -> None:
        pass


def make_bet(repo, tip_id, *, expires_in_minutes=60) -> int:
    expires = (datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    repo.set_tip_match(tip_id, market_id="1.234", selection_id=42, event_name="Kempton",
                       market_start_time=expires, match_score=100, side="BACK")
    return repo.insert_bet(tip_id=tip_id, state="APPROVED", side="BACK", stake_cents=2000,
                           stake_pct=0.02, bankroll_at_stake_cents=100000,
                           tipped_price_cents=450, validated_price_cents=440,
                           price_floor_cents=360, expires_at=expires)


def test_publish_consume_flow(repo, tip_id):
    bet_id = make_bet(repo, tip_id)
    repo.set_bet_state(bet_id, "PUBLISHED", published_at="2026-08-27T12:00:00Z")
    assert len(repo.feed_rows()) == 1
    repo.mark_consumed([bet_id])
    bet = repo.get_bet(bet_id)
    assert bet["state"] == "CONSUMED" and bet["consumed_at"] is not None
    # consumed rows keep being served until expiry (BFBM restart safety)
    assert len(repo.feed_rows()) == 1


def test_expiry_of_unconsumed(repo, tip_id):
    bet_id = make_bet(repo, tip_id, expires_in_minutes=-1)
    repo.set_bet_state(bet_id, "PUBLISHED", published_at="2026-08-27T12:00:00Z")
    assert repo.feed_rows() == []
    assert repo.expire_stale_published() == [bet_id]
    assert repo.get_bet(bet_id)["state"] == "EXPIRED"


@pytest.mark.asyncio
async def test_settlement_estimated_then_corrected(repo, tip_id):
    bet_id = make_bet(repo, tip_id)
    repo.set_bet_state(bet_id, "CONSUMED", consumed_at="2026-08-27T12:00:00Z")
    rec = Reconciler(repo, NullNotifier())

    # Settle WON on the estimate (validated price 4.40, stake EUR 20, 5% commission)
    await rec.settle_from_result(SettlementFact(bet_id=bet_id, result="WON"))
    bet = repo.get_bet(bet_id)
    assert bet["state"] == "SETTLED_WON"
    assert bet["settlement_source"] == "delayed_api_estimated"
    assert bet["needs_review"] == 1
    gross = int(2000 * (440 - 100) / 100)          # 6800 = EUR 68 profit at 4.40
    est_net = gross - int(gross * 0.05)
    assert bet["net_pnl_cents"] == est_net
    assert repo.current_bankroll_cents() == 100000 + est_net

    # BFBM export arrives: matched at 4.20 for the full stake -> correction posted
    await rec.apply_placement_facts([PlacementFact(tip_id=tip_id, matched_price_cents=420,
                                                   matched_stake_cents=2000)])
    bet = repo.get_bet(bet_id)
    assert bet["settlement_source"] == "bfbm_export" and bet["needs_review"] == 0
    gross_actual = int(2000 * (420 - 100) / 100)   # 6400
    net_actual = gross_actual - int(gross_actual * 0.05)
    assert bet["net_pnl_cents"] == net_actual
    assert repo.current_bankroll_cents() == 100000 + net_actual
    reasons = [r["reason"] for r in repo._all("SELECT reason FROM bankroll_ledger ORDER BY id")]
    assert reasons == ["opening", "bet_settlement", "settlement_correction"]


@pytest.mark.asyncio
async def test_settlement_lost_and_void(repo, source):
    for result, expected_state, expected_net in [("LOST", "SETTLED_LOST", -2000),
                                                 ("VOID", "SETTLED_VOID", 0)]:
        raw_id = repo.insert_raw_message(source_id=source["id"], platform="telegram",
                                         platform_message_id=result, is_edit=False,
                                         message_text="x", image_path=None,
                                         content_hash=f"h-{result}")
        tid = repo.insert_tip(raw_message_id=raw_id, source_id=source["id"], course="Kempton",
                              race_time_local="14:35", horse_name="H", side="BACK",
                              tipped_price_cents=450, rating=None, parse_confidence=0.9,
                              parse_model="m", parse_raw_json="{}")
        bet_id = make_bet(repo, tid)
        repo.set_bet_state(bet_id, "CONSUMED")
        rec = Reconciler(repo, NullNotifier())
        await rec.settle_from_result(SettlementFact(bet_id=bet_id, result=result))
        bet = repo.get_bet(bet_id)
        assert bet["state"] == expected_state and bet["net_pnl_cents"] == expected_net


@pytest.mark.asyncio
async def test_lay_settlement_inverts_result(repo, source):
    raw_id = repo.insert_raw_message(source_id=source["id"], platform="telegram",
                                     platform_message_id="lay", is_edit=False, message_text="x",
                                     image_path=None, content_hash="h-lay")
    tid = repo.insert_tip(raw_message_id=raw_id, source_id=source["id"], course="Kempton",
                          race_time_local="14:35", horse_name="H", side="LAY",
                          tipped_price_cents=300, rating=None, parse_confidence=0.9,
                          parse_model="m", parse_raw_json="{}")
    expires = (datetime.now(timezone.utc) + timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo.set_tip_match(tid, market_id="1.9", selection_id=7, event_name="Kempton",
                       market_start_time=expires, match_score=100, side="LAY")
    bet_id = repo.insert_bet(tip_id=tid, state="CONSUMED", side="LAY", stake_cents=2000,
                             stake_pct=0.02, bankroll_at_stake_cents=100000,
                             tipped_price_cents=300, validated_price_cents=300,
                             price_floor_cents=None, expires_at=expires)
    rec = Reconciler(repo, NullNotifier())
    # Horse LOST -> our lay bet WON the backer's stake (minus commission)
    await rec.settle_from_result(SettlementFact(bet_id=bet_id, result="LOST"))
    bet = repo.get_bet(bet_id)
    assert bet["state"] == "SETTLED_WON"
    assert bet["net_pnl_cents"] == 2000 - int(2000 * 0.05)
