-- 007: the listing gate's quarantine (ADR-0010, gotc/pipeline/listing_gate.py). Nothing is silently dropped:
-- every listing held back — at ingest (online-only, excluded places, campus-internal) or by the build-time gate —
-- is here with its rule and reason, and counted per source in docs/HEALTH.md.
CREATE TABLE gated_listings (
  city        TEXT NOT NULL,
  source_id   TEXT NOT NULL,
  record_id   TEXT NOT NULL,
  stage       TEXT NOT NULL,          -- 'ingest' (skipped while parsing) | 'build' (the real-public-event gate)
  title       TEXT NOT NULL,
  start_at    TEXT,
  rule        TEXT NOT NULL,          -- rule id, e.g. academic_calendar, closure, ingest:online_only
  family      TEXT NOT NULL,
  reason      TEXT NOT NULL,
  evidence    TEXT,                   -- the matched text
  gated_at    TEXT NOT NULL,
  PRIMARY KEY (city, source_id, record_id, stage)
);
CREATE INDEX gated_listings_source ON gated_listings(source_id, city);
