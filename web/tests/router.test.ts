import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS } from "../src/lib/filters";
import { build, parseHash, parsePath, setTitleLookup } from "../src/lib/router";
import { eventPath, idFromEventSegment, slugify } from "../src/lib/site";

describe("router", () => {
  it("round-trips view + filters through the URL", () => {
    const filters = { ...DEFAULT_FILTERS, cats: ["music", "trivia_games"], when: "weekend" as const, free: true, near: "Uptown", tags: [] };
    const h = build({ city: "minneapolis", view: "map", eventId: null, filters, day: null, ids: [] });
    expect(h).toBe("/minneapolis/map/?cats=music%2Ctrivia_games&when=weekend&free=1&near=Uptown");
    const [p, q] = h.split("?");
    expect(parsePath(p, q)).toMatchObject({ city: "minneapolis", view: "map", filters: { cats: ["music", "trivia_games"], when: "weekend", free: true, near: "Uptown" } });
  });

  it("uses clean landing paths for hub presets", () => {
    expect(build({ city: "chicago", view: "feed", filters: { ...DEFAULT_FILTERS, cats: ["music"] } })).toBe("/chicago/concerts/");
    expect(build({ city: "chicago", view: "feed", filters: { ...DEFAULT_FILTERS, when: "weekend" } })).toBe("/chicago/this-weekend/");
    expect(build({ city: "chicago", view: "feed", filters: DEFAULT_FILTERS })).toBe("/chicago/");
    expect(parsePath("/chicago/free/")).toMatchObject({ city: "chicago", view: "feed", hub: "free", filters: { free: true } });
    // a hub plus an extra filter falls back to query parameters
    expect(build({ city: "chicago", view: "feed", filters: { ...DEFAULT_FILTERS, cats: ["music"], q: "jazz" } })).toBe("/chicago/?q=jazz&cats=music");
  });

  it("builds pretty event paths and parses them back to the id", () => {
    setTitleLookup((id) => (id === "evt_ab12cd34ef56ab78" ? "Trivia Night @ Bar & Grill!" : undefined));
    expect(build({ city: "nyc", eventId: "evt_ab12cd34ef56ab78" })).toBe("/nyc/events/trivia-night-bar-and-grill-ab12cd34ef56ab78/");
    expect(parsePath("/nyc/events/trivia-night-bar-and-grill-ab12cd34ef56ab78/")).toMatchObject({ city: "nyc", eventId: "evt_ab12cd34ef56ab78" });
    expect(parsePath("/nyc/events/ab12cd34ef56ab78/").eventId).toBe("evt_ab12cd34ef56ab78");
    expect(idFromEventSegment("2026-season-kickoff-ab12cd34ef56ab78")).toBe("evt_ab12cd34ef56ab78");
    expect(eventPath("nyc", "evt_ff00ff00ff00ff00")).toBe("nyc/events/ff00ff00ff00ff00/");
  });

  it("translates legacy hash links", () => {
    expect(parseHash("#/nyc/event/evt_abc")).toMatchObject({ city: "nyc", eventId: "evt_abc" });
    expect(parseHash("#/minneapolis/deadlines")).toMatchObject({ city: "minneapolis", view: "deadlines" });
    expect(parseHash("#/minneapolis/feed?when=weekend")).toMatchObject({ city: "minneapolis", view: "feed", filters: { when: "weekend" } });
    expect(parsePath("/")).toMatchObject({ city: null, view: "feed" });
  });

  it("has site-wide pages without a city", () => {
    expect(parsePath("/about/")).toMatchObject({ city: null, view: "about" });
    expect(build({ city: null, view: "privacy" })).toBe("/privacy/");
  });

  it("slugifies titles", () => {
    expect(slugify("Café Olé — Live! 2026")).toBe("cafe-ole-live-2026");
    expect(slugify("a".repeat(30) + " " + "b".repeat(40)).length).toBeLessThanOrEqual(60);
  });
});

describe("shared lists", () => {
  it("round-trips ids", () => {
    const h = build({ city: "nyc", view: "saved", eventId: null, filters: DEFAULT_FILTERS, day: null, ids: ["evt_a", "evt_b"] });
    expect(parsePath(h.split("?")[0], h.split("?")[1]).ids).toEqual(["evt_a", "evt_b"]);
  });
});
