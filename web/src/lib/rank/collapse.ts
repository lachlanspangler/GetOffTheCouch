// 1B. Dedup and collapse before scoring (RANKING.md §1B):
//   series   → the next upcoming occurrence, with a count of the others ("+3 more dates")
//   group    → one card per multi-site program (rank.group), nearest branch else the most complete one
//   fp       → near-duplicates (rank.fp, computed in the pipeline) keep the higher-quality member

import type { Event } from "../types";
import { km } from "../filters";

export interface Collapsed {
  event: Event;
  more: number; // other occurrences in the series
  sites: number; // venues in the multi-site group (1 = single site)
}

export interface CollapseOptions {
  series?: boolean; // default true; the plan keeps occurrences and enforces one-per-series itself
  center?: [number, number] | null; // pick the branch nearest to here
}

const quality = (e: Event) => e.rank?.quality ?? 0.5;

function better(a: Event, b: Event, center: [number, number] | null | undefined): Event {
  if (center) {
    const da = a.location.lat != null && a.location.lon != null ? km(center, [a.location.lat, a.location.lon]) : 1e9;
    const db = b.location.lat != null && b.location.lon != null ? km(center, [b.location.lat, b.location.lon]) : 1e9;
    if (Math.abs(da - db) > 0.25) return da < db ? a : b;
  }
  if (quality(a) !== quality(b)) return quality(a) > quality(b) ? a : b;
  return a.start <= b.start ? a : b; // earlier occurrence, then stable
}

function collapseBy(items: Collapsed[], key: (e: Event) => string | null | undefined, pick: (a: Event, b: Event) => Event, merge: (into: Collapsed, other: Collapsed) => void): Collapsed[] {
  const out: Collapsed[] = [];
  const at = new Map<string, number>();
  for (const it of items) {
    const k = key(it.event);
    if (!k) {
      out.push(it);
      continue;
    }
    const i = at.get(k);
    if (i === undefined) {
      at.set(k, out.length);
      out.push({ ...it });
      continue;
    }
    const cur = out[i];
    const keep = pick(cur.event, it.event) === cur.event ? cur : { ...it };
    const other = keep === cur ? it : cur;
    merge(keep, other);
    out[i] = keep;
  }
  return out;
}

export function collapse(events: Event[], opts: CollapseOptions = {}): Collapsed[] {
  const sorted = [...events].sort((a, b) => a.start.localeCompare(b.start) || a.id.localeCompare(b.id));
  let items: Collapsed[] = sorted.map((event) => ({ event, more: 0, sites: event.rank?.group_n ?? 1 }));
  items = collapseBy(
    items,
    (e) => e.rank?.fp,
    (a, b) => better(a, b, null),
    () => {},
  );
  items = collapseBy(
    items,
    (e) => e.rank?.group,
    (a, b) => better(a, b, opts.center),
    (into, other) => (into.sites = Math.max(into.sites, other.sites)),
  );
  if (opts.series !== false) {
    items = collapseBy(
      items,
      (e) => e.series_id,
      (a, b) => (a.start <= b.start ? a : b), // the next upcoming occurrence
      (into, other) => (into.more += 1 + other.more),
    );
  }
  return items;
}
