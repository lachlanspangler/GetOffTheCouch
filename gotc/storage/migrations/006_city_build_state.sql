-- 006: per-city build/export input hashes (incremental builds, SCALING.md §4.6 item 4; gotc/pipeline/incremental.py)
CREATE TABLE city_build_state (
  city           TEXT PRIMARY KEY,
  inputs_hash    TEXT NOT NULL,      -- records + config + taxonomy + caches feeding build_city, at the last build
  built_at       TEXT NOT NULL,
  feed_hash      TEXT                -- exported card feed hash (generated_at excluded) at the last export
);
