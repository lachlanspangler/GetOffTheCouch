// 1D. Transparent linear score. score = Σ w_i f_i; contrib_i = w_i (f_i − baseline_i) is what explanations use.

import { FEATURES, type Features, type Weights } from "./types";
import { AFFINITY_CAP, BASELINES, MIN_AFFINITY_SIGNALS } from "./weights";

export interface ScoreOut {
  score: number;
  contrib: Features;
}

export function score(f: Features, w: Weights, affinitySignals = 0): ScoreOut {
  const contrib = {} as Features;
  let s = 0;
  for (const k of FEATURES) {
    let wk = w[k];
    if (k === "affinity" && affinitySignals < MIN_AFFINITY_SIGNALS) wk = 0;
    let c = wk * (f[k] - BASELINES[k]);
    if (k === "affinity") c = Math.max(-AFFINITY_CAP, Math.min(AFFINITY_CAP, c));
    contrib[k] = c;
    s += wk * BASELINES[k] + c; // = w·f, except affinity's capped term
  }
  return { score: Math.round(s * 1000) / 1000, contrib };
}

/** Smallest score spread treated as "a real difference" when normalizing (score points). */
export const MIN_SPAN = 1.5;

/**
 * Min-max within the pool so λ means the same thing on every surface: rel = (s − lo) / (max − lo + ε).
 * lo = min(pool min, max − MIN_SPAN): in a tiny pool whose scores differ by a few tenths, plain min-max would
 * stretch noise into 0..1 and push the last item to rel 0. Real city pools spread wider, so this is plain min-max.
 */
export function normalize(scores: number[]): number[] {
  if (!scores.length) return [];
  const hi = Math.max(...scores);
  const lo = Math.min(Math.min(...scores), hi - MIN_SPAN);
  return scores.map((s) => (s - lo) / (hi - lo + 1e-9));
}
