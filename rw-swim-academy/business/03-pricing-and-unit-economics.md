# 03. Pricing and Unit Economics: RW Swim Academy

**For:** Chris (the numbers) and Ruby (what they mean for her week)
**Prepared:** 26 September 2026
**Rule:** Prices are exactly as set in `BRIEF.md`. This file works out what those prices earn under stated assumptions. Anything marked **[CONFIRM]** is an assumption that must be replaced with a real quote before it is relied on. The interactive version of this model is `website/tools/calculator.html` (see section 11).

---

## 1. Assumptions (change these first)

| Item | Base case | Range | Source / note |
|---|---|---|---|
| Lane hire, public or school pool, per lane per hour | **£35** | £25 to £45 **[CONFIRM: get written quotes from each venue in `05` week 1]** | Kent public and school pools. Some venues charge per lane, some per "area" for groups. Off-peak and block bookings are usually cheaper |
| Pool time for a 30-minute lesson | 30 min of lane | | Assumes back-to-back lessons in a continuously hired lane. If the venue bills in whole hours, a lone 30-minute lesson costs a full hour |
| Pool time for a 45-minute group of 4 | 45 min of one lane or shallow-end area at the same rate | **[CONFIRM: a Splash group may need a shallow area, sometimes priced differently]** | |
| Stripe fees (UK cards) | 1.5% + 20p per transaction | | Stripe standard UK pricing **[CONFIRM current rate at sign-up]**. Bank transfer is free but manual |
| Consumables and admin per session (printing, certificates, kit wear, messaging) | £0.50 per 1:1 or 2:1 session; £1.50 per group session; £1.00 per clinic (video storage, drill plan) | | Small, but real |
| Ruby's time | Not deducted from "contribution": she is the owner, and contribution is what pays her | | Section 4 shows what each format pays her per hour so she can compare with employed teaching |
| Insurance (public liability and professional indemnity) | £250 per year | £150 to £300 **[CONFIRM: quote from Swim England members' scheme or STA]** | |
| Governing body membership (Swim England or STA) | £60 per year | **[CONFIRM]** | |
| Safeguarding course | £35 | Every 3 years **[CONFIRM]** | |
| Rescue award (NRASTC) | £200 | Every 2 years **[CONFIRM]** | |
| First aid | £100 | Every 3 years **[CONFIRM]** | |
| Enhanced DBS plus Update Service | £38 plus admin fee, then £13 per year | **[CONFIRM current DBS fees]** | |
| ICO data protection fee | £52 per year | **[CONFIRM via ICO self-assessment; some very small businesses are exempt]** | |
| Domain and email | £12 plus about £80 per year | | .co.uk domain; one business mailbox |
| Booking and payments software | £0 to £150 per year | | Stripe links and a form at launch; a booking platform later |
| Bookkeeping software | £0 to £200 per year | | Some business bank accounts include it free |
| Marketing | £600 per year | £300 to £600 in the first 90 days | Flyers, caps, small paid social |
| Kit (floats, kickboards, noodles, waterproof lesson cards, phone waterproof case, tripod) | £300 one-off, £100 per year after | | |
| Founding member caps | 30 x £6 = £180 one-off **[CONFIRM supplier]** | | |
| Paid teaching weeks per year | 40 | 38 term weeks plus about 4 weeks of holiday intensives, less Ruby's competition weeks | Monthly figures below = weekly x 40 / 12 |

**Fixed overheads (sole trader):** about £1,600 per year recurring, plus about £800 of one-offs in year 1. Call it **£160 per month** recurring, **£200 per month** in year 1.

**If trading as a Ltd company, add:** £50 incorporation, £34 per year confirmation statement, and an accountant at £600 to £1,200 per year **[CONFIRM]**. Call it **£250 to £260 per month** all in.

---

## 2. Session-level P&L, per format (base case: £35 per lane hour)

"Contribution" = what is left after lane hire, card fees and consumables. It is before Ruby's time and before fixed overheads.

### 2a. Private 1:1, 30 minutes

| | Single (£35) | Block of 6 (£195, £32.50 each) | Founding Member block (£175.50, £29.25 each) |
|---|---|---|---|
| Revenue per lesson | £35.00 | £32.50 | £29.25 |
| Lane hire (30 min) | £17.50 | £17.50 | £17.50 |
| Stripe | £0.73 | £0.52 | £0.47 |
| Consumables and admin | £0.50 | £0.50 | £0.50 |
| **Contribution per lesson** | **£16.27** | **£13.98** | **£10.78** |
| **Contribution per hour of pool time** | £32.54 | £27.96 | £21.56 |

Block of 12 (£372, £31 each): contribution about £12.50 per lesson, £25 per hour.

### 2b. Semi-Private 2:1, 30 minutes

| | Per lesson (£50) | Block of 6 for the pair (£270, £45 each) |
|---|---|---|
| Revenue per lesson | £50.00 | £45.00 |
| Lane hire | £17.50 | £17.50 |
| Stripe | £0.95 | £0.71 |
| Consumables and admin | £0.50 | £0.50 |
| **Contribution per lesson** | **£31.05** | **£26.29** |
| **Contribution per hour** | £62.10 | £52.58 |

### 2c. RW Progress Programme, 45 minutes, group of up to 4 (£160 per swimmer for 8 weeks = £20 per swimmer per session)

| Swimmers in the group | 4 | 3 | 2 |
|---|---|---|---|
| Revenue per session | £80.00 | £60.00 | £40.00 |
| Lane or area hire (45 min) | £26.25 | £26.25 | £26.25 |
| Stripe | £1.30 | £0.98 | £0.65 |
| Consumables, certificates, reports | £1.50 | £1.50 | £1.50 |
| **Contribution per session** | **£50.95** | **£31.27** | **£11.60** |
| **Contribution per hour** | £67.93 | £41.70 | £15.47 |

**Rule that falls out of this:** a Programme group runs at 3 or more, never at 2. At 2 swimmers it earns less per hour than a 1:1.

### 2d. Stroke Clinic, 60 minutes 1:1 (£55; 3-pack £150)

| | Single (£55) | In a 3-pack (£50 each) |
|---|---|---|
| Revenue | £55.00 | £50.00 |
| Lane hire (60 min) | £35.00 | £35.00 |
| Stripe | £1.03 | £0.82 |
| Video storage, drill plan | £1.00 | £1.00 |
| **Contribution** | **£17.97** | **£13.18** |
| Ruby's time (60 min in water plus about 30 min analysis and drill plan) | 1.5 hrs | 1.5 hrs |
| **Contribution per hour of Ruby's time** | **£11.98** | **£8.79** |

**Honest finding:** at £35 per lane hour the Stroke Clinic is the weakest earner per hour of Ruby's time, despite the brief calling it high-margin. It is high-margin only where the pool costs little or nothing (a client's own pool, a cheaper off-peak school pool at £25 or less, or a venue that lets Ruby use a lane she has already hired for a Programme). It is still worth running at launch for credibility and the club-track audience. See `02` for the 45-minute-plus-video-review option, which lifts contribution to about £27 at the same £55 price.

