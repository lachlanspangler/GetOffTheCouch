// Color primitives (DESIGN.md §3.8, layer 1). app.css must define the same hex values;
// tests/contrast.test.ts recomputes the §3.2 WCAG pairs from this table and checks app.css stays in sync.

export const PALETTE = {
  // Sand: warm neutral
  "sand-0": "#FFFFFF",
  "sand-25": "#FCFBF8",
  "sand-50": "#F7F5F0",
  "sand-75": "#F3F1EC",
  "sand-100": "#ECE9E2",
  "sand-200": "#E2DED5",
  "sand-300": "#C9C4BA",
  "sand-400": "#A39D93",
  "sand-500": "#8F897F",
  "sand-600": "#6F6A61",
  "sand-700": "#5F5A52",
  "sand-800": "#3A3732",
  "sand-850": "#2A2824",
  "sand-900": "#1F1D1A",
  "sand-950": "#151412",
  // Ember: the one accent
  "ember-50": "#FDF3EF",
  "ember-100": "#FBE3D9",
  "ember-200": "#F6C3AF",
  "ember-300": "#F0947A",
  "ember-400": "#E8775A",
  "ember-500": "#D4532D",
  "ember-600": "#B8421F",
  "ember-650": "#A63C1C",
  "ember-700": "#963518",
  "ember-800": "#722914",
  "ember-900": "#3A1A10",
  "ember-950": "#1A0D08",
  // Status
  "green-50": "#EDF7F0",
  "green-300": "#6FCB93",
  "green-700": "#1E6B3D",
  "green-950": "#15291D",
  "amber-50": "#FDF6E3",
  "amber-300": "#E8B85A",
  "amber-700": "#85540A",
  "amber-950": "#2E2410",
  "red-50": "#FDEEEE",
  "red-300": "#F28B8B",
  "red-700": "#B42328",
  "red-950": "#3A1D1D",
  "blue-50": "#EEF3FC",
  "blue-300": "#8DB0EE",
  "blue-700": "#2B579F",
  "blue-950": "#18233A",
} as const;

export type PaletteName = keyof typeof PALETTE;

/** sRGB relative luminance (WCAG 2.x). */
export function luminance(hex: string): number {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) throw new Error(`bad hex ${hex}`);
  const n = parseInt(m[1], 16);
  const lin = (c: number): number => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin((n >> 16) & 255) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255);
}

/** WCAG 2.x contrast ratio, 1–21. */
export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
