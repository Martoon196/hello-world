"use client";

import { useState } from "react";

const TIMEFRAMES = [
  ["IMMEDIATE", "Immediately"],
  ["M3", "Within 3 months"],
  ["M6", "Within 6 months"],
  ["M12", "Within 12 months"],
  ["UNKNOWN", "Not sure yet"],
];
const CHARGES = [
  ["FLEXIBLE", "Flexible / open"],
  ["FIRST", "First charge"],
  ["SECOND", "Second charge"],
  ["EQUITY", "Equity share"],
];
const EXPERIENCE = [
  ["NONE", "New to property"],
  ["SOME", "Some experience"],
  ["EXPERIENCED", "Experienced"],
];

export default function CapturePage() {
  const [form, setForm] = useState<Record<string, string>>({
    name: "",
    email: "",
    phone: "",
    fundsAvailable: "",
    timeframe: "IMMEDIATE",
    chargeType: "FLEXIBLE",
    targetReturnPct: "",
    experience: "SOME",
    notes: "",
  });
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");
  const [result, setResult] = useState<{ score: number; band: string } | null>(null);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("saving");
    const res = await fetch("/api/capture", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ...form, source: "WEBSITE" }),
    });
    if (res.ok) {
      const data = await res.json();
      setResult({ score: data.score, band: data.band });
      setStatus("done");
    } else {
      setStatus("error");
    }
  }

  const field = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none";
  const label = "block text-xs font-medium text-slate-600 mb-1";

  if (status === "done" && result) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-ink-900 to-brand-800">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
          <div className="text-4xl mb-3">✅</div>
          <h1 className="text-xl font-semibold text-slate-900">Thanks — you&apos;re in!</h1>
          <p className="text-slate-500 text-sm mt-2">
            One of the ProperInvest team will be in touch shortly with opportunities matched to your goals.
          </p>
          <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
            Internal score: <strong>{result.score}/100</strong> ({result.band})
          </div>
          <button
            onClick={() => { setStatus("idle"); setResult(null); }}
            className="mt-6 block w-full rounded-lg bg-brand-600 text-white py-2 text-sm font-medium hover:bg-brand-700"
          >
            Submit another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-ink-900 to-brand-800">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-lg">
        <div className="mb-6">
          <div className="text-brand-600 text-xs font-semibold uppercase tracking-wide">ProperInvest UK</div>
          <h1 className="text-2xl font-semibold text-slate-900 mt-1">Invest in property with us</h1>
          <p className="text-slate-500 text-sm mt-1">
            Tell us a little about your goals and we&apos;ll match you with secured opportunities.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className={label}>Full name *</label>
              <input required className={field} value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className={label}>Email</label>
              <input type="email" className={field} value={form.email} onChange={(e) => set("email", e.target.value)} />
            </div>
            <div>
              <label className={label}>Phone</label>
              <input className={field} value={form.phone} onChange={(e) => set("phone", e.target.value)} />
            </div>
            <div>
              <label className={label}>Capital available (£)</label>
              <input inputMode="numeric" className={field} value={form.fundsAvailable} onChange={(e) => set("fundsAvailable", e.target.value)} placeholder="50000" />
            </div>
            <div>
              <label className={label}>Target return (% p.a.)</label>
              <input inputMode="numeric" className={field} value={form.targetReturnPct} onChange={(e) => set("targetReturnPct", e.target.value)} placeholder="10" />
            </div>
            <div>
              <label className={label}>When can you invest?</label>
              <select className={field} value={form.timeframe} onChange={(e) => set("timeframe", e.target.value)}>
                {TIMEFRAMES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className={label}>Security preference</label>
              <select className={field} value={form.chargeType} onChange={(e) => set("chargeType", e.target.value)}>
                {CHARGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className={label}>Experience</label>
              <select className={field} value={form.experience} onChange={(e) => set("experience", e.target.value)}>
                {EXPERIENCE.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className={label}>Anything else?</label>
              <textarea className={field} rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
            </div>
          </div>

          {status === "error" && (
            <p className="text-sm text-rose-600">Something went wrong. Please check your details and try again.</p>
          )}

          <button
            type="submit"
            disabled={status === "saving"}
            className="w-full rounded-lg bg-brand-600 text-white py-2.5 text-sm font-semibold hover:bg-brand-700 disabled:opacity-50"
          >
            {status === "saving" ? "Submitting…" : "Request opportunities →"}
          </button>
          <p className="text-center text-[11px] text-slate-400">
            This form posts to <code>/api/capture</code> — the same endpoint your live site & chatbot will use.
          </p>
        </form>
      </div>
    </div>
  );
}
