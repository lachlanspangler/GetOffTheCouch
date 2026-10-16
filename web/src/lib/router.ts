// Hash router: every screen + filter state lives in the URL, so any view is a shareable link.
//   #/minneapolis/feed?when=weekend&cats=music,trivia_games&free=1
//   #/minneapolis/event/evt_123
import { useEffect, useState } from "preact/hooks";
import { DEFAULT_FILTERS, type Filters, type Size, type When } from "./filters";

export type View = "feed" | "calendar" | "map" | "deadlines" | "plan" | "saved" | "health" | "about";
export const VIEWS: View[] = ["feed", "deadlines", "calendar", "map", "plan", "saved", "health", "about"];

export interface Route {
  city: string | null;
  view: View;
  eventId: string | null;
  filters: Filters;
  day: string | null; // calendar day selection
}

export function parse(hash: string): Route {
  const [path, qs = ""] = hash.replace(/^#\/?/, "").split("?");
  const seg = path.split("/").filter(Boolean);
  const q = new URLSearchParams(qs);
  const city = seg[0] ?? null;
  let view: View = "feed";
  let eventId: string | null = null;
  if (seg[1] === "event" && seg[2]) eventId = decodeURIComponent(seg[2]);
  else if (seg[1] && (VIEWS as string[]).includes(seg[1])) view = seg[1] as View;
  const f: Filters = {
    ...DEFAULT_FILTERS,
    q: q.get("q") ?? "",
    cats: q.get("cats")?.split(",").filter(Boolean) ?? [],
    when: (q.get("when") as When) ?? DEFAULT_FILTERS.when,
    free: q.get("free") === "1",
    maxPrice: q.get("max") ? Number(q.get("max")) : null,
    social: q.get("social") === "1",
    size: (q.get("size") as Size) ?? "any",
    near: q.get("near"),
    radiusKm: q.get("r") ? Number(q.get("r")) : DEFAULT_FILTERS.radiusKm,
  };
  return { city, view, eventId, filters: f, day: q.get("day") };
}

export function build(r: Partial<Route> & { city: string | null }): string {
  const f = r.filters ?? DEFAULT_FILTERS;
  const q = new URLSearchParams();
  if (f.q) q.set("q", f.q);
  if (f.cats.length) q.set("cats", f.cats.join(","));
  if (f.when !== DEFAULT_FILTERS.when) q.set("when", f.when);
  if (f.free) q.set("free", "1");
  if (f.maxPrice != null) q.set("max", String(f.maxPrice));
  if (f.social) q.set("social", "1");
  if (f.size !== "any") q.set("size", f.size);
  if (f.near) q.set("near", f.near);
  if (f.near && f.radiusKm !== DEFAULT_FILTERS.radiusKm) q.set("r", String(f.radiusKm));
  if (r.day) q.set("day", r.day);
  const path = r.eventId ? `${r.city}/event/${encodeURIComponent(r.eventId)}` : `${r.city ?? ""}${r.city ? `/${r.view ?? "feed"}` : ""}`;
  const s = q.toString();
  return `#/${path}${s ? `?${s}` : ""}`;
}

export function useRoute(): [Route, (r: Partial<Route>, replace?: boolean) => void] {
  const [route, setRoute] = useState<Route>(() => parse(location.hash));
  useEffect(() => {
    const on = () => setRoute(parse(location.hash));
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  const go = (r: Partial<Route>, replace = false) => {
    const next = { ...route, ...r };
    const h = build(next);
    if (replace) history.replaceState(null, "", h);
    else location.hash = h;
    setRoute(parse(h));
  };
  return [route, go];
}
