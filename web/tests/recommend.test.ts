import { describe, expect, it } from "vitest";
import { buildPlan, DEFAULT_PROFILE, highlights, rank, scoreEvent } from "../src/lib/recommend";
import { ev, NOW } from "./helpers";

const labels = { "trivia_games.trivia": "Trivia nights", trivia_games: "Trivia & games", music: "Music" };

describe("scoreEvent", () => {
  it("explains every point it adds", () => {
    const e = ev({ category: "trivia_games.trivia", price: { currency: "USD", is_free: true }, social: { score: 0.85, reasons: ["Trivia: great"] }, tags: ["solo_friendly"], series_id: "x" });
    const s = scoreEvent(e, { ...DEFAULT_PROFILE, interests: ["trivia_games.trivia"] }, labels, {}, NOW)!;
    const texts = s.reasons.map((r) => r.text);
    expect(texts).toContain("You picked Trivia nights");
    expect(texts).toContain("It's free");
    expect(texts).toContain("Easy to show up solo");
    expect(s.score).toBeGreaterThan(2);
  });

  it("penalizes things outside budget and time, and drops cancelled/sold out", () => {
    const pricey = ev({ price: { currency: "USD", is_free: false, min: 80 } });
    const s = scoreEvent(pricey, { ...DEFAULT_PROFILE, budget: "free", interests: ["music"] }, labels, {}, NOW)!;
    expect(s.reasons.some((r) => r.weight < 0 && r.text.includes("$80"))).toBe(true);
    expect(scoreEvent(ev({ tickets: { availability: "sold_out" } as never }), DEFAULT_PROFILE, labels, {}, NOW)).toBeNull();
  });
});

describe("buildPlan", () => {
  it("fills weeks without overlaps, one per series, diverse families", () => {
    const events = [
      ev({ id: "t1", category: "trivia_games.trivia", series_id: "tri", start: "2026-10-20T00:00:00Z", social: { score: 0.9 } }),
      ev({ id: "t2", category: "trivia_games.trivia", series_id: "tri", start: "2026-10-27T00:00:00Z", social: { score: 0.9 } }),
      ev({ id: "c1", category: "music.concert", start: "2026-10-20T00:30:00Z" }), // overlaps t1
      ev({ id: "c2", category: "music.concert", start: "2026-10-22T01:00:00Z" }),
    ];
    const plan = buildPlan(events, { ...DEFAULT_PROFILE, interests: ["trivia_games", "music"] }, labels, {}, NOW);
    const ids = plan.weeks.flatMap((w) => w.picks.map((p) => p.event.id));
    expect(ids).toContain("t1");
    expect(ids).not.toContain("t2"); // same series
    expect(ids).not.toContain("c1"); // overlaps
    expect(ids).toContain("c2");
  });

  it("surfaces upcoming deadlines to act on", () => {
    const league = ev({ category: "sports_league.kickball", kind: "season", registration: { closes_at: "2026-10-25T04:59:00Z" } as never, social: { score: 0.9 } });
    const plan = buildPlan([league], { ...DEFAULT_PROFILE, interests: ["sports_league"] }, labels, {}, NOW);
    expect(plan.deadlines.map((d) => d.event.id)).toEqual([league.id]);
  });

  it("ranks interest matches first", () => {
    const r = rank([ev({ category: "music.concert" }), ev({ category: "trivia_games.trivia" })], { ...DEFAULT_PROFILE, interests: ["trivia_games"] }, labels, {}, NOW);
    expect(r[0].event.category).toBe("trivia_games.trivia");
  });
});

describe("weather", () => {
  it("demotes rainy outdoor picks and explains why", () => {
    const wet = ev({ category: "fitness.run_club", weather: { short: "Rain", precip_pct: 80, source: "nws", fetched_at: "2026-10-16T00:00:00Z" } as never });
    const dry = ev({ category: "fitness.run_club", weather: { short: "Sunny", precip_pct: 0, source: "nws", fetched_at: "2026-10-16T00:00:00Z" } as never });
    const p = { ...DEFAULT_PROFILE, interests: ["fitness"] };
    const sw = scoreEvent(wet, p, labels, {}, NOW)!;
    const sd = scoreEvent(dry, p, labels, {}, NOW)!;
    expect(sw.score).toBeLessThan(sd.score);
    expect(sw.reasons.some((r) => r.text.includes("80% chance of rain"))).toBe(true);
  });
});

describe("highlights", () => {
  it("picks soon, located, social things across different families", () => {
    const loc = { venue_name: "Somewhere" };
    const evs = [
      ev({ category: "trivia_games.trivia", social: { score: 0.9 }, location: loc, start: "2026-10-18T00:00:00Z" }),
      ev({ category: "trivia_games.trivia", social: { score: 0.9 }, location: loc, start: "2026-10-19T00:00:00Z" }),
      ev({ category: "sports_league.kickball", social: { score: 0.9 }, location: loc, start: "2026-10-20T00:00:00Z" }),
      ev({ category: "music.concert", social: { score: 0.75 }, location: loc, start: "2026-10-21T00:00:00Z" }),
      ev({ category: "volunteer.one_off", social: { score: 0.85 }, location: {}, start: "2026-10-21T00:00:00Z" }), // no place
      ev({ category: "arts.museum", social: { score: 0.5 }, location: loc, start: "2026-11-30T00:00:00Z" }), // too far out
    ];
    evs.forEach((e, i) => (e.sources = [{ source_id: `src${i}`, record_id: "r", fetched_at: "2026-10-16T00:00:00Z" }]));
    const h = highlights(evs, {}, NOW, 3);
    const fams = h.map((s) => s.event.category.split(".")[0]);
    expect(new Set(fams).size).toBe(3);
    expect(fams).not.toContain("volunteer");
    expect(fams).not.toContain("arts");
  });
});

describe("highlights source diversity", () => {
  it("caps any single source at two picks", () => {
    const loc = { venue_name: "Lib" };
    const evs = ["trivia_games.trivia", "fitness.yoga", "arts.workshop", "learning.language"].map((c, i) =>
      ev({ category: c, social: { score: 0.9 }, location: loc, start: `2026-10-1${7 + i}T00:00:00Z` }),
    );
    expect(highlights(evs, {}, NOW, 4)).toHaveLength(2);
  });
  it("demotes kids/teen programs for adults", () => {
    const s = scoreEvent(ev({ category: "arts.books", tags: ["kids_teens"] }), DEFAULT_PROFILE, {}, {}, NOW)!;
    expect(s.reasons.some((r) => r.text === "Aimed at kids or teens" && r.weight < 0)).toBe(true);
  });
});
