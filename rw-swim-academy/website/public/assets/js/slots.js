/* RW Swim Academy — slot generator shared by the browser (fallback/demo mode) and Netlify functions.
   Works with schedule.json and programmes.json. All times handled in the schedule timezone (Europe/London). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.RWSlots = factory();
})(typeof self !== "undefined" ? self : this, function () {
  const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

  function tzParts(date, tz) {
    if (!(date instanceof Date)) date = new Date(date);
    const dtf = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour12: false, weekday: "short", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const p = Object.fromEntries(dtf.formatToParts(date).map((x) => [x.type, x.value]));
    return { y: +p.year, m: +p.month, d: +p.day, hh: +p.hour % 24, mm: +p.minute, ss: +p.second, wd: p.weekday.toLowerCase().slice(0, 3) };
  }
  function tzOffsetMinutes(date, tz) {
    const p = tzParts(date, tz);
    return (Date.UTC(p.y, p.m - 1, p.d, p.hh, p.mm, p.ss) - date.getTime()) / 60000;
  }
  /** Local wall-clock time in `tz` -> UTC Date. Handles DST by iterating. */
  function localToUtc(y, m, d, hh, mm, tz) {
    const wall = Date.UTC(y, m - 1, d, hh, mm);
    let guess = wall;
    for (let i = 0; i < 2; i++) guess = wall - tzOffsetMinutes(new Date(guess), tz) * 60000;
    return new Date(guess);
  }
  function ymd(date, tz) { const p = tzParts(date, tz); return `${p.y}-${String(p.m).padStart(2, "0")}-${String(p.d).padStart(2, "0")}`; }
  function addDays(dateStr, n) { const [y, m, d] = dateStr.split("-").map(Number); const t = new Date(Date.UTC(y, m - 1, d + n)); return t.toISOString().slice(0, 10); }
  function weekdayOf(dateStr, tz) { const [y, m, d] = dateStr.split("-").map(Number); return tzParts(localToUtc(y, m, d, 12, 0, tz), tz).wd; }
  function atLocal(dateStr, timeStr, tz) { const [y, m, d] = dateStr.split("-").map(Number); const [hh, mm] = timeStr.split(":").map(Number); return localToUtc(y, m, d, hh, mm, tz); }

  /** Candidate start times for a product over the booking horizon (before removing calendar busy times). */
  function generateSlots(schedule, product, opts) {
    const tz = schedule.timezone || "Europe/London";
    const now = (opts && opts.now) || new Date();
    const lead = new Date(now.getTime() + (schedule.bookingLeadHours || 24) * 3600000);
    const horizon = schedule.bookingHorizonDays || 42;
    const windows = product.id === "taster" ? (schedule.tasterWindows || schedule.windows) : schedule.windows;
    const duration = product.duration || schedule.slotMinutes || 30;
    const step = schedule.slotMinutes || 30;
    const out = [];
    let day = ymd(now, tz);
    for (let i = 0; i <= horizon; i++, day = addDays(day, 1)) {
      const wd = weekdayOf(day, tz);
      for (const w of windows) {
        if (w.day !== wd) continue;
        const start = atLocal(day, w.start, tz), end = atLocal(day, w.end, tz);
        for (let t = start.getTime(); t + duration * 60000 <= end.getTime(); t += step * 60000) {
          if (t < lead.getTime()) continue;
          out.push({ start: new Date(t).toISOString(), end: new Date(t + duration * 60000).toISOString() });
        }
      }
    }
    return out;
  }

  /** All lesson occurrences for a booking. Returns [{start,end}] in ISO. */
  function occurrences(schedule, product, firstStartIso, extra) {
    const tz = schedule.timezone || "Europe/London";
    const duration = product.duration || 30;
    const n = product.lessons || 1;
    const first = new Date(firstStartIso);
    const p = tzParts(first, tz);
    const list = [];
    for (let i = 0; i < n; i++) {
      // weekly for blocks/programmes, daily (Mon–Fri) for intensives
      const dayOffset = product.type === "intensive" ? i : i * 7;
      const dateStr = addDays(`${p.y}-${String(p.m).padStart(2, "0")}-${String(p.d).padStart(2, "0")}`, dayOffset);
      const s = atLocal(dateStr, `${String(p.hh).padStart(2, "0")}:${String(p.mm).padStart(2, "0")}`, tz);
      list.push({ start: s.toISOString(), end: new Date(s.getTime() + duration * 60000).toISOString() });
    }
    return list;
  }

  function overlaps(a, b) { return new Date(a.start) < new Date(b.end) && new Date(b.start) < new Date(a.end); }
  /** Remove slots whose full set of occurrences collides with any busy period. */
  function removeBusy(schedule, product, slots, busy) {
    if (!busy || !busy.length) return slots;
    return slots.filter((s) => occurrences(schedule, product, s.start).every((o) => !busy.some((b) => overlaps(o, b))));
  }

  function fmt(iso, tz, opts) {
    return new Intl.DateTimeFormat("en-GB", Object.assign({ timeZone: tz || "Europe/London" }, opts)).format(new Date(iso));
  }

  return { DAYS, generateSlots, occurrences, removeBusy, atLocal, localToUtc, ymd, addDays, weekdayOf, fmt, tzParts };
});
