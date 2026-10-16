import { expect, test } from "@playwright/test";

const ANCHOR = new Date("2026-10-16T15:00:00Z");

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(ANCHOR);
});

test("home lists the demo city and flags demo data", async ({ page }) => {
  await page.goto("/?demo=1");
  await expect(page.getByRole("status")).toContainText("DEMO DATA");
  await expect(page.getByRole("button", { name: /Demoville/ })).toBeVisible();
});

test("feed shows cards, filters narrow them, and the URL keeps state", async ({ page }) => {
  await page.goto("/demoville/feed/?demo=1");
  const cards = page.getByTestId("event-card");
  await expect(cards.first()).toBeVisible();
  const before = await cards.count();
  const toggle = page.getByRole("button", { name: /^Filters/ });
  if (await toggle.isVisible()) await toggle.click(); // mobile keeps filters behind a toggle
  await page.getByRole("button", { name: "Free only" }).click();
  await expect(page).toHaveURL(/\/demoville\/free\/$/);
  expect(await cards.count()).toBeLessThan(before);
  await expect(page.getByText("Tuesday Trivia").first()).toBeVisible();
});

test("event drawer shows merged sources, price comparison and provenance", async ({ page }) => {
  await page.goto("/demoville/feed/?demo=1");
  await page.getByRole("link", { name: /Placeholder Band/ }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("cell", { name: "Example Tickets", exact: true })).toBeVisible();
  await expect(dialog.getByRole("cell", { name: "Example Resale", exact: true })).toBeVisible();
  await expect(dialog.getByText(/listings are not seats/).first()).toBeVisible();
  await expect(dialog.getByText("Where this came from")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("deadlines view sorts by urgency and offers calendar export", async ({ page }) => {
  await page.goto("/demoville/deadlines/?demo=1");
  await expect(page.getByRole("heading", { name: "Next 48 hours" })).toBeVisible();
  await expect(page.getByText("Fall Kickball League").first()).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /Add all .* to my calendar/ }).click();
  expect((await download).suggestedFilename()).toMatch(/deadlines\.ics$/);
});

test("new-in-town onboarding builds an explained plan", async ({ page }) => {
  await page.goto("/demoville/plan/?demo=1");
  await page.getByRole("button", { name: "Trivia & games" }).click();
  await page.getByRole("button", { name: "Rec & beer leagues" }).click();
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: /Build my first month/ }).click();
  await expect(page.getByRole("heading", { name: /Your first 30 days in Demoville/ })).toBeVisible();
  await expect(page.getByText(/You picked|You're into/).first()).toBeVisible();
});

test("health page explains source states", async ({ page }) => {
  await page.goto("/demoville/health/?demo=1");
  await expect(page.getByRole("heading", { name: /Data health/ })).toBeVisible();
  await expect(page.getByText("Demo source A")).toBeVisible();
});

test("map view renders pins", async ({ page }) => {
  await page.goto("/demoville/map/?demo=1");
  await expect(page.locator(".leaflet-overlay-pane canvas").first()).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/on the map/)).toContainText(/^[1-9]\d* on the map/);
});
