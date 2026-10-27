// Unit tests for the pure rank/ modules (RANKING.md §5.3.1): one table per feature, similarity bounds, MMR
// extremes, affinity decay, the seeded Beta sampler, and explanation honesty.
import { describe, expect, it } from "vitest";
import { affinity, decay, EMPTY, update, A0, B0 } from "../../src/lib/rank/affinity";
import { collapse } from "../../src/lib/rank/collapse";
import { candidates, windowFor } from "../../src/lib/rank/candidates";
import { capKey, mmr } from "../../src/lib/rank/diversify";
import { betaSample, pickExploration, seededRng } from "../../src/lib/rank/explore";
import { honest, reasons, template } from "../../src/lib/rank/explain";
import * as F from "../../src/lib/rank/features";
import { scoreOne } from "../../src/lib/rank/index";
import { normalize, score } from "../../src/lib/rank/score";
import { sim } from "../../src/lib/rank/similarity";
import { FEATURES, type Features, type RankContext, type Scored } from "../../src/lib/rank/types";
import { BASELINES, DEFAULT_WEIGHTS } from "../../src/lib/rank/weights";
import { DEFAULT_PROFILE } from "../../src/lib/rank/profile";
import { ev, NOW } from "../helpers";

const ctx = (over: Partial<RankContext> = {}): RankContext => ({ now: NOW, profile: null, labels: {}, neighborhoods: {}, surface: "for_you", ...over });
const H = 3_600_000;
const at = (h: number) => new Date(NOW.getTime() + h * H).toISOString();

