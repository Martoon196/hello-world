import { ScoreResult } from "./scoring";
import {
  TIMEFRAME_LABELS,
  CHARGE_LABELS,
  EXPERIENCE_LABELS,
  gbp,
} from "./format";

export interface AiLeadContext {
  name: string;
  fundsAvailable?: number | null;
  timeframe?: string | null;
  chargeType?: string | null;
  targetReturnPct?: number | null;
  experience?: string | null;
  notes?: string | null;
  score: ScoreResult;
}

export interface AiResult {
  source: "claude" | "fallback";
  summary: string;
  email: { subject: string; body: string };
}

// Claude model used when ANTHROPIC_API_KEY is present.
const MODEL = "claude-sonnet-4-6";

function profileLines(ctx: AiLeadContext): string {
  return [
    `Capital available: ${gbp(ctx.fundsAvailable)}`,
    `Timeframe: ${ctx.timeframe ? TIMEFRAME_LABELS[ctx.timeframe] ?? ctx.timeframe : "unknown"}`,
    `Security preference: ${ctx.chargeType ? CHARGE_LABELS[ctx.chargeType] ?? ctx.chargeType : "unknown"}`,
    `Target return: ${ctx.targetReturnPct != null ? ctx.targetReturnPct + "%" : "unknown"}`,
    `Experience: ${ctx.experience ? EXPERIENCE_LABELS[ctx.experience] ?? ctx.experience : "unknown"}`,
    ctx.notes ? `Notes: ${ctx.notes}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

// Deterministic, no-API qualification used when Claude is not configured.
function fallback(ctx: AiLeadContext): AiResult {
  const { band, score } = ctx.score;
  const top = [...ctx.score.factors].sort((a, b) => b.points - a.points)[0];
  const weak = [...ctx.score.factors].sort((a, b) => a.points / a.weight - b.points / b.weight)[0];

  const summary =
    `${ctx.name} scores ${score}/100 (${band}). ` +
    `Strongest signal: ${top.label.toLowerCase()} — ${top.rationale} ` +
    `Biggest gap: ${weak.label.toLowerCase()} — ${weak.rationale} ` +
    (band === "HOT"
      ? "Prioritise a call this week and present a live opportunity."
      : band === "WARM"
        ? "Nurture with a tailored opportunity and confirm timeframe."
        : "Keep on a longer nurture sequence until funds/timeframe firm up.");

  const subject =
    band === "HOT"
      ? `${ctx.name.split(" ")[0]}, a property opportunity matched to you`
      : `${ctx.name.split(" ")[0]}, your property investment options`;

  const body =
    `Hi ${ctx.name.split(" ")[0]},\n\n` +
    `Thanks for your interest in investing with ProperInvest UK. Based on what you've shared` +
    (ctx.fundsAvailable ? ` (around ${gbp(ctx.fundsAvailable)} to deploy${ctx.timeframe ? `, ${TIMEFRAME_LABELS[ctx.timeframe]?.toLowerCase()}` : ""})` : "") +
    `, I'd love to walk you through how our secured property deals work and the returns our investors typically see.\n\n` +
    `Would you be open to a short call this week? I can tailor a couple of live opportunities to your goals.\n\n` +
    `Best regards,\nThe ProperInvest UK Team`;

  return { source: "fallback", summary, email: { subject, body } };
}

// Generate a qualification summary + follow-up email draft for a lead.
// Uses Claude when ANTHROPIC_API_KEY is set; otherwise returns a solid
// template-based result so the feature always works.
export async function qualifyLead(ctx: AiLeadContext): Promise<AiResult> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return fallback(ctx);

  const prompt =
    `You are an SDR for ProperInvest UK, a property investment firm that places investor capital into ` +
    `secured property deals (lease options, purchase lease options, payment agreements). ` +
    `Here is an investor lead and our internal score:\n\n` +
    `Name: ${ctx.name}\nInternal score: ${ctx.score.score}/100 (${ctx.score.band})\n${profileLines(ctx)}\n\n` +
    `Respond ONLY with JSON of the form ` +
    `{"summary": string (2-3 sentence qualification + recommended next action), ` +
    `"email": {"subject": string, "body": string (warm, concise UK-English follow-up, no markdown)}}.`;

  try {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1024,
        messages: [{ role: "user", content: prompt }],
      }),
    });
    if (!res.ok) return fallback(ctx);
    const data = await res.json();
    const text: string = data?.content?.[0]?.text ?? "";
    const json = JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
    if (json?.summary && json?.email?.subject && json?.email?.body) {
      return { source: "claude", summary: json.summary, email: json.email };
    }
    return fallback(ctx);
  } catch {
    return fallback(ctx);
  }
}
