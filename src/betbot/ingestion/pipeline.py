"""The orchestration spine: raw message -> parse -> validate -> rules -> executor.

Whitelist and exact-duplicate checks run HERE, before the Claude call — security
and cost: unwhitelisted chatter never reaches the parser, let alone the rules.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from betbot.config import tunables
from betbot.db.repo import Repo
from betbot.ingestion import shadow
from betbot.notify import messages
from betbot.parsing.claude_parser import ParseError, parse_message
from betbot.rules import engine as rules_engine
from betbot.rules import guardrails as g
from betbot.validation.matcher import match_tip
from betbot.ops import killswitch

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, repo: Repo, betfair, executor, notifier):
        self.repo = repo
        self.betfair = betfair
        self.executor = executor
        self.notifier = notifier

    async def process_raw_message(self, raw_id: int) -> None:
        try:
            await self._process(raw_id)
        except Exception:
            log.exception("pipeline failed for raw_message %s", raw_id)
            self.repo.set_raw_status(raw_id, "parse_failed")

    async def _process(self, raw_id: int) -> None:
        raw = self.repo.get_raw_message(raw_id)
        if raw is None:
            return

        # Guardrail 1: source whitelist — before any API spend.
        source = self.repo._one("SELECT * FROM sources WHERE id=?", (raw["source_id"],)) \
            if raw["source_id"] else None
        if source is None or not source["is_whitelisted"]:
            self.repo.set_raw_status(raw_id, "skipped_not_whitelisted")
            log.info("raw %s skipped: not whitelisted", raw_id)
            return

        # Guardrail 2: exact duplicate content within 24h (covers re-sends and edits).
        if self.repo.recent_duplicate_hash(raw["content_hash"], raw_id):
            self.repo.set_raw_status(raw_id, "skipped_duplicate")
            return

        # Parse with Claude (retried by the scheduler for parse_failed rows).
        parsed = await asyncio.to_thread(
            parse_message, raw["message_text"], raw["image_path"]
        )
        cfg = tunables()
        if not parsed.is_tip or not parsed.tips:
            self.repo.set_raw_status(raw_id, "not_a_tip")
            return
        self.repo.set_raw_status(raw_id, "parsed")

        for tip in parsed.tips:
            tip_id = self.repo.insert_tip(
                raw_message_id=raw_id, source_id=source["id"],
                course=tip.course, race_time_local=tip.race_time,
                horse_name=tip.horse_name, side=tip.side,
                tipped_price_cents=int(round(tip.tipped_price * 100)) if tip.tipped_price else None,
                rating=tip.rating, parse_confidence=tip.confidence,
                parse_model=cfg.parsing.model,
                parse_raw_json=parsed.model_dump_json(),
            )
            await self._process_tip(tip_id, source)

    async def _process_tip(self, tip_id: int, source) -> None:
        cfg = tunables()
        tip = self.repo.get_tip(tip_id)
        now = datetime.now(timezone.utc)

        # Validate against Betfair (delayed key). Fails closed on API problems.
        try:
            markets = await asyncio.to_thread(self.betfair.todays_win_markets)
        except Exception:
            log.exception("betfair catalogue unavailable — failing closed")
            self.repo.set_tip_status(tip_id, "match_failed")
            await self.notifier.send(messages.parse_problem(
                source=source["display_name"], excerpt=f"{tip['horse_name']} {tip['course']}",
                why="Betfair unavailable for validation — no bet placed (fail closed)"))
            return

        match = match_tip(tip["course"], tip["race_time_local"], tip["horse_name"], markets, now)
        if not match.ok:
            self.repo.set_tip_status(tip_id, "match_failed")
            self.repo.log_guardrail(tip_id=tip_id, bet_id=None, rule="market_match", outcome="abort",
                                    detail={"reason": match.reason, "candidates": match.candidates})
            await self.notifier.send(messages.parse_problem(
                source=source["display_name"],
                excerpt=f"{tip['horse_name']} — {tip['course']} {tip['race_time_local']}",
                why=f"couldn't match to a Betfair market: {match.reason}"))
            return

        self.repo.set_tip_match(
            tip_id, market_id=match.market.market_id, selection_id=match.runner.selection_id,
            event_name=match.market.event_name,
            market_start_time=match.market.market_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            match_score=match.score, side=tip["side"],
        )
        self.repo.log_guardrail(tip_id=tip_id, bet_id=None, rule="market_match", outcome="pass",
                                detail={"score": match.score, "market_id": match.market.market_id})

        # Guardrail 5: semantic duplicate (same market/selection/side already active today).
        dedupe_key = f"{match.market.market_id}|{match.runner.selection_id}|{tip['side']}"
        existing = self.repo.find_active_dedupe(dedupe_key, tip_id)
        if existing is not None:
            self.repo.set_tip_status(tip_id, "duplicate")
            self.repo.log_guardrail(tip_id=tip_id, bet_id=None, rule="duplicate", outcome="abort",
                                    detail={"duplicate_of_tip": existing["id"]})
            await self.notifier.send(
                f"♻️ Duplicate tip skipped: {tip['horse_name']} ({tip['course']}) — "
                f"already tipped by another source today.")
            return

        # Freshest price snapshot, immediately before the rules run.
        price = await asyncio.to_thread(
            self.betfair.price_for, match.market.market_id, match.runner.selection_id)
        available_price_cents = available_size_cents = None
        runner_status, market_status, inplay = "ACTIVE", "OPEN", False
        if price is not None:
            runner_status, market_status, inplay = price.runner_status, price.market_status, price.inplay
            relevant_price = price.back_price if tip["side"] == "BACK" else price.lay_price
            relevant_size = price.back_size if tip["side"] == "BACK" else price.lay_size
            available_price_cents = int(round(relevant_price * 100)) if relevant_price else None
            available_size_cents = int(round(relevant_size * 100)) if relevant_size else None
            self.repo.insert_snapshot(
                tip_id=tip_id, market_id=match.market.market_id,
                selection_id=match.runner.selection_id, snapshot_type="at_validation",
                back_price_cents=int(round(price.back_price * 100)) if price.back_price else None,
                back_size_cents=int(round(price.back_size * 100)) if price.back_size else None,
                lay_price_cents=int(round(price.lay_price * 100)) if price.lay_price else None,
                lay_size_cents=int(round(price.lay_size * 100)) if price.lay_size else None,
                total_matched_cents=int(round(price.total_matched * 100)) if price.total_matched else None,
            )

        ctx = g.RuleContext(
            tip_id=tip_id, source_row=source, parse_confidence=tip["parse_confidence"],
            side=tip["side"], tipped_price_cents=tip["tipped_price_cents"],
            market_start_time=match.market.market_start_time,
            market_status=market_status, inplay=inplay, runner_status=runner_status,
            available_price_cents=available_price_cents,
            available_size_cents=available_size_cents,
            bankroll_cents=self.repo.current_bankroll_cents(),
            bets_today=self.repo.bets_created_today_count(),
            open_exposure_cents=self.repo.open_exposure_cents(),
            realized_pnl_today_cents=self.repo.realized_pnl_today_cents(),
            kill_switch_on=killswitch.is_kill_on(self.repo),
            cfg=cfg, now=now,
        )

        decision = rules_engine.evaluate(
            self.repo, ctx, market_id=match.market.market_id,
            selection_id=match.runner.selection_id, selection_name=match.runner.name,
            course=match.market.venue,
        )

        if not decision.approved:
            await self.notifier.send(messages.bet_aborted(
                horse=match.runner.name, course=match.market.venue,
                reason=decision.abort_reason.value if decision.abort_reason else "?",
                message=decision.abort_message, source=source["display_name"]))
            if decision.abort_reason in (g.AbortReason.DAILY_LOSS_BREAKER, g.AbortReason.MAX_EXPOSURE):
                await self.notifier.send(messages.breaker_tripped(
                    decision.abort_reason.value, decision.abort_message))
            return

        # Hand to the executor — unless shadow mode (paper trading) is on.
        if shadow.is_shadow_on(self.repo):
            self.repo.set_bet_state(decision.bet_id, "CONSUMED",
                                    published_at=self._now_str(), consumed_at=self._now_str())
            prefix = "👻 SHADOW (paper) "
        else:
            self.executor.publish(decision.approved_bet)
            prefix = ""

        await self.notifier.send(prefix + messages.bet_queued(
            horse=match.runner.name, course=match.market.venue,
            race_time=match.market.market_start_time.strftime("%H:%M"),
            side=tip["side"], stake_cents=decision.approved_bet.stake_cents,
            available_cents=available_price_cents or 0,
            tipped_cents=tip["tipped_price_cents"], source=source["display_name"]))

    @staticmethod
    def _now_str() -> str:
        from betbot.db.repo import utcnow
        return utcnow()
