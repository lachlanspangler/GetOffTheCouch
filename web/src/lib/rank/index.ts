// Ranking v2 entry points (RANKING.md §1, §5.2): candidates → collapse → features → linear score →
// MMR + hard caps (+ exploration slot, family floor) → explanations. Pure: same input + ctx → same output.

import type { Event } from "../types";
import { dayKey } from "../time";
import { candidates, excluded, windowFor, type Window } from "./candidates";
import { collapse } from "./collapse";
import { mmr, hardOk, type Caps } from "./diversify";
import { pickExploration, seededRng } from "./explore";
import { center, extract } from "./features";
import { reasons } from "./explain";
import { family, localDay, wantsFamily } from "./profile";
import { normalize, score } from "./score";
import type { FeatureName, RankContext, Reason, Scored } from "./types";
import { LAMBDA, weightsFor } from "./weights";

export * from "./types";

const DAY = 86_400_000;

/** Score one event (no candidate filtering). `centerOverride` replaces the neighborhood (Similar uses the anchor). */
export function scoreOne(e: Event, ctx: RankContext, centerOverride?: [number, number] | null): Scored {
  const f = extract(e, ctx, centerOverride);
  const { score: s, contrib } = score(f, weightsFor(ctx.weights), ctx.affinity?.n ?? 0);
  return { event: e, score: s, reasons: reasons(e, contrib, ctx), features: f, contrib };
}

export interface RankOptions {
  window?: Window;
  collapseSeries?: boolean;
  centerOverride?: [number, number] | null;
  filter?: (e: Event) => boolean;
}

/** Candidates in the surface's window, collapsed, scored, sorted by score, with pool-normalized `rel`. */
export function rankV2(events: Event[], ctx: RankContext, opts: RankOptions = {}): Scored[] {
  const w = opts.window ?? windowFor(ctx.surface, ctx.now, ctx.profile?.startDate);
  let pool = candidates(events, ctx.now, w, ctx.dismissed);
  if (opts.filter) pool = pool.filter(opts.filter);
  const items = collapse(pool, { series: opts.collapseSeries !== false, center: center(ctx) });
  const scored = items.map((it) => ({ ...scoreOne(it.event, ctx, opts.centerOverride), more: it.more, sites: it.sites }));
  const rel = normalize(scored.map((s) => s.score));
  scored.forEach((s, i) => (s.rel = rel[i]));
  return scored.sort((a, b) => b.score - a.score || a.event.start.localeCompare(b.event.start) || a.event.id.localeCompare(b.event.id));
}

export function capsFor(ctx: RankContext): Caps {
  const base: Caps = { maxPerSource: 2, minFamilies: 3, maxLowQ: 0.7, excludeKids: !wantsFamily(ctx.profile) };
  const caps = ctx.surface === "highlights" ? { ...base, maxLibrary: 1, maxPerDay: 3 } : base;
  return ctx.caps ? ({ ...caps, ...ctx.caps } as Caps) : caps;
}

export function lambdaFor(ctx: RankContext): number {
  if (ctx.lambda != null) return ctx.lambda;
  if (ctx.surface === "highlights") return LAMBDA.highlights;
  if (ctx.surface === "search") return LAMBDA.search;
  if (ctx.surface === "similar") return LAMBDA.similar;
  if (ctx.surface === "plan") return LAMBDA.plan;
  return (ctx.profile?.interests.length ?? 0) >= 2 ? LAMBDA.for_you_broad : LAMBDA.for_you_narrow;
}

const label = (f: string, ctx: RankContext) => ctx.labels[f] ?? f.replace(/_/g, " ");

/** "Never explore junk": exploration and floor picks need rel ≥ 0.5 and no real quality flags. */
export const EXPLORE_MIN_REL = 0.5;

/** Families that are in the pool (≥ 1 decent item) but missing from the list, respecting the caps. */
function missingFamilies(pool: Scored[], chosen: Scored[], caps: Caps, minCount = 1): Map<string, Scored> {
  const have = new Set(chosen.map((c) => family(c.event.category)));
  const used = new Set<string>();
  for (const c of chosen) [c.event.series_id, c.event.rank?.group, c.event.rank?.fp].forEach((k, i) => k && used.add(`${"sgf"[i]}:${k}`));
  const counts = new Map<string, number>();
  const best = new Map<string, Scored>();
  for (const s of pool) {
    const f = family(s.event.category);
    if (have.has(f) || (s.rel ?? 0) < EXPLORE_MIN_REL || (s.event.rank?.lowq ?? 0) >= 0.3 || f === "other") continue;
    counts.set(f, (counts.get(f) ?? 0) + 1);
    if (!best.has(f) && hardOk(s, chosen, caps, used)) best.set(f, s);
  }
  for (const f of [...best.keys()]) if ((counts.get(f) ?? 0) < minCount) best.delete(f);
  return best;
}

