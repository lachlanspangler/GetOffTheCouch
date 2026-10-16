# Status

## Milestone summary: 2026-10-16 (end of session 1, about 9 hours from an empty folder)

**What's real today.**
- **Volume:** ~9,800 live events across all 10 seed cities from 70+ healthy source×city units. Every unit runs through the self-healing pipeline, with no API keys at all.
- **Sources:**
  - parks and city open data (Socrata/ArcGIS/CKAN)
  - libraries (BiblioCommons/Communico/Trumba)
  - universities (Localist/LiveWhale), filtered to public events
  - Volo leagues
  - HandsOn/Galaxy volunteer shifts, with live "spots left"
  - Chicago Park District adult leagues and classes
  - new bar and restaurant openings from liquor and business licenses
  - UpcomingCons, Luma calendars, and the curated registry (page-watched quotes)
- **Enrichment:** NWS weather, Wikidata venue capacities, and the official new-resident starter pack (34 rules, 10 states).

| City | Events | Healthy sources | Leagues | Volunteer | Published deadlines |
|---|---|---|---|---|---|
| Austin | 631 | 8/8 (+4 need keys/blocked) | 62 | 5 | 17 |
| Boston | 1,385 | 8/8 (+6 need keys/blocked) | 99 | 542 | 91 |
| Chicago | 1,722 | 10/10 (+3 need keys/blocked) | 66 | 7 | 0 |
| Denver | 201 | 5/5 (+4 need keys/blocked) | 98 | 0 | 98 |
| Los Angeles | 779 | 8/8 (+3 need keys/blocked) | 48 | 225 | 50 |
| Miami | 773 | 6/6 (+3 need keys/blocked) | 17 | 7 | 17 |
| Minneapolis | 518 | 11/11 (+3 need keys/blocked) | 6 | 95 | 3 |
| Nashville | 589 | 5/5 (+3 need keys/blocked) | 7 | 406 | 1 |
| New York City | 2,914 | 11/11 (+3 need keys/blocked) | 149 | 220 | 122 |
| Seattle | 300 | 7/7 (+3 need keys/blocked) | 1 | 21 | 8 |

**Engineering.**
- ruff and mypy --strict are clean.
- ~220 pytest (unit, recorded-fixture adapter tests for 20+ adapters, contract, end-to-end self-healing scenarios).
- 17 vitest; 24 Playwright tests (smoke + axe WCAG AA) on desktop and mobile.
- CI workflow plus an hourly refresh workflow → GitHub Pages, with state persisted on an orphan branch.

**Real vs. stubbed**

| Area | State |
|---|---|
| Open data, libraries, universities, parks, Volo, volunteering, cons, Luma, curated registry | ✅ real and live |
| Openings (new liquor/business licenses) | ✅ real: NYC (SLA pending + new), Chicago, Austin (TABC), Denver, Seattle, LA, Nashville. Miami and Boston: no keyless source yet |
| Spots left / "% left" | ✅ real where sources report it (libraries, HandsOn shifts). Labeled estimates elsewhere |
| Weather, venue capacities, starter pack | ✅ real |
| Ticketmaster (concerts/sports/theater, face value) | 🟡 adapter + tests ready, **needs `TICKETMASTER_API_KEY`** |
| SeatGeek (resale prices, listing trends, selling fast) | 🟡 adapter + tests ready, **needs `SEATGEEK_CLIENT_ID`** |
| Meetup, Eventbrite per-organizer | ⏸ need OAuth/token |
| Visit Austin/Denver, Meet Boston (Simpleview); Maker Faire | ⏸ adapters done; blocked by CDN bot protection (we don't work around it) |

**Thin spots to fix next:**
1. Concerts: there's almost no music until the Ticketmaster key arrives.
2. Seattle and Minneapolis leagues: Volo doesn't operate there, and LeagueApps/TeamSideline forbid automation.
3. Denver has no general events source.
4. Geocoding coverage is low in Miami and Seattle, but it fills a bit more every run.

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
- **Exports.** Calendar export (.ics) with deadline alarms, shareable URLs and shared lists, saved events, "new this week" badges, and report-a-problem links.
- **Relevance.** Cancelled events are hidden, not-public university items are skipped (counted), a geofence drops out-of-area events, multi-site programs collapse, and an "Ongoing" section holds exhibits.
- **Operator tools.** `gotc forget <unit>` after a deliberate config change; `gotc replay` after a parser fix; `python -m gotc.autoideas`.

## Next (what I'd build next, in order)
1. **Ticketmaster key → concerts everywhere.** It's the biggest content gap. Then record real fixtures and check cross-seller dedup on live data.
2. **SeatGeek key → real price trends.** This makes "selling fast" and the price trend come from live resale data.
3. **More leagues.** HandsOn/Galaxy tenants and Volo markets (I-076). Outreach to LeagueLab/LeagueApps orgs for permission.
4. **Census batch geocoder** to close the coordinate gap in Miami and Seattle (I-076/batch idea).
5. **Payload split** (cards vs. details) once NYC passes ~8 MB raw.
6. **Email/push reminders.** These need a tiny backend (e.g. a scheduled GitHub Action + Buttondown). .ics alarms cover it today.

Also done this session (no longer gaps): Minneapolis deadlines via library registration and HandsOn Twin Cities, the Wikidata venue capacity registry, the registration-waves timeline, and neighborhood vibes.

See `python -m gotc.ideas next` for the ranked backlog.
