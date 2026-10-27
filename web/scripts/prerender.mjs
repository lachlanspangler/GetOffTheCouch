// Pre-render every indexable page to static HTML (ADR-0007): home, site pages, each city, its hubs and views,
// and one page per upcoming event (one per recurring series). Writes dist/<path>/index.html plus sitemaps.
//   node scripts/prerender.mjs            (after `vite build` and `vite build --ssr src/entry-server.tsx`)
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, "../dist");
const ssr = await import(resolve(here, "../dist-ssr/entry-server.js"));
const base = (process.env.GOTC_BASE ?? "/").replace(/\/?$/, "/");
const origin = process.env.GOTC_SITE_ORIGIN ?? "https://lachlanspangler.github.io";
const HORIZON_DAYS = Number(process.env.GOTC_PRERENDER_DAYS ?? 60);
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

function page(html, head, inline) {
  // function replacers: event text may contain "$&" and friends, which string replacements would interpret
  return template
    .replace(/<title>[\s\S]*?<\/title>\s*/, () => "")
    .replace(/<meta name="description"[^>]*>\s*/, () => "")
    .replace("</head>", () => `  ${head}\n  </head>`)
    .replace('<div id="app"></div>', () => `<div id="app" data-ssr="1" data-now="${now.toISOString()}">${html}</div>${inline ? `\n    <script type="application/json" id="gotc-initial">${inline}</script>` : ""}`);
}

