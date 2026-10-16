// 2.2 On-device affinity, pure part (RANKING.md §2.2). Beta-Bernoulli per key with a 21-day half-life that
// decays evidence back toward the prior (not toward zero). Keys describe the *event*, never the source:
// fam:<family>, cat:<category>, tag:<tag in a small vocabulary>, venue:<venue_id>, slot:<weekday:daypart>,
// price:<free|paid>. Nothing here touches storage; affinityStore.ts does the I/O.

import type { Event } from "../types";
import { family, slotKey } from "./profile";

export const A0 = 2;
export const B0 = 2; // prior mean 0.5, worth "4 pseudo-events"
export const HALF_LIFE_D = 21;
const DAY = 86_400_000;

export type Action = "calendar" | "save" | "open" | "outbound" | "dismiss" | "unsave";
export type DismissWhy = "topic" | "far" | "price" | "time";

export const DELTAS: Record<Action, { a: number; b: number }> = {
  calendar: { a: 3, b: 0 },
  save: { a: 2, b: 0 },
  open: { a: 0.5, b: 0 }, // clicks are noisy and position-biased: keep them small
  outbound: { a: 1.5, b: 0 },
  dismiss: { a: 0, b: 2 },
  unsave: { a: 0, b: 1 },
};

export const TAG_VOCAB = new Set([
  "solo_friendly",
  "free",
  "outdoor",
  "nightlife",
  "beginner_friendly",
  "recurring",
  "lgbtq",
  "sober_friendly",
]);

export interface KeyState {
  a: number;
  b: number;
  t: number; // ms of last update
  /** raw (undecayed) action counts, for plain-language explanations ("You saved 3 …") */
  c?: Partial<Record<Action, number>>;
}

export interface AffinityState {
  v: 1;
  keys: Record<string, KeyState>;
  n: number; // total signals recorded
}

export const EMPTY: AffinityState = { v: 1, keys: {}, n: 0 };
export const MAX_KEYS = 300;

export function decay(s: KeyState, now: number): KeyState {
  const g = Math.pow(0.5, Math.max(0, now - s.t) / (HALF_LIFE_D * DAY));
  return { a: A0 + (s.a - A0) * g, b: B0 + (s.b - B0) * g, t: now, c: s.c };
}

export const mean = (s: KeyState) => s.a / (s.a + s.b);
export const mass = (s: KeyState) => s.a + s.b - A0 - B0; // evidence beyond the prior

/** Keys an event updates for an action. "Not for me: too far / price / time" leaves topic keys alone (§2.4.5). */
export function keysFor(e: Event, action: Action, why?: DismissWhy): string[] {
  const topic = [`cat:${e.category}`, `fam:${family(e.category)}`, ...(e.tags ?? []).filter((t) => TAG_VOCAB.has(t)).map((t) => `tag:${t}`)];
  const venue = e.venue_id ? [`venue:${e.venue_id}`] : [];
  const slot = [`slot:${slotKey(e)}`];
  const price = [`price:${e.price.is_free ? "free" : "paid"}`];
  if (action === "dismiss" && why) {
    if (why === "far") return venue;
    if (why === "price") return price;
    if (why === "time") return slot;
  }
  return [...topic, ...venue, ...slot, ...price];
}

export function update(state: AffinityState, e: Event, action: Action, now: number, why?: DismissWhy): AffinityState {
  const d = DELTAS[action];
  const keys = { ...state.keys };
  for (const k of keysFor(e, action, why)) {
    const cur = keys[k] ? decay(keys[k], now) : { a: A0, b: B0, t: now };
    const c = { ...(keys[k]?.c ?? {}) };
    c[action] = (c[action] ?? 0) + 1;
    keys[k] = { a: cur.a + d.a, b: cur.b + d.b, t: now, c };
  }
  return prune({ v: 1, keys, n: state.n + 1 }, now);
}

function prune(s: AffinityState, now: number): AffinityState {
  const entries = Object.entries(s.keys);
  if (entries.length <= MAX_KEYS) return s;
  entries.sort((x, y) => mass(decay(y[1], now)) - mass(decay(x[1], now)));
  return { ...s, keys: Object.fromEntries(entries.slice(0, MAX_KEYS)) };
}

