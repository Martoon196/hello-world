"""Admin panel (/admin): the funnel, the official log, members and the tier
switchboard, site settings, the Founder Wall and email tools. Protected by the
same basic-auth as the ops dashboard."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from betbot.apex import emails
from betbot.apex.store import RESULTS, SETTINGS, SYSTEMS, ApexStore
from betbot.dashboard.app import _require_dashboard_auth
from betbot.members import mailer
from betbot.members.repo import MembersRepo

TEMPLATES_DIR = Path(__file__).parent / "templates"

VALID_PERIODS = ("free", "monthly", "yearly", "lifetime")
VALID_STATUSES = ("active", "trialing", "past_due", "canceled", "paused")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHARE_LINK = "apexcode.uk/?utm_source=social&utm_medium=post&utm_campaign=daily-result"


def parse_pounds(text: str | None) -> int | None:
    """'£31.12', '-122.35', '−30' -> pence. Blank -> None. Raises ValueError on junk."""
    if text is None or not text.strip():
        return None
    cleaned = text.strip().replace("£", "").replace(",", "").replace("−", "-").replace("+", "")
    return int(round(float(cleaned) * 100))


def parse_number(text: str | None) -> float | None:
    if text is None or not text.strip():
        return None
    return float(text.strip())


def back(msg: str, anchor: str = "") -> RedirectResponse:
    return RedirectResponse(f"/admin?msg={quote(msg)}{anchor}", status_code=303)


def share_text(row) -> str:
    outcome = row["position"] or row["result"].upper()
    return (f"{emails.day_label(row['race_date'])} · {row['selection']} · {outcome} · "
            f"{emails.money(row['pnl_pence'])}. Every result logged, losers included → {SHARE_LINK}")


def build_admin_router(mrepo: MembersRepo, repo, notifier=None) -> APIRouter:
    router = APIRouter(dependencies=[Depends(_require_dashboard_auth)])
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["money"] = emails.money
    templates.env.filters["odds"] = emails.odds
    templates.env.filters["day"] = emails.day_label
    store = ApexStore(repo)

    @router.get("/admin")
    def admin_home(request: Request):
        members = mrepo.list_members()
        rows = [{
            "m": m,
            "features": sorted(mrepo.features_for(m)),
            "overrides": mrepo.member_overrides(m["id"]),
        } for m in members if m["tier"] != "paddock"]
        log_rows = store.log_rows(limit=40)
        weekly_body, weekly_rows = emails.weekly_log_body(store)
        return templates.TemplateResponse(request, "admin.html", {
            "rows": rows, "tiers": mrepo.list_tiers(), "features": mrepo.list_features(),
            "tier_map": mrepo.tier_feature_map(),
            "periods": VALID_PERIODS, "statuses": VALID_STATUSES,
            "funnel": store.funnel(), "sources": store.top_sources(30),
            "log_rows": log_rows, "shares": {r["id"]: share_text(r) for r in log_rows},
            "systems": SYSTEMS, "results": RESULTS,
            "s": store.settings(), "setting_keys": list(SETTINGS),
            "founders": store.founders(approved_only=False),
            "weekly_body": weekly_body, "weekly_rows": weekly_rows,
            "smtp_ok": mailer.smtp_configured(),
            "msg": request.query_params.get("msg"),
        })

    # ---- official log ----

    @router.post("/admin/log/add")
    async def log_add(race_date: str = Form(...), system: str = Form(...),
                      selection: str = Form(""), venue: str = Form(""), event_time: str = Form(""),
                      market: str = Form(""), price: str = Form(""), stake: str = Form(""),
                      stake_pct: str = Form(""), reasoning: str = Form(""),
                      no_bet: str = Form(""), free_pick: str = Form("")):
        if not DATE_RE.match(race_date) or system not in SYSTEMS:
            return back("Need a date (YYYY-MM-DD) and a system.", "#log")
        is_no_bet = no_bet == "on"
        if not is_no_bet and not selection.strip():
            return back("Need a selection (or tick 'no-bet day').", "#log")
        try:
            price_val = parse_number(price)
            stake_pence = parse_pounds(stake)
            pct = parse_number(stake_pct)
        except ValueError:
            return back("Price, stake and stake % must be numbers.", "#log")
        if not is_no_bet:
            if pct is None:
                return back("Stake % of bank is required — it's the published rule.", "#log")
            cap = float(store.setting("stake_cap_pct") or 3)
            if pct > cap:
                return back(f"Not logged: {pct:g}% is above the published {cap:g}% cap. The Discipline "
                            "Guarantee makes that a free month. Lower the stake, or change the "
                            "published cap (site + settings) first.", "#log")
        row_id = store.add_log_row(
            race_date=race_date, system=system,
            selection=selection.strip() or "No bet", venue=venue.strip() or None,
            event_time=event_time.strip() or None, market=market.strip() or None,
            price_x100=int(round(price_val * 100)) if price_val else None,
            stake_pence=stake_pence, stake_pct=pct, reasoning=reasoning.strip() or None,
            free_pick=free_pick == "on" and not is_no_bet,
            result="no_bet" if is_no_bet else "pending")
        msg = "Logged."
        if free_pick == "on" and not is_no_bet:
            sent = await asyncio.to_thread(emails.send_free_pick, mrepo, store.get_log_row(row_id))
            msg = f"Logged, and sent to {sent} Paddock subscriber(s) as the free pick."
        return back(msg, "#log")

    @router.post("/admin/log/{row_id}/settle")
    def log_settle(row_id: int, result: str = Form(...), position: str = Form(""),
                   pnl: str = Form("")):
        if result not in RESULTS:
            return back("Unknown result.", "#log")
        try:
            pnl_pence = parse_pounds(pnl)
        except ValueError:
            return back("P/L must be a number of pounds, e.g. -20 or 11.40.", "#log")
        if result in ("won", "lost") and pnl_pence is None:
            return back("A won or lost result needs its P/L — no blanks in the log.", "#log")
        store.settle_log_row(row_id, result=result, position=position.strip() or None,
                             pnl_pence=pnl_pence)
        return back("Result saved — it's live on the site.", "#log")

    # ---- settings ----

    @router.post("/admin/settings")
    async def save_settings(request: Request):
        form = await request.form()
        for key in SETTINGS:
            if key.endswith("_enabled"):
                store.set_setting(key, "1" if form.get(key) == "on" else "0")
            elif key in form:
                value = str(form.get(key, ""))
                if key in ("founding_remaining",) and value and not value.isdigit():
                    continue
                store.set_setting(key, value)
        return back("Settings saved.", "#settings")

    # ---- founder wall ----

    @router.post("/admin/founders/add")
    def founder_add(display_name: str = Form(...), joined_label: str = Form(""), line: str = Form("")):
        store.add_founder(display_name, joined_label.strip() or None, line.strip() or None)
        return back("Added — approve it once the founder says yes.", "#founders")

    @router.post("/admin/founders/{founder_id}")
    def founder_update(founder_id: int, action: str = Form(...)):
        if action == "approve":
            store.set_founder_approved(founder_id, True)
        elif action == "hide":
            store.set_founder_approved(founder_id, False)
        elif action == "delete":
            store.delete_founder(founder_id)
        return back("Founder Wall updated.", "#founders")

    # ---- email tools ----

    @router.post("/admin/email/test")
    async def email_test(to: str = Form(...)):
        ok = await asyncio.to_thread(mailer.send_email, to, "Apex Code test email",
                                     "If you can read this, outgoing email works.")
        return back("Test email sent." if ok else "Test email FAILED — check the SMTP settings.", "#email")

    @router.post("/admin/email/weekly-test")
    async def weekly_test(to: str = Form(...)):
        body, _ = emails.weekly_log_body(store)
        ok = await asyncio.to_thread(mailer.send_email, to, "[TEST] The Apex Code — this week's log", body)
        return back("Preview sent." if ok else "Preview FAILED — check SMTP.", "#email")

    @router.post("/admin/email/weekly-now")
    async def weekly_now(confirm: str = Form("")):
        if confirm != "SEND":
            return back("Type SEND to confirm sending to the whole list.", "#email")
        sent = await emails.send_weekly_log(mrepo, store, notifier, force=True)
        return back(f"Weekly log sent to {sent} people.", "#email")

    # ---- members & switchboard ----

    @router.post("/admin/member/create")
    def create_member(email: str = Form(...), tier: str = Form("paddock")):
        if mrepo.get_member_by_email(email) is None:
            mrepo.create_member(email, tier=tier)
        return back("Member added.", "#members")

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
        return back("Member saved.", "#members")

    @router.post("/admin/member/{member_id}/feature")
    def member_feature(member_id: int, feature_key: str = Form(...), state: str = Form(...)):
        mrepo.set_member_feature(member_id, feature_key,
                                 None if state == "default" else state == "on")
        return back("Override saved.", "#members")

    @router.post("/admin/tier-feature")
    def tier_feature(tier: str = Form(...), feature_key: str = Form(...), enabled: str = Form(...)):
        mrepo.set_tier_feature(tier, feature_key, enabled == "on")
        return back("Switchboard updated.", "#switchboard")

    return router
