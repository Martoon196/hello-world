# Deal Sheet Scoring — Prop Invest UK

A small web app that turns the deal sheets people send you by WhatsApp, text and email into a consistent, scored assessment.

1. A sourcer opens the **submission form**, pastes their notes and drops in PDFs, photos or screenshots.
2. Claude reads everything and extracts the facts: address, price, value, refurb, rent, end value, tenure, vendor situation, sourcing fee, plus qualitative reads on location, condition risk, credibility of the numbers, and what's missing.
3. A **scoring matrix** (yours to edit, in `config/scoring-matrix.json`) turns those facts into a 0-100 score with a Pursue / Investigate / Pass rating, broken down metric by metric.
4. You review it all on a password-protected **dashboard**: the numbers as pitched, our working (yield, ROCE, profit on cost, money left in), red flags, missing information, and a ready-to-send list of questions for the sourcer.

Sourcers only ever see a "thanks, we've got it" message. Scores stay on your side.

## Run it

```bash
npm install
cp .env.example .env      # add your ANTHROPIC_API_KEY and a DASHBOARD_PASSWORD
set -a; . ./.env; set +a  # or use your host's env settings
npm start
```

- Form: http://localhost:3000/
- Dashboard: http://localhost:3000/dashboard.html (username `admin`, password from `DASHBOARD_PASSWORD`)

To try the UI without an API key: `MOCK_ANALYSIS=1 npm start` returns a canned Bolton BRR analysis for every submission.

Quick one-off from the terminal, no server needed:

```bash
npm run analyse -- --notes "3 bed terrace BL3, £95k agreed, worth £120k, £15k refurb, £850pcm" sheet.pdf photo.jpg
```

## Environment variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required unless `MOCK_ANALYSIS=1`. |
| `ANTHROPIC_MODEL` | Defaults to `claude-opus-5`. |
| `DASHBOARD_PASSWORD` | Protects the dashboard and the deal API. Set it. |
| `SUBMIT_TOKEN` | Optional. If set, the form only accepts submissions from links that include `?token=...`. Useful if the form URL gets passed around. |
| `DATA_DIR` | Where deals and uploads live. Defaults to `./data`. Point it at a persistent disk in production. |
| `PORT` | Defaults to 3000. |

## Put it on propinvestuk.co.uk

The app is self-contained, so the simplest route is:

1. Deploy it to any Node host with a persistent disk (Render, Railway, Fly.io, a small VPS). Set the env vars above and mount `DATA_DIR`.
2. Point a subdomain at it, e.g. `deals.propinvestuk.co.uk`.
3. On the main site, either link to it ("Send us a deal") or embed the form:

```html
<iframe src="https://deals.propinvestuk.co.uk/" style="width:100%;min-height:900px;border:0"></iframe>
```

If the main site is WordPress, Wix or Squarespace, an embed block with that iframe is all it needs.

## Tuning the scoring

`config/scoring-matrix.json` is the whole model. Per strategy (BTL, HMO, flip, BRR, development, commercial, rent-to-rent), it lists which metrics count and how much. Each financial metric has a curve of `[value, points]` pairs, so "9% gross yield = 90 points" is one line to change. The assumptions block sets LTV, interest rate, purchase costs, selling costs and running-cost percentages used in the working.

The qualitative metrics (location demand, condition risk, vendor motivation, exit liquidity, planning risk, sheet completeness, credibility of the numbers) come from Claude as 1-10 scores and are converted to points the same way.

Weights are renormalised over the metrics that actually have data, so a sheet with no rent figure isn't scored on yield. If less than 60% of the matrix is answerable, the score is pulled down so thin deal sheets can't score well.

This is the natural place to port the Property Predator scoring matrices: copy the weights and thresholds into this file, one strategy at a time.

## What's stored

`data/deals.json` holds every submission (submitter, notes, file list, extraction, scoring, your status and notes). Uploads sit in `data/uploads/<deal id>/`. Back up `DATA_DIR`.

## Supported attachments

PDF, JPG, PNG, WebP, GIF, and plain text / CSV / Markdown. Word and Excel files are stored but not read; the dashboard flags them so you can ask for a PDF.

## Roadmap

- Inbound email address: forward a WhatsApp export or an email to `deals@…` and have it land in the queue.
- Property Predator: port its matrices into the config, or expose `POST /api/deals` so Property Predator can push deals in and pull scores out.
- Investor matching: tag each investor's criteria (strategy, area, budget, yield floor) and surface which green deals fit whom.
- Postcode-level checks: Land Registry sold prices, EPC register and rental comps to test the sourcer's numbers automatically.

## Tests

```bash
npm test
```
