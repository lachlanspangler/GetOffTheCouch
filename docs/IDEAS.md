# Ideas

_Generated from `docs/ideas_ledger.json` by `python -m gotc.ideas render`. Edit the ledger via the CLI, not this file._

Score = value × confidence ÷ effort. The loop (docs/WORKFLOW.md) always picks the top **open** idea,
unless docs/HEALTH.md has something red.

**open** 91 · **doing** 4 · **done** 78 · **rejected** 28 · **parked** 2 · **blocked** 14

## Up next (open, by score)

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-137 | Nominatim compliance: ≤1 req/s and per-run budget | pipeline | 5 | 1 | 4.0 | doing | We burst ~55/min at 10 cities; policy violation (SCALING §4.3) |
| I-138 | Replace Wikidata SPARQL (robots-disallowed) with allowed API or curated venues | sources | 5 | 2 | 2.0 | doing | query.wikidata.org robots.txt disallows /sparql |
| I-140 | Per-city go-live gate (G1–G11) with live/beta/hidden tiers | cities | 5 | 2 | 2.0 | doing | Honest coverage; thin cities never pretend |
| I-139 | gotc discover <city>: Socrata/data.gov/ArcGIS/library/university/venue fingerprints | cities | 5 | 4 | 1.0 | doing | Adding a city should approach automatic |
| I-114 | Per-city sitemaps + sitemap index with honest lastmod | growth | 4 | 1 | 3.2 | open | Discovery for ~8k pages; Search Console URL-prefix property |
| I-145 | 'This weekend' hub with dated title (Oct 16–18), rewritten weekly | growth | 4 | 1 | 3.2 | open | Time Out pattern: one URL, fresh dates, high-intent query |
| I-146 | 'Not hosted by us · hosted by {Org}' line on event pages | ux | 4 | 1 | 3.2 | open | Partiful trust pattern; clarifies we're a guide |
| I-172 | OSM attribution on the dashboard for cached Nominatim coordinates | ux | 4 | 1 | 3.2 | open | The OSMF policy requires visible attribution; ~500 cached Nominatim results still place pins even though new lookups are off. Needs 'Geocoding © OpenStreetMap contributors' in the footer/map. |
| I-199 | Probe tooling honors Crawl-delay | infra | 4 | 1 | 3.2 | open | Prevents slips like azleg.gov (Crawl-delay 120) |
| I-211 | Galaxy Digital tenant sanity check (channel title/state must match city) | data-quality | 4 | 1 | 3.2 | open | Volunteer Now Dallas domain served a California tenant |
| I-075 | Card-level 'why this time is approximate' when a source only gives dates | data-quality | 3 | 1 | 2.4 | open | All-day vs unknown time are different truths |
| I-144 | Keep-alive for scheduled workflows (60-day inactivity disable) | infra | 3 | 1 | 2.4 | open | GitHub disables crons on inactive repos |
| I-185 | SeatEngine/Opendate fingerprints in discover | cities | 3 | 1 | 2.4 | open | Comedy clubs and venues become config-only |
| I-187 | LiveWhale pagination | sources | 3 | 1 | 2.4 | open | Brown's calendar stops at 100 items (~2–3 days) |
| I-188 | ArcGIS route geometry → representative point | pipeline | 3 | 1 | 2.4 | open | Raleigh street-event permits are routes and don't map |
| I-198 | Title include/exclude filters for ics, jsonld, tribe, HandsOn | sources | 3 | 1 | 2.4 | open | Stop hacking exclude_location with lookaheads |
| I-212 | Trumba custom-field filter (e.g. 'Event Open To' contains Public) | sources | 3 | 1 | 2.4 | open | Emory exposes it; adapter can't filter |
| I-214 | CivicPlus iCalendar fingerprint in discover | cities | 3 | 1 | 2.4 | open | Works via plain ics adapter (Dallas Parks) |
| I-168 | Backtest gotc discover on the 10 live cities (recall/precision per family) | pipeline | 5 | 2 | 2.0 | open | Discovery found Denver's htyp-tqzh from a cold catalog query; running it blind on all ten hand-built cities gives a measured recall number before we trust it on 40 new metros (SCALING.md §5 #1). |
| I-171 | Coverage UI: Live/Beta chip, pillar strip, coverage matrix page | ux | 5 | 2 | 2.0 | open | index.json and every feed now carry coverage (schema 1.5.0) but the dashboard doesn't render it yet, so beta cities look live and thin pillars look like empty lists. |
| I-064 | Communico adapter for more libraries + exhibit handling | sources | 2 | 1 | 1.6 | open | The communico adapter is generic; other Communico/Attend libraries can be config-only. We skip 'All day' rows (exhibits/displays); an exhibits-only card type could use them. |
| I-076 | Discover more HandsOn Connect / Galaxy Digital tenants and Volo markets for new cities | sources | 4 | 2 | 1.6 | open | HOC/Galaxy pages only list org calendars; Volo, HOC and Galaxy tenants exist in more cities (Volo: DC, Philly, SF, San Diego; HOC tenants findable via cdn0.handsonconnect.org) |
| I-112 | Event page lifecycle: ended banner → meta-refresh stub → delete | growth | 4 | 2 | 1.6 | open | Pages can't send 301/410; keeps shared links useful and the site bounded |
| I-113 | schema.org Event JSON-LD for one-off and recurring events only | growth | 4 | 2 | 1.6 | open | Eligible for event rich results; never for openings/deadlines (Google content rules) |
| I-116 | Per-city Atom feeds and deadlines.ics subscriptions | features | 4 | 2 | 1.6 | open | Subscribable calendars beat one-off downloads for deadlines |
| I-119 | Lighthouse CI + bundle budgets (entry JS ≤60 KB gz, CSS ≤15 KB) | infra | 4 | 2 | 1.6 | open | Performance budgets enforced in CI, not by memory |
| I-135 | Admin-noise flags (room rentals, closures, staff-only, open hours) per source | data-quality | 4 | 2 | 1.6 | open | Biggest junk class in library/city feeds |
| I-136 | 'Why am I seeing this' panel with personal reasons | features | 4 | 2 | 1.6 | open | Explains picks in plain language; trust |
| I-142 | Hash-gated incremental builds and exports | infra | 4 | 2 | 1.6 | open | Only rebuild cities whose inputs changed |
| I-143 | Raw payload retention + price snapshot downsampling | infra | 4 | 2 | 1.6 | open | State file would pass GitHub's 100 MB limit |
| I-147 | Organizer track record chip (past events, how long listed) | features | 4 | 2 | 1.6 | open | Meetup trust pattern without ratings we don't have |
| I-160 | Rank v2: cap by organizer/venue instead of listing source for aggregator feeds (visit_ballard_events, challenge_trivia_austin) | features | 4 | 2 | 1.6 | open | The <=2-per-source cap costs For You 0.075 NDCG@10; aggregators list many independent venues, so the source is a poor proxy for sameness |
| I-161 | Human spot-check >=20% of the ranking judgments, then re-snapshot on a new date as a held-out eval | data-quality | 4 | 2 | 1.6 | open | All 3,360 grades are one agent's; the flags, lambda and interest tweaks were chosen in-sample (RANKING.md 7.6) |
| I-162 | Taxonomy rules for library services and big-name concerts (MNsure Help filed as hike, Drop-in Tech Help as volunteering, Indigo Girls as festival) | data-quality | 4 | 2 | 1.6 | open | Ranking eval error analysis: category mistakes drive more bad picks than any weight |
| I-163 | UI for rank v2: 'Why am I seeing this?' (whySeeingThis), Not for me + why (dismiss), What we've learned panel with reset (learnedSummary/resetAffinity) | ux | 4 | 2 | 1.6 | open | The lib exposes all of it; nothing renders it yet, and dismisses give the cleanest negative signal |
| I-173 | gotc discover --verify: run chosen candidates in a scratch DB | pipeline | 4 | 2 | 1.6 | open | Candidates are scored on one probe; a scratch-DB run per unit (valid/rejected, categories, geofence drops, dup rate vs promoted units) makes promotion a review of numbers, not guesses (§2.8). |
| I-174 | Library and university seeds for discover from IMLS PLS + College Scorecard | sources | 4 | 2 | 1.6 | open | Seeds are operator-supplied today; the IMLS administrative-entity file and Scorecard (DATA_GOV_API_KEY, ≥10k students, online-only filtered) would make discovery hands-off for metros 11–50. |
| I-175 | CivicPlus calendar RSS adapter | sources | 4 | 2 | 1.6 | open | CivicPlus hosts city and parks calendars for many suburbs and mid-size cities (metros 30–100); RSSFeed.aspx is robots-allowed with a calendarEvent: namespace. discover already flags it as no_adapter_yet. |
| I-195 | Mobilize public events adapter | sources | 4 | 2 | 1.6 | open | Documented keyless API; Oregon Food Bank shifts; fills volunteering gaps |
| I-196 | LibCal multi-calendar discovery + JSON list adapter | cities | 4 | 2 | 1.6 | open | Phoenix needed 17 branch feeds; ICS caps at 500 past items |
| I-197 | Squarespace ?format=json events adapter (check ToS first) | sources | 4 | 2 | 1.6 | open | ~a dozen Bay Area venues |
| I-206 | LibCal date-window support | sources | 4 | 2 | 1.6 | open | Public ICS caps at 500 items starting a month back; Cleveland PL unusable |
| I-208 | Venue-ownership denylist (Live Nation, AEG/PromoWest, FPC) | cities | 4 | 2 | 1.6 | open | Ownership judged by hand today for several venues |
| I-096 | Data-quality guard: flag JSON-LD occurrence dates that contradict a posted weekly schedule | data-quality | 2 | 1 | 1.4 | open | Team Trivia's JSON-LD stamped a Thursday game with Friday's date (server rolled over). teamtrivia rejects those; a shared helper could do the same for the jsonld venue-calendar branch and Luma/ICS recurring sources. |
| I-084 | Find a volunteering source for Denver | sources | 4 | 2 | 1.4 | open | auto: 0 volunteering events in Denver right now |
| I-085 | Find a cons & faires source for Denver | sources | 4 | 2 | 1.4 | open | auto: 0 cons & faires events in Denver right now |
| I-087 | Find a run clubs source for Denver | sources | 4 | 2 | 1.4 | open | auto: 0 run clubs events in Denver right now |
| I-089 | Find a trivia nights source for Los Angeles | sources | 4 | 2 | 1.4 | open | auto: 0 trivia nights events in Los Angeles right now |
| I-090 | Find a cons & faires source for Nashville | sources | 4 | 2 | 1.4 | open | auto: 0 cons & faires events in Nashville right now |
| I-091 | Find a trivia nights source for Seattle | sources | 4 | 2 | 1.4 | open | auto: 0 trivia nights events in Seattle right now |
| I-111 | Pre-render city, hub and event pages at build time (SSR + hydrate) | growth | 5 | 3 | 1.33 | open | Crawlers and social scrapers need real HTML; most first visits come from search |
| I-117 | Week-sharded city data + inlined initial.json | infra | 5 | 3 | 1.33 | open | City JSON is 170–470 KB gz and blocks first render; target ≤30 KB first view |
| I-141 | Per-city state files + sharded matrix refresh + single publish job | infra | 5 | 3 | 1.33 | open | Monolithic run stops fitting at ~60–70 cities |
| I-169 | Per-city state files on the pipeline-state branch | infra | 5 | 3 | 1.33 | open | Deltas carry every source_record of a shard's cities (1.7 MB gz for NYC+Boston) and CI slim state forces a full rebuild hourly; per-city DBs fix both and keep every file far below GitHub's 100 MB limit (§4.6 item 2). |
| I-078 | Health check: flag when distinct listing pages return identical record sets (UpcomingCons) | health | 3 | 2 | 1.2 | open | UpcomingCons category pages returned the anime list for /gaming and /sci-fi within one minute; a guard that flags identical listing-id sets across distinct pages catches this server-side caching bug |
| I-081 | Share one fetch of national pages across city units in a run | pipeline | 3 | 2 | 1.2 | open | Global sources (upcomingcons, makerfaire) refetch identical national pages once per city; a per-run shared payload cache would cut 10x requests |
| I-082 | ics: lift Luma 'Get up-to-date information at' link as the event URL/RSVP offer | sources | 3 | 2 | 1.2 | open | Luma ICS feeds omit URL; descriptions say 'Get up-to-date information at: https://luma.com/...'; lifting it gives every Luma event an RSVP offer |
| I-098 | Per-room venue capacities (Icehouse main room vs whole building) to tighten attendance bands | data-quality | 3 | 2 | 1.2 | open | Whole-building capacities over-estimate small-room shows |
| I-100 | Health check: all-past start dates while the page lists upcoming items → flag series-first-date sources | health | 3 | 2 | 1.2 | open | Caught Triple Door by hand; make it automatic |
| I-102 | City concert digest: top 10 shows this week with lowest price per seller | features | 3 | 2 | 1.2 | open | Shareable, newsletter-ready view of the price comparison |
| I-115 | Build-time OG share images (art + title + date) via satori/resvg | growth | 3 | 2 | 1.2 | open | Shared links look like a publication in iMessage/Slack |
| I-149 | Fee-inclusive price display where sellers expose fees | data-quality | 3 | 2 | 1.2 | open | DICE pattern; only where reported |
| I-165 | Doctor: per-source share of admin/noise_recurring/service_desk flags; suggest an adapter reject rule above 30% | health | 3 | 2 | 1.2 | open | Fix noise upstream (RANKING.md section 4 feedback loop); rank hints now make the shares cheap to compute |
| I-176 | Fetch national feeds once per run and share across cities (Challenge, UpcomingCons) | pipeline | 3 | 2 | 1.2 | open | Challenge's 0.9 MB show list is fetched once per city unit today; at 50 cities that's 45 MB/run of identical bodies (§4.6 item 6). |
| I-184 | Modern Events Calendar REST adapter | sources | 3 | 2 | 1.2 | open | BJCC, Myriad Gardens, Arts Council OKC use it |
| I-186 | Squarespace events preset for jsonld | sources | 3 | 2 | 1.2 | open | 4 of 11 Memphis units |
| I-189 | Match 'X vs Y' games across arena and athletics feeds | pipeline | 3 | 2 | 1.2 | open | Providence Friars games duplicated |
| I-190 | Curated league registries for league-empty metros | data-quality | 3 | 2 | 1.2 | open | Leagues are empty in Tampa, Hartford and most of batch D |
| I-205 | Generic jsonfeed adapter (config-mapped JSON) | sources | 3 | 2 | 1.2 | open | Unlocks custom feeds like Wayne State's (~200 events) |
| I-213 | Chunked/backed-off BiblioCommons fetch for big systems | sources | 3 | 2 | 1.2 | open | Allegheny County Library 504 even for one day |
| I-080 | Dashboard strip: league/volunteer sign-ups closing in the next 7 days | features | 4 | 3 | 1.07 | open | Volo, HOC and Galaxy now give hundreds of shifts/seasons with spots-left and closes_at; a 'closing this week' strip per city is the core 'deadlines you'd otherwise miss' promise |
| I-170 | Week-sharded card files (now.json + w<ISO-week>.json) | ux | 4 | 3 | 1.07 | open | gotc validate now warns for Boston, Chicago, NYC and Seattle: their next-14-days cards are 1.7–2.5 MB raw / 259–346 KB gz, over the 1.5 MB / 250 KB first-paint budget (§4.6 item 5). |
| I-181 | Golden Volunteer adapter (Orlando, Raleigh volunteer centers) | sources | 4 | 3 | 1.07 | open | Main volunteer hubs in two metros run it |
| I-194 | Vega events adapter (San Diego Public Library moved off BiblioCommons) | sources | 4 | 3 | 1.07 | open | Libraries are migrating to Vega |
| I-207 | First-seen diff for renewal-dated license files | sources | 4 | 3 | 1.07 | open | Milwaukee/Detroit carry only renewal dates; snapshot diff exposes new licensees |
| I-036 | Source reliability score computed from health history | health | 3 | 2 | 1.05 | open | SOURCES.md reliability column from data, not vibes |
| I-088 | Improve geocoding for Denver (61/201 events unmapped) | data-quality | 3 | 2 | 1.05 | open | auto: map view and distance filters miss these |
| I-093 | Miami events from Florida DBPR temporary alcohol permits (bd4002lic.csv) | sources | 3 | 2 | 1.05 | open | Header CSV with DBA = event name and Expiration Date ~ the event's last day (research MIA-3: Halloween half marathon, seafood festival, PeruFest). The csvfile adapter + window filter already handle it; needs an all-day multi-day mapping and an Owner Name scrub (automatic). |
| I-105 | Austin Public Library events: recover the branch the JSON-LD omits | data-quality | 3 | 2 | 1.05 | open | Austin Public Library's Drupal event pages have JSON-LD without a location (60 listing pages); the listing HTML shows the branch. A jsonld option to take the venue from a CSS/regex hook on the listing, or a small Drupal-views adapter, would add Austin's library (~1,100 events/fortnight). |
| I-021 | Meetup GraphQL adapter (OAuth) incl. RSVP counts and attendanceForecast | sources | 5 | 3 | 1.0 | open | Run clubs, trivia, social groups; real RSVP numbers |
| I-037 | Season calendar: 'what's registering now' timeline for leagues | features | 4 | 3 | 0.93 | open | Leagues open/close in waves; show the wave |
| I-056 | Widen Minneapolis coverage (only 2 healthy sources) | cities | 4 | 3 | 0.93 | open | auto: thin coverage makes the city feel empty |
| I-030 | 'Bring a friend' mode: events good for pairs vs. solo | features | 3 | 2 | 0.9 | open | Different social modes for newcomers |
| I-094 | Boston new liquor licenses by first-seen snapshot diff | sources | 3 | 2 | 0.9 | open | The liquor-licenses CSV download is robots-allowed, but 'issued' is re-stamped in bulk (1,057 rows dated 2013-11, a batch of existing breweries re-issued 2026-09), so it can't signal newness. openings_by_first_seen (silent baseline) would; person names in business_name/applicant need entity_only_fields. |
| I-164 | Move newcomer_prior from rank/weights.ts into config/taxonomy.yaml and export it in index.json | pipeline | 2 | 2 | 0.8 | open | RANKING.md wants priors as config, documented per family; kept in TS for now to avoid index.json plumbing |
| I-028 | Price-drop / selling-fast alerts from snapshots | features | 4 | 3 | 0.8 | open | Needs SeatGeek/TM keys for real signal |
| I-118 | Service worker: cached data first, refresh in background, 'data as of' badge | infra | 3 | 3 | 0.8 | open | Usable on flaky phone connections; honest about staleness |
| I-166 | Rank v2 learned weights: coordinate ascent on the judgment sets with leave-one-city-out, signs fixed, x0.5-x2 bounds | features | 3 | 3 | 0.8 | open | Rollout step 7; worth it only after a second, held-out snapshot exists |
| I-200 | Shared regional units: one fetch split across cities | pipeline | 3 | 3 | 0.8 | open | HandsOn Bay Area / Challenge fetched once per city today |
| I-067 | Transit-time 'near me' from GTFS (keyless) instead of straight-line km | features | 4 | 4 | 0.8 | open | Newcomers without cars care about the bus ride, not the crow-flies distance |
| I-072 | Typical registration windows learned from history ('kickball usually registers in Feb') | features | 4 | 4 | 0.8 | open | Needs a season of snapshot history; gives 'plan ahead' power |
| I-108 | Levitt Pavilion Denver free concerts when the 2027 season posts (jsonld follow) | cities | 3 | 2 | 0.75 | open | Levitt Pavilion Denver (free summer concert series, Squarespace) had 0 upcoming events in October; Squarespace event pages carry Event JSON-LD, so a jsonld follow config should work when the 2027 season is announced (spring). |
| I-095 | Auto-add Team Trivia / Challenge Entertainment markets when venues appear | sources | 2 | 2 | 0.6 | open | Team Trivia's trivia-in-chicagoland/miami/nashville region pages list 0 venues today; Challenge's south-florida/chicagoland/southern-california metros are suburban only. A weekly doctor check could flag when an in-city venue shows up so a unit can be added. |
| I-106 | Taxonomy: negative keywords for 'curator tour', 'opening night', 'class' titles | data-quality | 2 | 2 | 0.6 | open | Taxonomy keywords misfire on venue feeds: 'Curator-Led Tour' → music.concert ('tour'), 'Opening Night Dinner' → nightlife.opening, 'Comedy Class' → nightlife.comedy. A small negative-keyword list (tour after curator/garden/walking; opening night; class/workshop beats genre) would fix several sources at once. |
| I-029 | Neighborhood 'vibe' summaries computed from event mix | features | 3 | 3 | 0.5 | open | Help pick where to live/hang out |

