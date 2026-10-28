"""Public endpoints the marketing site (apexcode.uk) reads, plus Paddock join and
unsubscribe. Nothing here exposes today's open selections — those are paid."""
from __future__ import annotations

import asyncio
import base64
import hmac
import html
import logging
from datetime import date

from fastapi import APIRouter, Form, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response

from betbot.apex import emails
from betbot.apex.store import ApexStore
from betbot.config import secrets
from betbot.members.repo import MembersRepo

log = logging.getLogger(__name__)

PIXEL = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
EMAIL_MAX = 254


def _row_json(r) -> dict:
    return {
        "date": r["race_date"],
        "label": emails.day_label(r["race_date"]),
        "system": r["system"],
        "selection": r["selection"],
        "venue": r["venue"],
        "time": r["event_time"],
        "market": r["market"],
        "price": emails.odds(r["price_x100"]) if r["price_x100"] else None,
        "result": r["result"],
        "position": r["position"],
        "pnl_pence": r["pnl_pence"],
        "pnl": emails.money(r["pnl_pence"]) if r["pnl_pence"] is not None else None,
        "stake": emails.money(r["stake_pence"]).lstrip("+") if r["stake_pence"] else None,
    }


def build_public_router(mrepo: MembersRepo, store: ApexStore, notifier) -> APIRouter:
    router = APIRouter()

    @router.get("/public/log.json")
    def public_log() -> JSONResponse:
        today = date.today().isoformat()
        rows = [r for r in store.log_rows(limit=120)
                if r["result"] != "pending" or r["race_date"] < today]
        return JSONResponse(
            {"updated_at": store.log_last_updated(), "rows": [_row_json(r) for r in rows]},
            headers={"Cache-Control": "public, max-age=120"})

    @router.get("/public/stats.json")
    def public_stats() -> JSONResponse:
        remaining = store.setting("founding_remaining")
        return JSONResponse({
            "founding_remaining": int(remaining) if remaining.isdigit() else None,
            "yearly_member_url": store.setting("yearly_member_url") or None,
            "yearly_pro_url": store.setting("yearly_pro_url") or None,
            "billing_portal_url": store.setting("billing_portal_url") or None,
        }, headers={"Cache-Control": "public, max-age=120"})

    @router.get("/public/founders.json")
    def public_founders() -> JSONResponse:
        return JSONResponse({"founders": [
            {"name": f["display_name"], "joined": f["joined_label"], "line": f["line"]}
            for f in store.founders()]}, headers={"Cache-Control": "public, max-age=300"})

    @router.get("/public/hit")
    def hit(p: str = "/", r: str = "", us: str = "", um: str = "", uc: str = "") -> Response:
        try:
            store.count_view(path=p, referrer=r or None, utm_source=us or None,
                             utm_medium=um or None, utm_campaign=uc or None)
        except Exception:
            log.exception("page view not counted")
        return Response(PIXEL, media_type="image/gif", headers={"Cache-Control": "no-store"})

    @router.post("/public/paddock")
    async def paddock_join(email: str = Form(...), source: str = Form("website"),
                           x_apex_key: str | None = Header(default=None)) -> JSONResponse:
        secret = secrets().paddock_shared_secret
        if not secret or not x_apex_key or not hmac.compare_digest(secret, x_apex_key):
            return JSONResponse({"ok": False}, status_code=403)
        email = email.strip()
        if not email or len(email) > EMAIL_MAX or "@" not in email:
            return JSONResponse({"ok": False, "error": "invalid"}, status_code=400)
        member_id, send_welcome = mrepo.join_paddock(email, source[:40])
        welcomed = False
        if send_welcome:
            welcomed = await asyncio.to_thread(emails.send_paddock_welcome, mrepo, member_id)
            if notifier is not None:
                await notifier.send(f"🐎 New Paddock signup: {email}")
        return JSONResponse({"ok": True, "welcomed": welcomed})

    def _page(body: str) -> HTMLResponse:
        return HTMLResponse(
            "<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Unsubscribe · The Apex Code</title>"
            "<body style='background:#0A0A0A;color:#F2EDE3;font:16px/1.6 system-ui,sans-serif;"
            "display:flex;min-height:100vh;align-items:center;justify-content:center;"
            "text-align:center;padding:1.5rem'><div><h1 style='letter-spacing:.04em'>"
            f"THE APEX CODE</h1>{body}</div></body>")

    # GET only asks: mail scanners pre-fetch links, and must not unsubscribe anyone.
    @router.get("/unsubscribe/{token}")
    def unsubscribe_confirm(token: str) -> HTMLResponse:
        return _page(
            "<p>Stop all Apex Code emails, including the Sunday log?</p>"
            f"<form method='post' action='/unsubscribe/{html.escape(token, quote=True)}'>"
            "<button style='background:#ECB02B;color:#111;border:0;border-radius:6px;"
            "padding:.6rem 1.2rem;font-weight:600;cursor:pointer'>Unsubscribe</button></form>")

    # POST does it — also the one-click target of the List-Unsubscribe-Post header.
    @router.post("/unsubscribe/{token}")
    def unsubscribe_do(token: str) -> HTMLResponse:
        member = mrepo.unsubscribe(token)
        if member is None:
            return _page("<p>That unsubscribe link isn't valid.</p>")
        return _page("<p>You're unsubscribed. No more Apex emails.</p>"
                     "<p style='color:#9A948A'>Changed your mind? Join again any time at "
                     "<a style='color:#ECB02B' href='https://apexcode.uk/#paddock'>apexcode.uk</a>.</p>")

    return router
