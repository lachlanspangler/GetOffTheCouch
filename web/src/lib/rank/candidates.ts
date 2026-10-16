// 1A. Candidate generation: a pure filter (RANKING.md §1A). Nothing here scores; it only removes things
// no surface should ever show: cancelled, postponed, past, sold out without resale, closed registration,
// hard administrative noise ("Closed for private event", "CANCELED: Yoga"), and what the user dismissed.

import type { Event } from "../types";
import { liveAvailability } from "../filters";

const H = 3_600_000;
const D = 24 * H;

export interface Window {
  from: Date;
  to: Date;
}

export function windowFor(surface: string, now: Date, startDate?: string | null): Window {
  const start = startDate && new Date(startDate) > now ? new Date(startDate) : now;
  const days = surface === "highlights" || surface === "similar" ? 7 : surface === "plan" ? 28 : 30;
  return { from: start, to: new Date(start.getTime() + days * D) };
}

export function hasResale(e: Event): boolean {
  return (e.offers ?? []).some((o) => o.kind === "resale" && o.availability !== "sold_out");
}

export function registrationClosed(e: Event, now: Date): boolean {
  return liveAvailability(e, now) === "registration_closed";
}

export function isPast(e: Event, now: Date): boolean {
  const end = e.end ? new Date(e.end).getTime() : new Date(e.start).getTime() + 2 * H;
  return end < now.getTime();
}

export function hardNoise(e: Event): boolean {
  return (e.rank?.flags ?? []).includes("hard_noise");
}

/** Never shown on any ranked surface (golden rule 1). */
export function excluded(e: Event, now: Date): boolean {
  const a = liveAvailability(e, now);
  if (a === "cancelled" || a === "postponed") return true;
  if (a === "sold_out" && !hasResale(e)) return true;
  if (a === "registration_closed" && (e.kind === "season" || e.registration?.closes_at)) return true;
  if (e.kind !== "opening" && isPast(e, now)) return true;
  return hardNoise(e);
}

export function inWindow(e: Event, w: Window, now: Date): boolean {
  const s = new Date(e.start).getTime();
  const end = e.end ? new Date(e.end).getTime() : s + 2 * H;
  if (e.kind === "opening") return now.getTime() - new Date(e.first_seen).getTime() <= 60 * D;
  if (e.kind === "season") {
    const c = e.registration?.closes_at;
    if (c) {
      const t = new Date(c).getTime();
      return t >= now.getTime() && t <= w.to.getTime() + 30 * D; // registration still open and closing soon-ish
    }
    return s >= w.from.getTime() && s <= w.to.getTime();
  }
  if (s >= w.from.getTime() && s <= w.to.getTime()) return true;
  // already running: only short things (a weekend festival), never month-long exhibits that would win every day
  return s < w.from.getTime() && end >= w.from.getTime() && end - s <= 3 * D;
}

export function candidates(
  events: Event[],
  now: Date,
  w: Window,
  dismissed?: ReadonlySet<string>,
): Event[] {
  return events.filter(
    (e) =>
      !excluded(e, now) &&
      inWindow(e, w, now) &&
      !(dismissed && (dismissed.has(e.id) || (e.series_id && dismissed.has(e.series_id)))),
  );
}
