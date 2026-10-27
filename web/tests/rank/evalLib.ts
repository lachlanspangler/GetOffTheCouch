// Offline ranking evaluation (RANKING.md §3): frozen real snapshots × personas × hand-made judgments.
// Node-only helpers shared by eval.test.ts (the gate), golden.test.ts (hard rules) and pool.test.ts (pooling).

import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { join } from "node:path";
import type { Event } from "../../src/lib/types";
import { DEFAULT_PROFILE, forYou, rank, setRanker } from "../../src/lib/recommend";
import { forYouV2, highlightsV2, rankV2, type Profile, type RankContext, type Scored } from "../../src/lib/rank/index";
import { family } from "../../src/lib/rank/profile";
import { sim } from "../../src/lib/rank/similarity";
import { capKey } from "../../src/lib/rank/diversify";
import { CAPS } from "../../src/lib/rank/weights";
import { highlights as highlightsAny } from "../../src/lib/recommend";

export const FIX = join(__dirname, "fixtures");
export const CITIES = ["minneapolis", "nyc", "chicago", "austin", "seattle"];

export interface Snapshot {
  city: string;
  city_name: string;
  now: string;
  events: Event[];
  neighborhoods: { name: string; lat: number; lon: number }[];
}

const cache = new Map<string, Snapshot>();
export function snapshot(city: string): Snapshot {
  let s = cache.get(city);
  if (!s) {
    s = JSON.parse(gunzipSync(readFileSync(join(FIX, `${city}.feed.json.gz`))).toString()) as Snapshot;
    cache.set(city, s);
  }
  return s;
}

export const labels: Record<string, string> = JSON.parse(readFileSync(join(FIX, "labels.json"), "utf8"));
const personaFile = JSON.parse(readFileSync(join(FIX, "personas.json"), "utf8")) as {
  neighborhood_by_city: Record<string, string>;
  personas: Record<string, Profile | null>;
};
export const PERSONAS = Object.keys(personaFile.personas);

export function persona(id: string, city: string): Profile | null {
  const p = personaFile.personas[id];
  if (!p) return null;
  return { ...p, neighborhood: p.neighborhood === "auto" ? personaFile.neighborhood_by_city[city] : p.neighborhood };
}

export function hoods(s: Snapshot): Record<string, [number, number]> {
  return Object.fromEntries(s.neighborhoods.map((n) => [n.name, [n.lat, n.lon] as [number, number]]));
}

export function ctxFor(s: Snapshot, profile: Profile | null, extra: Partial<RankContext> = {}): Omit<RankContext, "surface"> {
  return { now: new Date(s.now), profile, labels, neighborhoods: hoods(s), city: s.city, seed: `eval|${s.city}`, lastShown: {}, ...extra };
}

/** v1 baseline as the app shipped it: rank() with one card per series (v1 has no diversity re-rank here). */
export function runV1(s: Snapshot, profile: Profile | null, k = 10): Scored[] {
  setRanker("v1");
  try {
    return forYou(s.events, profile ?? DEFAULT_PROFILE, labels, hoods(s), new Date(s.now), k);
  } finally {
    setRanker(null);
  }
}

export function runV2(s: Snapshot, profile: Profile | null, k = 10, extra: Partial<RankContext> = {}): Scored[] {
  return forYouV2(s.events, ctxFor(s, profile, extra), k);
}

export function highlightsV1(s: Snapshot, n = 6): Scored[] {
  setRanker("v1");
  try {
    return highlightsAny(s.events, labels, new Date(s.now), n);
  } finally {
    setRanker(null);
  }
}

export function highlights2(s: Snapshot, n = 6): Scored[] {
  return highlightsV2(s.events, ctxFor(s, null), n);
}

export function poolV2(s: Snapshot, profile: Profile | null): Scored[] {
  return rankV2(s.events, { ...ctxFor(s, profile), surface: "for_you" });
}

export function v1Rank(s: Snapshot, profile: Profile | null): Scored[] {
  setRanker("v1");
  try {
    return rank(s.events, profile ?? DEFAULT_PROFILE, labels, hoods(s), new Date(s.now));
  } finally {
    setRanker(null);
  }
}

// ───────────── judgments ─────────────

export interface Judgments {
  version: number;
  city: string;
  snapshot: string;
  now: string;
  labeler: string;
  /** persona order of the grade strings */
  personas: string[];
  /** event id → "gggggg" (one 0–3 digit per persona, in `personas` order) + fp + title + rationale */
  labels: Record<string, { g: string; fp?: string; t: string; why: string }>;
  rules: { when: { tags_any?: string[]; flags_any?: string[] }; except_persona?: string[]; grade: number; why: string }[];
}

export function judgments(city: string): Judgments {
  return JSON.parse(readFileSync(join(FIX, `${city}.judgments.json`), "utf8")) as Judgments;
}

/** Grade for (event, persona): id → fingerprint → rule → null (unjudged). */
export function grade(j: Judgments, e: Event, personaId: string): number | null {
  const pi = j.personas.indexOf(personaId);
  const byId = j.labels[e.id];
  const hit = byId ?? Object.values(j.labels).find((l) => l.fp && l.fp === e.rank?.fp);
  if (hit && pi >= 0) return Number(hit.g[pi]);
  for (const r of j.rules) {
    if (r.except_persona?.includes(personaId)) continue;
    const tagHit = r.when.tags_any?.some((t) => (e.tags ?? []).includes(t));
    const flagHit = r.when.flags_any?.some((f) => (e.rank?.flags ?? []).includes(f));
    if (tagHit || flagHit) return r.grade;
  }
  return null;
}

