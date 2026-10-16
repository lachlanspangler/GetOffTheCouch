# Status

## Milestone summary: 2026-10-16 (session 1, ~6 hours from an empty folder)

**Done:**
- **End-to-end pipeline.**
  - Polite fetch → raw store → normalize → dedup → enrich → export → dashboard.
  - Self-healing health per source × city.
  - Hourly CI refresh to GitHub Pages.
  - Real data flows for Minneapolis: Parks + curated registry, verified live.
- **Dashboard.** Feed, deadlines, calendar, map, new-in-town plan, saved and health views, plus an event drawer with price comparison and provenance. Demo mode is clearly labeled.
- **Engineering.**
  - ruff + mypy --strict clean.
  - ~110 Python tests (unit, recorded-fixture adapters, contract, end-to-end self-healing).
  - 15 vitest + 14 Playwright smoke tests (desktop + mobile).
  - CI workflow and pre-commit hooks.

**Real vs. stubbed**

| Area | State |
|---|---|
| Minneapolis Park & Rec events (Tribe REST) | ✅ real, live |
| Curated registry (curling leagues, run clubs, cons) | ✅ real. Quotes re-verified against the live pages every run. MSP, Boston, Austin, Nashville, Seattle, LA |
| NWS weather on outdoor events | ✅ real, live |
| Census/Nominatim geocoding | ✅ real, cached |
| New-resident starter pack (license/vehicle/voting deadlines) | ✅ pipeline + UI done. State data being researched (agent running) |
| Ticketmaster (face value) | 🟡 adapter + tests done; **needs `TICKETMASTER_API_KEY`** |
| SeatGeek (resale, listings, trends) | 🟡 adapter + tests done; **needs `SEATGEEK_CLIENT_ID`** |
| % tickets left / selling fast / price trend | 🟡 implemented on snapshots. Real signal arrives with SeatGeek/TM keys |
| Other 9 cities' open data, libraries, universities, openings (liquor licenses) | 🔄 agent building (Socrata/ArcGIS/BiblioCommons/Trumba/CKAN) |
| Volo leagues, HandsOn/Galaxy volunteering, UpcomingCons, Maker Faire | 🔄 agent building |
| Meetup, Eventbrite (per-organizer) | ⏸ need OAuth/token (see below) |

## Keys needed (only you can get these)
| Key | Unlocks | How | Cost |
|---|---|---|---|
| `TICKETMASTER_API_KEY` | concerts, sports and theater for all cities; face-value prices; on-sale dates | https://developer-acct.ticketmaster.com/user/register (instant) | free |
| `SEATGEEK_CLIENT_ID` | resale prices, listing counts, so "selling fast" and price trends become real | https://seatgeek.com/account/develop (portal login) | free |
| `SOCRATA_APP_TOKEN` (optional) | higher rate limits on city open-data portals | https://dev.socrata.com/register | free |
| Ticketmaster Inventory Status API (optional) | first-party "few tickets left" | email devportalinquiry@ticketmaster.com | approval |
| Meetup OAuth client (later) | run clubs, social groups, real RSVP counts | https://www.meetup.com/api/oauth/list/ | may need Pro |

Put keys in `.env` locally, and in repo **Settings → Secrets → Actions** for the hourly refresh.

**Before the first push:**
1. Enable Pages (Settings → Pages → Source: GitHub Actions).
2. Set Actions → Workflow permissions to "Read and write".

## Outreach that would unlock more data (from research)
- **Permission:**
  - LeagueLab (Nashville Sports Leagues, Underdog Seattle): the best deadline data found, but their terms forbid automation without permission.
  - Trivia Mafia: locator API.
- **Per-org API keys:**
  - LeagueApps: Chicago Sport & Social, Boston Ski & Sports Club, CLUBWAKA Minneapolis.
  - Galaxy Digital: HandsOn Twin Cities, United Way King County.
- **Partner feed:** Volo (official). We'd be using their public pages until then.
- **Paid API quote:** Idealist (VolunteerMatch).

## What works (detail)
- **Pipeline.** `gotc run` is hourly-safe: units that aren't due skip in microseconds, and each unit commits in its own transaction, so it's resumable.
- **Health.** Healthy → degraded → quarantined (3 strikes, exponential probe backoff) → recovering → healthy. Schema drift, empty results and volume drops are detected on HTTP 200s. Last-known-good keeps serving, marked stale with a reason. Failures surface in HEALTH.md, `health.json`, the in-app Health page, the diary, and auto-opened GitHub issues.
- **Dedup.** Cross-source clustering with sticky ids. One card keeps every seller's price.
- **Estimates.** Attendance bands, social score and ticket signals each carry a method and confidence. See docs/METHODOLOGY.md.
- **Recommendations.** Explainable scoring plus a first-30-days plan. Weather-aware, deadline-aware, diverse.
- **Exports.** Calendar export (.ics) with deadline alarms, shareable URLs, saved events, "new this week" badges, and report-a-problem links.

## Known gaps / next
1. Merge the two adapter branches (9 more cities, openings, leagues, volunteering), then run all cities live.
2. Minneapolis has **no registration deadlines yet**. Library registration (BiblioCommons) and HandsOn Twin Cities should fix that.
3. Venue capacity registry (Wikidata P1083) for better attendance bands.
4. "Leagues registering now" wave timeline; neighborhood vibe cards.
5. Push notifications or email reminders would need a backend. .ics alarms cover it for now.

See `python -m gotc.ideas next` for the ranked backlog.
