// Screenshot every city's key views (desktop + mobile) for UX review.
//   node scripts/screenshots.mjs <outdir> [baseUrl]     (needs `npm run dev` or preview running)
import { chromium } from "../web/node_modules/@playwright/test/index.mjs";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "docs/screenshots/latest";
const base = process.argv[3] ?? "http://localhost:5173";
const cities = ["minneapolis", "nyc", "chicago", "los_angeles", "miami", "austin", "denver", "seattle", "nashville", "boston"];
const views = ["feed", "deadlines", "map"];
mkdirSync(out, { recursive: true });
const b = await chromium.launch();
const errors = [];
for (const [label, vp] of [["desktop", { width: 1280, height: 900 }], ["mobile", { width: 390, height: 844 }]]) {
  const p = await b.newPage({ viewport: vp });
  p.on("pageerror", (e) => errors.push(`${label}: ${e}`));
  for (const c of cities) {
    for (const v of label === "mobile" ? ["feed"] : views) {
      await p.goto(`${base}/${c}/${v}/`);
      await p.waitForTimeout(v === "map" ? 1800 : 900);
      await p.screenshot({ path: `${out}/${c}-${v}-${label}.png` });
    }
  }
  await p.close();
}
await b.close();
console.log(`screenshots → ${out}`, errors.length ? errors : "no page errors");