function seedFor(ctx: RankContext, tz: string): string {
  return ctx.seed ?? `${dayKey(ctx.now, tz)}|${ctx.city ?? ""}`;
}

/**
 * For You (and the generic top-k): MMR + caps, then one exploration slot at position 4 (Thompson sampling
 * over families missing from the list) and one family-floor slot at position 7 (a family with ≥ 3 decent
 * candidates not shown in the last 14 days). Both slots are labeled honestly in their reasons.
 */
export function topK(events: Event[], ctx: RankContext, k = 10, opts: RankOptions = {}): Scored[] {
  const pool = rankV2(events, ctx, opts);
  const caps = capsFor(ctx);
  const list = mmr(pool, { lambda: lambdaFor(ctx), k, caps });
  const tz = pool[0]?.event.timezone ?? "UTC";
  if ((ctx.explore ?? ctx.surface === "for_you") && list.length >= 6) {
    const head = list.slice(0, list.length - 1);
    const missing = missingFamilies(pool, head, caps);
    const fam = pickExploration([...missing.keys()], ctx.affinity, ctx.now.getTime(), seededRng(seedFor(ctx, tz)));
    const pick = fam ? missing.get(fam) : undefined;
    if (pick) {
      const why: Reason = { text: `Something different: ${label(fam!, ctx)}, to widen what you see`, weight: 0, kind: "explore" };
      list.pop();
      list.splice(3, 0, { ...pick, slot: "explore", reasons: [why, ...pick.reasons] });
    }
  }
  const cutoff = dayKey(new Date(ctx.now.getTime() - 14 * DAY), tz);
  // the floor needs ≥ 14 days of history: on a first visit nothing has been "missing lately" (and saying so would lie)
  const history = !!ctx.lastShown && Object.values(ctx.lastShown).some((d) => d < cutoff);
  if (ctx.lastShown && history && list.length >= 8) {
    const head = list.slice(0, list.length - 1);
    const missing = missingFamilies(pool, head, caps, 3);
    const overdue = [...missing.keys()]
      .map((f) => ({ f, last: ctx.lastShown![f] ?? null }))
      .filter(({ last }) => last === null || last < cutoff)
      .sort((a, b) => (a.last ?? "").localeCompare(b.last ?? "") || (missing.get(b.f)!.rel ?? 0) - (missing.get(a.f)!.rel ?? 0));
    const f = overdue[0]?.f;
    if (f) {
      const pick = missing.get(f)!;
      const why: Reason = { text: `Something different: you haven't seen ${label(f, ctx)} picks lately`, weight: 0, kind: "explore" };
      list.pop();
      list.splice(6, 0, { ...pick, slot: "floor", reasons: [why, ...pick.reasons] });
    }
  }
  return list;
}

export function forYouV2(events: Event[], ctx: Omit<RankContext, "surface">, k = 10): Scored[] {
  return topK(events, { ...ctx, surface: "for_you" }, k);
}

const PLACELESS = /^(usa|united states|us|online|virtual|tbd|tba)$/i;

