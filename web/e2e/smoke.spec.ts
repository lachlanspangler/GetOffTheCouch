import { expect, test } from "@playwright/test";

const ANCHOR = new Date("2026-10-16T15:00:00Z");

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(ANCHOR);
});

test("home lists the demo city and flags demo data", async ({ page }) => {
  await page.goto("/?demo=1");
  await expect(page.getByRole("status").first()).toContainText("Sample data");
  await expect(page.getByRole("link", { name: "Demoville" }).first()).toBeVisible();
});

test("feed shows rows, filters narrow them, and the URL keeps state", async ({ page, isMobile }) => {
  await page.goto("/demoville/?demo=1");
  const cards = page.getByTestId("event-card");
  await expect(cards.first()).toBeVisible();
  const before = await cards.count();
  if (isMobile) {
    await page.getByRole("button", { name: /^Filters/ }).click();
    await page.getByRole("dialog").getByLabel("Free only").check();
    await page.getByRole("button", { name: /^Show \d+ event/ }).click();
  } else {
    await page.getByRole("button", { name: "Price" }).click();
    await page.getByRole("button", { name: "Free only" }).click();
  }
  await expect(page).toHaveURL(/\/demoville\/free\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Free things to do in Demoville/);
  expect(await cards.count()).toBeLessThan(before);
  await expect(page.getByText("Tuesday Trivia").first()).toBeVisible();
});

test("event page shows merged sources, price comparison and provenance", async ({ page }) => {
  await page.goto("/demoville/concerts/?demo=1");
  await page.getByRole("link", { name: /Placeholder Band/ }).first().click();
  await expect(page).toHaveURL(/\/demoville\/events\/[a-z0-9-]*placeholder-band-[0-9a-f]+\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Placeholder Band/);
  await expect(page.getByRole("cell", { name: "Example Tickets", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Example Resale", exact: true })).toBeVisible();
  await expect(page.getByText(/listings are not seats/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Where this comes from" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Report a problem with this listing/ })).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/demoville\/concerts\/(\?demo=1)?$/);
});

test("legacy hash links redirect to real paths", async ({ page }) => {
  await page.goto("/?demo=1#/demoville/deadlines");
  await expect(page).toHaveURL(/\/demoville\/deadlines\/$/);
  await expect(page.getByRole("heading", { level: 1, name: "Deadlines" })).toBeVisible();
});

test("deadlines view groups by urgency and offers calendar export", async ({ page }) => {
  await page.goto("/demoville/deadlines/?demo=1");
  await expect(page.getByRole("heading", { name: "This week" })).toBeVisible();
  await expect(page.getByText("Fall Kickball League").first()).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /to your calendar/ }).first().click();
  expect((await download).suggestedFilename()).toMatch(/deadlines.*\.ics$/);
});

test("new-in-town wizard builds an explained plan", async ({ page }) => {
  await page.goto("/demoville/plan/?demo=1");
  await page.getByText("Trivia & games", { exact: true }).click();
  await page.getByText("Rec & beer leagues", { exact: true }).click();
  for (let i = 0; i < 2; i++) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Make my plan" }).click();
  await expect(page.getByRole("heading", { name: /Your first month in Demoville/ })).toBeVisible();
});

test("data status page explains source states", async ({ page }) => {
  await page.goto("/demoville/health/?demo=1");
  await expect(page.getByRole("heading", { level: 1, name: /Data status/ })).toBeVisible();
  await expect(page.getByText("Demo source A")).toBeVisible();
});

test("map view renders pins and a list", async ({ page }) => {
  await page.goto("/demoville/map/?demo=1");
  await expect(page.locator(".leaflet-overlay-pane canvas").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/on the map/)).toContainText(/^[1-9]\d* on the map/);
});

test("unknown paths render a friendly page, not a blank one", async ({ page }) => {
  await page.goto("/demoville/no-such-page/?demo=1");
  await expect(page.getByRole("heading", { name: /couldn't find that page/ })).toBeVisible();
});

test("after the wizard, the city page has an explained For you section, and 'Not for me' can be undone", async ({ page }) => {
  await page.goto("/demoville/plan/?demo=1");
  await page.getByText("Trivia & games", { exact: true }).click();
  for (let i = 0; i < 2; i++) await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Make my plan" }).click();
  await page.goto("/demoville/?demo=1");
  const section = page.getByRole("region", { name: "For you" }).or(page.locator("section[aria-labelledby=foryou]"));
  await expect(section).toBeVisible();
  await section.getByText("Why this?").first().click();
  await expect(section.getByText(/on your device/).first()).toBeVisible();
  await section.getByTestId("event-card").first().getByRole("link").click();
  await page.getByRole("button", { name: "Not for me" }).click();
  await expect(page.getByRole("status").filter({ hasText: "fewer like this" })).toBeVisible();
  await page.getByRole("button", { name: "Undo" }).click();
});
