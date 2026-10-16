# ADR-0004: Health is per (source × city) unit, judged on content as well as HTTP status

**Status:** accepted · 2026-10-16

## Context
Sources break in ways HTTP status codes don't show: fields get renamed, layouts change, lists come back empty, or a feed silently halves. A source can also be fine in one city and broken in another (Volo Boston vs. Volo Miami).

## Decision
- **The unit of health is `source_id@city`.** It has a pure state machine (`gotc/health/state.py`): healthy → degraded → quarantined (3rd consecutive failure; probe with exponential backoff up to 3 days) → recovering (2 successes) → healthy.
- **Successful fetches are judged on content too:**
  - schema drift: more than 50% rejects in a batch of 5 or more
  - empty results: 0 valid where `expect_min_records > 0`
  - volume drop: below 30% of the EWMA baseline
- **Destructive actions need trusted snapshots.** Records are marked gone only after a *complete, healthy, non-dropped* snapshot.
- **Last-known-good keeps serving.** Staleness is decided per event from its freshest member versus that source's SLA. Stale events are shown with a reason, never hidden.
- **Every transition writes to `health_log`.** That log feeds HEALTH.md, `health.json`, the in-app Health page, the diary, and GitHub issues.

## Consequences
- **Deliberate config changes can look like breakage** (128 → 9 records). `gotc forget <unit>` is the operator escape hatch.
- **Thresholds are global constants** for now. Per-source overrides are an open idea.