describe("features (each in [0, 1], documented formulas)", () => {
  it("timeliness: plateau 3 days, then decays; started → 0.2; seasons neutral", () => {
    expect(F.timeliness(ev({ start: at(0.5) }), NOW)).toBe(0.2);
    expect(F.timeliness(ev({ start: at(48) }), NOW)).toBe(1);
    expect(F.timeliness(ev({ start: at(72 + 168) }), NOW)).toBeCloseTo(Math.exp(-1));
    expect(F.timeliness(ev({ kind: "season", start: at(900) }), NOW)).toBe(0.5);
  });
  it("deadline urgency: logistic around 5 days; derived deadlines (confidence 0.5) are halved", () => {
    const rep = ev({ registration: { closes_at: at(5 * 24), confidence: 1 } as never });
    const der = ev({ registration: { closes_at: at(5 * 24), confidence: 0.5, method: "derived" } as never });
    expect(F.deadlineUrgency(rep, NOW)).toBeCloseTo(0.5);
    expect(F.deadlineUrgency(der, NOW)).toBeCloseTo(0.25);
    expect(F.deadlineUrgency(ev({ registration: { closes_at: at(-1) } as never }), NOW)).toBe(0);
  });
  it("price fit: free 1, unknown 0.5 (neutral), budget rules", () => {
    expect(F.priceFit(ev({ price: { currency: "USD", is_free: true } }), "free")).toBe(1);
    expect(F.priceFit(ev(), "free")).toBe(0.5);
    expect(F.priceFit(ev({ price: { currency: "USD", is_free: false, min: 20 } }), "free")).toBe(0);
    expect(F.priceFit(ev({ price: { currency: "USD", is_free: false, min: 20 } }), "cheap")).toBe(1);
    expect(F.priceFit(ev({ price: { currency: "USD", is_free: false, min: 60 } }), "cheap")).toBeCloseTo(Math.exp(-1));
    expect(F.priceFit(ev({ price: { currency: "USD", is_free: false, min: 300 } }), "any")).toBe(0.5);
  });
  it("distance fit: exp(−km/4); unknown → 0.5", () => {
    expect(F.distanceFit(ev(), [44.98, -93.27])).toBe(0.5);
    expect(F.distanceFit(ev({ location: { lat: 44.98, lon: -93.27 } }), [44.98, -93.27])).toBe(1);
    expect(F.distanceFit(ev({ location: { lat: 44.98, lon: -93.27 } }), null)).toBe(0.5);
  });
  it("time fit: profile slots, newcomer prior without one", () => {
    const sat = ev({ start: "2026-10-17T18:00:00Z" }); // Sat 1pm Chicago
    const tueDay = ev({ start: "2026-10-20T15:00:00Z" }); // Tue 10am
    expect(F.timeFit(sat, null)).toBe(1);
    expect(F.timeFit(tueDay, null)).toBe(0.35);
    expect(F.timeFit(tueDay, { ...DEFAULT_PROFILE, times: ["daytime"] })).toBe(1);
    expect(F.timeFit(sat, { ...DEFAULT_PROFILE, times: ["weeknights"] })).toBe(0);
  });
  it("interest: exact 1, family 0.85, none 0.5, mismatch 0.15", () => {
    const e = ev({ category: "trivia_games.trivia" });
    expect(F.interest(e, { ...DEFAULT_PROFILE, interests: ["trivia_games.trivia"] })).toBe(1);
    expect(F.interest(e, { ...DEFAULT_PROFILE, interests: ["trivia_games"] })).toBe(0.85);
    expect(F.interest(e, null)).toBe(0.5);
    expect(F.interest(e, { ...DEFAULT_PROFILE, interests: ["music"] })).toBe(0.15);
  });
  it("crowd fit: small crowds 1, huge 0.4, blended by confidence", () => {
    const est = (mid: number, confidence: number) => ev({ attendance: { low: mid / 2, mid, high: mid * 2, method: "m", confidence } as never });
    expect(F.crowdFit(est(100, 1))).toBe(1);
    expect(F.crowdFit(est(20000, 1))).toBe(0.4);
    expect(F.crowdFit(est(100, 0))).toBe(0.5);
    expect(F.crowdFit(ev())).toBe(0.5);
  });
  it("scarcity, weather, staleness, penalties", () => {
    expect(F.scarcity(ev({ tickets: { availability: "few_left" } as never }))).toBe(1);
    expect(F.scarcity(ev({ tickets: { availability: "registration_open", spots_left: 2, spots_total: 20 } as never }))).toBe(1);
    expect(F.scarcity(ev({ tickets: { availability: "registration_open", spots_left: 9, spots_total: 30 } as never }))).toBe(0);
    expect(F.weatherFit(ev({ weather: { short: "Rain", precip_pct: 80 } as never }))).toBe(0);
    expect(F.weatherFit(ev({ weather: { short: "Sunny", precip_pct: 0 } as never }))).toBe(1);
    expect(F.weatherFit(ev())).toBe(0.6);
    expect(F.pStale(ev({ stale: true }), NOW)).toBe(1);
    expect(F.pStale(ev({ last_checked: at(-24 * 6) }), NOW)).toBe(1); // 144h since, SLA 72h
    expect(F.pKidsMismatch(ev({ tags: ["kids_teens"] }), null)).toBe(1);
    expect(F.pKidsMismatch(ev({ tags: ["kids_teens"] }), { ...DEFAULT_PROFILE, interests: ["family"] })).toBe(0);
    expect(F.pLowConfidence(ev({ location: { geocode_confidence: 0.3 } }))).toBeCloseTo(0.7);
  });
  it("every extracted feature is within [0, 1]", () => {
    const e = ev({ is_new: true, tags: ["kids_teens", "campus", "solo_friendly"], stale: true, rank: { fp: "x", lowq: 1, complete: 0, desc_len: 5000 } as never });
    const f = F.extract(e, ctx());
    for (const k of FEATURES) expect(f[k], k).toBeGreaterThanOrEqual(0), expect(f[k], k).toBeLessThanOrEqual(1);
  });
});

