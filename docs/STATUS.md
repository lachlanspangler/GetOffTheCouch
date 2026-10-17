# Status

## Milestone summary: 2026-10-17, end of session 3 ("big quality leap")

**What's real today:** 36,161 upcoming events in **50 US metros** (the top 50 by population), from 791 configured
source×city units. Every page is pre-rendered, indexable and works without JavaScript. All of it runs without API keys.
`make check` is green: 470+ pytest, 282 vitest, the ranking eval and 68/68 Playwright + axe (WCAG 2.2 AA, light and
dark). Nothing is pushed.

### Before / after
- Every screen, desktop and mobile, light and dark: `docs/screenshots/v3-before/` vs `docs/screenshots/v3-after/`
  (60 each: home plus Minneapolis and NYC × feed, deadlines, calendar, map, plan, status, event).
- Two independent design reviews: round 1 graded the redesign C/D on data quality (`docs/research/CRITIQUE_v3_round1.md`).
  Round 2 graded the visuals near A, with About/Methodology/Privacy at A. Both rounds' top-10 lists were fixed.
  What's left is listed under "What I'd do next".

### What was built
1. **Research:** five docs in `docs/research/`: competitors.md (part 2), DESIGN.md, RANKING.md, SCALING.md and
   SEO_ACCESS.md. They fed 120+ new ledger ideas, including rejected ones with reasons.
2. **Design system and full redesign** (DESIGN.md):
   - **Foundations:** a three-layer token system and self-hosted Inter and Newsreader (73.5 KB, metric-matched
     fallbacks, zero layout shift). Category art is deterministic SVG instead of photos.
   - **Listings:** day-grouped list rows with a tested budget of three signals per card, and no fake urgency.
     The filter bar is one row, with a bottom sheet on mobile.
   - **Pages:**
     - real event pages with a ticket card and destination-named CTAs ("Register with …", "Express interest on …")
     - an editorial city page with honest coverage ("15 sources, strongest in …", "Still thin here: …")
     - a public status page with a quality-bar table
     - About, Methodology and Privacy pages that read like a company wrote them
   - **Curation layer** (`web/src/lib/curate.ts`, tested):
     - **Fixes how listings read:** shouting titles, address-as-venue, the year in a venue name.
     - **Hides from the city page:** out-of-region away games, campus-internal meetings, full or sold-out events,
       events already underway, kids' programs and board or admin roles.
     - **Kids' and admin listings stay findable.** They're one click away, and nothing is deleted.
3. **Ranking engine v2** (`web/src/lib/rank/`, RANKING.md §7):
   - **Pipeline:** candidates, then 29 features, then a linear score with per-feature contributions, then a diversity
     re-rank (MMR) with caps, then plain-language explanations.
   - **On-device personalization:** saves, opens, calendar adds and "Not for me", with a 21-day half-life, ±0.3 cap
     and an exploration slot. It's visible as "For you", "Why this?" and "What we've learned on this device", with a
     forget button.
   - **Offline evaluation:** 3,360 hand-labeled judgments across 5 cities × 6 personas, plus golden-rule tests.
     `npm run eval:rank` runs inside `make check`.
   - **Results:** the newcomer front page beats v1 (NDCG@6 **0.46 → 0.64**, junk 0.14 → 0.04, diversity 0.61 →
     0.90). Personalized "For you" relevance is slightly lower than v1 (0.46 vs 0.51) because of the
     two-per-source diversity cap. That's a deliberate trade, documented in RANKING.md.
4. **Findability** (ADR-0007):
   - **Real URLs:** `/chicago/`, hubs like `/chicago/concerts/` and `/chicago/this-weekend/`, and
     `/chicago/events/<title>-<id>/`. Old `#/` links redirect.
   - **Pre-rendered pages:** 19,846, each with a title, description, canonical, robots tag, Open Graph tags and
     Event JSON-LD. JSON-LD carries reported prices only, and only when a real address exists.
   - **Sitemaps and checks:** per-city sitemaps, plus a dist checker (0 problems).
   - **Hydration and speed:** exact hydration, so no flash or layout shift. On a throttled mid-range phone
     (Slow 4G, 4× CPU), LCP is about 0.7 s on every page tested and CLS is 0.
   - **Bundle:** entry JS is 59.9 KB gzipped against a 60 KB budget. Budgets are enforced in CI.
