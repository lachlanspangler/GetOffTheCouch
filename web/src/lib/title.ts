// Page titles: shared by the client (document.title) and the pre-renderer (lib/seo.ts). Kept tiny on purpose.
import type { Route } from "./router";
import { HUB_BY_SLUG } from "./site";
import { fmtDay, weekendRange } from "./time";
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
  cities: "Cities and coverage",
};

/** "Things to do this weekend in Chicago, Oct 30 – Nov 1": the weekend hub carries its dates (Time Out pattern). */
export function hubTitle(slug: string | null | undefined, city: string, now?: Date, tz?: string): string {
  const h = slug ? HUB_BY_SLUG.get(slug) : undefined;
  if (!h) return `Things to do in ${city}`;
  if (h.when === "weekend" && now && tz) {
    const w = weekendRange(now, tz);
    return `${h.label} in ${city}, ${w.label.replace(/^\w{3}, /, "").replace(/ – \w{3}, /, " – ")}`;
  }
  return `${h.label} in ${city}`;
}

export function pageTitle(route: Route, feed: CityFeed | null, event?: Event, now?: Date): string {
  const city = feed?.city_name;
  let page: string | null = null;
  if (event) page = `${event.title} · ${fmtDay(event.start, event.timezone)}`;
  else if (route.city && route.view === "feed" && city) page = hubTitle(route.hub, city, now, feed?.timezone);
  else page = VIEW_TITLE[route.view] ?? null;
  const parts = [page, city && (event || route.view !== "feed") ? city : null, SITE].filter(Boolean);
  return parts.length > 1 ? parts.join(" · ") : `${SITE} · ${TAGLINE}`;
}
