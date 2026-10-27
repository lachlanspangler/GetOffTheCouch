// Page metadata for pre-rendered pages: title, description, canonical, robots, Open Graph and JSON-LD.
// Pure functions of (route, data), shared by the client (document.title) and scripts/prerender.mjs.
import { applyFilters, collapseSeries } from "./filters";
import { isLeadable } from "./curate";
import { priceLabel } from "./format";
import type { Route } from "./router";
import { buildPath } from "./router";
import { absolute, HUB_BY_SLUG } from "./site";
import { fmtDay, fmtTime } from "./time";
import type { CityFeed, Event, Index } from "./types";

import { hubTitle, pageTitle, SITE, TAGLINE } from "./title";

export { hubTitle, pageTitle, SITE, TAGLINE };
const DEFAULT_DESC =
  "Everything worth leaving the house for in your city, and every deadline you'd otherwise miss: rec leagues, block parties, concerts with prices, volunteering, trivia, cons and faires. From official sources, checked every few hours.";



export interface Head {
  title: string;
  description: string;
  canonical: string;
  robots: "index,follow" | "noindex,follow";
  ogType: "website" | "article";
  jsonld: object[];
}

/** Kinds that are real events a person can attend on a date. Openings, seasons and deadlines never get Event markup. */
export function isMarkupEvent(e: Event): boolean {
  return (e.kind === "one_off" || e.kind === "recurring") && !e.is_demo;
}

function clip(s: string, n = 155): string {
  const t = s.replace(/\s+/g, " ").trim();
  return t.length <= n ? t : `${t.slice(0, n - 1).replace(/\s+\S*$/, "")}…`;
}


function eventDescription(e: Event, city: string): string {
  const when = `${fmtDay(e.start, e.timezone)}${e.all_day ? "" : `, ${fmtTime(e.start, e.timezone)}`}`;
  const where = e.location.venue_name ?? e.location.address ?? city;
  const price = priceLabel(e);
  const lead = [when, where, price].filter(Boolean).join(" · ");
  const body = e.summary?.trim() || `${e.title} in ${city}. Details, prices and where this listing comes from.`;
  return clip(`${lead}. ${body}`);
}

/** schema.org Event, only with reported values (ADR-0006): no estimated prices, no invented end times. */
export function eventJsonLd(e: Event, url: string): object {
  const status = e.tickets?.availability;
  const offers = (e.offers ?? [])
    .filter((o) => o.url && (o.kind === "primary" || o.kind === "resale" || o.kind === "registration"))
    .map((o) => ({
      "@type": "Offer",
      url: o.url,
      ...(o.price_min != null ? { price: o.price_min, priceCurrency: e.price.currency ?? "USD" } : {}),
      ...(o.availability === "sold_out" ? { availability: "https://schema.org/SoldOut" } : o.availability === "few_left" ? { availability: "https://schema.org/LimitedAvailability" } : {}),
      seller: { "@type": "Organization", name: o.seller },
    }));
  if (!offers.length && e.price.is_free && e.url) offers.push({ "@type": "Offer", url: e.url, price: 0, priceCurrency: "USD", seller: { "@type": "Organization", name: e.organizer ?? e.location.venue_name ?? "Organizer" } });
  const place: Record<string, unknown> = { "@type": "Place", name: e.location.venue_name || e.location.address || e.city };
  if (e.location.address) place.address = e.location.address;
  if (e.location.lat != null && e.location.lon != null) place.geo = { "@type": "GeoCoordinates", latitude: e.location.lat, longitude: e.location.lon };
  return {
    "@context": "https://schema.org",
    "@type": "Event",
    name: e.title,
    startDate: e.all_day ? e.start.slice(0, 10) : e.start,
    ...(e.end && !e.all_day ? { endDate: e.end } : {}),
    eventStatus: status === "cancelled" ? "https://schema.org/EventCancelled" : status === "postponed" ? "https://schema.org/EventPostponed" : "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: place,
    ...(e.summary ? { description: clip(e.summary, 500) } : {}),
    ...(e.organizer ? { organizer: { "@type": "Organization", name: e.organizer } } : {}),
    ...(offers.length ? { offers } : {}),
    url,
  };
}

function breadcrumbs(items: [string, string][]): object {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map(([name, item], i) => ({ "@type": "ListItem", position: i + 1, name, item })),
  };
}

