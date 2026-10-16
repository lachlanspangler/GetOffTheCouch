// "Why it's here": plain-language reasons built only from what the data actually says.
// Personal reasons (from saves and clicks on this device) are added by the ranking engine when available.
import { family } from "./categories";
import type { Event } from "./types";

const FAMILY_WHY: Record<string, string> = {
  sports_league: "Leagues are one of the easiest ways to meet people in a new city",
  volunteer: "Volunteering puts you next to the same people week after week",
  trivia_games: "Trivia is easy to join as a newcomer; teams often take strays",
  fitness: "Group workouts and run clubs are good places to start conversations",
  community: "A neighborhood event, good for getting a feel for the area",
  niche: "A niche crowd, which makes it easier to find your people",
};

export function whyThis(e: Event, now: Date): string[] {
  const out: string[] = [];
  const f = family(e.category);
  if (FAMILY_WHY[f]) out.push(FAMILY_WHY[f]);
  if (e.recurrence || (e.series_dates?.length ?? 0) > 2) out.push(`It repeats${e.recurrence ? ` (${e.recurrence.replace(/^Every /, "every ").replace(/\b(am|pm)\b/g, (m) => m.toUpperCase())})` : ""}, so you can become a regular`);
  if ((e.tags ?? []).includes("solo_friendly")) out.push("The listing says it's fine to come on your own");
  if ((e.tags ?? []).includes("beginner_friendly")) out.push("Beginners are welcome, according to the listing");
  if (e.price.is_free) out.push("It's free");
  if (e.sources.length > 1) out.push(`Listed by ${e.sources.length} separate sources`);
  if (e.is_new && now.getTime() - new Date(e.first_seen).getTime() < 3 * 86_400_000) out.push("Newly listed this week");
  return out.slice(0, 4);
}
