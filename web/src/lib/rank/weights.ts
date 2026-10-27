// 1D. Weight table (RANKING.md §1D, "v2.0" defaults) and per-feature neutral baselines.
//
// score = Σ w_i × f_i. contrib_i = w_i × (f_i − baseline_i): the baseline is what a typical, neutral event
// gets, so an unknown value (price unknown → 0.5) contributes exactly 0 and can never become a reason.

import type { Weights } from "./types";

export const DEFAULT_WEIGHTS: Weights = {
  interest: 1.2,
  goal_fit: 0.6,
  social: 0.8,
  category_prior: 0.5,
  affinity: 0.6, // switched off below MIN_AFFINITY_SIGNALS; contribution capped at ±AFFINITY_CAP
  timeliness: 0.5,
  deadline_urgency: 0.45,
  early_bird: 0.15,
  time_fit: 0.7,
  price_fit: 0.6,
  distance_fit: 0.4,
  solo: 0.3,
  completeness: 0.4,
  desc_info: 0.15,
  source_reliability: 0.2,
  corroboration: 0.1,
  field_trust: 0.1,
  crowd_fit: 0.2,
  established_venue: 0.1,
  scarcity: 0.15,
  weather_fit: 0.15,
  novelty: 0.2,
  recurring: 0.2,
  beginner: 0.15,
  p_kids_mismatch: -1.5,
  p_low_quality: -1.0,
  p_stale: -0.4,
  p_campus: -0.35,
  p_low_confidence: -0.3,
};

export const BASELINES: Weights = {
  interest: 0.5,
  goal_fit: 0,
  social: 0.4, // the pipeline's "no idea" social score
  category_prior: 0.5,
  affinity: 0.5,
  timeliness: 0.5, // "about a week out"; the next 3 days are a mild plus, not a headline reason
  deadline_urgency: 0,
  early_bird: 0,
  time_fit: 0.5,
  price_fit: 0.5,
  distance_fit: 0.5,
  solo: 0,
  completeness: 0.5,
  desc_info: 0.5,
  source_reliability: 0.8, // unknown reliability defaults to 0.8
  corroboration: 0,
  field_trust: 0.6,
  crowd_fit: 0.5,
  established_venue: 0,
  scarcity: 0,
  weather_fit: 0.6,
  novelty: 0,
  recurring: 0,
  beginner: 0,
  p_kids_mismatch: 0,
  p_low_quality: 0,
  p_stale: 0,
  p_campus: 0,
  p_low_confidence: 0,
};

export const MIN_AFFINITY_SIGNALS = 5;
export const AFFINITY_CAP = 0.3;

/**
 * Newcomer category prior (feature 23): our judgment of what helps you build a life in a new city.
 * A judgment call, documented in RANKING.md §1C; reasons that cite it say "on our newcomer list", never "popular".
 */
export const NEWCOMER_PRIOR: Record<string, number> = {
  sports_league: 0.9,
  trivia_games: 0.85,
  volunteer: 0.8,
  fitness: 0.75,
  niche: 0.7,
  nightlife: 0.7,
  learning: 0.7,
  community: 0.65,
  music: 0.6,
  food_drink: 0.6,
  outdoors: 0.6,
  arts: 0.55,
  sports_watch: 0.5,
  family: 0.3,
  other: 0.3,
};

/** time_fit without a profile: when a newcomer with a day job can actually go. */
export const SLOT_PRIOR = { weekends: 1.0, weeknights: 0.8, daytime: 0.35 } as const;

/** MMR λ per surface (§1E): lower = more spread. */
export const LAMBDA = {
  highlights: 0.6,
  // RANKING.md proposed 0.65 / 0.75. In the eval's λ sweep (npm run eval:ablate) NDCG@10 rises from 0.41 at
  // 0.65 to 0.46 at 0.9 and 0.47 at 1.0 (leave-one-city-out picks 0.9–1.0 in every fold): rel is min-max over the
  // whole pool, so near the top items differ by hundredths and a low λ lets similarity dominate. 0.9 keeps a
  // little venue/day de-clumping beyond the hard caps for ~0.01 NDCG; ILD stays ≈ 0.90 (gate 0.55).
  for_you_narrow: 0.9, // ≤ 1 interest
  for_you_broad: 0.9, // ≥ 2 interests
  search: 0.9,
  similar: 0.85,
  plan: 0.55,
} as const;

/**
 * Diversity caps per 10 slots (§1E; I-160, RANKING.md §7.7). The hard cap is on "who runs it, where"
 * (diversify.ts capKey: organizer × venue), not on the listing source, so aggregators (library branches, parks,
 * Volo fields, trivia bars, HandsOn charities) aren't capped as if they were one venue. perSource is the looser
 * backstop so one feed still can't flood the list. perFamily is a soft For You cap (relaxed only if the pool runs
 * out) that keeps family entropy ≥ 0.7 once the source cap is loosened: without it every looser config failed the
 * entropy gate. Chosen with the cap sweep in `npm run eval:ablate`: leave-one-city-out held-out For You NDCG@10
 * 0.471 vs 0.458 for the old ≤ 2-per-source cap; among gate-passing configs within 0.005 of the in-sample best
 * (≈ 0.48) this one has the smallest worst-city drop (−0.02). Highlights keeps ≤ 2 per source in its top 6.
 */
export const CAPS = { perKey: 2, perSource: 3, perFamily: 3, highlightsPerSource: 2 } as const;

export function weightsFor(over?: Partial<Weights>): Weights {
  return over ? { ...DEFAULT_WEIGHTS, ...over } : DEFAULT_WEIGHTS;
}
