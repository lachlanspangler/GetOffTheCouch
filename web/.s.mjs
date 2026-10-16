import { chromium } from "@playwright/test";
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1280, height: 1000 } });
const errs=[]; p.on("pageerror", e=>errs.push(String(e)));
const t0=Date.now(); await p.goto("http://localhost:5173/#/nyc/feed"); await p.getByTestId("event-card").first().waitFor(); console.log("first card ms", Date.now()-t0);
await p.screenshot({ path: "/tmp/gotc-shots/nyc.png" });
await p.goto("http://localhost:5173/#/"); await p.waitForTimeout(800); await p.screenshot({ path: "/tmp/gotc-shots/home2.png" });
console.log(errs); await b.close();
