// 1C. Feature extraction (RANKING.md §1C). Every feature is in [0, 1]; penalties (p_*) are 0–1 too and
// get negative weights. One small exported function per feature so each can be table-tested.
// h = hours until start, d = days.

import type { Event } from "../types";
import { km } from "../filters";
import { affinity as affinityOf } from "./affinity";
import { family, GOALS, slotOf, wantsFamily } from "./profile";
import type { Budget, Features, Profile, RankContext } from "./types";
import { NEWCOMER_PRIOR, SLOT_PRIOR } from "./weights";

const H = 3_600_000;
const clamp = (x: number, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, x));
const hoursUntil = (iso: string, now: Date) => (new Date(iso).getTime() - now.getTime()) / H;

/** 1. Plateau for the next 3 days, then a ~4.8-day half-life. Already started → 0.2. Seasons/openings: neutral 0.5. */
export function timeliness(e: Event, now: Date): number {
  if (e.kind === "season" || e.kind === "opening") return 0.5;
  const h = hoursUntil(e.start, now);
  if (h < 1) return 0.2;
  return h <= 72 ? 1 : Math.exp(-(h - 72) / 168);
}

/** 2. Logistic in days-to-close around 5 days, × registration confidence (derived deadlines are 0.5 → halved). */
export function deadlineUrgency(e: Event, now: Date): number {
  const c = e.registration?.closes_at;
  if (!c) return 0;
  const d = hoursUntil(c, now) / 24;
  if (d <= 0) return 0;
  return (1 / (1 + Math.exp((d - 5) / 1.5))) * (e.registration?.confidence ?? 1);
}

/** 3. Early-bird pricing ends within a week. */
export function earlyBird(e: Event, now: Date): number {
  const t = e.registration?.early_bird_ends_at;
  if (!t) return 0;
  const h = hoursUntil(t, now);
  return h > 0 && h <= 7 * 24 ? 1 : 0;
}

export const social = (e: Event) => e.social?.score ?? 0.4;
export const recurring = (e: Event) => (e.series_id || e.kind === "recurring" ? 1 : 0);
export const solo = (e: Event) => ((e.tags ?? []).some((t) => t === "solo_friendly" || t === "free_agent") ? 1 : 0);
export const beginner = (e: Event) =>
  (e.tags ?? []).includes("beginner_friendly") || (e.registration?.skill_levels ?? []).some((s) => s === "beginner" || s === "all") ? 1 : 0;

/** 8. Newly listed on GetOffTheCouch (is_new means newly *seen*, not a new event). */
export function novelty(e: Event, now: Date): number {
  if (e.is_new) return 1;
  const age = (now.getTime() - new Date(e.first_seen).getTime()) / H;
  return age < 0 ? 0 : Math.exp(-age / 72) * 0.5;
}

/** 9. Pipeline-computed share of 7 key fields present; neutral 0.5 when the feed predates rank hints. */
export const completeness = (e: Event) => e.rank?.complete ?? 0.5;

/** 10. ln(1 + len) / ln(401): a 400-char description is "complete". */
export function descInfo(e: Event): number {
  if (!e.rank) return 0.5;
  return clamp(Math.log(1 + (e.rank.desc_len ?? 0)) / Math.log(401));
}

export const sourceReliability = (e: Event) => e.rank?.src_rel ?? 0.8;

export function corroboration(e: Event): number {
  const n = new Set(e.sources.map((s) => s.source_id)).size;
  return clamp((n - 1) / 2);
}

/** 13. Mirrors resolve.FIELD_TRUST: curated registry > Ticketmaster > SeatGeek > everything else. */
export function fieldTrust(e: Event): number {
  const ids = e.sources.map((s) => s.source_id);
  if (ids.some((s) => s.startsWith("curated"))) return 1;
  if (ids.includes("ticketmaster")) return 0.9;
  if (ids.includes("seatgeek")) return 0.8;
  return 0.6;
}

/** 14. Free → 1, unknown → 0.5 (neutral: unknown is neither cheap nor pricey). */
export function priceFit(e: Event, budget: Budget): number {
  if (e.price.is_free) return 1;
  const p = e.price.min;
  if (p == null) return 0.5;
  if (budget === "free") return 0;
  if (budget === "cheap") return p <= 30 ? 1 : Math.exp(-(p - 30) / 30);
  return 1 - Math.min(1, p / 300) * 0.5;
}

export function distanceKm(e: Event, center: [number, number] | null | undefined): number | null {
  const { lat, lon } = e.location;
  return center && lat != null && lon != null ? km(center, [lat, lon]) : null;
}

/** 15. exp(−km / 4); unknown location or no neighborhood → 0.5. */
export function distanceFit(e: Event, center: [number, number] | null | undefined): number {
  const d = distanceKm(e, center);
  return d == null ? 0.5 : Math.exp(-d / 4);
}

/** 16. In one of your times → 1, else 0. No profile: the newcomer slot prior. Seasons/openings: neutral. */
export function timeFit(e: Event, profile: Profile | null): number {
  if (e.kind === "opening" || e.kind === "season") return 0.5;
  const slot = slotOf(e);
  if (!profile || !profile.times.length) return SLOT_PRIOR[slot];
  return profile.times.includes(slot) ? 1 : 0;
}

