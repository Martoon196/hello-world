# Free Taster Sequence (5 emails)

**Trigger:** books a free taster at `/taster`.
**Audience:** solution-aware to product-aware. They have chosen RW for a look; the job is to get them there, then convert the taster into a block.
**Funnel position:** middle to bottom.
**Voice:** Ruby, first person. T0 and T1 are transactional (sent regardless of marketing consent). T2 is written per child by Ruby from the template. T3 and T4 are automated and stop the moment a block is booked.
**Tokens:** `{{first_name}}`, `{{child_name}}`, `{{child_age}}`, `{{taster_date}}`, `{{taster_time}}`, `{{venue}}`, `{{venue_notes}}`, `{{programme}}`, `{{booking_link}}`, `{{founding_places_left}}`.

**Assumptions:** Ruby writes the assessment on paper poolside and photographs it or types the key lines into T2 the same evening. Founding-member places are counted by Chris and the number is updated weekly in the tool as a custom field. **[CONFIRM workflow]**

Timing: T0 immediate · T1 24 hours before `{{taster_date}}` · T2 manual, same day as taster · T3 3 days after T2 if no booking · T4 7 days after T2 if no booking.

---

## T0: Taster confirmed and what to bring
**Job:** confirm, reduce no-shows, set expectations. Framework: direct (transactional). Hook: reassurance.

