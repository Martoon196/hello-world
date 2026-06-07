import Link from "next/link";
import { prisma } from "@/lib/prisma";
import { STAGES } from "@/lib/stages";
import { gbp, gbpCompact, bandColor, SOURCE_LABELS, timeAgo } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const leads = await prisma.investorLead.findMany({
    orderBy: { createdAt: "desc" },
  });

  const open = leads.filter((l) => l.stage !== "LOST" && l.stage !== "INVESTED");
  const invested = leads.filter((l) => l.stage === "INVESTED");
  const totalCapital = open.reduce((s, l) => s + (l.fundsAvailable ?? 0), 0);
  const investedCapital = invested.reduce((s, l) => s + (l.fundsAvailable ?? 0), 0);
  const hot = leads.filter((l) => l.scoreBand === "HOT").length;
  const warm = leads.filter((l) => l.scoreBand === "WARM").length;
  const cold = leads.filter((l) => l.scoreBand === "COLD").length;

  const byStage = STAGES.map((s) => {
    const inStage = leads.filter((l) => l.stage === s.id);
    return {
      ...s,
      count: inStage.length,
      capital: inStage.reduce((sum, l) => sum + (l.fundsAvailable ?? 0), 0),
    };
  });
  const maxStageCount = Math.max(1, ...byStage.map((s) => s.count));

  const recent = leads.slice(0, 6);

  const kpis = [
    { label: "Open leads", value: open.length.toString(), sub: `${leads.length} total` },
    { label: "Capital in pipeline", value: gbpCompact(totalCapital), sub: "open leads only" },
    { label: "Hot leads", value: hot.toString(), sub: `${warm} warm · ${cold} cold` },
    { label: "Capital invested", value: gbpCompact(investedCapital), sub: `${invested.length} won` },
  ];

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Investor Dashboard</h1>
          <p className="text-slate-500 text-sm">Live view of investor leads and capital pipeline.</p>
        </div>
        <Link
          href="/pipeline"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Open pipeline →
        </Link>
      </header>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-xl bg-white p-5 ring-1 ring-slate-200 shadow-sm">
            <div className="text-xs uppercase tracking-wide text-slate-400">{k.label}</div>
            <div className="mt-2 text-3xl font-semibold text-slate-900">{k.value}</div>
            <div className="mt-1 text-xs text-slate-400">{k.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Funnel by stage */}
        <div className="lg:col-span-2 rounded-xl bg-white p-6 ring-1 ring-slate-200 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Pipeline by stage</h2>
          <div className="space-y-3">
            {byStage.map((s) => (
              <div key={s.id} className="flex items-center gap-3">
                <div className="w-28 text-sm text-slate-600 shrink-0">{s.label}</div>
                <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden">
                  <div
                    className={`${s.accent} h-6 rounded-full flex items-center justify-end pr-2`}
                    style={{ width: `${Math.max(6, (s.count / maxStageCount) * 100)}%` }}
                  >
                    <span className="text-[11px] font-medium text-white/90">{s.count}</span>
                  </div>
                </div>
                <div className="w-24 text-right text-xs text-slate-500 shrink-0">{gbpCompact(s.capital)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Score band breakdown */}
        <div className="rounded-xl bg-white p-6 ring-1 ring-slate-200 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Lead quality</h2>
          <div className="space-y-4">
            {[
              { band: "HOT", count: hot, note: "Prioritise now" },
              { band: "WARM", count: warm, note: "Nurture" },
              { band: "COLD", count: cold, note: "Long-term" },
            ].map((b) => (
              <div key={b.band} className="flex items-center justify-between">
                <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${bandColor(b.band)}`}>
                  {b.band}
                </span>
                <div className="text-right">
                  <div className="text-lg font-semibold text-slate-800">{b.count}</div>
                  <div className="text-[11px] text-slate-400">{b.note}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent leads */}
      <div className="mt-6 rounded-xl bg-white ring-1 ring-slate-200 shadow-sm overflow-hidden">
        <h2 className="text-sm font-semibold text-slate-700 px-6 py-4 border-b border-slate-100">
          Recent leads
        </h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-400 bg-slate-50">
              <th className="px-6 py-3 font-medium">Name</th>
              <th className="px-6 py-3 font-medium">Source</th>
              <th className="px-6 py-3 font-medium">Capital</th>
              <th className="px-6 py-3 font-medium">Score</th>
              <th className="px-6 py-3 font-medium">Stage</th>
              <th className="px-6 py-3 font-medium">Added</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {recent.map((l) => (
              <tr key={l.id} className="hover:bg-slate-50">
                <td className="px-6 py-3 font-medium text-slate-800">{l.name}</td>
                <td className="px-6 py-3 text-slate-500">{SOURCE_LABELS[l.source] ?? l.source}</td>
                <td className="px-6 py-3 text-slate-600">{gbp(l.fundsAvailable)}</td>
                <td className="px-6 py-3">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${bandColor(l.scoreBand)}`}>
                    {l.score} · {l.scoreBand}
                  </span>
                </td>
                <td className="px-6 py-3 text-slate-600">{l.stage}</td>
                <td className="px-6 py-3 text-slate-400 text-xs">{timeAgo(l.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
