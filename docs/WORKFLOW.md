# Workflow: the loop

GetOffTheCouch is built and kept alive by one loop. Humans and agents run the same steps, and every step leaves a written trail.

```
 ┌──► 0 TRIAGE ─► 1 PICK ─► 2 PLAN ─► 3 BUILD ─► 4 TEST ─► 5 VERIFY ─► 6 RECORD ─► 7 IDEATE ─┐
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Step | What you do | Command / file | Done when |
|---|---|---|---|
| **0 Triage** | Check health first. A 🔴 quarantined or 🟠 degraded unit beats any feature. | `make doctor` → `docs/HEALTH.md` | Every red/orange unit is fixed or has an open idea explaining why it can't be fixed yet |
| **1 Pick** | Take the highest-score open idea. Health fixes are implicitly score ∞. Skip ideas that are `blocked` on the user. | `python -m gotc.ideas next` | `python -m gotc.ideas set I-NNN doing` |
| **2 Plan** | Write 3–6 lines: the smallest change that delivers the idea, how you'll test it, and how you'll see it in the app. Big or irreversible decisions get an ADR. | diary draft, `docs/adr/` | You can name the test and the screen you'll check |
| **3 Build** | Make the change. Keep the layers separate: adapters → pipeline → export → web. Schema change? Bump `SCHEMA_VERSION`, then `make schema`. | code | — |
| **4 Test** | Unit tests for the logic. Fixture tests for adapters (`gotc record` first). Contract tests for exports. Fix root causes, never symptoms. | `make check` | Green |
| **5 Verify** | Run the real thing. `make pipeline` (live) or `make build` (offline), then `make dev`. Look at the actual screen with a Playwright screenshot. Check the numbers against the source website. | `make pipeline`, `make dev` | You saw it working with real data. Describe what you saw |
| **6 Record** | Diary entry (append at the bottom), mark the idea done, update STATUS.md if the state changed, then commit with the idea id. | `docs/DIARY.md`, `python -m gotc.ideas set I-NNN done --note …`, `git commit -m "I-NNN: …"` | Committed |
| **7 Ideate** | Add **at least 3** new ideas (features, sources, cities, data-quality tricks, UX polish). Look at what was hard, what the data showed, what a newcomer would want next. Reject bad ones with reasons. | `python -m gotc.ideas add …` | Ledger grew |

Then go back to 0. Never wait for the user. If you're truly blocked on something only they can give you (an API key, a paid account, a login), set the idea to `blocked`, list it under **Keys needed** in STATUS.md, stub it so the rest works without it, and take the next idea.

## The self-healing loop (runs unattended)

`make loop` (= `scripts/loop.sh`) runs hourly in GitHub Actions (`.github/workflows/refresh.yml`) and can also run locally from cron:

1. `gotc doctor --fix`: integrity check, probe quarantined units whose backoff has expired, prune retention, rebuild missing or invalid exports.
2. `gotc run`: fetch every **due** unit (cadence per data type, see `config/sources.yaml`), then build, export and regenerate HEALTH.md.
3. `pytest tests/contract`: the fresh export must validate against the schema.
4. On failure: heal once more and retry (**two-strike rule**). If it fails again, stop, append a FAILED line to the diary and exit non-zero so CI shows red. Don't patch around a failure twice.

### How a broken source is handled (failures are never silent)
| Symptom | Detected by | What happens automatically | What you do on the next loop |
|---|---|---|---|
| HTTP 403/404/5xx, timeout | `PoliteClient` typed errors | unit → degraded; retried within the hour; 3rd consecutive failure → **quarantined**, probed with exponential backoff (≤3 days) | 403: check robots/ToS. 404: find the moved endpoint. 5xx: usually self-heals |
| Schema drift (fields renamed) | >50% of records fail `SourceEvent` validation | treated as a failure; valid records kept; nothing marked gone | read `rejects` and the latest raw payload, fix the parser, run `gotc replay <unit>`, add a regression fixture |
| Empty results / layout changed | 0 valid records where `expect_min_records` > 0 | failure; last-known-good kept | inspect the raw payload; fix the adapter or config |
| Volume drop | < 30% of the EWMA baseline | **degraded**; data kept; **no deletions** this run | check whether it's real (season ended) or breakage |
| robots.txt now disallows | `RobotsDisallowed` | failure → quarantine | disable the source in config and document it in SOURCES.md. Never work around it |
| Missing API key | `requires:` in config | unit **disabled** with reason "needs KEY", shown on the Health page | add the key to STATUS.md "Keys needed" |
| Data older than SLA | export freshness check | events marked `stale` with a reason; the UI shows a stale badge | fix the unit |

Every one of these writes a row to `health_log`, shows up in `docs/HEALTH.md`, `web/public/data/health.json` and the in-app Health page, and is summarized in the diary's automated lines.

## Recipes

**Add a city.**
1. Copy `config/cities/minneapolis.yaml` to `<slug>.yaml`. Set tz, center, radius and neighborhoods.
2. Add city-specific sources. Look for Socrata/ArcGIS datasets, Tribe/Localist/LiveWhale/ICS calendars, library systems and liquor-license data (see `docs/research/`).
3. Run `gotc sources`, then `gotc run --city <slug>`, then `make dev`.
4. Global sources (Ticketmaster, SeatGeek) apply automatically.

**Add a source on a supported platform.** Add a YAML entry with `adapter: tribe|localist|livewhale|ics|socrata`, plus params. Run `gotc run --city X --source Y --force`, check HEALTH.md, then `gotc record <unit> --trim 5` and add a fixture test.

**Add a new adapter.**
1. Add `gotc/adapters/<family>.py` with `fetch` (network only) and `parse` (pure), and register it in `adapters/all.py`.
2. Record a fixture, write `tests/adapters/test_<family>.py`, and add the source to `docs/SOURCES.md` with its ToS/robots stance.

**Fix a quarantined unit.**
1. Run `gotc status`, then look at `rejects` and the latest `data/raw/<source>/<date>/…` payload.
2. Fix the parser or config, then run `gotc replay <unit>` and `gotc run --source <id> --force`.
3. Add a regression fixture.

**Add a curated league/con.** Add an entry to `config/registry/<city>/<kind>.yaml` with `url`, `verified_at` and an `evidence` quote copied from the page. Never type a date you didn't see on the organizer's page.

## Diary conventions
`docs/DIARY.md` is **append-only and chronological**, with the newest entry at the bottom. (GameCred was newest-first, which made appending error-prone.) Human/agent entries:

```
## 2026-10-15 23:10 UTC: <title>
**Did:** …  **Broke:** …  **Decided (and why):** …  **Verified:** what I saw in the real app  **Next:** …  **Ideas:** I-012 done; I-046, I-047 added
```
Automated lines from `gotc run` and `gotc doctor` are single bullets: `- 2026-10-15 23:00 UTC · run 12 ok: …`.
