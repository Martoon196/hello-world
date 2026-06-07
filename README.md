# ProperInvest CRM

A custom-built CRM for **ProperInvest UK** — gathering property opportunities and
investor leads, scoring them, and moving them through pipelines. Inspired by the
GoHighLevel workflow, but built from scratch so you own 100% of it.

> **Status:** Module 1 of 6 is live — the **Investor Lead pipeline + scoring**.
> The architecture (data model, scoring engine, pipeline UI, capture API) is built
> to be reused by the Property Deal module and everything after it.

---

## What's built so far

| Area | What it does |
|------|--------------|
| **Investor dashboard** (`/`) | KPI cards (open leads, capital in pipeline, hot leads, capital invested), a pipeline-by-stage funnel, a lead-quality breakdown, and a recent-leads table. |
| **Investor pipeline** (`/pipeline`) | GoHighLevel-style **drag-along** kanban board across 8 funnel stages. Click any card for a full lead drawer. |
| **Lead drawer** | Full investor profile, a **transparent score breakdown** (every factor shown), one-click stage moves, and an **AI qualify + email draft** button. |
| **Lead capture** (`/capture`) | A public funnel form — the same `/api/capture` endpoint your live site & website chatbot will post into. Scores the lead instantly on submit. |
| **Scoring engine** | A transparent, weighted, config-driven model (capital, timeframe, return expectation, security flexibility, experience). |
| **AI layer** | Qualification summary + tailored follow-up email. Uses **Claude** when `ANTHROPIC_API_KEY` is set, with a solid built-in fallback so it always works. |

### The scoring model (tunable in `src/lib/scoring.ts`)

| Factor | Weight | Logic |
|--------|-------:|-------|
| Capital available | 35 | More capital = stronger signal (curve, £250k ceiling). |
| Deployment timeframe | 25 | Sooner = better. |
| Return expectation | 20 | **Lower/realistic = better** (easier margin). 20%+ is penalised. |
| Security flexibility | 12 | Flexible / second charge preferred. |
| Experience | 8 | Experienced investors score higher. |

Leads are banded **HOT** (≥70), **WARM** (≥45), or **COLD**.

---

## Running it locally

```bash
npm install
npm run setup     # creates the SQLite DB + seeds 12 example investor leads
npm run dev       # http://localhost:3000
```

Pages: `/` dashboard · `/pipeline` board · `/capture` public form.

### Optional: turn on the AI
Add your key to `.env` (copy from `.env.example`):
```
ANTHROPIC_API_KEY="sk-ant-..."
```
Without it, AI features fall back to the built-in engine — nothing breaks.

### Push a lead in from anywhere (website / chatbot / Property Predator)
```bash
curl -X POST http://localhost:3000/api/capture \
  -H 'content-type: application/json' \
  -d '{"name":"Jane Doe","email":"jane@x.com","fundsAvailable":"50000",
       "timeframe":"M3","targetReturnPct":"10","source":"CHATBOT"}'
```

---

## Tech & architecture

- **Next.js 15** (App Router) + **TypeScript** + **Tailwind** — one codebase, deploys to Vercel/Render.
- **Prisma + SQLite** locally; switch the `provider` in `prisma/schema.prisma` to `postgresql` for production.
- Pure, framework-agnostic business logic in `src/lib/` (`scoring.ts`, `stages.ts`, `ai.ts`) so it's easy to test and reuse.

```
src/
  app/
    page.tsx            Dashboard
    pipeline/           Drag-along kanban
    capture/            Public lead-capture funnel
    api/
      leads/            List / create / update (PATCH moves stage + re-scores)
      capture/          Public intake for site + chatbot
      ai/qualify/       AI summary + email draft
  components/           Sidebar, PipelineBoard, LeadDrawer
  lib/                  scoring · stages · leadService · ai · format · prisma
prisma/                 schema + seed
```

---

## Roadmap (the full vision)

1. ✅ **Investor leads** — pipeline, scoring, capture, AI *(this module)*
2. **Property deals** — ingest from Property Predator; score on profit / GDV / availability / listing status; vendor & owner stages; lease options, PLOs, payment agreements.
3. **Email built-in** — send & sequence from inside the CRM (Gmail is connected), tied to stages.
4. **Website chatbot** — qualifies & captures investor leads on properinvestuk.co.uk straight into `/api/capture`.
5. **Social posting + scoring** — schedule posts and rate engagement.
6. **Deal ↔ investor matching** — AI suggests which investors fit which deals.

Built for Martin · ProperInvest UK.
