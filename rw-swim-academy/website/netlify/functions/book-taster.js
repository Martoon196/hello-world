// POST /api/book-taster — free bookings (price 0). Re-checks the slot, creates calendar events, sends emails.
const { config, schedule, RWSlots, json, validateBooking } = require("./lib/config");
const calendar = require("./lib/calendar");
const email = require("./lib/email");

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return json(405, { error: "Method not allowed" });
  let body; try { body = JSON.parse(event.body || "{}"); } catch { return json(400, { error: "Bad JSON" }); }
  const v = validateBooking(body);
  if (!v.ok) return json(400, { error: v.error });
  const { booking, product } = v;
  if (product.price !== 0) return json(400, { error: "This lesson needs payment. Please use the checkout." });

  // Make sure the slot is one we offer and still free
  const offered = RWSlots.generateSlots(schedule, product).some((s) => s.start === booking.start);
  if (!offered) return json(409, { error: "That time isn't available any more. Please pick another." });
  if (calendar.isConfigured()) {
    const busy = await calendar.busy(booking.occurrences[0].start, booking.occurrences[booking.occurrences.length - 1].end);
    if (RWSlots.removeBusy(schedule, product, [{ start: booking.start }], busy).length === 0) return json(409, { error: "Sorry, that slot has just been taken. Please choose another." });
  }
  try {
    booking.paymentRef = "free-taster";
    const ids = await calendar.createLessons(booking, { prefix: "TASTER" });
    await email.sendBookingEmails(booking, ids.length ? "" : "(calendar not connected)");
    return json(200, { ok: true, calendarEvents: ids.length, demo: !calendar.isConfigured() || !config.resendKey });
  } catch (e) {
    console.error("book-taster failed", e);
    return json(500, { error: "We couldn't complete the booking. Please email hello@rwswimacademy.co.uk." });
  }
};
