import { describe, expect, it } from "vitest";
import { cardSignals, priceSignal, statusLine } from "../src/lib/signals";
import { fmtTimeRange } from "../src/lib/time";
import { ev, NOW, TZ } from "./helpers";

const reg = (over: object) => ({ required: true, method: "reported", ...over }) as never;

describe("card signal budget (DESIGN.md §4.6)", () => {
  it("shows at most one status line, chosen by priority", () => {
    const e = ev({ stale: true, stale_reason: "source down", tickets: { availability: "cancelled" } as never });
    expect(statusLine(e, NOW)?.text).toMatch(/^Listing may be out of date/);
    const c = ev({ tickets: { availability: "cancelled" } as never, registration: reg({ closes_at: "2026-10-17T04:59:00Z" }) });
    expect(statusLine(c, NOW)).toMatchObject({ text: "Cancelled", tone: "critical" });
  });

  it("uses critical only inside 48 hours, caution to 14 days, and absolute dates", () => {
    const soon = ev({ registration: reg({ closes_at: "2026-10-17T04:59:00Z" }) }); // 11:59 PM tonight in Chicago
    expect(statusLine(soon, NOW)).toMatchObject({ text: "Registration closes today at 11:59 PM", tone: "critical" });
    const week = ev({ registration: reg({ closes_at: "2026-10-22T23:00:00Z" }) });
    expect(statusLine(week, NOW)).toMatchObject({ text: "Registration closes Thu, Oct 22", tone: "caution" });
    const far = ev({ registration: reg({ closes_at: "2026-11-30T23:00:00Z" }) });
    expect(statusLine(far, NOW)).toMatchObject({ text: "Registration open until Mon, Nov 30", tone: "secondary" });
  });

  it("never shows a countdown for a derived deadline", () => {
    const d = ev({ registration: reg({ method: "derived", closes_at: "2026-10-17T04:59:00Z" }) });
    expect(statusLine(d, NOW)).toMatchObject({ text: "Registration required", tone: "secondary" });
  });

  it("shows spots only when few are left, and Full at zero", () => {
    expect(statusLine(ev({ tickets: { spots_left: 4, spots_total: 24 } as never }), NOW)?.text).toBe("4 of 24 spots left");
    expect(statusLine(ev({ tickets: { spots_left: 18, spots_total: 24 } as never }), NOW)).toBeNull();
    expect(statusLine(ev({ category: "learning.class", tickets: { spots_left: 0, spots_total: 24 } as never }), NOW)?.text).toBe("Full");
  });

  it("has one tag at most and never a price guess", () => {
    const s = cardSignals(ev({ social: { score: 0.9 } as never, tags: ["solo_friendly", "beginner_friendly"] }), NOW);
    expect(s.tag).toBe("Good for meeting people");
    expect(s.price).toBeNull();
    expect(priceSignal(ev({ price: { currency: "USD", is_free: true } }))).toBe("Free");
    expect(priceSignal(ev({ price: { currency: "USD", is_free: false, min: 12, max: 20 } }))).toBe("$12–$20");
  });
});

describe("time ranges", () => {
  it("shares the meridiem and uses an en dash", () => {
    expect(fmtTimeRange("2026-10-20T00:00:00Z", "2026-10-20T03:00:00Z", TZ)).toBe("7–10 PM");
    expect(fmtTimeRange("2026-10-17T16:00:00Z", "2026-10-17T19:00:00Z", TZ)).toBe("11 AM–2 PM");
    expect(fmtTimeRange("2026-10-20T00:30:00Z", null, TZ)).toBe("7:30 PM");
  });
});
