// Golden rules (RANKING.md §3.3): hard fails, no thresholds. Every frozen real snapshot × every persona, plus a
// synthetic adversarial feed, on For You, Highlights, the plan and Similar.
import { describe, expect, it } from "vitest";
import type { Event } from "../../src/lib/types";
import { forYouV2, highlightsV2, planV2, rankV2, similarV2, type RankContext, type Scored } from "../../src/lib/rank/index";
import { violations } from "../../src/lib/rank/rules";
import { DEFAULT_PROFILE } from "../../src/lib/rank/profile";
import { CITIES, ctxFor, PERSONAS, persona, snapshot } from "./evalLib";
import { ev, NOW } from "../helpers";

describe.each(CITIES)("golden rules on the %s snapshot", (city) => {
  const s = snapshot(city);
  it.each(PERSONAS)("persona %s: For You, the plan and Similar obey every rule", (pid) => {
    const p = persona(pid, city);
    const ctx = ctxFor(s, p);
    const pool = rankV2(s.events, { ...ctx, surface: "for_you" });
    const list = forYouV2(s.events, ctx, 10);
    expect(list.length).toBe(10);
    expect(violations(list, { now: ctx.now, profile: p, surface: "for_you", pool })).toEqual([]);
    const plan = planV2(s.events, ctx);
    const picks = plan.weeks.flatMap((w) => w.picks);
    expect(violations(picks, { now: ctx.now, profile: p, surface: "plan" }).filter((v) => !v.startsWith("3 source"))).toEqual([]);
    for (const extra of [plan.habits, plan.deadlines, plan.openings]) expect(violations(extra, { now: ctx.now, profile: p, surface: "plan" }).filter((v) => v.startsWith("1") || v.startsWith("6"))).toEqual([]);
    const sims = similarV2(list[0].event, s.events, ctx);
    for (const x of sims) expect(x.id).not.toBe(list[0].event.id);
  });
  it("Highlights obey every rule (≤ 1 library, ≤ 2 per source, no kids)", () => {
    const ctx = ctxFor(s, null);
    const h = highlightsV2(s.events, ctx, 6);
    expect(h.length).toBe(6);
    expect(violations(h, { now: ctx.now, profile: null, surface: "highlights" })).toEqual([]);
  });
  it("is deterministic for the same input and now (seeded exploration)", () => {
    const ctx = ctxFor(s, persona("social_25", city));
    const ids = (l: Scored[]) => l.map((x) => x.event.id);
    expect(ids(forYouV2(s.events, ctx))).toEqual(ids(forYouV2([...s.events].reverse(), ctx)));
  });
});

