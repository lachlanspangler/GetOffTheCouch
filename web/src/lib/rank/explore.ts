// 2.3 Exploration slot: on-device Thompson sampling over families (RANKING.md §2.3). Seeded per day + city so
// a list doesn't reshuffle on every render, and tests are deterministic.

import { A0, B0, decay, type AffinityState } from "./affinity";
import { NEWCOMER_PRIOR } from "./weights";

/** mulberry32 over a string hash: tiny, fast, good enough for sampling (not for crypto). */
export function seededRng(seed: string): () => number {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  let a = h >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function normal(rng: () => number): number {
  const u = Math.max(rng(), 1e-12);
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Marsaglia–Tsang Gamma(k, 1); boosts k < 1 with the u^(1/k) trick. */
export function gammaSample(k: number, rng: () => number): number {
  if (k < 1) return gammaSample(k + 1, rng) * Math.pow(Math.max(rng(), 1e-12), 1 / k);
  const d = k - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x: number;
    let v: number;
    do {
      x = normal(rng);
      v = 1 + c * x;
    } while (v <= 0);
    v = v * v * v;
    const u = rng();
    if (u < 1 - 0.0331 * x ** 4 || Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}

export function betaSample(a: number, b: number, rng: () => number): number {
  const x = gammaSample(a, rng);
  const y = gammaSample(b, rng);
  return x / (x + y);
}

/**
 * Pick the family to explore: sample each candidate family's Beta posterior (decayed), × the newcomer prior.
 * Families with a strong "no" (decayed β ≥ 6) are respected and never explored.
 */
export function pickExploration(families: string[], state: AffinityState | null | undefined, now: number, rng: () => number): string | null {
  let best: string | null = null;
  let bestV = -1;
  for (const f of [...families].sort()) {
    const s = state?.keys[`fam:${f}`];
    const d = s ? decay(s, now) : { a: A0, b: B0, t: now };
    if (d.b >= 6) continue;
    const v = betaSample(d.a, d.b, rng) * (0.5 + 0.5 * (NEWCOMER_PRIOR[f] ?? 0.3));
    if (v > bestV) {
      best = f;
      bestV = v;
    }
  }
  return best;
}
