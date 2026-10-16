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

## Recommendations (dashboard, `web/src/lib/recommend.ts` → `web/src/lib/rank/`)
Ranking v2 is the default since 2026-10-16. The design is `docs/research/RANKING.md`; its "Results" section has the measured numbers. v1 (the additive rule list) stays as the comparison baseline: set `localStorage["gotc:ranker"] = "v1"` to use it.

**Pipeline hints (`gotc/pipeline/rankprep.py`, schema 1.5.0, `Event.rank`).** Computed at export from the full record, profile-independent:
- `fp`: a near-duplicate fingerprint (normalized title, venue or ~300 m cell, local date). Same-day, same-place titles with char-3-gram Jaccard ≥ 0.8 share one.
- `group` / `group_n`: the same program on the same day at 2+ venues (library storytime at 5 branches).
- `desc_len`: full description length (the card feed only has 240 characters).
- `flags` / `lowq`: administrative and low-information flags. The weighted sum is capped at 1. The flags are admin phrases, cancelled titles, generic titles, all caps, shouting, no info, no place, promo, long span, daily non-habit series, service desks (tech help, legal clinics, ESL classes) and specific-audience listings.
- `complete`: the share of 7 key fields present. `quality = complete × (1 − lowq)`.
- `src_rel`: the best member unit's 30-day reliability, 0–1.

**Browser (all pure functions except `affinityStore.ts`).**
1. *Candidates.* Removes anything cancelled, postponed, past, sold out without resale, closed for registration, hard noise or dismissed.
2. *Collapse.* One card per series, multi-site group and fingerprint.
3. *Features.* 29 features, each in [0, 1], with formulas documented in `features.ts`.
4. *Score.* A linear sum with a weight table (`weights.ts`). Each feature's contribution is measured against a neutral baseline, so an unknown value contributes exactly 0.
5. *Diversify.* MMR re-rank with hard caps: ≤ 2 per source and ≤ 1 per series, group or fingerprint in every 10, ≥ 3 families, no kids content for adults, nothing with `lowq ≥ 0.7`, and ≤ 1 library event in Highlights.
6. *Explain.* At most 3 reasons plus 1 caveat, each literally a score term. A derived deadline never gets a countdown. Estimates say "~" and "estimate". An unknown value is never a reason.

**Personalization is on-device only** (`localStorage`, nothing sent anywhere):
- Learning signals: saves, calendar adds, opens of ≥ 5 s, outbound clicks, unsaves and "Not for me" dismisses.
- The model: Beta counts per family, category, venue, time slot and a small tag vocabulary, with a 21-day half-life that decays back toward neutral.
- Limits: it switches on after 5 signals and its effect is capped at ±0.3. A "too far / price / time" dismiss never touches the topic.
- Exploration: one slot (position 4) is filled by seeded Thompson sampling over families missing from the list.
- Family floor: once there are 14 days of history, a family that hasn't been shown in 14 days gets one slot.
- `whySeeingThis()` (in `recommend.ts`) returns the plain-language "Why am I seeing this?" data.

The plan uses the same score and caps: per week, MMR λ 0.55 over picks with no time overlaps and one per series. Nothing is learned from other users.

## Openings (new bars and restaurants)
These come from government license data. They're always presented as a *signal*, not a confirmed opening date.
- **Newness dates.** Where a dataset has a real newness date (original issue, application or pending date), that's the date shown. Openings stay visible for 60 days.
- **No newness date.** Some datasets only carry renewal dates (Minneapolis On_Sale_Liquor), so `openings_by_first_seen` applies:
  - The first snapshot is a silent baseline. Existing businesses aren't news.
  - A license that appears later is shown with the day we first saw it, labeled "First appeared in the city's license data on …".
- **Privacy.** Personal-data columns (owners, applicants, phones, e-mails) are dropped before mapping (`gotc/adapters/mapped.py`).

## Coverage and the go-live gate (`gotc/pipeline/gate.py`, ADR-0008)
Every city carries a `coverage` block, published in `index.json` and in its feed. The dashboard reads it and never computes coverage itself.
- **Pillars** (counts from the exported events, so they match what's shown):

  | pillar | what counts | "strong" at |
  |---|---|---|
  | Leagues | upcoming `sports_league.*` events (seasons are planned months ahead) | 5 |
  | Openings & parties | openings first seen in the last 60 days, plus `nightlife.*` in the next 30 days | 10 |
  | Concerts | `music.*` in the next 30 days | 20 |
  | Volunteering | `volunteer.*` in the next 30 days | 5 |
  | Cons & faires | upcoming `niche.*` | 2 |
  | Trivia & games | `trivia_games.*` in the next 30 days | 5 |
  | Deadlines | published (not derived) registration deadlines in the next 60 days | 10 |

  A pillar is ✓ strong at its bar, ◐ thin below it, ✕ none at zero. The none state carries a note naming the gap ("we have no license or nightlife data for this city"). A thin pillar whose events all come from the curated registry says "all curated".
- **Gate criteria G1–G11** follow docs/research/SCALING.md §3. **Hard** criteria decide the tier; **soft** misses become "thin coverage" reasons. Two are calibrated, so that one rule doesn't block every city:
  - **G9:** a unit counts as recent if it succeeded within max(48 h, 2 × its cadence). Weekly sources aren't late between runs.
  - **G10:** a "green run" is one where ≤ max(1, 10 %) of the city's attempted units failed, in a streak of ≥ 3 runs spanning ≥ 48 h. Reject rate (7 days) must be < 10 % and geofence drops < 5 %.
  - **G2:** the bar drops from 250 to 150 events in the next 14 days for metros under 1.5 M people (Census CBSA population in `config/metros.yaml`).
- **Tiers:** live (all hard criteria pass), beta (enabled, a hard miss), hidden (`enabled: false`, not exported).
  - New cities start in beta. The ten cities published before the gate existed start live.
  - A live city that fails a hard criterion gets a banner after 72 h and drops to beta after 7 days, so one bad week doesn't flap the picker.
  - Every change is logged (`gate@<city>` in the health log).
- **Shares** (G6–G8, G11, top-source share) are computed over upcoming exported events. The geocode rate is the share with coordinates. Online-only events are skipped at ingest, so they never count against a city.
