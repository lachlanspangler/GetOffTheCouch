import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS } from "../src/lib/filters";
import { build, parse } from "../src/lib/router";

describe("router", () => {
  it("round-trips view + filters through the URL", () => {
    const filters = { ...DEFAULT_FILTERS, cats: ["music", "trivia_games"], when: "weekend" as const, free: true, near: "Uptown", tags: [] };
    const h = build({ city: "minneapolis", view: "map", eventId: null, filters, day: null, ids: [] });
    expect(h).toBe("#/minneapolis/map?cats=music%2Ctrivia_games&when=weekend&free=1&near=Uptown");
    const r = parse(h);
    expect(r).toMatchObject({ city: "minneapolis", view: "map", filters: { cats: ["music", "trivia_games"], when: "weekend", free: true, near: "Uptown" } });
  });

  it("parses event deep links", () => {
    expect(parse("#/nyc/event/evt_abc")).toMatchObject({ city: "nyc", eventId: "evt_abc" });
    expect(parse("")).toMatchObject({ city: null, view: "feed" });
  });
});

describe("shared lists", () => {
  it("round-trips ids", () => {
    const h = build({ city: "nyc", view: "saved", eventId: null, filters: DEFAULT_FILTERS, day: null, ids: ["evt_a", "evt_b"] });
    expect(parse(h).ids).toEqual(["evt_a", "evt_b"]);
  });
});
