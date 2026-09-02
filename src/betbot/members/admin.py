"""Admin panel (/admin): manage members, flip tier features and per-member
overrides live — the switchable-tools control room. Protected by the same
basic-auth as the ops dashboard."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from betbot.dashboard.app import _require_dashboard_auth
from betbot.members.repo import MembersRepo

TEMPLATES_DIR = Path(__file__).parent / "templates"

VALID_PERIODS = ("free", "monthly", "yearly", "lifetime")
VALID_STATUSES = ("active", "trialing", "past_due", "canceled", "paused")


def build_admin_router(mrepo: MembersRepo, repo) -> APIRouter:
    router = APIRouter(dependencies=[Depends(_require_dashboard_auth)])
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @router.get("/admin")
    def admin_home(request: Request):
        members = mrepo.list_members()
        tiers = mrepo.list_tiers()
        features = mrepo.list_features()
        tier_map = mrepo.tier_feature_map()
        rows = [{
            "m": m,
            "features": sorted(mrepo.features_for(m)),
            "overrides": mrepo.member_overrides(m["id"]),
        } for m in members]
        return templates.TemplateResponse(request, "admin.html", {
            "rows": rows, "tiers": tiers, "features": features, "tier_map": tier_map,
            "periods": VALID_PERIODS, "statuses": VALID_STATUSES,
            "founding_count": repo.get_state("founding_count", "0"),
        })

    @router.post("/admin/member/create")
    def create_member(email: str = Form(...), tier: str = Form("paddock")):
        if mrepo.get_member_by_email(email) is None:
            mrepo.create_member(email, tier=tier)
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/member/{member_id}")
    def update_member(member_id: int, tier: str = Form(None), status: str = Form(None),
                      billing_period: str = Form(None), delivery_mode: str = Form(None)):
        fields = {}
        if tier and any(t["name"] == tier for t in mrepo.list_tiers()):
            fields["tier"] = tier
        if status in VALID_STATUSES:
            fields["status"] = status
        if billing_period in VALID_PERIODS:
            fields["billing_period"] = billing_period
        if delivery_mode in ("manual", "auto"):
            fields["delivery_mode"] = delivery_mode
        mrepo.update_member(member_id, **fields)
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/member/{member_id}/feature")
    def member_feature(member_id: int, feature_key: str = Form(...), state: str = Form(...)):
        mrepo.set_member_feature(member_id, feature_key,
                                 None if state == "default" else state == "on")
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/tier-feature")
    def tier_feature(tier: str = Form(...), feature_key: str = Form(...), enabled: str = Form(...)):
        mrepo.set_tier_feature(tier, feature_key, enabled == "on")
        return RedirectResponse("/admin", status_code=303)

    @router.post("/admin/founding-count")
    def founding_count(count: str = Form(...)):
        # Hand-updated only, per project constants: the software displays it, a human owns it.
        if count.isdigit():
            repo.set_state("founding_count", count)
        return RedirectResponse("/admin", status_code=303)

    return router
