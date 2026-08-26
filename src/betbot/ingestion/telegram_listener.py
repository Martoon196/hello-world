"""Telethon user-session listener: stores every message from configured chats,
then hands whitelisted ones to the pipeline.

Non-whitelisted chats' messages are stored (audit) but never bet on — the
whitelist check lives in the pipeline, enforced again before parsing.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from telethon import TelegramClient, events

from betbot.config import secrets
from betbot.db.repo import Repo

log = logging.getLogger(__name__)

IMAGES_DIR = Path("data/images")


def content_hash(text: str | None, image_bytes: bytes | None) -> str:
    h = hashlib.sha256()
    h.update((text or "").strip().lower().encode())
    if image_bytes:
        h.update(image_bytes)
    return h.hexdigest()


class TelegramListener:
    def __init__(self, repo: Repo, pipeline):
        self.repo = repo
        self.pipeline = pipeline
        s = secrets()
        self.client = TelegramClient(s.telegram_session_name, s.telegram_api_id, s.telegram_api_hash)

    async def start(self) -> None:
        self.client.add_event_handler(self._on_message, events.NewMessage())
        self.client.add_event_handler(self._on_edit, events.MessageEdited())
        await self.client.start()
        log.info("telegram listener started")

    async def _on_message(self, event) -> None:
        await self._handle(event, is_edit=False)

    async def _on_edit(self, event) -> None:
        await self._handle(event, is_edit=True)

    async def _handle(self, event, *, is_edit: bool) -> None:
        try:
            self.repo.beat("telegram_listener")
            chat_id = str(event.chat_id)
            sender_id = str(event.sender_id) if event.sender_id else None
            source = self.repo.find_source("telegram", chat_id, sender_id)

            text = event.raw_text or None
            image_path = None
            image_bytes = None
            if event.photo:
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                image_bytes = await event.download_media(bytes)
                if image_bytes:
                    name = hashlib.sha256(image_bytes).hexdigest()[:16] + ".jpg"
                    path = IMAGES_DIR / name
                    path.write_bytes(image_bytes)
                    image_path = str(path)

            if not text and not image_path:
                return

            raw_id = self.repo.insert_raw_message(
                source_id=source["id"] if source else None,
                platform="telegram",
                platform_message_id=str(event.id),
                is_edit=is_edit,
                message_text=text,
                image_path=image_path,
                content_hash=content_hash(text, image_bytes),
            )
            await self.pipeline.process_raw_message(raw_id)
        except Exception:
            log.exception("telegram handler failed")
