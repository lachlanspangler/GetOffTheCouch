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
  s = s.replace(/\s+—\s+new [a-z ]*licen[sc]e( application)?$/i, "");
  s = s.replace(/\s+(presented|sponsored) by\s+[^|–—-]+$/i, "").replace(/\s*\((sold out|cancell?ed)\)\s*$/i, "");
  // the date belongs in the date column, not the title: "Open Mic Night – Tuesday October 27 at 8:00PM"
  s = s.replace(
    /\s*[-–—|,:]\s*(mon|tues?|wed(nes)?|thu(rs)?|fri|sat(ur)?|sun)[a-z]*\.?,?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(st|nd|rd|th)?(,?\s+\d{4})?(\s+(at|@)\s+\d{1,2}(:\d{2})?\s*([ap]\.?m\.?)?)?\s*$/i,
    "",
  );
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
  } else {
    // a shouting word inside a normal title ("BINGO | Games MONDAY"); short ones are usually acronyms (NASA, YMCA)
    s = s.replace(/\b[A-Z]{5,}\b/g, (w) => (/^(LGBTQ|NCAA|UNESCO)$/.test(w) ? w : w[0] + w.slice(1).toLowerCase()));
  }
  return s;
}

const ADDRESSY = /^\d+\s|\b(suite|ste\.?|floor|fl\.?)\s*\d|\b\d{5}(-\d{4})?\b/i;

/** Venue name to show: never a raw street address, never just the city name, never "TBD". */
export function displayVenue(e: Event, cityName?: string): string | null {
  let v = (e.location.venue_name ?? "").trim().replace(/^address:\s*/i, "").replace(/\s+(19|20)\d{2}$/, "");
  const parts = v.split(/,\s*/);
  if (parts.length > 1 && cityName && parts[0].toLowerCase() === cityName.toLowerCase()) v = parts[parts.length - 1];
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
  if (/\b(toddlers?|babies|baby|preschool|kids?|children'?s?|storytime|story time|teens?|tweens?|ages? \d+\s*[-–]\s*\d+|grades? \d+|\d+(st|nd|rd|th)\s*[-–]\s*\d+(st|nd|rd|th) grade)\b/i.test(e.title)) return true;
  return /\b(girls?'?s?|boys?'?s?|youth|junior|jr\.?)\b.*\b(clinic|camp|league|softball|soccer|basketball|baseball|volleyball|hockey|lacrosse|tennis)\b/i.test(e.title);
}

export function isAdminRole(e: Event): boolean {
  return /\b(board (member|director|seat)s?|treasurer|bookkeeper|finance chair|secretary|committee (member|chair)|grant writer|media outreach|accountant|data entry|web(site)? (developer|designer)|social media (manager|coordinator))\b/i.test(e.title);
}

export function isCampusOnly(e: Event): boolean {
  if (!(e.tags ?? []).includes("campus")) return false;
  if (/\b(club|meeting|workshop|info session|office hours|dawah|gbm|general body|trip|retreat|study (session|hall|group)|tabling|recruitment|elections?)\b/i.test(e.title)) return true;
  const v = e.location.venue_name ?? "";
  if (/\b(room|rm\.?|suite)\s*[a-z]?\d+|\b\d{3,4}[a-z]?\b/i.test(v)) return true; // a classroom, not a public venue
  return /^[A-Z]{2,6}\b/.test(e.title) && !/^(NCAA|NYU|UCLA|USC|UW|UT)\b/.test(e.title); // "UDAS …", "BPE …": student-org acronyms
}

/** Sold out or full: real, but nothing to head out for (still on its event page and in Saved). */
export function isFull(e: Event): boolean {
  const t = e.tickets;
  return t?.spots_left === 0 || t?.availability === "sold_out" || /\((sold out|full)\)/i.test(e.title);
}

const ADJACENT: Record<string, string[]> = {
  NY: ["NJ", "CT", "PA"], NJ: ["NY", "PA", "DE"], CT: ["NY", "MA", "RI"], MA: ["NH", "RI", "CT"], RI: ["MA", "CT"],
  PA: ["NJ", "DE", "OH"], DC: ["MD", "VA"], MD: ["DC", "VA", "DE", "PA"], VA: ["DC", "MD", "NC"], MO: ["KS", "IL"],
  KS: ["MO"], IL: ["IN", "WI"], IN: ["IL", "KY", "OH"], KY: ["IN", "OH"], OH: ["KY", "IN", "PA"], WI: ["IL", "MN"],
  MN: ["WI"], TN: ["MS", "AR", "GA"], OR: ["WA"], WA: ["OR"], NC: ["SC", "VA"], SC: ["NC"], GA: ["SC"], NV: [], UT: [],
};
const STATE_RE = /,\s*(A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\b|,\s*(Georgia|Texas|Florida|California|Alabama|Tennessee|Kentucky|Ohio|Virginia|Carolina)\b/;
const NAME_TO_CODE: Record<string, string> = { Georgia: "GA", Texas: "TX", Florida: "FL", California: "CA", Alabama: "AL", Tennessee: "TN", Kentucky: "KY", Ohio: "OH", Virginia: "VA" };

/** An away game in Rome, GA on the NYC feed: the listing names a state that isn't this metro's. */
export function isOutOfRegion(e: Event, cityState: string | undefined): boolean {
  if (!cityState || (e.location.lat != null && e.location.lon != null)) return false; // geocoded items are geofenced in the pipeline
  const m = STATE_RE.exec(`${e.location.venue_name ?? ""}, ${e.location.address ?? ""}`.replace(/^,\s*/, ""));
  if (!m) return false;
  const st = m[1] ?? NAME_TO_CODE[m[2] ?? ""];
  if (!st) return false; // "Carolina" alone is ambiguous
  return st !== cityState && !(ADJACENT[cityState] ?? []).includes(st);
}

/** Leads the city page: real, public, adult-friendly events (kids' things stay one filter away). */
export function isLeadable(e: Event, cityState?: string): boolean {
  return e.kind !== "opening" && !isKids(e) && !isAdminRole(e) && !isCampusOnly(e) && !isFull(e) && !isOutOfRegion(e, cityState);
}

/** "Eagan · 15 mi" for places well outside the city center; null when it's close enough not to matter. */
export function distanceNote(e: Event, center: [number, number] | undefined, thresholdKm = 16): string | null {
  if (!center || e.location.lat == null || e.location.lon == null) return null;
  const d = km(center, [e.location.lat, e.location.lon]);
  if (d < thresholdKm) return null;
  const parts = (e.location.address ?? "").split(/,\s*/);
  const town = parts.length >= 3 ? parts[parts.length - 2].replace(/\s+[A-Z]{2}\s*\d{5}.*$/, "").trim() : null;
  return `${town && town.length < 30 ? `${town}, ` : ""}${Math.round(d * 0.621)} mi from downtown`;
}

/** Started more than an hour ago with no end (or already ended): not something to head out for now. */
export function isUnderway(e: Event, now: Date): boolean {
  const start = new Date(e.start).getTime();
  if (e.all_day) return false;
  if (e.end) {
    const end = new Date(e.end).getTime();
    if (end < now.getTime()) return true;
    // a 2-hour show that started 40 minutes ago is over for planning purposes; a festival running all afternoon isn't
    return end - start <= 2 * 3600_000 && start < now.getTime() - 30 * 60_000;
  }
  return start < now.getTime() - 30 * 60_000;
}

/** Started and still going (long events only, since short ones that started are hidden). */
export function isHappeningNow(e: Event, now: Date): boolean {
  return !e.all_day && new Date(e.start) <= now && !!e.end && new Date(e.end) > now;
}
