-- 003: results of evidence-quote checks for curated facts that aren't events (e.g. starter-pack rules)
CREATE TABLE fact_checks (
  fact_id       TEXT PRIMARY KEY,
  source_url    TEXT NOT NULL,
  checked_at    TEXT NOT NULL,
  status        TEXT NOT NULL   -- evidence_present | page_changed | unchecked
);
