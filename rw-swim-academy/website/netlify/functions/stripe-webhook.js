// POST /api/stripe-webhook — Stripe calls this after payment. Add the endpoint in Stripe > Developers > Webhooks
// for the event `checkout.session.completed`, and put the signing secret in STRIPE_WEBHOOK_SECRET.
const { config, json } = require("./lib/config");
const calendar = require("./lib/calendar");
const email = require("./lib/email");

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return json(405, { error: "Method not allowed" });
  if (!config.stripeKey || !config.stripeWebhookSecret) return json(503, { error: "Stripe not configured" });
  const stripe = require("stripe")(config.stripeKey);
  let evt;
  try {
    const sig = event.headers["stripe-signature"];
    const raw = event.isBase64Encoded ? Buffer.from(event.body, "base64").toString("utf8") : event.body;
    evt = stripe.webhooks.constructEvent(raw, sig, config.stripeWebhookSecret);
  } catch (e) { console.error("Webhook signature failed", e.message); return json(400, { error: "Bad signature" }); }

  if (evt.type !== "checkout.session.completed") return json(200, { received: true, ignored: evt.type });
  const s = evt.data.object;
  if (s.payment_status !== "paid") return json(200, { received: true, unpaid: true });

  const m = s.metadata || {};
  const duration = require("./lib/config").getProduct(m.productId)?.duration || 30;
  const booking = {
    ...m, price: Number(m.price || 0), paymentRef: s.id,
    occurrences: String(m.occurrences || "").split(",").filter(Boolean).map((start) => ({ start, end: new Date(new Date(start).getTime() + duration * 60000).toISOString() })),
  };
  try {
    const ids = await calendar.createLessons(booking, { prefix: "Lesson" });
    const paid = `· paid £${((s.amount_total || 0) / 100).toFixed(2)}${s.total_details?.amount_discount ? ` (discount £${(s.total_details.amount_discount / 100).toFixed(2)})` : ""} · Stripe ${s.id}${ids.length ? "" : " · calendar not connected"}`;
    await email.sendBookingEmails(booking, paid);
  } catch (e) {
    // Return 500 so Stripe retries; the payment is safe either way.
    console.error("post-payment processing failed", e);
    return json(500, { error: "processing failed, will retry" });
  }
  return json(200, { received: true });
};
