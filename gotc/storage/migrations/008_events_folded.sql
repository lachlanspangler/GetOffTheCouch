-- 008: folded series occurrences (ADR-0009 amendment, build.cap_series). A long run exports only its next 8 dates;
-- the rest are still stored (folded = 1) so their canonical ids stay sticky and old links can be resolved.
ALTER TABLE events ADD COLUMN folded INTEGER NOT NULL DEFAULT 0;
