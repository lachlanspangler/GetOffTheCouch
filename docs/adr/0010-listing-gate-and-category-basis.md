# ADR-0010: A real-public-event gate before publish, and honest category provenance

**Status:** accepted · 2026-11-02

## Context
The live site showed "Fall B: Last day to withdraw from the University with a 25% refund of tuition" as a Miami
**Networking** event, with an expected crowd of ~60 (15–400), a 6/10 meeting-people score and the provenance line
"category: reported by the source (FIU events)". Five things were wrong at once:

1. `fiu_events` (Localist) pulls the whole university calendar, academic dates included.
2. Its `default_category: learning.networking` labelled anything the classifier couldn't place as Networking.
3. Nothing checked whether a listing was something people can go to. The ingest-time campus filter only skips items
   on *complete* fetches; FIU's fetch is capped at 5 pages, so already-stored records were never marked gone.
4. Provenance said "reported by the source" whenever the source sent *any* label. Here the labels were audiences and
   terms, and the category was our config default. That breaks "we never invent data" (ADR-0006).
5. The non-event then got a category-prior crowd estimate and a meeting-people score.

## Decision
1. **Every listing passes a rules gate at build time** (`gotc/pipeline/listing_gate.py`, rules in
   `config/listing_gate.yaml`), after categories are reconciled and before geocoding, clustering and enrichment.
   - **Rule families:** academic calendar · closure · office hours · appointment (incl. proctored testing) · admin
     deadline · governance meeting · internal only · placeholder (incl. "TBD at <team>" slots), plus campus-only rules
     (club meetings, support groups, admissions, career services, academic admin, term-calendar lines, listings
     tagged only for insiders).
   - **Ticketed shows are exempt** from the calendar-word rules (`skip_data_types`). "Night School Final Exam" and
     "Board of Directors" (a band) are shows.
   - **Hard rules** can only be overridden per source (`listing_gate.keep`).
   - **Soft rules** are rescued by `unless` title patterns, or by a sign-up family (leagues, volunteering, races).
     A family only counts when the source reported the category or the source is a league/volunteer source. Our own
     classifier's guess can't talk the gate out of a rule.
2. **Quarantine, never drop.**
   - Held-back listings go to `gated_listings` with the rule, family, reason and matched text.
   - The older ingest-time skips (online-only, excluded places, campus-internal, campus catch-all) are quarantined
     there too, with `stage = 'ingest'`. They travel through the shard deltas; build-stage rows are written by the
     publish build.
   - HEALTH.md has a per-unit "Held back" table, and `SourceStatus.held_back` shows on the Health page.
3. **Category basis on every listing** (`SourceEvent.category_basis`):
   - `source_label` (the source's own label, mapped)
   - `classified` (our keyword classifier or a title rule)
   - `source_kind` (a config default, allowed only for single-kind sources)
   - `fallback` (nothing matched → `other.uncategorized`)
   - `curated`

   **Provenance follows it:**
   - Only `source_label` may say "reported by the source".
   - `classified` says "worked out from the source's data".
   - Config defaults and uncategorized say "set by us, not the source" (`Method.DEFAULTED`), with a note on the
     event page.
   - Organizer and venue filled from config are marked defaulted too.
4. **No catch-all defaults on mixed sources.**
   - University, library, city, tourism, parks, garden, zoo and museum calendars may not set `default_category`.
   - A test enforces it: a mixed source needs `single_kind_reason` in its params to keep one.
   - Records stored under a removed default are re-classified from their own text at build, or left
     uncategorized, so a rebuild fixes old data without refetching.
5. **Uncategorized listings get no category prior.** No crowd band (unless the source reports a count or the venue
   capacity is known) and no meeting-people score. The event page says "Not enough info to estimate".

## Why rules, not a model
Rules are transparent, testable and per-source tunable. Every rejection carries a sentence a person can check. The
golden set (`tests/fixtures/listing_gate/golden.yaml`, ≥200 labelled real listings across metros) measures precision
and recall on every `make check`, so a rule change that starts eating real events fails CI. A learned model can come
later, behind the same `Verdict` interface, once user reports (I-224) give it labelled data.

## Amendments after review (2026-11-02)
- **Retired `campus_uncategorized`** and the ingest-time `campus_catchall` / "other"-family skip. The cold data review
  found about 55% of the uncategorized campus listings they held were real talks, exhibitions and sales. They now
  publish as uncategorized, with no estimates.
- **The campus audience rule** ignores a bare "Students" tag, which campuses also put on public events. It rescues on
  title *or* description (a lecture's title often doesn't say "lecture").
- **Re-derivation is limited to `REMOVED_DEFAULTS`** (`gotc/pipeline/removed_defaults.py`, frozen from 27ba235). The
  first version re-derived any "unexplained" stored category and changed 3,265 correct ones (games, volunteer
  shifts, trivia). Now 0 change outside the 176 sources whose default was removed.

## Consequences
- About 1% of live listings are held back at build. More were already skipped at ingest; those are now visible.
- The volume-drop health check is unaffected: it counts records at ingest, before the gate.
- `BUILD_VERSION` 2 forces one full rebuild. `config/listing_gate.yaml` is part of every city's build inputs hash.
