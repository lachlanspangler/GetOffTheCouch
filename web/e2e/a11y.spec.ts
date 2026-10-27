import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const ANCHOR = new Date("2026-10-16T15:00:00Z");
const PAGES = ["", "demoville/", "demoville/deadlines/", "demoville/calendar/", "demoville/map/", "demoville/plan/", "demoville/saved/", "demoville/health/", "about/", "methodology/", "privacy/", "cities/"];

for (const scheme of ["light", "dark"] as const) {
  for (const path of PAGES) {
    test(`no serious accessibility violations (${scheme}): /${path}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.clock.setFixedTime(ANCHOR);
      await page.goto(`/${path}?demo=1`);
      await page.waitForLoadState("networkidle");
      const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
      const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => `${v.id}: ${v.nodes.length} × ${v.nodes[0]?.target}`)).toEqual([]);
    });
  }
  test(`no serious accessibility violations (${scheme}): event page`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.clock.setFixedTime(ANCHOR);
    await page.goto("/demoville/concerts/?demo=1");
    await page.getByRole("link", { name: /Placeholder Band/ }).first().click();
    await page.waitForLoadState("networkidle");
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${v.id}: ${v.nodes.length} × ${v.nodes[0]?.target}`)).toEqual([]);
  });
}