/** 17. Small crowds are easier to meet people in; blended toward 0.5 by the estimate's uncertainty. */
export function crowdFit(e: Event): number {
  const a = e.attendance;
  if (!a) return 0.5;
  const m = a.mid;
  const raw = m <= 250 ? 1 : m <= 5000 ? 1 - (0.6 * Math.log10(m / 250)) / Math.log10(20) : 0.4;
  const c = clamp(a.confidence);
  return raw * c + 0.5 * (1 - c);
}

/** 18. The attendance band came from a known venue capacity. */
export const establishedVenue = (e: Event) => (/venue capacity/i.test(e.attendance?.method ?? "") ? 1 : 0);

/** 19. Few tickets/spots left (reported) or a selling-fast signal (derived from resale listings). */
export function scarcity(e: Event): number {
  const t = e.tickets;
  if (!t) return 0;
  if (t.selling_fast || t.availability === "few_left" || t.availability === "limited") return 1;
  if (t.spots_left != null && t.spots_total) return t.spots_left / t.spots_total <= 0.2 ? 1 : 0;
  return 0;
}

/** 20. Outdoor only: heavy rain → 0, clear → 1, else 0.6. Indoor/unknown → 0.6. */
export function weatherFit(e: Event): number {
  if (!e.weather) return 0.6; // the pipeline only fetches forecasts for outdoor events
  const p = e.weather.precip_pct;
  if (p != null && p >= 60) return 0;
  if (p != null && p < 20 && /sunny|clear/i.test(e.weather.short)) return 1;
  return 0.6;
}

/** 21. Exact pick → 1, family pick → 0.85 (RANKING.md had 0.7: too weak against social signals), none → 0.5, no match → 0.15. */
export function interest(e: Event, profile: Profile | null): number {
  const picks = profile?.interests ?? [];
  if (!picks.length) return 0.5;
  const cats = [e.category, ...(e.categories ?? [])];
  if (picks.some((i) => i.includes(".") && cats.includes(i))) return 1;
  if (picks.some((i) => !i.includes(".") && cats.some((c) => family(c) === i))) return 0.85;
  return 0.15;
}

/** 22. Best goal match: goal weight / 0.55 for its families; "meet people" → the social score. */
export function goalFit(e: Event, profile: Profile | null): number {
  let best = 0;
  for (const g of profile?.goals ?? []) {
    if (g === "meet_people") best = Math.max(best, social(e));
    else if (GOALS[g].families.includes(family(e.category))) best = Math.max(best, GOALS[g].weight / 0.55);
  }
  return clamp(best);
}

export const categoryPrior = (e: Event) => NEWCOMER_PRIOR[family(e.category)] ?? 0.3;

/** 25. Stale flag, or how far past its source's freshness SLA the last check is. */
export function pStale(e: Event, now: Date, slaHours?: Record<string, number>): number {
  if (e.stale) return 1;
  const sla = slaHours?.[e.sources[0]?.source_id ?? ""] ?? 72;
  const since = (now.getTime() - new Date(e.last_checked).getTime()) / H;
  return clamp((since - sla) / sla);
}

export const pLowQuality = (e: Event) => e.rank?.lowq ?? 0;
export const pKidsMismatch = (e: Event, profile: Profile | null) => ((e.tags ?? []).includes("kids_teens") && !wantsFamily(profile) ? 1 : 0);
export const pCampus = (e: Event) => ((e.tags ?? []).includes("campus") ? 1 : 0);

/** 29. 1 − the weakest confidence we have on where/when (approximate campus pins are 0.3). */
export function pLowConfidence(e: Event): number {
  const confs = [e.location.geocode_confidence, e.provenance?.start?.confidence, e.provenance?.location?.confidence].filter(
    (c): c is number => typeof c === "number",
  );
  return confs.length ? clamp(1 - Math.min(...confs)) : 0;
}

export function center(ctx: RankContext): [number, number] | null {
  const n = ctx.profile?.neighborhood;
  return n ? (ctx.neighborhoods[n] ?? null) : null;
}

export function extract(e: Event, ctx: RankContext, centerOverride?: [number, number] | null): Features {
  const p = ctx.profile;
  const now = ctx.now;
  return {
    timeliness: timeliness(e, now),
    deadline_urgency: deadlineUrgency(e, now),
    early_bird: earlyBird(e, now),
    social: social(e),
    recurring: recurring(e),
    solo: p && !p.solo ? 0 : solo(e),
    beginner: beginner(e),
    novelty: novelty(e, now),
    completeness: completeness(e),
    desc_info: descInfo(e),
    source_reliability: sourceReliability(e),
    corroboration: corroboration(e),
    field_trust: fieldTrust(e),
    price_fit: priceFit(e, p?.budget ?? "any"),
    distance_fit: distanceFit(e, centerOverride !== undefined ? centerOverride : center(ctx)),
    time_fit: timeFit(e, p),
    crowd_fit: crowdFit(e),
    established_venue: establishedVenue(e),
    scarcity: scarcity(e),
    weather_fit: weatherFit(e),
    interest: interest(e, p),
    goal_fit: goalFit(e, p),
    // a cold-start prior: once you have picked interests it counts half (shrunk toward its 0.5 baseline)
    category_prior: p?.interests.length ? 0.5 + (categoryPrior(e) - 0.5) * 0.5 : categoryPrior(e),
    affinity: affinityOf(e, ctx.affinity, now.getTime()),
    p_stale: pStale(e, now, ctx.slaHours),
    p_low_quality: pLowQuality(e),
    p_kids_mismatch: pKidsMismatch(e, p),
    p_campus: pCampus(e),
    p_low_confidence: pLowConfidence(e),
  };
}
