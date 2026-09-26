// Transactional email via Resend's HTTP API (no SDK needed). Logs instead of sending when RESEND_API_KEY is unset.
const { config, fmt } = require("./config");

async function send({ to, subject, html, replyTo }) {
  if (!config.resendKey) { console.log("[email:demo]", to, subject); return { demo: true }; }
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST", headers: { Authorization: `Bearer ${config.resendKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: config.emailFrom, to: Array.isArray(to) ? to : [to], subject, html, reply_to: replyTo || config.academyEmail || undefined }),
  });
  if (!r.ok) throw new Error(`Email failed: ${r.status} ${await r.text()}`);
  return r.json();
}

const wrap = (inner) => `<div style="font-family:Inter,Arial,sans-serif;color:#1B2B3A;max-width:600px;margin:0 auto;padding:24px">
  <div style="background:#0B2545;padding:18px 24px;border-radius:14px 14px 0 0"><span style="color:#fff;font-weight:800;font-size:20px;letter-spacing:1px">RW SWIM <span style="color:#12B5C9">ACADEMY</span></span></div>
  <div style="border:1px solid #DCE6EC;border-top:0;padding:24px;border-radius:0 0 14px 14px;line-height:1.6">${inner}
  <p style="color:#5B6B7B;font-size:13px;margin-top:28px">RW Swim Academy · Sevenoaks, Kent · <a href="mailto:${config.academyEmail || "hello@rwswimacademy.co.uk"}">${config.academyEmail || "hello@rwswimacademy.co.uk"}</a></p></div></div>`;

const datesList = (b) => `<ul>${b.occurrences.map((o) => `<li>${fmt(o.start)}</li>`).join("")}</ul>`;

function confirmationEmail(b) {
  const isTaster = b.price === 0;
  const subject = isTaster ? `Taster booked: ${b.child_name} with Ruby, ${fmt(b.start)}` : `Booking confirmed: ${b.productName} for ${b.child_name}`;
  const html = wrap(`
    <h2 style="color:#0B2545;margin-top:0">${isTaster ? "See you at the pool!" : "You're booked in."}</h2>
    <p>Hi ${b.parent_name.split(" ")[0]},</p>
    <p>${isTaster ? `${b.child_name}'s free taster with Ruby is booked.` : `Thanks for booking <strong>${b.productName}</strong> for ${b.child_name}${b.child2_name ? " and " + b.child2_name : ""}.`} Here are the details:</p>
    ${datesList(b)}
    <p><strong>Venue:</strong> Sevenoaks area. Ruby will confirm the exact pool, parking and where to meet by reply to this email within one working day. <em>[Once venues are fixed, put the address here.]</em></p>
    <p><strong>Please bring:</strong> swimsuit or jammers, goggles, a swim hat for long hair, a towel and a warm layer. Arrive 10 minutes early.</p>
    ${isTaster ? `<p>After the taster you'll get a written level assessment and Ruby's honest recommendation. No pressure either way.</p>` : `<p><strong>Moving a lesson:</strong> 24 hours' notice, one move per block. Ill on the day? Message before 8am and we'll try to swap. <strong>First-lesson promise:</strong> if ${b.child_name} doesn't want to come back after lesson one, tell us and we refund the rest.</p>`}
    ${b.medical ? `<p><strong>You told us:</strong> ${b.medical}</p>` : `<p>Anything Ruby should know before the first session (nerves, medical, what's worked before)? Just reply to this email.</p>`}
    <p>Ruby x</p>`);
  return { subject, html };
}

function academyNotification(b, extra = "") {
  const subject = `NEW ${b.price === 0 ? "TASTER" : "BOOKING"}: ${b.child_name} · ${b.productName} · ${fmt(b.start)}`;
  const html = wrap(`<h2 style="margin-top:0">New ${b.price === 0 ? "taster" : "booking"}</h2>
    <p><strong>${b.productName}</strong> · £${(b.price / 100).toFixed(2)} ${extra}</p>
    <p><strong>Parent:</strong> ${b.parent_name} · <a href="mailto:${b.email}">${b.email}</a> · ${b.phone}<br>
    <strong>Swimmer:</strong> ${b.child_name}, ${b.child_age} · ${b.ability}${b.child2_name ? `<br><strong>Second swimmer:</strong> ${b.child2_name}, ${b.child2_age}` : ""}<br>
    <strong>Photo consent:</strong> ${b.photo_consent}${b.cohort ? `<br><strong>Group:</strong> ${b.cohort}` : ""}</p>
    ${b.medical ? `<p><strong>Notes:</strong> ${b.medical}</p>` : ""}
    <p><strong>Dates:</strong></p>${datesList(b)}
    <p>Reply to the parent with the venue and parking details.</p>`);
  return { subject, html };
}

async function sendBookingEmails(b, extra) {
  const c = confirmationEmail(b);
  await send({ to: b.email, subject: c.subject, html: c.html });
  if (config.academyEmail) { const n = academyNotification(b, extra); await send({ to: config.academyEmail, subject: n.subject, html: n.html, replyTo: b.email }); }
}

module.exports = { send, sendBookingEmails, wrap };
