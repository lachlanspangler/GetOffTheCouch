// I-115: share cards say only what the page says (reported title, date, place, city) over the page's own art.
import { describe, expect, it } from "vitest";
import { cityCard, eventCard, homeCard, hubCard } from "../src/lib/og";
import { artSvg, familyOf } from "../src/lib/art";
import type { CityFeed, Index } from "../src/lib/types";
import { ev, NOW } from "./helpers";

const feed = { city: "testville", city_name: "Testville", state: "MN", timezone: "America/Chicago", events: [] } as unknown as CityFeed;

describe("share cards", () => {
  it("event cards carry the reported title, date and place, and the card art matches the page art", () => {
    const e = ev({ title: "Fall <Gala> & Party", start: "2026-10-24T00:30:00Z", end: "2026-10-24T03:00:00Z", location: { venue_name: "The Hall" } });
    const c = eventCard(feed, e);
    expect(c.key).toBe(`testville/e/${e.id.replace(/^evt_/, "")}`);
    expect(c.title).toBe("Fall <Gala> & Party");
    expect(c.date).toBe("Friday, October 23, 2026 · 7:30–10 PM");
    expect(c.kicker).toContain("Testville, MN");
    expect(c.art.svg).toBe(artSvg({ id: e.id, family: familyOf(e.category) }).svg);
    expect(c.art.svg).not.toContain("Gala"); // no event text ever enters the art
  });

  it("date-only events don't get a made-up time", () => {
    const c = eventCard(feed, ev({ start: "2026-10-24T05:00:00Z", all_day: true }));
    expect(c.date).toBe("Saturday, October 24, 2026");
  });

  it("city, hub and home cards", () => {
    expect(cityCard(feed, NOW).title).toBe("Things to do in Testville");
    const hub = hubCard(feed, "concerts", NOW)!;
    expect(hub.key).toBe("testville/concerts");
    expect(hub.title).toBe("Concerts & live music in Testville");
    expect(hub.art.family).toBe("music");
    expect(hubCard(feed, "this-weekend", NOW)!.date).toMatch(/Oct/);
    expect(hubCard(feed, "nope", NOW)).toBeNull();
    const index = { cities: [{}, {}] } as unknown as Index;
    expect(homeCard(index, NOW).kicker).toBe("2 US cities");
  });
});
