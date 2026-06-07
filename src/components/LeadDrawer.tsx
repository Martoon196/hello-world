"use client";

import { useState } from "react";
import { scoreLead } from "@/lib/scoring";
import { STAGES } from "@/lib/stages";
import {
  gbp,
  bandColor,
  SOURCE_LABELS,
  TIMEFRAME_LABELS,
  CHARGE_LABELS,
  EXPERIENCE_LABELS,
} from "@/lib/format";
import type { Lead } from "./PipelineBoard";

interface AiResult {
  source: string;
  summary: string;
  email: { subject: string; body: string };
}

export default function LeadDrawer({
  lead,
  onClose,
  onChanged,
}: {
  lead: Lead;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [ai, setAi] = useState<AiResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const breakdown = scoreLead(lead);

  async function setStage(stage: string) {
    await fetch(`/api/leads/${lead.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ stage }),
    });
    onChanged();
  }

  async function runAi() {
    setAiLoading(true);
    setAi(null);
    const res = await fetch("/api/ai/qualify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ id: lead.id }),
    });
    const data = await res.json();
    setAi(data.result ?? null);
    setAiLoading(false);
    onChanged();
  }

  const facts: [string, string][] = [
    ["Capital available", gbp(lead.fundsAvailable)],
    ["Timeframe", lead.timeframe ? TIMEFRAME_LABELS[lead.timeframe] ?? lead.timeframe : "—"],
    ["Security", lead.chargeType ? CHARGE_LABELS[lead.chargeType] ?? lead.chargeType : "—"],
    ["Target return", lead.targetReturnPct != null ? `${lead.targetReturnPct}%` : "—"],
    ["Experience", lead.experience ? EXPERIENCE_LABELS[lead.experience] ?? lead.experience : "—"],
    ["Source", SOURCE_LABELS[lead.source] ?? lead.source],
  ];

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white h-full shadow-xl overflow-y-auto scroll-thin">
        <div className="sticky top-0 bg-white border-b border-slate-100 px-6 py-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{lead.name}</h2>
            {lead.company && <div className="text-sm text-slate-500">{lead.company}</div>}
            <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
              {lead.email && <span>{lead.email}</span>}
              {lead.phone && <span>· {lead.phone}</span>}
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-xl leading-none">×</button>
        </div>

        <div className="p-6 space-y-6">
          {/* Score */}
          <div className="rounded-xl bg-slate-50 ring-1 ring-slate-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-slate-700">Lead score</span>
              <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${bandColor(breakdown.band)}`}>
                {breakdown.score}/100 · {breakdown.band}
              </span>
            </div>
            <div className="space-y-2">
              {breakdown.factors.map((f) => (
                <div key={f.key}>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{f.label}</span>
                    <span>{f.points}/{f.weight}</span>
                  </div>
                  <div className="mt-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div className="h-1.5 bg-brand-500 rounded-full" style={{ width: `${(f.points / f.weight) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Facts */}
          <div className="grid grid-cols-2 gap-3">
            {facts.map(([k, v]) => (
              <div key={k} className="rounded-lg ring-1 ring-slate-200 p-3">
                <div className="text-[11px] uppercase tracking-wide text-slate-400">{k}</div>
                <div className="text-sm text-slate-800 mt-0.5">{v}</div>
              </div>
            ))}
          </div>

          {lead.notes && (
            <div>
              <div className="text-xs font-medium text-slate-500 mb-1">Notes</div>
              <p className="text-sm text-slate-700">{lead.notes}</p>
            </div>
          )}

          {/* Stage mover */}
          <div>
            <div className="text-xs font-medium text-slate-500 mb-2">Move to stage</div>
            <div className="flex flex-wrap gap-1.5">
              {STAGES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setStage(s.id)}
                  className={`rounded-full px-3 py-1 text-xs ring-1 transition ${
                    s.id === lead.stage
                      ? "bg-brand-600 text-white ring-brand-600"
                      : "bg-white text-slate-600 ring-slate-200 hover:ring-brand-300"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* AI */}
          <div className="rounded-xl ring-1 ring-brand-200 bg-brand-50 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-brand-800">AI qualification</span>
              <button
                onClick={runAi}
                disabled={aiLoading}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {aiLoading ? "Thinking…" : ai ? "Regenerate" : "Qualify & draft email"}
              </button>
            </div>
            {ai ? (
              <div className="space-y-3">
                <p className="text-sm text-slate-700">{ai.summary}</p>
                <div className="rounded-lg bg-white ring-1 ring-slate-200 p-3">
                  <div className="text-xs font-semibold text-slate-700">{ai.email.subject}</div>
                  <pre className="mt-1 whitespace-pre-wrap font-sans text-xs text-slate-600">{ai.email.body}</pre>
                </div>
                <div className="text-[11px] text-brand-700/70">Generated by: {ai.source === "claude" ? "Claude" : "built-in scorer"}</div>
              </div>
            ) : (
              <p className="text-xs text-brand-700/70">
                Generate a qualification summary and a ready-to-send follow-up email tailored to this investor.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
