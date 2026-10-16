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

## 2026-10-16 05:30 UTC: leagues, volunteer and niche adapters (volo, handsonconnect, galaxydigital, upcomingcons, makerfaire, Luma ICS)
**Did:** Five adapters with real-fixture tests: `volo` (league discovery pages), `handsonconnect` (POST calendar JSON, 1–3 day windows), `galaxydigital` (RSS discovery + need detail pages), `upcomingcons` (schema.org microdata, global source filtered per city), `makerfaire` (global map JSON, distance filter). `PoliteClient.post` shares retry/throttle/robots/redaction with `get`. 13 Luma calendars via the existing `ics` adapter. Entries for cities not yet in this branch went to `config/pending_sources/<city>.yaml`; rows for SOURCES.md are in `docs/sources_additions.md`.
**Broke:** (1) `httpx.URL(url, params={})` silently dropped `?query` strings — every Luma ICS URL and the Maker Faire URL were fetched without their query. Fixed in PoliteClient (merge, don't replace) with a test. (2) PoliteClient kept cookies: Volo and Galaxy Digital redirect cookie-carrying requests to a remembered view, which dropped `?page=N` and turned detail pages into the listing. The client now never stores cookies. (3) HOC day entries carry campaign banners in `events`; they were rejected as records until skipped.
**Decided (and why):** Year-less Volo dates → next occurrence on/after the fetch date in the city tz, weekday-checked, and deadlines never after the first game (else they're last year's). HOC "0 still needed" → `waitlist` (the opportunity page says "Currently full … Add to Waiting list"). Galaxy "ongoing" needs → a recurring all-day record for the fetch day ("listed as open today"), "Until X" → end + `closes_at` (extracted); nothing invented. UpcomingCons is one global source; category comes from the con name or the generic `niche` parent, because the site's category pages returned the wrong lists. Maker Faire ships disabled: Cloudflare 403-challenges our client although robots allows it; we don't work around challenges.
**Verified:** live runs, 0 rejects everywhere: Volo BOS 91 / DEN 98 / LA 47 / MIA 17 / NYC 123 (matching each page's "N ways to play"); Boston Cares 541, Hands On Nashville 405, L.A. Works 244, NYC Service 168, UW Austin 0 (empty calendar); HandsOn Twin Cities 35, UWKC 15; UpcomingCons MPLS 3, CHI 2, LA 2, BOS 1, SEA 1; Luma 1–22 per calendar. `gotc build` + contract tests pass. Dashboard not screenshotted in this pass.
**Next:** merge pending sources into the city files; ask Make: and the Galaxy tenants for access/keys.  **Ideas:** I-046..I-052 added.
