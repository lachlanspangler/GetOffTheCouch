import type { Event } from "./types";
import { dayKey, parts } from "./time";

export type When = "today" | "tomorrow" | "weekend" | "week" | "month" | "all";
export type Size = "any" | "small" | "medium" | "large";

export interface Filters {
  q: string;
  cats: string[]; // taxonomy ids (top-level or child)
  when: When;
  free: boolean;
  maxPrice: number | null;
  social: boolean;
  size: Size;
  near: string | null; // neighborhood name
  radiusKm: number;
  tags: string[]; // all must be present
}

export const DEFAULT_FILTERS: Filters = {
  q: "",
  cats: [],
  when: "month",
  free: false,
  maxPrice: null,
  social: false,
  size: "any",
  near: null,
  radiusKm: 5,
  tags: [],
};

export const SIZE_LABEL: Record<Size, string> = {
  any: "Any size",
  small: "Intimate (<50)",
  medium: "Medium (50–1k)",
  large: "Big (1k+)",
};

export const WHEN_LABEL: Record<When, string> = {
  today: "Today",
  tomorrow: "Tomorrow",
  weekend: "This weekend",
  week: "Next 7 days",
  month: "Next 30 days",
  all: "Everything",
};

export function km(a: [number, number], b: [number, number]): number {
  const R = 6371;
  const dLat = ((b[0] - a[0]) * Math.PI) / 180;
  const dLon = ((b[1] - a[1]) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 + Math.cos((a[0] * Math.PI) / 180) * Math.cos((b[0] * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

function matchesWhen(e: Event, when: When, tz: string, now: Date): boolean {
  const start = new Date(e.start).getTime();
  const end = e.end ? new Date(e.end).getTime() : start + 3 * 3600_000;
  const t = now.getTime();
  // openings and live deadlines don't have a meaningful "when"
  if (e.kind === "opening") return when === "all" || when === "month" || when === "week";
  if (end < t - 30 * 60_000) return false;
  const day = 86_400_000;
  const today = dayKey(now, tz);
  switch (when) {
    case "today":
      return dayKey(e.start, tz) === today || (start < t && end > t);
    case "tomorrow":
      return dayKey(e.start, tz) === dayKey(new Date(t + day), tz);
    case "weekend": {
      // this weekend = Friday 5pm → Sunday night (if it's already the weekend, the current one)
      const p = parts(now, tz);
      const offFri = p.weekday === 0 ? -2 : p.weekday === 6 ? -1 : 5 - p.weekday;
      const friKey = dayKey(new Date(t + offFri * day), tz);
      const sunKey = dayKey(new Date(t + (offFri + 2) * day), tz);
      const k = dayKey(e.start, tz);
      if (k < friKey || k > sunKey) return false;
      return k !== friKey || parts(e.start, tz).hour >= 17 || e.all_day === true;
    }
    case "week":
      return start < t + 7 * day;
    case "month":
      return start < t + 30 * day;
    default:
      return true;
  }
}

export function matchesCategory(e: Event, cats: string[]): boolean {
  if (!cats.length) return true;
  const all = [e.category, ...(e.categories ?? [])];
  return cats.some((c) => all.some((x) => x === c || x.startsWith(c + ".")));
}

export function sizeOf(e: Event): Size {
  const m = e.attendance?.mid;
  if (m == null) return "any";
  return m < 50 ? "small" : m < 1000 ? "medium" : "large";
}

export function applyFilters(
  events: Event[],
  f: Filters,
  tz: string,
  neighborhoods: Record<string, [number, number]>,
  now: Date = new Date(),
): Event[] {
  const q = f.q.trim().toLowerCase();
  const center = f.near ? neighborhoods[f.near] : undefined;
  return events.filter((e) => {
    const av = e.tickets?.availability;
    if ((av === "cancelled" || av === "postponed") && !q) return false; // still findable by search
    if (!matchesWhen(e, f.when, tz, now)) return false;
    if (!matchesCategory(e, f.cats)) return false;
    if (f.free && !e.price.is_free) return false;
    if (f.maxPrice != null && !e.price.is_free) {
      const lo = e.price.min ?? null;
      if (lo == null || lo > f.maxPrice) return false;
    }
    if (f.social && (e.social?.score ?? 0) < 0.7) return false;
    if (f.tags.length && !f.tags.every((t) => (e.tags ?? []).includes(t))) return false;
    if (f.size !== "any" && sizeOf(e) !== f.size) return false;
    if (center) {
      const { lat, lon } = e.location;
      if (lat == null || lon == null || km(center, [lat, lon]) > f.radiusKm) return false;
    }
    if (q) {
      const hay = `${e.title} ${e.summary ?? ""} ${e.location.venue_name ?? ""} ${e.organizer ?? ""} ${(e.tags ?? []).join(" ")}`.toLowerCase();
      if (!q.split(/\s+/).every((w) => hay.includes(w))) return false;
    }
    return true;
  });
}

export interface Grouped {
  event: Event; // the next occurrence
  more: number; // other upcoming occurrences in the series
}

/** One card per series (the next occurrence), keeping order by start. */
export function collapseSeries(events: Event[]): Grouped[] {
  const out: Grouped[] = [];
  const bySeries = new Map<string, Grouped>();
  for (const e of [...events].sort((a, b) => a.start.localeCompare(b.start))) {
    if (!e.series_id) {
      out.push({ event: e, more: 0 });
      continue;
    }
    const g = bySeries.get(e.series_id);
    if (g) g.more += 1;
    else {
      const ng = { event: e, more: 0 };
      bySeries.set(e.series_id, ng);
      out.push(ng);
    }
  }
  return out;
}

export interface DeadlineItem {
  event: Event;
  at: string;
  kind: "closes" | "early_bird" | "opens";
  hours: number;
  derived: boolean; // no published date (e.g. "registration required" → before it starts)
}

/** Every upcoming deadline across events, soonest first. */
export function deadlines(events: Event[], now: Date = new Date()): DeadlineItem[] {
  const out: DeadlineItem[] = [];
  const seen = new Set<string>();
  for (const e of events) {
    const r = e.registration;
    if (!r) continue;
    const key = e.series_id ?? e.id;
    for (const [kind, at] of [
      ["closes", r.closes_at],
      ["early_bird", r.early_bird_ends_at],
      ["opens", r.opens_at],
    ] as const) {
      if (!at) continue;
      const hours = (new Date(at).getTime() - now.getTime()) / 3_600_000;
      if (hours < 0) continue;
      const k = `${key}:${kind}:${at}`;
      if (seen.has(k)) continue;
      seen.add(k);
      out.push({ event: e, at, kind, hours, derived: r.method === "derived" });
    }
  }
  return out.sort((a, b) => a.at.localeCompare(b.at));
}

export function urgency(hours: number): "now" | "soon" | "week" | "later" {
  return hours <= 48 ? "now" : hours <= 24 * 7 ? "soon" : hours <= 24 * 30 ? "week" : "later";
}

/** Long-running things (exhibits, multi-week faires) that would otherwise repeat on every day of the feed. */
export function isOngoing(e: Event, now: Date = new Date()): boolean {
  if (!e.end) return false;
  const start = new Date(e.start).getTime();
  const end = new Date(e.end).getTime();
  return end - start > 36 * 3600_000 && start < now.getTime() + 86_400_000;
}
