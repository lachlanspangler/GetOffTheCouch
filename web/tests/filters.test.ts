import { describe, expect, it } from "vitest";
import { applyFilters, collapseSeries, DEFAULT_FILTERS, deadlines, urgency } from "../src/lib/filters";
import { ev, NOW, TZ } from "./helpers";

const f = (o = {}) => ({ ...DEFAULT_FILTERS, ...o });

describe("applyFilters", () => {
  it("drops past events and respects date windows in the city timezone", () => {
    const past = ev({ start: "2026-10-15T00:00:00Z" });
    const tonight = ev({ start: "2026-10-17T01:00:00Z" }); // Fri 8pm local
    const sunday = ev({ start: "2026-10-18T18:00:00Z" });
    const nextWeek = ev({ start: "2026-10-22T00:00:00Z" });
    const all = [past, tonight, sunday, nextWeek];
    expect(applyFilters(all, f({ when: "all" }), TZ, {}, NOW)).toEqual([tonight, sunday, nextWeek]);
    expect(applyFilters(all, f({ when: "today" }), TZ, {}, NOW)).toEqual([tonight]);
    expect(applyFilters(all, f({ when: "weekend" }), TZ, {}, NOW)).toEqual([tonight, sunday]);
  });

  it("filters by category family, free, price, social, search and distance", () => {
    const trivia = ev({ category: "trivia_games.trivia", price: { currency: "USD", is_free: true }, social: { score: 0.9 } });
    const show = ev({ category: "music.concert", price: { currency: "USD", is_free: false, min: 45 }, location: { lat: 44.98, lon: -93.27 } });
    const all = [trivia, show];
    expect(applyFilters(all, f({ cats: ["trivia_games"] }), TZ, {}, NOW)).toEqual([trivia]);
    expect(applyFilters(all, f({ free: true }), TZ, {}, NOW)).toEqual([trivia]);
    expect(applyFilters(all, f({ maxPrice: 30 }), TZ, {}, NOW)).toEqual([trivia]);
    expect(applyFilters(all, f({ social: true }), TZ, {}, NOW)).toEqual([trivia]);
    expect(applyFilters([{ ...show, title: "Big Thief" }], f({ q: "big thief" }), TZ, {}, NOW)).toHaveLength(1);
    expect(applyFilters(all, f({ near: "Downtown", radiusKm: 2 }), TZ, { Downtown: [44.9765, -93.27] }, NOW)).toEqual([show]);
  });
});

describe("collapseSeries", () => {
  it("shows one card per series with a count of the rest", () => {
    const a = ev({ series_id: "s1", start: "2026-10-20T00:00:00Z" });
    const b = ev({ series_id: "s1", start: "2026-10-27T00:00:00Z" });
    const c = ev({ start: "2026-10-21T00:00:00Z" });
    const g = collapseSeries([b, c, a]);
    expect(g.map((x) => [x.event.id, x.more])).toEqual([[a.id, 1], [c.id, 0]]);
  });
});

describe("deadlines", () => {
  it("lists future deadlines soonest-first and classifies urgency", () => {
    const e1 = ev({ registration: { closes_at: "2026-10-17T04:59:00Z" } as never });
    const e2 = ev({ registration: { closes_at: "2026-11-30T04:59:00Z", opens_at: "2026-10-01T00:00:00Z" } as never });
    const d = deadlines([e2, e1], NOW);
    expect(d.map((x) => x.event.id)).toEqual([e1.id, e2.id]); // past opens_at dropped
    expect(urgency(d[0].hours)).toBe("now");
    expect(urgency(d[1].hours)).toBe("later");
  });
});
