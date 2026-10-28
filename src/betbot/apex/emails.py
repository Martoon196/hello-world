"""Apex lifecycle emails. Copy follows the brand constants: no profit promises,
every result shown (losers included), no numbers that aren't in the official log."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import date, timedelta

from betbot.apex.store import ApexStore
from betbot.config import tunables
from betbot.members import mailer
from betbot.members.repo import MembersRepo

log = logging.getLogger(__name__)

WELCOME_LINK_TTL_MINUTES = 72 * 60
TIER_NAMES = {"founding": "Founding 50", "member": "Apex Member", "pro": "Apex Pro",
              "paddock": "The Paddock"}


def site_url() -> str:
    return tunables().apex.site_url.rstrip("/")


def members_url() -> str:
    return tunables().apex.base_url.rstrip("/")


def money(pence: int | None) -> str:
    if pence is None:
        return "—"
    sign = "+" if pence > 0 else ("−" if pence < 0 else "")
    return f"{sign}£{abs(pence) / 100:,.2f}"


def odds(price_x100: int | None) -> str:
    return f"{price_x100 / 100:.2f}" if price_x100 else "—"


def day_label(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')}"


def log_line(row: sqlite3.Row) -> str:
    if row["result"] == "no_bet":
        return f"{day_label(row['race_date'])} · {row['system']} · NO BET — {row['reasoning'] or 'no qualifier'}"
    where = " ".join(x for x in (row["venue"], row["event_time"]) if x)
    pos = f" · {row['position']}" if row["position"] else ""
    return (f"{day_label(row['race_date'])} · {row['selection']}"
            f"{' (' + where + ')' if where else ''}{pos} · {row['result'].upper()} · "
            f"{money(row['pnl_pence'])}")


def unsub_url(mrepo: MembersRepo, member_id: int) -> str:
    return f"{members_url()}/unsubscribe/{mrepo.ensure_unsub_token(member_id)}"


# ---- one-off emails ----

def send_paddock_welcome(mrepo: MembersRepo, member_id: int) -> bool:
    member = mrepo.get_member(member_id)
    body = (
        "You're in.\n\n"
        "The Paddock is the free tier of The Apex Code. Here's what you get:\n\n"
        f"- The Bank Builder guide, starting now: {site_url()}/bank-builder.html\n"
        "  How to set up a betting bank, a staking plan, and a tipster lie-detector.\n"
        "  Use it on us; use it on everyone.\n"
        "- One free selection a week, with the full reasoning members get.\n"
        "- The full results log every Sunday. Every bet, wins and losses alike.\n\n"
        "The live feed runs on Telegram: https://t.me/TheApexCodeUK\n\n"
        "Questions? Just reply to this email.\n\n"
        "— The Apex Code")
    return mailer.send_email(member["email"], "You're in — welcome to The Paddock", body,
                             unsubscribe_url=unsub_url(mrepo, member_id))


def send_member_welcome(mrepo: MembersRepo, store: ApexStore, member_id: int) -> bool:
    """Sent once, the first time a member becomes active on a paid tier."""
    member = mrepo.get_member(member_id)
    token = mrepo.create_magic_link(member_id, ttl_minutes=WELCOME_LINK_TTL_MINUTES)
    tier = TIER_NAMES.get(member["tier"], member["tier"])
    lines = [
        f"Welcome to The Apex Code — you're on {tier}.",
        "",
        "Step 1 — sign in to the members area (this link works once, for 72 hours):",
        f"{members_url()}/auth/verify?token={token}",
        f"After that, get a fresh link any time at {members_url()}/login",
        "",
        "What happens next:",
        "- Selections land by about 10am on qualifying days, with the stake %, minimum price "
        "and target. No-bet days are announced too — that's the discipline.",
        "- Every result is logged within 24 hours, losers included.",
        f"- New to staking? Read the Bank Builder first: {site_url()}/bank-builder.html",
    ]
    invite = store.setting("members_telegram_invite")
    if invite:
        lines += ["", f"Join the members' Telegram: {invite}"]
    portal = store.setting("billing_portal_url")
    lines += ["", "Your billing, your call:"]
    if portal:
        lines.append(f"- Change plan, switch to yearly or cancel: {portal}")
    lines += ["- Want a 30-day pause instead of cancelling? Reply to this email.",
              "- Changed your mind within 14 days? Reply and you'll get a full refund.",
              "", "Only ever bet inside a bank you can afford to lose entirely.",
              "", "— The Apex Code"]
    ok = mailer.send_email(member["email"], f"You're in — welcome to {tier}", "\n".join(lines))
    if ok:
        mrepo.mark_welcomed(member_id)
    return ok


def send_free_pick(mrepo: MembersRepo, row: sqlite3.Row) -> int:
    """The Paddock's weekly free selection. Returns emails sent."""
    where = " ".join(x for x in (row["venue"], row["event_time"]) if x)
    lines = ["This week's free selection from The Apex Code — the same format members get.", "",
             row["system"].upper(),
             f"{row['selection']}{' — ' + where if where else ''}",
             f"Market: {row['market'] or '—'}",
             f"Minimum price: {odds(row['price_x100'])}"]
    if row["stake_pct"] is not None:
        lines.append(f"Stake: {row['stake_pct']:g}% of bank")
    body = "\n".join(lines) + "\n\n"
    if row["reasoning"]:
        body += f"Why: {row['reasoning']}\n\n"
    body += ("The result goes in the public log either way, win or lose: "
             f"{site_url()}/#log\n\n"
             "Never stake more than your plan says. If the price is gone, the bet is gone.\n\n"
             "— The Apex Code")
    sent = 0
    for m in mrepo.paddock_list():
        if mailer.send_email(m["email"], f"Free pick: {row['selection']}", body,
                             unsubscribe_url=unsub_url(mrepo, m["id"])):
            sent += 1
    return sent


