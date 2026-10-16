# Diary

Append-only and chronological: **newest entries at the bottom**. Human/agent entries use the template in
docs/WORKFLOW.md. Automated one-liners from `gotc run` / `gotc doctor` are bullets.

## 2026-10-15 22:35 UTC-5: Day 0: research, scaffold, first real vertical slice
**Did:**
- Read GameCred's workflow (CLAUDE.md, WORKFLOW, DIARY, IDEAS, ledger, HEALTH, Makefile, .github) and adapted it. Changes:
  - The ideas ledger JSON is the single source of truth, and IDEAS.md is generated from it. GameCred's two files drifted.
  - The diary is truly append-only, with the newest entry at the bottom.
  - Health is per source × city "unit" with a real state machine, instead of a doctor-only report.
- `git init` with the remote set. Not pushed (the user pushes).
- Launched 3 research agents (city open data, ticketing APIs + competitors, leagues/volunteer/niche). Ticketing is back: docs/research/ticketing_and_events_apis.md and competitors.md.
- Built the pipeline core:
  - Versioned pydantic schema and YAML taxonomy (14 top-level families, ~95 categories).
  - Config-driven cities/sources.
  - PoliteClient (robots, throttle, retries, conditional GET, secret redaction).
  - SQLite with migrations, gzipped raw payload store.
  - Health state machine; ingest/build/export/run/doctor.
  - Adapters: Socrata, ICS, Tribe Events, Localist, LiveWhale, Ticketmaster, SeatGeek.
  - Entity resolution with sticky ids, deadline extraction, attendance bands, ticket signals.
- First live run: Minneapolis Park & Rec (Tribe REST) returned 53 records → 51 events. Ticketmaster and SeatGeek show "disabled: needs key".

**Broke:**
- The editable install had no .pth file until `uv pip install -e .`.
- The location extractor grabbed whole sentences. Fixed by splitting at the sentence end.
- The "21+" regex never matched at end of text, because `\b` after `+` fails.
- 2-significant-figure rounding pushed the attendance ceiling above venue capacity. Now capped.

All four were caught by tests or by looking at the real output.

**Decided (and why):**
- **Python + SQLite + static dashboard (ADR-0001/0002).** Boring, free to host, and the dashboard can be served from GitHub Pages and refreshed by cron. No server to keep alive.
- **Health is per unit, not per source**, because a source can be fine in Chicago and broken in Miami.
- **Generic platform adapters before bespoke scrapers.** One Tribe/Localist/ICS adapter covers thousands of calendars, so adding a city becomes config.
- **Sign-up links found in description HTML become offers.** For volunteer and park events they're the most actionable thing on the card.
- **Volunteering is marked free** (derived, labeled).
- **Repeated occurrences get a `series_id`** so the list shows one card.
- **No "% tickets left" number unless a labeled signal backs it.** Research confirmed no legit source exposes seat inventory.

**Verified:** `gotc run --city minneapolis` live. The exported `web/public/data/cities/minneapolis.json` has 51 events, 20 with SignUpGenius/registration offers, 10 series, and real venues ("Lyndale Park/Rose Garden", "Powderhorn Park"…). HEALTH.md shows 1 healthy and 2 disabled with reasons. 76 tests green; ruff and mypy --strict clean.

**Next:** finish the commit, then the dashboard (Vite+Preact+TS), wider Minneapolis sources once city research lands (library, liquor licenses, curated leagues), then NYC.