const xesc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
function atom(feed, events) {
  const self = `${origin}${base}${feed.city}/new.xml`;
  const entries = events.map((e) => {
    const link = `${origin}${base}${ssr.eventPath(feed.city, e.id, e.title)}`;
    const when = new Intl.DateTimeFormat("en-US", { timeZone: e.timezone, weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(e.start));
    return `  <entry><id>${link}</id><title>${xesc(e.title)}</title><link href="${link}"/><updated>${e.first_seen}</updated><summary>${xesc(`${when}${e.location.venue_name ? ` · ${e.location.venue_name}` : ""}`)}</summary></entry>`;
  });
  return `<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n  <id>${self}</id>\n  <title>New in ${xesc(feed.city_name)} · Get Off the Couch</title>\n  <link rel="self" href="${self}"/>\n  <link href="${origin}${base}${feed.city}/"/>\n  <updated>${index.generated_at}</updated>\n${entries.join("\n")}\n</feed>\n`;
}

let files = 0;
let bytes = 0;
const sitemap = new Map(); // city ("" for site) → [{loc, lastmod}]
function write(path, html, head, lastmod, indexable, inline) {
  const out = join(dist, path, "index.html");
  mkdirSync(dirname(out), { recursive: true });
  const doc = page(html, head, inline);
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

// Inline first-render data (I-117, lib/partial.ts): the events the page shows (plus the whole-feed numbers it
// computed), so hydration doesn't wait for the city's shards. Inlined only when rendering from that partial data
// reproduces the page byte for byte; otherwise the page hydrates after loading the full feed, as before.
const stats = { inlined: 0, mismatch: 0, tooBig: 0, gz: [], cityPages: {} };

// Share cards (I-115, scripts/og.mjs ran first): the page's own card, else (events) its category hub's, else its
// city's, else the home page's.
const og = existsSync(join(dist, "og", "manifest.json")) ? JSON.parse(readFileSync(join(dist, "og", "manifest.json"), "utf8")) : {};
const HUB_CATS = Object.fromEntries(ssr.HUBS.filter((h) => h.cats).map((h) => [h.slug, h.cats]));
function ogImage(path, event) {
  const [city, a, b] = path.split("/");
  const hub = event && Object.keys(HUB_CATS).find((h) => HUB_CATS[h].some((c) => event.category === c || event.category.startsWith(`${c}.`)));
  const keys = !city ? ["home"] : !cityslugs.has(city) ? ["home"] : a === "events" ? [`${city}/e/${(/([0-9a-f]{8,})$/.exec(b ?? "") ?? [])[1]}`, `${city}/${hub}`, city] : a ? [`${city}/${a}`, city] : [city];
  const file = keys.map((k) => og[k]).find(Boolean);
  return file ? `${origin}${base}${file}` : undefined;
}

function renderPath(path, feed, lastmod, where = new Map(), event = undefined) {
  const url = `${base}${path}`;
  const r = ssr.render(url, index, feed, now, { image: ogImage(path, event) });
  const indexable = r.status === 200 && r.head.includes('content="index,follow"');
  const res = feed && r.status === 200 ? ssr.inlineFor(url, index, feed, now, r, where) : null;
  const inline = res?.json ?? null;
  if (res && !inline) stats[res.why === "too_big" ? "tooBig" : "mismatch"] += 1;
  if (inline) {
    stats.inlined += 1;
    const gz = gzipSync(inline, { level: 6 }).length;
    stats.gz.push(gz);
    if (!path.includes("/events/")) stats.cityPages[path] = gz;
  }
  write(path, r.html, r.head, lastmod, indexable, inline);
  return r;
}

/** event id → shard key from the city's manifest (lets the browser load one card's details without its shard). */
function shardKeys(slug) {
  const out = new Map();
  const m = join(dataDir, "cities", slug, "manifest.json");
  if (!existsSync(m)) return out;
  const manifest = JSON.parse(readFileSync(m, "utf8"));
  for (const s of manifest.shards) {
    for (const e of JSON.parse(readFileSync(join(dataDir, "cities", slug, s.cards.file), "utf8")).events) out.set(e.id, s.key);
  }
  return out;
}

const t0 = Date.now();
const day = (iso) => iso.slice(0, 10);
renderPath("", null, day(index.generated_at));
for (const p of ["about/", "methodology/", "privacy/", "health/", "cities/"]) renderPath(p, null, day(index.generated_at));

const HUBS = ["today", "this-weekend", "free", "concerts", "beer-leagues", "trivia", "nightlife", "volunteering", "festivals", "food-and-drink", "arts", "fitness", "outdoors", "games-to-watch", "cons-and-faires", "classes", "family"];
const VIEWS = ["deadlines", "calendar", "map", "plan", "saved", "health"];
let events = 0;
for (const c of index.cities) {
  const f = join(dataDir, "cities", `${c.slug}.json`);
  if (!existsSync(f)) continue;
  const feed = JSON.parse(readFileSync(f, "utf8"));
  if (feed.is_demo) continue;
  const lm = day(feed.generated_at ?? index.generated_at);
  const where = shardKeys(c.slug);
  renderPath(`${c.slug}/`, feed, lm, where);
  // I-116: subscribable calendar of published sign-up deadlines (refreshes in the user's calendar app)
  const dl = ssr.deadlines(feed.events, now).filter((d) => !d.derived && d.kind !== "opens");
  const dlEvents = [...new Map(dl.map((d) => [d.event.id, d.event])).values()];
  mkdirSync(join(dist, c.slug), { recursive: true });
  writeFileSync(join(dist, c.slug, "deadlines.ics"), ssr.calendar(dlEvents, { mode: "deadlines", name: `${feed.city_name} sign-up deadlines · Get Off the Couch`, refreshHours: 6, now }));
  // and an Atom feed of newly listed events
  const fresh = feed.events.filter((e) => e.is_new && e.kind !== "opening").sort((a, b) => b.first_seen.localeCompare(a.first_seen)).slice(0, 50);
  writeFileSync(join(dist, c.slug, "new.xml"), atom(feed, fresh));
  for (const h of HUBS) renderPath(`${c.slug}/${h}/`, feed, lm, where);
  for (const v of VIEWS) renderPath(`${c.slug}/${v}/`, feed, lm, where);
  const until = now.getTime() + HORIZON_DAYS * 86_400_000;
  const seenSeries = new Set();
  const upcoming = [...feed.events]
    .filter((e) => !e.is_demo) // openings render too (noindex): city pages link to them
    .filter((e) => new Date(e.end ?? e.start).getTime() >= now.getTime() - 86_400_000 && new Date(e.start).getTime() <= until)
    .sort((a, b) => a.start.localeCompare(b.start));
  for (const e of upcoming) {
    if (e.series_id) {
      if (seenSeries.has(e.series_id)) continue;
      seenSeries.add(e.series_id);
    }
    const path = ssr.eventPath(c.slug, e.id, e.title);
    renderPath(path, feed, day(e.last_checked ?? lm), where, e);
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
const sorted = [...stats.gz].sort((a, b) => a - b);
const kb = (n) => +((n ?? 0) / 1024).toFixed(1);
const inline = { pages: stats.inlined, mismatch: stats.mismatch, too_big: stats.tooBig, gz_kb_median: kb(sorted[sorted.length >> 1]), gz_kb_max: kb(sorted[sorted.length - 1]), city_pages_gz_kb: Object.fromEntries(Object.entries(stats.cityPages).filter(([p]) => /^[a-z_]+\/$/.test(p)).map(([p, n]) => [p, kb(n)])) };
const report = { files, events, indexed, mb: +(bytes / 1e6).toFixed(1), seconds: +((Date.now() - t0) / 1000).toFixed(1), inline };
writeFileSync(join(dist, "prerender.json"), JSON.stringify({ ...report, generated_at: index.generated_at }, null, 2));
console.log(`prerendered ${files} pages (${events} events, ${indexed} in sitemaps), ${report.mb} MB in ${report.seconds}s`);
console.log(`inline first-render data on ${inline.pages} pages (median ${inline.gz_kb_median} KB gz, max ${inline.gz_kb_max} KB); ${inline.mismatch} pages hydrate from the full feed instead (no exact partial), ${inline.too_big} too big`);
if (!statSync(join(dist, "404.html")).isFile()) throw new Error("missing 404.html shell");
