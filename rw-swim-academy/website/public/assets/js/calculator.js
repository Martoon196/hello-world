(function () {
  const $ = (s) => document.querySelector(s);
  const n = (id) => parseFloat($("#" + id).value) || 0;
  const gbp = (x) => "£" + x.toLocaleString("en-GB", { maximumFractionDigits: 0 });
  function calc() {
    const lane = n("laneHire"), pct = n("stripePct") / 100, fix = n("stripeFix") / 100, occ = n("occ") / 100;
    const types = [
      { name: "Private 1:1 (30 min)", mins: 30, revenue: 32.5, count: n("n11") },
      { name: "Semi-private 2:1 (30 min)", mins: 30, revenue: 45, count: n("n21") },
      { name: "Programme group (45 min, 4 places)", mins: 45, revenue: 80 * occ, count: n("ngrp") },
      { name: "Stroke clinic (60 min)", mins: 60, revenue: 55, count: n("nclin") },
      { name: "Free taster (25 min)", mins: 25, revenue: 0, count: n("ntaster") },
    ];
    let rows = "<tr><th>Session</th><th>Revenue</th><th>Lane</th><th>Fees</th><th>Contribution</th></tr>", wkRev = 0, wkCost = 0, wkHours = 0;
    types.forEach((t) => {
      const laneCost = lane * t.mins / 60, fees = t.revenue ? t.revenue * pct + fix : 0, c = t.revenue - laneCost - fees;
      rows += `<tr><td>${t.name}</td><td>${gbp(t.revenue)}</td><td>${gbp(laneCost)}</td><td>£${fees.toFixed(2)}</td><td style="color:${c >= 0 ? "#1E9E6A" : "#C0392B"};font-weight:700">${gbp(c)}</td></tr>`;
      wkRev += t.revenue * t.count; wkCost += (laneCost + fees) * t.count; wkHours += t.mins * t.count / 60;
    });
    $("#perSession").innerHTML = rows;
    const fixedWk = n("insurance") / 52 + n("admin") * 12 / 52;
    const wkContribution = wkRev - wkCost - fixedWk;
    $("#week").innerHTML = `<dt>Coaching hours</dt><dd>${wkHours.toFixed(1)}</dd><dt>Revenue</dt><dd>${gbp(wkRev)}</dd><dt>Lane + card fees</dt><dd>${gbp(wkCost)}</dd><dt>Fixed costs (share)</dt><dd>${gbp(fixedWk)}</dd><dt>Contribution</dt><dd><strong>${gbp(wkContribution)}</strong> (${wkRev ? Math.round(wkContribution / wkRev * 100) : 0}% margin)</dd>`;
    const w = n("weeks");
    $("#year").innerHTML = `<dt>Revenue</dt><dd>${gbp(wkRev * w)}</dd><dt>Contribution</dt><dd><strong>${gbp((wkRev - wkCost) * w - n("insurance") - n("admin") * 12)}</strong></dd><dt>Per coaching hour</dt><dd>${wkHours ? gbp(wkContribution / wkHours) : "—"}</dd>`;
  }
  document.querySelectorAll("input").forEach((i) => i.addEventListener("input", calc));
  calc();
})();
