/* RW Swim Academy — booking wizard
   1) choose product  2) choose time (live from /api/availability, falls back to schedule.json)
   3) swimmer details  4) confirm -> /api/create-checkout (Stripe) or /api/book-taster (free) */
(function () {
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const TZ = "Europe/London";
  const money = (p) => (p === 0 ? "Free" : "£" + (p / 100).toFixed(p % 100 ? 2 : 0));
  const state = { products: [], schedule: null, product: null, slot: null, cohort: null, details: null, demo: false };

  const alertBox = $("#booking-alert");
  const showAlert = (type, html) => { alertBox.innerHTML = `<div class="alert alert--${type}">${html}</div>`; };
  const clearAlert = () => (alertBox.innerHTML = "");

  function go(step) {
    $$(".wiz-panel").forEach((p) => p.classList.toggle("active", p.dataset.panel == step));
    $$("#wiz-steps li").forEach((li) => { const n = +li.dataset.step; li.classList.toggle("active", n === step); li.classList.toggle("done", n < step); });
    window.scrollTo({ top: $("#wiz-steps").offsetTop - 90, behavior: "smooth" });
  }
  $$("[data-back]").forEach((b) => b.addEventListener("click", () => go(+b.dataset.back)));

  function updateSummary() {
    const p = state.product;
    $("#s-product").textContent = p ? p.name : "—";
    $("#s-total").textContent = p ? money(p.price) : "£0";
    let when = "—";
    if (p && state.cohort) when = state.cohort.label;
    else if (p && state.slot) {
      const d = RWSlots.fmt(state.slot.start, TZ, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
      when = p.lessons > 1 ? (p.type === "intensive" ? `Mon–Fri from ${d}` : `Weekly from ${d}`) : d;
    }
    $("#s-when").textContent = when;
    $("#s-child").textContent = state.details ? `${state.details.child_name}, ${state.details.child_age}` + (state.details.child2_name ? ` & ${state.details.child2_name}` : "") : "—";
  }

  // ---------- Step 1: products ----------
  async function loadData() {
    const [pr, sc] = await Promise.all([fetch("/data/programmes.json").then((r) => r.json()), fetch("/data/schedule.json").then((r) => r.json())]);
    state.products = pr.products; state.schedule = sc;
    const list = $("#product-list");
    list.innerHTML = state.products.map((p) => `
      <label class="choice" data-id="${p.id}"><input type="radio" name="product" value="${p.id}">
        <span class="p">${money(p.price)}</span><b>${p.name}</b><span class="s">${p.short}</span>
        ${p.badge ? `<span class="badge" style="margin-top:8px">${p.badge}</span>` : ""}
      </label>`).join("");
    list.addEventListener("change", (e) => selectProduct(e.target.value));
    const pre = new URLSearchParams(location.search).get("product");
    if (pre && state.products.some((p) => p.id === pre)) { $(`input[value="${pre}"]`).checked = true; selectProduct(pre); }
  }
  function selectProduct(id) {
    state.product = state.products.find((p) => p.id === id); state.slot = null; state.cohort = null;
    $$(".choice").forEach((c) => c.classList.toggle("selected", c.dataset.id === id));
    $("#to-step-2").disabled = false;
    $("#second-swimmer").style.display = state.product.swimmers === 2 ? "" : "none";
    updateSummary();
  }
  $("#to-step-2").addEventListener("click", () => { go(2); loadTimes(); });

  // ---------- Step 2: times ----------
  async function loadTimes() {
    const p = state.product, box = $("#time-picker");
    $("#to-step-3").disabled = true; clearAlert();
    $("#time-heading").textContent = p.type === "programme" ? "Choose a programme group" : p.type === "intensive" ? "Choose a holiday week and start time" : p.lessons > 1 ? "Choose your weekly slot" : "Pick a time";
    $("#time-help").textContent = p.type === "programme" ? "Groups run for 8 weeks at the same time each week. Max 4 swimmers." : p.type === "intensive" ? "Five consecutive days, Monday to Friday, at the same time each day." : p.lessons > 1 ? `This becomes your slot every week for ${p.lessons} weeks. Your first lesson is the date shown.` : "Times shown are available in Ruby's calendar right now.";

    if (p.type === "programme") {
      const cohorts = (state.schedule.programmeCohorts || []).filter((c) => c.productId === p.id);
      box.innerHTML = cohorts.length ? `<div class="choice-grid">${cohorts.map((c, i) => `<label class="choice" data-i="${i}"><input type="radio" name="cohort" value="${i}"><b>${c.label}</b><span class="s">${c.spaces} spaces · 8 weeks · 45 min</span></label>`).join("")}</div>` : `<p>No groups scheduled yet. <a href="/contact.html#waitlist">Join the waiting list</a> and we'll tell you first.</p>`;
      box.onchange = (e) => { state.cohort = cohorts[+e.target.value]; state.slot = { start: RWSlots.atLocal(state.cohort.start, state.cohort.time, TZ).toISOString() }; $$(".choice", box).forEach((c) => c.classList.toggle("selected", c.dataset.i === e.target.value)); $("#to-step-3").disabled = false; updateSummary(); };
      return;
    }
    if (p.type === "intensive") {
      const weeks = state.schedule.intensiveWeeks || [];
      box.innerHTML = weeks.map((w, wi) => `<h3 style="margin-top:14px">${w.label}</h3><div class="slots">${w.times.map((t) => `<button type="button" class="slot" data-start="${RWSlots.atLocal(w.start, t, TZ).toISOString()}">${t}<small>daily</small></button>`).join("")}</div>`).join("") || `<p>No intensive weeks scheduled yet. <a href="/contact.html">Ask us</a>.</p>`;
      wireSlots(box); return;
    }
    // singles, tasters, blocks: live availability
    let slots = [], demo = false;
    try {
      const r = await fetch(`/api/availability?product=${encodeURIComponent(p.id)}`);
      if (!r.ok) throw new Error(r.status);
      const j = await r.json(); slots = j.slots; demo = !!j.demo;
    } catch (e) {
      slots = RWSlots.generateSlots(state.schedule, p); demo = true;
    }
    state.demo = demo;
    if (demo) showAlert("warn", "<strong>Preview mode.</strong> These are Ruby's standard teaching hours. Live availability appears once the calendar is connected (see the README).");
    if (!slots.length) { box.innerHTML = `<p>No slots in the next few weeks. <a href="/contact.html#waitlist">Join the waiting list</a>.</p>`; return; }
    const byDay = {};
    slots.forEach((s) => { const k = RWSlots.ymd(s.start, TZ); (byDay[k] = byDay[k] || []).push(s); });
    const days = Object.keys(byDay);
    box.innerHTML = `<div class="day-tabs">${days.map((d, i) => `<button type="button" class="day-tab${i === 0 ? " active" : ""}" data-day="${d}">${RWSlots.fmt(byDay[d][0].start, TZ, { weekday: "short", day: "numeric", month: "short" })}</button>`).join("")}</div><div class="slots" id="day-slots"></div>`;
    const render = (d) => { $("#day-slots").innerHTML = byDay[d].map((s) => `<button type="button" class="slot" data-start="${s.start}">${RWSlots.fmt(s.start, TZ, { hour: "2-digit", minute: "2-digit" })}<small>${p.duration} min</small></button>`).join(""); wireSlots(box); };
    $$(".day-tab", box).forEach((t) => t.addEventListener("click", () => { $$(".day-tab", box).forEach((x) => x.classList.remove("active")); t.classList.add("active"); render(t.dataset.day); }));
    render(days[0]);
  }
  function wireSlots(box) {
    $$(".slot", box).forEach((b) => b.addEventListener("click", () => {
      $$(".slot", box).forEach((x) => x.classList.remove("selected")); b.classList.add("selected");
      state.slot = { start: b.dataset.start }; state.cohort = null; $("#to-step-3").disabled = false; updateSummary();
    }));
  }
  $("#to-step-3").addEventListener("click", () => go(3));

  // ---------- Step 3: details ----------
  $("#details-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target;
    if (!f.checkValidity()) { f.reportValidity(); return; }
    state.details = Object.fromEntries(new FormData(f).entries());
    updateSummary(); renderReview(); go(4);
  });

  // ---------- Step 4: review + pay ----------
  function renderReview() {
    const p = state.product, d = state.details;
    const occ = state.cohort ? RWSlots.occurrences(state.schedule, p, state.slot.start) : RWSlots.occurrences(state.schedule, p, state.slot.start);
    const dates = occ.map((o) => RWSlots.fmt(o.start, TZ, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }));
    $("#review").innerHTML = `
      <h3>${p.name} · ${money(p.price)}</h3>
      <p class="muted">${p.short}</p>
      <p><strong>${occ.length === 1 ? "Date" : occ.length + " lessons"}:</strong> ${dates.length > 3 ? dates.slice(0, 3).join(" · ") + ` · and ${dates.length - 3} more` : dates.join(" · ")}</p>
      <p><strong>Swimmer:</strong> ${d.child_name}, ${d.child_age} (${d.ability})${d.child2_name ? ` and ${d.child2_name}, ${d.child2_age}` : ""}</p>
      <p><strong>Parent:</strong> ${d.parent_name} · ${d.email} · ${d.phone}</p>
      ${d.medical ? `<p><strong>Notes for Ruby:</strong> ${d.medical}</p>` : ""}
      <p class="small muted">Photo consent: ${d.photo_consent ? "yes" : "no"} · Venue confirmed by email · ${p.price ? "Card payment via Stripe on the next screen." : "Nothing to pay."}</p>`;
    $("#confirm-btn").textContent = p.price ? `Pay ${money(p.price)} securely` : "Confirm free taster";
  }
  $("#confirm-btn").addEventListener("click", async () => {
    const btn = $("#confirm-btn"); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> One moment…'; clearAlert();
    const payload = { productId: state.product.id, start: state.slot.start, cohort: state.cohort ? state.cohort.label : null, ...state.details, photo_consent: !!state.details.photo_consent };
    try {
      const endpoint = state.product.price ? "/api/create-checkout" : "/api/book-taster";
      const r = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.error || `Server error ${r.status}`);
      if (j.url) location.href = j.url; else location.href = "/thanks/taster-confirmed.html";
    } catch (err) {
      const msg = /404|Failed to fetch|NetworkError/.test(err.message)
        ? `The booking system isn't connected yet (preview mode). Email <a href="mailto:hello@rwswimacademy.co.uk?subject=Booking%20request:%20${encodeURIComponent(state.product.name)}">hello@rwswimacademy.co.uk</a> and we'll book you in by hand.`
        : `Sorry, that didn't work: ${err.message}. Please try again or email hello@rwswimacademy.co.uk.`;
      showAlert("error", msg); btn.disabled = false; renderReview();
    }
  });

  loadData().catch(() => showAlert("error", "Couldn't load lessons. Please refresh, or email hello@rwswimacademy.co.uk."));
})();
