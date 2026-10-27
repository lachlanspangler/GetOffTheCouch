// Performance budgets (SEO_ACCESS §4.2), measured as gzip bytes because GitHub Pages serves gzip only.
//   node scripts/check-budgets.mjs [--warn]
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { gzipSync } from "node:zlib";

const dist = resolve("dist");
const warnOnly = process.argv.includes("--warn");
const gz = (p) => gzipSync(readFileSync(p), { level: 9 }).length;
const gzs = (s) => gzipSync(s, { level: 9 }).length;
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;
const BUDGET = {
  entryJs: 60 * 1024,
  css: 15 * 1024,
  chunk: 80 * 1024,
  fonts: 80 * 1024,
  html: 40 * 1024, // the page itself, without its inline data
  cityData: 600 * 1024, // the legacy monolithic card file (kept for older clients)
  inline: 30 * 1024, // I-117: <script id="gotc-initial"> on a pre-rendered page
  shard: 150 * 1024, // one week shard (SEO_ACCESS §6.3)
  firstView: 150 * 1024, // pre-rendered city page: inline data + index.json before it's interactive
  // a client-rendered city view (a filtered or shared URL that isn't pre-rendered) must load the whole next 7 days;
  // NYC's busiest week is ~650 cards ≈ 290 KB gz today. 320 KB keeps that honest; slimmer cards are I-219.
  firstViewSpa: 320 * 1024,
};
const rows = [];
const fail = [];
const check = (name, size, budget) => {
  rows.push(`${size <= budget ? "✓" : "✗"} ${name}: ${kb(size)} (budget ${kb(budget)})`);
  if (size > budget) fail.push(name);
};
const INLINE = /<script type="application\/json" id="gotc-initial">([\s\S]*?)<\/script>/;

const html = readFileSync(join(dist, "404.html"), "utf8");
const entry = /src="[^"]*\/assets\/(index-[^"]+\.js)"/.exec(html)?.[1];
const assets = readdirSync(join(dist, "assets"));
if (entry) check(`entry JS (${entry})`, gz(join(dist, "assets", entry)), BUDGET.entryJs);
for (const f of assets.filter((f) => f.endsWith(".css"))) check(`CSS ${f}`, gz(join(dist, "assets", f)), BUDGET.css);
for (const f of assets.filter((f) => f.endsWith(".js") && f !== entry)) check(`lazy chunk ${f}`, gz(join(dist, "assets", f)), BUDGET.chunk);
const fonts = readdirSync(join(dist, "fonts")).filter((f) => f.endsWith(".woff2")).reduce((n, f) => n + statSync(join(dist, "fonts", f)).size, 0);
check("fonts (woff2, preloaded)", fonts, BUDGET.fonts);
for (const p of ["index.html", "nyc/index.html", "nyc/concerts/index.html", "minneapolis/index.html", "minneapolis/deadlines/index.html"]) {
  if (!existsSync(join(dist, p))) continue; // not pre-rendered in this build
  const doc = readFileSync(join(dist, p), "utf8");
  const inline = INLINE.exec(doc)?.[1];
  check(`page ${p}`, gzs(doc.replace(INLINE, "")), BUDGET.html);
  if (inline) check(`inline data ${p}`, gzs(inline), BUDGET.inline);
}

// Week shards (I-117) and the first-view data for each city: what the browser downloads before a pre-rendered city
// page is interactive (inline data + index.json), and before "this week" is complete without one (manifest, meta,
// ongoing + deadlines shards, the current and next week). Reported for every city; budgeted for the largest.
const cities = join(dist, "data", "cities");
const indexGz = existsSync(join(dist, "data", "index.json")) ? gz(join(dist, "data", "index.json")) : 0;
let largest = null;
if (existsSync(cities)) {
  for (const f of readdirSync(cities).filter((f) => f.endsWith(".json") && !f.includes(".details."))) {
    check(`legacy city data ${f}`, gz(join(cities, f)), BUDGET.cityData);
  }
  for (const slug of readdirSync(cities).filter((d) => existsSync(join(cities, d, "manifest.json")))) {
    const dir = join(cities, slug);
    const m = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8"));
    let biggest = 0;
    for (const s of m.shards) biggest = Math.max(biggest, gz(join(dir, s.cards.file)));
    check(`largest shard ${slug}`, biggest, BUDGET.shard);
    const today = Date.parse(m.generated_at);
    const first = m.shards.filter((s) => s.kind === "ongoing" || s.kind === "deadlines" || (s.kind === "week" && Date.parse(`${s.starts}T00:00:00Z`) < today + 8 * 86_400_000));
    const spa = gz(join(dir, "manifest.json")) + gz(join(dir, m.meta.file)) + first.reduce((n, s) => n + gz(join(dir, s.cards.file)), 0);
    const page = join(dist, slug, "index.html");
    const inline = existsSync(page) ? INLINE.exec(readFileSync(page, "utf8"))?.[1] : undefined;
    const hydrate = (inline ? gzs(inline) : 0) + indexGz;
    const legacy = gz(join(cities, `${slug}.json`));
    if (!largest || legacy > largest.legacy) largest = { slug, legacy, spa, hydrate, inline: !!inline };
  }
}
if (largest) {
  check(`first view ${largest.slug} (largest city), pre-rendered: inline data + index.json${largest.inline ? "" : " (no inline data!)"}`, largest.hydrate, BUDGET.firstView);
  check(`first view ${largest.slug}, client-rendered: manifest + meta + ongoing/deadlines + this and next week`, largest.spa, BUDGET.firstViewSpa);
  rows.push(`  (before I-117 both waited for the whole card file: ${kb(largest.legacy)} gz)`);
}
console.log(rows.join("\n"));
if (fail.length && !warnOnly) { console.error(`over budget: ${fail.join(", ")}`); process.exit(1); }
