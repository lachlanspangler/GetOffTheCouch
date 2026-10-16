// Performance budgets (SEO_ACCESS §4.2), measured as gzip bytes because GitHub Pages serves gzip only.
//   node scripts/check-budgets.mjs [--warn]
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { gzipSync } from "node:zlib";

const dist = resolve("dist");
const warnOnly = process.argv.includes("--warn");
const gz = (p) => gzipSync(readFileSync(p), { level: 9 }).length;
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;
const BUDGET = { entryJs: 60 * 1024, css: 15 * 1024, chunk: 80 * 1024, fonts: 80 * 1024, html: 40 * 1024, cityData: 600 * 1024 };
const rows = [];
const fail = [];
const check = (name, size, budget) => {
  rows.push(`${size <= budget ? "✓" : "✗"} ${name}: ${kb(size)} (budget ${kb(budget)})`);
  if (size > budget) fail.push(name);
};

const html = readFileSync(join(dist, "404.html"), "utf8");
const entry = /src="[^"]*\/assets\/(index-[^"]+\.js)"/.exec(html)?.[1];
const assets = readdirSync(join(dist, "assets"));
if (entry) check(`entry JS (${entry})`, gz(join(dist, "assets", entry)), BUDGET.entryJs);
for (const f of assets.filter((f) => f.endsWith(".css"))) check(`CSS ${f}`, gz(join(dist, "assets", f)), BUDGET.css);
for (const f of assets.filter((f) => f.endsWith(".js") && f !== entry)) check(`lazy chunk ${f}`, gz(join(dist, "assets", f)), BUDGET.chunk);
const fonts = readdirSync(join(dist, "fonts")).filter((f) => f.endsWith(".woff2")).reduce((n, f) => n + statSync(join(dist, "fonts", f)).size, 0);
check("fonts (woff2, preloaded)", fonts, BUDGET.fonts);
for (const p of ["index.html", "nyc/index.html", "minneapolis/index.html"]) {
  try { check(`page ${p}`, gz(join(dist, p)), BUDGET.html); } catch { /* not pre-rendered in this build */ }
}
try {
  for (const f of readdirSync(join(dist, "data", "cities")).filter((f) => f.endsWith(".json") && !f.includes(".details."))) {
    check(`city data ${f}`, gz(join(dist, "data", "cities", f)), BUDGET.cityData);
  }
} catch { /* no data in this build */ }
console.log(rows.join("\n"));
if (fail.length && !warnOnly) { console.error(`over budget: ${fail.join(", ")}`); process.exit(1); }
