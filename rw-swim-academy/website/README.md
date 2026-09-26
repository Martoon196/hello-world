# RW Swim Academy — website, booking & payments

A fast static website with a real booking flow: parents pick a lesson, pick a time from Ruby's live availability, pay by card (Stripe), and every lesson lands in Ruby's Google Calendar and the parent's inbox automatically. Free tasters skip payment and go straight to the calendar.

**Nothing here needs a developer to run day to day.** Prices live in one JSON file, Ruby's hours in another, and the whole thing deploys for free on Netlify.

## What's in the box

| Path | What it is |
|------|------------|
| `src/pages/*.html` | The pages (home, lessons, about, how it works, FAQ, contact, book, legal, thank-you pages). Edit these. |
| `src/pages/blog/*.md` | Blog posts in Markdown with a small header. Drop a new `.md` in, rebuild, it's live with the index and sitemap updated. |
| `src/partials/` | Shared header, footer, `<head>` and mobile sticky CTA. Change the menu once, it changes everywhere. |
| `public/` | The built site (what Netlify serves). Assets, logo, CSS, JS and data live here. |
| `public/data/programmes.json` | **Every lesson type and price.** Prices are in pence (`19500` = £195). The booking page and Stripe both read from this file, so a price change here is the only change needed. |
| `public/data/schedule.json` | **Ruby's teaching hours**, taster windows, programme start dates and holiday intensive weeks. |
| `public/assets/img/` | Logo SVGs and photo placeholders. Replace `ph-*.svg` by adding real photos with the names listed below. |
| `netlify/functions/` | Serverless code: live availability, free taster booking, Stripe Checkout, Stripe webhook (creates calendar events + emails after payment). |
| `public/tools/calculator.html` | Internal session-profit calculator (not linked from the menu). |
| `scripts/build.js` | Assembles pages from partials and renders blog Markdown. `npm run build`. |

## Run it locally

```bash
cd rw-swim-academy/website
npm install
npm run dev          # builds, then serves http://localhost:8080
```

