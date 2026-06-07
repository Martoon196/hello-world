import { NextResponse } from "next/server";
import { getLead } from "@/lib/leadService";
import { scoreLead } from "@/lib/scoring";
import { qualifyLead } from "@/lib/ai";
import { prisma } from "@/lib/prisma";

// POST /api/ai/qualify  { id }
// Generates an AI qualification summary + follow-up email draft for a lead and
// logs it to the lead's activity timeline.
export async function POST(req: Request) {
  try {
    const { id } = await req.json();
    const lead = await getLead(id);
    if (!lead) return NextResponse.json({ error: "Lead not found." }, { status: 404 });

    const score = scoreLead(lead);
    const result = await qualifyLead({
      name: lead.name,
      fundsAvailable: lead.fundsAvailable,
      timeframe: lead.timeframe,
      chargeType: lead.chargeType,
      targetReturnPct: lead.targetReturnPct,
      experience: lead.experience,
      notes: lead.notes,
      score,
    });

    await prisma.activity.create({
      data: {
        leadId: id,
        type: "AI",
        summary: `AI qualification (${result.source})`,
        detail: result.summary,
        actor: "ai",
      },
    });

    return NextResponse.json({ result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "AI qualification failed.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
