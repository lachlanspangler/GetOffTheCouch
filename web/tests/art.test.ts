import { describe, expect, it } from "vitest";
import { artSvg, cityArt, FAMILIES, familyOf, hash, rng, T, type Family } from "../src/lib/art";

const SAFE = /^[<>\w\s="\-.:/#(),;%]+$/;
const elements = (svg: string): number => (svg.match(/<[a-z]+/g) ?? []).length;
const ids = (n: number, prefix = "evt"): string[] => {
  const r = rng(hash(prefix));
  return Array.from({ length: n }, (_, i) => `${prefix}-${i}-${Math.floor(r() * 1e9).toString(36)}`);
};
const ALLOWED_PAINT = new Set<string>([...Object.values(T), "none"]);

describe("familyOf", () => {
  it("uses the first dot segment and maps unknowns to other", () => {
    expect(familyOf("music.concert")).toBe("music");
    expect(familyOf("trivia_games")).toBe("trivia_games");
    expect(familyOf("sports_league.kickball.coed")).toBe("sports_league");
    expect(familyOf("bogus.thing")).toBe("other");
    expect(familyOf("")).toBe("other");
    expect(familyOf("constructor")).toBe("other");
  });
});

describe("artSvg", () => {
  it("covers all 15 families", () => {
    expect(FAMILIES).toHaveLength(15);
  });

  it.each(FAMILIES)("%s: same input gives the identical string", (family) => {
    const a = artSvg({ id: "abc123", family });
    const b = artSvg({ id: "abc123", family });
    expect(b).toEqual(a);
    // and independent of the cache: a fresh id rendered twice
    expect(artSvg({ id: `fresh-${family}`, family }).svg).toBe(artSvg({ id: `fresh-${family}`, family }).svg);
  });

  it.each(FAMILIES)("%s: 1,000 random ids produce >= 950 distinct SVGs", (family) => {
    const seen = new Set(ids(1000).map((id) => artSvg({ id, family }).svg));
    expect(seen.size).toBeGreaterThanOrEqual(950);
  });

  it.each(FAMILIES)("%s: <= 60 elements, <= 3 KB, only T.* paint, safe charset", (family) => {
    for (const id of ids(300, family)) {
      const { svg } = artSvg({ id, family });
      expect(elements(svg)).toBeLessThanOrEqual(60);
      expect(new TextEncoder().encode(svg).length).toBeLessThanOrEqual(3072);
      expect(svg).toMatch(SAFE);
      for (const m of svg.matchAll(/(?:fill|stroke)="([^"]*)"/g)) expect(ALLOWED_PAINT.has(m[1])).toBe(true);
    }
  });

  it("never lets event data into the SVG (safety)", () => {
    const evil = `<script>alert("x")</script>' onload="steal()`;
    const title = "Big Thief at First Avenue";
    for (const family of FAMILIES) {
      const { svg, hue, shift } = artSvg({ id: evil, family, title });
      expect(svg).toMatch(SAFE);
      expect(svg).not.toContain("script");
      expect(svg).not.toContain("steal");
      expect(svg).not.toContain("Thief");
      expect(Number.isFinite(hue)).toBe(true);
      expect([-20, 0, 20]).toContain(shift);
    }
  });

  it("falls back to other for an unknown family at runtime", () => {
    const { hue, svg } = artSvg({ id: "x", family: "nope" as Family });
    expect(hue).toBe(70);
    expect(svg).toBe(artSvg({ id: "x", family: "other" }).svg);
  });

  it.each(FAMILIES)("%s: snapshot", (family) => {
    expect(artSvg({ id: "snapshot-evt-0001", family })).toMatchSnapshot();
  });
});

describe("cityArt", () => {
  it("is deterministic, small, safe and distinct per slug", () => {
    const slugs = ids(1000, "city");
    const seen = new Set<string>();
    for (const slug of slugs) {
      const a = cityArt(slug);
      expect(cityArt(slug)).toEqual(a);
      expect(elements(a.svg)).toBeLessThanOrEqual(60);
      expect(new TextEncoder().encode(a.svg).length).toBeLessThanOrEqual(3072);
      expect(a.svg).toMatch(SAFE);
      for (const m of a.svg.matchAll(/(?:fill|stroke)="([^"]*)"/g)) expect(ALLOWED_PAINT.has(m[1])).toBe(true);
      seen.add(a.svg);
    }
    expect(seen.size).toBeGreaterThanOrEqual(950);
    // exactly 2 park blocks in acc
    const { svg } = cityArt("minneapolis");
    const acc = /<g fill="var\(--art-acc\)">(.*?)<\/g>/.exec(svg);
    expect(acc && (acc[1].match(/<rect/g) ?? []).length).toBe(2);
  });

  it("snapshot", () => {
    expect(cityArt("minneapolis")).toMatchSnapshot();
  });
});