### 2e. Holiday Intensive (5 consecutive days)

| | 1:1, 5 x 30 min (£160, £32 per day) | Group of 4, 5 x 45 min (£95 per swimmer, £76 per session) |
|---|---|---|
| Revenue per session | £32.00 | £76.00 |
| Lane hire | £17.50 | £26.25 |
| Stripe | £0.52 | £1.30 |
| Consumables and report | £0.50 | £1.50 |
| **Contribution per session** | **£13.48** | **£46.95** |
| **Contribution per 5-day intensive** | £67.40 | £234.75 |
| **Contribution per hour** | £26.96 | £62.60 |

### 2f. Free Taster (20 min in water plus 5 min chat; booked as a 30-minute slot)

Cost per taster: about £17.50 of lane time (base case). 6 per week = £105 per week. If 50% convert to a block worth £195 (contribution about £84 over the block), the tasters more than pay for themselves within the first block: 6 tasters cost £105 and produce 3 blocks worth about £252 of contribution. **Cost per acquired swimmer: about £35.** Track this number; it is the one that tells you whether the taster is working.

### Summary: contribution per hour of pool time, by format (base case)

| Format | Revenue per hour | Contribution per hour | Rank |
|---|---|---|---|
| Programme group of 4 | £106.67 | £67.93 | 1 |
| Group Intensive (4) | £101.33 | £62.60 | 2 |
| 2:1 block | £90.00 | £52.58 | 3 |
| Programme group of 3 | £80.00 | £41.70 | 4 |
| 1:1 single | £70.00 | £32.54 | 5 |
| 1:1 block of 6 | £65.00 | £27.96 | 6 |
| 1:1 Intensive | £64.00 | £26.96 | 7 |
| 1:1 Founding block | £58.50 | £21.56 | 8 |
| Stroke Clinic (per hour of Ruby's time) | £55.00 | £11.98 | 9 |

**What this says:** 1:1 is the product parents ask for first and the best trust-builder, but groups of 3 to 4 and pairs are where the money is. The strategy in `01` (1:1 to earn trust, then move swimmers into pairs and Programmes) is also the profitable path. Do not try to run the business on 1:1 alone at £35 per lane hour.

---

## 3. Break-even

**Fixed overheads:** about £160 per month (sole trader, recurring).

| Format | Contribution per session | Sessions per month to cover overheads | Per week (over 3.33 weeks) |
|---|---|---|---|
| 1:1 block | £13.98 | 12 | 3.5 |
| 2:1 block | £26.29 | 7 | 2 |
| Programme group of 4 | £50.95 | 4 | 1.2 |

Break-even on overheads is trivially low: roughly 2 hours of lessons a week. **The real break-even is Ruby's time.** If Ruby could earn £20 to £25 per hour as an employed Level 2 teacher at a leisure centre **[CONFIRM local rates]**, then any format that contributes less than about £25 per hour of her time is not worth doing in a hired lane, and that is 1:1 at lane rates above about £40 per hour, Founding-rate 1:1 above about £35, and Stroke Clinics at any public-pool rate. This is why the venue negotiation in `05` week 1 matters more than any marketing decision.

**Break-even occupancy of a hired lane hour:** if the lane is booked for an hour and only one 30-minute 1:1 at block rate is sold, contribution is £32.50 less £35 lane less £1 fees = a loss of £3.50. Two 1:1s in the hour: £27.96. So a hired hour needs both halves filled, or one pair or group, to be worth hiring. **Practical rule: never hire a lane hour without two bookings in it; use the waiting list and tasters to fill the second half.**

---

## 4. What each format pays Ruby per hour of her time (base case)

| Format | Pool hour contribution | Extra unpaid time (notes, reports, messages) | Contribution per hour of Ruby's total time |
|---|---|---|---|
| 1:1 block | £27.96 | About 10 min per hour | About £24 |
| 2:1 block | £52.58 | About 10 min | About £45 |
| Programme group of 4 | £67.93 | About 15 min (4 reports) | About £54 |
| Stroke Clinic | £17.97 | 30 min analysis | About £12 |
| Group Intensive | £62.60 | About 10 min | About £54 |

---

## 5. Scenarios: 10, 20 and 30 coaching hours a week

**Assumed mix of sold hours (base):** 50% 1:1 blocks, 20% 2:1 blocks, 25% Programme groups (average 4), 5% Stroke Clinics. That gives a **blended revenue of about £80 per coaching hour and blended contribution of about £42 per coaching hour** at £35 lane hire.

**Group-heavy mix (Stage 2 target):** 25% 1:1, 15% 2:1, 55% groups, 5% clinics gives about £91 revenue and **£53 contribution per hour**.

| Coaching hours per week | 10 | 20 | 30 |
|---|---|---|---|
| Who can deliver it | Ruby alone, comfortably | Ruby at her full term-time availability, no slack for training or competitions; realistic only in holidays or with a coach doing 5 to 8 hrs | Ruby (12 to 15) plus one coach (15 to 18). Not Ruby alone |
| Revenue per week | £800 | £1,600 | £2,400 |
| Revenue per month (40 weeks / 12) | £2,660 | £5,330 | £8,000 |
| Revenue per year | £32,000 | £64,000 | £96,000 (see VAT note, section 8) |
| Contribution per week (base mix) | £424 | £848 | £1,271 |
| Contribution per month | £1,410 | £2,830 | £4,240 |
| Less fixed overheads per month | £160 | £160 | £250 (Ltd, accountant) |
| Less coach pay (30-hr case: 16 hrs/week at £25) | 0 | 0 | £1,330 |
| **Profit before tax per month (Ruby's take-home before tax, sole trader)** | **£1,250** | **£2,670** | **£2,660** |
| Profit before tax per year | £15,000 | £32,000 | £32,000 |
| Approx. income tax plus Class 4 NI (sole trader, 2026/27 rates, personal allowance £12,570) **[CONFIRM with accountant]** | £630 | £5,050 | £5,050 |
| **Net per year** | **£14,400** | **£26,950** | **£26,950** |
| **Net per month** | **£1,200** | **£2,250** | **£2,250** |

**Read this carefully:** at base mix, adding a coach at 30 hours barely moves Ruby's take-home, because a coach paid £25 per hour eats most of the £42 per hour contribution of a 1:1-heavy mix. Coaches only pay when they teach groups and pairs (£53 or more per hour) or when lane rates are lower. This is the numerical reason behind "Ruby first, then coaches" and behind moving the mix towards Programmes before hiring anyone.

The same 30-hour scenario at the group-heavy mix: contribution about £1,590 per week, £5,300 per month, less £250 overheads and £1,330 coach pay = about **£3,700 per month profit before tax**.

---

## 6. What it takes to reach £2k, £4k and £6k a month (profit before tax)

| Target | Contribution needed per month (target plus overheads) | Hours per week at base mix (£42/hr) | Hours per week at group-heavy mix (£53/hr) | Who delivers it | Stage |
|---|---|---|---|---|---|
| £2,000 | £2,160 | 15.3 | 12.2 | Ruby alone | Stage 1 to 2. Reachable by spring 2027 with about 40 to 45 active swimmers |
| £4,000 | £4,160 | 29.4 | 23.5 | Ruby at 15 hrs plus one coach at 10 to 15 hrs on groups; or Ruby alone in a summer of intensives | Stage 2. Realistic by late 2027 with 70 to 90 active swimmers, and only if the mix is group-heavy |
| £6,000 | £6,250 (Ltd overheads) | Not achievable at base mix with coaches paid £25/hr | Ruby 15 hrs plus two coaches at about 15 hrs each, all on groups and pairs, and lane hire at £30 or less or a price review | Stage 3. 150 plus swimmers, 2 venues |

The levers, in order of power: (1) lane-hire rate, (2) proportion of hours that are pairs and groups, (3) occupancy of hired hours (no empty half-hours), (4) price. Price is last on purpose: do not raise prices before the first 30 are in and renewing.

---

## 7. Sensitivity: lane hire versus price, 1:1 30-minute lesson (contribution per lesson)

Rows are the lesson price (block rate). Columns are lane hire per hour. Base case in bold. Prices other than £32.50 are shown for information only; the brief's prices stand.

| Price per lesson | £20/hr | £25/hr | £30/hr | **£35/hr** | £40/hr | £45/hr |
|---|---|---|---|---|---|---|
| £30.00 | £19.02 | £16.52 | £14.02 | £11.52 | £9.02 | £6.52 |
| **£32.50 (block of 6)** | £21.48 | £18.98 | £16.48 | **£13.98** | £11.48 | £8.98 |
| £35.00 (single) | £23.94 | £21.44 | £18.94 | £16.44 | £13.94 | £11.44 |
| £38.00 | £26.90 | £24.40 | £21.90 | £19.40 | £16.90 | £14.40 |
| £40.00 | £28.87 | £26.37 | £23.87 | £21.37 | £18.87 | £16.37 |

**How to read it:** every £5 per hour on lane hire costs £2.50 per 30-minute lesson, which is the same as a £2.50 price change. Negotiating a lane from £35 to £30 is worth as much as a 7.7% price rise, and parents never see it. Getting the hire rate right is the highest-value hour of Chris's month.

**The same sensitivity for a group of 4 (45 min, £20 per swimmer):** contribution per session runs from £62 at £20/hr to £43 at £45/hr. Groups are far less sensitive to lane cost, which is another reason to grow them.

---

## 8. Tax and structure notes (plain English, not advice: **confirm with an accountant**)

| Topic | What applies | What to do |
|---|---|---|
| Sole trader | Ruby registers for Self Assessment with HMRC by 5 October following the end of the tax year in which she starts trading (so by 5 October 2027 for a start in 2026/27) **[CONFIRM]**. Profit is taxed as her income: personal allowance £12,570, then 20% income tax up to £50,270, plus Class 4 National Insurance at 6% on profits between £12,570 and £50,270 **[CONFIRM current rates]**. Class 2 NI is now treated as paid for most small traders | Simplest option for year 1. Keep every receipt. A separate business bank account from day one, even as a sole trader |
| Limited company | £50 to incorporate at Companies House; corporation tax at the small profits rate (19% up to £50,000 of profit **[CONFIRM]**); Ruby is paid by salary and dividends; annual accounts and a confirmation statement; an accountant is realistic at £600 to £1,200 per year | Better for liability (a business teaching children), for having Chris or others as shareholders, for adding coaches and for any future investor. Costs about £100 per month more than sole trader in admin and fees |
| **VAT (important)** | Registration is compulsory when taxable turnover in any rolling 12 months exceeds **£90,000** **[CONFIRM current threshold]**. However, HMRC treats private tuition in a subject ordinarily taught in schools, given by an individual teacher acting independently (a sole trader or partner, not a company and not through employees), as **exempt** from VAT. Swimming is on the National Curriculum. This means Ruby teaching as a sole trader may be able to exceed £90k without charging VAT, whereas the same lessons through a Ltd company, or delivered by employed coaches, would be standard-rated at 20% once over the threshold **[CONFIRM with an accountant against HMRC VAT Notice 701/30, "Education and vocational training"; this is a genuine structural decision and worth a paid hour of advice]** | Discuss before choosing the structure. At Stage 1 turnover it does not bite; at Stage 2 to 3 it can be worth 20% of revenue |
| Ruby's age | At 18 Ruby is an adult and can be a sole trader, a company director and a shareholder without restriction. If she is, or becomes, a student, her self-employed income is still taxable in the normal way; student finance assessments are usually based on household income rather than a student's own earnings **[CONFIRM for her circumstances]** | No barrier. Make sure the business is in her name, not Chris's, so the track record is hers |
| Chris helping | Unpaid help is fine. If the business pays Chris, that is either a salary through PAYE (Ltd) or, as a sole trader, a genuine wage for real work, recorded properly | Decide and record it; do not leave it vague |
| Records | Making Tax Digital for Income Tax applies to sole traders with income over £50,000 from April 2026 and over £30,000 from April 2027 **[CONFIRM]**, which means digital records and quarterly updates | Use bookkeeping software from day one so this is never a scramble |
| Trading allowance | The first £1,000 of trading income a year is tax-free without registering, but the business will pass that in its first month | Ignore; register properly |
| Expenses | Lane hire, insurance, memberships, training, kit, phone share, mileage to venues (45p per mile **[CONFIRM]**), software, marketing, accountant | Log mileage between venues from week 1; it adds up |

---

## 9. Worked example: the first term with 30 Founding Members

Assumes the mix in `01` section 3.2, base-case lane hire, all 30 taking the Founding discount, blocks starting w/c 30 November 2026 and running into January (6 lessons for 1:1 and 2:1; 8 sessions for Programmes).

| Line | Working | £ |
|---|---|---|
| Revenue at list | 14 x £195 (1:1 blocks) + 4 x £270 (pairs) + 8 x £160 (Programmes) | 5,090 |
| Founding Member discount | 10% | (509) |
| **Revenue collected** | | **4,581** |
| Lane hire | 1:1: 14 x 6 x £17.50 = £1,470; pairs: 4 x 6 x £17.50 = £420; groups: 2 x 8 x £26.25 = £420 | (2,310) |
| Stripe fees | 1.5% of £4,581 plus 26 x 20p | (74) |
| Founding caps | 30 x £6 | (180) |
| Consumables, certificates, printing | | (60) |
| **Contribution from the founding term** | | **1,957** |
| Taster lane time to win the 30 (about 40 tasters at £17.50) | | (700) |
| **Contribution after acquisition cost** | | **1,257** |
| Fixed overheads for the same 8 to 9 weeks (year-1 rate, about £200 per month) | | (420) |
| **Profit before tax, founding term** | | **about 840** |

Over roughly 8 to 9 weeks and about 10.5 coaching hours a week, that is around £100 a week of profit. **That is fine.** The founding term is not where the money is; it is where the proof is: 30 assessments on file, 30 written reports, a renewal rate, a waiting list and the first reviews. The second term, with 80% renewing (24 swimmers), no caps to buy, half the taster load and the Programme groups full, contributes roughly £2,000 to £2,400 for the same hours, and the third term adds new swimmers on top.

---

## 10. Recommended first-year revenue target (November 2026 to October 2027)

| Quarter | What is happening | Coaching hrs/week | Revenue |
|---|---|---|---|
| Nov to Jan | Founding term, tasters, Christmas | 8 to 11 | £5,500 |
| Feb to Apr | Renewals, Programme intakes, February and Easter Intensives, clinics | 12 to 15 | £11,000 |
| May to Jul | Half-term Intensive, Sprint intake, summer pre-sell | 14 to 16 | £12,500 |
| Aug to Oct | Summer Intensives, September restart, first coach shadowing | 14 to 18 | £13,000 |
| **Year 1** | | | **£42,000** |

- **Realistic target: £40,000 revenue, about £20,000 contribution, about £17,000 profit before tax.**
- **Stretch: £55,000** if a second venue and a group-heavy mix land by Easter.
- **Floor (something is wrong if below): £25,000.** Most likely cause would be venue access, not demand.

These numbers assume Ruby stays under about 16 hours a week in term time so that training is protected.

---

## 11. How to use the calculator

`website/tools/calculator.html` (being built) is this file as a live model. Suggested use:

1. Enter the **real lane-hire quote** from each venue (per hour). Everything else updates.
2. Enter the **mix of hours** you actually sold last week (1:1, 2:1, group, clinic). The blended contribution per hour tells you what a coaching hour is worth right now.
3. Enter **Ruby's hours** and, from Stage 2, coach hours and pay. The profit line shows whether the coach is paying for themselves.
4. Use the **sensitivity grid** before any venue negotiation: it shows what a £5 change in hire rate is worth.
5. Compare **sole trader versus Ltd** on the tax tab once the accountant has confirmed the rates.
6. Check the **first-term example** against actuals at week 6. Where reality differs from the model, change the model, not the target.

Keep the assumptions table in section 1 and the calculator inputs in step. When a quote is confirmed, remove the **[CONFIRM]** tag in this file and update the calculator default.
