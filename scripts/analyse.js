#!/usr/bin/env node
// Quick local run: node scripts/analyse.js [--notes "text"] [file.pdf ...]
import fs from "node:fs";
import path from "node:path";
import { analyseDeal } from "../src/analyse.js";

const args = process.argv.slice(2);
let notes = "";
const files = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--notes") notes = args[++i] || "";
  else if (args[i] === "--notes-file") notes = fs.readFileSync(args[++i], "utf8");
  else files.push(args[i]);
}

const MIME = {
  ".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
  ".webp": "image/webp", ".gif": "image/gif", ".txt": "text/plain", ".csv": "text/csv", ".md": "text/markdown",
};

const uploads = files.map((p) => ({
  originalname: path.basename(p),
  mimetype: MIME[path.extname(p).toLowerCase()] || "application/octet-stream",
  buffer: fs.readFileSync(p),
}));

const result = await analyseDeal({ notes, files: uploads });
const { extraction: e, scoring: s } = result;

console.log(`\n${e.headline}`);
console.log(`Score: ${s.score}/100  ${s.label.toUpperCase()}  (${s.strategy}, coverage ${s.coverage}%)\n`);
console.log(e.summary, "\n");
console.log("Metrics:");
for (const m of s.metrics) {
  const v = m.available ? `${m.value}${m.unit}` : "n/a";
  console.log(`  ${m.label.padEnd(32)} ${String(v).padEnd(14)} ${m.available ? m.points + " pts" : ""}  (w ${m.weight})`);
}
if (e.red_flags.length) console.log("\nRed flags:\n  - " + e.red_flags.join("\n  - "));
if (e.questions_for_sourcer.length) console.log("\nAsk the sourcer:\n  - " + e.questions_for_sourcer.join("\n  - "));
console.log("\nVerdict:", e.verdict);
if (result.usage) console.log("\nTokens:", result.usage.input_tokens, "in /", result.usage.output_tokens, "out");
if (args.includes("--json")) console.log(JSON.stringify(result, null, 2));
