# GetOffTheCouch: agent operating manual

**"ur city made easy."** A living, auto-updating dashboard for people who just moved to (or are about to move to) a US city. It shows everything worth getting off the couch for, plus every deadline you'd otherwise miss: beer leagues, parties and openings, concerts with live prices, volunteering, cons and faires, trivia, and run clubs.

**It is a pipeline product first and a dashboard second.** Stale or fabricated data is the worst bug.

## Start every session like this
1. `make doctor`, then read `docs/HEALTH.md`. Anything 🔴 or 🟠 comes first.
2. Read the top of `docs/STATUS.md` (milestone summary) and the last ~3 entries of `docs/DIARY.md` (append-only, newest at the bottom).
3. Run `python -m gotc.ideas next` to see the highest-scoring open ideas.
4. Run the loop in `docs/WORKFLOW.md`. Never stop to ask the user something you can decide yourself. Pick the sensible default, write the reason in the diary, and keep going. The only blockers are things only the user can supply (a paid API key, an account). Stub those, document them in STATUS.md under "Keys needed", and move on.

## Non-negotiable rules
1. **Never fabricate data.** Every value is reported, derived, extracted, estimated (with a band and a method) or curated (with a source URL and a `verified_at`). Demo/seed data sets `is_demo: true`. It lives only in `web/public/demo/` and is never mixed into real exports.
2. **Never silently fail.** A broken source must show up in `docs/HEALTH.md`, `web/public/data/health.json`, the dashboard Health page and the diary. Its last-known-good data keeps serving, marked stale once it's older than the SLA.
3. **Respect sources.** Prefer official APIs. Honor robots.txt (`PoliteClient` does this by default) and ToS. Rate-limit, cache and back off. If robots disallows us, disable the source. Never work around it. Record each source's stance in `docs/SOURCES.md`.
4. **Secrets only from env/.env** (gitignored). The template is `.env.example`. URLs are redacted before they're stored.
5. **Schema changes:** edit `gotc/schema.py`, bump `SCHEMA_VERSION` (semver), then run `make schema` to regenerate the JSON Schema and TS types. Contract tests fail if you forget.
6. **Tests never hit the internet.** Adapter tests use recorded fixtures in `tests/fixtures/<source_id>/`, recorded with `gotc record <unit>`. Live checks are marked `@pytest.mark.live`.
7. **Verify, don't assume.** After every feature: `make check`, then `make pipeline` (or `make build` offline), then look at the real dashboard (`make dev`, Playwright screenshot), then write a diary entry with what you saw.
8. **Small commits**, one logical change each. Put the idea id in the message: `I-012: keep sign-up links as offers`. Never push; the user pushes.
9. **Big decisions get an ADR** in `docs/adr/NNNN-title.md`.
10. **Inclusive language** in code and docs (allowlist/denylist, primary/replica).

## Architecture map
```
config/                       ← adding a city or a source = YAML, not code
  cities/<slug>.yaml          city: tz, center, radius, neighborhoods, city-specific sources
  sources.yaml                global sources (Ticketmaster, SeatGeek…) + freshness SLAs per data type
  taxonomy.yaml               category tree (ids), social/attendance priors, keyword rules, tag vocabulary
  venues/<slug>.yaml          curated venue capacities (with capacity_source URLs)
  registry/<slug>/*.yaml      curated, verified leagues/cons/faires (adapter: curated)
gotc/                         Python pipeline (3.12, pydantic v2, httpx, SQLite)
  schema.py                   THE contract: SourceEvent (adapter output) → Event (canonical) → CityFeed (export)
  config.py taxonomy.py settings.py
  http/client.py              PoliteClient: robots, per-host throttle, retries+backoff, conditional GET, redaction
  adapters/                   base.py contract (fetch → payloads, parse → dicts); one module per family
    socrata ics calendars(tribe/localist/livewhale) ticketing(ticketmaster/seatgeek) …
  pipeline/
    ingest.py                 run one unit: fetch → raw store → parse → validate → upsert → health verdict
    build.py                  records → geocode → venues → cluster → merge → deadlines → enrich → events
    resolve.py                entity resolution (venues, events, sticky canonical ids)
    enrich.py                 attendance bands, ticket signals, price trend, tags, social score
    deadlines.py              "register by …" extraction with evidence
    geocode.py                Census → Nominatim, cached forever
    export.py                 events → web/public/data/{index,health}.json + cities/<slug>.json + week shards (ADR-0009)
    run.py                    scheduler: due units → build → export → HEALTH.md
  health/                     state.py (pure state machine) · store.py · report.py (HEALTH.md) · doctor.py
  storage/                    db.py (SQLite + migrations/) · raw.py (gzipped content-addressed payloads)
  ideas.py                    ideas ledger CLI (ledger JSON → IDEAS.md)
web/                          dashboard: Vite + Preact + TypeScript (static; reads web/public/data)
tests/                        unit · adapters (fixtures) · contract · integration · web (vitest + Playwright)
docs/                         WORKFLOW STATUS DIARY IDEAS ideas_ledger.json HEALTH SOURCES METHODOLOGY adr/ research/
```

**Units.** A unit is one (source, city) pair, e.g. `mprb_events@minneapolis`. It is the scheduler's atom of work and the health system's atom of state.

**Data flow.** `source_records` holds each source's latest view of each record. `events` is a full re-derivation (snapshot) built from it. History lives in `raw_fetches` (payloads), `price_snapshots` and `health_log`. A bad build is fixed by fixing code and rebuilding (`make build`). After a parser fix, run `gotc replay <unit>` to re-parse stored payloads without refetching.

## Commands
| | |
|---|---|
| `make setup` | venv + deps + web deps + pre-commit hooks |
| `make check` | lint + format check + mypy + all Python tests + web typecheck/tests (run before every commit) |
| `make pipeline` | `gotc run` for all due units, then build + export + HEALTH.md (live network) |
| `make build` | rebuild + export from the DB, no network |
| `make dev` | dashboard dev server at http://localhost:5173 |
| `make doctor` / `make heal` | health checks / plus safe automatic repairs |
| `make loop` | one non-interactive iteration of the self-healing loop (`scripts/loop.sh`) |
| `gotc sources` | every unit, its cadence and whether it's ready (keys) |
| `gotc record <unit> --trim 5` | record a real fixture for adapter tests |
| `python -m gotc.ideas next` / `add` / `set` / `reject` | the ideas ledger |

## Conventions
- **Python:** ruff (lint + format, line length 110) and mypy --strict on `gotc/`. Datetimes are always timezone-aware. Parse naive source times in the **city's** timezone.
- **Adapters:** `fetch` does network only, `parse` is pure. Yield `{"_reject": reason}` for records you can't use; never drop them silently. Put field mappings in config (Socrata) so a new dataset needs no code.
- **Estimates:** use `Estimate(low, mid, high, method, inputs, confidence)` and round to 2 significant figures.
- **Diary:** append a dated entry at the bottom of `docs/DIARY.md` covering what changed, what broke, what you decided and why. Automated runs append one-line entries.
- **Ideas:** add ideas with `python -m gotc.ideas add`. Record rejected ideas with a reason. Add at least 3 new ideas per loop.