5. **50 metros and scaling** (SCALING.md, ADR-0008):
   - **New tools:** `gotc discover` (automatic source discovery), `gotc city new`, and `config/metros.yaml`
     (Census-recentred).
   - **Go-live gate** (G1–G11), with live/beta tiers shown on the site.
   - **Infrastructure:** incremental builds and exports, per-city payload budgets, price-snapshot downsampling, a
     sharded hourly refresh with a monolithic fallback, and a keepalive workflow.
   - **Compliance:**
     - Nominatim is off: we were over its rate limit, and its robots.txt disallows `/search`.
     - The Wikidata lookups stopped: robots.txt disallows them.
     - A real RFC 9309 robots.txt parser replaced the old one, which had ignored wildcards. It disabled 12 units
       that had slipped through.
6. **Trust:** sourcing and "checked N ago" on every event, "Hosted by …, not by us", "Report a problem" (a
   prefilled GitHub issue) on every event and in the footer, and a privacy page that matches the code.

### City count and coverage
**50 cities exported.** 10 are **live** (the original cities, under a 7-day grace period) and **40 are beta**.

- **Every new city fails G10 by design:** it requires 48 h of green hourly runs, so all 40 stay beta until that history
  exists.
- **Four cities fail only that check:** Atlanta, Charlotte, San Diego and San Jose. They'll be promoted by the gate after
  48 h of runs.
- **The rest also miss real criteria:**
  - **G8 (≥80% geocoded), 24 cities:** these are mostly venue-name-only sources. Without Nominatim, Census can't
    place them.
  - **G3/G4 (category breadth and newcomer pillars):** no leagues, volunteering or openings feed in the city.
  - **G5 (no published deadlines):** 22 cities. RunSignup registration would fix most of these.
- **Genuinely thin today:** Fresno, Grand Rapids, Columbus, Louisville, Memphis, Oklahoma City and Riverside.
  In most cases the missing sources are robots-blocked, Cloudflare-walled or Simpleview 403s, so outreach is the way
  forward. Each one is in docs/SOURCES.md.

The columns are: city, tier, events, events in the next 7 days, healthy sources, strongest pillars, and pillars with nothing yet.

