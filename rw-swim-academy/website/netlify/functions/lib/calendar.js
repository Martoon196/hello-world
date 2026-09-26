// Google Calendar via a service account. The academy calendar must be shared with the service account email
// with "Make changes to events". If not configured, every function degrades gracefully (demo mode).
const { google } = require("googleapis");
const { config } = require("./config");

let client;
function getClient() {
  if (client !== undefined) return client;
  if (!config.calendarId || !config.serviceAccountJson) { client = null; return client; }
  try {
    const creds = JSON.parse(config.serviceAccountJson);
    const auth = new google.auth.JWT({ email: creds.client_email, key: creds.private_key, scopes: ["https://www.googleapis.com/auth/calendar"] });
    client = google.calendar({ version: "v3", auth });
  } catch (e) { console.error("Calendar credentials invalid:", e.message); client = null; }
  return client;
}
const isConfigured = () => !!getClient();

/** Busy periods in [from, to] (ISO). Returns [] when not configured. */
async function busy(from, to) {
  const cal = getClient(); if (!cal) return [];
  const r = await cal.freebusy.query({ requestBody: { timeMin: from, timeMax: to, timeZone: config.timezone, items: [{ id: config.calendarId }] } });
  return (r.data.calendars[config.calendarId].busy || []).map((b) => ({ start: b.start, end: b.end }));
}

/** Create one event per occurrence. Returns array of event ids (empty when not configured). */
async function createLessons(booking, opts = {}) {
  const cal = getClient(); if (!cal) return [];
  const ids = [];
  const n = booking.occurrences.length;
  for (let i = 0; i < n; i++) {
    const o = booking.occurrences[i];
    const summary = `${opts.prefix || "Lesson"}: ${booking.child_name}${booking.child2_name ? " & " + booking.child2_name : ""} (${booking.productName}${n > 1 ? `, ${i + 1}/${n}` : ""})`;
    const description = [
      `Parent: ${booking.parent_name} · ${booking.email} · ${booking.phone}`,
      `Swimmer: ${booking.child_name}, ${booking.child_age} · ${booking.ability}` + (booking.child2_name ? ` | ${booking.child2_name}, ${booking.child2_age}` : ""),
      booking.medical ? `Notes: ${booking.medical}` : "",
      `Photo consent: ${booking.photo_consent}`,
      booking.paymentRef ? `Payment: ${booking.paymentRef}` : "",
    ].filter(Boolean).join("\n");
    const r = await cal.events.insert({
      calendarId: config.calendarId,
      sendUpdates: "all",
      requestBody: {
        summary, description,
        start: { dateTime: o.start, timeZone: config.timezone }, end: { dateTime: o.end, timeZone: config.timezone },
        attendees: [{ email: booking.email, displayName: booking.parent_name }],
        reminders: { useDefault: false, overrides: [{ method: "email", minutes: 24 * 60 }, { method: "popup", minutes: 120 }] },
        extendedProperties: { private: { productId: booking.productId, paymentRef: booking.paymentRef || "" } },
      },
    });
    ids.push(r.data.id);
  }
  return ids;
}

module.exports = { isConfigured, busy, createLessons };
