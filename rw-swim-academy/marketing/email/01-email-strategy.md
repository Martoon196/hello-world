# RW Swim Academy: Email Strategy

Source of truth: `/rw-swim-academy/BRIEF.md`. **[CONFIRM]** items need checking by Chris or Ruby before go-live.

**Working assumptions**
- Chris owns email. Ruby writes or approves anything in her voice. **[ASSUMPTION]**
- Booking runs through a simple booking tool that can export or sync contacts (e.g. Acuity, SimplyBook.me, or a Google Form plus Stripe link at launch). **[ASSUMPTION; the business plan decides this]**
- Sender: Ruby Waller, RW Swim Academy `<hello@rwswimacademy.co.uk>`. Reply-to goes to a shared inbox Chris monitors. **[CONFIRM domain]**
- Postal address for the footer is the registered company address once the Ltd is formed. **[CONFIRM; required by PECR and the CAN-SPAM-style "identify the sender" rule in UK law]**

---

## 1. What email is for

Social gets attention. Email closes and keeps. For RW, email does four jobs, in order of money:

1. **Convert the waiting list into founding members** (Nov 2026 to Jan 2027).
2. **Convert tasters into blocks** (from Jan 2027; the single highest-value automation).
3. **Keep active parents renewing** at week 5 or 6 of every block, same slot, term after term.
4. **Bring lapsed parents back** and turn happy ones into reviews and referrals.

Email is not a newsletter for its own sake. Nobody in Sevenoaks needs a monthly "swim news" round-up. Every send has one job and one link.

---

## 2. List building

**Sources, in order of expected volume**
| Source | Mechanism | Where it lands |
|---|---|---|
| Founding-member waiting list | Form at `/founding`: first name, email, child's first name, child's age, postcode area, mobile (optional, for WhatsApp Channel) | Segment: Waiting list |
| Free taster booking | Booking form, tick box "Send me Ruby's lesson updates" (unticked by default) | Segment: Taster booked |
| Block or programme purchase | Booking form, same tick box | Segment: Active parent |
| Facebook group replies and DMs | Ruby sends the `/founding` or `/taster` link; never adds people manually without consent | Whichever they choose |
| Flyer and school outreach | QR code to `/founding` (pre-launch) or `/taster` (post-launch) | As above |
| Google Business Profile | "Book" button to `/taster` | Taster booked |

**Minimum fields:** first name, email, child's first name, child's age. Everything else is optional. Child's name and age drive most of the personalisation; without them the emails are generic.

**Do not:** buy lists, scrape school directories, or add parents from WhatsApp groups without an explicit opt-in. One complaint to the ICO is a bad week for a new business.

**Target:** 60 waiting-list contacts by 20 Dec 2026; 150 total contacts by end Feb 2027.

---

## 3. Tool recommendation

**Recommended: MailerLite (free plan).**

Why, for RW specifically:
- Free up to 1,000 subscribers and 12,000 emails a month. RW will not approach that in Stage 1.
- Automations on the free plan (MailerLite's free tier includes automation workflows; Mailchimp's free tier restricts multi-step automation). **[CONFIRM current plan limits at sign-up; they change]**
- Simple drag-and-drop editor, clean templates, easy custom fields for `{{child_name}}` and `{{child_age}}`.
- Built-in forms and landing pages, so `/founding` can be a MailerLite page embedded on the site if the website is not ready.
- Groups and segments are straightforward for a non-marketer.
- GDPR features (double opt-in, consent checkbox, unsubscribe link) are on by default.

**Alternatives**
- **Brevo (free plan):** unlimited contacts but a 300 emails per day cap, which is fine for RW. Slightly clunkier editor. Good if WhatsApp or SMS integration matters later (Brevo has both). Solid second choice.
- **Mailchimp (free plan):** 500 contacts, limited automations, Mailchimp branding on emails. Not recommended for RW; the automation limits get in the way of the taster sequence.

**Token format used in this pack:** `{{first_name}}`, `{{child_name}}`, `{{child_age}}`, `{{programme}}`, `{{slot_day}}`, `{{slot_time}}`, `{{venue}}`, `{{booking_link}}`, `{{taster_date}}`. Map these to the chosen tool's field names.

---

## 4. Segments

| Segment | Who | Entry | Exit |
|---|---|---|---|
| **Waiting list** | Joined `/founding` before launch | Form submission | Books a taster or a block, or 31 Jan 2027 (moved to "Prospect") |
| **Taster booked** | Booked a free taster | Booking confirmation | Attends taster (moves to "Taster attended"), no-shows (moves to "Prospect" after one nudge) |
| **Taster attended** | Had a taster, not yet booked | Ruby marks attended and sends assessment | Books a block (Active) or 14 days pass (Prospect) |
| **Active parent** | Has a current block or programme | Purchase | Block ends without renewal (moves to "Lapsed" after 14 days) |
| **Lapsed** | No booking for 60 days after last lesson | Automatic | Rebooks (Active) or unsubscribes |
| **Prospect** | Everyone else who opted in | Various | Books a taster |
| **Club-track tag** | Child aged 9 to 14, or booked a Stroke Clinic | Tag on age or purchase | n/a; used to filter clinic announcements |
| **Founding member tag** | First 30 swimmers to book a block | Manual tag by Chris | Never removed |

Keep it to these. More segments than Chris can remember is worse than fewer.

---

## 5. Automations map