| City | Tier | Events | 7 days | Sources | Strongest | Nothing yet |
|---|---|---|---|---|---|---|
| New York City | live | 2,782 | 673 | 15 | Openings & parties, Volunteering, Leagues | – |
| Chicago | live | 1,731 | 780 | 14 | Openings & parties, Leagues, Cons & faires | Deadlines |
| Boston | live | 1,473 | 673 | 13 | Volunteering, Leagues, Trivia & games | – |
| Phoenix | beta | 1,291 | 456 | 15 | Trivia & games, Volunteering, Openings & parties | Leagues, Deadlines |
| Seattle | live | 1,252 | 654 | 19 | Concerts, Openings & parties, Trivia & games | – |
| San Jose | beta | 1,208 | 811 | 10 | Leagues, Volunteering, Cons & faires | – |
| Atlanta | beta | 1,118 | 540 | 14 | Trivia & games, Leagues, Openings & parties | – |
| San Francisco | beta | 1,114 | 373 | 19 | Volunteering, Openings & parties, Leagues | – |
| Charlotte | beta | 1,068 | 505 | 10 | Trivia & games, Volunteering, Openings & parties | – |
| Austin | live | 970 | 201 | 20 | Openings & parties, Trivia & games, Concerts | Deadlines |
| Denver | live | 943 | 324 | 16 | Trivia & games, Leagues, Openings & parties | Volunteering, Cons & faires |
| Birmingham | beta | 867 | 296 | 16 | Trivia & games, Openings & parties, Concerts | – |
| Minneapolis | live | 848 | 240 | 19 | Volunteering, Trivia & games, Concerts | – |
| Nashville | live | 835 | 318 | 10 | Volunteering, Trivia & games, Concerts | Cons & faires |
| Los Angeles | live | 834 | 233 | 12 | Volunteering, Openings & parties, Leagues | Trivia & games |
| Dallas | beta | 825 | 163 | 12 | Trivia & games, Openings & parties, Concerts | Volunteering, Deadlines |
| Washington | beta | 823 | 379 | 11 | Leagues, Trivia & games, Deadlines | Cons & faires |
| Houston | beta | 819 | 304 | 15 | Trivia & games, Openings & parties, Volunteering | Leagues |
| Philadelphia | beta | 760 | 85 | 15 | Openings & parties, Concerts, Leagues | Trivia & games |
| Miami | live | 732 | 472 | 11 | Trivia & games, Openings & parties, Leagues | – |
| Salt Lake City | beta | 717 | 633 | 6 | Trivia & games, Openings & parties | Leagues, Cons & faires, Deadlines |
| Baltimore | beta | 689 | 201 | 14 | Leagues, Trivia & games, Deadlines | – |
| Cleveland | beta | 676 | 462 | 6 | Cons & faires | Leagues |
| Orlando | beta | 668 | 368 | 9 | Trivia & games, Openings & parties, Concerts | Deadlines |
| Raleigh | beta | 667 | 106 | 12 | Openings & parties, Trivia & games, Cons & faires | Deadlines |
| Tampa | beta | 620 | 229 | 12 | Trivia & games, Volunteering, Openings & parties | Cons & faires, Deadlines |
| Richmond | beta | 615 | 246 | 11 | Volunteering, Trivia & games, Concerts | Leagues, Openings & parties, Deadlines |
| Jacksonville | beta | 611 | 217 | 12 | Openings & parties, Trivia & games, Volunteering | – |
| Portland | beta | 600 | 208 | 15 | Concerts, Openings & parties, Trivia & games | Leagues, Volunteering |
| San Diego | beta | 574 | 241 | 8 | Leagues, Deadlines, Trivia & games | – |
| Providence | beta | 556 | 142 | 15 | Concerts, Openings & parties, Volunteering | – |
| Hampton Roads | beta | 507 | 158 | 11 | Trivia & games, Volunteering, Cons & faires | Leagues, Deadlines |
| Indianapolis | beta | 503 | 252 | 6 | Trivia & games, Volunteering | Leagues, Openings & parties, Deadlines |
| St. Louis | beta | 497 | 201 | 8 | Trivia & games, Volunteering, Openings & parties | Leagues, Deadlines |
| Las Vegas | beta | 488 | 390 | 8 | Volunteering, Trivia & games, Deadlines | Leagues |
| Hartford | beta | 479 | 168 | 12 | Openings & parties | Leagues, Volunteering, Cons & faires |
| San Antonio | beta | 458 | 105 | 12 | Trivia & games, Openings & parties | Leagues, Deadlines |
| Cincinnati | beta | 448 | 293 | 5 | Trivia & games, Volunteering | Openings & parties, Deadlines |
| Sacramento | beta | 444 | 221 | 9 | Openings & parties, Concerts, Cons & faires | Leagues, Volunteering, Deadlines |
| Riverside | beta | 411 | 107 | 7 | – | Openings & parties, Concerts, Cons & faires, Trivia & games, Deadlines |
| Memphis | beta | 388 | 62 | 12 | Trivia & games, Concerts | Leagues |
| Milwaukee | beta | 332 | 136 | 7 | Trivia & games | Leagues, Openings & parties, Deadlines |
| Pittsburgh | beta | 301 | 87 | 11 | Volunteering, Concerts, Deadlines | Leagues, Cons & faires, Trivia & games |
| Columbus | beta | 293 | 74 | 7 | Cons & faires | Leagues, Openings & parties, Deadlines |
| Kansas City | beta | 280 | 115 | 8 | Trivia & games, Volunteering, Leagues | Deadlines |
| Detroit | beta | 266 | 33 | 8 | Concerts, Volunteering | Leagues, Cons & faires, Trivia & games |
| Oklahoma City | beta | 262 | 39 | 11 | Trivia & games | Cons & faires |
| Grand Rapids | beta | 219 | 107 | 3 | – | Leagues, Openings & parties, Concerts, Volunteering, Cons & faires, Deadlines |
| Louisville | beta | 215 | 32 | 6 | Trivia & games, Concerts | Leagues, Volunteering, Cons & faires, Deadlines |
| Fresno | beta | 34 | 6 | 2 | – | Leagues, Openings & parties, Concerts, Volunteering, Cons & faires, Trivia & games, Deadlines |