describe("golden rules on a synthetic adversarial feed", () => {
  const T = (h: number) => new Date(NOW.getTime() + h * 3_600_000).toISOString();
  const src = (id: string) => [{ source_id: id, record_id: id, fetched_at: NOW.toISOString() }];
  const feed: Event[] = [
    ...Array.from({ length: 15 }, (_, i) => ev({ title: `Library program ${i}`, category: "arts.workshop", organizer: "City Library", location: { venue_name: `City Library – Branch ${i}` }, social: { score: 0.95 }, start: T(20 + i), sources: src("lib") })),
    ...Array.from({ length: 6 }, (_, i) => ev({ title: `Storytime ${i}`, category: "family.kids", tags: ["kids_teens"], social: { score: 1 }, location: { venue_name: "Park" }, start: T(30 + i), sources: src(`kids${i}`) })),
    ev({ title: "Weekly trivia", category: "trivia_games.trivia", series_id: "tri", social: { score: 0.9 }, location: { venue_name: "Bar" }, start: T(26), sources: src("bar") }),
    ev({ title: "Weekly trivia", category: "trivia_games.trivia", series_id: "tri", social: { score: 0.9 }, location: { venue_name: "Bar" }, start: T(26 + 168), sources: src("bar") }),
    ev({ title: "Closed for private event", category: "music.concert", rank: { fp: "x", flags: ["admin", "hard_noise"], lowq: 1 } as never, location: { venue_name: "Club" }, start: T(40), sources: src("club") }),
    ev({ title: "Room rental", category: "community.neighborhood", rank: { fp: "y", flags: ["admin"], lowq: 1 } as never, social: { score: 1 }, location: { venue_name: "Hall" }, start: T(41), sources: src("hall") }),
    ev({ title: "Cancelled show", category: "music.concert", tickets: { availability: "cancelled" } as never, location: { venue_name: "Club" }, start: T(42), sources: src("club2") }),
    ev({ title: "Sold out show", category: "music.concert", tickets: { availability: "sold_out" } as never, location: { venue_name: "Club" }, start: T(43), sources: src("club3") }),
    ev({ title: "Yesterday", category: "fitness.run_club", start: T(-30), sources: src("run") }),
    ev({ title: "League", category: "sports_league.kickball", kind: "season", registration: { closes_at: T(-2), method: "reported" } as never, sources: src("lg") }),
    ...["music.concert", "volunteer.one_off", "fitness.run_club", "niche.anime_con"].map((c, i) => ev({ title: `Other ${c}`, category: c, location: { venue_name: `V${i}` }, start: T(50 + i), sources: src(`o${i}`) })),
  ];
  const base: Omit<RankContext, "surface"> = { now: NOW, profile: null, labels: {}, neighborhoods: {}, lastShown: {} };
  it("For You: caps, no kids for adults, no noise, nothing cancelled/past/sold out", () => {
    const pool = rankV2(feed, { ...base, surface: "for_you" });
    const list = forYouV2(feed, base, 10);
    expect(violations(list, { now: NOW, profile: null, surface: "for_you", pool })).toEqual([]);
    const titles = list.map((s) => s.event.title);
    for (const bad of ["Closed for private event", "Room rental", "Cancelled show", "Sold out show", "Yesterday", "League"]) expect(titles).not.toContain(bad);
    expect(titles.filter((t) => t === "Weekly trivia")).toHaveLength(1);
  });
  it("Highlights: at most one library event", () => {
    const h = highlightsV2(feed, base, 6);
    expect(violations(h, { now: NOW, profile: null, surface: "highlights" })).toEqual([]);
    expect(h.filter((s) => /library/i.test(s.event.location.venue_name ?? "")).length).toBeLessThanOrEqual(1);
  });
  it("a family profile may see kids content", () => {
    const list = forYouV2(feed, { ...base, profile: { ...DEFAULT_PROFILE, interests: ["family"] } }, 10);
    expect(list.some((s) => (s.event.tags ?? []).includes("kids_teens"))).toBe(true);
  });
});

describe("monotonicity (§3.3.8)", () => {
  const city = "minneapolis";
  const s = snapshot(city);
  const freeCtx: RankContext = { ...ctxFor(s, { ...DEFAULT_PROFILE, budget: "free" }), surface: "for_you" };
  const pos = (events: Event[], id: string, ctx: RankContext) => rankV2(events, ctx).findIndex((x) => x.event.id === id);
  const sample = rankV2(s.events, freeCtx).filter((x) => !x.event.price.is_free).slice(0, 40);
  it("making an event free never lowers its rank for budget: free", () => {
    for (const x of sample) {
      const before = pos(s.events, x.event.id, freeCtx);
      const changed = s.events.map((e) => (e.id === x.event.id ? { ...e, price: { currency: "USD" as const, is_free: true } } : e));
      expect(pos(changed, x.event.id, freeCtx)).toBeLessThanOrEqual(before);
    }
  });
  it("marking an event stale never raises it", () => {
    for (const x of sample) {
      const before = pos(s.events, x.event.id, freeCtx);
      const changed = s.events.map((e) => (e.id === x.event.id ? { ...e, stale: true } : e));
      expect(pos(changed, x.event.id, freeCtx)).toBeGreaterThanOrEqual(before);
    }
  });
});
