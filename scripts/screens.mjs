// Full visual snapshot of every screen: desktop + mobile × light + dark.
//   node scripts/screens.mjs <outdir> [baseUrl] [cities comma-separated]
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "docs/screenshots/latest";
const base = process.argv[3] ?? "http://localhost:5173";
const cities = (process.argv[4] ?? "minneapolis,nyc").split(",");
mkdirSync(out, { recursive: true });
const views = ["feed", "deadlines", "calendar", "map", "plan", "health"];
const b = await chromium.launch();
const errors = [];
for (const scheme of ["light", "dark"]) {
  for (const [label, vp] of [["desktop", { width: 1366, height: 900 }], ["mobile", { width: 390, height: 844 }]]) {
    const ctx = await b.newContext({ viewport: vp, colorScheme: scheme, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    p.on("pageerror", (e) => errors.push(`${scheme}/${label}: ${e}`));
    const shot = async (name) => p.screenshot({ path: `${out}/${name}-${label}-${scheme}.png` });
    await p.goto(`${base}/`); await p.waitForTimeout(900); await shot("home");
    for (const c of cities) {
      for (const v of views) {
        await p.goto(`${base}/${c}/${v}/`);
        await p.waitForTimeout(v === "map" ? 2200 : 900);
        await shot(`${c}-${v}`);
      }
      await p.goto(`${base}/${c}/`); await p.waitForTimeout(900);
      const link = p.locator('[data-testid="event-card"] a').first();
      if (await link.count()) { await link.click(); await p.waitForTimeout(900); await shot(`${c}-event`); }
    }
    await ctx.close();
  }
}
await b.close();
console.log(`screens → ${out}`, errors.length ? errors.slice(0, 5) : "no page errors");
