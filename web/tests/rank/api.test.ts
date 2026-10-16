// recommend.ts public API under v2 (the default): the same callers (Plan, Highlights, Similar) keep working.
import { beforeEach, describe, expect, it } from "vitest";
import {
  buildPlan,
  DEFAULT_PROFILE,
  dismiss,
  forYou,
  highlights,
  rank,
  RANKER_V2,
  rankerVersion,
  scoreEvent,
  similar,
  whyThis,
} from "../../src/lib/recommend";
import { recordSignal } from "../../src/lib/rank/affinityStore";
import { ev, NOW } from "../helpers";

const labels = { "trivia_games.trivia": "Trivia nights", trivia_games: "Trivia & games", music: "Music" };
const src = (e: ReturnType<typeof ev>, id: string) => ((e.sources = [{ source_id: id, record_id: e.id, fetched_at: "2026-10-16T00:00:00Z" }]), e);

beforeEach(() => localStorage.clear());

describe("v2 behind the flag", () => {
  it("is the default ranker, and localStorage can switch back to v1", () => {
    expect(RANKER_V2).toBe(true);
    expect(rankerVersion()).toBe("v2");
    localStorage.setItem("gotc:ranker", "v1");
    expect(rankerVersion()).toBe("v1");
  });

  it("scoreEvent explains with ≤ 3 reasons + 1 caveat, each tied to a score term", () => {
    const e = ev({ category: "trivia_games.trivia", price: { currency: "USD", is_free: true }, social: { score: 0.85, reasons: ["Trivia: great"] }, tags: ["solo_friendly"], series_id: "x" });
    const s = scoreEvent(e, { ...DEFAULT_PROFILE, interests: ["trivia_games.trivia"] }, labels, {}, NOW)!;
    expect(s.reasons.filter((r) => r.kind !== "caveat").length).toBeLessThanOrEqual(3);
    expect(s.reasons[0].text).toBe("You picked Trivia nights");
    for (const r of s.reasons) expect(Math.abs(s.contrib![r.feature!])).toBeGreaterThan(0);
    expect(scoreEvent(ev({ tickets: { availability: "sold_out" } as never }), DEFAULT_PROFILE, labels, {}, NOW)).toBeNull();
  });

  it("rank() puts interest matches first and drops cancelled", () => {
    const r = rank([ev({ category: "music.concert" }), ev({ category: "trivia_games.trivia" }), ev({ tickets: { availability: "cancelled" } as never })], { ...DEFAULT_PROFILE, interests: ["trivia_games"] }, labels, {}, NOW);
    expect(r[0].event.category).toBe("trivia_games.trivia");
    expect(r).toHaveLength(2);
  });

  it("buildPlan: no overlaps, one per series, deadlines, habits", () => {
    const events = [
      ev({ id: "t1", category: "trivia_games.trivia", series_id: "tri", start: "2026-10-20T00:00:00Z", social: { score: 0.9 } }),
      ev({ id: "t2", category: "trivia_games.trivia", series_id: "tri", start: "2026-10-27T00:00:00Z", social: { score: 0.9 } }),
      ev({ id: "c1", category: "music.concert", start: "2026-10-20T00:30:00Z" }),
      ev({ id: "c2", category: "music.concert", start: "2026-10-22T01:00:00Z" }),
      ev({ id: "lg", category: "sports_league.kickball", kind: "season", registration: { closes_at: "2026-10-25T04:59:00Z" } as never, social: { score: 0.9 } }),
    ];
    const plan = buildPlan(events, { ...DEFAULT_PROFILE, interests: ["trivia_games", "music", "sports_league"] }, labels, {}, NOW);
    const ids = plan.weeks.flatMap((w) => w.picks.map((p) => p.event.id));
    expect(ids.filter((i) => i === "t1" || i === "t2")).toHaveLength(1);
    expect(ids.includes("t1") && ids.includes("c1")).toBe(false); // they overlap
    expect(plan.deadlines.map((d) => d.event.id)).toContain("lg");
    expect(plan.habits.map((h) => h.event.series_id)).toEqual(["tri"]);
  });

  it("highlights: soon, located, different families, ≤ 2 per source, no kids", () => {
    const loc = { venue_name: "Somewhere" };
    const evs = [
      src(ev({ category: "trivia_games.trivia", social: { score: 0.9 }, location: loc, start: "2026-10-18T00:00:00Z" }), "a"),
      src(ev({ category: "trivia_games.trivia", social: { score: 0.9 }, location: loc, start: "2026-10-19T00:00:00Z" }), "b"),
      src(ev({ category: "sports_league.kickball", social: { score: 0.9 }, location: loc, start: "2026-10-20T00:00:00Z" }), "c"),
      src(ev({ category: "music.concert", social: { score: 0.75 }, location: loc, start: "2026-10-21T00:00:00Z" }), "d"),
      src(ev({ category: "volunteer.one_off", social: { score: 0.85 }, location: {}, start: "2026-10-21T00:00:00Z" }), "e"), // no place
      src(ev({ category: "family.kids", tags: ["kids_teens"], social: { score: 0.9 }, location: loc, start: "2026-10-18T15:00:00Z" }), "f"),
      src(ev({ category: "arts.museum", social: { score: 0.5 }, location: loc, start: "2026-11-30T00:00:00Z" }), "g"), // too far out
    ];
    const h = highlights(evs, {}, NOW, 3);
    const fams = h.map((s) => s.event.category.split(".")[0]);
    expect(new Set(fams).size).toBe(3);
    expect(fams).not.toContain("volunteer");
    expect(fams).not.toContain("family");
    expect(fams).not.toContain("arts");
    const same = ["trivia_games.trivia", "fitness.yoga", "arts.workshop", "learning.language"].map((c, i) => ev({ category: c, social: { score: 0.9 }, location: loc, start: `2026-10-1${7 + i}T00:00:00Z` }));
    expect(highlights(same, {}, NOW, 4)).toHaveLength(2); // one source ("s") → at most 2
  });

  it("similar: same family this week, nearest first, never the same series", () => {
    const base = ev({ category: "music.concert", series_id: "b", location: { lat: 44.98, lon: -93.27 } });
    const near = ev({ category: "music.concert", location: { lat: 44.981, lon: -93.271 }, start: "2026-10-18T00:00:00Z" });
    const far = ev({ category: "music.festival", location: { lat: 45.2, lon: -93.0 }, start: "2026-10-18T02:00:00Z" });
    const sib = ev({ category: "music.concert", series_id: "b", start: "2026-10-19T00:00:00Z" });
    const other = ev({ category: "trivia_games.trivia", start: "2026-10-18T00:00:00Z" });
    const later = ev({ category: "music.concert", start: "2026-12-01T00:00:00Z" });
    expect(similar(base, [base, far, near, sib, other, later], NOW).map((x) => x.id)).toEqual([near.id, far.id]);
  });
});

