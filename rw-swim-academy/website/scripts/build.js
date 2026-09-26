/* Assembles pages from src/pages + src/partials into public/, and renders blog posts from Markdown.
   Run: npm run build  (needs `npm install` once for `marked`). */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "src");
const OUT = path.join(ROOT, "public");
const SITE_URL = process.env.SITE_URL || "https://rwswimacademy.co.uk";

const niceDate = (d) => d ? new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "";
const partial = (name) => fs.readFileSync(path.join(SRC, "partials", name + ".html"), "utf8");
const head = partial("head"), header = partial("header"), footer = partial("footer"), sticky = partial("sticky-cta");

function fill(tpl, vars) {
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => (vars[k] ?? ""));
}

// Front matter: first lines "key: value" until a line "---"
function parse(file) {
  const raw = fs.readFileSync(file, "utf8");
  const m = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  const meta = {};
  if (!m) return { meta, body: raw };
  m[1].split("\n").forEach((l) => { const i = l.indexOf(":"); if (i > 0) meta[l.slice(0, i).trim()] = l.slice(i + 1).trim(); });
  return { meta, body: m[2] };
}

function writePage(relOut, meta, bodyHtml) {
  const vars = {
    title: meta.title ? `${meta.title} | RW Swim Academy` : "RW Swim Academy",
    description: meta.description || "Private swimming lessons in Sevenoaks, Kent, with Ruby Waller.",
    siteUrl: SITE_URL,
    path: relOut.replace(/index\.html$/, ""),
    bodyClass: meta.sticky === "false" ? "" : "has-sticky",
    scripts: (meta.scripts || "").split(",").filter(Boolean).map((s) => `<script src="${s.trim()}" defer></script>`).join("\n"),
  };
  let html = fill(head, vars) + header + bodyHtml + (meta.sticky === "false" ? "" : sticky) + fill(footer, vars);
  if (meta.nav) html = html.replace(`data-nav="${meta.nav}"`, `data-nav="${meta.nav}" aria-current="page"`);
  const outFile = path.join(OUT, relOut);
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, html);
  console.log("wrote", relOut);
}

// 1) HTML pages
function walk(dir, base = "") {
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) { walk(p, path.join(base, f)); continue; }
    if (f.endsWith(".html")) {
      const { meta, body } = parse(p);
      writePage(path.join(base, f), meta, body);
    }
  }
}
walk(path.join(SRC, "pages"));

// 2) Blog posts from Markdown (src/pages/blog/*.md)
let marked;
try { marked = require("marked"); } catch { console.warn("marked not installed; skipping Markdown blog posts (run npm install)"); }
const blogDir = path.join(SRC, "pages", "blog");
const posts = [];
if (marked && fs.existsSync(blogDir)) {
  for (const f of fs.readdirSync(blogDir).filter((x) => x.endsWith(".md")).sort()) {
    const { meta, body } = parse(path.join(blogDir, f));
    const slug = meta.slug || f.replace(/\.md$/, "");
    const html = marked.parse(body);
    posts.push({ ...meta, slug });
    const article = `
<section class="page-hero"><div class="wrap"><span class="eyebrow">Blog</span><h1>${meta.title}</h1><p class="lead">${meta.description || ""}</p><p class="post-meta" style="color:rgba(255,255,255,.7)">${niceDate(meta.date)} · by ${meta.author || "Ruby Waller"}</p></div></section>
<section class="section"><div class="wrap"><article class="prose">${html}</article>
<div class="banner" style="margin-top:48px"><div><h3>Book a free taster with Ruby</h3><p>20 minutes in the water, a written assessment, and an honest recommendation. No pressure.</p></div><a class="btn btn--gold btn--lg" href="/book.html?product=taster">Book a free taster</a></div>
<p style="margin-top:24px"><a href="/blog/">&larr; All posts</a></p></div></section>`;
    writePage(path.join("blog", slug + ".html"), { ...meta, nav: "blog" }, article);
  }
  // Blog index
  const list = posts.sort((a, b) => (b.date || "").localeCompare(a.date || "")).map((p) => `
<article><span class="post-meta">${niceDate(p.date)}</span><h3><a href="/blog/${p.slug}.html">${p.title}</a></h3><p class="muted">${p.description || ""}</p><a href="/blog/${p.slug}.html">Read more &rarr;</a></article>`).join("");
  const index = `
<section class="page-hero"><div class="wrap"><span class="eyebrow">Blog</span><h1>Straight talk about learning to swim</h1><p class="lead">Practical advice for Kent parents from a coach who still races. No fluff.</p></div></section>
<section class="section"><div class="wrap"><div class="post-list grid grid--2">${list || "<p>First posts coming soon.</p>"}</div></div></section>`;
  writePage(path.join("blog", "index.html"), { title: "Blog", description: "Practical swimming advice for parents in Sevenoaks and Kent from Ruby Waller.", nav: "blog" }, index);
}

// 3) sitemap
const pages = [];
(function list(dir, base = "") { for (const f of fs.readdirSync(dir)) { const p = path.join(dir, f); if (fs.statSync(p).isDirectory()) { if (!["assets", "data"].includes(f)) list(p, base + f + "/"); } else if (f.endsWith(".html")) pages.push(base + f); } })(OUT);
fs.writeFileSync(path.join(OUT, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${pages.map((p) => `  <url><loc>${SITE_URL}/${p.replace(/index\.html$/, "")}</loc></url>`).join("\n")}\n</urlset>\n`);
fs.writeFileSync(path.join(OUT, "robots.txt"), `User-agent: *\nAllow: /\nSitemap: ${SITE_URL}/sitemap.xml\n`);
console.log("build complete:", pages.length, "pages");
