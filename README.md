# betbot — tip-driven horse-racing bet automation

Takes betting tips arriving in **Telegram** and **WhatsApp** groups, parses them
with Claude, validates them against **Betfair**, applies staking rules and
guardrails, and serves approved bets to **BF Bot Manager** (which places them on
Betfair under its licensed vendor key). Every bet, price, and result is tracked
in SQLite with a web dashboard — per-tipster ROI, strike rate, price-drift cost,
bankroll curve.

```
Telegram (Telethon) ─┐
                     ├─► Claude parser ─► Betfair validator ─► rules engine ─► CSV feed ─► BF Bot Manager ─► Betfair
WhatsApp (phone) ────┘         │                 │                  │
                               └── low confidence┴── abort/notify ──┴──► your Telegram
                                                                              ▲
                              results poller + BFBM export ─► reconciler ─► ledger + dashboard
```

## Design commitments

- **Executor-agnostic**: everything upstream of `src/betbot/execution/` doesn't
  know BF Bot Manager exists. v2 swaps in `flumine_executor.py` (direct Betfair
  API, live app key) with zero changes elsewhere.
- **Fail closed**: any doubt (low parse confidence, ambiguous market match,
  Betfair unreachable) means *no bet* plus a notification — never a guess.
- **Whitelist-first**: only registered chat/sender pairs can generate bets.
  Everything else is stored for audit and ignored.
- **Shadow mode by default**: the full pipeline runs and paper-settles against
  real results, but nothing reaches BF Bot Manager until you explicitly turn
  shadow off. Prove the tipsters before risking a euro.
- **Append-only money**: the bankroll is a ledger; estimates are corrected by
  new rows, never edited.

## Quick start (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env         # fill in what you have; components without creds stay off
pytest -m "not live_api"     # unit tests, no external calls
python -m betbot.main        # dashboard on http://localhost:8080
```

Register a tip source (nothing is bet on until whitelisted):

```bash
python scripts/add_source.py telegram -1001234567890 "Tipster John" --whitelist
python scripts/add_source.py --list
```

## Operations

- `/kill` `/resume` `/status` — Telegram commands to the notification bot
  (kill empties the BFBM feed within one poll).
- Shadow mode: `runtime_state.shadow_mode` (`on` by default). Turn off only
  after the Phase 3–4 paper-trading gate.
- `scripts/reconcile_bankroll.py` — deposits, withdrawals, weekly sync with the
  real Betfair balance.
- `scripts/replay_message.py <id>` — re-run the parser on a stored message.

## Build phases

See the plan: Phase 0 skeleton+ingestion → 1 parser+golden set → 2 Betfair
validation → 3 shadow mode → 4 settlement+dashboard (paper P&L proves the
tipsters) → 5 BFBM live at €2 minimum stakes → 6 WhatsApp leg + hardening →
7 ramp to full stakes. `docs/bfbm-setup.md` covers the BFBM VPS side.

## Homework (accounts code can't create)

Betfair account (funded, 2FA) · free delayed app key · BF Bot Manager
subscription · my.telegram.org API creds · @BotFather bot token · Anthropic API
key · Linux VPS (this app) + Windows VPS (BFBM) · spare Android phone with
MacroDroid for the WhatsApp leg.