**Ideas:** I-001..I-010 done; I-011, I-012, I-014, I-015 done; 45 in the ledger, including 7 rejected with reasons.
- 2026-10-16 04:39 UTC · run 2 ok: units[1 ok] → 74 events in 1 cities
- 2026-10-16 04:40 UTC · run 3 ok: units[1 ok] → 74 events in 1 cities
- 2026-10-16 04:48 UTC · doctor --fix: 0 errors, 0 fixed, 0 warnings
- 2026-10-16 04:48 UTC · run 4 ok: units[2 disabled, 2 skipped] → 74 events in 1 cities
- 2026-10-16 04:28 UTC · run 1 partial: units[2 disabled, 1 failed, 4 ok] → 1330 events in 1 cities
- 2026-10-16 04:35 UTC · run 2 ok: units[2 disabled, 6 ok] → 1498 events in 1 cities
- 2026-10-16 04:36 UTC · run 3 ok: units[2 disabled, 4 ok] → 414 events in 1 cities
- 2026-10-16 04:36 UTC · run 4 ok: units[2 disabled, 3 ok] → 464 events in 1 cities
- 2026-10-16 04:37 UTC · run 5 ok: units[2 disabled, 2 ok] → 825 events in 1 cities
- 2026-10-16 04:37 UTC · run 6 partial: units[2 disabled, 1 failed, 4 ok] → 628 events in 1 cities
- 2026-10-16 04:37 UTC · run 7 partial: units[2 disabled, 3 failed, 1 ok] → 0 events in 1 cities
- 2026-10-16 04:37 UTC · run 8 ok: units[2 disabled, 4 ok] → 300 events in 1 cities
- 2026-10-16 04:38 UTC · run 9 partial: units[2 disabled, 1 failed, 1 ok] → 176 events in 1 cities
- 2026-10-16 04:38 UTC · run 10 partial: units[2 disabled, 3 failed, 3 ok] → 751 events in 1 cities
- 2026-10-16 04:41 UTC · run 11 ok: units[1 ok] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 12 ok: units[1 ok] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 13 ok: units[1 ok] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 14 ok: units[1 ok] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 15 ok: units[1 ok] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 16 ok: units[1 disabled] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 17 ok: units[1 disabled] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 18 ok: units[1 disabled] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 19 ok: units[1 disabled] → 6476 events in 10 cities
- 2026-10-16 04:41 UTC · run 20 ok: units[1 disabled] → 6476 events in 10 cities
- 2026-10-16 04:50 UTC · run 21 ok: units[1 ok] → 6473 events in 10 cities
- 2026-10-16 04:50 UTC · run 22 ok: units[1 ok] → 6473 events in 10 cities
- 2026-10-16 04:50 UTC · run 23 ok: units[1 ok] → 6473 events in 10 cities
- 2026-10-16 04:50 UTC · run 24 ok: units[1 ok] → 6473 events in 10 cities
- 2026-10-16 04:50 UTC · run 25 ok: units[1 ok] → 6418 events in 10 cities
- 2026-10-16 04:50 UTC · run 26 ok: units[1 ok] → 6408 events in 10 cities
- 2026-10-16 04:50 UTC · run 27 ok: units[1 ok] → 6401 events in 10 cities