describe("score", () => {
  it("contributions are w × (f − baseline); unknown values contribute 0", () => {
    const f = { ...BASELINES } as Features;
    const { contrib } = score(f, DEFAULT_WEIGHTS, 99);
    for (const k of FEATURES) expect(Math.abs(contrib[k])).toBe(0);
  });
  it("affinity is off below 5 signals and capped at ±0.3", () => {
    const f = { ...BASELINES, affinity: 1 } as Features;
    expect(score(f, DEFAULT_WEIGHTS, 4).contrib.affinity).toBe(0);
    expect(score(f, { ...DEFAULT_WEIGHTS, affinity: 5 }, 5).contrib.affinity).toBe(0.3);
  });
  it("normalize: min-max with a minimum span", () => {
    expect(normalize([1, 3, 5])).toEqual([0, 0.5, 1].map((x) => expect.closeTo(x)));
    const tiny = normalize([4.0, 4.1]);
    expect(tiny[0]).toBeGreaterThan(0.9); // a 0.1-point gap isn't stretched into 0 vs 1
  });
});

describe("similarity and MMR", () => {
  const a = ev({ category: "music.concert", venue_id: "v", organizer: "X" });
  const b = ev({ category: "music.festival", venue_id: "v", organizer: "x " });
  const c = ev({ category: "volunteer.one_off", start: "2026-10-25T00:00:00Z", sources: [{ source_id: "other", record_id: "1", fetched_at: NOW.toISOString() }] });
  it("is symmetric, in [0, 1], and 1 for the same series", () => {
    for (const [x, y] of [[a, b], [a, c], [b, c]]) {
      expect(sim(x, y)).toBe(sim(y, x));
      expect(sim(x, y)).toBeGreaterThanOrEqual(0);
      expect(sim(x, y)).toBeLessThanOrEqual(1);
    }
    expect(sim(ev({ series_id: "s" }), ev({ series_id: "s" }))).toBe(1);
    expect(sim(a, b)).toBeGreaterThan(sim(a, c));
  });
  it("λ = 1 is pure ranking; λ = 0 maximizes spread", () => {
    const items: Scored[] = [a, b, c].map((event, i) => ({ event, score: 3 - i, reasons: [], rel: [1, 0.9, 0.5][i] }));
    expect(mmr(items, { lambda: 1, k: 3 }).map((s) => s.event.id)).toEqual([a.id, b.id, c.id]);
    expect(mmr(items, { lambda: 0.3, k: 2 }).map((s) => s.event.id)).toEqual([a.id, c.id]);
  });
  it("hard caps are never relaxed: ≤ 2 per source, ≤ 1 per series", () => {
    const same = [0, 1, 2, 3].map((i) => ({ event: ev({ category: `fitness.yoga`, series_id: i < 2 ? "dup" : undefined }), score: 1, reasons: [], rel: 1 - i / 10 }));
    const out = mmr(same, { lambda: 1, k: 4, caps: { maxPerSource: 2 } });
    expect(out).toHaveLength(2);
    expect(new Set(out.map((s) => s.event.series_id ?? s.event.id)).size).toBe(2);
  });
  it("I-160 cap key: organizer × venue, falling back to the source only when both are missing", () => {
    const src = (id: string) => [{ source_id: id, record_id: "r", fetched_at: NOW.toISOString() }];
    expect(capKey(ev({ organizer: " Volo  Sports ", venue_id: "v1", sources: src("volo") }))).toBe("o:volo sports|v:v1");
    expect(capKey(ev({ organizer: "Volo Sports", venue_id: "v1" }))).toBe(capKey(ev({ organizer: "volo sports", venue_id: "v1" })));
    expect(capKey(ev({ organizer: "Volo Sports", venue_id: "v1" }))).not.toBe(capKey(ev({ organizer: "Volo Sports", venue_id: "v2" })));
    expect(capKey(ev({ organizer: "--", venue_id: null, location: { venue_name: "Online" }, sources: src("feed") }))).toBe("src:feed");
    expect(capKey(ev({ organizer: null, venue_id: null, location: { venue_name: "Bar Nine" } }))).toBe("o:|v:bar nine");
  });
  it("I-160: an aggregator gets ≤ perSource across its venues, a one-room feed stays at ≤ perKey", () => {
    const src = (id: string) => [{ source_id: id, record_id: "r", fetched_at: NOW.toISOString() }];
    const trivia = Array.from({ length: 8 }, (_, i) => ev({ category: "trivia_games.trivia", organizer: "Trivia Co", venue_id: `bar${i}`, sources: src("trivia_co") }));
    const club = Array.from({ length: 8 }, () => ev({ category: "music.concert", organizer: "The Club", venue_id: "club", sources: src("club") }));
    const items: Scored[] = [...trivia, ...club].map((event, i) => ({ event, score: 1, reasons: [], rel: 1 - i / 100 }));
    const out = mmr(items, { lambda: 1, k: 10, caps: { maxPerKey: 2, maxPerSource: 3 } });
    expect(out.filter((s) => s.event.organizer === "Trivia Co")).toHaveLength(3);
    expect(out.filter((s) => s.event.organizer === "The Club")).toHaveLength(2);
  });
  it("the soft family cap yields when nothing else is left", () => {
    const items: Scored[] = Array.from({ length: 5 }, (_, i) => ({ event: ev({ category: "music.concert", venue_id: `v${i}` }), score: 1, reasons: [], rel: 1 - i / 10 }));
    expect(mmr(items, { lambda: 1, k: 5, caps: { maxPerFamily: 2 } })).toHaveLength(5);
  });
});

