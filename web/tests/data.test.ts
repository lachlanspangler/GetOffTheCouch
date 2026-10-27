// I-117: week-sharded city data. The loader fetches the manifest, then only the shards a view needs, merges them in
// the pipeline's order (so the merged feed equals the legacy file), and falls back to the legacy file without a manifest.
import { existsSync, readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CityData, needFor, priority } from "../src/lib/data";

const D = `${process.cwd()}/public/demo/`;
const haveShards = existsSync(`${D}cities/demoville/manifest.json`); // `gotc demo` writes it

function serve(opts: { noManifest?: boolean; gone?: Set<string> } = {}): string[] {
  const asked: string[] = [];
  vi.stubGlobal("fetch", async (url: string) => {
    const path = url.replace(/^\/data\//, "");
    asked.push(path);
    const file = `${D}${path}`;
    if ((opts.noManifest && path.endsWith("manifest.json")) || opts.gone?.has(path) || !existsSync(file)) {
      return { ok: false, status: 404, json: async () => ({}) };
    }
    return { ok: true, status: 200, json: async () => JSON.parse(readFileSync(file, "utf8")) };
  });
  return asked;
}

afterEach(() => vi.unstubAllGlobals());

describe.skipIf(!haveShards)("sharded city data", () => {
  const legacy = () => JSON.parse(readFileSync(`${D}cities/demoville.json`, "utf8"));
  const manifest = () => JSON.parse(readFileSync(`${D}cities/demoville/manifest.json`, "utf8"));
  const now = () => new Date(legacy().generated_at);
  const pastIds = () =>
    new Set(
      manifest()
        .shards.filter((s: { kind: string }) => s.kind === "past")
        .flatMap((s: { cards: { file: string } }) => JSON.parse(readFileSync(`${D}cities/demoville/${s.cards.file}`, "utf8")).events.map((e: { id: string }) => e.id)),
    );

  it("loads the current and next week first, then everything, equal to the legacy feed", async () => {
    const asked = serve();
    const c = new CityData("demoville");
    const first = await c.ensure(priority(now()));
    const m = manifest();
    const want = m.shards.filter((s: { kind: string; starts?: string }) =>
      s.kind === "ongoing" || s.kind === "deadlines" || (s.kind === "week" && Date.parse(`${s.starts}T00:00:00Z`) < now().getTime() + 8 * 86_400_000),
    );
    expect(asked.filter((p) => p.includes("/w/")).sort()).toEqual(want.map((s: { cards: { file: string } }) => `cities/demoville/${s.cards.file}`).sort());
    expect(first.events.length).toBeLessThan(legacy().events.length);
    const upcoming = await c.all();
    expect(upcoming.events.length).toBe(legacy().events.filter((e: { id: string }) => !pastIds().has(e.id)).length);
    const all = await c.ensure({ until: Infinity, all: true, past: true });
    expect(all).toEqual(legacy()); // same events in the same order, same metadata
  });

  it("falls back to the legacy file when there's no manifest", async () => {
    const asked = serve({ noManifest: true });
    const f = await new CityData("demoville").ensure(priority(now()));
    expect(f).toEqual(legacy());
    expect(asked).toContain("cities/demoville.json");
  });

  it("reads one card's details from its shard's details file", async () => {
    const asked = serve();
    const c = new CityData("demoville");
    const all = await c.all();
    const e = all.events[0];
    const details = JSON.parse(readFileSync(`${D}cities/demoville.details.json`, "utf8"));
    expect(await c.detail(e.id)).toEqual(details.events[e.id]);
    expect(asked.some((p) => p.includes("/d/"))).toBe(true);
    expect(asked).not.toContain("cities/demoville.details.json");
  });

  it("starts over from a fresh manifest once when a shard has gone (a deploy in between)", async () => {
    const m = manifest();
    const week = m.shards.find((s: { kind: string }) => s.kind === "week");
    let first = true;
    const asked: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      const path = url.replace(/^\/data\//, "");
      asked.push(path);
      if (first && path.endsWith(week.cards.file)) {
        first = false;
        return { ok: false, status: 404, json: async () => ({}) };
      }
      return { ok: true, status: 200, json: async () => JSON.parse(readFileSync(`${D}${path}`, "utf8")) };
    });
    const f = await new CityData("demoville").all({ until: Infinity, all: true, past: true });
    expect(f).toEqual(legacy());
    expect(asked.filter((p) => p.endsWith("manifest.json")).length).toBe(2);
  });
});

describe("what a view needs", () => {
  const now = new Date("2026-10-21T15:00:00Z");
  it("asks for more weeks only when the filter reaches them", () => {
    expect(needFor("feed", "week", null, now)).toEqual({ until: now.getTime() + 8 * 86_400_000, openings: true });
    expect(needFor("feed", "today", null, now).openings).toBeUndefined();
    expect(needFor("feed", "month", null, now).until).toBe(now.getTime() + 31 * 86_400_000);
    expect(needFor("feed", "all", null, now).all).toBe(true);
    expect(needFor("calendar", "week", null, now)).toEqual({ until: Infinity, all: true });
    expect(needFor("feed", "week", "evt_1", now)).toEqual({ until: Infinity, all: true, past: true });
    expect(needFor("saved", "week", null, now).past).toBe(true);
    expect(needFor("deadlines", "week", null, now)).toEqual(priority(now));
  });
});
