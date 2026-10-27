// Path router: every screen + filter state lives in a real URL, so any view is a shareable, indexable link.
//   /chicago/                         city feed
//   /chicago/concerts/                a landing hub (preset filters, see site.ts HUBS)
//   /chicago/deadlines/               a view
//   /chicago/events/<slug>-<hex>/     an event
//   /chicago/?when=weekend&free=1     filters stay in the query string (canonical = the clean path)
// Old #/city/view links are translated once on boot (parseHash) and replaced in history.
import { useEffect, useState } from "preact/hooks";
import { DEFAULT_FILTERS, type Filters, type Size, type When } from "./filters";
import { BASE, eventPath, HUB_BY_SLUG, hubFor, idFromEventSegment } from "./site";

export type View = "feed" | "calendar" | "map" | "deadlines" | "plan" | "saved" | "health" | "about" | "privacy" | "methodology" | "cities";
export const VIEWS: View[] = ["feed", "deadlines", "calendar", "map", "plan", "saved", "health", "about", "privacy", "methodology", "cities"];
/** Views that exist without a city (site-wide pages). */
export const SITE_VIEWS: View[] = ["about", "privacy", "methodology", "health", "cities"];

export interface Route {
  city: string | null;
  view: View;
  eventId: string | null;
  filters: Filters;
  day: string | null; // calendar day selection
  ids: string[]; // a shared list of event ids (/city/saved/?ids=a,b)
  hub?: string | null; // the landing hub this route came from, if any
  unknown?: boolean; // a path we don't recognise (rendered as a friendly "not found")
}

const WHENS = new Set(["today", "tomorrow", "weekend", "week", "month", "all"]);
const SIZES = new Set(["any", "small", "medium", "large"]);
const num = (v: string | null): number | null => (v != null && v !== "" && Number.isFinite(Number(v)) ? Number(v) : null);

function readFilters(q: URLSearchParams, base: Filters): Filters {
  const when = q.get("when");
  const size = q.get("size");
  return {
    ...base,
    q: q.get("q") ?? base.q,
    cats: q.get("cats")?.split(",").filter(Boolean) ?? base.cats,
    when: when && WHENS.has(when) ? (when as When) : base.when,
    free: q.has("free") ? q.get("free") === "1" : base.free,
    maxPrice: num(q.get("max")) ?? base.maxPrice,
    social: q.get("social") === "1" || base.social,
    size: size && SIZES.has(size) ? (size as Size) : base.size,
    near: q.get("near") ?? base.near,
    radiusKm: num(q.get("r")) ?? base.radiusKm,
    tags: q.get("tags")?.split(",").filter(Boolean) ?? base.tags,
  };
}

/** Parse a pathname (with or without the base) plus its query string. */
export function parsePath(pathname: string, search = ""): Route {
  let p = pathname;
  if (p.startsWith(BASE)) p = p.slice(BASE.length);
  const seg = p.split("/").filter(Boolean).map(decodeURIComponent);
  const q = new URLSearchParams(search.replace(/^\?/, ""));
  let city: string | null = seg[0] ?? null;
  let view: View = "feed";
  let eventId: string | null = null;
  let hub: string | null = null;
  let unknown = false;
  let base = DEFAULT_FILTERS;
  if (city && (SITE_VIEWS as string[]).includes(city) && seg.length === 1) {
    view = city as View;
    city = null;
  } else if (seg[1] === "events" && seg[2]) {
    eventId = idFromEventSegment(seg[2]) ?? seg[2];
  } else if (seg[1] === "event" && seg[2]) {
    eventId = seg[2]; // tolerate /city/event/evt_x
  } else if (seg[1] && (VIEWS as string[]).includes(seg[1])) {
    view = seg[1] as View;
  } else if (seg[1] && HUB_BY_SLUG.has(seg[1])) {
    const h = HUB_BY_SLUG.get(seg[1])!;
    hub = h.slug;
    base = { ...DEFAULT_FILTERS, cats: h.cats ?? [], when: h.when ?? DEFAULT_FILTERS.when, free: !!h.free };
  } else if (seg[1]) {
    unknown = true;
  }
  if (!eventId && seg.length > 2) unknown = true;
  return { city, view, eventId, filters: readFilters(q, base), day: q.get("day"), ids: q.get("ids")?.split(",").filter(Boolean) ?? [], hub, unknown };
}

