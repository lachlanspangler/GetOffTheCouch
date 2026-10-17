// Page titles: shared by the client (document.title) and the pre-renderer (lib/seo.ts). Kept tiny on purpose.
import type { Route } from "./router";
import { HUB_BY_SLUG } from "./site";
import { fmtDay } from "./time";
import type { CityFeed, Event } from "./types";

export const SITE = "Get Off the Couch";
export const TAGLINE = "Your city, made easy";

const VIEW_TITLE: Record<string, string> = {
  deadlines: "Deadlines",
  calendar: "Calendar",
  map: "Map",
  plan: "New in town",
  saved: "Saved",
  health: "Data status",
  about: "About",
  methodology: "How we get the data",
  privacy: "Privacy",
};

export function hubTitle(slug: string | null | undefined, city: string): string {
  const h = slug ? HUB_BY_SLUG.get(slug) : undefined;
  return h ? `${h.label} in ${city}` : `Things to do in ${city}`;
}

export function pageTitle(route: Route, feed: CityFeed | null, event?: Event): string {
  const city = feed?.city_name;
  let page: string | null = null;
  if (event) page = `${event.title} · ${fmtDay(event.start, event.timezone)}`;
  else if (route.city && route.view === "feed" && city) page = hubTitle(route.hub, city);
  else page = VIEW_TITLE[route.view] ?? null;
  const parts = [page, city && (event || route.view !== "feed") ? city : null, SITE].filter(Boolean);
  return parts.length > 1 ? parts.join(" · ") : `${SITE} · ${TAGLINE}`;
}