describe("candidates and collapse", () => {
  it("drop cancelled, past, sold out without resale, hard noise, dismissed; keep resale", () => {
    const w = windowFor("for_you", NOW);
    const keep = ev({ id: "keep" });
    const resale = ev({ id: "resale", tickets: { availability: "sold_out" } as never, offers: [{ kind: "resale", availability: "on_sale" }] as never });
    const out = candidates(
      [keep, resale, ev({ tickets: { availability: "cancelled" } as never }), ev({ start: at(-5) }), ev({ tickets: { availability: "sold_out" } as never }), ev({ rank: { fp: "f", flags: ["hard_noise"] } as never }), ev({ id: "gone" })],
      NOW,
      w,
      new Set(["gone"]),
    );
    expect(out.map((e) => e.id)).toEqual(["keep", "resale"]);
  });
  it("collapses series to the next date, multi-site groups to one card, near-dups to the better member", () => {
    const s1 = ev({ series_id: "s", start: at(30) });
    const s2 = ev({ series_id: "s", start: at(10) });
    const g1 = ev({ rank: { fp: "g1", group: "G", group_n: 3, quality: 0.4 } as never });
    const g2 = ev({ rank: { fp: "g2", group: "G", group_n: 3, quality: 0.9 } as never });
    const d1 = ev({ rank: { fp: "same", quality: 0.2 } as never });
    const d2 = ev({ rank: { fp: "same", quality: 0.8 } as never });
    const out = collapse([s1, s2, g1, g2, d1, d2]);
    expect(out.find((x) => x.event.series_id === "s")).toMatchObject({ event: s2, more: 1 });
    expect(out.find((x) => x.event.rank?.group === "G")).toMatchObject({ event: g2, sites: 3 });
    expect(out.filter((x) => x.event.rank?.fp === "same").map((x) => x.event)).toEqual([d2]);
  });
});

describe("affinity (Beta with 21-day decay toward the prior)", () => {
  const e = ev({ category: "trivia_games.trivia", venue_id: "v1" });
  it("starts neutral, learns from saves, decays back toward 0.5", () => {
    expect(affinity(e, EMPTY, NOW.getTime())).toBe(0.5);
    let s = EMPTY;
    for (let i = 0; i < 4; i++) s = update(s, e, "save", NOW.getTime());
    const now = affinity(e, s, NOW.getTime());
    const later = affinity(e, s, NOW.getTime() + 63 * 86_400_000); // three half-lives
    expect(now).toBeGreaterThan(0.6);
    expect(later).toBeLessThan(now);
    expect(later).toBeGreaterThan(0.5);
    const d = decay(s.keys[`cat:${e.category}`], NOW.getTime() + 1e13);
    expect(d.a).toBeCloseTo(A0);
    expect(d.b).toBeCloseTo(B0);
  });
  it("dismiss 'too far' touches the venue, never the topic", () => {
    const s = update(EMPTY, e, "dismiss", NOW.getTime(), "far");
    expect(Object.keys(s.keys)).toEqual(["venue:v1"]);
  });
});

