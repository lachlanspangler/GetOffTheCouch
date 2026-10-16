-- 001: initial schema. Never edit an applied migration; add a new numbered file instead.

-- Every HTTP payload we parsed, kept for replay/debugging (bodies live gzipped under data/raw/).
CREATE TABLE raw_fetches (
  id            INTEGER PRIMARY KEY,
  run_id        INTEGER,
  unit          TEXT NOT NULL,          -- "<source_id>@<city>"
  source_id     TEXT NOT NULL,
  city          TEXT NOT NULL,
  url           TEXT NOT NULL,          -- secrets redacted
  fetched_at    TEXT NOT NULL,          -- ISO-8601 UTC
  status        INTEGER NOT NULL,
  content_hash  TEXT NOT NULL,
  path          TEXT NOT NULL,          -- relative to data/raw
  bytes         INTEGER NOT NULL,
  elapsed_ms    INTEGER,
  from_cache    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX raw_fetches_unit ON raw_fetches(unit, fetched_at);

-- Each source's normalized view of each record (SourceEvent JSON), upserted per fetch.
CREATE TABLE source_records (
  source_id     TEXT NOT NULL,
  record_id     TEXT NOT NULL,
  city          TEXT NOT NULL,
  unit          TEXT NOT NULL,
  data          TEXT NOT NULL,          -- SourceEvent JSON
  content_hash  TEXT NOT NULL,          -- of data, to detect changes
  raw_fetch_id  INTEGER REFERENCES raw_fetches(id),
  start_at      TEXT NOT NULL,          -- UTC ISO, for windowing
  first_seen    TEXT NOT NULL,
  last_seen     TEXT NOT NULL,
  gone_at       TEXT,                   -- set when a complete snapshot no longer contains the record
  PRIMARY KEY (source_id, record_id, city)
);
CREATE INDEX source_records_city ON source_records(city, start_at);

-- Records that failed schema validation (drift detection + debugging). Pruned by retention.
CREATE TABLE rejects (
  id            INTEGER PRIMARY KEY,
  unit          TEXT NOT NULL,
  raw_fetch_id  INTEGER,
  at            TEXT NOT NULL,
  record_hint   TEXT,
  error         TEXT NOT NULL
);
CREATE INDEX rejects_unit ON rejects(unit, at);

-- Canonical (deduplicated, enriched) events.
CREATE TABLE events (
  id            TEXT PRIMARY KEY,
  city          TEXT NOT NULL,
  data          TEXT NOT NULL,          -- Event JSON
  start_at      TEXT NOT NULL,
  category      TEXT NOT NULL,
  first_seen    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX events_city_start ON events(city, start_at);

CREATE TABLE event_members (
  event_id      TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  source_id     TEXT NOT NULL,
  record_id     TEXT NOT NULL,
  city          TEXT NOT NULL,
  match_score   REAL NOT NULL,
  PRIMARY KEY (source_id, record_id, city)
);
CREATE INDEX event_members_event ON event_members(event_id);

CREATE TABLE venues (
  id            TEXT PRIMARY KEY,
  city          TEXT NOT NULL,
  name          TEXT NOT NULL,
  norm_name     TEXT NOT NULL,
  address       TEXT,
  lat           REAL,
  lon           REAL,
  capacity      INTEGER,
  capacity_source TEXT,
  url           TEXT,
  updated_at    TEXT NOT NULL
);
CREATE INDEX venues_city_norm ON venues(city, norm_name);

-- Time series for "price trend" and "selling fast".
CREATE TABLE price_snapshots (
  source_id     TEXT NOT NULL,
  record_id     TEXT NOT NULL,
  city          TEXT NOT NULL,
  seller        TEXT NOT NULL,
  observed_at   TEXT NOT NULL,
  price_min     REAL,
  price_max     REAL,
  listing_count INTEGER,
  availability  TEXT,
  PRIMARY KEY (source_id, record_id, city, seller, observed_at)
);

CREATE TABLE geocode_cache (
  query         TEXT PRIMARY KEY,
  lat           REAL,
  lon           REAL,
  matched       TEXT,
  provider      TEXT NOT NULL,
  confidence    REAL,
  looked_up_at  TEXT NOT NULL
);

-- Scheduler: runs and their per-unit progress (a crashed run is resumed by simply running again).
CREATE TABLE runs (
  id            INTEGER PRIMARY KEY,
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  status        TEXT NOT NULL,          -- running | ok | partial | failed
  trigger       TEXT,
  summary       TEXT
);

CREATE TABLE run_units (
  run_id        INTEGER NOT NULL REFERENCES runs(id),
  unit          TEXT NOT NULL,
  status        TEXT NOT NULL,          -- ok | failed | skipped
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  fetched       INTEGER DEFAULT 0,
  valid         INTEGER DEFAULT 0,
  rejected      INTEGER DEFAULT 0,
  error_kind    TEXT,
  error         TEXT,
  PRIMARY KEY (run_id, unit)
);

-- Health state machine per unit (see gotc/health/state.py).
CREATE TABLE unit_health (
  unit                 TEXT PRIMARY KEY,
  source_id            TEXT NOT NULL,
  city                 TEXT NOT NULL,
  state                TEXT NOT NULL,   -- healthy | degraded | quarantined | recovering | disabled
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  consecutive_successes INTEGER NOT NULL DEFAULT 0,
  last_attempt_at      TEXT,
  last_success_at      TEXT,
  last_failure_at      TEXT,
  last_error_kind      TEXT,
  last_error           TEXT,
  next_due_at          TEXT,
  last_count           INTEGER,
  baseline_count       REAL,            -- EWMA of successful record counts
  cursor               TEXT,            -- adapter-defined incremental cursor
  reason               TEXT
);

-- Append-only log of every health transition / failure. Failures are never silent.
CREATE TABLE health_log (
  id            INTEGER PRIMARY KEY,
  at            TEXT NOT NULL,
  unit          TEXT NOT NULL,
  level         TEXT NOT NULL,          -- info | warn | error
  kind          TEXT NOT NULL,          -- failure class or transition name
  message       TEXT NOT NULL
);
CREATE INDEX health_log_unit ON health_log(unit, at);
