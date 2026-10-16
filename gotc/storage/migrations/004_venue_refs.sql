-- 004: reference venue capacities (Wikidata P1083), refreshed weekly per city
CREATE TABLE venue_refs (
  city          TEXT NOT NULL,
  ref_id        TEXT NOT NULL,      -- e.g. "wikidata:Q7103968"
  name          TEXT NOT NULL,
  capacity      INTEGER NOT NULL,
  lat           REAL,
  lon           REAL,
  fetched_at    TEXT NOT NULL,
  PRIMARY KEY (city, ref_id)
);
