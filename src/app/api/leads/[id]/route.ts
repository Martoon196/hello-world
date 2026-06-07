import { NextResponse } from "next/server";
import { getLead, updateLead } from "@/lib/leadService";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const lead = await getLead(id);
  if (!lead) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ lead });
}

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const body = await req.json();
    const lead = await updateLead(id, body);
    return NextResponse.json({ lead });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to update lead.";
    const status = message === "Lead not found." ? 404 : 400;
    return NextResponse.json({ error: message }, { status });
  }
}
