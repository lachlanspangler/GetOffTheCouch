# Ideas

_Generated from `docs/ideas_ledger.json` by `python -m gotc.ideas render`. Edit the ledger via the CLI, not this file._

Score = value × confidence ÷ effort. The loop (docs/WORKFLOW.md) always picks the top **open** idea,
unless docs/HEALTH.md has something red.

**open** 20 · **doing** 3 · **done** 36 · **rejected** 7

## Up next (open, by score)

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-038 | City onboarding checklist (DMV, voter registration, library card, transit pass) as deadlines | features | 4 | 2 | 1.6 | doing | Every new resident has the same 10 deadlines; nobody lists them — 2026-10-16 doing: pipeline+UI shipped; state data being researched |
| I-049 | City 'starter pack' deadlines (library card, voter registration, transit pass, DMV 60-day rule) | features | 4 | 2 | 1.6 | doing | Every new resident has the same deadlines; state rules are public — 2026-10-16 doing: pipeline+UI shipped; state data being researched |
| I-020 | Curated league registry (YAML) with verified dates + page-watch to detect changes | sources | 5 | 3 | 1.33 | doing | Beer leagues have no APIs; curated + monitored is the honest path — 2026-10-16 doing: curated adapter + page-watch shipped; Volo adapter in progress |
| I-062 | Ask Simpleview boards (Meet Boston, Visit Austin, Visit Denver) for API access or an allowlisted UA | sources | 4 | 1 | 3.2 | open | Their event APIs return 403 (CDN bot protection) to our client though robots allows them; adapter + fixtures are done. With permission they add 250-500 curated events/week per city, and Denver has no other events source. |
| I-065 | Rate-limit-aware Socrata: register a free SOCRATA_APP_TOKEN | infra | 3 | 1 | 2.4 | open | 17 of our units are Socrata; keyless requests are throttled (503s seen in research). A free app token raises the ceiling; the adapter already sends X-App-Token when set. |
| I-064 | Communico adapter for more libraries + exhibit handling | sources | 2 | 1 | 1.6 | open | The communico adapter is generic; other Communico/Attend libraries can be config-only. We skip 'All day' rows (exhibits/displays); an exhibits-only card type could use them. |
| I-060 | Florida DBPR ABT CSV adapter (Miami openings + temporary event alcohol permits) | sources | 4 | 2 | 1.6 | open | daily.csv (headerless, Last-Modified works) gives Dade 'Issue Permanent License' openings; bd4002lic.csv gives one-day festival permits with dates. robots allows /sto/. Miami currently has no openings source. |
| I-061 | Chicago Park District adult sports registration deadlines (tn7v-6rnw type=Program) | sources | 4 | 2 | 1.6 | open | Program rows include Sports - Volleyball/Basketball/Soccer with fee, age_range and registration_date: real beer-league deadlines from official data. Same Socrata adapter; needs registration.closes_at mapping in mapped.py. |
| I-066 | Denver events: find a permitted source (Denver Arts & Venues, RiNo/Cherry Creek calendars, CU Denver) | cities | 4 | 2 | 1.6 | open | Denver's only events source (Visit Denver) is blocked and DPL's LibCal is robots-disallowed, so Denver has openings but no events. Needs new research. |
| I-054 | Find a trivia nights source for Minneapolis | sources | 4 | 2 | 1.4 | open | auto: 0 trivia nights events in Minneapolis right now |
| I-055 | Find a parties & openings source for Minneapolis | sources | 4 | 2 | 1.4 | open | auto: 0 parties & openings events in Minneapolis right now |
| I-057 | Find registration deadlines for Minneapolis | sources | 4 | 2 | 1.4 | open | auto: the Deadlines view is empty — the core promise |
| I-058 | Minneapolis new liquor licenses by snapshot-diffing On_Sale_Liquor licenseNumber | sources | 3 | 2 | 1.2 | open | The ArcGIS layer's issueDate includes renewals and there is no original-issue date; a licenseNumber not seen in yesterday's full snapshot (654 rows) is a genuinely new place. Needs a small stateful diff step (first-seen date per license). |
| I-063 | Boston openings/events via data.boston.gov resource CSV downloads instead of the robots-disallowed CKAN API | sources | 3 | 2 | 1.2 | open | robots disallows /api/ and /datastore/* but not /dataset/<slug>/resource/<id>/download/*.csv. A CSV adapter (shared with FL DBPR) would restore special-event licenses and food-license openings — confirm the path is allowed first. |
| I-033 | Map view clustering + 'near me' by neighborhood | ux | 4 | 3 | 1.07 | open | Distance filter in the pitch |
| I-036 | Source reliability score computed from health history | health | 3 | 2 | 1.05 | open | SOURCES.md reliability column from data, not vibes |
| I-021 | Meetup GraphQL adapter (OAuth) incl. RSVP counts and attendanceForecast | sources | 5 | 3 | 1.0 | open | Run clubs, trivia, social groups; real RSVP numbers |
| I-037 | Season calendar: 'what's registering now' timeline for leagues | features | 4 | 3 | 0.93 | open | Leagues open/close in waves; show the wave |
| I-056 | Widen Minneapolis coverage (only 2 healthy sources) | cities | 4 | 3 | 0.93 | open | auto: thin coverage makes the city feel empty |
| I-030 | 'Bring a friend' mode: events good for pairs vs. solo | features | 3 | 2 | 0.9 | open | Different social modes for newcomers |
| I-028 | Price-drop / selling-fast alerts from snapshots | features | 4 | 3 | 0.8 | open | Needs SeatGeek/TM keys for real signal |
| I-051 | Neighborhood vibe cards: event mix by neighborhood (from coords) | features | 3 | 3 | 0.8 | open | Helps people choose where to live/hang out |
| I-029 | Neighborhood 'vibe' summaries computed from event mix | features | 3 | 3 | 0.5 | open | Help pick where to live/hang out |

## Done

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-059 | Keep openings visible for N days after their license date (build.py window for kind=opening) | pipeline | 5 | 1 | 4.0 | done | build.load_live_records drops records whose end < now-2h, so every opening dated in the past (most license signals) never reaches the export: Denver exports 0 events, NYC exports none of its 1,216 opening records. Openings need a display window (e.g. 60 days after start) instead of a fabricated end date. — 2026-10-16 done: build.OPENING_WINDOW_DAYS |
| I-053 | Diff alerts: 'new this week' badge from first_seen | ux | 4 | 1 | 3.2 | done | first_seen is tracked already; newcomers love fresh stuff — 2026-10-16 done: pipeline is_new + badge |
| I-052 | Per-card 'report a problem' link → prefilled GitHub issue | data-quality | 3 | 1 | 2.4 | done | Crowd-sourced correction loop without accounts — 2026-10-16 done: prefilled GitHub issue link in drawer |
| I-050 | Venue capacity registry (config/venues) with Wikidata P1083 + source URLs | data-quality | 4 | 2 | 1.6 | done | Better attendance bands; currently mostly category priors — 2026-10-16 done: gotc/pipeline/venue_refs.py |
| I-048 | Rainy-day swap: suggest an indoor alternative when an outdoor pick has ≥60% rain | features | 4 | 2 | 1.6 | done | Weather is attached now; plans can self-adjust — 2026-10-16 done: recommend.ts rain penalty with reason |
| I-047 | 'Leagues registering now' wave timeline per city (opens→closes bars) | features | 4 | 3 | 1.07 | done | League signups come in seasonal waves; a Gantt-like strip shows what's open now — 2026-10-16 done: RegistrationWaves in Deadlines view |
| I-046 | Evidence-quote page-watch as a generic verifier for any curated fact | data-quality | 5 | 2 | 2.0 | done | Shipped inside curated adapter; generalize to venue capacities and recurring schedules — 2026-10-16 done: curated adapter page-watch |
| I-035 | Freshness SLA per field shown on cards ('checked 2h ago') | ux | 4 | 1 | 3.6 | done | Trust — 2026-10-16 done: 'checked 2h ago' on every card + stale badges |
| I-034 | Recorded-fixture adapter tests (tests never hit the internet) | infra | 5 | 2 | 2.25 | done | Engineering bar — 2026-10-16 done: tests/fixtures + FixtureTransport; never hits network |
| I-032 | NYC permitted events (block parties, street fairs) via Socrata | sources | 5 | 1 | 4.5 | done | Exactly the 'block party' pitch, keyless — 2026-10-16 done: nyc_permitted_events (social event types only), 549 records live 2026-10-16 |
| I-031 | Library systems via BiblioCommons RSS (Hennepin, Chicago, Boston) | sources | 4 | 2 | 1.6 | done | Free classes, clubs, talks — high-quality keyless data — 2026-10-16 done: bibliocommons adapter; hclib/chipublib/bpl live 2026-10-16 (254/969/440 records) |
| I-027 | Shareable links (state in URL) + saved events in localStorage | features | 4 | 2 | 1.8 | done | Share a plan with a friend — 2026-10-16 done: hash router encodes view+filters; saved in localStorage |
| I-026 | 'Good for meeting people' filter + social score explanations | features | 4 | 1 | 3.6 | done | Newcomers want people, not just events — 2026-10-16 done: filter chip + social score reasons in drawer |
| I-025 | Health page in the dashboard (per-source state, last success, SLA, errors) | health | 5 | 2 | 2.25 | done | Observability inside the product — 2026-10-16 done: in-app Health view + header freshness pill |
| I-024 | Wikidata SPARQL for venue capacities (P1083) with source links | data-quality | 4 | 2 | 1.4 | done | Better attendance estimates from real capacities — 2026-10-16 done: dup of I-050; shipped |
| I-023 | Auto-open a GitHub issue when a unit gets quarantined | health | 4 | 2 | 1.6 | done | Failures loud even when nobody watches the dashboard — 2026-10-16 done: scripts/health_issues.py opens/closes per unit |
| I-022 | GitHub Actions: hourly refresh, DB persisted via cache + data branch, Pages deploy | infra | 5 | 2 | 2.25 | done | It must auto-update — 2026-10-16 done: ci.yml + hourly refresh.yml, state on orphan branch |
| I-019 | New bars/restaurants from fresh liquor-license records (NY SLA, TABC, Chicago, Minneapolis, Seattle) | sources | 5 | 3 | 1.17 | done | Openings proxy from real government data, keyless — 2026-10-16 done: openings via socrata/arcgis config (NY SLA pending+new, Chicago, Seattle, TABC x2, LA, Denver x3, Nashville). Minneapolis skipped: no original-issue date (see snapshot-diff idea). NB build.py drops past-dated openings — see diary |
| I-018 | Weather badge on outdoor events from NWS api.weather.gov (keyless) | features | 4 | 2 | 1.6 | done | Outdoor plans need forecasts; NWS is free, US-only, perfect fit — 2026-10-16 done: NWS hourly forecast attached at build, cached 3h |
| I-017 | Calendar export (.ics) per event and for the whole plan, with VALARM before deadlines | features | 5 | 2 | 2.25 | done | 'Remind me before registration closes' without a backend — 2026-10-16 done: .ics with VALARM 2d/3h before deadlines |
| I-016 | New-in-town onboarding → personalized first-30-days plan with explanations | features | 5 | 3 | 1.33 | done | The core 'you're new, here's your first month' promise — 2026-10-16 done: 4-step onboarding → explained 30-day plan |
| I-015 | Dashboard: Vite + Preact + TS, list/calendar/map/deadlines views | ux | 5 | 4 | 1.12 | done | The product people see — 2026-10-16 done: feed/deadlines/calendar/map/plan/saved/health views |
| I-014 | Volunteer opportunities are free by definition (derived, labeled) | data-quality | 3 | 1 | 2.4 | done | Avoid 'price unknown' noise on volunteer cards — 2026-10-16 done: shipped in bootstrap commit (normalize.py / build.assign_series) |
| I-013 | Series collapse: group repeated occurrences into one recurring card with next dates | ux | 5 | 2 | 2.25 | done | Feeds list weekly things 8×; list view should show one card — 2026-10-16 done: shipped in bootstrap commit (normalize.py / build.assign_series) |
| I-012 | Keep registration/sign-up links from description HTML as offers (SignUpGenius, Eventbrite, etc.) | data-quality | 5 | 1 | 4.5 | done | 'Sign up here' links are the most actionable thing on a volunteer card — 2026-10-16 done: shipped in bootstrap commit (normalize.py / build.assign_series) |
| I-011 | Extract 'Location:'/'Where:' lines from descriptions when venue is missing | data-quality | 4 | 1 | 3.6 | done | MPRB and many calendars put the place only in the body — 2026-10-16 done: shipped in bootstrap commit (normalize.py / build.assign_series) |
| I-010 | Attendance estimate with method + band (capacity × fill, or category prior) | data-quality | 4 | 2 | 1.6 | done | Never fake precision |
| I-009 | Deadline extraction from free text with evidence | data-quality | 5 | 2 | 2.0 | done | 'register by Oct 3' → registration.closes_at |
| I-008 | Entity resolution: venues + cross-source event clustering with sticky ids | pipeline | 5 | 3 | 1.33 | done | Same concert on 5 sites = 1 card with 5 prices |
| I-007 | Ticketmaster + SeatGeek adapters (key-gated, report 'needs key' when absent) | sources | 5 | 2 | 2.0 | done | Concert prices; stubbed until keys arrive |
| I-006 | Generic adapters: Socrata, ICS, Tribe Events (WordPress), Localist, LiveWhale | sources | 5 | 3 | 1.33 | done | One adapter covers thousands of sites; cities become config |
| I-005 | Per-unit health state machine (healthy/degraded/quarantined/recovering) | health | 5 | 2 | 2.0 | done | Failures are never silent; last-known-good keeps serving |
| I-004 | SQLite storage with forward-only migrations + raw payload store | pipeline | 5 | 2 | 2.0 | done | Boring, solid, replayable |
| I-003 | Polite HTTP client: robots, per-host rate limit, backoff, conditional GET | pipeline | 5 | 2 | 2.0 | done | Respect sources; cheap polling |
| I-002 | Category taxonomy (YAML) with keyword classifier + deprecation | data-quality | 5 | 2 | 2.0 | done | Categories are ids, never free text |
| I-001 | Versioned event schema (pydantic) as the single contract | pipeline | 5 | 2 | 2.0 | done | Every layer validates against one schema; TS types generated from it |

## Rejected (and why)

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-045 | Showing a precise '% tickets left' from any source | data-quality | 4 | 2 | 1.6 | rejected | No legit source exposes seat inventory to third parties; we show labeled signals with bands instead |
| I-044 | Yelp Events API | sources | 3 | 2 | 1.2 | rejected | $229+/mo after trial |
| I-043 | DoStuff network (Do512/Do312) scraping | sources | 4 | 2 | 1.6 | rejected | No API and actively blocks bots — ask for a partnership instead |
| I-042 | Resident Advisor scraping | sources | 3 | 2 | 1.2 | rejected | Terms §4.4 ban scraping; undocumented GraphQL |
| I-041 | Bandsintown API | sources | 3 | 2 | 1.2 | rejected | Terms limit use to artists' own data and forbid mixing with other sources without distinction |
| I-040 | Songkick API | sources | 4 | 2 | 1.6 | rejected | Paid license; no new hobbyist approvals |
| I-039 | Eventbrite city-wide search | sources | 4 | 2 | 1.6 | rejected | Eventbrite removed public event search in 2019 (404); only per-organizer/venue access remains |