## Blocked (needs something only a human can provide)

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-215 | Socrata app token (recommended at 50 cities) | infra | 3 | 1 | 2.4 | blocked | More Socrata domains → more throttling; free token; needs the user |
| I-209 | Michigan/Ohio SoS pages (robots 403): outreach or curated path | sources | 3 | 1 | 2.4 | blocked | No MI starter pack; OH voter registration missing |
| I-202 | CA ABC license data access | sources | 4 | 1 | 3.2 | blocked | Only route to openings in six CA metros; reports page is Cloudflare-challenged |
| I-201 | Simpleview tourism boards permission (Phoenix, Scottsdale, Salt Lake, Sacramento, Riverside, Fresno) | sources | 3 | 1 | 2.4 | blocked | Deliberate 403s; outreach only |
| I-183 | Outreach: Memphis Public Libraries, Community Libraries of Providence, Hands On Birmingham, LibraryMarket | sources | 4 | 1 | 3.2 | blocked | Each is a city's primary official source and blocked today |
| I-182 | NC ABC new-permit feed via outreach | sources | 4 | 2 | 1.6 | blocked | Openings for Charlotte and Raleigh |
| I-159 | Search Console property + sitemap submission | growth | 4 | 1 | 3.2 | blocked | Blocked on the user's Google account |
| I-158 | Custom domain before Google indexes github.io URLs | growth | 4 | 1 | 3.2 | blocked | Avoids a site move later; blocked on the user |
| I-103 | Ask AEG Presents for permission to use their per-venue events JSON (Denver/Seattle concerts) | sources | 4 | 2 | 1.2 | blocked | AEG's Next.js venue sites (Mission Ballroom, Bluebird, Ogden, Gothic, Fiddler's Green; Showbox/Neumos in Seattle) read a public JSON blob per venue (aegwebprod…/json/events/<id>/events.json) with face-value prices, on-sale dates and door times. Its terms didn't render to us, so we skipped it. A permission e-mail to AEG could unlock ~10 big venues in 3+ cities with one adapter. — 2026-10-16 blocked: needs the user to contact AEG Presents |
| I-097 | Trivia for LA/Seattle/Chicago: hosts there gate schedules behind bot challenges; ask Geeks Who Drink / King Trivia for a feed | sources | 3 | 2 | 1.2 | blocked | Team Trivia has no LA/Seattle markets and 0 venues in Chicagoland today |
| I-092 | RunSignup: register as an API caller and enable the runsignup source | sources | 5 | 1 | 4.5 | blocked | Adapter, config and fixture tests are done; the API Terms require caller registration (free, needs the user's RunSignup account). Recorded Chicago response: 45 races, 42 with a reported registration close date, 15 early-bird price steps, so every city gains published deadlines. |
| I-079 | Email Make: (makerfaire.com) for permission/allowlisting of /query/?type=map | sources | 3 | 1 | 2.4 | blocked | Maker Faire map JSON is keyless and robots-allowed but Cloudflare challenges our client; asking Make: for access (or an export) unblocks the only national faire feed |
| I-065 | Rate-limit-aware Socrata: register a free SOCRATA_APP_TOKEN | infra | 3 | 1 | 2.4 | blocked | 17 of our units are Socrata; keyless requests are throttled (503s seen in research). A free app token raises the ceiling; the adapter already sends X-App-Token when set. — 2026-10-16 blocked: needs SOCRATA_APP_TOKEN from the user (free) |
| I-062 | Ask Simpleview boards (Meet Boston, Visit Austin, Visit Denver) for API access or an allowlisted UA | sources | 4 | 1 | 3.2 | blocked | Their event APIs return 403 (CDN bot protection) to our client though robots allows them; adapter + fixtures are done. With permission they add 250-500 curated events/week per city, and Denver has no other events source. — 2026-10-16 blocked: needs the user to contact Simpleview boards |

## Parked

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-148 | Practical newcomer tips per venue (transit line, entrance) | features | 3 | 3 | 0.8 | parked | Partiful-style practical help, needs curation |
| I-129 | Self-hosted Protomaps PMTiles per city | infra | 3 | 4 | 0.6 | parked | No third-party tile server; enables static map images at build time |

## Done

| ID | Idea | Area | V | E | Score | Status | Why / notes |
|---|---|---|---|---|---|---|---|
| I-134 | Thompson-sampling exploration slot + 14-day family floor | features | 3 | 2 | 1.2 | done | Prevents filter bubbles in on-device personalization — 2026-10-16 done: exploration slot at position 4; floor needs 14 days of history |
| I-133 | On-device affinity from saves/opens/dismisses (21-day half-life, ±0.3 cap) | features | 4 | 3 | 1.07 | done | Learns without tracking; capped so it can't override penalties — 2026-10-16 done: rank/affinity.ts + affinityStore.ts; saves, calendar adds, opens ≥5 s, outbound, dismiss |
| I-132 | Judgment sets per city × persona with NDCG/ILD regression gate | data-quality | 5 | 3 | 1.33 | done | Measurable ranking quality without user data — 2026-10-16 done: 5 cities × 6 personas, 560 events labeled; npm run eval:rank in make check |
| I-131 | Golden-rule ranking tests (no kids items atop adult picks, ≤2 per source) | data-quality | 5 | 1 | 4.0 | done | Hard-fail tests for embarrassing rankings — 2026-10-16 done: web/tests/rank/golden.test.ts on 5 snapshots × 6 personas + adversarial feed |
| I-130 | Ranking v2: candidates → features → score → MMR → explanations | features | 5 | 3 | 1.33 | done | Algorithmic ranking is the product (RANKING.md) — 2026-10-16 done: 2026-10-16 rank v2 shipped (default on); results RANKING.md §7 |
| I-128 | Public status page with plain-sentence summary, freshness out of the header | health | 4 | 2 | 1.6 | done | Turns pipeline honesty into a trust asset without dev-ops chrome |
| I-127 | Contrast regression test recomputing WCAG ratios from tokens | ux | 4 | 1 | 3.2 | done | Token edits can't silently break AA |
| I-126 | Real event page with sticky ticket card and destination-named CTA | ux | 5 | 3 | 1.33 | done | Bookmarkable, SEO-ready, provenance next to the CTA |
| I-125 | Calm map: grayscale tiles, one-color pins, white clusters, list/map split | ux | 4 | 2 | 1.6 | done | The map stops shouting; list is the accessible equivalent |
| I-124 | Deterministic SVG art per event/category/city | ux | 4 | 3 | 1.07 | done | Solves 'no photos' legally; stable per id; theme-aware via OKLCH |
| I-123 | One-row filter bar with menus + mobile bottom sheet + applied chips | ux | 5 | 3 | 1.33 | done | First event moves from y≈377 to ~250 on desktop; no clipped mobile controls |
| I-122 | Day-grouped list rows instead of a boxed card grid | ux | 5 | 3 | 1.33 | done | Chronological scanning like Resy/Time Out, ~2× events per screen |
| I-121 | Card signal budget: one meta line, one status, one tag (cardSignals) | ux | 5 | 2 | 2.0 | done | Removes badge soup with tested logic; enforces no fake urgency |
| I-120 | Design tokens + self-hosted Inter/Newsreader with metric-matched fallbacks | ux | 5 | 2 | 2.0 | done | Biggest single jump in perceived quality, zero CLS |
| I-110 | Path routing with clean city/hub/event URLs + legacy hash redirect | growth | 5 | 2 | 2.0 | done | Hash URLs are invisible to search and link previews (SEO_ACCESS §1) |
| I-109 | Weekly habits section in the 30-day plan | features | 4 | 1 | 3.2 | done | Recurring social events are the fastest way to make friends in a new city |
| I-107 | SIDEARM athletics ICS for the other cities' universities (home games, force_category) | sources | 3 | 1 | 2.1 | done | SIDEARM Sports athletics sites (gohuskies.com, denverpioneers.com) publish calendar.ashx/calendar.ics for all sports; home games are filterable by LOCATION. Most NCAA schools use SIDEARM: Minnesota, Northwestern/DePaul/Loyola, BU/BC/Northeastern, UCLA/USC, Miami, Vanderbilt/Belmont, Columbia/Fordham. — 2026-10-16 done: 8 schools added |
| I-104 | Survey carbonhouse /events/rss venues in the other 7 cities (Ryman Nashville first: 76 events) | sources | 3 | 1 | 2.4 | done | rss_events covers any carbonhouse venue at /events/rss. The Ryman (Nashville) answered with 76 events; other cities' arenas/theatres on carbonhouse were not surveyed. Pure YAML per venue. — 2026-10-16 done: 10 carbonhouse venues added |
| I-101 | On-sale reminders: .ics alarm 15 min before Ticketmaster public on-sale | features | 4 | 1 | 3.2 | done | On-sale times are now reported deadlines; reminders make them useful — 2026-10-16 done: ics vonsaleFor |
| I-099 | 'Similar this week' strip in the drawer (same family, nearby, different source) | features | 3 | 2 | 1.2 | done | Helps browsing from a good find — 2026-10-16 done: recommend.similar |
| I-086 | Find a concerts source for Denver | sources | 4 | 2 | 1.4 | done | auto: 0 concerts events in Denver right now — 2026-10-16 done: Cervantes, Larimer, Globe Hall, Lost Lake, Denver Arts & Venues |
| I-083 | Find a trivia nights source for Denver | sources | 4 | 2 | 1.4 | done | auto: 0 trivia nights events in Denver right now — 2026-10-16 done: Team Trivia + Challenge (168 games) |
| I-077 | Track Volo price steps per program (early bird → regular → last chance) as a price trend | data-quality | 4 | 2 | 1.6 | done | Volo detail /l/{uuid} and the discover card show the same program; a weekly diff of price per player lets us show 'price went up on 10/17' with evidence and alert before early-bird ends — 2026-10-16 done: Volo offers are snapshotted each run → price_trend shows early-bird → regular steps automatically |
| I-074 | Census batch geocoder (10k addresses/POST) to fill coordinates in one call | data-quality | 4 | 2 | 1.6 | done | Per-request geocoding is slow; batch API is keyless — 2026-10-16 done: Geocoder.batch + variants |
| I-073 | Friendsgiving / holiday-alone finder for first holidays in a new city | features | 3 | 2 | 1.2 | done | First holidays in a new city are the loneliest; curate + classify — 2026-10-16 done: router ids + Saved shared mode |
| I-071 | Shared plan links: encode picks in URL so a friend can see overlaps | features | 3 | 2 | 1.2 | done | Social without accounts — 2026-10-16 done: gotc/health/reliability.py |
| I-070 | Source reliability score per unit (uptime, reject rate, freshness) auto-rendered into SOURCES.md | health | 4 | 2 | 1.6 | done | Reliability column from data instead of a hand grade — 2026-10-16 done: dup of I-071 (reliability.py) |
| I-069 | Accessibility + sober-friendly filters from tags (wheelchair, ASL, alcohol-free) | ux | 4 | 1 | 3.2 | done | Tags already derived; expose as filter chips — 2026-10-16 done: FilterBar tag chips |
| I-068 | 'Free food' detector (pizza provided, free snacks) as a tag + filter | features | 3 | 1 | 2.4 | done | Real newcomer budget hack; text patterns are reliable — 2026-10-16 done: enrich free_food |
| I-066 | Denver events: find a permitted source (Denver Arts & Venues, RiNo/Cherry Creek calendars, CU Denver) | cities | 4 | 2 | 1.6 | done | Denver's only events source (Visit Denver) is blocked and DPL's LibCal is robots-disallowed, so Denver has openings but no events. Needs new research. — 2026-10-16 done: 2026-10-16 session 2: Denver now has general events — JeffCo + Arapahoe library calendars (BiblioCommons, 210 + 108), Denver Arts & Venues DPAC + Coliseum RSS (110 + 26, new rss_events adapter), DU Pioneers home games (32), Cervantes' (40). Visit Denver stays blocked (403). |
| I-063 | Boston openings/events via data.boston.gov resource CSV downloads instead of the robots-disallowed CKAN API | sources | 3 | 2 | 1.2 | done | robots disallows /api/ and /datastore/* but not /dataset/<slug>/resource/<id>/download/*.csv. A CSV adapter (shared with FL DBPR) would restore special-event licenses and food-license openings — confirm the path is allowed first. — 2026-10-16 done: boston_food_openings_csv |
| I-061 | Chicago Park District adult sports registration deadlines (tn7v-6rnw type=Program) | sources | 4 | 2 | 1.6 | done | Program rows include Sports - Volleyball/Basketball/Soccer with fee, age_range and registration_date: real beer-league deadlines from official data. Same Socrata adapter; needs registration.closes_at mapping in mapped.py. — 2026-10-16 done: chicago_park_adult_leagues + _classes |
| I-060 | Florida DBPR ABT CSV adapter (Miami openings + temporary event alcohol permits) | sources | 4 | 2 | 1.6 | done | daily.csv (headerless, Last-Modified works) gives Dade 'Issue Permanent License' openings; bd4002lic.csv gives one-day festival permits with dates. robots allows /sto/. Miami currently has no openings source. — 2026-10-16 done: fl_dbpr_openings_miami (csvfile adapter, bd4006lic.csv Original Licensure Date, on-premises series only): 66 live, 0 rejects. Temporary event permits (bd4002lic.csv) split into a new idea. |
| I-059 | Keep openings visible for N days after their license date (build.py window for kind=opening) | pipeline | 5 | 1 | 4.0 | done | build.load_live_records drops records whose end < now-2h, so every opening dated in the past (most license signals) never reaches the export: Denver exports 0 events, NYC exports none of its 1,216 opening records. Openings need a display window (e.g. 60 days after start) instead of a fabricated end date. — 2026-10-16 done: build.OPENING_WINDOW_DAYS |
| I-058 | Minneapolis new liquor licenses by snapshot-diffing On_Sale_Liquor licenseNumber | sources | 3 | 2 | 1.2 | done | The ArcGIS layer's issueDate includes renewals and there is no original-issue date; a licenseNumber not seen in yesterday's full snapshot (654 rows) is a genuinely new place. Needs a small stateful diff step (first-seen date per license). — 2026-10-16 done: openings_by_first_seen |
| I-057 | Find registration deadlines for Minneapolis | sources | 4 | 2 | 1.4 | done | auto: the Deadlines view is empty — the core promise — 2026-10-16 done: MPLS deadlines now from HCLib registration + HandsOn |
| I-055 | Find a parties & openings source for Minneapolis | sources | 4 | 2 | 1.4 | done | auto: 0 parties & openings events in Minneapolis right now — 2026-10-16 done: via I-058 |
| I-054 | Find a trivia nights source for Minneapolis | sources | 4 | 2 | 1.4 | done | auto: 0 trivia nights events in Minneapolis right now — 2026-10-16 done: 33 trivia events via Downtown Council/Luma |
| I-053 | Diff alerts: 'new this week' badge from first_seen | ux | 4 | 1 | 3.2 | done | first_seen is tracked already; newcomers love fresh stuff — 2026-10-16 done: pipeline is_new + badge |
| I-052 | Per-card 'report a problem' link → prefilled GitHub issue | data-quality | 3 | 1 | 2.4 | done | Crowd-sourced correction loop without accounts — 2026-10-16 done: prefilled GitHub issue link in drawer |
| I-051 | Neighborhood vibe cards: event mix by neighborhood (from coords) | features | 3 | 3 | 0.8 | done | Helps people choose where to live/hang out — 2026-10-16 done: web/src/lib/vibes.ts |
| I-050 | Venue capacity registry (config/venues) with Wikidata P1083 + source URLs | data-quality | 4 | 2 | 1.6 | done | Better attendance bands; currently mostly category priors — 2026-10-16 done: gotc/pipeline/venue_refs.py |
| I-049 | City 'starter pack' deadlines (library card, voter registration, transit pass, DMV 60-day rule) | features | 4 | 2 | 1.6 | done | Every new resident has the same deadlines; state rules are public — 2026-10-16 done: 10 states, 34 items |
| I-048 | Rainy-day swap: suggest an indoor alternative when an outdoor pick has ≥60% rain | features | 4 | 2 | 1.6 | done | Weather is attached now; plans can self-adjust — 2026-10-16 done: recommend.ts rain penalty with reason |
| I-047 | 'Leagues registering now' wave timeline per city (opens→closes bars) | features | 4 | 3 | 1.07 | done | League signups come in seasonal waves; a Gantt-like strip shows what's open now — 2026-10-16 done: RegistrationWaves in Deadlines view |
| I-046 | Evidence-quote page-watch as a generic verifier for any curated fact | data-quality | 5 | 2 | 2.0 | done | Shipped inside curated adapter; generalize to venue capacities and recurring schedules — 2026-10-16 done: curated adapter page-watch |
| I-038 | City onboarding checklist (DMV, voter registration, library card, transit pass) as deadlines | features | 4 | 2 | 1.6 | done | Every new resident has the same 10 deadlines; nobody lists them — 2026-10-16 done: dup of starter pack I-049 (shipped) |
| I-035 | Freshness SLA per field shown on cards ('checked 2h ago') | ux | 4 | 1 | 3.6 | done | Trust — 2026-10-16 done: 'checked 2h ago' on every card + stale badges |
| I-034 | Recorded-fixture adapter tests (tests never hit the internet) | infra | 5 | 2 | 2.25 | done | Engineering bar — 2026-10-16 done: tests/fixtures + FixtureTransport; never hits network |
| I-033 | Map view clustering + 'near me' by neighborhood | ux | 4 | 3 | 1.07 | done | Distance filter in the pitch — 2026-10-16 done: markercluster |
| I-032 | NYC permitted events (block parties, street fairs) via Socrata | sources | 5 | 1 | 4.5 | done | Exactly the 'block party' pitch, keyless — 2026-10-16 done: nyc_permitted_events (social event types only), 549 records live 2026-10-16 |
| I-031 | Library systems via BiblioCommons RSS (Hennepin, Chicago, Boston) | sources | 4 | 2 | 1.6 | done | Free classes, clubs, talks — high-quality keyless data — 2026-10-16 done: bibliocommons adapter; hclib/chipublib/bpl live 2026-10-16 (254/969/440 records) |
| I-027 | Shareable links (state in URL) + saved events in localStorage | features | 4 | 2 | 1.8 | done | Share a plan with a friend — 2026-10-16 done: hash router encodes view+filters; saved in localStorage |
| I-026 | 'Good for meeting people' filter + social score explanations | features | 4 | 1 | 3.6 | done | Newcomers want people, not just events — 2026-10-16 done: filter chip + social score reasons in drawer |
| I-025 | Health page in the dashboard (per-source state, last success, SLA, errors) | health | 5 | 2 | 2.25 | done | Observability inside the product — 2026-10-16 done: in-app Health view + header freshness pill |
| I-024 | Wikidata SPARQL for venue capacities (P1083) with source links | data-quality | 4 | 2 | 1.4 | done | Better attendance estimates from real capacities — 2026-10-16 done: dup of I-050; shipped |
| I-023 | Auto-open a GitHub issue when a unit gets quarantined | health | 4 | 2 | 1.6 | done | Failures loud even when nobody watches the dashboard — 2026-10-16 done: scripts/health_issues.py opens/closes per unit |
| I-022 | GitHub Actions: hourly refresh, DB persisted via cache + data branch, Pages deploy | infra | 5 | 2 | 2.25 | done | It must auto-update — 2026-10-16 done: ci.yml + hourly refresh.yml, state on orphan branch |
| I-020 | Curated league registry (YAML) with verified dates + page-watch to detect changes | sources | 5 | 3 | 1.33 | done | Beer leagues have no APIs; curated + monitored is the honest path — 2026-10-16 done: curated adapter + page-watch shipped |
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
| I-217 | Scraping Hands On Atlanta dashboard | sources | 2 | 2 | 0.8 | rejected | Rejected: custom app, no feed, ToS unclear |
| I-216 | Georgetown BID Tribe feed | sources | 1 | 1 | 0.8 | rejected | Rejected: mostly daily retail promos |
| I-210 | CivicPlus RSS adapter for Midwest metros | sources | 2 | 2 | 0.8 | rejected | Rejected: candidates tiny or mostly board meetings |
| I-204 | SOLVE volunteer listings | sources | 2 | 1 | 1.6 | rejected | Rejected: terms forbid data mining |
| I-203 | San Diego Reader calendar | sources | 2 | 1 | 1.6 | rejected | Rejected: terms forbid scraping |
| I-193 | OKC garage-sale permits | sources | 1 | 1 | 0.8 | rejected | Rejected: private home addresses |
| I-192 | CT business registry as openings | sources | 2 | 2 | 0.8 | rejected | Rejected: formations aren't openings and rows carry personal data |
| I-191 | jaxevents.com (Legends Global) | sources | 2 | 1 | 1.6 | rejected | Rejected: terms forbid robots |
| I-180 | Guess Communico tenants from the city name (<name>.libnet.info) | sources | 2 | 1 | 1.6 | rejected | Cheap library discovery. — 2026-10-16 rejected: Unknown libnet.info subdomains 302 to google.co.uk (we'd be fetching Google), and names collide across states (hcpl = Harford County MD, not Harris County TX). Only fingerprinted links from a library's own homepage are probed. |
| I-179 | Keep Nominatim at 1 req/s with a per-run cap | pipeline | 3 | 1 | 2.4 | rejected | Would keep place-name geocoding as before. — 2026-10-16 rejected: nominatim.openstreetmap.org/robots.txt disallows /search and the OSMF policy limits recurring scripts to 4 req/min and strongly discourages periodic app use. Nominatim is off by default; GOTC_NOMINATIM=1 is a compliant 15 s / 20-per-run lane. |
| I-178 | Urban Institute Education Data API (cbsa= filter) for university discovery | sources | 3 | 1 | 2.4 | rejected | Has IPEDS by CBSA in one call. — 2026-10-16 rejected: educationdata.urban.org/robots.txt says Disallow: /api/. Use College Scorecard (api.data.gov key) instead (I-116). |
| I-177 | Wikidata venue capacities via www.wikidata.org/w/api.php (wbgetentities) | sources | 3 | 1 | 2.4 | rejected | Considered as the SPARQL replacement. — 2026-10-16 rejected: www.wikidata.org/robots.txt disallows /w/ (so /w/api.php), /api/ and /wiki/Special: for all agents (checked 2026-10-16). Venue capacities come from config/venues instead. |
| I-167 | Ranking engine v2: pipeline rank hints (schema 1.5.0), normalized linear score with contributions, MMR + hard caps, honest explanations, on-device affinity, offline eval | features | 5 | 4 | 1.0 | rejected | RANKING.md rollout steps 1-6; results in RANKING.md section 7 — 2026-10-16 rejected: Duplicate of I-130 (Ranking v2), which is now done |
| I-157 | Mixing online events into city results | data-quality | 1 | 1 | 0.8 | rejected | Rejected: Meetup/Eventbrite do it and it dilutes 'what's on in my city' |
| I-156 | Event photos scraped from organizer pages | ux | 2 | 2 | 0.8 | rejected | Rejected: rights unclear; generated art instead |
| I-155 | Per-card static map thumbnails from OSM tiles | ux | 2 | 2 | 0.8 | rejected | Rejected: bulk tile prefetch violates the OSMF tile policy |
| I-154 | Server-side accounts to sync saves | features | 2 | 4 | 0.4 | rejected | Rejected for now: privacy-first; share links and .ics cover cross-device |
| I-153 | Gamification: streaks, badges, confetti for attending | ux | 1 | 2 | 0.4 | rejected | Rejected: the brief forbids it; trust over engagement tricks |
| I-152 | 'Selling fast' badges without evidence | ux | 1 | 1 | 0.8 | rejected | Rejected: Eventbrite shows them on most cards; we require a real signal (ADR-0006) |
| I-151 | Newsletter pop-ups and app-install gates | growth | 1 | 1 | 0.8 | rejected | Rejected: Time Out's three pop-ups are an anti-pattern for a trusted guide |
| I-150 | Paid/promoted placement slots | growth | 1 | 2 | 0.4 | rejected | Rejected: competitors' promoted slots erode trust; we sell nothing |
| I-045 | Showing a precise '% tickets left' from any source | data-quality | 4 | 2 | 1.6 | rejected | No legit source exposes seat inventory to third parties; we show labeled signals with bands instead |
| I-044 | Yelp Events API | sources | 3 | 2 | 1.2 | rejected | $229+/mo after trial |
| I-043 | DoStuff network (Do512/Do312) scraping | sources | 4 | 2 | 1.6 | rejected | No API and actively blocks bots — ask for a partnership instead |
| I-042 | Resident Advisor scraping | sources | 3 | 2 | 1.2 | rejected | Terms §4.4 ban scraping; undocumented GraphQL |
| I-041 | Bandsintown API | sources | 3 | 2 | 1.2 | rejected | Terms limit use to artists' own data and forbid mixing with other sources without distinction |
| I-040 | Songkick API | sources | 4 | 2 | 1.6 | rejected | Paid license; no new hobbyist approvals |
| I-039 | Eventbrite city-wide search | sources | 4 | 2 | 1.6 | rejected | Eventbrite removed public event search in 2019 (404); only per-organizer/venue access remains |

