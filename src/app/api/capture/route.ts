import { NextResponse } from "next/server";
import { createLead, LeadInput } from "@/lib/leadService";

// Public lead-capture endpoint.
//
// This is the door that properinvestuk.co.uk forms, the website chatbot, and
// social campaigns post into. It accepts a lenient payload, coerces numeric
// fields, scores the lead, and drops it into the NEW column automatically.
//
// Example:
//   POST /api/capture
//   { "name": "Jane Doe", "email": "jane@x.com", "fundsAvailable": "50000",
//     "timeframe": "M3", "targetReturnPct": "10", "source": "CHATBOT" }
export async function POST(req: Request) {
  try {
    const raw = await req.json();

    const num = (v: unknown): number | null => {
      if (v == null || v === "") return null;
      const n = typeof v === "number" ? v : parseFloat(String(v).replace(/[^0-9.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };

    const input: LeadInput = {
      name: String(raw.name ?? "").trim(),
      email: raw.email ?? null,
      phone: raw.phone ?? null,
      company: raw.company ?? null,
      source: raw.source ?? "WEBSITE",
      fundsAvailable: num(raw.fundsAvailable),
      timeframe: raw.timeframe ?? null,
      chargeType: raw.chargeType ?? null,
      targetReturnPct: num(raw.targetReturnPct),
      experience: raw.experience ?? null,
      notes: raw.notes ?? null,
      stage: "NEW",
    };

    if (!input.name) {
      return NextResponse.json({ error: "A name is required." }, { status: 400 });
    }

    const lead = await createLead(input);
    return NextResponse.json(
      { ok: true, id: lead.id, score: lead.score, band: lead.scoreBand },
      { status: 201 },
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Capture failed.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
