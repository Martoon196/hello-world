"""Server-rendered dashboard (Jinja2, no JS build step). Seed of the future own UI.

Protected by HTTP Basic auth when DASHBOARD_PASSWORD is set (username: betbot).
Without it the dashboard is world-readable — set the password.
"""
from __future__ import annotations

import secrets as pysecrets
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from betbot.config import secrets
from betbot.db.repo import Repo
from betbot.dashboard import queries
from betbot.ingestion import shadow
from betbot.ops import killswitch

TEMPLATES_DIR = Path(__file__).parent / "templates"

_basic = HTTPBasic(auto_error=False)


def _require_dashboard_auth(credentials: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    password = secrets().dashboard_password
    if not password:
        return  # no password configured — open (setup.sh nags about this)
    ok = (credentials is not None
          and pysecrets.compare_digest(credentials.username, "betbot")
          and pysecrets.compare_digest(credentials.password, password))
    if not ok:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic realm=betbot"})


def build_dashboard_router(repo: Repo) -> APIRouter:
    router = APIRouter(dependencies=[Depends(_require_dashboard_auth)])
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["eur"] = lambda cents: f"€{(cents or 0) / 100:,.2f}"
    templates.env.filters["odds"] = lambda cents: f"{cents / 100:.2f}" if cents else "—"

    @router.get("/")
    def index(request: Request):
        conn = repo.conn
        tot = queries.totals(conn)
        settled = tot["settled"] or 0
        return templates.TemplateResponse(request, "index.html", {
            "bankroll_cents": repo.current_bankroll_cents(),
            "kill_on": killswitch.is_kill_on(repo),
            "shadow_on": shadow.is_shadow_on(repo),
            "totals": tot,
            "strike_rate": (tot["wins"] or 0) / settled * 100 if settled else 0,
            "roi": (tot["net_pnl_cents"] or 0) / tot["staked_cents"] * 100 if tot["staked_cents"] else 0,
            "sources": queries.per_source_stats(conn),
            "bets": queries.recent_bets(conn),
            "review": queries.needs_review(conn),
            "curve": queries.bankroll_curve(conn),
        })

    return router
