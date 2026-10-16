// I-051: neighborhood "vibe" from what actually happens there — counts of upcoming events by category
// family within ~1.5 km of each neighborhood's centroid. Purely descriptive; shown with the counts.
import type { Event } from "./types";
import { km } from "./filters";

export interface Vibe {
  name: string;
  total: number;
  top: { family: string; n: number }[];
  free: number;
}

export function vibes(events: Event[], hoods: { name: string; lat: number; lon: number }[], radiusKm = 1.5): Vibe[] {
  return hoods
    .map((h) => {
      const near = events.filter(
        (e) => e.location.lat != null && e.location.lon != null && km([h.lat, h.lon], [e.location.lat, e.location.lon]) <= radiusKm,
      );
      const counts = new Map<string, number>();
      for (const e of near) {
        const f = e.category.split(".")[0];
        if (f !== "other") counts.set(f, (counts.get(f) ?? 0) + 1);
      }
      const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([family, n]) => ({ family, n }));
      return { name: h.name, total: near.length, top, free: near.filter((e) => e.price.is_free).length };
    })
    .sort((a, b) => b.total - a.total);
}
