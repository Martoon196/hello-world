const listEl = document.getElementById("list");
const detailEl = document.getElementById("detail");
let deals = [];
let labels = {};
let filter = "all";
let activeId = null;
let pollTimer = null;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const gbp = (n) => (n == null ? "—" : "£" + Math.round(n).toLocaleString("en-GB"));
const pct = (n) => (n == null ? "—" : `${n}%`);
const when = (iso) => new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (r.status === 401) { location.reload(); throw new Error("Login required"); }
  if (r.status === 204) return null;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function load() {
  const data = await api("api/deals");
  deals = data.deals; labels = data.strategy_labels;
  renderList();
  const pending = deals.some((d) => d.status === "queued" || d.status === "analysing");
  clearTimeout(pollTimer);
  if (pending) pollTimer = setTimeout(load, 4000);
  if (activeId) {
    const cur = deals.find((d) => d.id === activeId);
    if (cur && (cur.status === "done" || cur.status === "failed")) showDeal(activeId, false);
  }
}

function badge(d, big = false) {
  if (d.status === "done" && d.analysis) {
    return `<div class="badge ${d.analysis.scoring.rating}">${d.analysis.scoring.score}</div>`;
  }
  const t = d.status === "failed" ? "Failed" : d.status === "analysing" ? "Reading…" : "Queued";
  return `<div class="badge pending">${t}</div>`;
}

function renderList() {
  const rows = deals.filter((d) => filter === "all" || (d.reviewer_status || "new") === filter);
  if (!rows.length) { listEl.innerHTML = `<div class="empty">No deals here yet.</div>`; return; }
  listEl.innerHTML = rows.map((d) => {
    const a = d.analysis;
    const title = a?.extraction?.headline || d.submitter?.headline || (d.files?.length ? `${d.files.length} attachment(s)` : "Deal sheet");
    const meta = [d.submitter?.name, a ? labels[a.scoring.strategy] : null, when(d.created_at)].filter(Boolean).join(" · ");
    return `<div class="deal-row ${d.id === activeId ? "active" : ""}" data-id="${d.id}">${badge(d)}<div><div class="t">${esc(title)}</div><div class="m">${esc(meta)}</div></div></div>`;
  }).join("");
  listEl.querySelectorAll(".deal-row").forEach((el) => el.addEventListener("click", () => showDeal(el.dataset.id)));
}

function metricsTable(s) {
  return `<div style="overflow-x:auto"><table><thead><tr><th>Metric</th><th class="num">Value</th><th class="num">Points</th><th class="num">Weight</th><th style="width:120px"></th></tr></thead><tbody>` +
    s.metrics.map((m) => `<tr>
      <td>${esc(m.label)}${m.source === "qualitative" ? ' <span class="muted small">(Claude)</span>' : ""}</td>
      <td class="num">${m.available ? esc(m.value) + esc(m.unit) : '<span class="muted">n/a</span>'}</td>
      <td class="num">${m.available ? m.points : "—"}</td>
      <td class="num">${m.weight}</td>
      <td><div class="bar"><i style="width:${m.available ? m.points : 0}%"></i></div></td></tr>`).join("") +
    `</tbody></table></div>`;
}

function list(items) {
  return items?.length ? `<ul class="flags">${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="muted small">None noted.</p>`;
}