// ───────────── metrics (§3.2) ─────────────

const dcg = (gs: number[]) => gs.reduce((acc, g, i) => acc + (2 ** g - 1) / Math.log2(i + 2), 0);

export interface Metrics {
  ndcg: number;
  /** NDCG against the best list that obeys the hard caps (per source, per organizer × venue, ≤ 1 per series/group): how close a
   *  rules-compliant ranker gets to the best rules-compliant list. Capped at 1 (v1 ignores the caps). */
  ndcgCaps: number;
  p10: number;
  ild: number;
  entropy: number;
  judged: number;
  junk: number;
  stale: number;
  freshH: number;
  isNew: number;
  families: number;
}

export function metrics(list: Scored[], j: Judgments, personaId: string, pool: Event[], now: Date, k = 10): Metrics {
  const top = list.slice(0, k);
  const gs = top.map((s) => grade(j, s.event, personaId));
  const g0 = gs.map((g) => g ?? 0); // unjudged counts as 0 (conservative)
  // ideal: best grades available in the judged pool for this persona (one per series/fp, like any surface)
  const seen = new Set<string>();
  const ideal: number[] = [];
  for (const e of pool) {
    const g = grade(j, e, personaId);
    if (g == null) continue;
    const key = e.series_id ?? e.rank?.fp ?? e.id;
    if (seen.has(key)) continue;
    seen.add(key);
    ideal.push(g);
  }
  ideal.sort((a, b) => b - a);
  const idcg = dcg(ideal.slice(0, k));
  // caps-aware ideal: greedy by grade under the hard caps (≤ CAPS.perSource per source, ≤ CAPS.perKey per
  // organizer × venue, ≤ 1 per series/group/fp). With two nested caps greedy is a close, not always exact, bound;
  // the soft family cap is ignored.
  const judgedPool = pool
    .map((e) => ({ e, g: grade(j, e, personaId) }))
    .filter((x): x is { e: Event; g: number } => x.g != null)
    .sort((a, b) => b.g - a.g || a.e.id.localeCompare(b.e.id));
  const perSrc = new Map<string, number>();
  const perKey = new Map<string, number>();
  const usedK = new Set<string>();
  const capped: number[] = [];
  for (const { e, g } of judgedPool) {
    if (capped.length >= k) break;
    const keys = [e.series_id, e.rank?.group, e.rank?.fp].filter(Boolean) as string[];
    const src = e.sources[0]?.source_id ?? "";
    const ck = capKey(e);
    if (keys.some((x) => usedK.has(x)) || (perSrc.get(src) ?? 0) >= CAPS.perSource || (perKey.get(ck) ?? 0) >= CAPS.perKey) continue;
    keys.forEach((x) => usedK.add(x));
    perSrc.set(src, (perSrc.get(src) ?? 0) + 1);
    perKey.set(ck, (perKey.get(ck) ?? 0) + 1);
    capped.push(g);
  }
  const idcgCaps = dcg(capped);
  let simSum = 0;
  let pairs = 0;
  for (let a = 0; a < top.length; a++)
    for (let b = a + 1; b < top.length; b++) {
      simSum += sim(top[a].event, top[b].event);
      pairs++;
    }
  const fams = new Map<string, number>();
  for (const s of top) fams.set(family(s.event.category), (fams.get(family(s.event.category)) ?? 0) + 1);
  const poolFams = new Set(pool.map((e) => family(e.category))).size;
  let H = 0;
  for (const n of fams.values()) {
    const p = n / top.length;
    H -= p * Math.log2(p);
  }
  const maxH = Math.log2(Math.min(k, poolFams));
  const hours = top.map((s) => (new Date(s.event.start).getTime() - now.getTime()) / 3_600_000).filter((h) => h >= 0).sort((a, b) => a - b);
  return {
    ndcg: idcg ? dcg(g0) / idcg : 0,
    ndcgCaps: idcgCaps ? Math.min(1, dcg(g0) / idcgCaps) : 0,
    p10: g0.filter((g) => g >= 2).length / k,
    ild: pairs ? 1 - simSum / pairs : 0,
    entropy: maxH > 0 ? H / maxH : 0,
    judged: top.length ? gs.filter((g) => g != null).length / top.length : 0,
    junk: top.length ? gs.filter((g) => g === 0).length / top.length : 0,
    stale: top.length ? top.filter((s) => s.event.stale).length / top.length : 0,
    freshH: hours.length ? hours[Math.floor(hours.length / 2)] : 0,
    isNew: top.length ? top.filter((s) => s.event.is_new).length / top.length : 0,
    families: fams.size,
  };
}

export function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
}

/** Coverage: distinct families in the union of all personas' top 10s ÷ families in the pool. */
export function coverage(lists: Scored[][], pool: Event[]): number {
  const fams = new Set(lists.flat().map((s) => family(s.event.category)));
  return fams.size / new Set(pool.map((e) => family(e.category))).size;
}
