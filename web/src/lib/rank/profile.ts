// Profile constants and small helpers shared by v1 (recommend.ts) and v2 (rank/).

import type { Event } from "../types";
import { parts } from "../time";
import type { Goal, Profile, Slot } from "./types";

export const DEFAULT_PROFILE: Profile = {
  interests: [],
  goals: ["meet_people"],
  budget: "any",
  times: ["weeknights", "weekends"],
  neighborhood: null,
  solo: true,
  startDate: null,
};

export const GOALS: Record<Goal, { label: string; families: string[]; weight: number }> = {
  meet_people: { label: "Meet people", families: [], weight: 0 },
  stay_active: { label: "Stay active", families: ["fitness", "sports_league", "outdoors"], weight: 0.5 },
  culture: { label: "Arts & culture", families: ["arts", "music"], weight: 0.4 },
  party: { label: "Go out", families: ["nightlife", "music", "food_drink"], weight: 0.4 },
  give_back: { label: "Give back", families: ["volunteer", "community"], weight: 0.55 },
  nerd_out: { label: "Nerd out", families: ["niche", "trivia_games", "learning"], weight: 0.5 },
};

export function family(id: string): string {
  return id.split(".")[0];
}

const slotCache = new WeakMap<Event, { slot: Slot; weekday: number; hour: number; day: string }>();

function local(e: Event) {
  let c = slotCache.get(e);
  if (!c) {
    const p = parts(e.start, e.timezone);
    const slot: Slot =
      p.weekday === 0 || p.weekday === 6 || (p.weekday === 5 && p.hour >= 17) ? "weekends" : p.hour >= 17 ? "weeknights" : "daytime";
    const day = `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
    c = { slot, weekday: p.weekday, hour: p.hour, day };
    slotCache.set(e, c);
  }
  return c;
}

export function slotOf(e: Event): Slot {
  return local(e).slot;
}

/** Local calendar day in the event's zone ("2026-10-17"). */
export function localDay(e: Event): string {
  return local(e).day;
}

export function weekdayHour(e: Event): { weekday: number; hour: number } {
  const c = local(e);
  return { weekday: c.weekday, hour: c.hour };
}

const DAYPART = (h: number) => (h < 12 ? "morning" : h < 17 ? "afternoon" : "evening");
const WEEKDAY = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** "Saturday evening" */
export function whenPhrase(e: Event): string {
  const { weekday, hour } = weekdayHour(e);
  return `${WEEKDAY[weekday]} ${DAYPART(hour)}`;
}

/** weekday × daypart key for affinity ("sat:evening") */
export function slotKey(e: Event): string {
  const { weekday, hour } = weekdayHour(e);
  return `${WEEKDAY[weekday].slice(0, 3).toLowerCase()}:${DAYPART(hour)}`;
}

export function wantsFamily(p: Profile | null): boolean {
  return !!p && p.interests.some((i) => i === "family" || i.startsWith("family."));
}

export function primarySource(e: Event): string {
  return e.sources[0]?.source_id ?? "";
}

export function isLibrary(e: Event): boolean {
  return /\blibrary\b/i.test(`${e.location.venue_name ?? ""} ${e.organizer ?? ""}`);
}
