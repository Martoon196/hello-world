// Shared config + data for functions. Product prices always come from programmes.json (server side), never from the client.
const programmes = require("../../../public/data/programmes.json");
const schedule = require("../../../public/data/schedule.json");
const RWSlots = require("../../../public/assets/js/slots.js");

const env = (k, d) => (process.env[k] && process.env[k].trim()) || d;
const config = {
  siteUrl: env("SITE_URL", "http://localhost:8888"),
  academyEmail: env("ACADEMY_EMAIL", ""),
  academyPhone: env("ACADEMY_PHONE", ""),
  timezone: env("TIMEZONE", schedule.timezone || "Europe/London"),
  stripeKey: env("STRIPE_SECRET_KEY", ""),
  stripeWebhookSecret: env("STRIPE_WEBHOOK_SECRET", ""),
  calendarId: env("GOOGLE_CALENDAR_ID", ""),
  serviceAccountJson: env("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
  resendKey: env("RESEND_API_KEY", ""),
  emailFrom: env("EMAIL_FROM", "RW Swim Academy <hello@rwswimacademy.co.uk>"),
};

const json = (status, body) => ({ statusCode: status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" }, body: JSON.stringify(body) });
const getProduct = (id) => programmes.products.find((p) => p.id === id);
const fmt = (iso, opts) => RWSlots.fmt(iso, config.timezone, Object.assign({ weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }, opts));

/** Validate a booking payload from the client. Returns {ok, error, booking}. */
function validateBooking(body) {
  const b = body || {};
  const product = getProduct(b.productId);
  if (!product) return { ok: false, error: "Unknown lesson type." };
  const start = new Date(b.start);
  if (isNaN(start) || start < new Date()) return { ok: false, error: "Please choose a time in the future." };
  const req = ["parent_name", "email", "phone", "child_name", "child_age", "ability"];
  for (const k of req) if (!b[k] || !String(b[k]).trim()) return { ok: false, error: `Missing ${k.replace("_", " ")}.` };
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(b.email)) return { ok: false, error: "That email address doesn't look right." };
  if (product.swimmers === 2 && !b.child2_name) return { ok: false, error: "Please add the second swimmer's name." };
  if (!b.terms) return { ok: false, error: "Please accept the terms and conditions." };
  const clean = (s, n = 500) => String(s || "").replace(/[<>]/g, "").trim().slice(0, n);
  const booking = {
    productId: product.id, productName: product.name, price: product.price, start: start.toISOString(), cohort: clean(b.cohort, 120),
    parent_name: clean(b.parent_name, 80), email: clean(b.email, 120).toLowerCase(), phone: clean(b.phone, 30),
    child_name: clean(b.child_name, 60), child_age: clean(b.child_age, 3), ability: clean(b.ability, 80),
    child2_name: clean(b.child2_name, 60), child2_age: clean(b.child2_age, 3), medical: clean(b.medical, 480),
    photo_consent: b.photo_consent === true || b.photo_consent === "yes" ? "yes" : "no",
  };
  booking.occurrences = RWSlots.occurrences(schedule, product, booking.start);
  return { ok: true, booking, product };
}

module.exports = { config, programmes, schedule, RWSlots, json, getProduct, validateBooking, fmt };
