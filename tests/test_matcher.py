"""Matcher tests, including the same-name-horse and ambiguity refusal cases."""
from datetime import datetime, timezone

from betbot.validation.betfair_client import MarketInfo, RunnerInfo
from betbot.validation.matcher import match_tip

NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)


def market(venue: str, hour: int, minute: int, runners: list[str], market_id: str = "1.1") -> MarketInfo:
    # August: UK is UTC+1, so 14:35 UK local = 13:35 UTC
    return MarketInfo(
        market_id=market_id, event_name=f"{venue} race", venue=venue,
        market_start_time=datetime(2026, 8, 27, hour, minute, tzinfo=timezone.utc),
        runners=[RunnerInfo(i + 1, name) for i, name in enumerate(runners)],
    )


def test_exact_match():
    markets = [market("Kempton", 13, 35, ["Silver Dancer", "Red Baron"])]
    m = match_tip("Kempton", "14:35", "Silver Dancer", markets, NOW)
    assert m.ok and m.runner.name == "Silver Dancer" and m.market.market_id == "1.1"


def test_dot_time_and_fuzzy_horse():
    markets = [market("Kempton", 13, 35, ["Silver Dancer", "Red Baron"])]
    m = match_tip("kempton", "2.35", "silver dancer", markets, NOW)
    assert m.ok and m.runner.name == "Silver Dancer"


def test_same_horse_name_two_courses_resolved_by_race():
    # Same horse name runs at two venues — race-first matching picks the right one.
    markets = [
        market("Kempton", 13, 35, ["Silver Dancer", "Red Baron"], "1.1"),
        market("Ascot", 14, 10, ["Silver Dancer", "Blue Moon"], "1.2"),
    ]
    m = match_tip("Ascot", "15:10", "Silver Dancer", markets, NOW)
    assert m.ok and m.market.market_id == "1.2"


def test_wrong_time_refuses():
    markets = [market("Kempton", 13, 35, ["Silver Dancer"])]
    m = match_tip("Kempton", "16:00", "Silver Dancer", markets, NOW)
    assert not m.ok and "no race" in m.reason


def test_unknown_course_refuses():
    markets = [market("Kempton", 13, 35, ["Silver Dancer"])]
    m = match_tip("Longchamp", "14:35", "Silver Dancer", markets, NOW)
    assert not m.ok


def test_low_score_horse_refuses():
    markets = [market("Kempton", 13, 35, ["Silver Dancer", "Red Baron"])]
    m = match_tip("Kempton", "14:35", "Golden Arrow", markets, NOW)
    assert not m.ok and "no confident runner" in m.reason


def test_two_similar_runners_refuses():
    markets = [market("Kempton", 13, 35, ["Royal Flush II", "Royal Flush"])]
    m = match_tip("Kempton", "14:35", "Royal Flush", markets, NOW)
    assert not m.ok and "ambiguous" in m.reason


def test_unparseable_time_refuses():
    markets = [market("Kempton", 13, 35, ["Silver Dancer"])]
    m = match_tip("Kempton", "next race", "Silver Dancer", markets, NOW)
    assert not m.ok and "unparseable" in m.reason
