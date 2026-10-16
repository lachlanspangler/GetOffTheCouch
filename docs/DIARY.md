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