/** Highlights: this week, real places only, no all-day blocks, no campus/kids items, breadth first. */
export function highlightsV2(events: Event[], ctx: Omit<RankContext, "surface">, n = 6): Scored[] {
  return topK(events, { ...ctx, surface: "highlights" }, n, {
    filter: (e) =>
      e.kind !== "opening" &&
      e.kind !== "season" &&
      !e.all_day &&
      new Date(e.start).getTime() >= ctx.now.getTime() &&
      !!(e.location.venue_name || e.location.address) &&
      !PLACELESS.test((e.location.venue_name ?? "").trim()) &&
      !(e.tags ?? []).some((t) => t === "campus" || (t === "kids_teens" && !wantsFamily(ctx.profile))),
  });
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

/** First 4 weeks: per week, MMR (λ 0.55) over decent picks with no overlaps and one per series overall. */
export function planV2(events: Event[], ctx: Omit<RankContext, "surface">, perWeek = 3): Plan {
  const pctx: RankContext = { ...ctx, surface: "plan" };
  const start = ctx.profile?.startDate && new Date(ctx.profile.startDate) > ctx.now ? new Date(ctx.profile.startDate) : ctx.now;
  const all = rankV2(events, pctx, { collapseSeries: false, window: { from: start, to: new Date(start.getTime() + 30 * DAY) } });
  const decent = all.filter((s) => (s.rel ?? 0) >= 0.25 && (s.event.rank?.lowq ?? 0) < 0.5);
  const caps = capsFor(pctx);
  const chosen: Scored[] = [];
  const weeks: PlanWeek[] = [];
  for (let w = 0; w < 4; w++) {
    const from = new Date(start.getTime() + w * 7 * DAY);
    const to = new Date(from.getTime() + 7 * DAY);
    const pool = decent.filter((s) => {
      const t = new Date(s.event.start).getTime();
      return t >= from.getTime() && t < to.getTime() && s.event.kind !== "opening" && s.event.kind !== "season";
    });
    const usedSeries = new Set(chosen.map((c) => c.event.series_id).filter(Boolean));
    const picks = mmr(
      pool.filter((s) => !(s.event.series_id && usedSeries.has(s.event.series_id))),
      {
        lambda: LAMBDA.plan,
        k: perWeek,
        caps: { ...caps, minFamilies: Math.min(perWeek, 3), allow: (s, cur) => ![...chosen, ...cur].some((c) => overlaps(c.event, s.event)) },
      },
    );
    chosen.push(...picks);
    picks.sort((a, b) => a.event.start.localeCompare(b.event.start));
    weeks.push({ label: w === 0 ? "Week 1 — get out there" : `Week ${w + 1}`, from: from.toISOString(), picks });
  }
  const picked = new Set(chosen.map((s) => s.event.id));
  const horizon = start.getTime() + 30 * DAY;
  const once = <T extends Scored>(arr: T[]) => {
    const seen = new Set<string>();
    return arr.filter((s) => {
      const k = s.event.series_id ?? s.event.rank?.fp ?? s.event.id;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  };
  const deadlines = once(
    all.filter((s) => {
      const c = s.event.registration?.closes_at;
      return !picked.has(s.event.id) && c && new Date(c).getTime() > ctx.now.getTime() && new Date(c).getTime() < horizon;
    }),
  ).slice(0, 6);
  const openings = all.filter((s) => s.event.kind === "opening").slice(0, 5);
  const habits = once(
    all.filter(
      (s) =>
        (s.event.series_id || s.event.kind === "recurring") &&
        (s.event.social?.score ?? 0) >= 0.7 &&
        !(s.event.tags ?? []).includes("kids_teens") &&
        (s.event.rank?.lowq ?? 0) < 0.5,
    ),
  ).slice(0, 3);
  return { weeks, deadlines, openings, habits };
}

/** Similar this week: same family, near the anchor, varied venue and day (λ 0.85). */
export function similarV2(anchor: Event, events: Event[], ctx: Omit<RankContext, "surface">, n = 4): Event[] {
  const here = anchor.location.lat != null && anchor.location.lon != null ? ([anchor.location.lat, anchor.location.lon] as [number, number]) : null;
  const sctx: RankContext = { ...ctx, surface: "similar" };
  const fam = family(anchor.category);
  const pool = rankV2(events, sctx, {
    centerOverride: here,
    filter: (x) => x.id !== anchor.id && family(x.category) === fam && x.kind !== "opening" && !(anchor.series_id && x.series_id === anchor.series_id),
  });
  return mmr(pool, { lambda: LAMBDA.similar, k: n, caps: { maxLowQ: 0.7 } }).map((s) => s.event);
}

/** Single-event v2 score for the legacy scoreEvent() API: null when no surface would show it. */
export function scoreEventV2(e: Event, ctx: RankContext): Scored | null {
  return excluded(e, ctx.now) ? null : scoreOne(e, ctx);
}

// ───────────── "Why am I seeing this?" ─────────────

export interface WhyItem {
  text: string;
  contribution: number; // score points vs a neutral event
  feature?: FeatureName;
}

export interface Why {
  headline: string;
  reasons: WhyItem[];
  caveat: WhyItem | null;
  /** the on-device personalization part, e.g. "You saved 3 · Trivia nights" (null until ≥ 5 signals) */
  personal: WhyItem | null;
  /** exploration / family-floor note when the card holds a "something different" slot */
  slot: string | null;
  privacy: string;
}

export function whyThis(s: Scored, ctx: Pick<RankContext, "profile" | "labels"> & { cityName?: string }): Why {
  const pick = (r: Reason): WhyItem => ({ text: r.text, contribution: r.weight, feature: r.feature });
  const personal = s.reasons.find((r) => r.kind === "personal");
  const caveat = s.reasons.find((r) => r.kind === "caveat");
  const slot = s.reasons.find((r) => r.kind === "explore");
  const headline = slot
    ? "Something different"
    : ctx.profile
      ? "Why you're seeing this"
      : `Picked for someone new to ${ctx.cityName ?? "the city"}`;
  return {
    headline,
    reasons: s.reasons.filter((r) => r.kind === "reason").map(pick),
    caveat: caveat ? pick(caveat) : null,
    personal: personal ? pick(personal) : null,
    slot: slot?.text ?? null,
    privacy: "Ranked on your device from your choices and what you've saved. Nothing is sent anywhere.",
  };
}

export { localDay };
