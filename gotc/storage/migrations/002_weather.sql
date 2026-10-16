-- 002: cached NWS hourly forecasts per city (refreshed at most every 3h by the build step)
CREATE TABLE weather_cache (
  city          TEXT PRIMARY KEY,
  fetched_at    TEXT NOT NULL,
  data          TEXT NOT NULL      -- JSON list of {start, end, temp_f, precip_pct, short}
);