async function showDeal(id, scroll = true) {
  activeId = id;
  renderList();
  const d = await api(`api/deals/${id}`);
  const a = d.analysis;
  const rs = d.reviewer_status || "new";
  const head = `
    <div class="toolbar" style="margin:0 0 12px">
      <select id="rstatus">${["new", "shortlisted", "offered", "rejected"].map((s) => `<option value="${s}" ${s === rs ? "selected" : ""}>${s[0].toUpperCase() + s.slice(1)}</option>`).join("")}</select>
      <button class="ghost" id="rean">Re-analyse</button>
      <button class="ghost danger" id="del">Delete</button>
      <span class="muted small">Received ${when(d.created_at)}${a?.model ? ` · model ${esc(a.model)}` : ""}</span>
    </div>`;

  if (!a) {
    detailEl.innerHTML = `<div class="card">${head}
      <h2>${esc(d.submitter?.headline || "Deal sheet")}</h2>
      <p class="muted">${d.status === "failed" ? `Analysis failed: ${esc(d.error)}` : "Analysis in progress. This page refreshes itself."}</p>
      ${rawSection(d)}</div>`;
    wireButtons(d); return;
  }

  const e = a.extraction, s = a.scoring, f = e.financials, p = e.property, dv = s.derived;
  detailEl.innerHTML = `
    <div class="card">${head}
      <div class="hero">
        ${badge(d, true)}
        <div>
          <h2>${esc(e.headline)}</h2>
          <span class="pill ${s.rating}">${esc(s.label)}</span>
          <span class="pill grey">${esc(labels[s.strategy] || s.strategy)}</span>
          <span class="pill grey">${s.coverage}% of matrix answerable</span>
          <div class="muted small" style="margin-top:6px">${esc([p.address, p.postcode].filter(Boolean).join(", ") || "Address not given")}</div>
        </div>
      </div>
      <h3>Verdict</h3><p>${esc(e.verdict)}</p>
      <h3>Summary</h3><p>${esc(e.summary)}</p>
      ${a.unsupported_files?.length ? `<div class="notice err small">Not readable: ${esc(a.unsupported_files.join(", "))}. Ask for PDF or images.</div>` : ""}
    </div>

    <div class="grid2" style="margin-top:16px">
      <div class="card">
        <h2>The numbers as pitched</h2>
        <dl class="kv">
          <dt>Asking price</dt><dd>${gbp(f.asking_price)}</dd>
          <dt>Purchase price</dt><dd>${gbp(f.purchase_price)}</dd>
          <dt>Claimed value now</dt><dd>${gbp(f.estimated_market_value)}</dd>
          <dt>Refurb</dt><dd>${gbp(f.refurb_cost)}</dd>
          <dt>End value / GDV</dt><dd>${gbp(f.end_value)}</dd>
          <dt>Rent (pcm)</dt><dd>${gbp(f.monthly_rent)}${f.number_of_lettable_units ? ` across ${f.number_of_lettable_units} units` : ""}</dd>
          <dt>Sourcing fee</dt><dd>${gbp(f.sourcing_fee)}</dd>
          <dt>Exit</dt><dd>${esc(f.exit_strategy || "—")}</dd>
          <dt>Comparables</dt><dd>${f.comparables_provided ? "Provided" : '<span class="pill red">None provided</span>'}</dd>
        </dl>
        <h3>Property</h3>
        <dl class="kv">
          <dt>Type</dt><dd>${esc(p.property_type || "—")}${p.bedrooms ? `, ${p.bedrooms} bed` : ""}${p.bathrooms ? `, ${p.bathrooms} bath` : ""}</dd>
          <dt>Tenure</dt><dd>${esc(p.tenure)}${p.lease_years_remaining ? ` (${p.lease_years_remaining} yrs)` : ""}</dd>
          <dt>EPC</dt><dd>${esc(p.epc_rating || "—")}</dd>
          <dt>Condition</dt><dd>${esc(p.condition || "—")}</dd>
          <dt>Occupancy</dt><dd>${esc(p.current_occupancy || "—")}</dd>
        </dl>
      </div>
      <div class="card">
        <h2>Our working</h2>
        <dl class="kv">
          <dt>Total cost</dt><dd>${gbp(dv.total_cost)}</dd>
          <dt>Cash in</dt><dd>${gbp(dv.cash_in)}</dd>
          <dt>Gross yield</dt><dd>${pct(dv.gross_yield)}</dd>
          <dt>Discount to MV</dt><dd>${pct(dv.discount_to_mv)}</dd>
          <dt>Net income / yr</dt><dd>${gbp(dv.annual_net_income)}</dd>
          <dt>ROCE</dt><dd>${pct(dv.roce)}</dd>
          <dt>Profit on cost</dt><dd>${pct(dv.profit_on_cost)} (${gbp(dv.gross_profit)})</dd>
          <dt>Pulled out on refi</dt><dd>${gbp(dv.money_pulled_out)}</dd>
          <dt>Money left in</dt><dd>${gbp(dv.money_left_in)} (${pct(dv.money_left_in_pct)})</dd>
        </dl>
        <h3>Assumptions</h3>${list(s.assumptions)}
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h2>Score breakdown &middot; ${s.score}/100</h2>
      ${metricsTable(s)}
      ${s.missing_metrics.length ? `<p class="muted small">Could not score: ${esc(s.missing_metrics.join(", "))}. Score is scaled down when less than 60% of the matrix is answerable.</p>` : ""}
      <p class="muted small">${esc(e.qualitative.notes)}</p>
    </div>

    <div class="grid2" style="margin-top:16px">
      <div class="card"><h2>Red flags</h2>${list(e.red_flags)}<h3>Missing information</h3>${list(e.missing_information)}</div>
      <div class="card"><h2>Reply to ${esc(e.source.name || d.submitter?.name || "the sourcer")}</h2>${list(e.questions_for_sourcer)}
        <button class="ghost" id="copyq" style="margin-top:10px">Copy questions</button>
        <h3>Sourcer</h3>
        <dl class="kv">
          <dt>Name</dt><dd>${esc(e.source.name || d.submitter?.name || "—")}${e.source.company ? `, ${esc(e.source.company)}` : ""}</dd>
          <dt>Contact</dt><dd>${esc(d.submitter?.contact || e.source.contact || "—")}</dd>
          <dt>Urgency</dt><dd>${esc(e.source.deadline_or_urgency || "—")}</dd>
        </dl>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h2>Your notes</h2>
      <textarea id="rnotes" placeholder="Anything you want to remember about this one">${esc(d.reviewer_notes || "")}</textarea>
      <button class="ghost" id="savenotes" style="margin-top:8px">Save notes</button>
      ${rawSection(d)}
    </div>`;
  wireButtons(d, e);
  if (scroll && window.innerWidth < 900) detailEl.scrollIntoView({ behavior: "smooth" });
}

