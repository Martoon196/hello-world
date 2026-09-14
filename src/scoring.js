import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_MATRIX_PATH = path.join(here, "..", "config", "scoring-matrix.json");

export function loadMatrix(matrixPath = process.env.SCORING_MATRIX || DEFAULT_MATRIX_PATH) {
  return JSON.parse(fs.readFileSync(matrixPath, "utf8"));
}

const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const round = (v, dp = 1) => (v == null ? null : Math.round(v * 10 ** dp) / 10 ** dp);

/** Linear interpolation over [value, points] pairs, clamped at both ends. */
export function curvePoints(curve, value) {
  const pts = [...curve].sort((a, b) => a[0] - b[0]);
  if (value <= pts[0][0]) return pts[0][1];
  if (value >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1];
    const [x1, y1] = pts[i];
    if (value <= x1) return y0 + ((value - x0) / (x1 - x0)) * (y1 - y0);
  }
  return pts[pts.length - 1][1];
}

/** Work out the financial metrics we can from what the sourcer gave us. */
export function deriveFinancials(extraction, matrix) {
  const a = matrix.assumptions;
  const f = extraction.financials || {};
  const strategy = extraction.strategy || "other";
  const assumptions = [];

  const price = num(f.purchase_price) ?? num(f.asking_price);
  if (price != null && num(f.purchase_price) == null) {
    assumptions.push("No agreed price given, so the asking price is used as the purchase price.");
  }
  const mv = num(f.estimated_market_value);
  const refurb = num(f.refurb_cost) ?? 0;
  if (num(f.refurb_cost) == null) assumptions.push("No refurb cost stated; assumed £0.");

  let costs = num(f.other_purchase_costs);
  if (costs == null && price != null) {
    costs = price * a.purchase_costs_pct;
    assumptions.push(
      `Purchase costs not stated; assumed ${a.purchase_costs_pct * 100}% of price for SDLT, legals and fees.`
    );
  }
  costs = (costs ?? 0) + (num(f.sourcing_fee) ?? 0);

  const endValue = num(f.end_value) ?? mv;
  if (num(f.end_value) == null && mv != null) {
    assumptions.push("No end value / GDV stated; current market value used instead.");
  }

  const monthlyRent = num(f.monthly_rent);
  const annualRent = monthlyRent != null ? monthlyRent * 12 : null;
  const annualService = (num(f.monthly_service_charge_and_ground_rent) ?? 0) * 12;

  const d = {
    purchase_price: price,
    market_value: mv,
    refurb_cost: refurb,
    purchase_costs: price != null ? costs : null,
    total_cost: null,
    end_value: endValue,
    annual_rent: annualRent,
    gross_yield: null,
    discount_to_mv: null,
    profit_on_cost: null,
    gross_profit: null,
    cash_in: null,
    annual_net_income: null,
    roce: null,
    money_pulled_out: null,
    money_left_in: null,
    money_left_in_pct: null,
  };

  if (price != null) {
    d.total_cost = price + refurb + costs;
    if (annualRent != null && price > 0) d.gross_yield = (annualRent / price) * 100;
    if (mv != null && mv > 0) d.discount_to_mv = ((mv - price) / mv) * 100;

    if (endValue != null && d.total_cost > 0) {
      const netSale = endValue * (1 - a.selling_costs_pct);
      d.gross_profit = netSale - d.total_cost;
      d.profit_on_cost = (d.gross_profit / d.total_cost) * 100;
    }

    const ltv = strategy === "rent_to_rent" ? 0 : a.ltv;
    const mortgage = price * ltv;
    const deposit = price - mortgage;
    d.cash_in = deposit + refurb + costs;
    if (ltv > 0) {
      assumptions.push(
        `Mortgage assumed at ${ltv * 100}% LTV and ${(a.interest_rate * 100).toFixed(2)}% interest.`
      );
    }

    if (annualRent != null && d.cash_in > 0) {
      const opexPct = a.opex_pct[strategy] ?? a.opex_pct.default;
      const opex = annualRent * opexPct;
      d.annual_net_income = annualRent - opex - annualService - mortgage * a.interest_rate;
      d.roce = (d.annual_net_income / d.cash_in) * 100;
      assumptions.push(`Running costs assumed at ${opexPct * 100}% of rent.`);
    }

    if (ltv > 0 && endValue != null && d.cash_in > 0) {
      const refiLoan = endValue * ltv;
      d.money_pulled_out = refiLoan - mortgage;
      d.money_left_in = d.cash_in - d.money_pulled_out;
      d.money_left_in_pct = clamp((d.money_left_in / d.cash_in) * 100, 0, 200);
    }
  }

  for (const k of Object.keys(d)) d[k] = round(d[k], 1);
  return { derived: d, assumptions };
}

/** Score a deal extraction against the matrix. Pure function, no I/O. */
export function scoreDeal(extraction, matrix = loadMatrix()) {
  const strategy = matrix.strategies[extraction.strategy] ? extraction.strategy : "other";
  const weights = matrix.strategies[strategy];
  const { derived, assumptions } = deriveFinancials(extraction, matrix);
  const q = extraction.qualitative || {};

  const rows = [];
  let weightedSum = 0;
  let weightTotal = 0;
  const missing = [];

  for (const [key, weight] of Object.entries(weights)) {
    const def = matrix.metrics[key];
    if (!def) continue;
    let value = null;
    let points = null;
    if (def.source === "derived") {
      value = num(derived[key]);
      if (value != null) points = curvePoints(def.curve, value);
    } else {
      const raw = num(q[key]);
      if (raw != null) {
        value = clamp(Math.round(raw), 1, 10);
        const pct = ((value - 1) / 9) * 100;
        points = def.direction === "lower" ? 100 - pct : pct;
      }
    }
    const available = points != null;
    if (available) {
      weightedSum += weight * points;
      weightTotal += weight;
    } else {
      missing.push(def.label);
    }
    rows.push({
      key,
      label: def.label,
      source: def.source,
      unit: def.unit || (def.source === "qualitative" ? "/10" : ""),
      value: value == null ? null : round(value, 1),
      points: points == null ? null : Math.round(points),
      weight,
      available,
    });
  }

  const coverage = weightTotal / Object.values(weights).reduce((s, w) => s + w, 0);
  let score = weightTotal > 0 ? weightedSum / weightTotal : 0;
  // If a lot of the matrix is unanswerable, the score cannot be trusted; pull it down.
  if (coverage < 0.6) score = score * (0.5 + coverage / 1.2);
  score = Math.round(clamp(score, 0, 100));

  const band = [...matrix.ratings].sort((a, b) => b.min - a.min).find((r) => score >= r.min);

  return {
    matrix_version: matrix.version,
    strategy,
    score,
    rating: band?.rating ?? "red",
    label: band?.label ?? "Pass",
    coverage: Math.round(coverage * 100),
    metrics: rows,
    missing_metrics: missing,
    derived,
    assumptions,
  };
}
