import { prisma } from "./prisma";
import { scoreLead } from "./scoring";
import { isValidStage } from "./stages";

export interface LeadInput {
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  source?: string | null;
  fundsAvailable?: number | null;
  timeframe?: string | null;
  chargeType?: string | null;
  targetReturnPct?: number | null;
  experience?: string | null;
  notes?: string | null;
  ownerName?: string | null;
  stage?: string | null;
}

// Create a lead, score it, and log its opening activity entries.
export async function createLead(input: LeadInput) {
  if (!input.name || !input.name.trim()) {
    throw new Error("A name is required.");
  }
  const { score, band } = scoreLead(input);
  const stage = input.stage && isValidStage(input.stage) ? input.stage : "NEW";

  // Place new leads at the top of their column.
  const minPos = await prisma.investorLead.aggregate({
    where: { stage },
    _min: { position: true },
  });
  const position = (minPos._min.position ?? 0) - 1;

  return prisma.investorLead.create({
    data: {
      name: input.name.trim(),
      email: input.email ?? null,
      phone: input.phone ?? null,
      company: input.company ?? null,
      source: input.source || "WEBSITE",
      fundsAvailable: input.fundsAvailable ?? null,
      timeframe: input.timeframe ?? null,
      chargeType: input.chargeType ?? null,
      targetReturnPct: input.targetReturnPct ?? null,
      experience: input.experience ?? null,
      notes: input.notes ?? null,
      ownerName: input.ownerName ?? null,
      stage,
      score,
      scoreBand: band,
      position,
      activities: {
        create: [
          { type: "CREATED", summary: `Lead captured from ${(input.source || "website").toLowerCase()}`, actor: "system" },
          { type: "SCORE", summary: `Scored ${score}/100 (${band})`, actor: "system" },
        ],
      },
    },
    include: { activities: true },
  });
}

// Update a lead. Re-scores when profile fields change and logs activity for
// stage changes so the timeline stays accurate.
export async function updateLead(id: string, input: Partial<LeadInput> & { position?: number }) {
  const existing = await prisma.investorLead.findUnique({ where: { id } });
  if (!existing) throw new Error("Lead not found.");

  const merged = {
    fundsAvailable: input.fundsAvailable ?? existing.fundsAvailable,
    timeframe: input.timeframe ?? existing.timeframe,
    chargeType: input.chargeType ?? existing.chargeType,
    targetReturnPct: input.targetReturnPct ?? existing.targetReturnPct,
    experience: input.experience ?? existing.experience,
  };
  const { score, band } = scoreLead(merged);

  const stageChanged =
    input.stage && isValidStage(input.stage) && input.stage !== existing.stage;

  const activityCreates: { type: string; summary: string; actor: string }[] = [];
  if (stageChanged) {
    activityCreates.push({
      type: "STAGE_CHANGE",
      summary: `Moved ${existing.stage} → ${input.stage}`,
      actor: input.ownerName || "user",
    });
  }

  const data: Record<string, unknown> = {
    score,
    scoreBand: band,
  };
  for (const key of [
    "name",
    "email",
    "phone",
    "company",
    "source",
    "fundsAvailable",
    "timeframe",
    "chargeType",
    "targetReturnPct",
    "experience",
    "notes",
    "ownerName",
    "position",
  ] as const) {
    if (input[key] !== undefined) data[key] = input[key];
  }
  if (stageChanged) data.stage = input.stage;
  if (activityCreates.length) data.activities = { create: activityCreates };

  return prisma.investorLead.update({
    where: { id },
    data,
    include: { activities: { orderBy: { createdAt: "desc" } } },
  });
}

export async function listLeads() {
  return prisma.investorLead.findMany({
    orderBy: [{ position: "asc" }, { createdAt: "desc" }],
  });
}

export async function getLead(id: string) {
  return prisma.investorLead.findUnique({
    where: { id },
    include: { activities: { orderBy: { createdAt: "desc" } } },
  });
}
