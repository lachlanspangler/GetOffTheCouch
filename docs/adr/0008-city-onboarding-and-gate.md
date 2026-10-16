# ADR-0008: City onboarding (discover → draft → gate) and the sharded refresh

**Status:** accepted · 2026-10-16 · design: `docs/research/SCALING.md`

## Decision
- **Onboarding is a pipeline, not a hand search.**
  1. `gotc city new <slug>` writes `config/cities/<slug>.yaml` with `enabled: false`, from the top-50 table
     in `config/metros.yaml` (Census V2024 CBSA ranks). Centers were re-derived with one Census geocoder call
     per city-hall address (`gotc city recenter`). A match is accepted only on the same house number and
     street direction and within 5 km of the table value. Otherwise the row keeps `center_source: scaling_md`.
  2. `gotc discover <slug> --seed kind=URL …` probes open-data catalogs (Socrata, data.gov, ArcGIS Hub →
     org-scoped search), library/university/venue/volunteer platforms and the national leagues/trivia feeds.
     It writes scored candidates to `data/discover/<slug>.yaml` (gitignored), never to config.
  3. A human or agent reviews the candidates, promotes them into the city file, records fixtures and adds the
     SOURCES.md rows.
  4. `gotc gate --city <slug>` decides when `enabled: true` is earned.
- **Politeness is structural.** Every discovery request goes through `PoliteClient` with robots checked first.
  The only exceptions are the documented ones in docs/SOURCES.md (`services*.arcgis.com`). On top of that:
  - a per-run request budget
  - a memo, so no URL is fetched twice per run
  - a ToS denylist (`config/discovery_denylist.yaml`), checked before any request to a host and on every page
  - Cloudflare challenges (including on robots.txt) are a hard exclude for that host, never retried
  - A robots.txt that answers 401/403 means "disallow all" (RFC 9309) and is labeled as such.
  - No Wikidata seeding: its query paths are robots-disallowed.
- **The go-live gate** (`gotc/pipeline/gate.py`) implements SCALING.md §3 G1–G11, with two calibrations so
  the literal rule doesn't block every city:
  - G9 allows max(48 h, 2 × cadence) since a unit's last success.
  - A G10 "green run" means ≤ max(1, 10 %) of the city's attempted units failed.
  It produces a `coverage` block per city: seven pillars (strong/thin/none), strongest pillars, geocode rate,
  top-source share, criteria and human-readable reasons. The block is published in `index.json` and in each
  city feed (schema 1.5.0, additive).
- **Tiers.**
  - `hidden`: `enabled: false`, never exported.
  - `beta`: enabled but failing a hard criterion. Exported and labeled.
  - `live`: every hard criterion passes.
  - New cities start in beta. Incumbent metros (published before the gate existed) start live.
  - A live city failing a hard criterion shows a banner after 72 h and is demoted after 7 days. A beta city is
    promoted as soon as it passes.
  - Every transition is logged to `health_log` as `gate@<city>` and shown in HEALTH.md.
- **The hourly refresh is sharded.** `prepare` pins the state commit and plans shards (`gotc shards`).
  - The shard jobs fetch disjoint cities and upload delta DBs (`gotc state delta`).
  - One `publish` job merges them (`gotc state merge`, ids remapped, mismatched bases refused), then builds,
    exports, deploys Pages and persists state once.
  - The single `gotc.db.gz` state format is unchanged, so the monolithic workflow stays a working fallback.
- **Incremental builds/exports.** A city is rebuilt only when a hash of its records, config, taxonomy, curated
  files and build caches changed, its build is > 3 h old, or its events are slim CI placeholders. Unchanged
  feeds aren't rewritten.

## Why
Ten cities were built by hand, about 20 units each. Fifty or a hundred can't be. Discovery has to be
repeatable, evidence-carrying and polite by construction: the research session's two robots slips happened
because the robots check was a step someone had to remember. And without an honest bar, thin cities would
quietly look sparse instead of saying "we have no license data here".

Sharding is what keeps the hourly wall time near 10 minutes at 100 cities (SCALING.md §4.4). Deltas over a
shared base let us shard without first splitting the state into per-city files (§4.6 item 2), which is still
the follow-up.

## Consequences
- The UI must render `coverage` (Live/Beta chip, pillar strip, coverage page). Until then, beta cities look
  like live ones. The web redesign owns that.
- In CI, slim state means every city is still rebuilt every hour, so incremental builds pay off locally and
  only once state keeps `events.data` per city (per-city state files).
- Each delta carries all `source_records` of its cities: 12 MB raw, 1.7 MB gz for NYC + Boston today. That is fine for
  1-day artifacts. Per-city state files will shrink it.
- Gate thresholds are product decisions in code (`gate.py`). Change them there and note it in the diary. The
  tests pin the calibration.
- Discovery's recall is unmeasured until it's backtested on the ten live cities (idea in the ledger).
