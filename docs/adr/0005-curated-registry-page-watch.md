# ADR-0005: Curated facts carry verbatim evidence and verify themselves

**Status:** accepted · 2026-10-16

## Context
The highest-value data for newcomers has no API:
- league seasons
- con and faire dates
- run-club schedules
- state new-resident rules

Hand-curated data rots silently, and an agent typing dates "from memory" would be fabrication.

## Decision
- **Evidence is required.** Every curated entry (`config/registry/*.yaml`, `config/starter_pack/*.yaml`) must carry `evidence` (a verbatim quote, with "..." between excerpts), `source_url` and `verified_at`. The schema rejects entries without them.
- **Page-watch re-checks every run.** It re-fetches the source page (robots-aware) and checks every quote fragment is still present. The comparison uses alphanumerics only, so markup, whitespace, quotes and drop-caps don't cause false alarms.
  - **Still present:** the entry counts as re-verified now (`fetched_at = now`).
  - **Missing:** the card says "the organizer's page changed", confidence drops, and freshness freezes at `verified_at`, so the entry goes stale on schedule.
  - **Blocked (403/Cloudflare):** the entry is "unchecked" and ages normally. We never work around blocks.
- **ToS beats page-watch.** Sites whose terms forbid automation (LeagueLab) get `watch: false`. They're manual re-verification only.

## Consequences
- **Curation is cheap to keep honest.** Staleness happens automatically.
- **Quotes must be specific enough to fail when the facts change.** "Registration is open now" is weaker than a date.