# ---- scheduled emails ----

def weekly_log_body(store: ApexStore, today: date | None = None) -> tuple[str, int]:
    today = today or date.today()
    start = today - timedelta(days=6)
    rows = store.settled_between(start.isoformat(), today.isoformat())
    lines = [f"The Apex Code log — week ending {today.day} {today.strftime('%B')}", ""]
    if rows:
        lines += ["Every result this week, in the order they ran:", ""]
        lines += [f"- {log_line(r)}" for r in rows]
        pnl = sum(r["pnl_pence"] or 0 for r in rows if r["result"] in ("won", "lost", "void"))
        lines += ["", f"Week total: {money(pnl)}"]
    else:
        lines += ["No results were logged this week."]
    lines += ["", f"The full log, from bet one: {site_url()}/#log", "",
              "Past results don't predict future results. Bet only what you can afford to lose.",
              "", "— The Apex Code"]
    return "\n".join(lines), len(rows)


async def send_weekly_log(mrepo: MembersRepo, store: ApexStore, notifier=None,
                          force: bool = False) -> int:
    if not force and not store.enabled("sunday_email_enabled"):
        return 0
    body, _ = weekly_log_body(store)
    recipients = mrepo.weekly_email_list()
    sent = 0
    for m in recipients:
        ok = await asyncio.to_thread(
            mailer.send_email, m["email"], "The Apex Code — this week's log", body,
            unsubscribe_url=unsub_url(mrepo, m["id"]))
        sent += int(ok)
    if notifier is not None:
        await notifier.send(f"📬 Sunday log email sent to {sent}/{len(recipients)}")
    return sent


async def send_verdict_requests(mrepo: MembersRepo, store: ApexStore, notifier=None) -> int:
    if not store.enabled("verdict_email_enabled"):
        return 0
    body = ("You've been with The Apex Code for a month.\n\n"
            "What's the honest verdict so far? Good, bad, or 'not sure yet' — all useful.\n"
            "Just reply to this email. With your permission we may quote you, critical "
            "answers included. That's the deal with an honest log.\n\n"
            "— The Apex Code")
    sent = 0
    for m in mrepo.members_due_verdict():
        ok = await asyncio.to_thread(
            mailer.send_email, m["email"], "A month in — what's the honest verdict?", body,
            unsubscribe_url=unsub_url(mrepo, m["id"]))
        if ok:
            mrepo.mark_verdict_asked(m["id"])
            sent += 1
    if sent and notifier is not None:
        await notifier.send(f"🗣 Day-30 verdict request sent to {sent} member(s)")
    return sent
