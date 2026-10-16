// Post-build guard for the pre-rendered site (SEO_ACCESS §7.1 phase 5): every page has a title, description and
// absolute canonical; JSON-LD parses and Event markup has its required fields; no legacy #/ links; noindex pages
// stay out of sitemaps; size budgets hold.  node scripts/check-dist.mjs [--warn]
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const dist = resolve(process.argv.find((a) => a.startsWith("--dist="))?.slice(7) ?? "dist");
const warnOnly = process.argv.includes("--warn");
const problems = [];
const pages = [];
(function walk(d) {
  for (const f of readdirSync(d)) {
    const p = join(d, f);
    if (statSync(p).isDirectory()) { if (!["assets", "data", "demo", "fonts", "sitemaps"].includes(f)) walk(p); }
    else if (f === "index.html") pages.push(p);
  }
})(dist);

const sitemapLocs = new Set();
for (const f of readdirSync(join(dist, "sitemaps"))) {
  for (const m of readFileSync(join(dist, "sitemaps", f), "utf8").matchAll(/<loc>([^<]+)<\/loc>/g)) sitemapLocs.add(m[1]);
}

let events = 0;
for (const p of pages) {
  const html = readFileSync(p, "utf8");
  const rel = p.slice(dist.length);
  const title = /<title>([^<]+)<\/title>/.exec(html)?.[1];
  const canonical = /<link rel="canonical" href="([^"]+)"/.exec(html)?.[1];
  const robots = /<meta name="robots" content="([^"]+)"/.exec(html)?.[1];
  if (!title) problems.push(`${rel}: no <title>`);
  if (!/<meta name="description" content="[^"]{20,}"/.test(html)) problems.push(`${rel}: missing or short description`);
  if (!canonical || !/^https:\/\//.test(canonical)) problems.push(`${rel}: canonical missing or not absolute`);
  if (/href="#\//.test(html)) problems.push(`${rel}: legacy #/ link`);
  if (!html.includes('data-ssr="1"')) problems.push(`${rel}: not pre-rendered`);
  if (robots === "noindex,follow" && canonical && sitemapLocs.has(canonical)) problems.push(`${rel}: noindex page listed in a sitemap`);
  for (const m of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
    let j;
    try { j = JSON.parse(m[1]); } catch { problems.push(`${rel}: JSON-LD doesn't parse`); continue; }
    if (j["@type"] === "Event") {
      events += 1;
      for (const k of ["name", "startDate", "location", "eventStatus"]) if (!j[k]) problems.push(`${rel}: Event JSON-LD missing ${k}`);
      if (!j.location?.name) problems.push(`${rel}: Event location has no name`);
      for (const o of j.offers ?? []) if ("price" in o && typeof o.price !== "number") problems.push(`${rel}: offer price not a number`);
    }
  }
}
const size = (function du(d) { let n = 0; for (const f of readdirSync(d)) { const p = join(d, f); const s = statSync(p); n += s.isDirectory() ? du(p) : s.size; } return n; })(dist);
if (size > 800 * 1024 * 1024) problems.push(`dist is ${(size / 1e6).toFixed(0)} MB (budget 800 MB)`);
if (pages.length > 60_000) problems.push(`${pages.length} pages (budget 60k files)`);
console.log(`check-dist: ${pages.length} pages, ${events} with Event JSON-LD, ${sitemapLocs.size} sitemap URLs, ${(size / 1e6).toFixed(0)} MB, ${problems.length} problems`);
for (const p of problems.slice(0, 30)) console.log(`  ✗ ${p}`);
if (problems.length && !warnOnly) process.exit(1);
