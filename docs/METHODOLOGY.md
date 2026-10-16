# Methodology

This doc covers how GetOffTheCouch turns raw listings into the cards you see. Keep it in sync with `gotc/pipeline/` whenever a formula changes.

## Provenance: every value says where it came from
| Method | Meaning | Example |
|---|---|---|
| `reported` | The source said so | Ticketmaster `priceRanges` |
| `derived` | Deterministic transform of reported data | geocoding an address; "volunteering is free" |
| `extracted` | Pulled from free text, with the sentence kept as `evidence` | "Register by Nov 3" |
| `estimated` | A model. Always a low/mid/high band plus a method string | crowd size |
| `curated` | Verified by hand from a quoted page, re-checked automatically | league dates from a club website |

Each event carries `provenance[field] = {source, fetched_at, method, confidence}` for title, start, location, category, price and registration.

## Entity resolution (dedup)
1. **Venues.** Names are normalized: case, accents and "&" are folded, and filler words are dropped ("the", "theatre", "hall"…). Two venues are the same if the normalized names match, or if they're under 150 m apart with ≥ 0.8 name similarity.
2. **Events.** Blocked by local calendar day, then compared only across different sources. A pair matches when all of these hold:
   - Starts are within 3 h (unless all-day).
   - Same place: the same venue entity, or < 400 m apart, or venue names ≥ 0.85 similar.
   - Normalized titles are ≥ 0.82 similar. Normalization strips "presents", "live", "tour", years and ticket noise.

   With no location at all, titles must be ≥ 0.95 similar and starts within 15 min.

   Two records from the same source are never merged, even transitively.
3. **Merging.** Fields come from the most-trusted member. The order is curated > Ticketmaster > SeatGeek > others. All offers are kept, so you can compare prices across sellers.
4. **Sticky ids.** If any member already belonged to an event, the cluster keeps the oldest such id. Links and saved events survive re-runs.

## Series
Occurrences from the same source with the same normalized title and the same place share a `series_id`. With 3 or more occurrences, the kind becomes `recurring`. The list view shows one card per series ("+3 more dates"). The calendar shows every date.

## Attendance estimate (`enrich.estimate_attendance`)
| Inputs available | Estimate | Confidence |
|---|---|---|
| Organizer/source reported a number | ±15% | 0.75 |
| Venue capacity known | capacity × fill band for ticket status. Sold out: 90–100%. Few left: 75–97%. On sale: 40–88%. Unknown: 20–85% | 0.6 (0.4 if status unknown) |
| Nothing | the category prior `[p10, p50, p90]` from `config/taxonomy.yaml` | 0.25 |

All numbers are rounded to 2 significant figures and capped at capacity. The UI always shows the band and the method.

## Tickets: "% left", selling fast, price trend
No legitimate source gives third parties real seat inventory, so these are labeled signals, never facts:
- **% left.** Resale listings now ÷ the most listings we've seen for this event (peak ≥ 10). The band is ±40% relative and confidence is 0.35. The method text says "listings are not seats". Sold out on the primary seller shows 0–5%.
- **Selling fast** fires on any of these:
  - listings down ≥ 25% versus 24–96 h ago (peak ≥ 20)
  - the seller flags few tickets left
  - the lowest price up ≥ 20% in the trend window
- **Price trend.** The lowest listed price over the last 7 days of snapshots. Under 5% change counts as flat.

### Reported spots (the one real "% left")
Library systems publish capacity and registration counts per program. When a source reports both, `pct_left` is exact. For example, "17 of 20 spots taken (reported by hclib_events)" gives low = mid = high, with confidence 0.9.

Attendance is then anchored on actual signups: the band runs from registered × 0.75 to capacity. With ≤ 20% of spots left, the event is marked selling fast. At 0 left, registration is marked closed.

## Deadlines
Deadlines come from structured registration fields first. Otherwise they're extracted from descriptions with phrase patterns ("register by", "registration closes", "deadline:", "early-bird … ends", "registration opens"). Guards:
- The date must parse.
- It must fall between 7 days ago and the event start + 1 day.
- A date without a year rolls forward.
- A date without a time means 11:59 pm.

The earliest match wins. The sentence it came from is shown.

**Derived deadlines.** Some programs require registration but publish no close date, such as league programs with only an "opens" date, or library programs flagged "registration required". These get `closes_at = start` with `method: derived`, confidence 0.5, and an evidence sentence saying no close date is published.

The UI never shows a countdown for derived deadlines. It shows "Registration required" or "3 of 15 spots left". In the Deadlines view, they sit apart from published deadlines under "Sign up before it starts".

## Good for meeting people (0–1)
The score starts from the category prior in `taxonomy.yaml` (leagues 0.9, trivia 0.85, volunteering 0.8, big concerts 0.35…), then adjusts:

| Signal | Adjustment |
|---|---|
| Recurring | +0.08 |
| Solo- or free-agent-friendly | +0.10 |
| 10–250 expected attendees | +0.05 |
| Over 5,000 expected | −0.15 |
| Beginner friendly | +0.04 |

The reasons are shown with the score.

## Freshness
Every source has an SLA by data type (`config/sources.yaml`):
- ticket prices: 4 h
- concerts: 12 h
- events, leagues, volunteering and openings: 24 h
- recurring: 48 h
- conventions: 7 d
- curated: 14 d per source

An event is **stale** when its freshest member was last confirmed longer ago than that member's SLA. Stale events stay visible with a reason. They're never silently dropped.

## Curated facts: page-watch
Curated entries and starter-pack rules store a verbatim `evidence` quote. Each run re-fetches the source page and checks every quote fragment is still present, ignoring markup, whitespace and quote style:
- **Still there:** the fact counts as re-verified now.
- **Missing:** the card is flagged "page changed", confidence drops, and the freshness clock stops, so it turns stale on schedule.
- **Page blocked:** the check is skipped and the fact ages normally.

## Recommendations (dashboard, `web/src/lib/recommend.ts`)
Scoring is a transparent sum of rules, each with the sentence it adds: interests, goals, budget, time of week, distance from your neighborhood, solo-friendliness, recurrence, deadline urgency, and a stale-data penalty.

The 30-day plan is greedy per week: up to 3 picks, with no time overlaps, one occurrence per series, and a −0.45 diversity penalty per repeated category family.

Nothing is learned from other users. Preferences stay on the device.
