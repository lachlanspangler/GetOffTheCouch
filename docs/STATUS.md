# Status

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
Branch `worktree-agent-af5b74cde53399d39` (scaling work, 2026-10-16). When you push it to `main`:

1. **The hourly refresh becomes sharded** (`.github/workflows/refresh.yml`, ADR-0008):
   - `prepare` pins the current `pipeline-state` commit and plans shards with `gotc shards --size 4`
     (10 cities → 3 shards today, balanced by unit count).
   - `shard` (matrix, `max-parallel: 8`) restores that state, runs `gotc run --cities … --no-build`, and uploads
     a delta DB + its new raw payloads as a 1-day artifact. Shards never deploy, push or call Nominatim.
   - `publish` restores the same state, merges the deltas (`gotc state merge`), runs `scripts/loop.sh` with
     `--no-fetch` (doctor → build → export → contract tests), deploys Pages **once**, force-pushes the state,
     and saves raw payloads to the Actions cache **once per day** (key `raw-YYYY-MM-DD`, was once per run).
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
6. **The dashboard needs an OSM credit** ("Geocoding © OpenStreetMap contributors") for previously cached
   Nominatim coordinates; web/ was out of scope for this branch.

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
