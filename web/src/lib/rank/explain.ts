// 1F. Explanations (RANKING.md §1F). Each sentence is literally a term of the score: the top positive
// contributions (≥ 0.12, at most 3) plus at most one caveat (a term ≤ −0.2). Honesty rules, unit-tested:
//   * a derived deadline never gets a countdown; estimates say "~"/"probably" and "estimate"
//   * "free" only when price.is_free; no superlatives; unknown values contribute 0 so never become reasons
//   * negatives are facts ("Aimed at kids & teens"), not judgments

import type { Event } from "../types";
import { fmtDay } from "../time";
import { strongestKey } from "./affinity";
import { distanceKm } from "./features";
import { family, GOALS, slotOf, whenPhrase } from "./profile";
import type { FeatureName, Features, RankContext, Reason, Scored } from "./types";

export const MIN_REASON = 0.12;
export const MIN_CAVEAT = -0.2;
export const MAX_REASONS = 3;

const famLabel = (e: Event, labels: Record<string, string>) => labels[family(e.category)] ?? family(e.category).replace(/_/g, " ");
const n2 = (x: number) => (x >= 1000 ? `${Math.round(x / 100) / 10}k`.replace(".0k", "k") : String(Math.round(x)));

function deadlineText(e: Event, now: Date): string | null {
  const r = e.registration;
  if (!r?.closes_at) return null;
  if (r.method === "derived") return "Registration required; no close date is published";
  const day = fmtDay(r.closes_at, e.timezone);
  const days = Math.round((new Date(r.closes_at).getTime() - now.getTime()) / 86_400_000);
  const when = days <= 3 ? ` (${days <= 0 ? "today" : days === 1 ? "tomorrow" : `in ${days} days`})` : "";
  return r.method === "extracted" ? `Registration closes ${day}${when}, per the listing text` : `Registration closes ${day}${when}`;
}

function crowdText(e: Event, positive: boolean): string | null {
  const a = e.attendance;
  if (!a) return null;
  const reported = a.inputs && "reported" in a.inputs;
  if (reported) return `Organizer reports ~${n2(a.mid)} people`;
  const band = `~${n2(a.low)}–${n2(a.high)}, estimate`;
  return positive ? `Probably a small crowd (${band})` : `Probably a big crowd (${band})`;
}

function scarcityText(e: Event): string | null {
  const t = e.tickets;
  if (!t) return null;
  if (t.spots_left != null && t.spots_total) return `${t.spots_total - t.spots_left} of ${t.spots_total} spots taken (reported)`;
  if (t.availability === "few_left") return "Seller flags few tickets left";
  if (t.availability === "limited") return "Seller reports limited availability";
  if (t.selling_fast && t.signal) return /listings/i.test(t.signal) ? `${t.signal[0].toUpperCase()}${t.signal.slice(1)} (listings aren't seats)` : `Signal: ${t.signal}`;
  return null;
}

