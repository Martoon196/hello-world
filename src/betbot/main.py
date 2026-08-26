"""betbot entrypoint: wires DB, listener, FastAPI app, and scheduled jobs.

Degrades gracefully: components without credentials (Telegram, Betfair,
Anthropic) log a warning and stay off, so the dashboard and DB always run.
"""
from __future__ import annotations

import asyncio
import logging

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from betbot.config import secrets, tunables
from betbot.dashboard.app import build_dashboard_router
from betbot.db.database import connect, migrate
from betbot.db.repo import Repo
from betbot.execution.bfbm_feed import FeedExecutor, build_feed_router
from betbot.ingestion.pipeline import Pipeline
from betbot.ingestion.whatsapp_webhook import build_whatsapp_router
from betbot.notify import messages
from betbot.notify.telegram_bot import Notifier
from betbot.ops.heartbeat import build_heartbeat_router, watchdog_check
from betbot.settlement.bfbm_import import build_bfbm_results_router
from betbot.settlement.reconciler import Reconciler
from betbot.settlement.results_poller import poll_results

log = logging.getLogger(__name__)


async def _daily_summary(repo: Repo, notifier: Notifier) -> None:
    settled = repo.bets_settled_today()
    wins = sum(1 for b in settled if b["state"] == "SETTLED_WON")
    net = sum(b["net_pnl_cents"] or 0 for b in settled)
    drift = sum(
        int((b["matched_stake_cents"] or 0) * ((b["tipped_price_cents"] or 0) - (b["matched_price_cents"] or 0)) / 100)
        for b in settled
        if b["state"] == "SETTLED_WON" and b["tipped_price_cents"] and b["matched_price_cents"]
    )
    await notifier.send(messages.daily_summary(
        bets=len(settled), wins=wins, net_pnl_cents=net,
        bankroll_cents=repo.current_bankroll_cents(), drift_cost_cents=drift))


async def amain() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    s = secrets()
    cfg = tunables()

    conn = connect(s.betbot_db_path)
    migrate(conn)
    repo = Repo(conn)
    repo.seed_bankroll_if_empty(cfg.bankroll.opening_cents)

    notifier = Notifier(repo)
    executor = FeedExecutor(repo)

    betfair = None
    if s.betfair_username and s.betfair_app_key:
        from betbot.validation.betfair_client import BetfairClient
        betfair = BetfairClient()
    else:
        log.warning("Betfair credentials missing — validation/settlement disabled")

    pipeline = Pipeline(repo, betfair, executor, notifier)
    reconciler = Reconciler(repo, notifier)

    app = FastAPI(title="betbot", docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(build_feed_router(repo))
    app.include_router(build_whatsapp_router(repo, pipeline))
    app.include_router(build_bfbm_results_router(repo, reconciler))
    app.include_router(build_heartbeat_router(repo))
    app.include_router(build_dashboard_router(repo))

    scheduler = AsyncIOScheduler(timezone="UTC")
    if betfair:
        scheduler.add_job(poll_results, "interval",
                          seconds=cfg.settlement.results_poll_interval_seconds,
                          args=[repo, betfair, reconciler])
        scheduler.add_job(lambda: asyncio.to_thread(betfair.keep_alive), "interval", minutes=15)
    scheduler.add_job(watchdog_check, "interval", minutes=5, args=[repo, notifier])
    scheduler.add_job(_daily_summary, "cron", hour=cfg.notifications.daily_summary_hour_utc,
                      args=[repo, notifier])
    scheduler.start()

    tasks = [asyncio.create_task(notifier.command_loop())]

    if s.telegram_api_id and s.telegram_api_hash:
        from betbot.ingestion.telegram_listener import TelegramListener
        listener = TelegramListener(repo, pipeline)
        try:
            await listener.start()
        except Exception as e:
            # Keep the rest of the app (dashboard, feed, webhook) alive.
            log.error("Telegram listener disabled: %s", e)
            await notifier.send(f"⚠️ Telegram listener is OFF: {e}")
    else:
        log.warning("Telegram API credentials missing — Telegram ingestion disabled")

    server = uvicorn.Server(uvicorn.Config(app, host=s.betbot_host, port=s.betbot_port,
                                           log_level="info"))
    await notifier.send("🟢 betbot started")
    try:
        await server.serve()
    finally:
        for t in tasks:
            t.cancel()
        scheduler.shutdown(wait=False)


def run() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    run()
