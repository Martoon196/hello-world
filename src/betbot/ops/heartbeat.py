"""Heartbeat endpoint + staleness watchdog.

The Android WhatsApp forwarder pings /heartbeat/whatsapp_forwarder every 15
minutes; internal components beat via repo.beat(). The watchdog job alerts when
anything critical goes quiet.
"""
from __future__ import annotations

import hmac
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from betbot.config import secrets, tunables
from betbot.db.repo import Repo
from betbot.notify import messages

log = logging.getLogger(__name__)

VALID_COMPONENTS = {"whatsapp_forwarder", "telegram_listener", "bfbm_poller", "results_poller"}


def build_heartbeat_router(repo: Repo) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> PlainTextResponse:
        return PlainTextResponse("ok")

    @router.post("/heartbeat/{component}")
    @router.get("/heartbeat/{component}")
    def beat(component: str, token: str = "") -> PlainTextResponse:
        expected = secrets().whatsapp_webhook_token
        if not expected or not hmac.compare_digest(token, expected):
            return PlainTextResponse("not found", status_code=404)
        if component not in VALID_COMPONENTS:
            return PlainTextResponse("unknown component", status_code=400)
        repo.beat(component)
        return PlainTextResponse("ok")

    return router


async def watchdog_check(repo: Repo, notifier) -> None:
    """Scheduled job: alert on stale heartbeats and unpolled published bets."""
    cfg = tunables()
    now = datetime.now(timezone.utc)
    in_racing_hours = cfg.watchdog.racing_hours_utc[0] <= now.hour < cfg.watchdog.racing_hours_utc[1]
    alerted_key_prefix = "watchdog_alerted_"

    async def alert_once(key: str, text: str) -> None:
        # One alert per condition per day — don't spam every watchdog tick.
        marker = repo.get_state(alerted_key_prefix + key)
        today = now.strftime("%Y-%m-%d")
        if marker != today:
            repo.set_state(alerted_key_prefix + key, today)
            await notifier.send(messages.watchdog_alert(key, text))

    wa_age = repo.heartbeat_age_seconds("whatsapp_forwarder")
    if wa_age is not None and wa_age > cfg.watchdog.whatsapp_heartbeat_stale_minutes * 60:
        await alert_once("whatsapp_forwarder", f"no heartbeat for {wa_age/60:.0f} min — check the phone")

    tg_age = repo.heartbeat_age_seconds("telegram_listener")
    if in_racing_hours and tg_age is not None and tg_age > cfg.watchdog.telegram_quiet_alert_hours * 3600:
        await alert_once("telegram_listener", f"no Telegram events for {tg_age/3600:.1f} h during racing hours")

    # BFBM not polling while bets are waiting is the dangerous case.
    published = repo.bets_in_state("PUBLISHED")
    if published:
        poll_age = repo.heartbeat_age_seconds("bfbm_poller")
        limit = cfg.feed.expected_poll_interval_seconds * 3
        if poll_age is None or poll_age > limit:
            await alert_once("bfbm_poller",
                             f"{len(published)} bets waiting but BFBM hasn't polled the feed "
                             f"({'never' if poll_age is None else f'{poll_age:.0f}s ago'})")
