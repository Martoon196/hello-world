"""Member-facing portal: login page, member dashboard, delivery-mode switch,
and the per-member Auto-Bet feed endpoint."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from betbot.apex import emails
from betbot.apex.store import ApexStore
from betbot.config import tunables
from betbot.db.repo import Repo
from betbot.execution.bfbm_feed import render_feed_csv
from betbot.members.auth import current_member
from betbot.members.repo import ACTIVE_STATUSES, MembersRepo

TEMPLATES_DIR = Path(__file__).parent / "templates"


def build_portal_router(repo: Repo, mrepo: MembersRepo, notifier=None) -> APIRouter:
    router = APIRouter()
    store = ApexStore(repo)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["money"] = emails.money
    templates.env.filters["odds"] = emails.odds
    templates.env.filters["day"] = emails.day_label

    @router.get("/login")
    def login(request: Request, expired: int = 0):
        return templates.TemplateResponse(request, "login.html", {"expired": expired})

    @router.get("/members")
    def members_home(request: Request):
        member = current_member(request, mrepo)
        if member is None:
            return RedirectResponse("/login", status_code=303)
        features = mrepo.features_for(member)
        base = tunables().apex.base_url.rstrip("/")
        active = member["status"] in ACTIVE_STATUSES
        return templates.TemplateResponse(request, "members.html", {
            "member": member,
            "features": features,
            "active": active,
            "paid": member["tier"] != "paddock",
            "selections": (store.open_selections(date.today().isoformat())
                           if "selections" in features else []),
            "log_rows": store.log_rows(limit=200) if "full_log" in features else [],
            "feed_url": (f"{base}/feed/member/{member['feed_token']}.csv"
                         if "auto_bet" in features else None),
            "s": store.settings(),
            "asked": request.query_params.get("asked") == "1",
        })

    @router.post("/members/question")
    async def ask_question(request: Request, question: str = Form(...)):
        member = current_member(request, mrepo)
        if member is None:
            return RedirectResponse("/login", status_code=303)
        if "qa" not in mrepo.features_for(member):
            return PlainTextResponse("Ask the Analyst is not included in your plan.", status_code=403)
        if notifier is not None and question.strip():
            await notifier.send(f"❓ Ask the Analyst — {member['email']}:\n{question.strip()[:2000]}")
        return RedirectResponse("/members?asked=1", status_code=303)

    @router.post("/members/delivery")
    def set_delivery(request: Request, mode: str = Form(...)):
        member = current_member(request, mrepo)
        if member is None:
            return RedirectResponse("/login", status_code=303)
        if mode == "auto" and "auto_bet" not in mrepo.features_for(member):
            return PlainTextResponse("Auto-Bet is not included in your plan.", status_code=403)
        if mode in ("manual", "auto"):
            mrepo.update_member(member["id"], delivery_mode=mode)
        return RedirectResponse("/members", status_code=303)

    @router.post("/members/feed/rotate")
    def rotate_feed(request: Request):
        member = current_member(request, mrepo)
        if member is None:
            return RedirectResponse("/login", status_code=303)
        mrepo.rotate_feed_token(member["id"])
        return RedirectResponse("/members", status_code=303)

    @router.get("/feed/member/{token}.csv")
    def member_feed(token: str, request: Request) -> Response:
        member = mrepo.get_member_by_feed_token(token)
        if (member is None
                or member["status"] not in ACTIVE_STATUSES
                or member["delivery_mode"] != "auto"
                or "auto_bet" not in mrepo.features_for(member)):
            return PlainTextResponse("not found", status_code=404)
        body, bet_ids = render_feed_csv(repo)
        client_ip = request.client.host if request.client else None
        mrepo.log_member_feed(member["id"], client_ip, len(bet_ids))
        return PlainTextResponse(body, media_type="text/csv")

    return router
