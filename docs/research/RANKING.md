# Ranking v2: research and implementation design

Status: implemented 2026-10-16 (rollout steps 1–6 of §5.4; step 7, learned weights, is not done). v2 is the default ranker behind `RANKER_V2` in `web/src/lib/recommend.ts`; `localStorage["gotc:ranker"] = "v1"` switches back. Measured results and every deviation from this design are in §7 "Results" below. Read §7 before trusting the numbers in §1: some proposed values changed after evaluation.

Scope: how the dashboard picks and orders events for a brand-new resident (Highlights, For You, the 30-day plan, Similar). The pipeline facts it relies on are in `docs/METHODOLOGY.md` and `gotc/schema.py` (`SCHEMA_VERSION` 1.4.0).

---

## 0. Where v1 stands, and what the data looks like

**v1 (`recommend.ts`)** is an additive rule list. Every rule adds a weight and a sentence. Highlights and the plan use greedy hard constraints: one per family, at most 2 per source, one library, one per series, and a −0.45 penalty per repeated family. This is the right philosophy (explainable, on-device, no other users' data). Its weak spots:

1. **Unbounded, unnormalized sums.** Interests (+1.0) and kids (−0.9) sit on the same scale as rain (−0.4), with no notion of feature range. Adding a rule silently re-weights all the others.
2. **No quality signal.** An event with no venue, no price, no description and a one-word title scores the same as a fully specified one. Highlights filters out some of this with hard rules (venue required, "TBD/online" banned), but For You and the plan don't.
3. **Diversity only by family** (plus ad-hoc library/source caps), applied in two different greedy loops.
4. **No learning at all**, not even on-device from the user's own saves and dismisses.
5. **No offline evaluation.** The tests check mechanics ("explains every point"), not whether the top 10 is good.

**The data (Minneapolis export, 872 events) explains why quality and diversity matter more than relevance:**

| Fact | Count | Implication |
|---|---|---|
| Top source `hclib_events` (library) | 268 (31%) | One source can flood any list without per-source caps |
| `family` + `kids_teens` tag | 120 family-category events, 154 kids-tagged | The "kids for adults" guard is a top-3 rule |
| Price unknown (not free, no min) | 703 (81%) | "Price fit" must treat unknown as neutral, not as cheap or pricey |
| No venue name | 148 (17%) | Completeness is a real separating signal |
| Events with >1 source (corroborated) | 2 | Corroboration is rare. Weight it low: a bonus, not a requirement |
| In a series | 510 (58%) | Series collapse has to happen before ranking, not after |
| `recurring` tag | 366 | Recurring is common, so "repeats" can't be a big boost |

These shares differ by city. NYC and LA lean on Ticketmaster, Minneapolis on library and park calendars. So the weights below are chosen to be robust rather than tuned to one feed.

---

## 1. The v2 pipeline

```
feed.json ─▶ [A] candidates ─▶ [B] dedup / collapse ─▶ [C] features ─▶ [D] score ─▶ [E] diversify ─▶ [F] explain
               (pure filter)     (groups, series)       (0..1 each)     (linear)     (MMR + hard caps)  (reasons)
                                                                          ▲
                                                          on-device affinity (section 2)
```

This is the same multi-stage shape as industrial feeds, scaled down: YouTube splits candidate generation from ranking [Covington 2016]. Instagram Explore runs three ranking passes, each with more features [Meta 2019]. Pinterest's Pixie does cheap candidate retrieval before ranking [Eksombatchai 2018]. We have about 1,000 items per city, so every stage runs in the browser in milliseconds and the "cheap first pass" reduces to a filter.

### 1A. Candidate generation (pure filter)

```ts
candidates(events, ctx) = events.filter(e =>
  e.city === ctx.city &&
  (!e.is_demo || ctx.demo) &&
  inWindow(e, ctx) &&                    // see below
  !["cancelled","postponed"].includes(liveAvailability(e, now)) &&
  !(liveAvailability(e, now) === "sold_out" && !hasResale(e)) &&
  !(registrationClosed(e, now) && (e.kind === "season" || e.registration?.closes_at)) &&
  !isPast(e, now) &&                     // (end ?? start + 2h) < now
  !hardNoise(e))                         // section 4: rentals, "closed", staff-only, test listings
```

Windows: Highlights uses `[now, now+7d]`. For You uses `[now, now+30d]`. The plan uses `[start, start+30d]`, where `start` is `profile.startDate` if it's later than now. Openings use `first_seen ≤ 60 d`. Seasons stay in if registration is open, or its `closes_at` falls inside the window.

Ongoing all-day multi-week items (exhibits) are allowed in only if `end - start ≤ 3 d`, or if they're pinned to the "Ongoing" shelf. Otherwise they win every day by default.

### 1B. Dedup and collapse (before scoring)

Entity resolution in the pipeline already merges cross-source duplicates (METHODOLOGY section "Entity resolution"). The browser still needs three collapses:

1. **Series collapse.** Keep the next upcoming occurrence per `series_id`. Carry `series_dates.length` for "+N more dates".
2. **Multi-site collapse.** The same program runs at several branches on the same day (library storytime at 6 branches, "Volunteer shift" across sites). Key: `norm(title) + organizer + local_date`. When the group has 3 or more venues, show one card "at 6 locations". Pick the branch nearest to `profile.neighborhood`, else the one with the most complete data. The Python pipeline precomputes this as `rank.group_id` / `rank.group_size` (section 5).
3. **Near-duplicate collapse.** Same-source records the resolver refuses to merge (by design), plus cross-source pairs just under its thresholds. Fingerprint:
   `fp = sha1(normTitle(title) | venue_id ?? geocell(lat,lon,~300m) | local_date)`.
   Equal `fp` means duplicates. Otherwise, inside a `(local_date, venue_id)` block, a char-3-gram Jaccard ≥ 0.8 on normalized titles counts as a duplicate. Keep the member with the higher quality score (feature 9).

### 1C. Feature extraction

Every feature maps into **[0, 1]**, with 0 meaning "absent/neutral-low". Penalties are separate features that also run 0 to 1 and get negative weights. That keeps the score a convex-ish combination of comparable units. `h` = hours until start, `d` = days.

| # | Feature | Formula (TS-ish) | Data |
|---|---|---|---|
| 1 | `timeliness` | `h < 1 ? 0.2 : h ≤ 72 ? 1 : exp(-(h - 72) / 168)`. Plateau for the next 3 days, then half-life about 4.8 d | `start` |
| 2 | `deadline_urgency` | `c = closes_at; d = days(c - now); d ≤ 0 ? 0 : 1 / (1 + exp((d - 5) / 1.5))`, × `registration.confidence` (derived deadlines are 0.5, so they're halved) | `registration` |
| 3 | `early_bird` | `early_bird_ends_at` in `(now, now + 7d]` ? 1 : 0 | `registration` |
| 4 | `social` | `social.score ?? 0.4` | enrich |
| 5 | `recurring` | `series_id ∨ kind = recurring ? 1 : 0` | |
| 6 | `solo` | `tags ∋ solo_friendly ∨ free_agent ? 1 : 0` | tags |
| 7 | `beginner` | `tags ∋ beginner_friendly` or `skill_levels ∋ beginner/all` | |
| 8 | `novelty` | `is_new ? 1 : exp(-ageHours(first_seen) / 72) × 0.5` | `is_new`, `first_seen` |
| 9 | `completeness` | mean of 7 bits: real venue (not generic), lat/lon, price known (`is_free ∨ min ≠ null`), `url`, end time, description ≥ 80 chars, category ≠ `other` | many |
| 10 | `desc_info` | `min(1, ln(1 + len) / ln(1 + 400))`. `len` is precomputed, because `summary` lives in `details.json` | `rank.desc_len` |
| 11 | `source_reliability` | `(reliability.score ?? 80) / 100` for the event's best source unit (I-071) | health.json |
| 12 | `corroboration` | `min(1, (distinct source_ids - 1) / 2)` | `sources` |
| 13 | `field_trust` | `curated → 1, ticketmaster → 0.9, seatgeek → 0.8, else 0.6`. Mirrors `resolve.FIELD_TRUST` | `sources` |
| 14 | `price_fit` | free → 1. Unknown → 0.5. Budget `free`: paid → 0. Budget `cheap`: `p ≤ 30 ? 1 : exp(-(p - 30) / 30)`. Budget `any`: `1 - min(1, p / 300) × 0.5` | `price` |
| 15 | `distance_fit` | `exp(-km / 4)`. Unknown location or no neighborhood → 0.5 | `location` |
| 16 | `time_fit` | `slot ∈ profile.times ? 1 : 0`. With no profile, use the newcomer prior: weeknight 0.8, weekend 1.0, daytime 0.35 | `start` |
| 17 | `crowd_fit` | from `attendance.mid` m: `m ≤ 250 ? 1 : m ≤ 5000 ? 1 - 0.6 × log10(m / 250) / log10(20) : 0.4`, blended with 0.5 by `1 - attendance.confidence` | `attendance` |
| 18 | `established_venue` | `venue_id` has a curated capacity → 1, else 0 | venues |
| 19 | `scarcity` | `selling_fast ∨ availability ∈ {few_left, limited} ∨ spots_left / spots_total ≤ 0.2 ? 1 : 0` | `tickets` |
| 20 | `weather_fit` | outdoor only: `precip ≥ 60 → 0`, `< 20 ∧ clear → 1`, else 0.6. Indoor → 0.6 | `weather` |
| 21 | `interest` | exact taxonomy pick → 1, family pick → 0.7, no picks → 0.5, has picks but no match → 0.15 | profile |
| 22 | `goal_fit` | `max` over goals: family ∈ goal families → goal weight / 0.55. `meet_people` → `social` | profile |
| 23 | `category_prior` | newcomer prior for the family (table below) | taxonomy |
| 24 | `affinity` | on-device learned score in [0, 1], 0.5 = unknown (section 2) | localStorage |
| 25 | `p_stale` (penalty) | `stale ? 1 : clamp((hoursSince(last_checked) - SLA) / SLA, 0, 1)` | `stale`, `last_checked` |
| 26 | `p_low_quality` (penalty) | spam/low-information score from section 4, in [0, 1] | `rank.flags` |
| 27 | `p_kids_mismatch` (penalty) | `tags ∋ kids_teens ∧ ¬profile wants family ? 1 : 0` | tags |
| 28 | `p_campus` (penalty) | `tags ∋ campus ? 1 : 0` | tags |
| 29 | `p_low_confidence` (penalty) | `1 - min(provenance.start.confidence, provenance.location.confidence)` | `provenance` |

**Newcomer category prior** (`category_prior`, feature 23). This is a judgment call encoding "what helps you build a life in a new city". Put it in `config/taxonomy.yaml` as `newcomer_prior` per family so it's config, not code:

| family | prior | | family | prior |
|---|---|---|---|---|
| sports_league | 0.9 | | community | 0.65 |
| trivia_games | 0.85 | | music | 0.6 |
| volunteer | 0.8 | | food_drink | 0.6 |
| fitness | 0.75 | | arts | 0.55 |
| niche | 0.7 | | sports_watch | 0.5 |
| nightlife | 0.7 | | outdoors | 0.6 |
| learning | 0.7 | | family / other | 0.3 / 0.3 |

### 1D. Scoring

**Transparent linear model.** `score(e) = Σ_i w_i × f_i(e)`, where `w_i > 0` for signals and `< 0` for penalties. Default weights (v2.0):

| feature | w | | feature | w |
|---|---|---|---|---|
| interest | 1.20 | | completeness | 0.40 |
| goal_fit | 0.60 | | desc_info | 0.15 |
| social | 0.80 | | source_reliability | 0.20 |
| category_prior | 0.50 | | corroboration | 0.10 |
| affinity | 0.60 (×0 until ≥ 5 signals) | | field_trust | 0.10 |
| timeliness | 0.50 | | crowd_fit | 0.20 |
| deadline_urgency | 0.45 | | established_venue | 0.10 |
| early_bird | 0.15 | | scarcity | 0.15 |
| time_fit | 0.70 | | weather_fit | 0.15 |
| price_fit | 0.60 | | novelty | 0.20 |
| distance_fit | 0.40 | | recurring | 0.20 |
| solo | 0.30 | | beginner | 0.15 |
| **p_kids_mismatch** | **−1.50** | | **p_low_quality** | **−1.00** |
| **p_stale** | **−0.40** | | **p_campus** | **−0.35** |
| **p_low_confidence** | **−0.30** | | | |

Keep a `contrib[i] = w_i × (f_i - baseline_i)` vector. The baseline is the value a "typical neutral" event gets (0.5 for neutral-defaulting features, 0 for the others). Ranking uses `score`. Explanations use `contrib`, so "price unknown" (0.5) never produces a "because of price" reason.

**Why linear.** It explains itself exactly: each reason is literally a term of the sum. It's monotone and auditable, and it's hard to overfit with tiny judgment sets. The explainable-recommendation survey [Zhang & Chen 2020] puts this "model-intrinsic" explainability at the honest end of the spectrum. Post-hoc explanations of black-box models can mislead users [Tintarev & Masthoff 2007; Zhang & Chen 2020].

**Optional learned weights (offline, never from user data).** Fit `w` on the hand-labeled judgment sets (section 3) with coordinate ascent that maximizes mean NDCG@10 across cities and personas [Metzler & Croft 2007, "Linear feature-based models for IR"; RankLib's CoordinateAscent]. Constraints:
- Signs are fixed (penalties stay negative). Each weight stays within ×0.5 to ×2 of its default.
- Leave-one-city-out cross-validation: weights must not raise NDCG in one city by tanking another.
- Learned weights ship as `web/src/lib/rank/weights.v2_1.json`, reviewed like code. The defaults stay as the fallback.

**Normalization for diversify/plan.** Before MMR, min-max the scores within the candidate pool: `rel(e) = (s - s_min) / (s_max - s_min + ε)`. This makes λ comparable across pools. The plan's "score > 0.2" cutoff becomes `rel ≥ 0.25` and `p_low_quality < 0.5`.

### 1E. Diversity re-rank (MMR + hard caps)

**MMR** [Carbonell & Goldstein 1998] greedily picks
`argmax_{i ∉ S} [ λ × rel(i) − (1 − λ) × max_{j ∈ S} sim(i, j) ]`.

**Similarity** over our schema, in [0, 1]:

```ts
sim(a, b) =
  a.series_id && a.series_id === b.series_id ? 1 :
  a.rank?.group_id && a.rank.group_id === b.rank?.group_id ? 1 :
  clamp(
    0.35 * (family(a) === family(b)) +
    0.15 * (a.category === b.category) +          // same subcategory
    0.20 * (a.venue_id && a.venue_id === b.venue_id) +
    0.10 * (src(a) === src(b)) +
    0.10 * (localDate(a) === localDate(b)) +
    0.10 * (a.organizer && norm(a.organizer) === norm(b.organizer))
  , 0, 1)
```

**λ defaults:**

| Surface | λ | Why |
|---|---|---|
| Highlights (no profile, 6 to 10 cards) | 0.60 | Front page: breadth is the product |
| For You with ≤ 1 interest | 0.65 | |
| For You with ≥ 2 interests | 0.75 | Interests already diversify |
| Search / filtered category view | 0.90 | The user asked for this family. Only de-clump venue and day |
| Similar this week | 0.85 | Same family by design, vary venue and day |
| Plan (per week, 3 picks) | 0.55 | Plus the existing no-overlap and one-per-series constraints |

**Hard caps** applied inside the same greedy loop (skip a candidate that violates one, and relax a cap only if the pool runs out):
- ≤ 1 per `series_id` and `group_id`.
- ≤ 2 per source in the top 10 (≤ 1 in Highlights' top 6). *Superseded by I-160 (§7.7):* ≤ 2 per organizer × venue and ≤ 3 per source in For You's top 10, a soft ≤ 3 per family, and ≤ 2 per source in Highlights.
- ≤ 1 library-hosted event in Highlights.
- ≥ 3 families in the top 10 (once 7 slots are filled, the remaining slots must add a new family if any candidate with `rel ≥ 0.3` exists).
- ≤ 3 per local day in Highlights.

**Alternatives considered.**
- *xQuAD* [Santos, Macdonald & Ounis 2010] covers explicit aspects in proportion to a prior: aspects = families, `P(a)` = the normalized `category_prior`. It's a good fit if we want "proportional to newcomer prior" coverage rather than "spread out". It's one function swap behind the same interface. Pick xQuAD for Highlights if judgment sets show MMR under-represents leagues and volunteering.
- *DPP* [Kulesza & Taskar 2012] with fast greedy MAP [Chen, Zhang & Zhou 2018], as used at YouTube [Wilhelm et al. 2018]. More principled set diversity, but the kernel needs embeddings and its explanations are opaque. Overkill at about 1k items with hand-built similarity. Rejected for now.
- Topic diversification [Ziegler et al. 2005] is the original "users prefer diversified lists even at some accuracy cost" result. It supports a λ well below 1.

### 1F. Explanation generation

1. Sort the positive `contrib` terms in descending order. Keep those ≥ 0.12, at most 3. If any penalty term is ≤ −0.2, add **one caveat**.
2. Each feature has a **template keyed by provenance method**, so wording never overclaims:

| Feature | reported / curated | estimated / derived / extracted |
|---|---|---|
| scarcity | "Ticketmaster flags few tickets left" / "17 of 20 spots taken (library)" | "Resale listings are down 38% in 2 days (listings aren't seats)" |
| crowd_fit | "Organizer expects ~120 people" | "Probably a small crowd (~60–200, estimate)" |
| deadline_urgency | "Registration closes Fri, Oct 24" | derived: "Registration required, no close date published" (**never a countdown**) |
| novelty | "Just listed (new on GetOffTheCouch this week)". Never "new event": `is_new` means newly *seen* | |
| social | first `social.reasons` entry ("Trivia: teams welcome strangers") | |
| source_reliability / corroboration | "Listed by 2 sources" | |
| time_fit / distance_fit | "Saturday afternoon, one of your times" / "1.4 km from Uptown" | |
| affinity | "You've saved 3 trivia nights" (counts, never inferred traits) | |
| exploration slot | "Something different: you haven't seen many volunteering picks" | |
| p_stale (caveat) | "Last confirmed 3 days ago, so check the link" | |

3. **Honesty rules** (unit-tested):
   - No superlatives ("best", "most popular", "hottest") unless backed by a reported number.
   - Estimates always carry "~" or "probably" plus the band.
   - "Free" only when `price.is_free` (reported).
   - Never invent a reason that has no matching `contrib` term.
   - Negative signals are phrased as facts, not judgments ("Aimed at kids & teens", not "Not for you").

---

## 2. Cold start and on-device personalization

### 2.1 A brand-new user (no profile, no history)

Use **population-free defaults**, since we have no other users by design:
- `interest = 0.5` for everything, `affinity` weight 0, `category_prior` on, `time_fit` from the newcomer slot prior (weekend 1.0, weeknight 0.8, daytime 0.35), `distance_fit = 0.5`, `price_fit` with budget `any`.
- **City defaults** from `config/cities/<slug>.yaml` → optional `ranking: { family_boost: {sports_league: 0.1}, lambda: 0.6 }` for local character (Austin music, Minneapolis leagues). They must be documented with a reason in the YAML.
- **One-screen onboarding** (already partly in `vibes.ts`): 3 taps (goals, budget, times) beat a long questionnaire. Eliciting a few explicit preferences is the standard cold-start fix in the literature [Rashid et al. 2002, "Getting to know you"; Schein et al. 2002]. Skip should be one tap, with no penalty for skipping.

### 2.2 Learning from saves, clicks and dismisses (localStorage only)

**Signals and implicit weights.** Implicit feedback is a confidence, not a rating [Hu, Koren & Volinsky 2008]:

| Action | Δα (positive) | Δβ (negative) | Notes |
|---|---|---|---|
| Add to calendar / ICS | 3 | 0 | strongest intent |
| Save | 2 | 0 | |
| Open card ≥ 5 s | 0.5 | 0 | clicks are noisy and position-biased [Joachims et al. 2005]; keep them small |
| Click outbound ticket/registration link | 1.5 | 0 | |
| "Not for me" dismiss | 0 | 2 | ask the optional "why": topic / too far / price / time |
| Unsave | 0 | 1 | |
| Impression without interaction | 0 | 0 | **ignored**, because position bias makes skips meaningless at our volume |

**Keys** each event updates: `fam:<family>`, `cat:<category>`, `tag:<tag>` (only for a small vocabulary: solo_friendly, free, outdoor, nightlife, beginner_friendly, recurring, lgbtq, sober_friendly), `venue:<venue_id>` and `slot:<weekday×daypart>`. **Never** source ids: users don't think in sources.

**Beta-Bernoulli with time decay.** Bayesian smoothing like this is what keeps one save from swinging the ranking. It's the same reasoning as Wilson / Bayesian average ratings [Miller 2009].

```ts
// state per key: { a, b, t }  prior a0 = b0 = 2 (mean 0.5, worth "4 pseudo-events")
const HALF_LIFE_D = 21;
function decay(s, now) {
  const g = Math.pow(0.5, (now - s.t) / (HALF_LIFE_D * 86400e3));
  // decay evidence toward the prior, not toward zero
  return { a: A0 + (s.a - A0) * g, b: B0 + (s.b - B0) * g, t: now };
}
function update(s, dA, dB, now) { const d = decay(s, now); return { a: d.a + dA, b: d.b + dB, t: now }; }
const mean = (s) => s.a / (s.a + s.b);

// event affinity in [0,1]: weighted average of key means, by key specificity
function affinity(e, store, now) {
  const parts = [[`cat:${e.category}`, 0.4], [`fam:${family(e.category)}`, 0.3],
                 [`venue:${e.venue_id}`, 0.1], [`slot:${slotKey(e)}`, 0.1],
                 ...e.tags.filter(inVocab).map(t => [`tag:${t}`, 0.1 / e.tags.length])];
  let num = 0, den = 0;
  for (const [k, w] of parts) { const s = store[k]; if (!s) continue;
    const d = decay(s, now), n = d.a + d.b - A0 - B0;            // evidence mass
    const wk = w * Math.min(1, n / 4);                            // trust grows with evidence
    num += wk * mean(d); den += wk; }
  return den ? 0.5 + (num / den - 0.5) * Math.min(1, den / 0.5) : 0.5;
}
```

- The affinity weight (0.60) only switches on after ≥ 5 total signals. Its contribution is capped at ±0.3 (`w × (f − 0.5)`), so it re-orders within relevant items but never overrides `interest` or the kids/quality penalties.
- Storage: `localStorage["gotc:affinity:v1"] = { v: 1, keys: { "fam:music": {a, b, t} }, n }`. Cap at 300 keys, pruning the lowest evidence mass first. Bump `v` on format change and drop old data rather than migrate it.
- Settings shows "What GetOffTheCouch has learned" as a list of keys with plain labels and counts, a per-row ✕, and "Reset everything". Data never leaves the device. No sync and no analytics events carry it.

**Why not federated learning?** FL [McMahan et al. 2017] trains a shared model from on-device gradients. It needs a server, aggregation, and some trust in how updates are handled. The product rule is "nothing is learned from other users", and per-user Beta counts are enough at our scale. Revisit only if we ever want cross-user priors, and then only via an ADR.

### 2.3 Exploration slot (on-device Thompson sampling)

Reserve **one slot in the top 10** (position 4 or 7, never 1) and **one plan pick per 2 weeks** for exploration:

```ts
// families the user has *not* strongly signalled; sample from each family's Beta posterior
const fams = familiesInPool.filter(f => (store[`fam:${f}`]?.b ?? 0) < 6);   // respect strong "no"s
const draw = (f) => betaSample(decay(store[`fam:${f}`] ?? {a:A0, b:B0, t:now}, now));
const pick = argmax(fams, f => draw(f) * (0.5 + 0.5 * prior[f]));            // TS × newcomer prior
const item = bestInFamily(pick, minRel = 0.3);                               // never explore junk
```

Thompson sampling [Thompson 1933; Chapelle & Li 2011] gets more exploration out of uncertain arms automatically, needs no tuning, and runs in a few lines in the browser (Beta via two Gamma draws, seeded per day so the list doesn't reshuffle on every render). Spotify Home uses a bandit framework for the same explore/exploit balance [Spotify 2020]. LinUCB [Li et al. 2010] is the contextual alternative; it isn't worth it without shared data.

### 2.4 Avoiding filter bubbles

The risk is real but modest. Users who consume diverse recommendations narrow less [Nguyen et al. 2014]. The fixes are structural:

1. The exploration slot (2.3).
2. **Family floor.** Any family with ≥ 3 candidates at `rel ≥ 0.3` appears at least once per 14 days of sessions, tracked locally as `lastShown[family]`.
3. Affinity is capped (±0.3) and decays (21-day half-life). A burst of trivia saves fades within a month.
4. The MMR λ stays below 0.8 on personalized surfaces.
5. Dismisses with "why = too far / price / time" update `slot:`/distance/price preferences, **not** the topic key. Disliking a Tuesday doesn't mean disliking music.
6. Beyond-accuracy metrics (ILD, coverage, entropy) are first-class gates in section 3 [Kaminskas & Bridge 2016].

### 2.5 "Why am I seeing this?" UI copy

On each card, a small "Why this?" link opens a popover:

> **Why you're seeing this**
> • You picked *Trivia nights*
> • Tuesday 7 pm, one of your times
> • Easy to show up solo
>
> *Heads-up: last confirmed 3 days ago, so check the link.*
>
> Ranked on your device from your choices and what you've saved. Nothing is sent anywhere. [Adjust preferences] · [Not for me]

For the exploration slot:

> **Something different.** You haven't seen many *volunteering* picks yet, so here's a well-reviewed one. [More like this] · [Less like this]

For a brand-new user:

> **Picked for someone new to Minneapolis.** Social, soon and close to the center. Tell us a bit about you to tune this. [Set preferences]

---

## 3. Offline evaluation without user data

### 3.1 Judgment sets

**Freeze a feed snapshot per city** so that ids are stable for the lifetime of a judgment set:
`tests/fixtures/ranking/<city>/<YYYY-MM-DD>.feed.json` is a trimmed copy of `cities/<slug>.json`. `now` is fixed to the snapshot's `generated_at`.

**Personas** (`tests/fixtures/ranking/personas.json`):

| id | profile |
|---|---|
| `newcomer_default` | no profile (Highlights / For You cold start) |
| `social_25` | meet_people + party, budget cheap, weeknights + weekends, solo |
| `active_30` | stay_active, any budget, weekends + daytime, neighborhood set |
| `culture_free` | culture, budget free, weekends |
| `parent_35` | interests `family`, daytime + weekends (kids content is *relevant* here) |
| `nerd_40` | nerd_out + give_back, weeknights |

**Grades:** 0 = wouldn't show a newcomer (noise, wrong audience, junk). 1 = fine filler. 2 = good pick. 3 = "this is why the site exists" (social, concrete, soon, matches persona).

**Format.** Labels are anchored to ids **and** fingerprints **and** optional rules:

```jsonc
// tests/fixtures/ranking/minneapolis/2026-10-16.judgments.json
{
  "version": 1,
  "city": "minneapolis",
  "snapshot": "2026-10-16.feed.json",
  "now": "2026-10-16T12:00:00-05:00",
  "labeler": "agent:claude + human spot-check",
  "judgments": [
    {
      "persona": "newcomer_default",
      "event_id": "evt_8f2c…",
      "fp": { "title": "trivia night", "venue": "bryant lake bowl", "weekday": 2, "daypart": "evening",
              "category": "trivia_games.trivia", "source": "curated_minneapolis" },
      "grade": 3,
      "rationale": "Weekly, team-friendly, solo ok, 7pm Tue, $0"
    }
  ],
  "rules": [
    { "persona": "*", "when": { "tags_any": ["kids_teens"] }, "except_persona": ["parent_35"], "grade": 0,
      "rationale": "kids content for adults" },
    { "persona": "*", "when": { "title_re": "(?i)\\b(closed|rental|staff only|private event)\\b" }, "grade": 0 }
  ]
}
```

**Resolving a label when ids disappear** (a later snapshot, or a sticky-id break):
1. Exact `event_id` match.
2. Else a fingerprint match: same normalized venue, same weekday and daypart, and title char-3-gram Jaccard ≥ 0.8. The grade carries over with `matched_by: "fp"`.
3. Else the first matching `rule`.
4. Else **unjudged**. Unjudged items count as grade 0 for NDCG (conservative), and the report prints the **judged@10** rate. If judged@10 < 0.8, the eval fails with "relabel needed", not "quality dropped". This is standard handling of incomplete judgments [Buckley & Voorhees 2004 discuss the bias].

**How to build a set** (about 1 hour per city, agent-assisted):
1. `npm run eval:pool -- --city minneapolis`. Pool the top 30 from v1, from v2 and from three random-weight variants per persona, then dedup. Pooling is the TREC method.
2. The agent proposes grades with a rationale, based on title, venue, time, price and tags. A human corrects at least 20%. Record `labeler`.
3. Commit the snapshot and judgments together. Never relabel by looking at a ranker's output order.

### 3.2 Metrics (per city × persona, then macro-averaged)

| Metric | Definition | Gate |
|---|---|---|
| **NDCG@10** | `DCG = Σ_{r=1}^{10} (2^{g_r} − 1) / log2(r + 1)`, normalized by the ideal ordering of the judged pool [Järvelin & Kekäläinen 2002] | ≥ baseline − 0.02 |
| **P@10 (g ≥ 2)** | fraction of the top 10 with grade ≥ 2 | ≥ baseline − 0.05 |
| **ILD@10** | `mean_{i<j} (1 − sim(i, j))` with the 1E `sim` [Ziegler 2005] | ≥ 0.55 |
| **Family entropy@10** | `H = −Σ p_f log2 p_f`, normalized by `log2(min(10, #families in pool))` | ≥ 0.7 |
| **Coverage** | distinct families in the union of all personas' top 10s ÷ families in the pool | ≥ 0.6 |
| **Freshness** | median hours-to-start in the top 10, and share of `is_new` | reported, ≤ 120 h |
| **Staleness rate@10** | share of `stale` in the top 10 | ≤ 0.1 |
| **Junk@10** | share with grade 0 | ≤ 0.1 |
| **judged@10** | share of the top 10 that resolved to a label | ≥ 0.8, else "relabel" |

Store the current numbers in `tests/fixtures/ranking/baseline.json`. Update them only in a commit that says why (for example, "I-1xx: new weights, NDCG +0.04").

### 3.3 Golden-rule tests (hard fail, no thresholds)

These run against every snapshot and every persona, and against synthetic adversarial feeds:
1. Nothing cancelled, postponed, past, or sold out without resale in any surface.
2. No `kids_teens` in the top 10 unless the persona has a `family` interest.
3. ≤ 2 per organizer × venue and ≤ 3 per source in the top 10 (≤ 2 per source in Highlights; was ≤ 2 per source everywhere before I-160, §7.7). ≤ 1 per series or multi-site group. ≤ 1 library in Highlights.
4. ≥ 3 families in the top 10 whenever the pool has ≥ 3 families at `rel ≥ 0.3`.
5. No `p_low_quality ≥ 0.7` item in the top 10.
6. A derived deadline never renders a countdown string. Every reason maps to a nonzero `contrib`. No reason contains a superlative without a reported number.
7. Determinism: the same input and `now` produce the same output (the exploration RNG is seeded by `date + city`).
8. Monotonicity spot checks: making an event free never lowers its rank for `budget: free`. Setting `stale: true` never raises it.

---

## 4. Anti-spam and quality

Calendars from libraries, parks and venues aren't spammy the way UGC is. Their noise is administrative: room bookings, closures, staff meetings, daily open hours. The Python pipeline computes these as `rank.flags[]` plus a `rank.quality` score. The browser just weights them.

**Duplicate-ish listings**
- Cross-source: handled by `resolve.py`.
- Same-source near-duplicates and multi-site groups: section 1B. At our scale (≤ 2k per city), an O(n²) Jaccard pass per (day, venue) block is fine. MinHash [Broder 1997] or SimHash [Charikar 2002; Manku et al. 2007] only become worth it beyond about 50k items.
- Title-variant series ("Trivia Night", "Trivia Night – Halloween Edition"): put the same `series_id` candidate on titles that strip parenthetical and edition suffixes, at the same venue and weekday.

**Recurring noise.** Flag `noise_recurring` when a series has more than 12 occurrences per 30 days **and** the family isn't `trivia_games`, `fitness` or `sports_league` ("Open computer lab", "Museum open hours", "Lap swim"). Score 0.6. A daily item gets shown once as a habit, at most.

**Low-information and administrative events** (each flag adds to `p_low_quality`, capped at 1):

| Flag | Rule | +score |
|---|---|---|
| `admin` | title matches `/\b(closed|closure|rental|reserved|private (event|party)|staff only|members only|board meeting|committee|office hours|study room|test event)\b/i` | 1.0 (hard noise if ≥ 2 hits) |
| `generic_title` | normalized title ≤ 2 tokens and in a generic list (`event`, `meeting`, `program`, `open play`, `tbd`, `class`) | 0.4 |
| `all_caps` | uppercase letters / letters > 0.6 and length > 12 | 0.2 |
| `shouty` | ≥ 3 `!`, or emoji or ★ runs ≥ 3 | 0.2 |
| `no_info` | no description, no price, no url | 0.3 |
| `no_place` | no venue and no lat/lon (and not online) | 0.4 |
| `promo` | `/use code|% off|promo|limited time offer|buy now/i` in the title | 0.3 |
| `long_span` | `end − start > 3 d` and not a season or exhibit with a venue | 0.3 |
| `kids_detect` | regex for `storytime|toddler|ages \d+\s*[-–]\s*\d+|grades? (k|\d)|teen (night|zone)|baby|preschool` → add the `kids_teens` tag in enrich (feeds penalty 27) | — |
| `internal_campus` | campus venue plus `/students only|faculty|staff/` → `campus` tag | — |

`rank.quality = completeness × (1 − p_low_quality)`. Sort duplicate-group representatives by it.

**Feedback loop.** `make doctor` reports the share of each source's events flagged `admin` or `noise_recurring`. Above 30%, it suggests an adapter-level reject rule, so the noise gets fixed upstream.

---

## 5. Implementation plan

### 5.1 Precompute in Python vs compute in the browser

**Python (`gotc/pipeline/rankprep.py`, called from `build.py` after enrich).** Anything profile-independent that's expensive or needs data the browser doesn't load (descriptions, run history):
- `rank.fingerprint`, `rank.group_id`, `rank.group_size` (multi-site and near-duplicates)
- `rank.desc_len`, because `summary` is split into `details.json`
- `rank.flags[]`, `rank.p_low_quality`, `rank.completeness`, `rank.quality`
- `rank.src_reliability` (from `gotc.health.reliability`, best member unit)
- the kids/campus tag detection improvements (in `enrich.py`)
- `newcomer_prior` added to `taxonomy.yaml`, exported into the feed's category labels

Schema: add `class RankHints(Strict)` and `Event.rank: RankHints | None = None`. Bump to **1.5.0** (additive, minor), then `make schema`. Contract tests cover the rest.

**Browser (`web/src/lib/rank/`).** Everything that depends on `now`, the profile or local history: timeliness, deadline urgency, time/price/distance fit, weather fit, affinity, MMR, exploration, explanations.

### 5.2 TypeScript module boundaries (all pure, except `affinityStore.ts`)

```
web/src/lib/rank/
  types.ts         RankContext {now, city, profile, labels, neighborhoods, affinity, surface}, Features, Contrib
  candidates.ts    candidates(events, ctx): Event[]                        — 1A
  collapse.ts      collapse(events, ctx): Event[]                          — 1B (series, group, fp)
  features.ts      extract(e, ctx): Features  (one small fn per feature, exported for tests)
  weights.ts       DEFAULT_WEIGHTS, BASELINES, loadLearned()               — 1D
  score.ts         score(f, w): {score, contrib}; normalize(pool)
  similarity.ts    sim(a, b)
  diversify.ts     mmr(scored, {lambda, k, caps}); xquad() alternative     — 1E
  explain.ts       reasons(e, contrib, f): Reason[]; TEMPLATES; honesty guards — 1F
  affinity.ts      decay, update, affinity(e, state, now) (pure)           — 2.2
  explore.ts       seededRng(seed), betaSample, pickExploration            — 2.3
  affinityStore.ts localStorage I/O + event hooks (the only side effects)
  rules.ts         golden-rule predicates, shared by tests and a dev-only runtime assert
  index.ts         rankV2(events, ctx): Scored[]; highlightsV2, forYouV2, planV2, similarV2
```

`recommend.ts` keeps its exported API (`rank`, `highlights`, `buildPlan`, `similar`, `scoreEvent`) and delegates to `rank/index.ts` behind a flag: `localStorage["gotc:ranker"] = "v1" | "v2"`, with v2 as the default only after the gates pass. `Scored` keeps the shape `{event, score, reasons}`, and v2 adds `features?` and `contrib?` for the debug panel.

### 5.3 Test strategy

1. **Unit (vitest, `web/tests/rank/*.test.ts`).** One table-driven test per feature function (edge cases: unknown price → 0.5, derived deadline halves urgency). Plus `sim` symmetry and bounds, MMR (λ = 1 is pure ranking; λ = 0 maximizes spread), affinity decay toward the prior, a seeded Beta sampler (mean within ±0.02 over 10k draws), and explanation honesty guards.
2. **Property tests** (`fast-check`, dev dependency). Determinism, the monotonicity rules from 3.3.8, and "caps never violated" on random feeds.
3. **Golden rules** (`rank/golden.test.ts`) over every frozen snapshot and persona.
4. **Offline eval** (`rank/eval.test.ts` + `npm run eval:rank`). Compute section 3.2 metrics, compare against `baseline.json`, and fail on regression. It prints a v1-vs-v2 table, so the first PR is a pure comparison.
5. **Pipeline (pytest).** `tests/unit/test_rankprep.py` for flags, fingerprints and groups, with fixture events taken from real noisy titles (record them; never invent "realistic" ones).
6. **Visual check** per `CLAUDE.md` rule 7: Playwright screenshot of Highlights and For You for two cities, plus a diary entry.

### 5.4 Rollout order

1. Python `rankprep` + schema 1.5.0 (flags, groups, desc_len, reliability), no UI change.
2. `rank/` features, score and explain, with v1-equivalent weights to prove parity (NDCG within 0.01 of v1).
3. Judgment sets for 3 cities (Minneapolis, NYC, Austin: three different source mixes). Baseline v1.
4. v2 weights + MMR + caps → must beat v1 on NDCG@10 and ILD.
5. Affinity + "What we've learned" settings + "Why this?" popover.
6. Exploration slot, family floor.
7. Optional: learned weights via coordinate ascent (ADR).

---

## 6. Idea candidates

`title | area | value 1-5 | effort 1-5 | why`

1. Precompute RankHints (flags, fingerprint, multi-site groups, desc_len, reliability) in the pipeline, schema 1.5.0 | pipeline | 5 | 2 | Unblocks every quality feature. `summary` isn't in the card feed, so the browser can't compute description signals
2. Normalized linear scorer with contrib-based explanations (`rank/score.ts` + `explain.ts`) | web/ranking | 5 | 3 | Fixes the unbounded-sum drift in v1, and reasons become literally the score terms
3. MMR re-rank with schema-aware similarity plus hard caps, shared by Highlights, For You and the plan | web/ranking | 4 | 2 | Replaces three ad-hoc greedy loops with one tested function. A library source holding 31% of the feed can't flood lists
4. Frozen-snapshot judgment sets (3 cities × 6 personas) with id + fingerprint + rule labels | eval | 5 | 3 | First objective measure of ranking quality. Fingerprints survive id churn
5. `npm run eval:rank` regression gate in `make check` (NDCG@10, ILD, entropy, junk@10, judged@10) | eval/CI | 4 | 2 | Ranking changes become falsifiable instead of vibes
6. Golden-rule test suite (no kids-for-adults, no cancelled/past, ≤ 2 per source, ≥ 3 families, honest wording) | tests | 5 | 1 | Cheap, catches the worst embarrassments, runs on every snapshot
7. Administrative-noise detector (closures, rentals, staff-only, daily open hours) with a doctor report per source | pipeline/quality | 4 | 2 | Library and park calendars are the main noise. Fixing it upstream helps every surface
8. On-device Beta affinity from saves, calendar adds and dismisses, with 21-day decay and a "What we've learned" panel with reset | web/personalization | 4 | 3 | Personalization without sending anything anywhere, which keeps the privacy promise
9. Thompson-sampling exploration slot plus a 14-day family floor | web/personalization | 3 | 2 | Avoids the filter bubble, and newcomers don't yet know what they like
10. "Why this?" popover with provenance-aware templates and a "Not for me (why?)" dismiss | web/UX | 4 | 2 | Builds trust, and gives cleaner negative signals (topic vs time vs price)

---

## 7. Results (2026-10-16)

### 7.1 What was built

| Piece | Where |
|---|---|
| Pipeline hints, schema 1.5.0 (`Event.rank`: `fp`, `group`/`group_n`, `desc_len`, `flags`, `lowq`, `complete`, `quality`, `src_rel`) | `gotc/pipeline/rankprep.py`, called from `export.py` before summaries are cut; `tests/unit/test_rankprep.py` uses real titles |
| Candidates → collapse → 29 features → linear score with contributions → MMR + hard caps → explanations | `web/src/lib/rank/*.ts` (pure) |
| On-device affinity (Beta, 21-day half-life, ±0.3 cap, on after 5 signals), dismiss, exploration slot, family floor, "Why am I seeing this?" (`whyThis`, exported as `whySeeingThis`) | `rank/affinity.ts`, `rank/affinityStore.ts`, `rank/explore.ts`, `rank/index.ts` |
| Same public API (`rank`, `scoreEvent`, `buildPlan`, `highlights`, `similar`) plus `forYou`, `whySeeingThis`, `dismiss`, `recordSignal`, `learnedSummary`, `resetAffinity` | `web/src/lib/recommend.ts` |
| Offline eval: 5 frozen real snapshots, 6 personas, hand labels, gates; golden-rule hard fails | `web/tests/rank/`, `npm run eval:rank` (part of `make check`, ~2 s) |

### 7.2 Evaluation set

- **Snapshots.** Real exports from 2026-10-16T20:53Z for Minneapolis, NYC, Chicago, Austin and Seattle. The window is `now → now + 7 days`, plus league seasons whose registration closes within 30 days: 2,818 events in total. Hints are recomputed by `scripts/rank_snapshot.py`. The files are gzipped, 45–150 KB each.
- **Pooling.** For each city × persona, the union of v1's top 20, v2's top 20 (before and after diversification) and the top 10 of three random-weight variants: 560 events.
- **Labels.** Each event was graded 0–3 for each of the 6 personas (3,360 grades), by reading its title, venue, day and time, price and description. Pools were sorted by id while labeling, never by a ranker's order. Rationales are in `fixtures/<city>.judgments.json`.
- **Labeler.** `agent:claude`, with **no human spot-check yet**. §3.1 asks a human to correct ≥ 20%; that's still owed.
- **Coverage.** judged@10 is 0.99–1.00, so unjudged items barely affect the numbers.

### 7.3 Numbers (macro over 5 cities × 6 personas, For You top 10)

"v2 (10-16)" is the first shipped v2 (≤ 2 per source). "v2 + I-160" is the current ranker: caps by organizer × venue with a looser per-source backstop (§7.7).

| Metric | v1 | v2 (10-16) | v2 + I-160 | Gate |
|---|---|---|---|---|
| NDCG@10 | **0.51** | 0.46 | 0.48 | ≥ stored v2 − 0.02 (regression gate; see 7.5) |
| NDCG@10 vs the best *caps-compliant* list | 0.60 → 0.56¹ | 0.55 | 0.52¹ | reported |
| P@10 (grade ≥ 2) | **0.53** | 0.42 | 0.45 | ≥ stored v2 − 0.05 |
| ILD@10 | 0.61 | **0.90** | **0.90** | ≥ 0.55 |
| Family entropy@10 | 0.33 | **0.73** | **0.73** | ≥ 0.7 |
| Coverage (families in all personas' top 10s ÷ pool) | 0.63 | **0.83** | **0.83** | ≥ 0.6 |
| Median hours to start | 102 | **50** | 57 | ≤ 120 |
| Stale@10 | 0 | 0 | 0 | ≤ 0.1 |
| Junk@10, no-profile persona | 0.14 | **0.04** | 0.06 | ≤ 0.1 |
| Junk@10, all personas (a 0 here often means "not this persona") | 0.28 | 0.28 | 0.27 | reported |
| judged@10 | 1.00 | 0.99 | 0.98 | ≥ 0.8 |

¹ The caps-compliant ideal follows the shipped caps, so I-160 changed its denominator (the looser caps admit a better ideal list); v1's number under the new ideal is 0.56.

**Highlights (the cold-start front page, top 6, newcomer persona), NDCG@6:**

| City | v1 | v2 |
|---|---|---|
| Minneapolis | 0.73 | 0.76 |
| NYC | 0.64 | 0.75 |
| Chicago | 0.16 | 0.61 |
| Austin | 0.35 | 0.67 |
| Seattle | 0.44 | 0.39 |
| **Mean** | **0.46** | **0.64** |

Highlights junk falls from 0.10 to 0. I-160 leaves every Highlights number unchanged (it keeps ≤ 2 per source in the top 6).

### 7.4 What costs relevance: ablation (`npm run eval:ablate`)

| Variant | NDCG@10 | ILD@10 | Junk@10 |
|---|---|---|---|
| v1 | 0.510 | 0.61 | 0.28 |
| **v2 as shipped** (λ 0.9, caps, exploration slot) | 0.458 | 0.90 | 0.28 |
| without the exploration slot | 0.470 | 0.89 | 0.27 |
| also λ = 1 (no MMR) | 0.471 | 0.85 | 0.27 |
| also without the ≤ 2-per-source cap | 0.533 | 0.75 | 0.19 |
| pure v2 score (no caps, no MMR, no exploration) | **0.560** | 0.61 | 0.16 |

**Reading it.**
- The v2 score orders events better than v1: 0.56 vs 0.51 at equal (zero) diversity.
- Nearly all of the For You NDCG loss comes from the **≤ 2-per-source hard cap** (−0.075). The exploration slot costs another −0.012.
- Some feeds put every relevant item for a persona in one source: Austin trivia (`challenge_trivia_austin`), Minneapolis kids programs (`hclib_events`), NYC leagues (`volo_nyc`) and Seattle bar games (`visit_ballard_events`). In those, v1's top 10 was often ten near-identical items, which NDCG rewards and a newcomer wouldn't.
- The cap is a golden rule (§3.3.3), so it stays. *I-160 (§7.7) reworked it into a cap on organizer × venue, which recovers part of the loss.*

**The rollout gate in §5.4.4 ("v2 must beat v1 on NDCG@10 and ILD") is not met for For You.** It is met for Highlights (+0.18 NDCG@6), and ILD, entropy, coverage, freshness and junk improve everywhere.

v2 is on by default because the task asked for it, Highlights is the surface people see, and nothing in the UI renders For You yet. Integrators: flip `RANKER_V2` if you disagree.

### 7.5 Deviations from §1–§4 (all made after looking at the eval, so the numbers above are in-sample)

1. **For You λ is 0.9, not 0.65/0.75.**
   - Why: `rel` is min-max over the whole pool, so the top candidates differ by hundredths and a low λ lets similarity dominate.
   - The sweep: NDCG rises from 0.41 at λ 0.65 to 0.46 at 0.9 and 0.47 at 1.0. Leave-one-city-out picks 0.9–1.0 in every fold.
   - 0.9 keeps a little venue/day de-clumping.
2. **`interest` family pick is 0.85, not 0.7.** At 0.7, a parent who picked "family" still got mostly adult-social picks.
3. **`category_prior` counts half once interests are set.** It shrinks toward its 0.5 baseline, because it's a cold-start device.
4. **`timeliness` baseline is 0.5, not 0.** Otherwise "Coming up Saturday" was the top reason on nearly every card.
5. **`weather_fit` uses any event with a forecast.** The pipeline only fetches forecasts for outdoor events.
6. **`normalize` keeps a minimum span of 1.5 score points.** In tiny pools, plain min-max turned a 0.1-point gap into rel 0 vs 1.
7. **Exploration and floor picks need `rel ≥ 0.5` and `lowq < 0.3`, not `rel ≥ 0.3`.** The family floor only fires once there are 14 days of history, because on a first visit "you haven't seen X lately" would be false.
8. **Two new pipeline flags,** found while labeling:
   - `service_desk` (0.6): tech help, legal clinics, ESL/ELL classes, enrollment desks.
   - `audience_specific` (0.5): "high school students", "first responders", "must speak French", "Russian-speaking", adaptive programs.
   - These aren't low quality; they just aren't picks for a general list.
   - `noise_recurring` exempts `volunteer` because food-pantry shifts are habits.
   - `committee` only counts in meeting phrases, since "International Rescue Committee's Annual Benefit Dinner" was a false hit.
9. **Eval gates.**
   - NDCG and P@10 gate against the stored v2 numbers (`fixtures/baseline.json`), not against v1 (see 7.4).
   - Junk@10 gates on the no-profile persona, because a persona's 0 often means "not my thing".
   - Highlights NDCG@6 must stay ≥ v1 − 0.02.
10. **`newcomer_prior` lives in `rank/weights.ts`, not `config/taxonomy.yaml`.** This kept the change free of index.json plumbing (I-164).

### 7.6 Caveats and next steps

- **In-sample.** The new flags, the λ choice and the interest/prior tweaks were all chosen after seeing these labels; only λ was cross-validated. The next snapshot (a new date) is the honest test. Labels carry fingerprints, so they survive id churn.
- **One labeler, no human check.** Persona grades encode one reading of "weeknights", "free" or "nerd out".
- **The eval personas have goals but no interests** (except `parent_35`), while the Plan UI requires interests. Their For You numbers lean on `goal_fit` and social signals.
- **The live feeds don't carry hints yet.** Until the next export, `rank` is absent and v2 falls back to neutral values for completeness, quality and reliability. Hard-noise and dup collapse only kick in after the pipeline runs with schema 1.5.0.
- **`src_rel` is null everywhere today,** because reliability needs ≥ 3 runs per unit in 30 days.
- **Category mistakes in the data hurt more than any weight.** Examples: "MNsure Help" filed as a hike, "Indigo Girls" as a festival, "Drop-in Tech Help" as volunteering. Fixing classification upstream is the cheapest relevance win left.

### 7.7 I-160: cap by organizer × venue, not by listing source (2026-10-27)

**Problem.** §7.4 showed that the ≤ 2-per-source cap cost For You 0.075 NDCG@10. Aggregator feeds list many independent things: library branches, parks, Volo's fields, Challenge Trivia's 13 bars, HandsOn's and NYC Service's charities, Earshot Jazz's 42 venues. Capping them as if each feed were one venue throws away good picks.

**What the snapshots say about the key.**
- `organizer` is set on all but 36 of 2,818 events (counting placeholders like "--" as missing). For single-owner aggregators it's the feed owner on every row ("Hennepin County Library", "Volo Sports", "Challenge Entertainment", "NYC Parks"). An *organizer-first* key (organizer, else venue, else source) is therefore the source cap again for exactly the feeds I-160 is about. In-sample it was the worst key: 0.40–0.48 NDCG@10, depending on the caps.
- `venue_id` or a venue name is present on 83% of rows. Most of the rest are whole feeds with no venue (HandsOn, NYC permits, Dakota), where organizer carries the signal instead. No event lacks both, so the source fallback never fires on these snapshots.
- So the key is **organizer × venue** (`diversify.ts capKey`): normalized organizer plus `venue_id` (else the venue name, ignoring placeless names like "Online"). The listing source is used only when both are missing. "Venue first" scored within 0.003 of it in-sample, but it ignores organizer, so it would merge HandsOn's charities into one key.
- **The `group` hint** (same program, same day, 2+ venues) already allows only 1 per group. That's why a key per branch can't let one storytime fill the list. Series and fingerprints stay at ≤ 1 too.

**Caps** (`weights.ts CAPS`, per 10 slots):
- ≤ 2 per organizer × venue. This is hard, and a one-room venue feed has one key, so it stays at 2 as before.
- ≤ 3 per listing source. A hard backstop so one feed still can't take more than 30%.
- ≤ 3 per family. A *soft* cap, relaxed only if the pool runs out, For You only. In the sweep, every looser-source config without it failed the family-entropy gate (0.60–0.68 against a gate of 0.7). Loosening the source cap mostly lets one family back in, and entropy, not the source cap, was the next binding constraint.
- Highlights keeps ≤ 2 per source in its top 6. Its sweep showed ≤ 0.008 gain from loosening, and Seattle fell.

**Tuning discipline** (`npm run eval:ablate`, the "I-160 cap sweep"):
- The key was fixed on the data argument above, not tuned.
- The grid: per-key cap {1, 2} × per-source cap {2, 3, 4, 5, 10} × soft family cap {none, 3, 4, 5}, plus the old cap.
- Leave-one-city-out: each fold picks the best mean NDCG on the other 4 cities among configs that pass the ILD, entropy and no-profile-junk gates there, then scores the held-out city.

| Held-out city | Fold's pick | In-sample (other 4) | Held-out | Old cap |
|---|---|---|---|---|
| Minneapolis | key ≤ 1, source ≤ 3, family ≤ 4 | 0.456 | 0.574 | 0.529 |
| NYC | key ≤ 1, source ≤ 10, family ≤ 4 | 0.530 | 0.393 | 0.373 |
| Chicago | key ≤ 1, source ≤ 10, family ≤ 3 | 0.485 | 0.451 | 0.482 |
| Austin | key ≤ 1, source ≤ 10, family ≤ 3 | 0.466 | 0.526 | 0.528 |
| Seattle | key ≤ 2, source ≤ 3, family ≤ 3 | 0.491 | 0.414 | 0.379 |
| **Mean** | | | **0.471** | **0.458** |

**Reading the sweep.**
- The procedure generalizes: held-out +0.013 over the old cap.
- The folds disagree on the exact caps, so the surface is flat near the top, and all-city in-sample differences of 0.005 are noise.
- The shipped config is *key ≤ 2, source ≤ 3, family ≤ 3*: in-sample 0.476 against a best of 0.480 among gate-passing configs.
- Why that one: of the gate-passing configs within 0.005 of the best, it has the smallest worst-city drop vs the old cap (Chicago −0.019; the others drop −0.03 somewhere). The one config with a smaller drop (−0.010) sits exactly on the entropy gate (0.700).
- Per city (old → new): Minneapolis 0.529 → 0.580, NYC 0.373 → 0.383, Chicago 0.482 → 0.463, Austin 0.528 → 0.539, Seattle 0.379 → 0.414.

**Results, For You top 10** (in-sample over 5 cities × 6 personas; the held-out estimate is the LOCO mean above):

| | v1 | v2 old cap | v2 + I-160 |
|---|---|---|---|
| NDCG@10 | 0.510 | 0.458 | **0.476** (held-out 0.471) |
| P@10 | 0.53 | 0.42 | **0.45** |
| ILD@10 | 0.61 | 0.90 | 0.90 |
| Family entropy@10 | 0.33 | 0.73 | 0.73 |
| Junk@10, no profile | 0.14 | 0.04 | 0.06 |
| Highlights NDCG@6 | 0.46 | 0.64 | 0.64 |

**Ablation after I-160:**

| Variant | NDCG@10 | ILD@10 | Junk@10 |
|---|---|---|---|
| shipped | 0.476 | 0.90 | 0.27 |
| without the exploration slot | 0.489 | 0.89 | 0.25 |
| without exploration and the family cap | 0.505 | 0.86 | 0.22 |
| without exploration and the source, key and family caps | 0.533 | 0.75 | 0.19 |
| pure v2 score (no caps, no MMR, no exploration) | 0.560 | 0.61 | 0.16 |

**The goal (For You NDCG@10 ≥ v1) is not met.**
- I-160 closes 0.018 of the 0.052 gap in-sample (0.013 held-out).
- What's left is the price of the family-entropy gate (≈ 0.016–0.03) and the exploration slot (0.013), not the source cap.
- Reaching v1 under these labels would mean lowering the entropy gate below 0.7, or dropping exploration. Both are product decisions, not tuning, so they weren't made here.
- The λ sweep under the new caps still puts λ at 0.85–0.95 in every fold, so λ stays at 0.9.

---

## References

- Carbonell, J. & Goldstein, J. (1998). *The use of MMR, diversity-based reranking for reordering documents and producing summaries.* SIGIR. https://www.cs.cmu.edu/~jgc/publication/The_Use_MMR_Diversity_Based_LTMIR_1998.pdf
- Santos, R., Macdonald, C. & Ounis, I. (2010). *Exploiting query reformulations for web search result diversification* (xQuAD). WWW.
- Ziegler, C.-N., McNee, S., Konstan, J. & Lausen, G. (2005). *Improving recommendation lists through topic diversification.* WWW.
- Kulesza, A. & Taskar, B. (2012). *Determinantal point processes for machine learning.* Foundations and Trends in ML. https://arxiv.org/abs/1207.6083
- Chen, L., Zhang, G. & Zhou, H. (2018). *Fast greedy MAP inference for determinantal point process to improve recommendation diversity.* NeurIPS. https://arxiv.org/abs/1709.05135
- Wilhelm, M. et al. (2018). *Practical diversified recommendations on YouTube with determinantal point processes.* CIKM. https://dl.acm.org/doi/10.1145/3269206.3272018
- Covington, P., Adams, J. & Sargin, E. (2016). *Deep neural networks for YouTube recommendations.* RecSys. Two-stage candidate generation/ranking, and the "example age" freshness feature. https://research.google/pubs/deep-neural-networks-for-youtube-recommendations/
- Meta AI (2019). *Powered by AI: Instagram's Explore recommender system.* Multi-pass ranking 500 → 150 → 50 → 25. https://ai.meta.com/blog/powered-by-ai-instagrams-explore-recommender-system/
- Eksombatchai, C. et al. (2018). *Pixie: A system for recommending 3+ billion items to 200+ million users in real-time.* WWW. https://arxiv.org/abs/1711.07601
- Agarwal, D. et al. (2014). *Activity ranking in LinkedIn feed.* KDD. Feed ranking with freshness and diversity re-ranking.
- Spotify Engineering (2020). *For your ears only: personalizing Spotify Home with machine learning.* Bandit explore/exploit. https://engineering.atspotify.com/2020/01/for-your-ears-only-personalizing-spotify-home-with-machine-learning
- Salihefendic, A. (2015). *How Hacker News ranking algorithm works* and *How Reddit ranking algorithms work.* Gravity time decay `(p − 1) / (t + 2)^1.8` and log-votes + time "hot". https://medium.com/hacking-and-gonzo. Our `timeliness` is the inverse case: we decay toward the *future* start, not away from the post time.
- Miller, E. (2009). *How not to sort by average rating.* Wilson lower bound and Bayesian smoothing. https://www.evanmiller.org/how-not-to-sort-by-average-rating.html
- Hu, Y., Koren, Y. & Volinsky, C. (2008). *Collaborative filtering for implicit feedback datasets.* ICDM. Implicit signals as confidence.
- Joachims, T., Granka, L., Pan, B., Hembrooke, H. & Gay, G. (2005). *Accurately interpreting clickthrough data as implicit feedback.* SIGIR. Position bias.
- Thompson, W. R. (1933). *On the likelihood that one unknown probability exceeds another.* Biometrika.
- Chapelle, O. & Li, L. (2011). *An empirical evaluation of Thompson sampling.* NeurIPS.
- Li, L., Chu, W., Langford, J. & Schapire, R. (2010). *A contextual-bandit approach to personalized news article recommendation.* WWW. https://arxiv.org/abs/1003.0146
- McMahan, B. et al. (2017). *Communication-efficient learning of deep networks from decentralized data.* AISTATS. https://arxiv.org/abs/1602.05629
- Schein, A., Popescul, A., Ungar, L. & Pennock, D. (2002). *Methods and metrics for cold-start recommendations.* SIGIR.
- Rashid, A. M. et al. (2002). *Getting to know you: learning new user preferences in recommender systems.* IUI.
- Minkov, E., Charrow, B., Ledlie, J., Teller, S. & Jaakkola, T. (2010). *Collaborative future event recommendation.* CIKM. Events are born cold: every item is new, so content and context features carry the load.
- Macedo, A., Marinho, L. & Santos, R. (2015). *Context-aware event recommendation in event-based social networks.* RecSys. Time, location and social context features for events.
- Nguyen, T. et al. (2014). *Exploring the filter bubble: the effect of using recommender systems on content diversity.* WWW.
- Kaminskas, M. & Bridge, D. (2016). *Diversity, serendipity, novelty, and coverage: a survey and empirical analysis of beyond-accuracy objectives in recommender systems.* ACM TiiS.
- Zhang, Y. & Chen, X. (2020). *Explainable recommendation: a survey and new perspectives.* Foundations and Trends in IR. https://arxiv.org/abs/1804.11192
- Tintarev, N. & Masthoff, J. (2007). *A survey of explanations in recommender systems.* ICDE Workshops.
- Järvelin, K. & Kekäläinen, J. (2002). *Cumulated gain-based evaluation of IR techniques.* ACM TOIS. NDCG.
- Buckley, C. & Voorhees, E. (2004). *Retrieval evaluation with incomplete information.* SIGIR.
- Metzler, D. & Croft, W. B. (2007). *Linear feature-based models for information retrieval.* Information Retrieval 10(3). Coordinate ascent.
- Broder, A. (1997). *On the resemblance and containment of documents.* MinHash.
- Charikar, M. (2002). *Similarity estimation techniques from rounding algorithms.* STOC. SimHash; Manku, G., Jain, A. & Das Sarma, A. (2007). *Detecting near-duplicates for web crawling.* WWW.

*Citation note: on 2026-10-16 these URLs were fetched and their titles/authors confirmed: YouTube DNN, Instagram Explore, Pixie, DPP fast greedy MAP, LinUCB, the explainable-rec survey, Spotify Home, and Evan Miller. The MMR PDF downloaded but couldn't be text-extracted. Medium and ACM returned 403 to the fetcher, so check those links by hand. The other entries are cited from the standard literature without fetching.*
