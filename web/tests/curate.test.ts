import { describe, expect, it } from "vitest";
import { displayPlace, displayTitle, displayVenue, distanceNote, isAdminRole, isKids, isLeadable, isUnderway } from "../src/lib/curate";
import { ev, NOW } from "./helpers";

describe("display curation", () => {
  it("fixes shouting titles but leaves mixed case alone", () => {
    expect(displayTitle("LAURA VEIRS")).toBe("Laura Veirs");
    expect(displayTitle("VOLUNTEERS NEEDED!!!")).toBe("Volunteers Needed!");
    expect(displayTitle("DJ NIGHT AT THE ROOFTOP")).toBe("DJ Night at the Rooftop");
    expect(displayTitle("iPhone Photo Walk")).toBe("iPhone Photo Walk");
    expect(displayTitle("Kabin — new liquor license application")).toBe("Kabin");
  });

  it("never shows a raw address, a bare city or TBD as the venue", () => {
    expect(displayVenue(ev({ location: { venue_name: "990 Lone Oak Rd, Suite 136, Eagan, MN" } }))).toBeNull();
    expect(displayVenue(ev({ location: { venue_name: "Minneapolis" } }), "Minneapolis")).toBeNull();
    expect(displayVenue(ev({ location: { venue_name: "ADDRESS:TBD" } }))).toBeNull();
    expect(displayVenue(ev({ location: { venue_name: "First Avenue" } }))).toBe("First Avenue");
    expect(displayPlace(ev({ location: { address: "WEST 97 STREET between COLUMBUS AVENUE and AMSTERDAM" } }))).toBe("West 97 Street");
  });

  it("labels places far from the center", () => {
    const e = ev({ location: { lat: 44.85, lon: -93.15, address: "1 Main St, Eagan, MN 55121" } });
    expect(distanceNote(e, [44.98, -93.27])).toMatch(/^Eagan · \d+ mi$/);
    expect(distanceNote(ev({ location: { lat: 44.98, lon: -93.26 } }), [44.98, -93.27])).toBeNull();
  });
});

describe("what leads the city page", () => {
  it("keeps kids' programs, admin roles and openings out of the lead", () => {
    expect(isKids(ev({ title: "Fall Crafts for Toddlers & Families", category: "volunteer.one_day" }))).toBe(true);
    expect(isAdminRole(ev({ title: "Board Members and Treasurer: Help Lead" }))).toBe(true);
    expect(isLeadable(ev({ kind: "opening" }))).toBe(false);
    expect(isLeadable(ev({ title: "Tuesday Trivia" }))).toBe(true);
  });

  it("treats events that started over an hour ago (no end) as underway", () => {
    expect(isUnderway(ev({ start: new Date(NOW.getTime() - 2 * 3600_000).toISOString() }), NOW)).toBe(true);
    expect(isUnderway(ev({ start: new Date(NOW.getTime() - 20 * 60_000).toISOString() }), NOW)).toBe(false);
    expect(isUnderway(ev({ start: new Date(NOW.getTime() - 2 * 3600_000).toISOString(), end: new Date(NOW.getTime() + 3600_000).toISOString() }), NOW)).toBe(false);
  });
});