### What I need from you
1. **Push**, then watch the first sharded "Refresh data" run (see "Will change on push" below). If it misbehaves, run
   "Refresh data (monolithic fallback)" by hand.
2. **Keys** (in `.env` and as repo secrets):
   - `TICKETMASTER_API_KEY` covers concerts at Live Nation and arena venues in every city. It's the biggest
     content gap.
   - `SEATGEEK_CLIENT_ID`.
   - `RUNSIGNUP_API_REG` and `_SECRET` add race deadlines everywhere and fix G5 in most cities.
   - Optional: `SOCRATA_APP_TOKEN`, recommended now that we read about 20 Socrata domains.
3. **Domain:**
   - **Decide on a custom domain before Google indexes the github.io URLs.** Moving later is a site move. With a
     domain: set it in Pages and set `GOTC_BASE=/` and `GOTC_SITE_ORIGIN` in refresh.yml.
   - **Then add a Search Console URL-prefix property** and submit `sitemap.xml`.
4. **Confirm two judgment calls:**
   - **weather.gov:** its robots.txt is `Disallow: /`, but its API docs ask apps to call it, so we still do.
   - **Venue ownership:** Roseland Theater (Portland) and Kentucky Performing Arts are kept. Both are the venue's own
     site, despite a "Live Nation Presents" label.
5. **Outreach** that would unlock the thin cities (all blocked on you):
   - Simpleview tourism boards (Phoenix, Scottsdale, Salt Lake, Sacramento, Riverside, Fresno, Columbus)
   - CA ABC license data
   - the Michigan and Ohio SoS sites (robots 403)
   - libraries that block robots: Free Library of Philadelphia, Carnegie, Louisville, Columbus, Memphis, Providence
   - Hands On Birmingham and Hands On Atlanta, LibraryMarket, and the earlier list below
6. **If the repo is private:** the sharded hourly refresh needs more Actions minutes than the free tier. Public repos are unlimited.

### What I'd do next
1. **After 48 h of hourly runs:** re-check the gate. Several beta cities should go live on their own. Then work the
   remaining beta failures city by city.
2. **Geocoding without Nominatim:** a curated per-city venue file (`config/venues`) for the top venue-name-only places
   would fix G8 in most cities. A self-hosted Pelias or Photon would need a decision from you.
3. **Ranking:** cap by organizer instead of listing source (I-160), which should close the For You gap. Get a human
   to check the judgment labels (I-161).
4. **Speed and SEO:** week-sharded city data with an inlined `initial.json` (I-117; the NYC feed is 443 KB gz),
   build-time OG share images (I-115), and the event-page lifecycle stubs (I-112).
5. **The remaining critique items:**
   - one category vocabulary across filters, hubs and rows
   - per-source allowlists for university calendars
   - a dated "This weekend" title
6. **The ranked backlog:** `python -m gotc.ideas next`.

---

# Earlier milestones

## Milestone summary: 2026-10-16, end of session 2

**What's real today:** 13,182 live events across all 10 seed cities. They come from 196 configured source×city units, and every enabled unit is healthy. Everything below runs without API keys.

| City | Events | Music | Games to watch | Trivia | Volunteer | Leagues | Openings | Published deadlines | Healthy sources |
|---|---|---|---|---|---|---|---|---|---|
| Austin | 1,026 | 382 | 75 | 60 | 11 | 17 | 51 | 1 | 20/20 |
| Boston | 1,567 | 95 | 142 | 54 | 542 | 99 | 21 | 91 | 14/14 |
| Chicago | 1,806 | 74 | 43 | 2 | 7 | 66 | 135 | 0 | 14/14 |
| Denver | 970 | 191 | 58 | 169 | 0 | 98 | 103 | 99 | 16/16 |
| Los Angeles | 886 | 103 | 117 | 0 | 225 | 48 | 104 | 50 | 12/12 |
| Miami | 831 | 63 | 75 | 97 | 8 | 17 | 66 | 17 | 11/11 |
| Minneapolis | 872 | 237 | 110 | 33 | 95 | 6 | 0 | 3 | 19/19 |
| Nashville | 878 | 190 | 45 | 177 | 406 | 7 | 13 | 1 | 10/10 |
| New York City | 3,040 | 128 | 72 | 3 | 221 | 149 | 1184 | 122 | 15/15 |
| Seattle | 1,306 | 433 | 33 | 38 | 26 | 1 | 33 | 7 | 19/19 |

