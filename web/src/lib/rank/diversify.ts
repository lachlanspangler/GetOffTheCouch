// 1E. MMR re-rank with hard caps (RANKING.md §1E), shared by Highlights, For You, the plan and Similar.
//   pick argmax_i [ λ·rel(i) − (1 − λ)·max_{j∈S} sim(i, j) ]
// Hard caps are never relaxed (they are golden rules): ≤ 1 per series / multi-site group / fingerprint,
// ≤ maxPerSource per 10 slots, ≤ maxLibrary library events, no kids content for adults, no lowq ≥ 0.7.
// Soft caps (≤ maxPerDay, the family floor) are relaxed only when nothing else is left.

import type { Event } from "../types";
import { family, isLibrary, localDay, primarySource } from "./profile";
import { sim } from "./similarity";
import type { Scored } from "./types";

export interface Caps {
  maxPerSource?: number; // per 10 slots
  maxLibrary?: number;
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

const keysOf = (e: Event) => [e.series_id && `s:${e.series_id}`, e.rank?.group && `g:${e.rank.group}`, e.rank?.fp && `f:${e.rank.fp}`].filter(Boolean) as string[];

export function hardOk(s: Scored, chosen: Scored[], caps: Caps, used: Set<string>): boolean {
  const e = s.event;
  if (keysOf(e).some((k) => used.has(k))) return false;
  if (caps.excludeKids && (e.tags ?? []).includes("kids_teens")) return false;
  if (caps.maxLowQ != null && (e.rank?.lowq ?? 0) >= caps.maxLowQ) return false;
  if (caps.maxPerSource != null) {
    const allowed = caps.maxPerSource * Math.ceil((chosen.length + 1) / 10);
    const src = primarySource(e);
    if (chosen.filter((c) => primarySource(c.event) === src).length >= allowed) return false;
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
