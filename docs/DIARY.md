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