### Done this session
- **Concerts with live prices (priority 1).** The biggest gap is now partly closed without keys.
  - **Sources:**
    - Venues' own calendars (schema.org JSON-LD): 17 venues, face-value prices where published.
    - 10 big arenas and theaters via public venue RSS: Ryman, Bridgestone, Target Center, Grand Casino Arena, TD Garden, Kaseya, Barclays, Crypto.com Arena, Wintrust, Moody Center.
    - Denver Arts & Venues, ACL Live, H-E-B Center, and comedy and jazz calendars.
  - **Dedup:** the same show from a venue calendar and Ticketmaster merges into one event (tested on a real fixture).
  - **Price display:**
    - Cards show "from $X · N sellers" with a per-seller tooltip.
    - A weekly price-trend badge appears only with ≥24h of snapshots, and the drawer has a sparkline.
    - Price snapshots are taken every run, so trends become real as hourly runs accumulate.
  - **Availability and on-sale:**
    - "~x% left" is shown only from reported counts (libraries, volunteer shifts) or labeled resale-listing signals.
    - Ticketmaster on-sale and presale times become reported "Tickets go on sale" deadlines, with .ics reminders 1 day and 15 minutes before.
  - **Ticketmaster and SeatGeek are fully built and tested** against documented-shape fixtures. They turn on the moment keys exist.
- **Coverage holes (priority 2):**
  - **Denver:** 201 → 970 events (libraries, arts venues, concerts, trivia, DU games).
  - **Seattle:** 300 → 1,306 events (KCLS, city calendar, jazz, comedy, theatres, Huskies).
  - **Austin:** concerts and comedy added (ACL Live, Moody Center, Cap City, Flamingo Cantina).
  - **Openings:** Miami (Florida DBPR original-licensure dates) and Boston (food-license CSV).
  - **Trivia:** Team Trivia and Challenge Entertainment in Denver, Nashville and Austin.
  - **Athletics:** college home games in 9 cities.
  - **Chicago deadlines:** still 0 published. The keyless fix, RunSignup races, is built and recorded (+42 real Chicago deadlines) but gated on a free API registration (see below).
- **Newcomer walkthrough (priority 3).** Before and after screenshots are in `docs/screenshots/{before,after}/`. Fixed:
  - contradictory "closed/open" badges (availability now reconciled with live deadlines)
  - highlights repeating in the day list below them
  - kids/teen and campus programs topping adult picks
  - "~1" crowd sizes
  - mobile filters filling the first screen (now behind "Filters (N)")
  - campus catch-all noise; "12 AM" date-only items
  - NBA games, forums and venue tours labeled as concerts
  - library-dominated highlights; no concert in highlights
- **Widening (priority 4):**
  - "Pick a weekly habit" in the plan; "Similar this week" in the drawer.
  - 40 sourced venue capacities, so 499 concerts now get capacity × fill attendance bands instead of category priors.
  - Map clustering.
  - Tolerant XML feeds; disabled a source (Triple Door) whose dates were wrong rather than patching around it.
- **Fixed for CI and tooling:**
  - `make pipeline` had been broken by flag order.
  - Cold-cache geocoding is now bounded so the hourly refresh fits its timeout.
  - `run --source` rebuilds only affected cities.

### Real vs. stubbed
| Area | State |
|---|---|
| Open data, libraries, universities, parks, venue calendars, arenas, athletics, Volo, volunteering, cons, trivia, openings, curated registry | ✅ real, live |
| Weather, venue capacities (40 sourced; Wikidata rows frozen 2026-10-16, robots), starter pack, geocoding (Census; Nominatim off) | ✅ real |
| Face-value concert prices | ✅ real where venues publish them. Ticketmaster fills the rest once keyed |
| Resale prices, listing counts, "selling fast" from resale | 🟡 SeatGeek adapter ready; **needs `SEATGEEK_CLIENT_ID`** |
| Ticketmaster (most big-venue tickets, on-sale times) | 🟡 adapter ready; **needs `TICKETMASTER_API_KEY`** |
| RunSignup races (published registration deadlines in every city) | 🟡 adapter + fixture ready; **needs free API caller registration** |
| Price trends | 🟡 real snapshots accumulate per run; a trend shows after ≥24h of data |
| Meetup, Eventbrite per-organizer | ⏸ need OAuth/token |

