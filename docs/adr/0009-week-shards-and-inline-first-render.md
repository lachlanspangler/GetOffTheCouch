# ADR-0009: Week-sharded city data and exact inline first-render data

**Status:** accepted · 2026-10-27 (I-117)

## Decision
- **Shards next to the legacy file.** `export.py` keeps writing `cities/<slug>.json` + `.details.json` unchanged (contract tests, older clients, external users). It also writes `cities/<slug>/manifest.json` (schema `CityManifest`, 1.7.0) plus content-hashed card and details shards: `meta.<hash>.json` (the CityFeed with `events: []`), `w/<key>.<hash>.json` and `d/<key>.<hash>.json`.
- **Every card is in exactly one shard**, by the ISO week it starts in, in the city's timezone: `ongoing` (started before the current week, still running), `deadlines` (starts after next week but has an upcoming registration date), one shard per week for 12 weeks, `openings` (license signals, whose date is a filing date), `later`, and `past-<week>` (already over). A week with more than 400 cards splits into `<key>.2`, `<key>.3`… so no shard passes the 150 KB gzip budget. Files no longer in the manifest are deleted.
- **Only the manifest is unhashed.** The client fetches it with `cache: "no-cache"` (a cheap 304) and the shards with the default cache, so Pages' `max-age=600` can't serve a stale shard after a deploy. A shard 404 (a deploy between the two fetches) reloads the manifest once and starts over.
- **Load order.** `data.ts` loads meta + `ongoing` + `deadlines` + this week and next first, then the rest in idle time (skipped with `Save-Data`). Filters that reach further ("Next 30 days", Everything, the calendar) load the weeks they need on demand; past weeks load only for saved items and ended events' pages. No manifest → the legacy file.
- **Inline first-render data.** A pre-rendered page carries `<script type="application/json" id="gotc-initial">` with only the events it shows (list rows slimmed to fields the rows use) and the whole-feed values it computed: counts, picks, the rows of each list. Views compute those through `memo()` (`lib/partial.ts`): recorded on the server, replayed while the browser hydrates from the partial feed on the same route. The pre-renderer re-renders every page from its inline data and inlines it **only if the HTML is byte-for-byte identical**; otherwise the page hydrates from the full feed as before. While the inline feed is shown the app keeps the server's clock, and on any other route it waits for real data.

## Why
The whole city file (450 KB gzip for NYC) had to download and parse before a pre-rendered page could hydrate, and before a client-rendered page could show anything. A byte-for-byte check at build time is the only way to be sure a partial dataset can't change what the page says, so "exact or not at all" is the rule.

## Consequences
- Pages grow by their inline data (median 2 KB gzip; up to ~20 KB on a city page) and `dist/data` roughly doubles (legacy + shards). Drop the legacy files once nothing reads them, and the dist size halves again.
- Code that renders a whole-feed number on a pre-rendered page must go through `memo()`. If it doesn't, the build still produces a correct site; that page just stops getting inline data (the pre-render summary counts these as "hydrate from the full feed").
