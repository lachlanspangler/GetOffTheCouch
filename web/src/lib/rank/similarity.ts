// 1E. Schema-aware similarity in [0, 1], symmetric. Used by MMR and by the ILD metric.

import type { Event } from "../types";
import { family, localDay, primarySource } from "./profile";

const norm = (s: string | null | undefined) => (s ?? "").trim().toLowerCase();

export function sim(a: Event, b: Event): number {
  if (a.series_id && a.series_id === b.series_id) return 1;
  if (a.rank?.group && a.rank.group === b.rank?.group) return 1;
  if (a.rank?.fp && a.rank.fp === b.rank?.fp) return 1;
  const s =
    0.35 * +(family(a.category) === family(b.category)) +
    0.15 * +(a.category === b.category) +
    0.2 * +(!!a.venue_id && a.venue_id === b.venue_id) +
    0.1 * +(primarySource(a) === primarySource(b)) +
    0.1 * +(localDay(a) === localDay(b)) +
    0.1 * +(!!a.organizer && norm(a.organizer) === norm(b.organizer));
  return Math.max(0, Math.min(1, s));
}
