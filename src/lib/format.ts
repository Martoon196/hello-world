// Shared display helpers and label maps used across the UI.

export function gbp(value?: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  }).format(value);
}

export function gbpCompact(value?: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export const TIMEFRAME_LABELS: Record<string, string> = {
  IMMEDIATE: "Immediately",
  M3: "Within 3 months",
  M6: "Within 6 months",
  M12: "Within 12 months",
  UNKNOWN: "Unknown",
};

export const CHARGE_LABELS: Record<string, string> = {
  FIRST: "First charge",
  SECOND: "Second charge",
  EQUITY: "Equity share",
  FLEXIBLE: "Flexible",
};

export const EXPERIENCE_LABELS: Record<string, string> = {
  NONE: "New investor",
  SOME: "Some experience",
  EXPERIENCED: "Experienced",
};

export const SOURCE_LABELS: Record<string, string> = {
  WEBSITE: "Website",
  CHATBOT: "Website chatbot",
  SOCIAL: "Social media",
  REFERRAL: "Referral",
  EVENT: "Event",
  PORTAL: "Portal",
};

export function bandColor(band: string): string {
  switch (band) {
    case "HOT":
      return "bg-rose-100 text-rose-700 ring-rose-200";
    case "WARM":
      return "bg-amber-100 text-amber-700 ring-amber-200";
    default:
      return "bg-slate-100 text-slate-600 ring-slate-200";
  }
}

export function timeAgo(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return d.toLocaleDateString("en-GB");
}