/** Sentence for one feature's contribution, or null when the data can't honestly support one. */
export function template(f: FeatureName, e: Event, c: number, ctx: RankContext): string | null {
  const pos = c > 0;
  const p = ctx.profile;
  switch (f) {
    case "interest": {
      if (!pos) return "Outside your picks";
      const cats = [e.category, ...(e.categories ?? [])];
      const exact = p?.interests.find((i) => i.includes(".") && cats.includes(i));
      if (exact) return `You picked ${ctx.labels[exact] ?? exact}`;
      const fam = p?.interests.find((i) => !i.includes(".") && cats.some((x) => family(x) === i));
      return fam ? `You're into ${ctx.labels[fam] ?? fam}` : null;
    }
    case "goal_fit": {
      const g = p?.goals.find((x) => x !== "meet_people" && GOALS[x].families.includes(family(e.category)));
      if (g) return `Fits "${GOALS[g].label}"`;
      return p?.goals.includes("meet_people") ? (e.social?.reasons?.[0] ?? "Good for meeting people") : null;
    }
    case "social":
      return pos ? (e.social?.reasons?.[0] ?? "Good for meeting people") : "Not much mingling";
    case "category_prior":
      return pos ? `${famLabel(e, ctx.labels)}: high on our list for newcomers` : null;
    case "timeliness":
      return pos ? `Coming up ${whenPhrase(e)}, ${fmtDay(e.start, e.timezone)}` : null;
    case "deadline_urgency":
      return pos ? deadlineText(e, ctx.now) : null;
    case "early_bird": {
      const t = e.registration?.early_bird_ends_at;
      return t ? `Early-bird pricing ends ${fmtDay(t, e.timezone)}` : null;
    }
    case "time_fit": {
      const slot = slotOf(e);
      if (!p || !p.times.length) return pos ? `${whenPhrase(e)}: easy to make` : slot === "daytime" ? "During the workday" : null;
      return pos ? `${whenPhrase(e)}, one of your times` : slot === "daytime" ? "During the workday" : `It's on ${slot}`;
    }
    case "price_fit": {
      if (e.price.is_free) return "It's free";
      const lo = e.price.min;
      if (lo == null) return null;
      return pos ? `From $${Math.round(lo)}${p?.budget === "cheap" ? ", within your budget" : ""}` : `Costs from $${Math.round(lo)}`;
    }
    case "distance_fit": {
      const n = p?.neighborhood;
      const d = distanceKm(e, n ? ctx.neighborhoods[n] : null);
      if (d == null || !n) return null;
      return pos ? `${d.toFixed(1)} km from ${n}` : `${Math.round(d)} km from ${n}`;
    }
    case "solo":
      return "Easy to show up solo";
    case "beginner":
      return "Beginner friendly";
    case "recurring":
      return "Repeats, so you can become a regular";
    case "novelty":
      return e.is_new ? "Just listed (new on GetOffTheCouch this week)" : null;
    case "completeness":
      return pos ? "Full details listed (place, time, price)" : "Sparse listing: few details published";
    case "desc_info":
      return pos ? "Detailed description" : null;
    case "source_reliability":
      return pos && e.rank?.src_rel != null ? `Source has a strong track record (${Math.round(e.rank.src_rel * 100)}/100 reliability)` : null;
    case "corroboration": {
      const n = new Set(e.sources.map((s) => s.source_id)).size;
      return n > 1 ? `Listed by ${n} sources` : null;
    }
    case "field_trust":
      return e.sources.some((s) => s.source_id.startsWith("curated")) ? "Verified by hand (curated listing)" : null;
    case "crowd_fit":
      return crowdText(e, pos);
    case "established_venue":
      return "At an established venue (known capacity)";
    case "scarcity":
      return scarcityText(e);
    case "weather_fit": {
      const w = e.weather;
      if (!w) return null;
      return pos ? `Forecast: ${w.short.toLowerCase()} (NWS)` : `${Math.round(w.precip_pct ?? 0)}% chance of rain (NWS)`;
    }
    case "affinity": {
      const k = strongestKey(e, ctx.affinity, ctx.labels, ctx.now.getTime());
      return k ? k.text : null;
    }
    case "p_stale": {
      const d = Math.round((ctx.now.getTime() - new Date(e.last_checked).getTime()) / 86_400_000);
      return d >= 1 ? `Last confirmed ${d} day${d === 1 ? "" : "s"} ago, so check the link` : "Details may be out of date, so check the link";
    }
    case "p_low_quality":
      return "Sparse or administrative listing";
    case "p_kids_mismatch":
      return "Aimed at kids & teens";
    case "p_campus":
      return "Campus event (may be student-focused)";
    case "p_low_confidence":
      return "Location is approximate";
  }
  return null;
}

/** ≤ 3 reasons + ≤ 1 caveat, each tied to its contribution. */
export function reasons(e: Event, contrib: Features, ctx: RankContext): Reason[] {
  const terms = (Object.keys(contrib) as FeatureName[]).map((f) => ({ f, c: contrib[f] }));
  const out: Reason[] = [];
  const seen = new Set<string>();
  let when = false; // timeliness and time_fit both describe "when": say it once
  for (const { f, c } of terms.filter((t) => t.c >= MIN_REASON).sort((a, b) => b.c - a.c)) {
    if (out.length >= MAX_REASONS) break;
    if ((f === "timeliness" || f === "time_fit") && when) continue;
    const text = template(f, e, c, ctx);
    if (!text || seen.has(text)) continue;
    if (f === "timeliness" || f === "time_fit") when = true;
    seen.add(text);
    out.push({ text, weight: Math.round(c * 100) / 100, feature: f, kind: f === "affinity" ? "personal" : "reason" });
  }
  for (const { f, c } of terms.filter((t) => t.c <= MIN_CAVEAT).sort((a, b) => a.c - b.c)) {
    const text = template(f, e, c, ctx);
    if (!text) continue;
    out.push({ text, weight: Math.round(c * 100) / 100, feature: f, kind: "caveat" });
    break;
  }
  return out;
}

const SUPERLATIVE = /\b(best|most popular|hottest|top[- ]rated|#1|number one|must[- ]see)\b/i;

/** Golden rule 6 as a predicate: every reason maps to a nonzero term; no derived countdowns; no superlatives. */
export function honest(s: Scored): string[] {
  const problems: string[] = [];
  for (const r of s.reasons) {
    if (r.kind === "explore") continue;
    if (!r.feature || !s.contrib || Math.abs(s.contrib[r.feature]) < 1e-9) problems.push(`no contrib: ${r.text}`);
    if (SUPERLATIVE.test(r.text)) problems.push(`superlative: ${r.text}`);
    if (r.feature === "deadline_urgency" && s.event.registration?.method === "derived" && /\b(in \d+ days?|today|tomorrow|left)\b/i.test(r.text))
      problems.push(`countdown on derived deadline: ${r.text}`);
    if (/\bfree\b/i.test(r.text) && r.feature === "price_fit" && !s.event.price.is_free) problems.push(`free claim: ${r.text}`);
    if (r.feature === "crowd_fit" && !/~/.test(r.text)) problems.push(`estimate without ~: ${r.text}`);
  }
  return problems;
}
