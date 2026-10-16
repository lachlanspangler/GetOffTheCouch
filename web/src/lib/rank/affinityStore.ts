// The only side effects in rank/: on-device personalization state in localStorage (RANKING.md §2.2).
// Data never leaves the device: no sync, no analytics. Keys:
//   gotc:affinity:v1   { v, keys: { "fam:music": {a, b, t, c} }, n }   (Beta state + raw counts)
//   gotc:dismissed:v1  { ids: { [eventOrSeriesId]: ms } }               ("Not for me")
//   gotc:shown:v1      { [family]: { last: "2026-10-16", prev: "2026-10-01" | null } }   (family floor)
// Bump the version suffix on format change and drop old data rather than migrate it.

import type { Event } from "../types";
import { loadRaw, save, usePersistent } from "../store";
import { EMPTY, learned, update, type Action, type AffinityState, type DismissWhy } from "./affinity";

const K_AFF = "affinity:v1";
const K_DISMISS = "dismissed:v1";
const K_SHOWN = "shown:v1";

interface Dismissed {
  ids: Record<string, number>;
}
type Shown = Record<string, { last: string; prev: string | null }>;

export function loadAffinity(): AffinityState {
  const s = loadRaw<AffinityState>(K_AFF, EMPTY);
  return s && s.v === 1 && s.keys ? s : EMPTY;
}

/** Record one interaction. Impressions are deliberately not signals (position bias makes skips meaningless). */
export function recordSignal(e: Event, action: Action, why?: DismissWhy, now: number = Date.now()): AffinityState {
  const next = update(loadAffinity(), e, action, now, why);
  save(K_AFF, next);
  return next;
}

export const recordSave = (e: Event) => recordSignal(e, "save");
export const recordUnsave = (e: Event) => recordSignal(e, "unsave");
export const recordCalendar = (e: Event) => recordSignal(e, "calendar");
export const recordOpen = (e: Event) => recordSignal(e, "open");
export const recordOutbound = (e: Event) => recordSignal(e, "outbound");

export function loadDismissed(): Set<string> {
  const d = loadRaw<Dismissed>(K_DISMISS, { ids: {} });
  return new Set(Object.keys(d?.ids ?? {}));
}

/**
 * "Not for me". Hides the event (and its whole series) from every ranked surface and records a negative
 * signal. `why` = "far" | "price" | "time" updates only that preference, never the topic (§2.4.5).
 */
export function dismiss(e: Event, why?: DismissWhy, now: number = Date.now()): void {
  const d = loadRaw<Dismissed>(K_DISMISS, { ids: {} });
  const ids = { ...(d?.ids ?? {}), [e.id]: now };
  if (e.series_id) ids[e.series_id] = now;
  save(K_DISMISS, { ids });
  recordSignal(e, "dismiss", why, now);
}

export function undismiss(e: Event): void {
  const d = loadRaw<Dismissed>(K_DISMISS, { ids: {} });
  const ids = { ...(d?.ids ?? {}) };
  delete ids[e.id];
  if (e.series_id) delete ids[e.series_id];
  save(K_DISMISS, { ids });
}

/** Family floor bookkeeping: families shown on a surface today. Same-day re-renders don't move `last`. */
export function markShown(families: string[], today: string): void {
  const s = loadRaw<Shown>(K_SHOWN, {}) ?? {};
  let changed = false;
  for (const f of new Set(families)) {
    const cur = s[f];
    if (cur?.last === today) continue;
    s[f] = { last: today, prev: cur?.last ?? null };
    changed = true;
  }
  if (changed) save(K_SHOWN, s);
}

/** Per family, the last day it was shown *before* today (stable across re-renders on the same day). */
export function lastShownBefore(today: string): Record<string, string> {
  const s = loadRaw<Shown>(K_SHOWN, {}) ?? {};
  const out: Record<string, string> = {};
  for (const [f, v] of Object.entries(s)) {
    const d = v.last < today ? v.last : v.prev;
    if (d) out[f] = d;
  }
  return out;
}

/** Settings → "What GetOffTheCouch has learned": plain labels and counts, one row per key. */
export function learnedSummary(labels: Record<string, string>, now: number = Date.now()) {
  return learned(loadAffinity(), labels, now);
}

export function forgetKey(key: string): void {
  const s = loadAffinity();
  const keys = { ...s.keys };
  delete keys[key];
  save(K_AFF, { ...s, keys });
}

export function resetAffinity(): void {
  save(K_AFF, EMPTY);
  save(K_DISMISS, { ids: {} });
  save(K_SHOWN, {});
}

/** Re-render hooks for components that show learned state or depend on dismissals. */
export function useAffinity(): AffinityState {
  return usePersistent<AffinityState>(K_AFF, EMPTY)[0];
}

export function useDismissed(): Set<string> {
  const [d] = usePersistent<Dismissed>(K_DISMISS, { ids: {} });
  return new Set(Object.keys(d?.ids ?? {}));
}
