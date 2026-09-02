"""Passwordless member auth: email -> magic link -> session cookie."""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from betbot.config import secrets, tunables
from betbot.members import mailer
from betbot.members.repo import MembersRepo

log = logging.getLogger(__name__)

SESSION_COOKIE = "apex_session"


def current_member(request: Request, mrepo: MembersRepo) -> Optional[sqlite3.Row]:
    token = request.cookies.get(SESSION_COOKIE)
    return mrepo.session_member(token) if token else None


def build_auth_router(mrepo: MembersRepo, notifier) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/request")
    async def request_link(email: str = Form(...)) -> PlainTextResponse:
        member = mrepo.get_member_by_email(email)
        if member is not None:
            token = mrepo.create_magic_link(member["id"])
            base = tunables().apex.base_url.rstrip("/")
            await mailer.send_magic_link(member["email"], f"{base}/auth/verify?token={token}",
                                         notifier=notifier)
        else:
            log.info("magic link requested for unknown email")
        # Same answer either way — no probing which emails are members.
        return PlainTextResponse(
            "If that email belongs to a member, a sign-in link is on its way. "
            "Check your inbox (and spam).")

    @router.get("/auth/verify")
    def verify(token: str = "") -> RedirectResponse:
        member_id = mrepo.consume_magic_link(token)
        if member_id is None:
            return RedirectResponse("/login?expired=1", status_code=303)
        session = mrepo.create_session(member_id)
        response = RedirectResponse("/members", status_code=303)
        response.set_cookie(SESSION_COOKIE, session, max_age=30 * 24 * 3600,
                            httponly=True, samesite="lax")
        return response

    @router.post("/auth/logout")
    def logout(request: Request) -> RedirectResponse:
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            mrepo.delete_session(token)
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE)
        return response

    return router
