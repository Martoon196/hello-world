import { NextResponse } from "next/server";
import { createLead, listLeads, LeadInput } from "@/lib/leadService";

export async function GET() {
  const leads = await listLeads();
  return NextResponse.json({ leads });
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as LeadInput;
    const lead = await createLead(body);
    return NextResponse.json({ lead }, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create lead.";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
