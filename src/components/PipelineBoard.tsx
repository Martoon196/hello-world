"use client";

import { useEffect, useState, useCallback } from "react";
import { STAGES } from "@/lib/stages";
import { gbp, bandColor, SOURCE_LABELS } from "@/lib/format";
import LeadDrawer from "./LeadDrawer";

export interface Lead {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  source: string;
  fundsAvailable: number | null;
  timeframe: string | null;
  chargeType: string | null;
  targetReturnPct: number | null;
  experience: string | null;
  notes: string | null;
  stage: string;
  score: number;
  scoreBand: string;
  ownerName: string | null;
}

export default function PipelineBoard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch("/api/leads");
    const data = await res.json();
    setLeads(data.leads);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function moveLead(id: string, stage: string) {
    const prev = leads;
    // Optimistic update.
    setLeads((ls) => ls.map((l) => (l.id === id ? { ...l, stage } : l)));
    const res = await fetch(`/api/leads/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ stage }),
    });
    if (!res.ok) setLeads(prev); // rollback
  }

  const openLead = leads.find((l) => l.id === openId) || null;

  return (
    <div className="p-6 md:p-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Investor Pipeline</h1>
          <p className="text-slate-500 text-sm">Drag leads between stages. Scores recalculate automatically.</p>
        </div>
      </header>

      {loading ? (
        <div className="text-slate-400 text-sm">Loading pipeline…</div>
      ) : (
        <div className="flex gap-4 overflow-x-auto scroll-thin pb-4">
          {STAGES.map((stage) => {
            const items = leads.filter((l) => l.stage === stage.id);
            const capital = items.reduce((s, l) => s + (l.fundsAvailable ?? 0), 0);
            return (
              <div
                key={stage.id}
                onDragOver={(e) => {
                  e.preventDefault();
                  setOverStage(stage.id);
                }}
                onDragLeave={() => setOverStage((s) => (s === stage.id ? null : s))}
                onDrop={(e) => {
                  e.preventDefault();
                  setOverStage(null);
                  if (dragId) moveLead(dragId, stage.id);
                  setDragId(null);
                }}
                className={`w-72 shrink-0 rounded-xl bg-slate-100/70 ring-1 ring-slate-200 ${
                  overStage === stage.id ? "drop-target" : ""
                }`}
              >
                <div className="px-3 py-3 border-b border-slate-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${stage.accent}`} />
                    <span className="text-sm font-medium text-slate-700">{stage.label}</span>
                    <span className="text-xs text-slate-400">{items.length}</span>
                  </div>
                  <span className="text-[11px] text-slate-400">{gbp(capital)}</span>
                </div>

                <div className="p-2 space-y-2 min-h-[120px]">
                  {items.map((l) => (
                    <button
                      key={l.id}
                      draggable
                      onDragStart={() => setDragId(l.id)}
                      onDragEnd={() => setDragId(null)}
                      onClick={() => setOpenId(l.id)}
                      className={`w-full text-left rounded-lg bg-white p-3 ring-1 ring-slate-200 shadow-sm hover:ring-brand-300 transition cursor-grab active:cursor-grabbing ${
                        dragId === l.id ? "dragging" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-medium text-slate-800 text-sm">{l.name}</span>
                        <span className={`shrink-0 inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold ring-1 ${bandColor(l.scoreBand)}`}>
                          {l.score}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">{gbp(l.fundsAvailable)}</div>
                      <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                        <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                          {SOURCE_LABELS[l.source] ?? l.source}
                        </span>
                        {l.targetReturnPct != null && (
                          <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                            {l.targetReturnPct}% target
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                  {items.length === 0 && (
                    <div className="text-center text-[11px] text-slate-400 py-6">Drop leads here</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {openLead && (
        <LeadDrawer
          lead={openLead}
          onClose={() => setOpenId(null)}
          onChanged={load}
        />
      )}
    </div>
  );
}
