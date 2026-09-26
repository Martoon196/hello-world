// POST /api/create-checkout — creates a Stripe Checkout Session for a paid booking.
// Prices come from programmes.json on the server. Booking details ride along in session metadata and are
// turned into calendar events + emails by stripe-webhook.js once payment succeeds.
const { config, schedule, RWSlots, json, validateBooking } = require("./lib/config");
const calendar = require("./lib/calendar");

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return json(405, { error: "Method not allowed" });
  if (!config.stripeKey) return json(503, { error: "Payments aren't switched on yet. Please email hello@rwswimacademy.co.uk to book." });
  let body; try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "Bad JSON" }); }
  const v = validateBooking(body);
  if (!v.ok) return json(400, { error: v.error });
  const { booking, product } = v;
  if (product.price === 0) return json(400, { error: "This is a free lesson; no payment needed." });

  // Availability re-check for slot-based products (programmes/intensives are checked by Ruby on receipt)
  if (product.type === "single" || product.type === "block") {
    const offered = RWSlots.generateSlots(schedule, product).some((s) => s.start === booking.start);
    if (!offered) return json(409, { error: "That time isn't available any more. Please pick another." });
    if (calendar.isConfigured()) {
      const busy = await calendar.busy(booking.occurrences[0].start, booking.occurrences[booking.occurrences.length - 1].end);
      if (RWSlots.removeBusy(schedule, product, [{ start: booking.start }], busy).length === 0) return json(409, { error: "Sorry, that slot has just been taken. Please choose another." });
    }
  }

  const stripe = require("stripe")(config.stripeKey);
  const metadata = {};
  for (const [k, val] of Object.entries(booking)) {
    if (k === "occurrences") metadata.occurrences = val.map((o) => o.start).join(",");
    else metadata[k] = String(val ?? "").slice(0, 500);
  }
  try {
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      customer_email: booking.email,
      allow_promotion_codes: true, // founding member codes (FOUNDER10 etc.) are created in the Stripe dashboard
      line_items: [{
        quantity: 1,
        price_data: {
          currency: "gbp", unit_amount: product.price,
          product_data: { name: product.name, description: `${booking.child_name}${booking.child2_name ? " & " + booking.child2_name : ""} · first lesson ${RWSlots.fmt(booking.start, config.timezone, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}` },
        },
      }],
      metadata,
      payment_intent_data: { description: `${product.name} for ${booking.child_name}` },
      success_url: `${config.siteUrl}/thanks/booking-success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${config.siteUrl}/book.html?product=${product.id}`,
      consent_collection: { terms_of_service: "none" },
      expires_at: Math.floor(Date.now() / 1000) + 30 * 60,
    });
    return json(200, { url: session.url });
  } catch (e) {
    console.error("stripe session failed", e.message);
    return json(500, { error: "Couldn't start the payment. Please try again or email hello@rwswimacademy.co.uk." });
  }
};
