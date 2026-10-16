// Pre-render every indexable page to static HTML (ADR-0007): home, site pages, each city, its hubs and views,
// and one page per upcoming event (one per recurring series). Writes dist/<path>/index.html plus sitemaps.
//   node scripts/prerender.mjs            (after `vite build` and `vite build --ssr src/entry-server.tsx`)
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, "../dist");
const ssr = await import(resolve(here, "../dist-ssr/entry-server.js"));
const base = (process.env.GOTC_BASE ?? "/").replace(/\/?$/, "/");
const origin = process.env.GOTC_SITE_ORIGIN ?? "https://lachlanspangler.github.io";
const HORIZON_DAYS = Number(process.env.GOTC_PRERENDER_DAYS ?? 45);
const MAX_FILES = 60_000;
const MAX_BYTES = 800 * 1024 * 1024;

const template = readFileSync(join(dist, "index.html"), "utf8");
if (!template.includes('<div id="app"></div>')) throw new Error("dist/index.html has no empty #app to fill");
const dataDir = join(dist, "data");
if (!existsSync(join(dataDir, "index.json"))) {
  console.log("prerender: no dist/data/index.json (no pipeline export yet); the site stays a client-rendered shell");
  process.exit(0);
}
const index = JSON.parse(readFileSync(join(dataDir, "index.json"), "utf8"));
if (index.is_demo) throw new Error("refusing to pre-render demo data");
const now = new Date(process.env.GOTC_PRERENDER_NOW ?? index.generated_at);
const cityslugs = new Set(index.cities.map((c) => c.slug));

function page(html, head) {
  return template
    .replace(/<title>[\s\S]*?<\/title>\s*/, "")
    .replace(/<meta name="description"[^>]*>\s*/, "")
    .replace("</head>", `  ${head}\n  </head>`)
    .replace('<div id="app"></div>', `<div id="app" data-ssr="1">${html}</div>`);
}

let files = 0;
let bytes = 0;
const sitemap = new Map(); // city ("" for site) → [{loc, lastmod}]
function write(path, html, head, lastmod, indexable) {
  const out = join(dist, path, "index.html");
  mkdirSync(dirname(out), { recursive: true });
  const doc = page(html, head);
  writeFileSync(out, doc);
  files += 1;
  bytes += Buffer.byteLength(doc);
  if (indexable) {
    const first = path.split("/")[0];
    const key = cityslugs.has(first) ? first : "";
    const list = sitemap.get(key) ?? [];
    list.push({ loc: `${origin}${base}${path}`, lastmod });
    sitemap.set(key, list);
  }
}

function renderPath(path, feed, lastmod) {
  const r = ssr.render(`${base}${path}`, index, feed, now);
  const indexable = r.status === 200 && r.head.includes('content="index,follow"');
  write(path, r.html, r.head, lastmod, indexable);
  return r;
}

const t0 = Date.now();
const day = (iso) => iso.slice(0, 10);
renderPath("", null, day(index.generated_at));
for (const p of ["about/", "methodology/", "privacy/", "health/"]) renderPath(p, null, day(index.generated_at));

const HUBS = ["today", "this-weekend", "this-week", "free", "concerts", "beer-leagues", "trivia", "nightlife", "volunteering", "festivals", "food-and-drink", "arts", "fitness", "outdoors", "games-to-watch", "cons-and-faires", "classes", "family"];
const VIEWS = ["deadlines", "calendar", "map", "plan", "saved", "health"];
let events = 0;
for (const c of index.cities) {
  const f = join(dataDir, "cities", `${c.slug}.json`);
  if (!existsSync(f)) continue;
  const feed = JSON.parse(readFileSync(f, "utf8"));
  if (feed.is_demo) continue;
  const lm = day(feed.generated_at ?? index.generated_at);
  renderPath(`${c.slug}/`, feed, lm);
  for (const h of HUBS) renderPath(`${c.slug}/${h}/`, feed, lm);
  for (const v of VIEWS) renderPath(`${c.slug}/${v}/`, feed, lm);
  const until = now.getTime() + HORIZON_DAYS * 86_400_000;
  const seenSeries = new Set();
  const upcoming = [...feed.events]
    .filter((e) => e.kind !== "opening" && !e.is_demo)
    .filter((e) => new Date(e.end ?? e.start).getTime() >= now.getTime() - 86_400_000 && new Date(e.start).getTime() <= until)
    .sort((a, b) => a.start.localeCompare(b.start));
  for (const e of upcoming) {
    if (e.series_id) {
      if (seenSeries.has(e.series_id)) continue;
      seenSeries.add(e.series_id);
    }
    const path = ssr.eventPath(c.slug, e.id, e.title);
    renderPath(path, feed, day(e.last_checked ?? lm));
    events += 1;
  }
  if (files > MAX_FILES || bytes > MAX_BYTES) throw new Error(`pre-render too big: ${files} files, ${(bytes / 1e6).toFixed(0)} MB`);
}

// Sitemaps: an index plus one file per city (each well under the 50k-URL limit).
const xml = (urls) =>
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map((u) => `  <url><loc>${u.loc}</loc><lastmod>${u.lastmod}</lastmod></url>`).join("\n")}\n</urlset>\n`;
mkdirSync(join(dist, "sitemaps"), { recursive: true });
const parts = [];
for (const [key, urls] of sitemap) {
  const name = `sitemaps/${key || "site"}.xml`;
  writeFileSync(join(dist, name), xml(urls));
  parts.push(`  <sitemap><loc>${origin}${base}${name}</loc><lastmod>${day(index.generated_at)}</lastmod></sitemap>`);
}
writeFileSync(join(dist, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${parts.join("\n")}\n</sitemapindex>\n`);

const indexed = [...sitemap.values()].reduce((n, l) => n + l.length, 0);
const report = { files, events, indexed, mb: +(bytes / 1e6).toFixed(1), seconds: +((Date.now() - t0) / 1000).toFixed(1) };
writeFileSync(join(dist, "prerender.json"), JSON.stringify({ ...report, generated_at: index.generated_at }, null, 2));
console.log(`prerendered ${files} pages (${events} events, ${indexed} in sitemaps), ${report.mb} MB in ${report.seconds}s`);
if (!statSync(join(dist, "404.html")).isFile()) throw new Error("missing 404.html shell");