```
/founding form ──► Waiting List Welcome (5 emails over 14 days)
                        │
                        └─► "Doors open" broadcast (3 Jan) ─► books taster? ──┐
                                                                                ▼
/taster booking ──► Taster Sequence
                    ├─ T0  Confirmation + what to bring (immediate)
                    ├─ T1  24h reminder
                    ├─ T2  Same-day follow-up: assessment + recommended block (manual trigger by Ruby)
                    ├─ T3  3-day nudge (if no booking)
                    └─ T4  7-day last call, founding offer expiry (if no booking)
                              │
                              ▼
block/programme purchase ──► Active Parent flow
                    ├─ A0  Block confirmation (immediate)
                    ├─ A4  Week-4 progress note (manual send by Ruby, template)
                    ├─ A6  Week-6 renewal "Ruby's held your slot" (auto, day 38)
                    ├─ A8  Week-8 progress report + certificate (manual, template)
                    ├─ A8+3  Google review request (auto, 3 days after A8)
                    └─ A8+14 Referral email (auto, 14 days after A8, if renewed)

No renewal 14 days after block ends ──► tag Lapsed
Lapsed + 60 days ──► Win-back 1 ─► (7 days) Win-back 2 ─► stop

First lesson anniversary ──► "One year swimming with Ruby" (auto, date field)

Ad hoc broadcasts (segment-filtered): holiday intensive, term dates, pool closure, late-cancellation reminder, stroke clinic (Club-track tag only)
```

Manual triggers: Ruby's week-4, week-8 and post-taster emails are personal and must be written per child. The templates in `03` and `04` are there to make that a five-minute job, not to remove the human.

---

## 6. Sending cadence

| Segment | Cadence | Notes |
|---|---|---|
| Waiting list (Nov to Dec) | Automation: 5 emails in 14 days, then 1 broadcast a fortnight | Do not exceed. These are people who have not bought anything yet. |
| Taster booked / attended | Automation only | No broadcasts to this segment until they become Active or Prospect. Avoid stacking a promo on top of a follow-up. |
| Active parents | Transactional + 2 personal notes per block, plus a maximum of 2 broadcasts a month | Term dates and holiday intensives are the usual broadcasts. |
| Lapsed | 2 emails, 7 days apart, then nothing until the anniversary | No monthly "we miss you". |
| Prospects | 1 broadcast a fortnight max | Tips-led, taster CTA. Pull the best-performing blog post and Reel. |

**Send times:** Tuesday or Thursday, 8.00 to 8.30pm for parents (post-bedtime scroll). Transactional emails go immediately. Sunday 7pm works for "slots released" broadcasts. Test and adjust after eight weeks.

**Subject line style:** lower-case-first-word is fine, no exclamation marks, no emoji, no "RE:" tricks. Under 45 characters where possible.

---

## 7. Compliance (UK GDPR and PECR)

- **Lawful basis:** consent for marketing emails (waiting list, prospects, lapsed); legitimate interests / contract for transactional emails (confirmations, reminders, cancellations, progress notes). Keep the two separate: a parent who unsubscribes from marketing must still get their booking confirmation.
- **Consent wording** on every form (unticked box): "Send me Ruby's lesson tips, slot releases and offers by email. You can unsubscribe any time." Log date, time and form source. MailerLite does this automatically.
- **Children's data:** the parent is the subscriber. Store child's first name and age only. No surnames, no DOB, no school, no medical notes in the email tool. Medical notes live in the booking system with restricted access. **[CONFIRM booking tool's data handling]**
- **Unsubscribe:** one-click link in every marketing email, honoured within 24 hours (tool does it instantly). Transactional emails carry a "manage preferences" link but do not need unsubscribe.
- **Sender identity:** every email shows "RW Swim Academy" and a postal address in the footer. **[CONFIRM registered address]**
- **Retention:** delete Prospects who have not opened anything in 18 months. Delete Lapsed after 24 months unless they re-engage. Note this in the privacy policy.
- **Privacy notice:** link in every footer to rwswimacademy.co.uk/privacy. Must mention MailerLite (or chosen tool) as a processor.
- **ICO registration:** as a business processing personal data, RW must pay the ICO data protection fee (currently the lowest tier for small businesses). **[CONFIRM current fee and register when the Ltd is formed]**
- **Testimonials and reviews:** written permission before quoting a parent in an email. First name and child's first name only, and only if they say yes to both.
- **Photos in email:** same consent rules as social. Default to no children's faces in email.

**Footer block (every email)**
> RW Swim Academy · Sevenoaks, Kent · hello@rwswimacademy.co.uk
> [Registered address, CONFIRM]
> You're getting this because you {{signup_reason}}. Unsubscribe | Update preferences | Privacy

---

## 8. Metrics that matter

| Metric | Benchmark to beat | Why |
|---|---|---|
| Waiting list welcome open rate (email 1) | 60% | They just signed up. Below this, the sender name or deliverability is wrong. |
| Waiting list to taster booking | 40% of list books a taster by end Jan | The list is the funnel. |
| Taster to block (within 7 days of T2) | 60% | The number the business lives on. |
| Week-6 renewal rate | 70% | Retention is cheaper than acquisition. |
| Review request to review | 30% | 10 Google reviews by end Feb is the goal. |
| Unsubscribe rate per send | under 0.5% | Above 1% on any send means the send was wrong for that segment. |

Review monthly with the social KPIs.
