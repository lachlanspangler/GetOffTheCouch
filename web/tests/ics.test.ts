import { describe, expect, it } from "vitest";
import { calendar } from "../src/lib/ics";
import { ev } from "./helpers";

describe("ics", () => {
  it("produces a valid calendar with alarms and escaped text", () => {
    const e = ev({ title: "Trivia; Night, Vol 2", location: { venue_name: "Pub", address: "1 Main St, Minneapolis" }, registration: { closes_at: "2026-10-18T04:59:00Z" } as never });
    const out = calendar([e]);
    expect(out.startsWith("BEGIN:VCALENDAR\r\n")).toBe(true);
    expect(out.trim().endsWith("END:VCALENDAR")).toBe(true);
    expect(out).toContain(String.raw`SUMMARY:Trivia\; Night\, Vol 2`);
    expect(out).toContain("DTSTART:20261020T000000Z");
    expect(out.match(/BEGIN:VEVENT/g)).toHaveLength(2); // event + deadline
    expect(out).toContain("TRIGGER:-P2D");
    expect(out.split("\r\n").every((l) => l.length <= 75)).toBe(true);
  });

  it("deadline-only mode exports just the deadline", () => {
    const e = ev({ registration: { closes_at: "2026-10-18T04:59:00Z" } as never });
    const out = calendar([e], { mode: "deadlines" });
    expect(out.match(/BEGIN:VEVENT/g)).toHaveLength(1);
    expect(out).toContain("Register:");
  });

  it("all-day events use DATE values", () => {
    expect(calendar([ev({ all_day: true, start: "2026-11-01T05:00:00Z" })], { mode: "events" })).toContain("DTSTART;VALUE=DATE:20261101");
  });
});
