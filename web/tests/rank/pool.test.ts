// `npm run eval:pool`: TREC-style pooling for labeling (RANKING.md §3.1). For every city × persona, the union of
// v1's top 20, v2's top 20 (before and after diversification) and three random-weight variants' top 10. Writes
// a labeling sheet sorted by id (never by any ranker's order) to $GOTC_POOL_OUT. Skipped in normal test runs.

import { writeFileSync } from "node:fs";
import { describe, it } from "vitest";
import type { Event } from "../../src/lib/types";
import { seededRng } from "../../src/lib/rank/explore";
import { forYouV2, rankV2 } from "../../src/lib/rank/index";
import { FEATURES, type Weights } from "../../src/lib/rank/types";
import { DEFAULT_WEIGHTS } from "../../src/lib/rank/weights";
import { CITIES, ctxFor, PERSONAS, persona, runV1, snapshot } from "./evalLib";
import { dayKey, fmtTime, weekdayShort } from "../../src/lib/time";

const OUT = process.env.GOTC_POOL_OUT;

describe.skipIf(!OUT)("eval:pool", () => {
  it("writes labeling sheets", () => {
    for (const city of (process.env.GOTC_POOL_CITIES ?? CITIES.join(",")).split(",")) {
      const s = snapshot(city);
      const ids = new Set<string>();
      for (const pid of PERSONAS) {
        const p = persona(pid, city);
        runV1(s, p, 20).forEach((x) => ids.add(x.event.id));
        forYouV2(s.events, ctxFor(s, p), 20).forEach((x) => ids.add(x.event.id));
        rankV2(s.events, { ...ctxFor(s, p), surface: "for_you" }).slice(0, 20).forEach((x) => ids.add(x.event.id));
        for (let v = 0; v < 3; v++) {
          const rng = seededRng(`${city}|${pid}|${v}`);
          const w = Object.fromEntries(FEATURES.map((f) => [f, DEFAULT_WEIGHTS[f] * (0.5 + 1.5 * rng())])) as Weights;
          forYouV2(s.events, ctxFor(s, p, { weights: w, explore: false }), 10).forEach((x) => ids.add(x.event.id));
        }
      }
      const byId = new Map(s.events.map((e) => [e.id, e]));
      const rows = [...ids].sort().map((id) => line(byId.get(id)!));
      writeFileSync(`${OUT}/pool_${city}.txt`, rows.join("\n") + "\n");
    }
  });
});

function line(e: Event): string {
  const tz = e.timezone;
  const price = e.price.is_free ? "free" : e.price.min != null ? `$${e.price.min}` : "?";
  const tags = (e.tags ?? []).filter((t) => !["registration_required", "recurring", "free"].includes(t)).join(",");
  return [
    e.id,
    e.title.slice(0, 70),
    (e.location.venue_name ?? "-").slice(0, 35),
    `${weekdayShort(e.start, tz)} ${dayKey(e.start, tz).slice(5)} ${e.all_day ? "allday" : fmtTime(e.start, tz)}`,
    e.kind === "one_off" ? "" : e.kind,
    e.category,
    price,
    tags,
    `soc${e.social?.score ?? "?"}`,
    e.sources[0]?.source_id,
    (e.rank?.flags ?? []).join(","),
    e.series_id ? "S" : "",
    (e.summary ?? "").replace(/\s+/g, " ").slice(0, 90),
  ].join(" | ");
}
