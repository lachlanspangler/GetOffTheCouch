// Honest per-city coverage: how many sources feed a city and what it's strongest in, from the data itself.
import { family } from "./categories";
import type { CityFeed, TaxonomyEntry } from "./types";

export interface Coverage {
  sources: number; // enabled sources that delivered something
  strongest: string[]; // family labels, most listings first
  thin: string[]; // families with fewer than 5 upcoming listings
  text: string; // "14 sources, strongest in concerts and volunteering"
}

const PLURAL: Record<string, string> = {
  music: "music",
  sports_league: "rec leagues",
  nightlife: "nightlife",
  community: "community events",
  food_drink: "food and drink",
  volunteer: "volunteering",
  niche: "cons and niche events",
  trivia_games: "trivia and games",
  fitness: "fitness",
  outdoors: "outdoors",
  arts: "arts",
  sports_watch: "games to watch",
  family: "family events",
  learning: "classes and talks",
};

export function coverage(feed: CityFeed, tax: Record<string, TaxonomyEntry>, now: Date): Coverage {
  const sources = (feed.sources ?? []).filter((s) => s.state !== "disabled" && (s.records ?? 0) > 0).length;
  const counts = new Map<string, number>();
  for (const e of feed.events) {
    if (e.kind === "opening" || new Date(e.start).getTime() < now.getTime() - 86_400_000) continue;
    const f = family(e.category);
    counts.set(f, (counts.get(f) ?? 0) + 1);
  }
  const ranked = [...counts.entries()].filter(([f]) => f !== "other").sort((a, b) => b[1] - a[1]);
  const strongest = ranked.slice(0, 2).map(([f]) => PLURAL[f] ?? tax[f]?.label.toLowerCase() ?? f);
  const thin = Object.keys(PLURAL).filter((f) => (counts.get(f) ?? 0) < 5).map((f) => PLURAL[f]);
  const text = `${sources} source${sources === 1 ? "" : "s"}${strongest.length ? `, strongest in ${strongest.join(" and ")}` : ""}`;
  return { sources, strongest, thin, text };
}