To run the booking functions locally too, install the Netlify CLI (`npm i -g netlify-cli`), copy `.env.example` to `.env`, fill in keys, then `netlify dev` (site at http://localhost:8888).

Without any keys the site runs in **preview mode**: the booking page shows Ruby's standard hours, the "Pay" button explains the system isn't connected yet and gives the email address. So the site can go live on day one and payments can be switched on later.

## Go live in an afternoon

### 1. Domain and email (30 min)
1. Buy `rwswimacademy.co.uk` (check availability first; `rwswim.co.uk` / `rwswimacademy.com` as fallbacks).
2. Set up Google Workspace (about £5/user/month) for `hello@rwswimacademy.co.uk`. This also gives you the Google Calendar used below.

### 2. Deploy on Netlify (20 min, free)
1. Create an account at netlify.com, "Add new site" → "Import an existing project" → pick this GitHub repo.
2. Base directory: `rw-swim-academy/website`. Build command and publish folder are read from `netlify.toml`.
3. Deploy. You get a `something.netlify.app` URL immediately; add the custom domain under Domain management and follow the DNS steps.
4. Site settings → Forms: enable form detection. The **contact** and **waiting-list** forms then appear in the Netlify dashboard. Under Forms → Notifications add an email notification to `hello@rwswimacademy.co.uk` so every enquiry lands in the inbox.
5. Site settings → Environment variables: add `SITE_URL` (your live URL) and `ACADEMY_EMAIL`.

### 3. Stripe payments (30 min)
1. Create a Stripe account (stripe.com), complete business verification (sole trader or Ltd details, bank account).
2. Developers → API keys → copy the **Secret key** into Netlify env var `STRIPE_SECRET_KEY`. Use the test key first (`sk_test_…`), then swap for live.
3. Developers → Webhooks → Add endpoint: `https://YOUR-DOMAIN/api/stripe-webhook`, event `checkout.session.completed`. Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
4. Products → Coupons → create **FOUNDER10** (10% off, forever, limit 30 redemptions) and tick "customer-facing promotion code". Founding members type it on the Stripe payment page. Add others as you like (e.g. `SIBLING10`, `REFER1`).
5. Test with card `4242 4242 4242 4242` while on test keys. You should see the booking in Stripe, events in the calendar and two emails (parent + academy).

### 4. Google Calendar (30 min)
This lets the site read Ruby's busy times and write lessons into her calendar, with the parent invited.
1. In Google Calendar create a calendar called **RW Swim Academy Lessons**. Ruby puts her own training, galas and holidays in the same calendar (or in another calendar she shares to it), so those times never show as available.
2. Go to console.cloud.google.com → create a project "rw-swim-academy" → APIs & Services → enable **Google Calendar API**.
3. IAM & Admin → Service accounts → Create → then Keys → Add key → JSON. Download it.
4. Back in Google Calendar, open the lessons calendar's settings → "Share with specific people" → add the service account's email (ends `iam.gserviceaccount.com`) with **Make changes to events**.
5. Netlify env vars: `GOOGLE_CALENDAR_ID` (from calendar settings → "Integrate calendar") and `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the whole JSON file contents on one line).

### 5. Email confirmations (15 min)
1. Create a free account at resend.com, verify the domain (three DNS records), create an API key → `RESEND_API_KEY`.
2. Set `EMAIL_FROM` to `RW Swim Academy <hello@rwswimacademy.co.uk>`.
(Any transactional email provider works; `netlify/functions/lib/email.js` is 40 lines and easy to swap.)

### 6. Photos and final checks
Add real photos with these exact names in `public/assets/img/` and the placeholders disappear automatically:
`ruby-hero.jpg` (portrait, 4:5), `ruby-racing.jpg` (3:2), `ruby-poolside.jpg` (3:2), `lesson-1.jpg`, `lesson-2.jpg`, `lesson-3.jpg` (3:2, only with written consent), `og-image.jpg` (1200×630, used when the site is shared on WhatsApp/Facebook).

Then search the site for `[CONFIRM]` and fix each one (qualification name, safeguarding lead, legal entity in the privacy notice), have the terms checked, and update the social links in `src/partials/footer.html` once handles are claimed.

## Day-to-day changes

- **Change a price or add a lesson type:** edit `public/data/programmes.json`. Prices in pence. Rebuild/redeploy (Netlify does this on every git push).
- **Change Ruby's hours:** edit `windows` / `tasterWindows` in `public/data/schedule.json`. One-off blockouts (galas, holidays) just go in the Google Calendar as busy events.
- **Add a programme group or holiday week:** add to `programmeCohorts` / `intensiveWeeks` in `schedule.json`.
- **Add a blog post:** create `src/pages/blog/my-post.md` with the header format used by the existing posts, run `npm run build` (or just push; Netlify builds).
- **Edit text on a page:** edit the file in `src/pages/`, not `public/` (public is overwritten on build).

## How the booking flow works (for whoever maintains it)

```
book.html ──► /api/availability?product=ID ──► schedule.json windows − Google Calendar busy ──► slots
        └─► details form
        └─► paid:  POST /api/create-checkout ──► Stripe Checkout ──► webhook /api/stripe-webhook
                                                                     └─► calendar events (one per lesson, parent invited)
                                                                     └─► confirmation email to parent + notification to academy
        └─► free:  POST /api/book-taster ──► re-checks slot ──► calendar event + emails
```
- Prices are always taken from `programmes.json` on the server; the client cannot change them.
- Block bookings check that *every* weekly occurrence is free before offering the slot.
- Booking details ride in Stripe session metadata, so nothing is stored until payment succeeds. Stripe retries the webhook if the calendar or email step fails.
- Time zone is Europe/London throughout, including across the clock changes.

## Testing done
- `scripts` logic tested with Node: slot generation, 24 h lead time, DST-safe weekly occurrences (Oct/Nov 2026), taster windows, busy-slot removal, intensive Mon–Fri, input validation, all four functions in preview mode.
- Every page screenshotted at desktop and mobile widths with Playwright; the full booking wizard walked through; no horizontal overflow at 390 px.
