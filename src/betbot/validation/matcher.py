"""Match a parsed tip to a Betfair market + runner.

Race first (course fuzzy + time window), then the horse ONLY among that race's
runners — which structurally kills the two-horses-same-name problem. Ambiguity
(two candidate races, low fuzzy score) is a refusal, never a guess.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from rapidfuzz import fuzz, process, utils

from betbot.config import tunables
from betbot.validation.betfair_client import MarketInfo, RunnerInfo

log = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")


@dataclass
class MatchResult:
    ok: bool
    reason: str = ""
    market: MarketInfo | None = None
    runner: RunnerInfo | None = None
    score: float = 0.0
    candidates: list[str] | None = None


def _tip_start_utc(race_time: str, reference: datetime) -> datetime | None:
    """Interpret 'HH:MM' (or 'H.MM') as UK/IE local time on the reference date."""
    cleaned = race_time.strip().replace(".", ":")
    try:
        hour, minute = (int(p) for p in cleaned.split(":")[:2])
    except (ValueError, IndexError):
        return None
    # Tipsters write "2.35" for 14:35 — racing is an afternoon/evening sport.
    if hour < 9:
        hour += 12
    # Timezone-aware, so comparisons against Betfair's UTC marketStartTime are correct.
    return reference.astimezone(UK_TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)


def match_tip(course: str, race_time: str, horse_name: str,
              markets: list[MarketInfo], now: datetime) -> MatchResult:
    cfg = tunables().matching

    tip_start = _tip_start_utc(race_time, now)
    if tip_start is None:
        return MatchResult(ok=False, reason=f"unparseable race time '{race_time}'")

    window = timedelta(minutes=cfg.race_time_window_minutes)
    course_norm = course.strip().lower()

    # Candidate races: venue fuzzy-matches the course AND start time inside the window.
    races: list[tuple[float, MarketInfo]] = []
    for m in markets:
        venue_score = fuzz.token_set_ratio(course_norm, m.venue.lower())
        if venue_score < 80:
            continue
        if abs(m.market_start_time - tip_start) <= window:
            races.append((venue_score, m))

    if not races:
        near = sorted({m.venue for m in markets
                       if fuzz.token_set_ratio(course_norm, m.venue.lower()) >= 80})
        return MatchResult(ok=False, reason="no race found for course/time",
                           candidates=[f"{v} (course matched, no race at {race_time})" for v in near] or None)

    races.sort(key=lambda t: (-t[0], abs(t[1].market_start_time - tip_start)))
    if len(races) > 1 and races[0][1].market_start_time != races[1][1].market_start_time \
            and races[0][0] == races[1][0]:
        return MatchResult(ok=False, reason="ambiguous: multiple races match course/time",
                           candidates=[f"{m.venue} {m.market_start_time:%H:%M}" for _, m in races[:3]])

    market = races[0][1]

    # Horse: fuzzy match among THIS race's runners only.
    names = {r.name: r for r in market.runners}
    best = process.extractOne(horse_name.strip(), list(names.keys()),
                              scorer=fuzz.token_set_ratio, processor=utils.default_process)
    if best is None:
        return MatchResult(ok=False, reason="race has no runners listed")
    best_name, score, _ = best
    if score < cfg.min_match_score:
        return MatchResult(
            ok=False, reason=f"no confident runner match (best '{best_name}' score {score:.0f})",
            market=market, score=score,
            candidates=[best_name],
        )

    # Two runners scoring near-identically is a refusal, not a guess.
    scored = process.extract(horse_name.strip(), list(names.keys()),
                             scorer=fuzz.token_set_ratio, processor=utils.default_process, limit=2)
    if len(scored) > 1 and scored[1][1] >= cfg.min_match_score and scored[1][0] != best_name:
        return MatchResult(ok=False, reason="ambiguous: two runners match the horse name",
                           market=market, candidates=[scored[0][0], scored[1][0]])

    return MatchResult(ok=True, market=market, runner=names[best_name], score=float(score))