**Subject line options**
1. (Direct) {{child_name}}'s free taster is booked: {{taster_date}}, {{taster_time}}
2. (How-to) what to bring on {{taster_date}} (it's not much)
3. (Humanity) see you both on {{taster_date}}

**Preview text:** Where to go, what to bring, and what happens in the 20 minutes.

**Body**

Hi {{first_name}},

{{child_name}}'s taster is booked.

**When:** {{taster_date}} at {{taster_time}}. Please arrive 10 minutes early.
**Where:** {{venue}}. {{venue_notes}} **[e.g. parking, which entrance, tell reception you're with RW Swim Academy]**
**How long:** 20 minutes in the water, then 5 minutes with me on poolside.

**What to bring**
- Costume on under clothes (saves the changing-room scramble)
- Goggles that fit. Quick test: press them to the face without the strap. If they stick for a second, they're right.
- Towel, and something warm for after
- Long hair tied back

Nothing else. No floats, no armbands. I have everything.

**What happens.** You sit poolside and watch. I'll look at how {{child_name}} gets in, whether they'll put their face in and blow out, whether they can float and get their feet back down, and one width of whatever they've got. If they don't want to get in, we sit on the edge with feet in and that's fine. It's not a test.

Afterwards I'll show you a one-page written assessment. You keep it. I'll email a copy the same day with a recommended next step. No decisions on poolside.

**Need to change it?** Reply to this email or message [Chris's number] **[CONFIRM]** with at least 24 hours' notice and we'll move it. Tasters are limited to six a week, so if you can't make it, please tell us so another family can have the slot.

Ruby

PS: If {{child_name}} is nervous about it, one thing that helps: tell them they're going to "meet Ruby and have a splash", not "have a swimming test".

**CTA:** None beyond reply-to-change. Add to calendar link if the tool supports it.

---

## T1: 24-hour reminder
**Job:** cut no-shows to zero. Framework: direct. Hook: self-interest (practical).

**Subject line options**
1. (Direct) tomorrow at {{taster_time}}: {{child_name}}'s taster
2. (How-to) tomorrow's taster: the 30-second checklist
3. (Humanity) looking forward to meeting {{child_name}} tomorrow

**Preview text:** {{venue}}, 10 minutes early, goggles that fit.

**Body**

Hi {{first_name}},

Quick reminder that {{child_name}}'s taster is tomorrow, {{taster_date}}, at {{taster_time}}, at {{venue}}.

The 30-second checklist:
- Costume on under clothes
- Goggles (suction test: press on, no strap, do they stick?)
- Towel and a hoodie
- Arrive 10 minutes early and tell reception you're with RW

Can't make it? Reply now or message [Chris's number] so another family can take the slot. Same-day illness: message before 8am and we'll try to swap.

See you tomorrow.

Ruby

PS: If they want to bring their goggles in the bath tonight for ten minutes, it makes the first minute in the pool a lot easier.

**CTA:** None. Reply to cancel.

---

## T2: Same-day follow-up with assessment and recommended block
**Job:** deliver the assessment, recommend one block, make booking one click. This is the conversion email. Framework: FAB with proof from the taster itself. Hook: personal proof. **Written by Ruby per child using this template; fill every bracket.**

**Subject line options**
1. (Personal) {{child_name}}'s assessment from today
2. (Self-interest) where {{child_name}} is, and what I'd do next
3. (Humanity) it was lovely meeting {{child_name}}
4. (Curiosity) the thing {{child_name}} did that surprised me

**Preview text:** One page, one recommendation, one link. No pressure.

**Body**

Hi {{first_name}},

Really good to meet you and {{child_name}} today. Here's the assessment I showed you on poolside, plus what I'd recommend.

**Where {{child_name}} is now**
- Getting in: [e.g. "steps, unprompted, no hesitation" / "sat on the edge for a few minutes, then in via the steps holding my hand"]
- Face and breath: [e.g. "face in for a count of three, bubbles with a hum by the end" / "not yet, but blew bubbles at the surface, which is the first step"]
- Float and recover: [e.g. "back float with light support, feet down on their own" / "not yet, we'll build this in weeks 1 to 3"]
- One width: [e.g. "width of front crawl, head up, holds breath; needs breathing out under the water" / "kicked to me on a float, strong legs"]

**Level:** [Splash / Stroke / Sprint] **[or "1:1 first, then a group when they're ready"]**

**The one thing that surprised me:** [one genuine, specific observation. e.g. "How quickly they trusted the water once they'd chosen to put one foot in. That's not something I can teach; you've done that."]

**What I'd recommend**
[Choose one; delete the others]

- **A block of six 1:1 lessons, 30 minutes, {{slot_day}} at {{slot_time}}.** £195, or £175.50 as a founding member. I'd work on [two specific things] first, and I'd expect [honest, modest expectation, e.g. "face in comfortably and a back float unaided by week 4"].
- **The {{programme}} Progress Programme: 8 weeks, 45 minutes, groups of four at the same level, {{slot_day}} at {{slot_time}}.** £160, or £144 as a founding member. There are [X] places left in that group.
- **Semi-private 2:1 with [sibling/friend]:** £25 per swimmer per lesson, block of six £270. Only if they're at a similar level, which today they [are / aren't quite].

Book here: {{booking_link}}

Two things so you can decide at home without any pressure:
1. If {{child_name}} doesn't want to come back after the first lesson of a block, tell us and we'll refund the rest. No awkward conversation.
2. Founding-member places: {{founding_places_left}} of 30 left as of this evening. Once they're gone, the 10% for life goes with them. I'm not going to chase you about it; I'd just rather you knew.

Any questions, reply to this. I answer everything myself.

Ruby

PS: Regardless of what you decide, the bath-time homework that would help most is [one specific thing, e.g. "humming with the face in the water for a count of three, every bath"]. That's yours to keep.

**CTA:** Book the recommended block (one link).

---

## T3: 3-day nudge (only if no booking)
**Job:** get a reply or a click by removing the most likely objection. Framework: PAS, very short. Hook: question.

**Subject line options**
1. (Question) was it the day, the time, or the price?
2. (Humanity) no pressure, just checking one thing
3. (Self-interest) {{child_name}}'s slot is still free (for now)
4. (Curiosity) the thing most parents ask me at this point

**Preview text:** If something didn't fit, tell me and I'll see what I can move.

**Body**

Hi {{first_name}},

Three days since {{child_name}}'s taster, and I haven't heard back, which is completely fine. I know how the week goes.

If you're still deciding, the thing that usually gets in the way is one of three:

**The day or time.** Reply with what you can do and I'll see if I can move something. I can't promise, but I'll try.
**The price.** A block is the best value, but a single 1:1 at £35 is there if you'd rather try one lesson first.
**Whether {{child_name}} will want to keep going.** That's what the refund rule is for. First lesson of a block, they don't want to come back, we refund the rest.

If it's something else, reply and tell me. I'd rather know.

The recommended slot from the assessment ({{slot_day}} at {{slot_time}}) is still open today: {{booking_link}}

Ruby

PS: {{founding_places_left}} founding places left. That's a real number, not a countdown.

**CTA:** Book, or reply with the obstacle.

---

## T4: 7-day last call with founding offer expiry (only if no booking)
**Job:** one honest final ask, then stop. Framework: urgency-led direct. Hook: closure.

**Subject line options**
1. (Urgency) last one from me about {{child_name}}'s slot
2. (Direct) I'll release {{child_name}}'s slot on {{release_date}}
3. (Humanity) no hard feelings either way
4. (Offer) the founding rate ends when the places do

**Preview text:** The slot I held goes back to the list on {{release_date}}. Here's the link if you want it.

**Body**

Hi {{first_name}},

Last email from me about this, then I'll leave you be.

I've held {{slot_day}} at {{slot_time}} for {{child_name}} since the taster. On {{release_date}} it goes back to the list, because other families are waiting on that day.

If you'd like it: {{booking_link}}

The founding-member rate (10% off for life, free cap, priority booking) applies to the first 30 swimmers to book a block. There are {{founding_places_left}} left as I write this. If they go before you book, the standard price applies, and I won't pretend otherwise.

If now isn't the right time, that's genuinely fine. The assessment is yours to keep, the bath-time homework still works, and you can book a taster again whenever you're ready. I'll be here.

Thanks for coming to see me. It was good to meet {{child_name}}.

Ruby

PS: If you'd rather I didn't email about lessons at all, the unsubscribe link is at the bottom and I'll only ever send booking confirmations after that.

**CTA:** Book (one link). Then the automation ends.

---

## Audit (email rubric, 1 to 5)

| Email | Subject lines | Preview | First line | One job / one CTA | Voice | Momentum | Notes |
|---|---|---|---|---|---|---|---|
| T0 | 4 | 5 | 5 | 5 | 5 | 5 | Three subject lines rather than five: transactional, the child's name and date do the work. |
| T1 | 4 | 5 | 5 | 5 | 5 | 5 | Same. Kept under 120 words. |
| T2 | 5 | 5 | 5 | 5 | 5 | 5 | The template forces one recommendation, not a menu. Ruby must delete the two unused options. The "one thing that surprised me" line is the whole email; do not skip it. |
| T3 | 5 | 5 | 4 | 5 | 5 | 5 | Opening line acknowledges silence without guilt. Three named objections instead of "any questions?". |
| T4 | 5 | 5 | 5 | 5 | 5 | 5 | Contains a genuine end and a genuine door left open. Scarcity is true only if `{{founding_places_left}}` is updated; if Chris can't maintain it, delete that paragraph rather than fake it. |

**Auto-fixes applied:** removed "Just checking in" from the T3 draft first line. Replaced "guaranteed a place" with "held" in T4. Prohibited words: none present.

**Flags:** Chris's number, venue notes per venue, whether the tool can hold `{{founding_places_left}}` as a global field, and the `{{release_date}}` logic (suggest taster date + 10 days).
