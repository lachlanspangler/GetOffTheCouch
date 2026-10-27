// Inline first-render data (I-117). A pre-rendered page carries <script id="gotc-initial"> with only the events
// it shows plus the numbers and picks it computed from the whole feed ("memos"), so hydration doesn't wait for the
// city's data files and still matches the server HTML exactly.
//
//   server (scripts/prerender.mjs): record(feed) → render → the memo values + the event ids they reference
//   browser (main.tsx):             replay(partialFeed, sig, memos) → hydrate → the same values come back
//
// Every computation over the *whole* feed that the first render shows goes through memo(). While a feed object is
// in replay mode and the route is still the pre-rendered one, memo() returns the server's value; otherwise it
// computes. Once the full data has loaded, the app swaps in a new feed object and replay simply stops applying.
import type { Route } from "./router";
import type { CityFeed, Event } from "./types";

interface Entry {
  mode: "record" | "replay";
  sig: string;
  values: Record<string, unknown>;
  ids: Map<string, Event>;
}

const entries = new WeakMap<object, Entry>();
let current = "";

/** Identity of a page for replay purposes: everything in the route that changes what's rendered. */
export function routeSig(r: Route): string {
  return JSON.stringify([r.city, r.view, r.hub ?? null, r.eventId, r.filters, r.day, r.ids]);
}

/** The app calls this on every render, so memo() knows whether it's still rendering the pre-rendered page. */
export function setRenderSig(sig: string): void {
  current = sig;
}

const byIdOf = (feed: CityFeed) => new Map(feed.events.map((e) => [e.id, e]));

/** Server: start recording memo values for one render of `feed`. Returns the (live) value map. */
export function record(feed: CityFeed): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  entries.set(feed, { mode: "record", sig: "", values, ids: byIdOf(feed) });
  return values;
}

/** Browser (and the pre-renderer's self-check): serve recorded values for this partial feed and route. */
export function replay(feed: CityFeed, sig: string, values: Record<string, unknown>): void {
  entries.set(feed, { mode: "replay", sig, values, ids: byIdOf(feed) });
}

export function release(feed: CityFeed): void {
  entries.delete(feed);
}

/** True for the small inline feed a pre-rendered page hydrated with (the full data isn't in yet). */
export function isInline(feed: CityFeed | null | undefined): boolean {
  return !!feed && entries.get(feed)?.mode === "replay";
}

class Missing extends Error {}

// Events are stored as {"$e": id} references; everything else must be plain JSON (numbers, strings, objects).
function encode(v: unknown, ids: Map<string, Event>): unknown {
  if (Array.isArray(v)) return v.map((x) => encode(x, ids));
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    if (typeof o.id === "string" && ids.get(o.id) === v) return { $e: o.id };
    return Object.fromEntries(Object.entries(o).map(([k, x]) => [k, encode(x, ids)]));
  }
  return v;
}

function decode(v: unknown, ids: Map<string, Event>): unknown {
  if (Array.isArray(v)) return v.map((x) => decode(x, ids));
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    if (typeof o.$e === "string") {
      const e = ids.get(o.$e);
      if (!e) throw new Missing(o.$e);
      return e;
    }
    return Object.fromEntries(Object.entries(o).map(([k, x]) => [k, decode(x, ids)]));
  }
  return v;
}

/** A value computed from the whole feed: recorded on the server, replayed while hydrating from inline data. */
export function memo<T>(feed: CityFeed | null | undefined, key: string, compute: () => T): T {
  const en = feed ? entries.get(feed) : undefined;
  if (en?.mode === "replay" && en.sig === current && key in en.values) {
    try {
      return decode(en.values[key], en.ids) as T;
    } catch (err) {
      if (!(err instanceof Missing)) throw err;
    }
  }
  const v = compute();
  if (en?.mode === "record") en.values[key] = encode(v, en.ids);
  return v;
}

/** Event ids referenced by recorded memo values (the pre-renderer puts these events in the inline feed). */
export function referencedIds(values: Record<string, unknown>): Set<string> {
  const out = new Set<string>();
  const walk = (v: unknown): void => {
    if (Array.isArray(v)) v.forEach(walk);
    else if (v && typeof v === "object") {
      const o = v as Record<string, unknown>;
      if (typeof o.$e === "string") out.add(o.$e);
      else Object.values(o).forEach(walk);
    }
  };
  walk(values);
  return out;
}

/** Shape of the inline <script type="application/json" id="gotc-initial">. */
export interface InitialData {
  v: 1;
  sig: string;
  feed: CityFeed;
  memo: Record<string, unknown>;
  where?: Record<string, string>; // event id → shard key, so a card's details load without its whole shard
}
