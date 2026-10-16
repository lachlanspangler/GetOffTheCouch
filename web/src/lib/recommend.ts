// Recommendations that explain themselves. Pure functions: (events, profile, now) → ranked picks + reasons.
//
// Every point added to a score comes with the sentence that justifies it, so the UI can always answer
// "why is this here?". Nothing here is learned from other users; it's transparent rules over your choices.

import type { Event } from "./types";
import { km, liveAvailability } from "./filters";
import { hoursUntil, parts } from "./time";

export type Goal = "meet_people" | "stay_active" | "culture" | "party" | "give_back" | "nerd_out";
export type Budget = "free" | "cheap" | "any";
export type Slot = "weeknights" | "weekends" | "daytime";

export interface Profile {
  interests: string[]; // taxonomy ids
  goals: Goal[];
  budget: Budget;
  times: Slot[];
  neighborhood: string | null;
  solo: boolean;
  startDate?: string | null; // "2026-11-01" — plan starts here if later than today (moving soon)
}

export const DEFAULT_PROFILE: Profile = {
  interests: [],
  goals: ["meet_people"],
  budget: "any",
  times: ["weeknights", "weekends"],
  neighborhood: null,
  solo: true,
  startDate: null,
};

export const GOALS: Record<Goal, { label: string; families: string[]; weight: number }> = {
  meet_people: { label: "Meet people", families: [], weight: 0 },
  stay_active: { label: "Stay active", families: ["fitness", "sports_league", "outdoors"], weight: 0.5 },
  culture: { label: "Arts & culture", families: ["arts", "music"], weight: 0.4 },
  party: { label: "Go out", families: ["nightlife", "music", "food_drink"], weight: 0.4 },
  give_back: { label: "Give back", families: ["volunteer", "community"], weight: 0.55 },
  nerd_out: { label: "Nerd out", families: ["niche", "trivia_games", "learning"], weight: 0.5 },
};

export interface Reason {
  text: string;
  weight: number;
}

export interface Scored {
  event: Event;
  score: number;
  reasons: Reason[];
}

const CHEAP = 30;

export function slotOf(e: Event): Slot {
  const p = parts(e.start, e.timezone);
  if (p.weekday === 0 || p.weekday === 6 || (p.weekday === 5 && p.hour >= 17)) return "weekends";
  return p.hour >= 17 ? "weeknights" : "daytime";
}

function family(id: string): string {
  return id.split(".")[0];
}

export function scoreEvent(
  e: Event,
  profile: Profile,
  labels: Record<string, string>,
  neighborhoods: Record<string, [number, number]>,
  now: Date = new Date(),
): Scored | null {
  const avail = liveAvailability(e, now);
  if (avail === "cancelled" || avail === "sold_out" || avail === "postponed") return null;
  if (avail === "registration_closed" && (e.kind === "season" || e.registration?.closes_at)) return null;
  const reasons: Reason[] = [];
  const add = (weight: number, text: string) => reasons.push({ weight, text });
  const cats = [e.category, ...(e.categories ?? [])];

  // 1. interests
  const exact = profile.interests.find((i) => i.includes(".") && cats.includes(i));
  const fam = profile.interests.find((i) => !i.includes(".") && cats.some((c) => family(c) === i));
  if (exact) add(1.0, `You picked ${labels[exact] ?? exact}`);
  else if (fam) add(0.7, `You're into ${labels[fam] ?? fam}`);
  else if (profile.interests.length) add(-0.3, "Outside your picks — a wildcard");

  // 2. goals
  for (const g of profile.goals) {
    if (g === "meet_people") {
      const s = e.social?.score ?? 0.4;
      if (s >= 0.7) add(0.8 * s, e.social?.reasons?.[0] ?? "Good for meeting people");
      else if (s < 0.4) add(-0.2, "Not much mingling");
    } else if (GOALS[g].families.includes(family(e.category))) {
      add(GOALS[g].weight, `Fits "${GOALS[g].label}"`);
    }
  }

  // 3. budget
  const lo = e.price.min ?? null;
  if (e.price.is_free) add(profile.budget === "free" ? 0.5 : 0.2, "It's free");
  else if (lo != null) {
    if (profile.budget === "free") add(-1.2, `Costs from $${Math.round(lo)}`);
    else if (profile.budget === "cheap" && lo > CHEAP) add(-0.6, `Pricier (from $${Math.round(lo)})`);
  }

  // 4. time slot
  const slot = slotOf(e);
  if (e.kind !== "opening" && e.kind !== "season") {
    if (profile.times.length && !profile.times.includes(slot)) add(-0.7, `It's ${slot === "daytime" ? "during the workday" : `on ${slot}`}`);
  }

  // 5. distance
  const center = profile.neighborhood ? neighborhoods[profile.neighborhood] : undefined;
  const { lat, lon } = e.location;
  if (center && lat != null && lon != null) {
    const d = km(center, [lat, lon]);
    if (d < 2) add(0.35, `${d.toFixed(1)} km from ${profile.neighborhood}`);
    else if (d < 5) add(0.15, `${d.toFixed(1)} km from ${profile.neighborhood}`);
    else if (d > 12) add(-0.3, `${Math.round(d)} km away`);
  }

  // 6. going solo / becoming a regular
  const tags = e.tags ?? [];
  const wantsFamily = profile.interests.some((i) => i === "family" || i.startsWith("family."));
  if (tags.includes("kids_teens") && !wantsFamily) add(-0.9, "Aimed at kids or teens");
  if (tags.includes("campus")) add(-0.25, "Campus event (may be student-focused)");
  if (profile.solo && (tags.includes("solo_friendly") || tags.includes("free_agent"))) add(0.35, "Easy to show up solo");
  if (tags.includes("beginner_friendly")) add(0.15, "Beginner friendly");
  if (e.series_id || e.kind === "recurring") add(0.2, "Repeats — you can become a regular");

  // 7. deadlines make things urgent
  const closes = e.registration?.closes_at;
  if (closes) {
    const h = hoursUntil(closes, now);
    if (h > 0 && h < 24 * 14) add(0.25, `Registration closes in ${Math.max(1, Math.round(h / 24))} day${h < 36 ? "" : "s"}`);
  }
  if (e.tickets?.selling_fast) add(0.1, "Selling fast");
  const rain = e.weather?.precip_pct ?? null;
  if (rain != null && rain >= 60) add(-0.4, `${Math.round(rain)}% chance of rain (NWS)`);
  else if (e.weather && rain != null && rain < 20 && /sunny|clear/i.test(e.weather.short)) add(0.1, `Forecast: ${e.weather.short.toLowerCase()}`);
  if (e.stale) add(-0.3, "Details may be out of date");

  const score = reasons.reduce((s, r) => s + r.weight, 0);
  reasons.sort((a, b) => b.weight - a.weight);
  return { event: e, score: Math.round(score * 100) / 100, reasons };
}

