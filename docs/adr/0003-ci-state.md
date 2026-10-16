# ADR-0003: Where pipeline state lives in CI

**Status:** accepted · 2026-10-15

## Context
GitHub Actions runners are ephemeral, but the pipeline needs memory between runs:
- health state machines and backoff
- `first_seen` and sticky canonical ids
- price/listing snapshots for trends
- the geocode cache
- last-known-good records for quarantined sources

## Decision
- **The SQLite DB** is gzipped and force-pushed as the single commit of an orphan branch, `pipeline-state`, at the end of every run, and restored at the start. Force-pushing keeps the repo from growing without bound, and the DB stays small (MBs).
- **Raw payloads** (`data/raw`) go in the Actions cache. That's best effort: losing them only loses replay ability for older payloads, never live data.
- **Generated dashboard data** is not committed to `main` (no churn). It's built into the Pages artifact every run.

## Consequences
- If the state branch is lost, the next run rebuilds from scratch. We lose price history and first-seen dates, but the product keeps working, so the design degrades gracefully.
- Two concurrent refreshes could race. `concurrency: refresh` with `cancel-in-progress: false` serializes them.
- Moving to a server later only means replacing these two steps with a volume mount.
