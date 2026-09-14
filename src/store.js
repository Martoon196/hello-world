import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const DATA_DIR = path.resolve(process.env.DATA_DIR || "data");
const DEALS_FILE = path.join(DATA_DIR, "deals.json");
const UPLOADS_DIR = path.join(DATA_DIR, "uploads");

fs.mkdirSync(UPLOADS_DIR, { recursive: true });

function readAll() {
  try {
    return JSON.parse(fs.readFileSync(DEALS_FILE, "utf8"));
  } catch (e) {
    if (e.code === "ENOENT") return [];
    throw e;
  }
}

function writeAll(deals) {
  const tmp = DEALS_FILE + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(deals, null, 2));
  fs.renameSync(tmp, DEALS_FILE);
}

const safeName = (n) => (n || "file").replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 120);

export const store = {
  dir: DATA_DIR,

  list() {
    return readAll()
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
      .map(({ notes, ...rest }) => rest);
  },

  get(id) {
    return readAll().find((d) => d.id === id) || null;
  },

  create({ submitter, notes, files }) {
    const id = crypto.randomUUID();
    const dir = path.join(UPLOADS_DIR, id);
    fs.mkdirSync(dir, { recursive: true });
    const saved = files.map((f, i) => {
      const name = `${i + 1}-${safeName(f.originalname)}`;
      fs.writeFileSync(path.join(dir, name), f.buffer);
      return { name, original: f.originalname, type: f.mimetype, size: f.size };
    });
    const deal = {
      id,
      created_at: new Date().toISOString(),
      status: "queued",
      submitter,
      notes,
      files: saved,
      analysis: null,
      error: null,
      reviewer_status: "new",
    };
    const deals = readAll();
    deals.push(deal);
    writeAll(deals);
    return deal;
  },

  update(id, patch) {
    const deals = readAll();
    const i = deals.findIndex((d) => d.id === id);
    if (i === -1) return null;
    deals[i] = { ...deals[i], ...patch, updated_at: new Date().toISOString() };
    writeAll(deals);
    return deals[i];
  },

  remove(id) {
    const deals = readAll();
    const next = deals.filter((d) => d.id !== id);
    if (next.length === deals.length) return false;
    writeAll(next);
    fs.rmSync(path.join(UPLOADS_DIR, id), { recursive: true, force: true });
    return true;
  },

  /** Re-read a deal's uploads from disk as multer-style file objects. */
  loadFiles(deal) {
    return deal.files.map((f) => ({
      originalname: f.original,
      mimetype: f.type,
      size: f.size,
      buffer: fs.readFileSync(path.join(UPLOADS_DIR, deal.id, f.name)),
    }));
  },

  filePath(id, name) {
    const p = path.join(UPLOADS_DIR, id, path.basename(name));
    return fs.existsSync(p) ? p : null;
  },
};
