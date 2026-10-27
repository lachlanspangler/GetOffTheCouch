// Share cards (I-115): what the 1200×630 Open Graph image for a page says. scripts/og.mjs turns this into a PNG
// (satori + resvg) at build time; the browser never loads this module. Only reported data: the title, the date and
// place the source gave us, the city. The art is the same deterministic motif the page shows (lib/art.ts).
import { artSvg, cityArt, familyOf, type Family } from "./art";
import { displayPlace, displayTitle } from "./curate";
import { HUB_BY_SLUG } from "./site";
import { hubTitle } from "./title";
import { isDateOnly } from "../components/EventRow";
import { fmtDateLong, fmtDay, fmtTimeRange, weekendRange } from "./time";
import type { CityFeed, Event, Index } from "./types";

export interface OgCard {
  key: string; // stable page key → output file name ("home", "nyc", "nyc/concerts", "nyc/e/<hex>")
  kicker: string; // "New York City, NY"
  title: string;
  date: string;
  art: { svg: string; hue: number; shift: number; family: Family | "city" };
}

/** Bump when the card layout or wording changes: every cached image is re-rendered once. */
export const OG_TEMPLATE = 1;

export function homeCard(index: Index, now: Date): OgCard {
  return {
    key: "home",
    kicker: `${index.cities.length} US cities`,
    title: "Everything worth getting off the couch for",
    date: `Leagues, shows, openings and the deadlines you'd miss · updated ${fmtDay(now.toISOString(), "America/New_York")}`,
    art: { ...cityArt("home"), family: "city" },
  };
}

export function cityCard(feed: CityFeed, now: Date): OgCard {
  return {
    key: feed.city,
    kicker: `${feed.city_name}, ${feed.state}`,
    title: `Things to do in ${feed.city_name}`,
    date: `This week, from ${fmtDay(now.toISOString(), feed.timezone)}`,
    art: { ...cityArt(feed.city), family: "city" },
  };
}

export function hubCard(feed: CityFeed, hub: string, now: Date): OgCard | null {
  const h = HUB_BY_SLUG.get(hub);
  if (!h) return null;
  const family = h.cats ? familyOf(h.cats[0]) : "other";
  const date =
    h.when === "weekend"
      ? weekendRange(now, feed.timezone).label
      : h.when === "today"
        ? fmtDay(now.toISOString(), feed.timezone)
        : h.when === "month"
          ? `The next 30 days, from ${fmtDay(now.toISOString(), feed.timezone)}`
          : `This week, from ${fmtDay(now.toISOString(), feed.timezone)}`;
  return {
    key: `${feed.city}/${hub}`,
    kicker: `${feed.city_name}, ${feed.state}`,
    title: hubTitle(hub, feed.city_name),
    date,
    art: h.cats ? { ...artSvg({ id: `${feed.city}:${hub}`, family }), family } : { ...cityArt(feed.city), family: "city" },
  };
}

export function eventCard(feed: CityFeed, e: Event): OgCard {
  const family = familyOf(e.category);
  const day = fmtDateLong(e.start, e.timezone);
  const time = e.all_day || isDateOnly(e) ? "" : fmtTimeRange(e.start, e.end, e.timezone);
  const place = displayPlace(e, feed.city_name);
  return {
    key: `${feed.city}/e/${e.id.replace(/^evt_/, "")}`,
    kicker: [place, `${feed.city_name}, ${feed.state}`].filter(Boolean).join(" · "),
    title: displayTitle(e.title),
    date: time ? `${day} · ${time}` : day,
    art: { ...artSvg({ id: e.id, family }), family },
  };
}