## What I need from you
1. **GitHub (one time):**
   - Settings → Pages → Source: **GitHub Actions**. The Pages API currently returns 404, so the site isn't enabled yet.
   - Actions → General → Workflow permissions: **Read and write**.
   - Actions → **Refresh data** → **Run workflow**, once by hand. The hourly schedule hadn't fired by 08:43 UTC, 2h after the push. GitHub often delays a new repo's first cron, and a manual run also verifies Pages and the state branch.
2. **Keys** (add to `.env` locally and as repo secrets):
   - `TICKETMASTER_API_KEY`: free, instant, https://developer-acct.ticketmaster.com/user/register
   - `SEATGEEK_CLIENT_ID`: free, https://seatgeek.com/account/develop
   - `RUNSIGNUP_API_REG` + `RUNSIGNUP_API_REG_SECRET`: free API caller registration; RunSignup's terms require it.
   - Optional: `SOCRATA_APP_TOKEN`.
3. **Outreach** that would unlock more (all blocked on you):
   - AEG Presents (Mission Ballroom, Bluebird, Ogden, Gothic…)
   - LeagueLab (Nashville Sports Leagues, Underdog Seattle)
   - LeagueApps clubs (Chicago Sport & Social, Boston Ski & Sports, CLUBWAKA)
   - Simpleview boards (Meet Boston, Visit Austin, Visit Denver)
   - Geeks Who Drink / King Trivia (LA and Seattle trivia)
   - Galaxy Digital tenants; Volo partner feed

## Will change on push
Everything below is merged into local `main` (about 170 commits ahead of origin). When you push:

1. **The hourly refresh becomes sharded** (`.github/workflows/refresh.yml`, ADR-0008):
   - `prepare` pins the current `pipeline-state` commit and plans shards with `gotc shards --size 4`
     (10 cities → 3 shards today, balanced by unit count).
   - `shard` (matrix, `max-parallel: 8`) restores that state, runs `gotc run --cities … --no-build`, and uploads
     a delta DB + its new raw payloads as a 1-day artifact. Shards never deploy, push or call Nominatim.
   - `publish` restores the same state, merges the deltas (`gotc state merge`), runs `scripts/loop.sh` with
     `--no-fetch` (doctor → build → export → contract tests), deploys Pages **once**, force-pushes the state,
     and saves raw payloads to the Actions cache once per run (key `raw-<run_id>`, restored by prefix; `GOTC_RAW_RETENTION_DAYS=7` keeps the store bounded).
   - Same name ("Refresh data"), same cron (`17 * * * *`), same secrets, same Pages environment, same
     `refresh` concurrency group. **No new one-time settings.** The existing Pages setup (Source: GitHub
     Actions; workflow permissions: read and write) is all it needs.
   - A failed shard doesn't block the deploy; its cities keep last-known-good data.
2. **Fallback:** the previous single-job workflow is kept as `refresh-monolithic.yml`, manual only. If the
   sharded run misbehaves: Actions → "Refresh data (monolithic fallback)" → Run workflow. To switch back for
   good: uncomment its `schedule:` line and comment out the one in `refresh.yml`. Both use the same state
   branch format (one `gotc.db.gz`), so you can switch either way at any time.
3. **New `keepalive.yml`:** on the 1st of each month it re-enables `refresh.yml` and itself via the REST API
   (`permissions: actions: write`), against GitHub's 60-day inactivity disable. No commits to main. In CI,
   `gotc doctor` now warns in HEALTH.md when the last scheduled run is > 3 h old.