describe("dismiss + on-device signals", () => {
  it("dismissed events (and their series) leave every surface", () => {
    const a = ev({ category: "trivia_games.trivia", series_id: "s1", social: { score: 0.9 }, location: { venue_name: "Bar" }, start: "2026-10-18T00:00:00Z" });
    const a2 = ev({ category: "trivia_games.trivia", series_id: "s1", social: { score: 0.9 }, location: { venue_name: "Bar" }, start: "2026-10-25T00:00:00Z" });
    const b = src(ev({ category: "music.concert", location: { venue_name: "Club" }, start: "2026-10-19T00:00:00Z" }), "z");
    dismiss(a);
    const ids = forYou([a, a2, b], null, labels, {}, NOW).map((s) => s.event.id);
    expect(ids).toEqual([b.id]);
    expect(highlights([a, a2, b], labels, NOW).map((s) => s.event.id)).toEqual([b.id]);
  });

  it("'Why am I seeing this?' includes the personal part once enough is learned", () => {
    const pool = [0, 1, 2, 3, 4, 5].map((i) => src(ev({ category: "trivia_games.trivia", social: { score: 0.9 }, venue_id: `v${i}`, start: `2026-10-1${7 + (i % 3)}T00:00:00Z` }), `s${i}`));
    const music = [0, 1, 2].map((i) => src(ev({ category: "music.concert", venue_id: `m${i}`, start: "2026-10-18T01:00:00Z" }), `m${i}`));
    const t0 = NOW.getTime() - 86_400_000;
    for (const e of pool.slice(0, 3)) recordSignal(e, "save", undefined, t0);
    for (const e of pool.slice(3, 5)) recordSignal(e, "calendar", undefined, t0);
    const list = forYou([...pool, ...music], null, labels, {}, NOW);
    const trivia = list.find((s) => s.event.category === "trivia_games.trivia")!;
    const why = whyThis(trivia, { profile: null, labels, cityName: "Testville" });
    expect(why.personal?.text).toMatch(/^You saved 3 and added 2 to your calendar · Trivia nights$/);
    expect(why.personal!.contribution).toBeGreaterThan(0);
    expect(why.headline).toBe("Picked for someone new to Testville");
    expect(why.privacy).toMatch(/Nothing is sent anywhere/);
  });
});
