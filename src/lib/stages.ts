// The investor lead funnel. Order here defines left-to-right pipeline order.
// This mirrors a GoHighLevel-style pipeline where leads are dragged along stages.

export type StageId =
  | "NEW"
  | "CONTACTED"
  | "QUALIFYING"
  | "QUALIFIED"
  | "OFFER"
  | "COMMITTED"
  | "INVESTED"
  | "LOST";

export interface StageDef {
  id: StageId;
  label: string;
  description: string;
  // Tailwind classes for the column accent.
  accent: string;
  // Is this a "won"/"lost" terminal stage?
  terminal?: "won" | "lost";
}

export const STAGES: StageDef[] = [
  {
    id: "NEW",
    label: "New",
    description: "Just arrived — not yet contacted.",
    accent: "bg-slate-400",
  },
  {
    id: "CONTACTED",
    label: "Contacted",
    description: "First outreach made.",
    accent: "bg-sky-400",
  },
  {
    id: "QUALIFYING",
    label: "Qualifying",
    description: "Gathering funds / charge / return appetite.",
    accent: "bg-indigo-400",
  },
  {
    id: "QUALIFIED",
    label: "Qualified",
    description: "Profile complete and scored.",
    accent: "bg-violet-500",
  },
  {
    id: "OFFER",
    label: "Offer Out",
    description: "Specific opportunity presented.",
    accent: "bg-amber-500",
  },
  {
    id: "COMMITTED",
    label: "Committed",
    description: "Verbally / in principle agreed.",
    accent: "bg-orange-500",
  },
  {
    id: "INVESTED",
    label: "Invested",
    description: "Funds deployed — won.",
    accent: "bg-emerald-500",
    terminal: "won",
  },
  {
    id: "LOST",
    label: "Lost",
    description: "Not proceeding.",
    accent: "bg-rose-500",
    terminal: "lost",
  },
];

export const STAGE_IDS = STAGES.map((s) => s.id);

export function stageDef(id: string): StageDef | undefined {
  return STAGES.find((s) => s.id === id);
}

export function isValidStage(id: string): id is StageId {
  return STAGE_IDS.includes(id as StageId);
}
