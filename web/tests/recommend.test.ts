import { describe, expect, it } from "vitest";
import { buildPlan, DEFAULT_PROFILE, rank, scoreEvent } from "../src/lib/recommend";
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