function rawSection(d) {
  const files = d.files?.length
    ? `<ul class="files">${d.files.map((f) => `<li><a href="api/deals/${d.id}/files/${encodeURIComponent(f.name)}" target="_blank">${esc(f.original)}</a><span class="muted">${(f.size / 1024).toFixed(0)} KB</span></li>`).join("")}</ul>`
    : `<p class="muted small">No attachments.</p>`;
  return `<h3>Attachments</h3>${files}<h3>As submitted</h3><pre class="raw">${esc(d.notes || "(no notes)")}</pre>`;
}

function wireButtons(d, e) {
  document.getElementById("rstatus").onchange = async (ev) => {
    await api(`api/deals/${d.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer_status: ev.target.value }) });
    load();
  };
  document.getElementById("rean").onclick = async () => { await api(`api/deals/${d.id}/reanalyse`, { method: "POST" }); load(); showDeal(d.id, false); };
  document.getElementById("del").onclick = async () => {
    if (!confirm("Delete this deal and its attachments?")) return;
    await api(`api/deals/${d.id}`, { method: "DELETE" });
    activeId = null; detailEl.innerHTML = `<div class="card"><div class="empty">Deleted.</div></div>`; load();
  };
  const sn = document.getElementById("savenotes");
  if (sn) sn.onclick = async () => {
    await api(`api/deals/${d.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer_notes: document.getElementById("rnotes").value }) });
    sn.textContent = "Saved"; setTimeout(() => (sn.textContent = "Save notes"), 1500);
  };
  const cq = document.getElementById("copyq");
  if (cq && e) cq.onclick = () => {
    navigator.clipboard.writeText(`Hi ${e.source.name || d.submitter?.name || ""},\n\nThanks for sending this over. A few questions before I can take it further:\n\n${e.questions_for_sourcer.map((q, i) => `${i + 1}. ${q}`).join("\n")}\n\nThanks`);
    cq.textContent = "Copied"; setTimeout(() => (cq.textContent = "Copy questions"), 1500);
  };
}

document.getElementById("filters").addEventListener("click", (ev) => {
  const b = ev.target.closest("button"); if (!b) return;
  filter = b.dataset.f;
  document.querySelectorAll("#filters button").forEach((x) => x.classList.toggle("on", x === b));
  renderList();
});
document.getElementById("refresh").addEventListener("click", (ev) => { ev.preventDefault(); load(); });
load().catch((err) => (listEl.innerHTML = `<div class="notice err">${esc(err.message)}</div>`));
