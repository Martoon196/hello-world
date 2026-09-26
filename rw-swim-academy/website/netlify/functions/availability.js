// GET /api/availability?product=private-6
// Returns { slots: [{start,end}], demo: boolean }. Slots are Ruby's teaching windows minus Google Calendar busy times,
// and (for blocks) only slots where every weekly occurrence is free.
const { schedule, RWSlots, json, getProduct } = require("./lib/config");
const calendar = require("./lib/calendar");

exports.handler = async (event) => {
  const product = getProduct((event.queryStringParameters || {}).product);
  if (!product) return json(400, { error: "Unknown product" });
  const candidates = RWSlots.generateSlots(schedule, product);
  if (!candidates.length) return json(200, { slots: [], demo: !calendar.isConfigured() });
  let busy = [];
  if (calendar.isConfigured()) {
    try {
      const from = candidates[0].start;
      const last = RWSlots.occurrences(schedule, product, candidates[candidates.length - 1].start).pop().end;
      busy = await calendar.busy(from, last);
    } catch (e) { console.error("freebusy failed", e.message); return json(200, { slots: candidates, demo: true, warning: "calendar unavailable" }); }
  }
  return json(200, { slots: RWSlots.removeBusy(schedule, product, candidates, busy), demo: !calendar.isConfigured() });
};
