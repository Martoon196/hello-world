"""Notification message templates. All money in cents at the boundary."""
from __future__ import annotations


def eur(cents: int | None) -> str:
    return f"€{(cents or 0) / 100:.2f}"


def price(cents: int | None) -> str:
    return f"{(cents or 0) / 100:.2f}"


def bet_queued(*, horse: str, course: str, race_time: str, side: str, stake_cents: int,
               available_cents: int, tipped_cents: int | None, source: str) -> str:
    lines = [f"🐎 Bet queued: {side} {horse} @ {price(available_cents)}",
             f"{course} {race_time} · stake {eur(stake_cents)} · source: {source}"]
    if tipped_cents and available_cents < tipped_cents:
        impact = int(stake_cents * (tipped_cents - available_cents) / 100)
        lines.append(f"⚠️ Price drifted: tipped {price(tipped_cents)}, now {price(available_cents)} "
                     f"— a win pays ~{eur(impact)} less")
    elif tipped_cents and available_cents > tipped_cents:
        impact = int(stake_cents * (available_cents - tipped_cents) / 100)
        lines.append(f"📈 Price drifted in our favour: tipped {price(tipped_cents)}, "
                     f"now {price(available_cents)} — a win pays ~{eur(impact)} more")
    return "\n".join(lines)


def bet_aborted(*, horse: str, course: str, reason: str, message: str, source: str) -> str:
    return (f"🚫 No bet: {horse} ({course}) — {reason}\n{message}\nsource: {source}")


def parse_problem(*, source: str, excerpt: str, why: str) -> str:
    return f"🤔 Couldn't act on a message from {source}: {why}\n« {excerpt[:200]} »"


def bet_settled(*, horse: str, result: str, net_pnl_cents: int, bankroll_cents: int,
                estimated: bool) -> str:
    emoji = "✅" if net_pnl_cents >= 0 else "❌"
    tag = " (estimated — awaiting BFBM export)" if estimated else ""
    return (f"{emoji} {result}: {horse} — {eur(net_pnl_cents)}{tag}\n"
            f"Bankroll: {eur(bankroll_cents)}")


def breaker_tripped(kind: str, detail: str) -> str:
    return f"🧯 Circuit breaker tripped ({kind}): {detail}\nBetting paused for today. /status for details."


def watchdog_alert(component: str, detail: str) -> str:
    return f"🚨 Watchdog: {component} — {detail}"


def daily_summary(*, bets: int, wins: int, net_pnl_cents: int, bankroll_cents: int,
                  drift_cost_cents: int) -> str:
    return (f"🌙 Daily summary: {bets} bets, {wins} won, P&L {eur(net_pnl_cents)}\n"
            f"Bankroll: {eur(bankroll_cents)} · price-drift impact today: {eur(drift_cost_cents)}")
