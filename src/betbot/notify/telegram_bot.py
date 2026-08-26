"""Outbound Telegram notifications + inbound admin commands (/kill /resume /status).

Uses the official Bot API over httpx. The command listener long-polls
getUpdates and only obeys the configured admin chat id.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from betbot.config import secrets
from betbot.db.repo import Repo
from betbot.ops import killswitch

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, repo: Repo):
        self.repo = repo
        s = secrets()
        self.token = s.telegram_bot_token
        self.chat_id = s.telegram_admin_chat_id
        self._client = httpx.AsyncClient(timeout=20)

    @property
    def api(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    async def send(self, text: str) -> None:
        if not self.token or not self.chat_id:
            log.info("notify (no bot configured): %s", text)
            return
        try:
            await self._client.post(f"{self.api}/sendMessage",
                                    json={"chat_id": self.chat_id, "text": text})
        except httpx.HTTPError:
            log.exception("telegram notify failed")

    async def command_loop(self) -> None:
        """Long-poll for admin commands. Only the admin chat is obeyed."""
        if not self.token or not self.chat_id:
            return
        offset = 0
        while True:
            try:
                r = await self._client.get(f"{self.api}/getUpdates",
                                           params={"timeout": 50, "offset": offset},
                                           timeout=60)
                for update in r.json().get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message") or {}
                    if str(msg.get("chat", {}).get("id")) != str(self.chat_id):
                        continue
                    await self._handle_command((msg.get("text") or "").strip().lower())
            except (httpx.HTTPError, ValueError, KeyError):
                log.exception("telegram command loop error")
                await asyncio.sleep(10)

    async def _handle_command(self, text: str) -> None:
        if text.startswith("/kill"):
            killswitch.set_kill(self.repo, True)
            n = len(self.repo.bets_in_state("PUBLISHED"))
            for bet in self.repo.bets_in_state("PUBLISHED"):
                self.repo.set_bet_state(bet["id"], "EXPIRED")
            await self.send(f"🛑 KILL SWITCH ON. Feed emptied ({n} pending bets withdrawn). "
                            f"No new bets until /resume.")
        elif text.startswith("/resume"):
            killswitch.set_kill(self.repo, False)
            await self.send("✅ Kill switch off — betting resumed.")
        elif text.startswith("/status"):
            bank = self.repo.current_bankroll_cents() / 100
            open_bets = len(self.repo.bets_in_state("PUBLISHED", "CONSUMED"))
            pnl_today = self.repo.realized_pnl_today_cents() / 100
            kill = "ON 🛑" if killswitch.is_kill_on(self.repo) else "off"
            await self.send(f"📊 Bankroll €{bank:.2f} | open bets {open_bets} | "
                            f"P&L today €{pnl_today:+.2f} | kill switch {kill}")
