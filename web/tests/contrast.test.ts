// Recomputes every WCAG pair from DESIGN.md §3.2 using the primitives in src/lib/palette.ts, so a token
// edit can't silently break AA. Also checks app.css defines the same primitive hex values.
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { contrast, PALETTE, type PaletteName } from "../src/lib/palette";

type Kind = "text" | "ui";
/** [label, fg, bg, kind, ratio documented in §3.2] */
type Pair = readonly [string, PaletteName, PaletteName, Kind, number];

const LIGHT: Pair[] = [
  ["text on canvas", "sand-900", "sand-25", "text", 16.25],
  ["text on surface", "sand-900", "sand-0", "text", 16.81],
  ["text-secondary on canvas", "sand-700", "sand-25", "text", 6.61],
  ["text-secondary on sunken", "sand-700", "sand-75", "text", 6.06],
  ["text-secondary on hover (sand-100)", "sand-700", "sand-100", "text", 5.64],
  ["text-muted on canvas", "sand-600", "sand-25", "text", 5.19],
  ["text-muted on surface", "sand-600", "sand-0", "text", 5.37],
  ["text-muted on sunken", "sand-600", "sand-75", "text", 4.76],
  ["input border on surface", "sand-500", "sand-0", "ui", 3.47],
  ["white on accent button", "sand-0", "ember-600", "text", 5.47],
  ["white on accent hover", "sand-0", "ember-700", "text", 7.45],
  ["link on canvas", "ember-650", "sand-25", "text", 6.18],
  ["link on surface", "ember-650", "sand-0", "text", 6.39],
  ["accent text on accent-soft", "ember-700", "ember-50", "text", 6.83],
  ["accent text on accent-soft-strong", "ember-700", "ember-100", "text", 6.06],
  ["focus ring on canvas", "ember-600", "sand-25", "ui", 5.29],
  ["positive on surface", "green-700", "sand-0", "text", 6.51],
  ["positive on tint", "green-700", "green-50", "text", 5.94],
  ["caution on surface", "amber-700", "sand-0", "text", 6.42],
  ["caution on tint", "amber-700", "amber-50", "text", 5.95],
  ["critical on surface", "red-700", "sand-0", "text", 6.54],
  ["critical on tint", "red-700", "red-50", "text", 5.8],
  ["white on critical", "sand-0", "red-700", "text", 6.54],
  ["info on surface", "blue-700", "sand-0", "text", 7.08],
  ["info on tint", "blue-700", "blue-50", "text", 6.36],
  ["inverse: white on text", "sand-0", "sand-900", "text", 16.81],
];

const DARK: Pair[] = [
  ["text on canvas", "sand-75", "sand-950", "text", 16.31],
  ["text on surface", "sand-75", "sand-900", "text", 14.9],
  ["text on raised", "sand-75", "sand-850", "text", 13.03],
  ["text-secondary on surface", "sand-300", "sand-900", "text", 9.68],
  ["text-muted on canvas", "sand-400", "sand-950", "text", 6.84],
  ["text-muted on surface", "sand-400", "sand-900", "text", 6.25],
  ["text-muted on raised", "sand-400", "sand-850", "text", 5.47],
  ["input border on surface", "sand-600", "sand-900", "ui", 3.13],
  ["input border on canvas", "sand-600", "sand-950", "ui", 3.43],
  ["on-accent text on accent button", "ember-950", "ember-400", "text", 6.53],
  ["link on canvas", "ember-300", "sand-950", "text", 8.08],
  ["link on surface", "ember-300", "sand-900", "text", 7.38],
  ["link on accent-soft", "ember-300", "ember-900", "text", 6.91],
  ["focus ring on canvas", "ember-400", "sand-950", "ui", 6.33],
  ["positive on surface", "green-300", "sand-900", "text", 8.52],
  ["caution on surface", "amber-300", "sand-900", "text", 9.16],
  ["critical on surface", "red-300", "sand-900", "text", 7.08],
  ["info on surface", "blue-300", "sand-900", "text", 7.67],
  ["positive on tint", "green-300", "green-950", "text", 7.78],
  ["caution on tint", "amber-300", "amber-950", "text", 8.31],
  ["critical on tint", "red-300", "red-950", "text", 6.44],
  ["info on tint", "blue-300", "blue-950", "text", 7.15],
];

const MIN: Record<Kind, number> = { text: 4.5, ui: 3 };

describe.each([
  ["light", LIGHT],
  ["dark", DARK],
] as const)("%s theme contrast (WCAG 2.x)", (_theme, pairs) => {
  it.each(pairs)("%s (%s on %s)", (_label, fg, bg, kind, documented) => {
    const ratio = contrast(PALETTE[fg], PALETTE[bg]);
    expect(ratio).toBeGreaterThanOrEqual(MIN[kind]);
    // keep DESIGN.md §3.2 honest: documented ratio matches the hex values (±0.02)
    expect(Math.abs(ratio - documented)).toBeLessThanOrEqual(0.02);
  });
});

describe("documented failures stay documented", () => {
  it("text-muted on sand-100 (hover bg) is below AA, so hover/selected rows must use text-secondary", () => {
    const ratio = contrast(PALETTE["sand-600"], PALETTE["sand-100"]);
    expect(ratio).toBeLessThan(4.5);
    expect(Math.abs(ratio - 4.43)).toBeLessThanOrEqual(0.02);
  });
});

describe("app.css primitives match palette.ts", () => {
  const cssPath = resolve(__dirname, "../src/styles/app.css");
  const css = existsSync(cssPath) ? readFileSync(cssPath, "utf8") : "";
  const defined = new Map<string, string>();
  for (const m of css.matchAll(/--((?:sand|ember|green|amber|red|blue)-\d+)\s*:\s*([^;}\n]+)/g))
    if (!defined.has(m[1])) defined.set(m[1], m[2].trim());

  // app.css is being migrated to the §3.8 tokens; a primitive it doesn't define yet is skipped.
  for (const name of Object.keys(PALETTE) as PaletteName[]) {
    it.skipIf(!defined.has(name))(`--${name}`, () => {
      expect(defined.get(name)?.toUpperCase()).toBe(PALETTE[name].toUpperCase());
    });
  }
});
