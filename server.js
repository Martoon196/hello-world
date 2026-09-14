import express from "express";
import multer from "multer";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { store } from "./src/store.js";
import { enqueueAnalysis } from "./src/queue.js";
import { ACCEPTED_TYPES_HELP, MODEL } from "./src/analyse.js";
import { STRATEGY_LABELS } from "./src/schema.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const DASHBOARD_PASSWORD = process.env.DASHBOARD_PASSWORD || "";
const SUBMIT_TOKEN = process.env.SUBMIT_TOKEN || "";

if (!process.env.ANTHROPIC_API_KEY && process.env.MOCK_ANALYSIS !== "1") {
  console.warn("WARNING: ANTHROPIC_API_KEY is not set. Submissions will fail to analyse. Set MOCK_ANALYSIS=1 to test without a key.");
}
if (!DASHBOARD_PASSWORD) {
  console.warn("WARNING: DASHBOARD_PASSWORD is not set. The dashboard is open to anyone who can reach this server.");
}

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "1mb" }));

// --- auth for the review side ---------------------------------------------
function requireDashboardAuth(req, res, next) {
  if (!DASHBOARD_PASSWORD) return next();
  const header = req.headers.authorization || "";
  if (header.startsWith("Basic ")) {
    const [, pass] = Buffer.from(header.slice(6), "base64").toString().split(":");
    if (pass === DASHBOARD_PASSWORD) return next();
  }
  res.set("WWW-Authenticate", 'Basic realm="Deal dashboard", charset="UTF-8"');
  res.status(401).send("Login required");
}

// --- light rate limit on the public form -----------------------------------
const hits = new Map();
function rateLimit(req, res, next) {
  const key = req.ip;
  const now = Date.now();
  const recent = (hits.get(key) || []).filter((t) => now - t < 60 * 60 * 1000);
  if (recent.length >= 20) return res.status(429).json({ error: "Too many submissions, try again later." });
  recent.push(now);
  hits.set(key, recent);
  next();
}

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { files: 8, fileSize: 20 * 1024 * 1024 },
});

// --- public: submission -----------------------------------------------------
app.get("/api/config", (req, res) => {
  res.json({ accepted: ACCEPTED_TYPES_HELP, token_required: Boolean(SUBMIT_TOKEN), model: MODEL });
});

app.post("/api/deals", rateLimit, upload.array("files", 8), (req, res) => {
  if (SUBMIT_TOKEN && req.body.token !== SUBMIT_TOKEN && req.query.token !== SUBMIT_TOKEN) {
    return res.status(403).json({ error: "This form needs a valid link. Ask for the current one." });
  }
  const notes = String(req.body.notes || "").slice(0, 50000);
  const files = req.files || [];
  if (!notes.trim() && files.length === 0) {
    return res.status(400).json({ error: "Paste the deal details or attach a file." });
  }
  const submitter = {
    name: String(req.body.name || "").slice(0, 200),
    contact: String(req.body.contact || "").slice(0, 200),
    headline: String(req.body.headline || "").slice(0, 300),
  };
  const deal = store.create({ submitter, notes, files });
  enqueueAnalysis(deal.id);
  res.status(202).json({ id: deal.id, status: deal.status });
});

// --- private: review --------------------------------------------------------
app.get("/api/deals", requireDashboardAuth, (req, res) => {
  res.json({ deals: store.list(), strategy_labels: STRATEGY_LABELS });
});

app.get("/api/deals/:id", requireDashboardAuth, (req, res) => {
  const deal = store.get(req.params.id);
  if (!deal) return res.status(404).json({ error: "Not found" });
  res.json(deal);
});

app.post("/api/deals/:id/reanalyse", requireDashboardAuth, (req, res) => {
  const deal = store.get(req.params.id);
  if (!deal) return res.status(404).json({ error: "Not found" });
  store.update(deal.id, { status: "queued" });
  enqueueAnalysis(deal.id);
  res.status(202).json({ id: deal.id, status: "queued" });
});

app.patch("/api/deals/:id", requireDashboardAuth, (req, res) => {
  const allowed = ["new", "shortlisted", "offered", "rejected"];
  const patch = {};
  if (allowed.includes(req.body.reviewer_status)) patch.reviewer_status = req.body.reviewer_status;
  if (typeof req.body.reviewer_notes === "string") patch.reviewer_notes = req.body.reviewer_notes.slice(0, 5000);
  const deal = store.update(req.params.id, patch);
  if (!deal) return res.status(404).json({ error: "Not found" });
  res.json(deal);
});

app.delete("/api/deals/:id", requireDashboardAuth, (req, res) => {
  if (!store.remove(req.params.id)) return res.status(404).json({ error: "Not found" });
  res.status(204).end();
});

app.get("/api/deals/:id/files/:name", requireDashboardAuth, (req, res) => {
  const p = store.filePath(req.params.id, req.params.name);
  if (!p) return res.status(404).send("Not found");
  res.sendFile(p);
});

app.get("/dashboard.html", requireDashboardAuth, (req, res, next) => next());
app.get("/dashboard", requireDashboardAuth, (req, res) => res.redirect("/dashboard.html"));

app.use(express.static(path.join(here, "public")));

app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    return res.status(400).json({ error: `Upload problem: ${err.message}` });
  }
  console.error(err);
  res.status(500).json({ error: "Something went wrong." });
});

app.listen(PORT, () => {
  console.log(`Deal sheet scoring running on http://localhost:${PORT}`);
  console.log(`  Submit form:  http://localhost:${PORT}/`);
  console.log(`  Dashboard:    http://localhost:${PORT}/dashboard.html`);
});