describe("exploration", () => {
  it("seeded RNG is deterministic; Beta sampler mean within ±0.02 over 10k draws", () => {
    const r1 = seededRng("2026-10-16|minneapolis");
    const r2 = seededRng("2026-10-16|minneapolis");
    expect([r1(), r1(), r1()]).toEqual([r2(), r2(), r2()]);
    const rng = seededRng("beta");
    let sum = 0;
    for (let i = 0; i < 10_000; i++) sum += betaSample(2, 6, rng);
    expect(sum / 10_000).toBeCloseTo(0.25, 1);
    expect(Math.abs(sum / 10_000 - 0.25)).toBeLessThan(0.02);
  });
  it("respects a strong 'no' (decayed β ≥ 6) and is stable for a seed", () => {
    const no = ev({ category: "music.concert" });
    let s = EMPTY;
    for (let i = 0; i < 3; i++) s = update(s, no, "dismiss", NOW.getTime());
    for (let i = 0; i < 20; i++) expect(pickExploration(["music", "volunteer"], s, NOW.getTime(), seededRng(`x${i}`))).toBe("volunteer");
    expect(pickExploration(["music", "arts", "niche"], null, 0, seededRng("a"))).toBe(pickExploration(["niche", "arts", "music"], null, 0, seededRng("a")));
  });
});

describe("explanations (honesty rules)", () => {
  it("derived deadlines never get a countdown; reported ones may", () => {
    const der = ev({ registration: { closes_at: at(30), method: "derived", confidence: 0.5 } as never });
    const rep = ev({ registration: { closes_at: at(30), method: "reported", confidence: 1 } as never });
    expect(template("deadline_urgency", der, 0.3, ctx())).toBe("Registration required; no close date is published");
    expect(template("deadline_urgency", rep, 0.3, ctx())).toMatch(/Registration closes .* \(tomorrow\)/);
  });
  it("estimates are worded as estimates; reported attendance as reported", () => {
    const est = ev({ attendance: { low: 60, mid: 100, high: 200, method: "typical range", confidence: 0.25 } as never });
    const rep = ev({ attendance: { low: 100, mid: 120, high: 140, method: "reported", inputs: { reported: 120 }, confidence: 0.75 } as never });
    expect(template("crowd_fit", est, 0.2, ctx())).toBe("Probably a small crowd (~60–200, estimate)");
    expect(template("crowd_fit", rep, 0.2, ctx())).toBe("Organizer reports ~120 people");
  });
  it("unknown is never a reason; 'free' only when is_free; ≤ 3 reasons + ≤ 1 caveat", () => {
    const unknown = scoreOne(ev({ category: "music.concert" }), ctx());
    expect(unknown.reasons.some((r) => r.feature === "price_fit")).toBe(false);
    const kid = scoreOne(ev({ category: "family.kids", tags: ["kids_teens"], social: { score: 0.9, reasons: ["x"] }, price: { currency: "USD", is_free: true } }), ctx());
    expect(kid.reasons.filter((r) => r.kind === "caveat")).toEqual([expect.objectContaining({ text: "Aimed at kids & teens" })]);
    expect(kid.reasons.filter((r) => r.kind !== "caveat").length).toBeLessThanOrEqual(3);
    expect(honest(kid)).toEqual([]);
    const fake: Scored = { ...kid, reasons: [{ text: "The best night in town", weight: 1, feature: "social" }] };
    expect(honest(fake).join()).toMatch(/superlative/);
  });
  it("every reason maps to a nonzero contribution", () => {
    const s = scoreOne(ev({ category: "trivia_games.trivia", tags: ["solo_friendly"], series_id: "s", is_new: true, price: { currency: "USD", is_free: true } }), ctx({ profile: { ...DEFAULT_PROFILE, interests: ["trivia_games"] } }));
    expect(s.reasons.length).toBeGreaterThan(0);
    for (const r of reasons(s.event, s.contrib!, ctx())) expect(Math.abs(s.contrib![r.feature!])).toBeGreaterThan(0.1);
  });
});