/** Minimum upcoming items for a hub to be indexable (thin pages are noindex; SEO_ACCESS §1.8). */
export const HUB_MIN = 5;

export function headFor(route: Route, index: Index, feed: CityFeed | null, event: Event | undefined, now: Date): Head {
  const path = route.eventId && event ? buildPath({ city: route.city, eventId: route.eventId }) : buildPath({ city: route.city, view: route.view, filters: route.filters });
  const canonical = absolute(path.split("?")[0]);
  const jsonld: object[] = [];
  let description = DEFAULT_DESC;
  let robots: Head["robots"] = "index,follow";
  if (event && feed) {
    description = eventDescription(event, feed.city_name);
    // Google requires a location address for in-person events: no address, no Event markup (never a guessed one)
    if (isMarkupEvent(event) && event.location.address && new Date(event.end ?? event.start).getTime() >= now.getTime()) jsonld.push(eventJsonLd(event, canonical));
    if (event.kind === "opening" || new Date(event.end ?? event.start).getTime() < now.getTime() - 86_400_000) robots = "noindex,follow";
    jsonld.push(breadcrumbs([[feed.city_name, absolute(`${feed.city}/`)], [event.title, canonical]]));
  } else if (feed && route.view === "feed") {
    const n = collapseSeries(applyFilters(feed.events, route.filters, feed.timezone, {}, now).filter((e) => isLeadable(e, feed.state))).length;
    const h = route.hub ? HUB_BY_SLUG.get(route.hub) : undefined;
    description = h
      ? clip(`${n.toLocaleString("en-US")} upcoming: ${h.label.toLowerCase()} in ${feed.city_name}, from official calendars and venues, checked every few hours.`)
      : clip(`What's on in ${feed.city_name} this week, and what's due: ${n.toLocaleString("en-US")} upcoming events from ${(feed.sources ?? []).filter((s) => s.state !== "disabled").length} local sources, plus league and registration deadlines.`);
    if (h && n < HUB_MIN) robots = "noindex,follow";
    if (h) jsonld.push(breadcrumbs([[feed.city_name, absolute(`${feed.city}/`)], [h.label, canonical]]));
  } else if (feed) {
    if (route.view === "deadlines") description = clip(`League sign-ups, registration cutoffs and early-bird prices in ${feed.city_name}, soonest first, plus the state's new-resident deadlines.`);
    if (["calendar", "map", "plan", "saved", "health"].includes(route.view)) robots = "noindex,follow"; // city health duplicates /health/
  } else if (!route.city && route.view === "feed") {
    jsonld.push({ "@context": "https://schema.org", "@type": "WebSite", name: SITE, url: absolute("") });
    description = clip(`${DEFAULT_DESC} ${index.cities.length} cities.`);
  }
  if (route.unknown) robots = "noindex,follow";
  return { title: pageTitle(route, feed, event, now), description, canonical, robots, ogType: event ? "article" : "website", jsonld };
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** JSON for a <script> tag: escape "<" so a title can never close the tag. */
export function safeJson(o: object): string {
  return JSON.stringify(o).replace(/</g, "\\u003c");
}

export function headHtml(h: Head, image?: string): string {
  const tags = [
    `<title>${esc(h.title)}</title>`,
    `<meta name="description" content="${esc(h.description)}" />`,
    `<link rel="canonical" href="${esc(h.canonical)}" />`,
    `<meta name="robots" content="${h.robots}" />`,
    `<meta property="og:site_name" content="${SITE}" />`,
    `<meta property="og:type" content="${h.ogType}" />`,
    `<meta property="og:title" content="${esc(h.title.replace(` · ${SITE}`, ""))}" />`,
    `<meta property="og:description" content="${esc(h.description)}" />`,
    `<meta property="og:url" content="${esc(h.canonical)}" />`,
    ...(image ? [`<meta property="og:image" content="${esc(image)}" />`, `<meta property="og:image:width" content="1200" />`, `<meta property="og:image:height" content="630" />`] : []),
    `<meta name="twitter:card" content="${image ? "summary_large_image" : "summary"}" />`,
    ...h.jsonld.map((j) => `<script type="application/ld+json">${safeJson(j)}</script>`),
  ];
  return tags.join("\n    ");
}
