import { analyseDeal } from "./analyse.js";
import { store } from "./store.js";

let chain = Promise.resolve();

/** Analyse deals one at a time in the background; the dashboard polls for status. */
export function enqueueAnalysis(dealId) {
  chain = chain.then(() => runAnalysis(dealId)).catch(() => {});
  return chain;
}

export async function runAnalysis(dealId) {
  const deal = store.get(dealId);
  if (!deal) return;
  store.update(dealId, { status: "analysing", error: null });
  try {
    const files = store.loadFiles(deal);
    const result = await analyseDeal({ notes: deal.notes, files, submitter: deal.submitter });
    store.update(dealId, {
      status: "done",
      analysis: { ...result, analysed_at: new Date().toISOString() },
    });
  } catch (err) {
    console.error(`[analysis] deal ${dealId} failed:`, err);
    store.update(dealId, { status: "failed", error: err.message || String(err) });
  }
}
