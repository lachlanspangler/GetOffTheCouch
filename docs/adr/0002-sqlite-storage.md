# ADR-0002: SQLite for pipeline storage, gzipped files for raw payloads

**Status:** accepted · 2026-10-15

## Decision
- **One SQLite file** (`data/gotc.db`, WAL mode) holds source records, canonical events, venues, price snapshots, the geocode cache, runs and health.
- **Migrations** are forward-only numbered SQL files in `gotc/storage/migrations/`, applied on open.
- **Raw HTTP bodies** are stored gzipped and content-addressed under `data/raw/<source>/<date>/`, then referenced from `raw_fetches`. Retention is 30 days, but the newest payload per unit is kept forever for replay.

## Why not DuckDB / Postgres
- **Postgres** needs a server.
- **DuckDB** is great for analytics, but the workload here is many small transactional upserts, which SQLite does better. A single file is also easy to cache and restore in CI.

## Consequences
- Each unit commits in its own transaction, so a run that dies halfway is resumed by running again.
- `events` is a derived snapshot. `make build` re-derives it from `source_records` at any time.
