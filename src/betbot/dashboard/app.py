"""Server-rendered dashboard (Jinja2, no JS build step). Seed of the future own UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from betbot.db.repo import Repo
from betbot.dashboard import queries
from betbot.ingestion import shadow
from betbot.ops import killswitch

TEMPLATES_DIR = Path(__file__).parent / "templates"


def build_dashboard_router(repo: Repo) -> APIRouter:
    router = APIRouter()
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
