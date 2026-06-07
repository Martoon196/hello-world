// Investor lead scoring engine.
//
// Produces a 0–100 score from an investor's profile, plus a HOT/WARM/COLD band.
// The model is intentionally transparent and config-driven so the business can
// tune what "a good investor" means without touching app logic. This same
// pattern will be reused for Property Deal scoring (GDV/profit/availability).

export interface ScoreInput {
  fundsAvailable?: number | null;
  timeframe?: string | null;
  chargeType?: string | null;
  targetReturnPct?: number | null;
  experience?: string | null;
}

export interface ScoreFactor {
  key: string;
  label: string;
  weight: number; // contribution out of 100
  points: number; // 0..weight actually awarded
  rationale: string;
}

export interface ScoreResult {
  score: number; // 0–100
  band: "HOT" | "WARM" | "COLD";
  factors: ScoreFactor[];
}

// Weights sum to 100. Tune these to change what the business values most.
export const WEIGHTS = {
  funds: 35, // how much capital they can deploy
  timeframe: 25, // how soon they can deploy it
  targetReturn: 20, // realistic return expectation (lower = easier to satisfy)
  chargeFlex: 12, // flexibility on the security they require
  experience: 8, // experienced investors are smoother to work with
} as const;

// Capital scale: £250k+ available is treated as a maximum-strength signal.
const FUNDS_CEILING = 250_000;

function fundsPoints(funds?: number | null): { pts: number; why: string } {
  if (funds == null || funds <= 0)
    return { pts: 0, why: "No capital figure captured yet." };
  const ratio = Math.min(funds / FUNDS_CEILING, 1);
  // Mild curve so mid-size investors still score meaningfully.
  const pts = Math.round(WEIGHTS.funds * Math.sqrt(ratio));
  return {
    pts,
    why: `£${funds.toLocaleString("en-GB")} available (ceiling £${FUNDS_CEILING.toLocaleString("en-GB")}).`,
  };
}

const TIMEFRAME_SCORE: Record<string, number> = {
  IMMEDIATE: 1,
  M3: 0.8,
  M6: 0.55,
  M12: 0.3,
  UNKNOWN: 0.15,
};

function timeframePoints(tf?: string | null): { pts: number; why: string } {
  const key = (tf || "UNKNOWN").toUpperCase();
  const frac = TIMEFRAME_SCORE[key] ?? 0.15;
  return {
    pts: Math.round(WEIGHTS.timeframe * frac),
    why: `Deployment timeframe: ${key.toLowerCase()}.`,
  };
}

// Lower, realistic return expectations are better for the business margin.
// Sweet spot ~8%; expectations climbing toward 20%+ are penalised because
// they are harder (and costlier) to satisfy.
function targetReturnPoints(pct?: number | null): { pts: number; why: string } {
  if (pct == null)
    return { pts: Math.round(WEIGHTS.targetReturn * 0.5), why: "Return expectation unknown — neutral." };
  let frac: number;
  if (pct <= 8) frac = 1;
  else if (pct >= 20) frac = 0.15;
  else frac = 1 - ((pct - 8) / (20 - 8)) * 0.85;
  return {
    pts: Math.round(WEIGHTS.targetReturn * frac),
    why: `Targets ${pct}% return (lower = easier to satisfy).`,
  };
}

const CHARGE_SCORE: Record<string, number> = {
  FLEXIBLE: 1,
  SECOND: 0.8,
  EQUITY: 0.7,
  FIRST: 0.4,
};

function chargePoints(charge?: string | null): { pts: number; why: string } {
  const key = (charge || "").toUpperCase();
  const frac = CHARGE_SCORE[key] ?? 0.5;
  return {
    pts: Math.round(WEIGHTS.chargeFlex * frac),
    why: charge ? `Security preference: ${key.toLowerCase()}.` : "Security preference unknown.",
  };
}

const EXPERIENCE_SCORE: Record<string, number> = {
  EXPERIENCED: 1,
  SOME: 0.6,
  NONE: 0.25,
};

function experiencePoints(exp?: string | null): { pts: number; why: string } {
  const key = (exp || "").toUpperCase();
  const frac = EXPERIENCE_SCORE[key] ?? 0.4;
  return {
    pts: Math.round(WEIGHTS.experience * frac),
    why: exp ? `Experience: ${key.toLowerCase()}.` : "Experience unknown.",
  };
}

export function scoreLead(input: ScoreInput): ScoreResult {
  const f = fundsPoints(input.fundsAvailable);
  const t = timeframePoints(input.timeframe);
  const r = targetReturnPoints(input.targetReturnPct);
  const c = chargePoints(input.chargeType);
  const e = experiencePoints(input.experience);

  const factors: ScoreFactor[] = [
    { key: "funds", label: "Capital available", weight: WEIGHTS.funds, points: f.pts, rationale: f.why },
    { key: "timeframe", label: "Deployment timeframe", weight: WEIGHTS.timeframe, points: t.pts, rationale: t.why },
    { key: "targetReturn", label: "Return expectation", weight: WEIGHTS.targetReturn, points: r.pts, rationale: r.why },
    { key: "chargeFlex", label: "Security flexibility", weight: WEIGHTS.chargeFlex, points: c.pts, rationale: c.why },
    { key: "experience", label: "Experience", weight: WEIGHTS.experience, points: e.pts, rationale: e.why },
  ];

  const score = Math.max(0, Math.min(100, factors.reduce((sum, x) => sum + x.points, 0)));
  const band: ScoreResult["band"] = score >= 70 ? "HOT" : score >= 45 ? "WARM" : "COLD";

  return { score, band, factors };
}
