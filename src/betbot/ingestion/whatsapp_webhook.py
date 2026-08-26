"""WhatsApp ingest webhook.

The spare Android phone runs MacroDroid: on a WhatsApp notification it POSTs
{title, text} here. `title` is the chat/group name — it's matched against
registered whatsapp sources by chat_id (we use the notification title as the
chat identifier, since Android notifications don't expose a stable group id).
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from betbot.config import secrets
from betbot.db.repo import Repo

log = logging.getLogger(__name__)


class WhatsAppNotification(BaseModel):
    title: str          # notification title = chat/group name (or "Group: Sender")
    text: str           # notification body = the message text
    sender: str | None = None


def build_whatsapp_router(repo: Repo, pipeline) -> APIRouter:
    router = APIRouter()

    @router.post("/ingest/whatsapp")
    async def ingest(payload: WhatsAppNotification, background: BackgroundTasks,
                     token: str = "") -> PlainTextResponse:
        expected = secrets().whatsapp_webhook_token
        if not expected or not hmac.compare_digest(token, expected):
            return PlainTextResponse("not found", status_code=404)

        repo.beat("whatsapp_forwarder")

        # Group notifications often come as "Group name: Sender" — try full title
        # first, then the part before the colon.
        chat_id = payload.title.strip()
        source = repo.find_source("whatsapp", chat_id, payload.sender)
        if source is None and ":" in chat_id:
            source = repo.find_source("whatsapp", chat_id.split(":")[0].strip(), payload.sender)

        h = hashlib.sha256(payload.text.strip().lower().encode()).hexdigest()
        raw_id = repo.insert_raw_message(
            source_id=source["id"] if source else None,
            platform="whatsapp",
            platform_message_id=None,
            is_edit=False,
            message_text=payload.text,
            image_path=None,   # notification text only; image tips need the Telegram leg
            content_hash=h,
        )
        background.add_task(pipeline.process_raw_message, raw_id)
        return PlainTextResponse("ok")

    return router
