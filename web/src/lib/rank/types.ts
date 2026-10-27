// Ranking v2 types (docs/research/RANKING.md §5.2). Profile types live here so recommend.ts can re-export
// them without an import cycle.

import type { Event } from "../types";
import type { AffinityState } from "./affinity";
import type { Caps } from "./diversify";

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

export type Surface = "highlights" | "for_you" | "plan" | "similar" | "search";

export interface RankContext {
  now: Date;
  /** null = brand-new user: newcomer priors instead of preferences (RANKING.md §2.1) */
  profile: Profile | null;
  labels: Record<string, string>;
  neighborhoods: Record<string, [number, number]>;
  surface: Surface;
  city?: string;
  /** on-device learned state (affinityStore); null/undefined = nothing learned */
  affinity?: AffinityState | null;
  /** ids and series ids the user dismissed ("Not for me") */
  dismissed?: ReadonlySet<string>;
  /** family floor: per family, the last local day (before today) it was shown, e.g. { music: "2026-10-01" } */
  lastShown?: Record<string, string>;
  /** source_id → freshness SLA in hours (feed.sources); default 72 */
  slaHours?: Record<string, number>;
  /** exploration slot on/off (default on for for_you; off for eval baselines that want pure ranking) */
  explore?: boolean;
  /** seed for the exploration RNG (default: local date + city), so lists don't reshuffle per render */
  seed?: string;
  /** experiment overrides (eval ablations): MMR λ and cap settings */
  lambda?: number;
  caps?: Partial<Caps>;
  /** weight overrides (eval experiments, learned weights) */
  weights?: Partial<Weights>;
}

export const FEATURES = [
  "timeliness",
  "deadline_urgency",
  "early_bird",
  "social",
  "recurring",
  "solo",
  "beginner",
  "novelty",
  "completeness",
  "desc_info",
  "source_reliability",
  "corroboration",
  "field_trust",
  "price_fit",
  "distance_fit",
  "time_fit",
  "crowd_fit",
  "established_venue",
  "scarcity",
  "weather_fit",
  "interest",
  "goal_fit",
  "category_prior",
  "affinity",
  "p_stale",
  "p_low_quality",
  "p_kids_mismatch",
  "p_campus",
  "p_low_confidence",
] as const;

export type FeatureName = (typeof FEATURES)[number];
export type Features = Record<FeatureName, number>;
export type Weights = Record<FeatureName, number>;

export type ReasonKind = "reason" | "caveat" | "personal" | "explore";

export interface Reason {
  text: string;
  weight: number;
  /** v2: the score term this sentence explains (absent for v1 reasons) */
  feature?: FeatureName;
  kind?: ReasonKind;
}

export interface Scored {
  event: Event;
  score: number;
  reasons: Reason[];
  /** v2 only: feature values, per-feature contributions vs the neutral baseline, pool-normalized score */
  features?: Features;
  contrib?: Features;
  rel?: number;
  /** v2: why this card is in a slot it didn't win on score (exploration or family floor) */
  slot?: "explore" | "floor";
  /** v2: other upcoming dates in the series / other branches running the same program */
  more?: number;
  sites?: number;
}