/** Event affinity in [0, 1]; 0.5 = nothing learned. Weighted by key specificity and evidence (§2.2). */
export function affinity(e: Event, state: AffinityState | null | undefined, now: number): number {
  if (!state || !state.n) return 0.5;
  const tags = (e.tags ?? []).filter((t) => TAG_VOCAB.has(t));
  const parts: [string, number][] = [
    [`cat:${e.category}`, 0.4],
    [`fam:${family(e.category)}`, 0.3],
    [`venue:${e.venue_id}`, 0.1],
    [`slot:${slotKey(e)}`, 0.1],
    [`price:${e.price.is_free ? "free" : "paid"}`, 0.05],
    ...tags.map((t) => [`tag:${t}`, 0.1 / tags.length] as [string, number]),
  ];
  let num = 0;
  let den = 0;
  for (const [k, w] of parts) {
    const s = state.keys[k];
    if (!s) continue;
    const d = decay(s, now);
    const wk = w * Math.min(1, mass(d) / 4); // trust grows with evidence
    num += wk * mean(d);
    den += wk;
  }
  return den ? 0.5 + (num / den - 0.5) * Math.min(1, den / 0.5) : 0.5;
}

const VERB: Record<Action, [string, string]> = {
  save: ["saved", ""],
  calendar: ["added", "to your calendar"],
  open: ["opened", ""],
  outbound: ["followed", "links"],
  dismiss: ["dismissed", ""],
  unsave: ["unsaved", ""],
};

function keyLabel(k: string, labels: Record<string, string>): string {
  const [kind, id] = [k.slice(0, k.indexOf(":")), k.slice(k.indexOf(":") + 1)];
  if (kind === "cat" || kind === "fam") return labels[id] ?? id;
  if (kind === "tag") return id.replace(/_/g, " ");
  if (kind === "slot") return id.replace(":", " ") + " events";
  if (kind === "price") return id === "free" ? "free events" : "paid events";
  return "events at this venue";
}

/** "You saved 3 and opened 2: Trivia nights" — counts only, never inferred traits. */
export function describeKey(k: string, s: KeyState, labels: Record<string, string>): string {
  const c = s.c ?? {};
  const acts = (Object.keys(VERB) as Action[]).filter((a) => (c[a] ?? 0) > 0);
  const label = keyLabel(k, labels);
  if (acts.length === 1 && !VERB[acts[0]][1]) return `You ${VERB[acts[0]][0]} ${c[acts[0]]} · ${label}`;
  const bits = acts.map((a) => `${VERB[a][0]} ${c[a]}${VERB[a][1] ? " " + VERB[a][1] : ""}`);
  const list = bits.length > 1 ? `${bits.slice(0, -1).join(", ")} and ${bits[bits.length - 1]}` : bits[0];
  return `You ${list} · ${label}`;
}

/** The key that moved this event's affinity most, with a plain-language sentence. */
export function strongestKey(e: Event, state: AffinityState | null | undefined, labels: Record<string, string>, now: number): { key: string; text: string; lean: number } | null {
  if (!state?.n) return null;
  let best: { key: string; text: string; lean: number } | null = null;
  for (const k of [`cat:${e.category}`, `fam:${family(e.category)}`, `venue:${e.venue_id}`, `slot:${slotKey(e)}`]) {
    const s = state.keys[k];
    if (!s) continue;
    const d = decay(s, now);
    const lean = (mean(d) - 0.5) * Math.min(1, mass(d) / 4);
    if (!best || Math.abs(lean) > Math.abs(best.lean)) best = { key: k, text: describeKey(k, s, labels), lean };
  }
  return best;
}

/** "What GetOffTheCouch has learned": every key with a plain label, counts and lean (Settings panel). */
export function learned(state: AffinityState, labels: Record<string, string>, now: number): { key: string; label: string; text: string; lean: number }[] {
  return Object.entries(state.keys)
    .map(([key, s]) => {
      const d = decay(s, now);
      return { key, label: keyLabel(key, labels), text: describeKey(key, s, labels), lean: Math.round((mean(d) - 0.5) * 100) / 100 };
    })
    .sort((a, b) => Math.abs(b.lean) - Math.abs(a.lean));
}