export function rank(
  events: Event[],
  profile: Profile,
  labels: Record<string, string>,
  neighborhoods: Record<string, [number, number]>,
  now: Date = new Date(),
): Scored[] {
  return events
    .filter((e) => new Date(e.end ?? e.start).getTime() >= now.getTime() || e.kind === "opening")
    .map((e) => scoreEvent(e, profile, labels, neighborhoods, now))
    .filter((s): s is Scored => s !== null)
    .sort((a, b) => b.score - a.score || a.event.start.localeCompare(b.event.start));
}

export interface PlanWeek {
  label: string;
  from: string;
  picks: Scored[];
}

export interface Plan {
  weeks: PlanWeek[];
  habits: Scored[]; // recurring social things to become a regular at
  deadlines: Scored[]; // registrations to act on soon
  openings: Scored[]; // new places to try
}

function overlaps(a: Event, b: Event): boolean {
  const as = new Date(a.start).getTime();
  const ae = a.end ? new Date(a.end).getTime() : as + 2 * 3600_000;
  const bs = new Date(b.start).getTime();
  const be = b.end ? new Date(b.end).getTime() : bs + 2 * 3600_000;
  return as < be && bs < ae;
}

/**
 * First 30 days: up to `perWeek` picks per week, greedy by score with constraints —
 * no overlapping times, one occurrence per series, and a diversity penalty per repeated family.
 */
export function buildPlan(
  events: Event[],
  profile: Profile,
  labels: Record<string, string>,
  neighborhoods: Record<string, [number, number]>,
  now: Date = new Date(),
  perWeek = 3,
): Plan {
  const start = profile.startDate && new Date(profile.startDate) > now ? new Date(profile.startDate) : now;
  const ranked = rank(events, profile, labels, neighborhoods, now).filter((s) => s.score > 0.2);
  const chosen: Event[] = [];
  const usedSeries = new Set<string>();
  const famCount = new Map<string, number>();
  const weeks: PlanWeek[] = [];
  const week = 7 * 86_400_000;
  for (let w = 0; w < 4; w++) {
    const from = new Date(start.getTime() + w * week);
    const to = new Date(from.getTime() + week);
    const pool = ranked.filter((s) => {
      const t = new Date(s.event.start).getTime();
      return t >= from.getTime() && t < to.getTime() && s.event.kind !== "opening" && s.event.kind !== "season";
    });
    const picks: Scored[] = [];
    while (picks.length < perWeek) {
      let best: Scored | null = null;
      let bestAdj = -Infinity;
      for (const s of pool) {
        if (picks.includes(s)) continue;
        if (s.event.series_id && usedSeries.has(s.event.series_id)) continue;
        if (chosen.some((c) => overlaps(c, s.event))) continue;
        const adj = s.score - 0.45 * (famCount.get(family(s.event.category)) ?? 0);
        if (adj > bestAdj) {
          best = s;
          bestAdj = adj;
        }
      }
      if (!best) break;
      picks.push(best);
      chosen.push(best.event);
      if (best.event.series_id) usedSeries.add(best.event.series_id);
      const f = family(best.event.category);
      famCount.set(f, (famCount.get(f) ?? 0) + 1);
    }
    picks.sort((a, b) => a.event.start.localeCompare(b.event.start));
    weeks.push({ label: w === 0 ? "Week 1 — get out there" : `Week ${w + 1}`, from: from.toISOString(), picks });
  }
  const horizon = start.getTime() + 30 * 86_400_000;
  const picked = new Set(chosen.map((e) => e.id));
  const deadlines = ranked
    .filter((s) => !picked.has(s.event.id))
    .filter((s) => {
      const c = s.event.registration?.closes_at;
      return c && new Date(c).getTime() > now.getTime() && new Date(c).getTime() < horizon;
    })
    .filter((s, i, arr) => !s.event.series_id || arr.findIndex((x) => x.event.series_id === s.event.series_id) === i)
    .slice(0, 6);
  const openings = ranked.filter((s) => s.event.kind === "opening").slice(0, 5);
  // weekly habits: the fastest way to know people in a new city is seeing the same faces every week
  const seenSeries = new Set<string>();
  const habits = ranked
    .filter((s) => (s.event.series_id || s.event.kind === "recurring") && (s.event.social?.score ?? 0) >= 0.7)
    .filter((s) => !(s.event.tags ?? []).includes("kids_teens"))
    .filter((s) => {
      const k = s.event.series_id ?? s.event.title;
      if (seenSeries.has(k)) return false;
      seenSeries.add(k);
      return true;
    })
    .slice(0, 3);
  return { weeks, deadlines, openings, habits };
}