/** Legacy `#/city/view?…` links from before path routing. */
export function parseHash(hash: string): Route {
  const [path, qs = ""] = hash.replace(/^#\/?/, "").split("?");
  const seg = path.split("/").filter(Boolean);
  if (seg[1] === "event" && seg[2]) return { ...parsePath(`/${seg[0]}/`, qs), eventId: decodeURIComponent(seg[2]) };
  return parsePath(`/${path}`, qs);
}

/** Event titles for pretty event URLs; the app registers a lookup once the city feed loads. */
let titleOf: (id: string) => string | undefined = () => undefined;
export function setTitleLookup(fn: (id: string) => string | undefined): void {
  titleOf = fn;
}

/** Path relative to BASE plus query: "chicago/concerts/?free=1". */
export function buildPath(r: Partial<Route> & { city: string | null }): string {
  const f = r.filters ?? DEFAULT_FILTERS;
  const view = r.view ?? "feed";
  let path: string;
  let preset = DEFAULT_FILTERS;
  if (!r.city) path = (SITE_VIEWS as string[]).includes(view) ? `${view}/` : "";
  else if (r.eventId) path = eventPath(r.city, r.eventId, titleOf(r.eventId));
  else if (view !== "feed") path = `${r.city}/${view}/`;
  else {
    const h = hubFor(f, DEFAULT_FILTERS);
    path = h ? `${r.city}/${h.slug}/` : `${r.city}/`;
    if (h) preset = f;
  }
  const q = new URLSearchParams();
  if (!r.eventId && view === "feed" && preset === DEFAULT_FILTERS) {
    if (f.q) q.set("q", f.q);
    if (f.cats.length) q.set("cats", f.cats.join(","));
    if (f.when !== DEFAULT_FILTERS.when) q.set("when", f.when);
    if (f.free) q.set("free", "1");
    if (f.maxPrice != null) q.set("max", String(f.maxPrice));
    if (f.social) q.set("social", "1");
    if (f.size !== "any") q.set("size", f.size);
    if (f.near) q.set("near", f.near);
    if (f.near && f.radiusKm !== DEFAULT_FILTERS.radiusKm) q.set("r", String(f.radiusKm));
    if (f.tags.length) q.set("tags", f.tags.join(","));
  } else if (!r.eventId && (view === "calendar" || view === "map")) {
    // calendar and map share the feed's filters
    if (f.q) q.set("q", f.q);
    if (f.cats.length) q.set("cats", f.cats.join(","));
    if (f.when !== DEFAULT_FILTERS.when) q.set("when", f.when);
    if (f.free) q.set("free", "1");
    if (f.near) q.set("near", f.near);
    if (f.tags.length) q.set("tags", f.tags.join(","));
  }
  if (r.day) q.set("day", r.day);
  if (r.ids?.length) q.set("ids", r.ids.join(","));
  const s = q.toString();
  return `${path}${s ? `?${s}` : ""}`;
}

/** Full href including the base path. */
export function build(r: Partial<Route> & { city: string | null }): string {
  return BASE + buildPath(r);
}

let background: Route | null = null;
let live: Route | null = null;

/** An event route shows on top of the view it was opened from (or the city feed on a direct visit). */
function withBackground(r: Route): Route {
  if (!r.eventId) {
    background = null;
    return r;
  }
  if (background && background.city === r.city) return { ...r, view: background.view, filters: background.filters, day: background.day, ids: background.ids, hub: background.hub };
  return r;
}

function current(): Route {
  if (typeof location === "undefined") return parsePath("/");
  if (location.hash.startsWith("#/")) return parseHash(location.hash);
  return withBackground(parsePath(location.pathname, location.search));
}

export function useRoute(initial?: Route): [Route, (r: Partial<Route>, replace?: boolean) => void] {
  const [route, setRoute] = useState<Route>(() => initial ?? current());
  live = route;
  useEffect(() => {
    if (location.hash.startsWith("#/")) history.replaceState(null, "", build(parseHash(location.hash)));
    const on = () => setRoute(current());
    addEventListener("popstate", on);
    // Plain <a href> links inside the app navigate without a reload.
    const click = (ev: MouseEvent) => {
      if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
      const a = (ev.target as Element | null)?.closest?.("a");
      if (!a || a.target || a.hasAttribute("download") || a.origin !== location.origin) return;
      if (!a.pathname.startsWith(BASE) || /\.[a-z0-9]+$/i.test(a.pathname)) return;
      if (a.hash && a.pathname === location.pathname && a.search === location.search) return; // in-page anchor
      ev.preventDefault();
      if (a.pathname.includes("/events/") && !live?.eventId) background = live;
      if (a.pathname + a.search !== location.pathname + location.search) history.pushState(null, "", a.pathname + a.search + a.hash);
      setRoute(current());
      const id = a.hash.slice(1);
      if (id) requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView());
      else if (!a.pathname.includes("/events/")) scrollTo(0, 0);
    };
    document.addEventListener("click", click);
    return () => {
      removeEventListener("popstate", on);
      document.removeEventListener("click", click);
    };
  }, []);
  const go = (r: Partial<Route>, replace = false) => {
    const next = { ...route, ...r };
    // An event opens over the current view; remember that view so closing returns to it, filters intact.
    if (next.eventId && !route.eventId) background = route;
    if (!next.eventId && route.eventId && background && r.view === undefined && r.filters === undefined) {
      Object.assign(next, { view: background.view, filters: background.filters, day: background.day, ids: background.ids });
    }
    const h = build(next);
    if (replace) history.replaceState(null, "", h);
    else if (h !== location.pathname + location.search) history.pushState(null, "", h);
    setRoute(withBackground(parsePath(h.split("?")[0], h.split("?")[1] ?? "")));
  };
  return [route, go];
}
