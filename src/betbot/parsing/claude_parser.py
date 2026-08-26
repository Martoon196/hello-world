"""Structured tip extraction via the Anthropic API.

Uses client.messages.parse() with the ParsedMessage Pydantic schema so the
response is schema-validated JSON — no regex post-processing. Image tips go in
as base64 image blocks (vision) ahead of the instruction text.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

import anthropic

from betbot.config import tunables
from betbot.parsing.models import ParsedMessage

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You extract horse-racing betting tips from messages sent to betting tip groups.

Rules:
- A tip names a horse and (usually) a course and race time. Extract every distinct tip in the message.
- Messages that are chatter, greetings, results recaps ("winner!", P&L screenshots), adverts, or
  anything without an actionable selection are NOT tips: set is_tip=false and tips=[].
- Convert fractional odds to decimal (7/2 -> 4.5, evens -> 2.0). Leave tipped_price null if absent.
- race_time is as written (UK/IE local time, HH:MM 24h). "2.35" means 14:35 for afternoon racing.
- Copy the horse and course names as written; do not correct spelling.
- Set confidence low (< 0.8) whenever a field is a guess: missing course, unclear time,
  a name you had to infer, or a blurry image.
- side is LAY only when the message clearly says to lay/oppose the horse; otherwise BACK."""


class ParseError(Exception):
    """Raised when the message could not be parsed after retries."""


def _image_block(image_path: str) -> dict:
    media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    data = base64.standard_b64encode(Path(image_path).read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def parse_message(message_text: str | None, image_path: str | None = None,
                  client: anthropic.Anthropic | None = None) -> ParsedMessage:
    """Parse one raw message into structured tips. Raises ParseError on API failure."""
    cfg = tunables().parsing
    client = client or anthropic.Anthropic()

    content: list[dict] = []
    if image_path:
        content.append(_image_block(image_path))
    content.append({"type": "text", "text": message_text or "(image only — extract tips from the image)"})

    try:
        response = client.messages.parse(
            model=cfg.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            output_format=ParsedMessage,
        )
    except anthropic.RateLimitError as e:
        raise ParseError(f"rate limited: {e}") from e
    except anthropic.APIStatusError as e:
        raise ParseError(f"API error {e.status_code}: {e}") from e
    except anthropic.APIConnectionError as e:
        raise ParseError(f"connection error: {e}") from e

    parsed = response.parsed_output
    if parsed is None:
        raise ParseError("model returned no parseable output")
    return parsed