/** Default highlights for someone who hasn't set preferences: social, concrete, soon, diverse. */
export function highlights(events: Event[], labels: Record<string, string>, now: Date = new Date(), n = 6): Scored[] {
  const week = now.getTime() + 7 * 86_400_000;
  const pool = events.filter(
    (e) =>
      e.kind !== "opening" &&
      !e.all_day &&
      new Date(e.start).getTime() >= now.getTime() &&
      new Date(e.start).getTime() <= week &&
      !!(e.location.venue_name || e.location.address) &&
      !/^(usa|united states|us|online|tbd|tba)$/i.test((e.location.venue_name ?? "").trim()) &&
      !(e.tags ?? []).some((t) => t === "campus" || t === "kids_teens"),
  );
  const ranked = rank(pool, { ...DEFAULT_PROFILE, interests: [] }, labels, {}, now);
  const out: Scored[] = [];
  const fams = new Map<string, number>();
  const series = new Set<string>();
  const perSource = new Map<string, number>();
  for (const s of ranked) {
    if (s.score <= 0) break;
    const f = family(s.event.category);
    const src = s.event.sources[0]?.source_id ?? "";
    if ((fams.get(f) ?? 0) >= 1 && out.length < n - 1) continue; // one per family until the last slot
    if ((perSource.get(src) ?? 0) >= 2) continue; // no single source dominates the front page
    const isLibrary = /\blibrary\b/i.test(`${s.event.location.venue_name ?? ""} ${s.event.organizer ?? ""}`);
    if (isLibrary && out.some((o) => /\blibrary\b/i.test(`${o.event.location.venue_name ?? ""} ${o.event.organizer ?? ""}`))) continue;
    if (s.event.series_id && series.has(s.event.series_id)) continue;
    out.push(s);
    fams.set(f, (fams.get(f) ?? 0) + 1);
    perSource.set(src, (perSource.get(src) ?? 0) + 1);
    if (s.event.series_id) series.add(s.event.series_id);
    if (out.length >= n) break;
  }
  // a city is also its music: reserve one slot for the best show this week if none made it in
  if (!out.some((s) => family(s.event.category) === "music")) {
    const show = ranked.find((s) => family(s.event.category) === "music" && !s.event.tags?.includes("campus") && !out.includes(s));
    if (show) {
      if (out.length >= n) out.pop();
      out.push({ ...show, reasons: [{ text: "A show worth seeing this week", weight: 0.1 }, ...show.reasons] });
    }
  }
  return out;
}

/** "Similar this week": same family, upcoming within 7 days, nearest first when we know where both are. */
export function similar(e: Event, events: Event[], now: Date = new Date(), n = 4): Event[] {
  const fam = family(e.category);
  const t0 = now.getTime();
  const week = t0 + 7 * 86_400_000;
  const here = e.location.lat != null && e.location.lon != null ? ([e.location.lat, e.location.lon] as [number, number]) : null;
  const seen = new Set<string>([e.series_id ?? e.id]);
  return events
    .filter((x) => x.id !== e.id && family(x.category) === fam && x.kind !== "opening")
    .filter((x) => {
      const t = new Date(x.start).getTime();
      return t >= t0 && t <= week && liveAvailability(x, now) !== "cancelled";
    })
    .map((x) => ({
      x,
      d: here && x.location.lat != null && x.location.lon != null ? km(here, [x.location.lat, x.location.lon]) : 50,
    }))
    .sort((a, b) => a.d - b.d || a.x.start.localeCompare(b.x.start))
    .map((r) => r.x)
    .filter((x) => {
      const k = x.series_id ?? x.id;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .slice(0, n);
}
