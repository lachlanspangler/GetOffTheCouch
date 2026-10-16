import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ANCHOR = new Date("2026-10-16T15:00:00Z");

for (const view of ["feed", "deadlines", "calendar", "plan", "health"]) {
  test(`no serious accessibility violations: ${view}`, async ({ page }) => {
    await page.clock.setFixedTime(ANCHOR);
    await page.goto(`/?demo=1#/demoville/${view}`);
    await page.waitForLoadState("networkidle");
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.length} × ${v.nodes[0]?.target}`)).toEqual([]);
  });
}
