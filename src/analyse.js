import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { DealExtraction } from "./schema.js";
import { scoreDeal, loadMatrix } from "./scoring.js";

const here = path.dirname(fileURLToPath(import.meta.url));

export const MODEL = process.env.ANTHROPIC_MODEL || "claude-opus-5";

const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/gif", "image/webp"]);
const TEXT_TYPES = new Set(["text/plain", "text/csv", "text/markdown", "application/json"]);
const TEXT_EXT = /\.(txt|csv|md|json|eml)$/i;

export const ACCEPTED_TYPES_HELP =
  "PDF, JPG, PNG, WebP, GIF or plain text / CSV. Word and Excel files: export to PDF first.";

const SYSTEM_PROMPT = `You are the acquisitions analyst for Prop Invest UK, a UK property investment business.
Deal sourcers, agents and contacts send in "deal sheets" by WhatsApp, text, email and PDF. Your job is to read one
submission and turn it into a structured, honest assessment for the investor who owns the business.

How to work:
- Extract only what the material actually says. Never invent an address, price, rent or value. If something is not
  stated, return null and list it under missing_information.
- All money is GBP. Convert weekly or per-room rents into a total monthly figure and say so in the summary.
- Sourcers are salespeople. Treat claimed values, rents and refurb budgets with professional scepticism, and use
  numbers_credibility to say how realistic they look for the area and property type described.
- Red flags are specific and evidenced ("Refurb budget of £8k for a full rewire, kitchen and bathroom is unrealistic"),
  not generic ("do due diligence").
- Questions for the sourcer should be the exact questions the investor would send back in a reply.
- Write in plain UK English. Be direct. The investor is experienced and does not need basics explained.`;

/** Convert uploaded files + notes into Claude content blocks. */
export function buildContent({ notes, files = [], submitter = {} }) {
  const content = [];
  const unsupported = [];

  for (const f of files) {
    const name = f.originalname || "attachment";
    const type = (f.mimetype || "").toLowerCase();
    if (type === "application/pdf") {
      content.push({
        type: "document",
        source: { type: "base64", media_type: "application/pdf", data: f.buffer.toString("base64") },
        title: name,
      });
    } else if (IMAGE_TYPES.has(type)) {
      content.push({
        type: "image",
        source: { type: "base64", media_type: type, data: f.buffer.toString("base64") },
      });
    } else if (TEXT_TYPES.has(type) || TEXT_EXT.test(name)) {
      content.push({ type: "text", text: `--- Attached file: ${name} ---\n${f.buffer.toString("utf8")}` });
    } else {
      unsupported.push(name);
    }
  }

  const lines = ["<submission>"];
  if (submitter.name || submitter.contact) {
    lines.push(`Sent in by: ${submitter.name || "unknown"}${submitter.contact ? ` (${submitter.contact})` : ""}`);
  }
  if (submitter.headline) lines.push(`Their headline: ${submitter.headline}`);
  lines.push("");
  lines.push(notes && notes.trim() ? notes.trim() : "(No written notes - see attachments.)");
  lines.push("</submission>");
  lines.push("");
  lines.push(
    "Read the submission and every attachment above, then return the structured deal assessment."
  );
  content.push({ type: "text", text: lines.join("\n") });

  return { content, unsupported };
}

function mockExtraction() {
  const p = path.join(here, "..", "test", "fixtures", "mock-extraction.json");
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

/**
 * Run a deal sheet through Claude and the scoring matrix.
 * Returns { extraction, scoring, model, usage, unsupported_files }.
 */
export async function analyseDeal({ notes, files = [], submitter = {} }, opts = {}) {
  const matrix = opts.matrix || loadMatrix();
  const { content, unsupported } = buildContent({ notes, files, submitter });

  if (content.length === 1 && !(notes && notes.trim())) {
    throw new Error(
      `Nothing readable was submitted. Add some notes or attach a supported file (${ACCEPTED_TYPES_HELP})`
    );
  }

  let extraction;
  let usage = null;
  let model = MODEL;

  if (process.env.MOCK_ANALYSIS === "1") {
    extraction = mockExtraction();
    model = "mock";
    if (submitter.name) extraction.source.name = submitter.name;
  } else {
    const client = opts.client || new Anthropic();
    const response = await client.messages.parse({
      model: MODEL,
      max_tokens: 16000,
      system: [{ type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }],
      messages: [{ role: "user", content }],
      output_config: { format: zodOutputFormat(DealExtraction) },
    });

    if (response.stop_reason === "refusal") {
      throw new Error("The model declined to analyse this submission.");
    }
    if (!response.parsed_output) {
      throw new Error(`Could not parse the analysis (stop_reason: ${response.stop_reason}).`);
    }
    extraction = response.parsed_output;
    usage = response.usage;
    model = response.model;
  }

  const scoring = scoreDeal(extraction, matrix);
  return { extraction, scoring, model, usage, unsupported_files: unsupported };
}
