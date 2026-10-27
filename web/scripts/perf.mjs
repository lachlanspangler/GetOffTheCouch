// Lab Core Web Vitals on a mid-range phone: 4× CPU slowdown, "Slow 4G" (150 ms RTT, 1.6 Mbps down), gzip like
// GitHub Pages. Serves dist/ under GOTC_BASE and reports LCP, CLS and TBT-ish long tasks per URL.
//   node scripts/perf.mjs [paths...]
import { createServer } from "node:http";
import { existsSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { gzipSync } from "node:zlib";
import { chromium } from "@playwright/test";

const base = (process.env.GOTC_BASE ?? "/GetOffTheCouch/").replace(/\/?$/, "/");
const dist = resolve("dist");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".woff2": "font/woff2", ".xml": "application/xml" };
const server = createServer((req, res) => {
  let p = decodeURIComponent((req.url ?? "/").split("?")[0]);
  if (!p.startsWith(base)) { res.writeHead(404).end(); return; }
  p = join(dist, p.slice(base.length));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, "index.html");
  const found = existsSync(p);
  const body = readFileSync(found ? p : join(dist, "404.html"));
  const type = TYPES[extname(p)] ?? "application/octet-stream";
  const zip = type !== "font/woff2";
  res.writeHead(found ? 200 : 404, { "content-type": type, ...(zip ? { "content-encoding": "gzip" } : {}), "cache-control": "max-age=600" });
  res.end(zip ? gzipSync(body) : body);
});
// GOTC_PERF_PORT: another local server may already own the default port (it would be measured instead)
const port = Number(process.env.GOTC_PERF_PORT ?? 4399);
await new Promise((ok, fail) => server.once("error", fail).listen(port, "127.0.0.1", ok));

const args = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const paths = args.length ? args : ["", "nyc/", "nyc/concerts/", "minneapolis/deadlines/"];
const b = await chromium.launch();
const results = [];
for (const path of paths) {
  const ctx = await b.newContext({ viewport: { width: 412, height: 915 }, deviceScaleFactor: 2.6, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  await page.addInitScript(() => {
    const w = window;
    w.__lcp = 0; w.__cls = 0; w.__tbt = 0;
    new PerformanceObserver((l) => { for (const e of l.getEntries()) { w.__lcp = e.startTime; w.__lcpEl = (e.element?.tagName ?? "") + "." + (e.element?.className ?? "") + ":" + (e.element?.textContent ?? "").slice(0, 40); } }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) w.__cls += e.value; }).observe({ type: "layout-shift", buffered: true });
    new PerformanceObserver((l) => { for (const e of l.getEntries()) w.__tbt += Math.max(0, e.duration - 50); }).observe({ type: "longtask", buffered: true });
  });
  await page.goto(`http://127.0.0.1:${port}${base}${path}`, { waitUntil: "load" });
  await page.waitForTimeout(6000);
  const m = await page.evaluate(() => {
    // hydration: main.tsx marks "gotc:hydrated"; data: JSON under /data/ (encoded bytes) before hydration and in total
    const hyd = performance.getEntriesByName("gotc:hydrated")[0]?.startTime ?? null;
    const data = performance.getEntriesByType("resource").filter((r) => r.name.includes("/data/") && r.name.endsWith(".json"));
    const kb = (rs) => Math.round(rs.reduce((n, r) => n + (r.encodedBodySize || r.transferSize || 0), 0) / 1024);
    return { lcp: window.__lcp, cls: window.__cls, tbt: window.__tbt, el: window.__lcpEl, hyd, before: hyd == null ? null : kb(data.filter((r) => r.responseEnd <= hyd)), total: kb(data) };
  });
  results.push({ path: `/${path}`, lcp_ms: Math.round(m.lcp), cls: +m.cls.toFixed(3), tbt_ms: Math.round(m.tbt), hydrated_ms: m.hyd == null ? null : Math.round(m.hyd), data_kb_before_hydration: m.before, data_kb_6s: m.total, lcp_el: m.el?.slice(0, 24) });
  await ctx.close();
}
await b.close();
server.close();
console.table(results);
const bad = results.filter((r) => r.lcp_ms > 2500 || r.cls > 0.1);
if (bad.length && !process.argv.includes("--warn")) process.exitCode = 1;
