import type { Event } from "../src/lib/types";

let n = 0;
export function ev(over: Partial<Event> = {}): Event {
  n += 1;
  return {
    id: `evt_${n}`,
    city: "testville",
    title: `Event ${n}`,
    kind: "one_off",
    category: "music.concert",
    start: "2026-10-20T00:00:00Z", // Mon Oct 19, 7pm Chicago
    timezone: "America/Chicago",
    location: {},
    price: { currency: "USD", is_free: false },
    sources: [{ source_id: "s", record_id: String(n), fetched_at: "2026-10-16T00:00:00Z" }],
    first_seen: "2026-10-16T00:00:00Z",
    last_checked: "2026-10-16T00:00:00Z",
    ...over,
  } as Event;
}

export const NOW = new Date("2026-10-16T15:00:00Z"); // Fri Oct 16, 10am Chicago
export const TZ = "America/Chicago";
