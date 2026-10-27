// 1E. MMR re-rank with hard caps (RANKING.md §1E), shared by Highlights, For You, the plan and Similar.
//   pick argmax_i [ λ·rel(i) − (1 − λ)·max_{j∈S} sim(i, j) ]
// Hard caps are never relaxed (they are golden rules): ≤ 1 per series / multi-site group / fingerprint,
// ≤ maxPerKey per cap key (organizer × venue, see capKey) and ≤ maxPerSource per listing source per 10 slots,
// ≤ maxLibrary library events, no kids content for adults, no lowq ≥ 0.7.
// Soft caps (≤ maxPerFamily, ≤ maxPerDay, the family floor) are relaxed only when nothing else is left.

import type { Event } from "../types";
import { family, isLibrary, localDay, primarySource } from "./profile";
import { sim } from "./similarity";
import type { Scored } from "./types";

export interface Caps {
  maxPerKey?: number; // per 10 slots, per capKey (who runs it, where)
  maxPerSource?: number; // per 10 slots, per listing source: the looser anti-flood backstop for aggregators
  /** cap-key override (eval experiments only); default capKey */
  key?: (e: Event) => string;
  maxLibrary?: number;
  maxPerFamily?: number; // soft, per 10 slots
  maxPerDay?: number;
  minFamilies?: number; // in the first 10 slots, when the pool has them at rel ≥ 0.3
  excludeKids?: boolean;
  maxLowQ?: number; // exclude rank.lowq ≥ this
  /** extra hard constraint (the plan's no-overlap rule) */
  allow?: (s: Scored, chosen: Scored[]) => boolean;
}

export interface MmrOptions {
  lambda: number;
  k: number;
  caps?: Caps;
}

const norm = (s: string | null | undefined) => (s ?? "").trim().toLowerCase().replace(/\s+/g, " ");
const PLACELESS = /^(usa|united states|us|online|virtual|tbd|tba|various|multiple locations)?$/;
const NO_ORG = /^[\W_]*$/; // "", "--"

/** Normalized organizer ("" when absent or placeholder punctuation). */
export function orgOf(e: Event): string {
  const o = norm(e.organizer);
  return NO_ORG.test(o) ? "" : o;
}

/** venue_id, else the normalized venue name ("" when absent or placeless, e.g. "Online"). */
export function venueOf(e: Event): string {
  if (e.venue_id) return e.venue_id;
  const v = norm(e.location?.venue_name);
  return PLACELESS.test(v) ? "" : v;
}

/**
 * Diversity cap key (I-160, RANKING.md §7.7): "who runs it, where" = organizer × venue, falling back to the
 * listing source only when an event has neither. Aggregator feeds (a city or parks calendar, a library system's
 * branches, Volo's fields, a trivia company's bars, HandsOn's charities) differ on one of the two, so they are no
 * longer capped as if they were one venue; a single-room venue feed has one key and stays at ≤ maxPerKey.
 * The same program at many branches on one day already shares `rank.group` (≤ 1 per group), so a key per
 * branch can't let one storytime fill the list; maxPerSource stops one feed flooding it.
 */
export function capKey(e: Event): string {
  const o = orgOf(e);
  const v = venueOf(e);
  return o || v ? `o:${o}|v:${v}` : `src:${primarySource(e)}`;
}

/** Per-10-slots allowance: `cap` in the first 10, 2 × cap in the first 20, … */
const allowance = (cap: number, n: number) => cap * Math.ceil((n + 1) / 10);

const keysOf = (e: Event) => [e.series_id && `s:${e.series_id}`, e.rank?.group && `g:${e.rank.group}`, e.rank?.fp && `f:${e.rank.fp}`].filter(Boolean) as string[];

export function hardOk(s: Scored, chosen: Scored[], caps: Caps, used: Set<string>): boolean {
  const e = s.event;
  if (keysOf(e).some((k) => used.has(k))) return false;
  if (caps.excludeKids && (e.tags ?? []).includes("kids_teens")) return false;
  if (caps.maxLowQ != null && (e.rank?.lowq ?? 0) >= caps.maxLowQ) return false;
  if (caps.maxPerSource != null) {
    const src = primarySource(e);
    if (chosen.filter((c) => primarySource(c.event) === src).length >= allowance(caps.maxPerSource, chosen.length)) return false;
  }
  if (caps.maxPerKey != null) {
    const key = caps.key ?? capKey;
    const k = key(e);
    if (chosen.filter((c) => key(c.event) === k).length >= allowance(caps.maxPerKey, chosen.length)) return false;
  }
  if (caps.maxLibrary != null && isLibrary(e) && chosen.filter((c) => isLibrary(c.event)).length >= caps.maxLibrary) return false;
  if (caps.allow && !caps.allow(s, chosen)) return false;
  return true;
}

export function mmr(items: Scored[], { lambda, k, caps = {} }: MmrOptions): Scored[] {
  const chosen: Scored[] = [];
  const used = new Set<string>();
  const pool = items.filter((s) => s.rel != null);
  const maxSim = new Map<Scored, number>(pool.map((s) => [s, 0]));
  const fams = new Set<string>();
  const minFam = caps.minFamilies ?? 0;
  const head = Math.min(k, 10);
  while (chosen.length < k) {
    const left = pool.filter((s) => !chosen.includes(s) && hardOk(s, chosen, caps, used));
    if (!left.length) break;
    const need = minFam - fams.size;
    let cands = left;
    if (need > 0 && chosen.length < head && head - chosen.length <= need) {
      const fresh = left.filter((s) => !fams.has(family(s.event.category)) && (s.rel ?? 0) >= 0.3);
      if (fresh.length) cands = fresh;
    }
    if (caps.maxPerFamily != null) {
      const byFam = (s: Scored) => chosen.filter((c) => family(c.event.category) === family(s.event.category)).length;
      const ok = cands.filter((s) => byFam(s) < allowance(caps.maxPerFamily!, chosen.length));
      if (ok.length) cands = ok;
    }
    if (caps.maxPerDay != null) {
      const byDay = (s: Scored) => chosen.filter((c) => localDay(c.event) === localDay(s.event)).length;
      const ok = cands.filter((s) => byDay(s) < caps.maxPerDay!);
      if (ok.length) cands = ok;
    }
    let best = cands[0];
    let bestV = -Infinity;
    for (const s of cands) {
      const v = lambda * (s.rel ?? 0) - (1 - lambda) * (maxSim.get(s) ?? 0);
      if (v > bestV + 1e-12 || (Math.abs(v - bestV) <= 1e-12 && s.event.start < best.event.start)) {
        best = s;
        bestV = v;
      }
    }
    chosen.push(best);
    keysOf(best.event).forEach((x) => used.add(x));
    fams.add(family(best.event.category));
    for (const s of pool) maxSim.set(s, Math.max(maxSim.get(s) ?? 0, sim(s.event, best.event)));
  }
  return chosen;
}
