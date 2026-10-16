import { describe, expect, it } from "vitest";
import { parsePath } from "../src/lib/router";
import { eventJsonLd, headFor, headHtml, isMarkupEvent, safeJson } from "../src/lib/seo";
import type { CityFeed, Index } from "../src/lib/types";
import { ev, NOW } from "./helpers";

const index = { schema_version: "1", generated_at: NOW.toISOString(), taxonomy: {}, tags: {}, cities: [] } as unknown as Index;
const feed = (events = [ev()]) => ({ city: "testville", city_name: "Testville", timezone: "America/Chicago", events, sources: [] }) as unknown as CityFeed;

describe("Event JSON-LD", () => {
  it("only marks up real events, never openings or seasons", () => {
    expect(isMarkupEvent(ev({ kind: "one_off" }))).toBe(true);
    expect(isMarkupEvent(ev({ kind: "opening" }))).toBe(false);
    expect(isMarkupEvent(ev({ kind: "season" }))).toBe(false);
  });

  it("includes only reported prices and a named place", () => {
    const e = ev({
      location: { venue_name: "The Hall", address: "1 Main St" },
      offers: [{ seller: "Box Office", kind: "primary", url: "https://x.test/t", price_min: 25, fetched_at: NOW.toISOString(), availability: "on_sale" } as never],
    });
    const j = eventJsonLd(e, "https://site.test/e/") as Record<string, any>;
    expect(j["@type"]).toBe("Event");
    expect(j.location).toMatchObject({ name: "The Hall", address: "1 Main St" });
    expect(j.offers[0]).toMatchObject({ price: 25, priceCurrency: "USD" });
    const noPrice = eventJsonLd(ev({ offers: [{ seller: "S", kind: "primary", url: "https://x.test", fetched_at: NOW.toISOString() } as never] }), "u") as Record<string, any>;
    expect(noPrice.offers[0].price).toBeUndefined();
  });

  it("escapes < so a title can't close the script tag", () => {
    expect(safeJson({ name: "</script><script>alert(1)" })).not.toContain("</script>");
  });
});

describe("page heads", () => {
  it("gives event pages a canonical, a description and Event markup", () => {
    const e = ev({ id: "evt_ab12cd34", title: "Kickball Night" });
    const route = parsePath("/testville/events/kickball-night-ab12cd34/");
    const h = headFor(route, index, feed([e]), e, NOW);
    expect(h.canonical).toMatch(/\/testville\/events\/(kickball-night-)?ab12cd34\/$/);
    expect(h.robots).toBe("index,follow");
    expect(h.jsonld.some((j) => (j as { "@type": string })["@type"] === "Event")).toBe(true);
    expect(h.description.length).toBeGreaterThan(20);
    expect(headHtml(h)).toContain('<link rel="canonical"');
  });

  it("noindexes thin hubs and app views", () => {
    expect(headFor(parsePath("/testville/trivia/"), index, feed(), undefined, NOW).robots).toBe("noindex,follow");
    expect(headFor(parsePath("/testville/map/"), index, feed(), undefined, NOW).robots).toBe("noindex,follow");
    expect(headFor(parsePath("/testville/"), index, feed(), undefined, NOW).robots).toBe("index,follow");
  });
});
