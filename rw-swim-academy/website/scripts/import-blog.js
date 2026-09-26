/* Copies the blog posts written in ../marketing/blog/post-*.md into src/pages/blog/ with the header the build needs.
   Run: node scripts/import-blog.js   (then npm run build). Edit the slug/date map below when adding posts. */
const fs = require("fs"), path = require("path");
const SRC = path.resolve(__dirname, "../../marketing/blog");
const OUT = path.resolve(__dirname, "../src/pages/blog");
const MAP = {
  "post-01": { slug: "private-vs-group-swimming-lessons", date: "2026-11-02" },
  "post-02": { slug: "child-scared-of-water", date: "2026-11-16" },
  "post-03": { slug: "how-long-does-it-take-to-learn-to-swim", date: "2026-11-30" },
  "post-04": { slug: "what-racing-at-kent-counties-taught-me", date: "2026-12-14" },
  "post-05": { slug: "is-my-child-ready-for-a-swimming-club", date: "2027-01-04" },
  "post-06": { slug: "water-safety-for-families-in-kent", date: "2027-01-18" },
};
fs.mkdirSync(OUT, { recursive: true });
for (const f of fs.readdirSync(SRC).filter((x) => /^post-\d\d.*\.md$/.test(x)).sort()) {
  const key = f.slice(0, 7), m = MAP[key] || { slug: f.replace(/\.md$/, ""), date: "2027-01-01" };
  const raw = fs.readFileSync(path.join(SRC, f), "utf8");
  const title = (raw.match(/^#\s+(.+)$/m) || [, f])[1].trim();
  const desc = (raw.match(/\*\*Meta description:\*\*\s*(.+)/) || [, ""])[1].trim();
  // body = everything after the first horizontal rule following the metadata block
  const idx = raw.indexOf("\n---\n");
  let body = idx > -1 ? raw.slice(idx + 5) : raw.replace(/^#\s+.+\n/, "");
  body = body.replace(/^\s*\n/, "");
  const esc = (s) => s.replace(/\n/g, " ");
  fs.writeFileSync(path.join(OUT, m.slug + ".md"), `---\ntitle: ${esc(title)}\ndescription: ${esc(desc)}\ndate: ${m.date}\nauthor: Ruby Waller\nslug: ${m.slug}\n---\n${body}`);
  console.log("imported", f, "->", m.slug + ".md");
}
