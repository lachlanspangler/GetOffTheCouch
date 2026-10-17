// The card signal budget (DESIGN.md §4.6): one meta line, at most one status line, at most one tag.
// Every card variant reads from here, so "never invent urgency" is enforced in one tested place.
import { liveAvailability } from "./filters";
import { priceLabel } from "./format";
import { fmtDay, fmtTime, hoursUntil, dayKey } from "./time";
import type { Event } from "./types";

export type Tone = "critical" | "caution" | "positive" | "muted" | "secondary";

export interface Status {
  text: string;
  tone: Tone;
  icon: "clock" | "users" | "alert" | "ticket" | null;
}

export interface CardSignals {
  price: string | null; // "Free", "$12–$20", "From $39 · 3 sellers"
  status: Status | null;
  tag: string | null;
}

/** "From $39 · 3 sellers" only when more than one seller actually lists a price. */
export function priceSignal(e: Event): string | null {
  const p = priceLabel(e);
  if (!p) return null;
  const sellers = new Set((e.offers ?? []).filter((o) => o.price_min != null).map((o) => o.seller));
  return sellers.size > 1 ? `From ${p.split("–")[0]} · ${sellers.size} sellers` : p;
}

/** "today at 6 PM", "tomorrow, 11:59 PM", "Thu, Oct 22" — absolute, in the city's zone. */
export function closesPhrase(iso: string, tz: string, now: Date): string {
  const k = dayKey(iso, tz);
  const today = dayKey(now, tz);
  const tomorrow = dayKey(new Date(now.getTime() + 86_400_000), tz);
  if (k === today) return `today at ${fmtTime(iso, tz)}`;
  if (k === tomorrow) return `tomorrow, ${fmtTime(iso, tz)}`;
  return fmtDay(iso, tz);
}

function isTicketed(e: Event): boolean {
  return /^(music|nightlife\.comedy|arts\.theater|sports_watch)/.test(e.category);
}

export function statusLine(e: Event, now: Date): Status | null {
  const tz = e.timezone;
  const avail = liveAvailability(e, now);
  const r = e.registration;
  const t = e.tickets;
  if (e.stale) return { text: `Listing may be out of date · ${e.stale_reason ?? "the source hasn't updated recently"}`, tone: "caution", icon: "alert" };
  if (avail === "cancelled") return { text: "Cancelled", tone: "critical", icon: "alert" };
  if (avail === "postponed") return { text: "Postponed", tone: "critical", icon: "alert" };
  if (t?.spots_left === 0 || avail === "sold_out") {
    const label = isTicketed(e) && t?.spots_left == null ? "Sold out" : "Full";
    return { text: avail === "waitlist" ? `${label} · waitlist open` : label, tone: "muted", icon: "users" };
  }
  const published = r?.closes_at && r.method !== "derived" ? r.closes_at : null;
  if (published) {
    const h = hoursUntil(published, now);
    if (h < 0) return { text: "Registration closed", tone: "muted", icon: "clock" };
    if (h <= 48) return { text: `Registration closes ${closesPhrase(published, tz, now)}`, tone: "critical", icon: "clock" };
    if (h <= 24 * 14) return { text: `Registration closes ${fmtDay(published, tz)}`, tone: "caution", icon: "clock" };
  }
  if (t?.spots_left != null && t.spots_left > 0) {
    const total = t.spots_total ?? null;
    if (t.spots_left <= Math.max(5, (total ?? 0) * 0.25)) {
      const free = e.price.is_free;
      return { text: total ? `${t.spots_left} of ${total} spots left` : `${t.spots_left} spot${t.spots_left === 1 ? "" : "s"} left`, tone: free ? "secondary" : "caution", icon: "users" };
    }
  }
  // "selling quickly" only from a real ticket signal on ticketed events (DESIGN.md §4.6 rule 7)
  if (t?.selling_fast && isTicketed(e) && t.spots_left == null) return { text: "Selling quickly", tone: "caution", icon: "ticket" };
  if (r?.opens_at && hoursUntil(r.opens_at, now) > 0) {
    return { text: `${isTicketed(e) ? "Tickets go on sale" : "Registration opens"} ${closesPhrase(r.opens_at, tz, now)}`, tone: "secondary", icon: "clock" };
  }
  if (r && r.method === "derived") return { text: "Registration required", tone: "secondary", icon: null };
  if (published) return { text: `Registration open until ${fmtDay(published, tz)}`, tone: "secondary", icon: "clock" };
  return null;
}

export function tagSignal(e: Event, now: Date): string | null {
  const tags = e.tags ?? [];
  // earned, not boilerplate: a high social score and a format where you see the same people again
  if ((e.social?.score ?? 0) >= 0.85 && (e.recurrence || e.series_id || (e.tags ?? []).includes("solo_friendly"))) return "Good for meeting people";
  if (tags.includes("solo_friendly")) return "Good to go solo";
  if (tags.includes("beginner_friendly")) return "Beginner friendly";
  if (e.is_new && now.getTime() - new Date(e.first_seen).getTime() <= 3 * 86_400_000) return "New this week";
  return null;
}

export function cardSignals(e: Event, now: Date): CardSignals {
  return { price: priceSignal(e), status: statusLine(e, now), tag: tagSignal(e, now) };
}
