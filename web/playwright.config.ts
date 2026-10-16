import { defineConfig, devices } from "@playwright/test";

// Smoke tests run against the fictional demo dataset (`gotc demo --anchor 2026-10-16T15:00:00+00:00`)
// with the browser clock frozen at that anchor, so they're deterministic and never touch real sources.
export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://localhost:4174", trace: "retain-on-failure" },
  webServer: { command: "npx vite --port 4174 --strictPort", port: 4174, reuseExistingServer: !process.env.CI },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