## 2026-10-16 05:00 UTC: ten cities, six new adapters, openings from license data
**Did:** Added `arcgis`, `ckan`, `bibliocommons`, `trumba`, `simpleview` and `communico` adapters, plus `gotc/adapters/mapped.py`, the config-driven row mapper now shared by socrata/arcgis/ckan. It handles openings (all-day on the license's newness date, a bar-vs-restaurant split, a "License signal, not a confirmed opening date" description), drops personal-data columns, withholds person-like legal names, and has data-quality guards (`validate`, `reject_future_start`, `max_future_days`, `sane_coords`). Wrote configs for nyc, chicago, los_angeles, miami, austin, denver, seattle, nashville and boston, and added HCLib, the Downtown Council and UMN to minneapolis. Fixture tests for every adapter run on real samples and recorded payloads. Wrote docs/SOURCES.md.
**Broke:** The NYU LiveWhale payload crashed `calendars._price` (numeric `cost`), which is fixed now. The PII column regex matched "busine**ssn**ame", so Boston food licenses lost their names; it's now anchored, with a regression test.
**Decided (and why):** (1) Disabled Meet Boston, Visit Austin and Visit Denver. Their Simpleview APIs return 403 "Access Denied" (CDN bot protection) to PoliteClient even though robots allows them, and we don't evade bot protection. (2) Disabled the data.boston.gov CKAN units because robots says `Disallow: /api/`. (3) ArcGIS gets `respect_robots = False` like Socrata. It's a documented REST API, and `services*.arcgis.com/robots.txt` answers 403 "Invalid URL" (no policy), which PoliteClient would read as "disallow all". (4) Minneapolis liquor is skipped because the data has no original-issue date (I-046).
**Verified:** Live run of all 10 cities: 36 healthy units, 5 disabled with reasons, 20 key-gated (TM/SeatGeek). Counts are in docs/SOURCES.md. In the exports, openings dated in the past never appear, because `build.load_live_records` drops records whose end is before now. Only the future-dated LA/Seattle registrations show up (24 + 9), and Denver exports 0 events. I couldn't fix this, since build.py belongs to another agent, so it's logged as I-047. I didn't run `make dev` or look at the dashboard: web/ belongs to another agent.
**Next:** I-047 (openings display window), I-048 (FL DBPR CSV), I-054 (Denver events), I-049 (Chicago adult sports deadlines).
**Ideas:** I-019, I-031, I-032 done; I-046..I-054 added.
_Note (merge, 2026-10-16 05:10 UTC): the idea ids in the entry above were renumbered on merge: I-046..I-054 there are I-058..I-066 in the ledger._

## 2026-10-16 05:20 UTC: dashboard, curated registry, starter pack, weather, a11y; merged 10-city adapters
**Did:**
- **Dashboard (Vite + Preact + TS).**
  - Views: feed with series collapsed, deadlines by urgency with a "registering now" timeline, calendar, Leaflet map (canvas), new-in-town onboarding → explained 30-day plan, saved, health, about.
  - Event drawer: price comparison, attendance band, provenance, report link.
  - .ics export with alarms, shareable URLs, demo mode.
- **Curated registry with page-watch.** Each entry quotes its source verbatim, and every run re-checks that the quote is still on the page. 10/11 Minneapolis quotes were re-verified live.
- **Enrichment:**
  - New-resident starter pack (pipeline + UI; state data being researched).
  - NWS weather on outdoor events, which also feeds the rain penalty in recommendations.
  - Wikidata venue capacities (P1083, demolished venues excluded).
  - Auto-ideas from coverage gaps; "new" badges (pipeline-side); a 60-day openings window.
- **Merged the adapters branch:** 10 cities, plus arcgis/ckan/bibliocommons/trumba/simpleview/communico.

**Broke:**
- **Axe found real WCAG AA failures:** button contrast (white on #ff5a36 is about 3:1), category-label contrast, calendar ARIA grid without rows, aria-label on a div. All fixed at the token level (`--btn`, `--cat-l`), not suppressed.
- **The contract test caught stale demo exports** after schema bumps. The demo is now a generated, gitignored artifact (`make demo`).
- **Openings dated in the past were silently dropped by build** (found by the adapter agent). Now visible for 60 days.

**Decided (and why):**
- **ArcGIS skips the robots check, like Socrata (the agent's call; I agree).** It's a documented public REST API. `services*.arcgis.com/robots.txt` returns 403 "Invalid URL", which reflects the host setup, not a crawl policy.
- **LeagueLab sites are curated with `watch: false`.** Their terms forbid automated access, so we don't page-watch them.
- **Starter-pack due dates are computed client-side** from the user's move date. That keeps personal data on the device.

**Verified:**
- Screenshots of home, feed, drawer, map, plan, deadlines and the waves timeline (desktop + 390px mobile).
- 24 Playwright tests (smoke + axe) on desktop and mobile; 175 pytest; 15 vitest.
- Full live run of all 10 cities in progress.

**Next:** finish the full live run and check every city in the browser. Merge the Volo/volunteer/cons branch and the starter-pack data. Watch payload size for NYC.
- 2026-10-16 05:06 UTC · run 5 ok: units[25 disabled, 35 ok, 2 skipped] → 8032 events in 10 cities
- 2026-10-16 05:15 UTC · run 6 ok: units[1 ok] → 1751 events in 1 cities
- 2026-10-16 05:16 UTC · run 7 ok: units[1 ok] → 1751 events in 1 cities
- 2026-10-16 05:16 UTC · run 8 ok: units[1 ok] → 1751 events in 1 cities
- 2026-10-16 05:17 UTC · run 9 ok: units[1 ok] → 1719 events in 1 cities

## 2026-10-16 05:30 UTC: leagues, volunteer and niche adapters (volo, handsonconnect, galaxydigital, upcomingcons, makerfaire, Luma ICS)
**Did:** Five adapters with real-fixture tests: `volo` (league discovery pages), `handsonconnect` (POST calendar JSON, 1–3 day windows), `galaxydigital` (RSS discovery + need detail pages), `upcomingcons` (schema.org microdata, global source filtered per city), `makerfaire` (global map JSON, distance filter). `PoliteClient.post` shares retry/throttle/robots/redaction with `get`. 13 Luma calendars via the existing `ics` adapter. Entries for cities not yet in this branch went to `config/pending_sources/<city>.yaml`; rows for SOURCES.md are in `docs/sources_additions.md`.
**Broke:** (1) `httpx.URL(url, params={})` silently dropped `?query` strings — every Luma ICS URL and the Maker Faire URL were fetched without their query. Fixed in PoliteClient (merge, don't replace) with a test. (2) PoliteClient kept cookies: Volo and Galaxy Digital redirect cookie-carrying requests to a remembered view, which dropped `?page=N` and turned detail pages into the listing. The client now never stores cookies. (3) HOC day entries carry campaign banners in `events`; they were rejected as records until skipped.
**Decided (and why):** Year-less Volo dates → next occurrence on/after the fetch date in the city tz, weekday-checked, and deadlines never after the first game (else they're last year's). HOC "0 still needed" → `waitlist` (the opportunity page says "Currently full … Add to Waiting list"). Galaxy "ongoing" needs → a recurring all-day record for the fetch day ("listed as open today"), "Until X" → end + `closes_at` (extracted); nothing invented. UpcomingCons is one global source; category comes from the con name or the generic `niche` parent, because the site's category pages returned the wrong lists. Maker Faire ships disabled: Cloudflare 403-challenges our client although robots allows it; we don't work around challenges.
**Verified:** live runs, 0 rejects everywhere: Volo BOS 91 / DEN 98 / LA 47 / MIA 17 / NYC 123 (matching each page's "N ways to play"); Boston Cares 541, Hands On Nashville 405, L.A. Works 244, NYC Service 168, UW Austin 0 (empty calendar); HandsOn Twin Cities 35, UWKC 15; UpcomingCons MPLS 3, CHI 2, LA 2, BOS 1, SEA 1; Luma 1–22 per calendar. `gotc build` + contract tests pass. Dashboard not screenshotted in this pass.
**Next:** merge pending sources into the city files; ask Make: and the Galaxy tenants for access/keys.  **Ideas:** I-046..I-052 added.

_Note (merge): idea ids in the entry above were renumbered on merge (see ledger titles)._
- 2026-10-16 05:44 UTC · run 10 ok: units[35 disabled, 35 ok, 39 skipped] → 9837 events in 10 cities
- 2026-10-16 05:48 UTC · run 11 ok: units[1 ok] → 1385 events in 1 cities
- 2026-10-16 05:48 UTC · run 12 ok: units[1 ok] → 658 events in 1 cities
- 2026-10-16 05:48 UTC · run 13 ok: units[1 ok] → 589 events in 1 cities
- 2026-10-16 05:48 UTC · run 14 ok: units[1 ok] → 300 events in 1 cities
- 2026-10-16 05:48 UTC · run 15 ok: units[1 ok] → 779 events in 1 cities
- 2026-10-16 05:49 UTC · run 16 ok: units[1 ok] → 658 events in 1 cities
