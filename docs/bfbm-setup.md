# BF Bot Manager setup (Windows VPS)

Goal: BFBM is a **dumb order-placer plus dead-man backstop**. Our rules engine
owns every discretionary decision; BFBM only executes what the feed serves and
guards the last few seconds we can't see. Configure it exactly as below and
document any deviation here.

## 1. Install

1. Windows VPS (2 GB RAM is plenty). Install BF Bot Manager V3 (Betfair version).
2. Log in with the Betfair account. Enable auto-start of BFBM on VPS boot.

## 2. Import tips from URL

- Strategy: **"Bet on imported tips"** with URL import.
- URL: `https://<your-host>/feed/bfbm.csv?token=<FEED_TOKEN>` (HTTPS only).
- Poll interval: 30 s (must match `feed.expected_poll_interval_seconds` in
  `config/settings.yaml` — the watchdog alerts at 3× this).
- Map columns per the feed header:
  `RaceDate, RaceTime, Course, MarketId, SelectionId, SelectionName, BetType, MinPrice, Stake, Notes`
- **Match on MarketId + SelectionId**, not names. SelectionName is a
  human-readable fallback only.
- The `Notes` column carries our `tip_NNNNN` marker — it must be preserved into
  BFBM's bet logs (it's how results round-trip back to betbot).

## 3. Betting settings

- Bet type: from the `BetType` column (BACK/LAY).
- Stake: **from the `Stake` column**. Disable ALL BFBM staking plans (no
  percentage rules, no Fibonacci/recovery, nothing).
- Min price: **from the `MinPrice` column** (this is our floor — BFBM must not
  bet below it, and should take best available at/above it).
- Bet timing: place immediately on import (betbot already holds bets until the
  right moment; feed rows vanish 60 s before the off).

## 4. Keep enabled (the backstop)

- Non-runner handling: skip removed runners.
- Suspended-market handling: skip/retry per BFBM default.
- One absolute max-stake safety rule set ABOVE our cap (e.g. €150 when our
  `absolute_max_stake_cents` is €100) — it should only ever fire if betbot is buggy.

## 5. Disable

- Every other rule, trigger, recovery plan, and price rule. If BFBM blocks or
  reshapes a bet our engine approved, the two rule layers are fighting — that's
  a config bug.

## 6. Results export back to betbot

Create `C:\betbot\post-results.ps1`:

```powershell
$log = "C:\path\to\bfbm\bet-log.csv"   # BFBM's bet log / results export file
if (Test-Path $log) {
  Invoke-RestMethod -Uri "https://<your-host>/ingest/bfbm-results?token=<BFBM_RESULTS_TOKEN>" `
    -Method Post -InFile $log -ContentType "text/csv"
}
```

Task Scheduler: run it every 30 minutes. Betbot parses the CSV tolerantly (any
column layout with a price, a matched size, and the `tip_NNNNN` marker works).

## 7. Verification checklist (Phase 5 gate)

- [ ] BFBM polls the feed (watch `feed_downloads` / dashboard heartbeat).
- [ ] A €2 test bet flows end-to-end and the matched price lands back in betbot.
- [ ] `/kill` in Telegram empties the feed within one poll and BFBM places nothing.
- [ ] Stopping BFBM triggers the "not polling" alert within ~2 minutes.
- [ ] A deliberately price-collapsed row (MinPrice above current price) is NOT placed.
