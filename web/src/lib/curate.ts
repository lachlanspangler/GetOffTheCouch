// Display curation: how a listing is presented, never what it says. Fixes shouting titles and address-as-venue,
// and decides what's "for adults by default" (kids' programs and board/admin volunteer roles stay findable, but
// don't lead the city page). Pure and tested.
import { family, } from "./categories";
import { km } from "./filters";
import type { Event } from "./types";

const SMALL = new Set(["a", "an", "and", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "the", "to", "vs", "with"]);

/** "LAURA VEIRS" → "Laura Veirs"; "VOLUNTEERS NEEDED!!!" → "Volunteers Needed!"; mixed case is left alone. */
export function displayTitle(t: string): string {
  let s = t.trim().replace(/\s+/g, " ").replace(/!{2,}/g, "!").replace(/\?{2,}/g, "?");
  s = s.replace(/\s+—\s+new liquor license( application)?$/i, "");
  const letters = s.replace(/[^A-Za-z]/g, "");
  const upper = s.replace(/[^A-Z]/g, "").length;
  if (letters.length >= 6 && upper / letters.length > 0.8) {
    s = s
      .toLowerCase()
      .split(" ")
      .map((w, i) => {
        if (/^(dj|nyc|usa|lgbtq\+?|ii|iii|iv|5k|10k|ymca|ucla|nyu|umn)$/i.test(w)) return w.toUpperCase();
        if (i > 0 && SMALL.has(w)) return w;
        return w.replace(/^([("'“]?)(\p{L})/u, (_, p: string, c: string) => p + c.toUpperCase());
      })
      .join(" ");
  }
  return s;
}

const ADDRESSY = /^\d+\s|\b(suite|ste\.?|floor|fl\.?)\s*\d|\b\d{5}(-\d{4})?\b/i;

/** Venue name to show: never a raw street address, never just the city name, never "TBD". */
export function displayVenue(e: Event, cityName?: string): string | null {
  const v = (e.location.venue_name ?? "").trim();
  if (!v || /^(address:?\s*)?(tbd|tba|n\/a|online|usa|united states)$/i.test(v)) return null;
  if (cityName && v.toLowerCase() === cityName.toLowerCase()) return null;
  if (ADDRESSY.test(v)) return null;
  return v.length > 80 ? `${v.slice(0, 77)}…` : v;
}

/** A short "where" for rows: venue, else the first part of the address, deduplicated. */
export function displayPlace(e: Event, cityName?: string): string | null {
  const v = displayVenue(e, cityName);
  if (v) return v;
  const a = (e.location.address ?? "").trim();
  if (!a || /tbd/i.test(a)) return e.location.neighborhood ?? null;
  const parts = [...new Set(a.split(/,\s*/).map((p) => p.trim()).filter(Boolean))];
  const street = parts[0]
    .replace(/\b([A-Z]{2,})\b/g, (w) => (w.length <= 3 && /^(NE|NW|SE|SW|N|S|E|W)$/.test(w) ? w : w[0] + w.slice(1).toLowerCase()))
    .replace(/\s+between\s+.*/i, "");
  return street.length > 60 ? `${street.slice(0, 57)}…` : street;
}

export function isKids(e: Event): boolean {
  if (family(e.category) === "family") return true;
  if ((e.tags ?? []).includes("kids_teens")) return true;
  return /\b(toddlers?|babies|baby|preschool|kids?|children'?s?|storytime|story time|teens?|tweens?|ages? \d+\s*[-–]\s*\d+)\b/i.test(e.title);
}

export function isAdminRole(e: Event): boolean {
  return /\b(board (member|director|seat)s?|treasurer|bookkeeper|finance chair|secretary|committee (member|chair)|grant writer|media outreach|accountant|data entry|web(site)? (developer|designer)|social media (manager|coordinator))\b/i.test(e.title);
}

export function isCampusOnly(e: Event): boolean {
  return (e.tags ?? []).includes("campus") && /\b(club|meeting|workshop|info session|office hours|dawah|gbm|general body)\b/i.test(e.title);
}

/** Leads the city page: real, public, adult-friendly events (kids' things stay one filter away). */
export function isLeadable(e: Event): boolean {
  return e.kind !== "opening" && !isKids(e) && !isAdminRole(e) && !isCampusOnly(e);
}

/** "Eagan · 15 mi" for places well outside the city center; null when it's close enough not to matter. */
export function distanceNote(e: Event, center: [number, number] | undefined, thresholdKm = 16): string | null {
  if (!center || e.location.lat == null || e.location.lon == null) return null;
  const d = km(center, [e.location.lat, e.location.lon]);
  if (d < thresholdKm) return null;
  const parts = (e.location.address ?? "").split(/,\s*/);
  const town = parts.length >= 3 ? parts[parts.length - 2].replace(/\s+[A-Z]{2}\s*\d{5}.*$/, "").trim() : null;
  return `${town && town.length < 30 ? `${town} · ` : ""}${Math.round(d * 0.621)} mi`;
}

/** Started more than an hour ago with no end (or already ended): not something to head out for now. */
export function isUnderway(e: Event, now: Date): boolean {
  const start = new Date(e.start).getTime();
  if (e.all_day) return false;
  if (e.end) return new Date(e.end).getTime() < now.getTime();
  return start < now.getTime() - 60 * 60_000;
}
