// SSR entry for scripts/prerender.mjs: render one route to HTML plus its <head> tags, from the same data files
// the browser reads. Effects don't run on the server, so pages show their finished, data-driven state.
import renderToString from "preact-render-to-string";
import { App } from "./app";
import { registerViews } from "./lib/views";
import { About, Methodology, Privacy } from "./views/About";
import { Health } from "./views/Health";
import { Plan } from "./views/Plan";
import { Cities } from "./views/Cities";
import { Calendar } from "./views/Calendar";
import { MapView } from "./views/MapView";
import { Saved } from "./views/Saved";
import { Deadlines } from "./views/Deadlines";

registerViews({ about: About, methodology: Methodology, privacy: Privacy, health: Health, plan: Plan, cities: Cities, calendar: Calendar, map: MapView, saved: Saved, deadlines: Deadlines });
import { record, referencedIds, release, replay, routeSig, type InitialData } from "./lib/partial";
import { parsePath } from "./lib/router";
import { headFor, headHtml, safeJson } from "./lib/seo";
import type { CityFeed, Event, Index } from "./lib/types";

export interface Rendered {
  html: string;
  head: string;
  status: number;
  sig: string;
  memo: Record<string, unknown>; // whole-feed values the page used (lib/partial.ts), for the inline data
  ids: string[]; // events those values reference
}

/**
 * Render `path`. `initial` renders from an inline partial feed instead, exactly as the browser will hydrate it;
 * the pre-renderer compares that HTML with the full render before inlining anything.
 */
export function render(path: string, index: Index, feed: CityFeed | null, now: Date, opts: { image?: string; initial?: InitialData } = {}): Rendered {
  const [p, q = ""] = path.split("?");
  const route = parsePath(p, q);
  const sig = routeSig(route);
  const event = route.eventId && feed ? feed.events.find((e) => e.id === route.eventId) : undefined;
  const data = opts.initial ? opts.initial.feed : feed;
  let memo: Record<string, unknown> = {};
  if (opts.initial) replay(opts.initial.feed, opts.initial.sig, opts.initial.memo);
  else if (feed) memo = record(feed);
  let html: string;
  try {
    html = renderToString(<App initial={{ index, feed: data, route, now }} />);
  } finally {
    if (data) release(data);
  }
  const head = headFor(route, index, feed, event, now);
  return {
    html,
    head: headHtml(head, opts.image),
    status: route.unknown || (route.eventId && !event) ? 404 : 200,
    sig,
    memo,
    ids: [...referencedIds(memo)],
  };
}

// Inline first-render data (I-117): the events the page shows plus the whole-feed values it computed. Each variant,
// smallest first, is accepted only if rendering from exactly that partial data reproduces the page byte for byte.
// Slimmed fields are all optional in the Event type, so code that runs on the partial feed already handles them
// missing; the page's own event (event pages) is always complete.
const SLIM_HARD = ["summary", "rank", "provenance", "attendance", "categories", "is_demo", "is_new", "stale", "offers", "organizer", "price_trend", "recurrence", "registration", "series_dates", "url", "venue_id"];
const SLIM_SOFT = ["summary", "rank", "provenance"];
const SLIM_MAX = [...SLIM_HARD, "social", "tickets", "tags", "weather"]; // e.g. an event page's "similar" rows
const META_HARD = ["starter_pack", "coverage", "neighborhoods", "venues"];
export const INLINE_MAX = 200 * 1024; // raw bytes; pages with longer lists hydrate from their data files instead

function slim(e: Event, drop: string[]): Event {
  const o: Record<string, unknown> = { ...e };
  for (const k of drop) delete o[k];
  o.sources = (e.sources ?? []).map((x) => ({ source_id: x.source_id }));
  return o as unknown as Event;
}

export type Inline = { json: string; data: InitialData } | { json: null; why: "mismatch" | "too_big" };

export function inlineFor(path: string, index: Index, feed: CityFeed, now: Date, r: Rendered, where: Map<string, string> = new Map()): Inline {
  const [p, q = ""] = path.split("?");
  const mainId = parsePath(p, q).eventId;
  const ids = new Set(r.ids);
  for (const m of r.html.matchAll(/\/events\/(?:[a-z0-9-]*-)?([0-9a-f]{8,})\//g)) ids.add(`evt_${m[1]}`);
  if (mainId) ids.add(mainId);
  const events = feed.events.filter((e) => ids.has(e.id));
  // [event fields to drop, feed keys to drop, keep only the sources the inlined events cite]
  const variants: [string[] | null, string[], boolean][] = [
    [SLIM_MAX, META_HARD, true],
    [SLIM_HARD, META_HARD, false],
    [SLIM_SOFT, [], false],
    [null, [], false],
  ];
  for (const [drop, metaDrop, cited] of variants) {
    const evs = drop ? events.map((e) => (e.id === mainId ? e : slim(e, drop))) : events;
    const part: Record<string, unknown> = { ...feed, events: evs };
    const vids = new Set(evs.map((e) => e.venue_id).filter(Boolean));
    part.venues = (feed.venues ?? []).filter((v) => vids.has(v.id));
    for (const k of metaDrop) delete part[k];
    if (metaDrop.length) {
      const used = new Set(evs.flatMap((e) => (e.sources ?? []).map((x) => x.source_id)));
      part.sources = (feed.sources ?? [])
        .filter((x) => !cited || used.has(x.source_id))
        .map((x) => ({ source_id: x.source_id, name: x.name, state: x.state, stale: x.stale, records: x.records }));
    }
    const w: Record<string, string> = {};
    for (const e of evs) if (where.has(e.id)) w[e.id] = where.get(e.id)!;
    const data: InitialData = { v: 1, sig: r.sig, feed: part as unknown as CityFeed, memo: r.memo, where: w };
    const json = safeJson(data);
    if (json.length > INLINE_MAX) return { json: null, why: "too_big" };
    let again: string;
    try {
      again = render(path, index, feed, now, { initial: data }).html;
    } catch {
      continue; // a slimmed field was needed after all
    }
    if (again === r.html) return { json, data };
  }
  return { json: null, why: "mismatch" };
}

export { headFor } from "./lib/seo";
export { eventPath } from "./lib/site";
export { calendar } from "./lib/ics";
export { deadlines } from "./lib/filters";
