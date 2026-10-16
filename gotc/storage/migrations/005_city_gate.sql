-- 005: go-live gate state per city (gotc/pipeline/gate.py, ADR-0008). Transitions are logged to health_log
-- as unit "gate@<city>".
CREATE TABLE city_gate (
  city           TEXT PRIMARY KEY,
  tier           TEXT NOT NULL,      -- live | beta | hidden
  since          TEXT NOT NULL,      -- when the current tier started
  failing_since  TEXT,               -- first evaluation of the current hard-failure streak (NULL = passing)
  evaluated_at   TEXT NOT NULL,
  data           TEXT NOT NULL       -- the last CityCoverage JSON
);