4. **First run after the push:** the state DB gains two tables (migrations 005 `city_gate`, 006
   `city_build_state`), applied automatically. The ten current cities are incumbents (`config/metros.yaml`), so
   the go-live gate keeps them **live** for 7 days even though G10 (≥ 48 h of green runs) can't pass yet; a
   live city failing a hard criterion shows `coverage.banner: true` after 72 h and drops to beta on day 7
   (today that would be Austin and Miami on G8 geocoding, Chicago/Austin on G5 deadlines, Denver/Nashville on
   G3/G4; see `gotc gate`).
5. **Nominatim is now off** (robots.txt disallows `/search`; docs/SOURCES.md). New place-name-only locations
   won't get coordinates until you decide otherwise (`GOTC_NOMINATIM=1`, a compliant 4/min lane).
   **Wikidata venue capacities stopped refreshing** (robots.txt disallows `/sparql` and `/w/api.php`); existing
   rows keep serving.
6. **The site moves from `#/` URLs to real paths and pre-renders every page** (ADR-0007):
   - **Pages artifact:** about 500 MB at 50 cities (the guard fails at 800 MB). The prerender step adds about 2 minutes
     to `publish`.
   - **Base path:** `refresh.yml` sets `GOTC_BASE=/GetOffTheCouch/`. Without it, assets would 404.
   - **Old `#/` links** keep working through a client-side redirect.
   - **CI:** `ci.yml` now builds the demo dataset before the web tests and enforces the JS/CSS/font budgets.
7. **The OSM credit** for cached Nominatim coordinates is in the footer ("Map data and some locations ©
   OpenStreetMap contributors").

## What I'd do next
1. With keys: record real Ticketmaster/SeatGeek fixtures, then check cross-seller dedup and price comparison on live NYC/LA arena data.
2. With RunSignup registration: race deadlines in all cities. That alone fixes Chicago's 0 published deadlines.
3. After a few days of hourly runs: review price-trend and "selling fast" signals on real snapshot history, and tune the thresholds.
4. Remaining polish ideas (time-precision labels, per-room capacities, series-date health check, concert digest) are in `python -m gotc.ideas next`.

## What works (detail)
- **Pipeline.** `gotc run` is hourly-safe: units that aren't due skip in microseconds, and each unit commits in its own transaction, so it's resumable.
- **Health.** Healthy → degraded → quarantined (3 strikes, exponential probe backoff) → recovering → healthy. Schema drift, empty results and volume drops are detected on HTTP 200s. Last-known-good keeps serving, marked stale with a reason. Failures surface in HEALTH.md, `health.json`, the in-app Health page, the diary, and auto-opened GitHub issues.
- **Dedup.** Cross-source clustering with sticky ids. One card keeps every seller's price.
- **Estimates.** Attendance bands, social score and ticket signals each carry a method and confidence. See docs/METHODOLOGY.md.
- **Recommendations.** Explainable scoring plus a first-30-days plan. Weather-aware, deadline-aware, diverse.
- **Exports.** Calendar export (.ics) with deadline alarms, shareable URLs and shared lists, saved events, "new this week" badges, and report-a-problem links.
- **Relevance.** Cancelled events are hidden, not-public university items are skipped (counted), a geofence drops out-of-area events, multi-site programs collapse, and an "Ongoing" section holds exhibits.
- **Operator tools.** `gotc forget <unit>` after a deliberate config change; `gotc replay` after a parser fix; `python -m gotc.autoideas`.

## Next (what I'd build next, in order)
1. **Ticketmaster key → concerts everywhere.** It's the biggest content gap. Then record real fixtures and check cross-seller dedup on live data.
2. **SeatGeek key → real price trends.** This makes "selling fast" and the price trend come from live resale data.
3. **More leagues.** HandsOn/Galaxy tenants and Volo markets (I-076). Outreach to LeagueLab/LeagueApps orgs for permission.
4. **Census batch geocoder** to close the coordinate gap in Miami and Seattle (I-076/batch idea).
5. **Payload split** (cards vs. details) once NYC passes ~8 MB raw.
6. **Email/push reminders.** These need a tiny backend (e.g. a scheduled GitHub Action + Buttondown). .ics alarms cover it today.

Also done this session (no longer gaps): Minneapolis deadlines via library registration and HandsOn Twin Cities, the Wikidata venue capacity registry, the registration-waves timeline, and neighborhood vibes.

See `python -m gotc.ideas next` for the ranked backlog.
