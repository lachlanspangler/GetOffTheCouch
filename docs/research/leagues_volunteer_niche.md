# Research: adult rec leagues, volunteer, and niche sources

**Checked:** 2026-10-15 · **Method:** polite `curl` with UA `GetOffTheCouch-research/0.1 (contact: spanglew@amazon.com)`, at least 2 s between requests (at least 5 s for minneapolisparks.org). Every robots.txt here was actually fetched. ToS pages were fetched and searched for scrape/robot/spider/crawl/automated clauses. No challenge pages were bypassed and no UA was spoofed. No credentials embedded in third-party pages were reused.
**Companion files:** `seed_registry.yaml` (93 verified entries) and `samples/` (real responses, ≤5 records, trimmed only).

## TL;DR: recommendations

| # | Source | Category | Access path | Auth | robots | ToS | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **Volo Sports** (+ ZogSports, merged) | leagues | SSR HTML `volosports.com/discover/{city}?category=leagues&page=N` | none | allow | personal-use license, no scrape clause | **ADAPTER** (daily, low volume). Covers Boston, Denver, LA, Miami, NYC |
| 2 | **LeagueLab** widget (Nashville Sports Leagues, Underdog Seattle) | leagues | `widget.leaguelab.com/v1/{org}/league-listing` HTML table with **Signup Deadline** | none | allow (crawl-delay 5) | **bans automated access without permission** | **PERMISSION-GATED ADAPTER**: email for permission, parser ready |
| 3 | **LeagueApps** (CSSC Chicago, BSSC Boston, CLUBWAKA Mpls) | leagues | legacy `/leagues?pg=N` HTML. Official `public.leagueapps.io` API needs a per-org key | org API key | empty/allow | **bans automated tools** | **CURATED + request API key** from each org |
| 4 | TeamSideline (Minneapolis Parks adult leagues) | leagues | none (Cloudflare 403 even on robots.txt) | n/a | blocked | n/a | **REJECT automation**; page-watch the MPRB landing page |
| 5 | Austin SSC, St. Paul CC, Chaska CC, Pickleheads, MN Broomball | leagues | Cloudflare/TLS blocks | n/a | n/a | n/a | **CURATED-MANUAL** |
| 6 | Curling clubs (Frogtown, Four Seasons, Denver CC, Nashville CC) | leagues | readable club HTML. Registration on FinnlyConnect (robots `Disallow: /`) / CCM / Playpass | none | mixed | n/a | **CURATED + page-watch** |
| 7 | **Eventbrite** organizer pages (Hollywood Curling, Fleet Feet Chicago) | leagues/niche | official API `/v3/organizers/{id}/events/` (+ JSON-LD on event pages) | OAuth token (free) | `/e/` allowed | API terms | **ADAPTER via official API** (organizer-ID registry) |
| 8 | **HandsOn Connect** (Boston Cares, Hands On Nashville, L.A. Works, NYC Service, UW Austin) | volunteer | `POST /search/getOpportunitiesCalendar` JSON | none | 404 (none) | none found | **ADAPTER** (1–3 day windows) |
| 9 | **Galaxy Digital Get Connected** (HandsOn Twin Cities, UW King County) | volunteer | `/need/rss/` + SSR `/need/`, `/need/detail/` | none (API = tenant Bearer key) | allow | no clause | **ADAPTER**; ask orgs for API keys |
| 10 | **MPRB The Events Calendar REST** | volunteer/events | `/wp-json/tribe/events/v1/events` | none | `/wp-json` allowed, `?ical=` disallowed | public agency | **ADAPTER** (≥5 s spacing, returns 429 fast) |
| 11 | **NYC Parks via NYC Open Data** `w3wp-dpdi` | volunteer/events | Socrata | none/app token | n/a | open data | **ADAPTER** |
| 12 | Idealist (VolunteerMatch merged in) | volunteer | paid "Open Network API" | paid key | allow | **bans scraping** | **REJECT scraping; apply for API** |
| 13 | JustServe / Points of Light Engage / AmeriCorps | volunteer | OAuth / Livewire / WAF | n/a | n/a | PoL **bans automation** | **REJECT** (contact JustServe for a partnership) |
| 14 | Chicago Cares, New York Cares, United Way Miami, Mile High UW | volunteer | Salesforce / Drupal JS / Andar / 403 | n/a | mixed | n/a | **CURATED** (+ sitemap watch for Chicago Cares) |
| 15 | **UpcomingCons** | niche (cons) | HTML with schema.org `Event` microdata | none | empty | no clause | **ADAPTER** (weekly) |
| 16 | **Maker Faire** | niche | `makerfaire.com/query/?type=map` JSON (2,522 rows) | none | allow | no clause | **ADAPTER** (weekly) |
| 17 | **Geeks Who Drink** | niche (trivia) | `admin-ajax.php?action=mb_display_mapped_events` (page nonce) | none | admin-ajax explicitly allowed | no clause | **ADAPTER** (weekly, 1 request). Not in MN |
| 18 | **Luma** calendars | niche / Meetup alternative | `api.lu.ma/ics/get?entity=calendar&id=cal-…` ICS | none | allow | no clause | **ADAPTER** (ICS per curated calendar) |
| 19 | Car Show Radar | niche | WP REST posts by state category (free-text dates) | none | allow | no clause | ADAPTER, low priority |
| 20 | Wikidata SPARQL / WikiFur API | niche | SPARQL / MediaWiki API | none | API use OK | CC0 / CC-BY-SA | **ENTITY REGISTRY ONLY**: no upcoming edition dates (0 of 41 US anime cons had 2026+) |
| 21 | Trivia Mafia (MN) | niche | `/locations` HTML. Day/time only via Storepoint API (robots `Disallow: /`) | none | blocked for API | n/a | **CURATED + ask permission** |
| 22 | furrycons.com, animecons.com, fancons.com | niche | Cloudflare challenge even on robots.txt | n/a | blocked | n/a | **REJECT** (UpcomingCons covers them) |
| 23 | renfaire.com / renfaires.com / carshowfinder.org | niche | frozen 2015 data / parked / SEO blog | n/a | n/a | n/a | **REJECT** (renfaire.com sitemap: one-time name/URL discovery only) |
| 24 | Sporcle Live, Strava, Facebook Events | niche | robots-disallowed / API agreement / no public search | n/a | n/a | prohibitive | **REJECT** |
| 25 | Meetup GraphQL | niche | `api.meetup.com/gql-ext` | OAuth | allow | ToS behind challenge | **DEFER** (get an OAuth client and confirm the access tier) |
| 26 | Official con/faire/run-club sites (Furry Migration, Anime Detour, Twin Cities Con, MarsCon, Mill City Running, MSRA Back to the 50's) | niche | homepage text | none | allow | n/a | **CURATED + yearly/monthly page-watch** |

### Takeaways for the pipeline design
1. **Build adapters per platform, not per org.** One `volo`, one `leaguelab`, one `handsonconnect`, one `galaxydigital`, one `tribe_events` (WordPress The Events Calendar), one `eventbrite`, one `ics`, and one `socrata` adapter. Then adding a city or org is a config row (`{platform, base_url, tenant_id, city}`).
2. **The best "register-by" data sits behind ToS gates** (LeagueLab, LeagueApps). Treat permission outreach as a deliverable. A draft list of contacts is below. Until permission arrives, these orgs go in the curated registry with page-watch hashing of their *own* marketing pages (not the platform).
3. **Never fake deadlines.** Volo gives `Closes M/D` and `Price goes up M/D`. LeagueLab gives `Signup Deadline`. HandsOn Connect gives only shift times plus `volunteersStillNeeded`. Most volunteer shifts have no separate deadline.
4. **Year-less dates and server-relative strings.** Volo prints `10/19` and "Closing in 8m" / "Tomorrow 10/17" (it looks like the server uses UTC). LeagueApps prints EDT times for a Chicago org. Store raw strings, `fetched_at`, and the inferred value with confidence.
5. **Staleness is real.** Memory Lanes still links a *2025* winter league PDF in Oct 2026. Per-detail-page UpcomingCons entries can show 2016 editions. renfaire.com is frozen at 2015. Health checks should flag `season_year < current_season`.
6. **Rate limits.** minneapolisparks.org returned 429 on the 3rd request within ~5 s. Boston Cares returned about 1 MB per 7-day window. Respect `Crawl-delay` (ASSC 20, BSSC/Zog 10, clubwaka 3, LeagueLab 5).

### Permission / API-key outreach list
| Org / platform | Ask for | Contact path |
|---|---|---|
| Nashville Sports Leagues / Underdog Sports Leagues / League Lab | written permission to read the public league-listing widget daily | NSL P.O. Box 60273 Nashville TN (site contact form); underdogseattle.com contact; leaguelab.com |
| Chicago Sport & Social Club, BSSC, CLUBWAKA | LeagueApps public API key (`x-api-key`, per site) | org contact pages (CLUBWAKA: info@clubwaka.com, listed on clubwaka.com) |
| Volo Sports | partner/affiliate feed (we'll use public pages meanwhile) | volosports.com/contact-us |
| Trivia Mafia | permission to use their Storepoint locator feed | triviamafia.com |
| Idealist | Open Network API quote | idealist.org/en/open-network-api ("Submit an Inquiry") |
| HandsOn Twin Cities, UW King County | Galaxy Digital API key (Bearer) | org volunteer centers |
| JustServe | data partnership | justserve.org |

---

## 1. Adult rec / beer leagues

### Key finding: leagues live on a handful of SaaS platforms

The operator (Volo, CSSC, Underdog, a parks department) doesn't decide how we get the data. The registration platform behind the operator does. We found these:

| Platform | Who uses it (verified) | Public data surface | robots.txt | ToS on automated access | Verdict |
|---|---|---|---|---|---|
| **Volo (own Next.js app)** | Volo: Boston, Denver, LA, Miami, NYC metro (+ ZogSports, which merged into Volo) | Server-rendered HTML at `/discover/{city}?category=leagues&page=N` (24 cards/page) | `Allow: /`, only `/rfo /admin /staff` disallowed | PDF ToS gives a "personal, non-commercial" license. Bans reproducing the Service and circumventing access controls. **No scraping/robot clause** (grepped the full PDF text) | **Adapter (low volume)**, link back to Volo. Also ask Volo for a partnership/affiliate feed |
| **LeagueApps** | Chicago Sport & Social Club (`chicagosocial.leagueapps.com`), BSSC Boston (siteId 47536, widget), CLUBWAKA Minneapolis (`clubwakaminneapolis.leagueapps.com`) | Legacy `/leagues?pg=N` HTML (CSSC only) has full fees and reg windows. Newer sites only show an SPA member portal. Official public API `public.leagueapps.io/v1/sites/{siteId}/programs/current?x-api-key=` returns `403 {"errorCode":40001,"message":"Invalid API Key"}` without a key | Org subdomains serve an **empty** robots.txt (no rules). `widgets.leagueapps.com` has `User-agent: *` with no Disallow | **ToS forbids it**: "Using automated tools to access, upload or download content is not permitted." and bans any "robot, spider ... to retrieve, index, 'data mine'" | **Curated registry + ask each org for its LeagueApps API key** (keys are issued per org). Never reuse the key the embed widget fetches from `getWidgetConfig` |
| **LeagueLab** | Nashville Sports Leagues, Underdog Sports Leagues Seattle (`underdogseattle.com`) | `https://widget.leaguelab.com/v1/{org}/league-listing` is a public embeddable HTML table with **Signup Deadline, Start Date, Team/Individual Price, Status**. Org sites have `/leagues?v=upcoming` | Org sites: `User-agent: * Disallow:` + `Crawl-delay: 5`. widget host has no robots.txt (falls through to leaguelab.com, which only blocks wp-admin) | **ToS forbids it without permission**: "You will not collect users' content or information, or otherwise access League Lab, using automated means (such as harvesting bots, robots, spiders, or scrapers) without our permission." | **Permission-gated adapter**: best data quality of all platforms. Email NSL/Underdog/LeagueLab for written permission. Until then, curated registry |
| **TeamSideline** | Minneapolis Park & Rec Board adult leagues (`teamsideline.com/sites/minneapolisparks`) | none reachable | `robots.txt` itself returns **403 Cloudflare "Just a moment..."** | n/a (can't even read it) | **Reject automation**. Page-watch the MPRB landing page instead |
| **FinnlyConnect** | Four Seasons Curling Club (Blaine, MN) learn-to-curl registration | SPA | `User-agent: * Disallow: /` | n/a | **Reject**. Curated |
| **Playpass** | Nashville Curling Club | Org page has schema.org `SportsOrganization` JSON-LD (no events) | `Disallow: /activities/ /dashboard/ /organizers/ ...` | not checked | Curated (org page only) |
| **CurlingClubManager / Joomla JEvents** | Frogtown Curling Club (St. Paul), Denver Curling Club | Server-rendered HTML. Joomla RSS `/index.php?format=feed&type=rss` (club news). JEvents iCal export returned **HTTP 500** | Joomla default (only admin/system dirs disallowed) | not found | Curated + page-watch (low-frequency RSS for news) |
| **Eventbrite** | Hollywood Curling (LA) learn-to-curl sessions | Event pages carry schema.org `EducationEvent` JSON-LD with `startDate`, `offers.lowPrice`, `availabilityEnds`. Official API: `/v3/organizers/{id}/events/` (OAuth token) | `/e/` pages not disallowed for `*` | use the official API | **Adapter via Eventbrite API** (organizer-ID registry). Many small clubs sell clinics this way |
| **Cloudflare-challenged sites** | Austin Sports & Social Club (`austinssc.com`), St. Paul Curling Club, Chaska Curling Center, Pickleheads, MN Broomball (TLS reset) | none | ASSC robots allows all, `Crawl-delay: 20`, but the homepage returns a 403 challenge | n/a | **Curated registry only.** Never try to get around the challenge |

### Volo Sports (incl. ZogSports)
- **Endpoint:** `GET https://www.volosports.com/discover/{city-slug}?category=leagues&page={N}`. City slugs come from `https://www.volosports.com/sitemap.xml`: `boston, denver, los-angeles, miami, new-york-metro-area` cover our seed cities (also baltimore, washington-dc, san-diego, san-francisco, philadelphia, ...). The page redirects to add `&includeFees=true` in some cities (Boston, LA), and those prices include fees. `page=2` returned 24 cards with no overlap with page 1. "N ways to play" gives the total (Denver 98, Boston 92, NYC 126, LA 47, Miami 17 on 2026-10-15).
- **Auth:** none.
- **Fields per card:** league UUID (`/l/{uuid}`), program type (League / Pickup / Tournament), weekday, title (sport + level + neighborhood), venue name, start date (`M/D`, **no year**), weeks, time window, early-bird vs regular price per player and per team, gender format (Coed/Open/Men's/Women's), skill level, team size (e.g. 6v6), badges ("Price goes up 10/17", "1 TEAM SPOT LEFT", "SOLD OUT! Limited Free Agents Only!", "STAFF PICK"), and close status ("Closes 11/6", "Closing in 2h 17m", "Last chance").
- **Gotchas:** dates have no year, so infer the year from fetch time. Relative strings ("Closing in 8m", "Tomorrow 10/17") are computed server-side. NYC showed "Tomorrow 10/17" at ~03:50 UTC 10/16, which suggests the server uses UTC, not city local time. Prefer absolute values and store `fetched_at`. The `/l/{uuid}` detail page is a client-rendered SPA with no SSR data.
- **Behind the scenes:** the SPA bundle references Hasura (`REACT_APP_HASURA_URL`) with a `/graphql` path and queries named `LeagueSearch`, `getLeague`, and so on. Anonymous POSTs to `www.volosports.com/{graphql,v1/graphql,api/graphql}` returned the HTML shell, and `api.volosports.com/{graphql,v1/graphql}` returned 404. **We don't recommend reverse-engineering the private GraphQL**: the ToS bans circumventing access controls, and it's undocumented.
- **City sport pages** (`/denver/kickball`) carry only `SportsActivityLocation` + `FAQPage` JSON-LD. Example FAQ: "You can expect your Volo kickball league to be anywhere from $39-$89 per player for the entire season." This is useful as a price prior.
- Volo also has `/{city}/volunteer` pages (Denver, LA). The volunteer section covers them.
- **Cadence:** daily (prices step up on early-bird deadlines; "Closing in" changes hourly). Total cost: about 5 cities × ≤6 pages/day.
- **Sample:** `samples/volo-discover-denver-leagues.html` (5 cards, unmodified markup).
- **Recommendation:** **ADAPTER** (HTML parse, ≤1 req/5 s, daily). Facts only (title/date/price/deadline) plus a deep link. Health check: card count > 0 and "ways to play" number parsed. Separately, ask Volo for a partner feed.

### Chicago Sport & Social Club (CSSC), on LeagueApps
- Site `https://chicagosocial.com` (old domain chicagosportandsocialclub.com redirects; https on the old domain refused the connection). Registration is at `https://chicagosocial.leagueapps.com/leagues` (387 KB legacy HTML, 50 programs/page, pagination `?pg=1`).
- Per-program markup is very structured: `<li id="baseevent-{programId}">`, `dd.program-list-season`, `dd.program-list-starts`, `dd.program-list-registration-dates` (early-bird and regular windows!), `dd.program-list-location`, `.base-gamedays strong` (weekday), `.base-format`, `.early-bird-price` / `.regular-price` (team and free-agent fees, "+ 5.0% Processing Fee").
- Quirk: registration windows render in EDT (`Wed Sep 23 23:59:59 EDT 2026`) even though this is a Chicago org.
- Sport filter list includes **Broomball** and **Curling** as well as kickball, bowling, pickleball, and more.
- **Sample:** `samples/leagueapps-chicagosocial-leagues.html` (5 program blocks, from a single research fetch).
- **Recommendation:** **CURATED + request API key.** The data is perfect, but LeagueApps ToS bans automated download. Ask CSSC for an `x-api-key` (LeagueApps public API is per-site) or a CSV/feed. Until then, store the org in the registry with the human-visited listing URL and a manual "season opens" note.

### Boston Ski & Sports Club (BSSC), on LeagueApps
- `https://bssc.com/sports/?la-state=OPEN_REGISTRATIONS&la-sport=...`. The program grid is an iframe widget (`leagueappwidget.web.app`, `generateLeagueWidget('9b694738-...')`) backed by `us-central1-leagueappwidget.cloudfunctions.net/getWidgetConfig` → `public.leagueapps.io/v1/sites/{siteId}/programs/current?x-api-key=...`. LeagueApps siteId **47536** (from the login link).
- robots: Yoast `Disallow:` (allow all) + `Crawl-delay: 10`.
- **Recommendation:** **CURATED + request API key.** We must not reuse a widget-config key.

### CLUBWAKA (World Adult Kickball Association)
- `waka.com` is a **TV station** (WAKA Action 8 News, Montgomery AL), not the kickball org. The real orgs are `kickball.com` (World Kickball Association) and `clubwaka.com`.
- `https://kickball.com/join-the-fun/` lists CLUBWAKA markets, including **Boston MA, Los Angeles CA, Miami FL, Minneapolis MN** (also Ft. Lauderdale, West Palm Beach, Orange County, ...).
- `https://clubwaka.com/locations/minneapolis-2/` (redirected from `/leagues/minneapolis`) embeds the official LeagueApps listing widget (`widgets.leagueapps.com`, id `882a4259-...`). Registration is at `clubwakaminneapolis.leagueapps.com` (SPA portal; `/leagues` legacy listing not available).
- robots (Flywheel): `Disallow: /*?`, `Allow: /locations/*?la-state=`, `Crawl-delay: 3`.
- **Recommendation:** **CURATED** (market list from kickball.com, which is WordPress with an open `wp-json`). Page-watch `clubwaka.com/locations/{city}` monthly. API key request same as LeagueApps.

### Underdog Sports Leagues (Seattle), on LeagueLab
- `underdogsportsleagues.com` meta-refreshes to `https://www.underdogseattle.com`. (`underdogsports.com` is an unrelated fantasy-sports company.)
- `/leagues?v=upcoming` (504 KB SSR) shows division-level status, cost, deposit, deadlines, and start dates (see seed_registry.yaml quotes).
- robots: `User-agent: * Disallow:` + `Crawl-delay: 5` (SemrushBot blocked). LeagueLab ToS applies (automated access needs permission).
- **Recommendation:** **permission-gated adapter** (same LeagueLab parser as Nashville). Curated until permission arrives.

### Nashville Sports Leagues (NSL), on LeagueLab
- Sport pages (e.g. `/kickball/`) embed `https://widget.leaguelab.com/v1/nashvillesportsleagues/league-listing?sport=Kickball`. The `sport` param didn't filter server-side; all 43 rows came back.
- Row markup: `<tr class=widget-league-listing id="widget-league-listing-{id}" data-sports=... data-days=... data-statuss="Open" data-genders=... data-leaguetypes=... data-signuptypes=...>` with labelled cells: League Name, Sport, Location, Days, Start Time(s), Skill Level(s), Gender(s), Format, Team Price, Individual Price, **Start Date**, **Signup Deadline**, **Status**.
- **Sample:** `samples/leaguelab-nashville-listing.html` (header + 5 rows).
- **Recommendation:** best "register-by" data found anywhere. **Ask permission**, then build the adapter (daily).

### Austin Sports & Social Club (ASSC)
- `austinsportsandsocial.com` redirects to `https://austinssc.com`, which returns **403 Cloudflare challenge** to curl. robots.txt (readable): `User-Agent: * Allow: / Crawl-delay: 20`.
- **Recommendation:** **CURATED** (no automation; don't get around the challenge). Volo isn't in Austin.

### Denver
- `dssc.com` is "Data Systems Search Consultants". There is no "Denver Sports & Social Club" domain (`denversportsandsocialclub.com` and similar names don't resolve). **Volo Denver** is the major operator (98 listings). Denver Curling Club (`denvercurlingclub.com`, CurlingClubManager) is curated.

### Miami / LA / NYC
- Miami: Volo (17 listings) and CLUBWAKA Miami. Miami Sport & Social domains don't resolve.
- LA: Volo (47), ZogSports LA (now Volo), CLUBWAKA LA, Hollywood Curling (Eventbrite).
- NYC: Volo NY metro (126) and ZogSports NY, which merged: "ZogSports is officially joining forces with Volo Sports!" (`https://play.zogsports.com/zogsports-volo`). Sports Monster (`sportsmonster.net`) exists (NJ/NY area), not deep-checked.

### Minneapolis-specific
- **Minneapolis Park & Recreation Board (MPRB) adult leagues.** `https://www.minneapolisparks.org/activities-events/sports_leagues/adult_sports_leagues/` lists Spring/Summer, Fall, and Winter 2026 sports, including **Broomball (indoor + outdoor), Pond Hockey, Pickleball, Kickball, Kubb, Mölkky, Cornhole, Bocce, Dodgeball**. Registration happens on TeamSideline (blocked). The MPRB site itself is WordPress + The Events Calendar with an open REST API (`/wp-json/tribe/events/v1/events`). That API is great for volunteer and park events, but the league registrations aren't in it. **Rate limit:** the 3rd request within ~5 s returned **HTTP 429**. robots disallows the `?ical=` / `eventDisplay=` / `tribe-bar-date=` query permutations (it doesn't disallow `/wp-json/`). Use ≥5 s spacing and ≤1 run/day.
- **Curling:** Frogtown Curling Club (St. Paul, Joomla, readable), Four Seasons Curling Club (Blaine; site now at `fogertyarena.com/curling-club/`; registration on FinnlyConnect with robots `Disallow: /`), St. Paul Curling Club (`stpaulcurlingclub.org`, 403 to non-browser UA), Chaska Curling Center (403 Cloudflare). All curated.
- **Broomball:** MPRB indoor/winter broomball (TeamSideline). `mnbroomball.org` resolves but TLS-resets. `usabroomball.com` is now a **gambling spam site** (domain lapsed). Don't link to it.
- **Bowling:** Memory Lanes (`memorylanes.com`, WordPress, empty robots.txt). The "Winter Bowling Leagues" page links a **2025** sign-up PDF (`/wp-content/uploads/2024/12/2025-Winter-sign-up.pdf`) that was still posted in Oct 2026. Treat it as **stale**, which is a good test case for staleness detection. Bryant Lake Bowl's bowling page states "We never have leagues." (but it has a trivia night; see niche).
- **Not found / not real (as of 2026-10-15):** "Minneapolis Sport & Social", "Twin Cities Kickball", "MN Sport & Social Club". None of mnsportandsocial.com, twincitieskickball.com, mplskickball.com, socialsportsmn.com, or minnesotasportandsocial.com resolve. `mnssc.org` resolves but refused TLS. `tcsportsclub.com` is a "Coming Soon" Squarespace page. Don't seed these.

### Pickleball & bowling directories
- **Pickleheads:** robots disallows `/api/` and some paths, and `/terms` returns 403 to curl (bot protection). **Reject.**
- **USBC (bowl.com):** robots `Allow: /`. League finder not deep-checked. Candidate for a later pass.
- **DUPR:** robots allows most. API is for clubs/partners. Not a public event feed.
- **SportsEngine / DaySmart (Dash):** robots have broad per-bot `Disallow: /` blocks. Skip.
- MPRB pickleball leagues (TeamSideline) and Volo pickleball (Denver, NYC "Party Pickleball") are the realistic sources.

---

## 2. Volunteer sources

All checks done 2026-10-15 with UA `GetOffTheCouch-research/0.1 (contact: spanglew@amazon.com)`, about 2 s between requests. "robots" means the live robots.txt was fetched. "ToS" means the terms page was fetched and searched for scrape/robot/spider/crawl/automated clauses.

### Key finding: three white-label platforms cover most US HandsOn / United Way portals

Most city volunteer centers don't build their own sites. They run on a few SaaS platforms, and each platform exposes the same public endpoints on every tenant. **HandsOn Connect** and **Galaxy Digital Get Connected** are now both owned by Better Impact (the handsonconnect.org banner says: "HandsOn Connect & Get Connected by Galaxy Digital are now part of Better Impact"). One adapter per platform covers many cities, and adding a tenant becomes a config change.

| Platform | Tenants verified (seed cities) | Keyless machine-readable surface |
|---|---|---|
| HandsOn Connect (HOC) | Boston Cares, Hands On Greater Nashville, L.A. Works, NYC Service, United Way for Greater Austin | `POST /search/getOpportunitiesCalendar` returns JSON (the same endpoint the site's own calendar uses) |
| Galaxy Digital Get Connected | HandsOn Twin Cities, United Way of King County (Seattle) | `GET /need/rss/` (RSS 2.0, 15 newest) plus server-rendered `/need/` table and `/calendar/` |
| The Events Calendar (WordPress) | Minneapolis Park & Rec Board | `GET /wp-json/tribe/events/v1/events` (JSON) |

---

### 2.1 HandsOn Connect: `POST {site}/search/getOpportunitiesCalendar`

- **Tenants verified:** www.bostoncares.org (block 589), handson.unitedwaygreaternashville.org (hon.org redirects there; block 2009), volunteer.laworks.com (works without a block id), www.nycservice.org (block 2073), volunteer.uwatx.org (block 447; without a block id it returned 0 items).
- **Request:** form-encoded POST with `searchvo_startfrom=YYYY-MM-DD&searchvo_endfrom=YYYY-MM-DD&searchvo_searchresultblockid=<id from <input name="calendar-search-block-id"> on /calendar>`. Any other date format or param name returns `{"message":"The StartFrom or EndFrom are invalid dates...","code":400}`. I took the request shape from the site's own JS bundle (`parametersAPI['searchvo_startfrom'] = startDateView` …, `$.ajax({method:"POST", url: urlSite + '/search/getOpportunitiesCalendar'})`).
- **Auth:** none.
- **robots:** bostoncares.org/robots.txt, hon/handson.unitedwaygreaternashville.org and volunteer.laworks.com/robots.txt all return **404**, so there are no restrictions. nycservice.org/robots.txt is also 404.
- **ToS:** HOC's platform site has a privacy policy but no terms page at /terms-of-use/ or /terms-of-service/ (both 404). The tenant sites I checked have no terms link in the footer. No anti-scraping clause found.
- **Fields per occurrence:** `opportunityName, opportunityLink, organizationServedName, organizationServedId, managingOrganization, description, startDateTimeISO, endDateTimeISO, startTime, endTime, timezone, locationCity, locationState, locationZipCode, locationType, maximumAttendance, volunteersStillNeeded, opportunityType, scheduledType, managedBy, occurrenceId, miniSitePath`. Responses are grouped by `dayDate`, and each response also carries facet lists (causes, populationsServed …).
- **Volume:** Boston Cares returned 314 occurrences and about 1 MB for a 7-day window. Nashville returned 111 occurrences and 273 KB for 3 days. **Query 1–3 day windows.** Descriptions are large.
- **Cadence:** shifts change daily, so fetch once a day per tenant for a rolling 14 to 30 days. `volunteersStillNeeded` gives a free "spots left" signal, so a second lighter fetch for the next 3 days is reasonable.
- **Sample:** `samples/handsonconnect-bostoncares-calendar.json` (first day, first 5 occurrences, facets dropped).
- **Recommendation: ADAPTER (high value).** One `handsonconnect` adapter with per-tenant config `{base_url, block_id, city}`. Find more tenants by looking for `cdn0.handsonconnect.org` in a site's HTML. Risk: the endpoint is undocumented. Add a health check that asserts `code==200` and that each item has the expected keys. It is polite to email each affiliate as well.

### 2.2 Galaxy Digital "Get Connected" portals

- **Tenants verified:** `handsontwincities.galaxydigital.com` (HandsOn Twin Cities, linked from handsontwincities.org) and `volunteer.uwkc.org` (United Way of King County, Seattle; `uwkc.galaxydigital.com` 301s to it). Guessed slugs for other cities all returned the "Galaxy Digital: Bad Domain" page. Tenants have to be found from each org's own site, not by guessing slugs.
- **Endpoints (keyless):**
  - `GET /need/rss/`: RSS 2.0 with the 15 newest needs (`title, link (need_id), pubDate, description(HTML), guid`). It has **no shift date, location or org**, so use it for discovery and incremental change detection. Sample: `samples/galaxydigital-handsontwincities-need-rss.xml`.
  - `GET /need/` (paginated `/need/index/<n>`): server-rendered table `<tr class="need">` with title, link, org (`.subtitle`) and date text ("Is Ongoing" / "Runs Until Dec 11, 2026"). Sample: `samples/galaxydigital-handsontwincities-needs.html`.
  - `GET /calendar/`: server-rendered month calendar with shift times and "N spots remaining" text.
  - `GET /need/detail/?need_id=N`: full detail (date, time, description).
  - `/event/rss/` does not exist (redirects to page_not_found).
- **Official API:** "Get Connected Client API v1.9.2" at `https://api.galaxydigital.com/docs/` (OpenAPI spec at `/docs/api.yml?v=1.9.2`). It has `/needs`, `/events`, `/agencies` and more, with `securitySchemes: Bearer (Authorization header)`. Unauthenticated `GET /api/needs` returns `401 {"message":"Unauthenticated."}`. The API is **tenant-admin scoped**, so each org would have to issue us a key.
- **robots:** `handsontwincities.galaxydigital.com/robots.txt` and `volunteer.uwkc.org/robots.txt` block a list of SEO bots by name. The `User-agent: *` group has `Disallow:` (empty), so everything is allowed.
- **ToS:** galaxydigital.com/terms-and-conditions has no scrape/robot/spider/crawl clause. It covers customer use of the SaaS.
- **Cadence:** RSS every 6 h. Fetch detail pages only for new or changed `need_id`s, and refresh the listing daily.
- **Recommendation: ADAPTER** (RSS for discovery, then detail-page parse). Upgrade path: ask HandsOn Twin Cities / UWKC for an API key.

### 2.3 Minneapolis Park & Recreation Board: The Events Calendar REST

- **Endpoint:** `GET https://www.minneapolisparks.org/wp-json/tribe/events/v1/events?categories=environmental-volunteer-opportunities&per_page=50&start_date=...`
- **Auth:** none.
- **robots:** allows `/wp-json/`. It disallows query-string calendar traps (`?tribe-bar-date=`, `?eventDisplay=`, `?ical=`, `?outlook-ical=`, `?format=ical`, `?tribe_eventcategory`, `?tribe_events_cat=`). **Do not use the `?ical=1` export**, because robots.txt disallows it. The REST `categories=` param is not on the disallow list.
- **Rate limit:** **HTTP 429 after about 3 requests in a few seconds.** Space requests by at least 5 s and back off on 429.
- **Fields:** `id, title, description(HTML), url, start_date, end_date, utc_*, timezone, all_day, cost, cost_details, categories[], venue{venue,address,city,zip,geo_lat,geo_lng}, organizer[], website, modified`, plus pagination `total, total_pages, next_rest_url`. On 2026-10-15 the volunteer category had `total: 34` upcoming events.
- **Sample:** `samples/mprb-tribe-events.json` (3 events).
- **Cadence:** daily.
- **Recommendation: ADAPTER.** It is the cleanest feed in this section. The same generic `tribe-events` adapter works on any WordPress site running The Events Calendar.

### 2.4 NYC Parks events: NYC Open Data (Socrata) `w3wp-dpdi`

- **Endpoint:** `https://data.cityofnewyork.us/resource/w3wp-dpdi.json?$q=volunteer&$limit=50` ("NYC Parks Public Events – Upcoming 14 Days", `data_updated_at 2026-10-15T13:19:45Z`, updated daily).
- **Auth:** none. A Socrata app token (free) raises rate limits. One `$where=upper(categories) like '%VOLUNTEER%'` query returned **503**, but `$q=volunteer` worked.
- **Why Socrata and not the site:** nycgovparks.org robots.txt has `Disallow: /xml/` and `Disallow: /*xml` for `User-agent: *`, which covers the site's RSS feed `/xml/events_300_rss.xml`. `/events/volunteer` also returned 403 (CloudFront) to our UA. The Open Data copy is the sanctioned channel.
- **Fields:** `title, guid, link.url, description, starttime, endtime, location, parknames, parkids, coordinates, categories (pipe-delimited; includes "Volunteer"), contact_phone, registration_url, image.url`.
- **Sample:** `samples/nyc-parks-socrata-w3wp-dpdi-volunteer.json` (5 records, unmodified).
- **Recommendation: ADAPTER** (it fits the generic Socrata adapter used elsewhere in the pipeline).

### 2.5 Idealist (includes VolunteerMatch)

- **VolunteerMatch is gone as a separate site.** volunteermatch.org redirects to `https://www.idealist.org/volunteermatch` ("VolunteerMatch is now part of Idealist"). `volunteermatch.org/robots.txt` returns 404.
- **robots (idealist.org):** `User-agent: *` only disallows `*/third-party-login?provider=*`, so it is permissive.
- **ToS (idealist.org/en/terms-of-service):** **prohibits** it. Quote: "(j) access or use the Services by means of any automated program … (including but not limited to spiders, robots, scrapers, crawlers, avatars, data mining tools, or the like) … (k) scrape, copy, republish, license or sell the data or information on the Services".
- **API:** "Open Network API" (`/en/open-network-api`) is a **paid, inquiry-based** product: "Open Network API Pricing … Plug the complete Volunteer Match, powered by Idealist database of vetted volunteering opportunities directly into your website or mobile app. Submit an Inquiry."
- **Recommendation: REJECT scraping. File a partnership/API inquiry** (it would be the largest national coverage) and stub the adapter behind `IDEALIST_API_KEY`.

### 2.6 JustServe

- **robots:** `User-Agent: *` with Allow `/projects`, `/organizations` …, Disallow `/admin/ /dashboard/ /account/ /attachment/`.
- **Tech:** Next.js app rendered client-side. `/projects?city=…` HTML has no listings. The data comes from `https://www.justserve.org/api…` behind an OAuth client (`NEXT_PUBLIC_CLIENT_ID: JustServeClient`, and a client secret is embedded in `__NEXT_DATA__`). **We must not reuse embedded credentials.**
- **ToS:** `/legal/terms` is client-rendered too, so I couldn't read it without a browser. Not verified.
- **Recommendation: REJECT for automation.** Contact JustServe about a data partnership. A curated registry is fine for link-outs.

### 2.7 Points of Light Engage / AmeriCorps / volunteer.gov

- **Points of Light Engage** (`engage.pointsoflight.org`, the opportunity search linked from pointsoflight.org/volunteer): robots allows everything except `/weavers-admin/` and `/login/`, but **the ToS forbids it**: "Without our written permission, you may not: … (b) access the Service or Site using any high volume or automated means (including but not limited to robots, spiders, crawlers, and scripts)". Results load through Laravel Livewire (stateful), not an API. **REJECT** unless written permission is obtained.
- **AmeriCorps (americorps.gov):** even `robots.txt` sits behind an **Azure WAF JS challenge (403)**. **REJECT** (we won't solve challenges).
- **volunteer.gov:** bare `volunteer.gov` returns Cloudflare 522. `www.volunteer.gov/s/` is a Salesforce community, and its robots allows everything. Content is federal-lands volunteering (NPS/USFS), not urban, and pages are client-rendered. **REJECT / low priority.** It could later be a curated source for "volunteer in a national park near X".

### 2.8 Other city portals checked

| Org | City | Platform / finding | Recommendation |
|---|---|---|---|
| Chicago Cares (chicagocares.org/s/) | Chicago | Salesforce Experience Cloud with Volunteers for Salesforce. robots: `Allow: /`. Sitemap index `/s/sitemap.xml` lists `sitemap-gw_volunteers__volunteer_shift__c-N.xml` (shift URLs + lastmod). Shift pages are client-rendered. | Curated + sitemap watch (lastmod gives change detection). A headless fetch might be OK later. Ask for a feed. |
| New York Cares (newyorkcares.org) | NYC | Drupal 10. Project search `/search` is JS-loaded and I found no public JSON. robots disallows `/search/` (slash path). | Curated (org-level entry). NYC Service (HOC) and NYC Parks (Socrata) cover NYC instead. |
| Greater Twin Cities United Way (gtcuw.org) | Minneapolis | WordPress. The volunteer page links out to idealist.org and volunteermatch.org, so it has no own listings. robots: `Crawl-delay: 10`, allow all. | Curated (org entry); listings come via HandsOn Twin Cities. |
| United Way Miami (volunteermiami.org redirects to portal.unitedwaymiami.org/Volunteer/QuickSearch.jsp) | Miami | Andar Software portal. robots disallows a few admin JSPs. OpCalendar.jsp rendered an empty month to curl (JS/session). The page says "This site contains confidential information. Each account is intended only for the person to whom it is assigned…". | Curated + page-watch on QuickSearch category links. No adapter. |
| Mile High United Way (volunteer.unitedwaydenver.org) | Denver | **403 Forbidden to our UA, even for robots.txt.** | Curated only. We do not spoof UAs. |
| Volo Sports `/<city>/volunteer` | Denver etc. | Denver page: "Volunteering in Denver is coming soon". There is a JSON-LD `SportsActivityLocation` stub but no listings. | Watch (cheap page-watch on the Volo city volunteer page). |
| HandsOn Twin Cities (handsontwincities.org) | Minneapolis | Squarespace marketing site. robots blocks AI bots by name. For `*` it disallows `?format=json` and `/api/`. The real listings are on Galaxy (2.2). | Use Galaxy tenant. |

### 2.9 Summary table

| Source | Endpoint | Auth | robots | ToS | Fields | Cadence | Recommendation |
|---|---|---|---|---|---|---|---|
| HandsOn Connect (Boston Cares, Hands On Nashville, L.A. Works, NYC Service, UW Austin) | POST `/search/getOpportunitiesCalendar` | none | 404 (no rules) | no clause found | name, org, ISO start/end, tz, city/zip, spots still needed, type | daily, 1–3 day windows | **Adapter** |
| Galaxy Digital (HandsOn Twin Cities, UW King County) | `/need/rss/` + `/need/` + `/need/detail/` | none (API needs tenant Bearer key) | `*` allowed | no clause | title, link, pubDate, desc. Detail page adds date/time/spots | RSS 6 h, detail on change | **Adapter**; ask for API key |
| MPRB (Minneapolis) | `/wp-json/tribe/events/v1/events` | none | `/wp-json` allowed; `?ical=` disallowed | public agency | full event + venue geo + category | daily, ≥5 s spacing (429s) | **Adapter** |
| NYC Parks via NYC Open Data | Socrata `w3wp-dpdi` | none (app token optional) | n/a (site `/xml/` disallowed, use Socrata) | open data | title, start/end, location, coords, categories, registration_url | daily | **Adapter** |
| Idealist / VolunteerMatch | Open Network API | paid key | permissive | **bans scraping** | n/a | n/a | Reject scraping; **apply for API** |
| JustServe | private OAuth API | OAuth client | allows /projects | not readable without JS | n/a | n/a | Reject; contact |
| Points of Light Engage | Livewire UI | none | permissive | **bans automated access** | n/a | n/a | Reject unless written permission |
| AmeriCorps | n/a | n/a | WAF challenge | n/a | n/a | n/a | Reject |
| volunteer.gov | Salesforce community | none | allow all | not checked | federal-lands opps | n/a | Reject / low priority |
| Chicago Cares | Salesforce; shift sitemap | none | allow | not checked | sitemap URLs + lastmod only | daily sitemap | Curated + sitemap watch |
| New York Cares | Drupal JS search | n/a | `/search/` disallowed | not checked | n/a | n/a | Curated |
| United Way Miami (Andar) | JSP portal | session | partial | confidentiality notice | n/a | n/a | Curated + page-watch |
| Mile High United Way | n/a | n/a | 403 to UA | n/a | n/a | n/a | Curated only |
| Volo volunteer pages | HTML | none | allowed | personal non-commercial license | "coming soon" | weekly | Page-watch |

### Notes for the pipeline

- Use the HOC field `volunteersStillNeeded` as the "spots left" / "filling fast" signal. Galaxy calendar HTML shows "N spots remaining".
- Galaxy "Runs Until <date>" and the HOC `endDateTimeISO` of the last occurrence are the volunteer "register-by" signals. Most volunteer shifts have no separate signup deadline, so we must not invent one.
- MPRB event descriptions contain human schedule text ("Dates: Tuesdays and Thursdays 9-11am, May-September") and outbound signup links (SignUpGenius, Friends groups). Keep them as `signup_url`.

---

## 3. Niche sources (cons, faires, car shows, maker faires, trivia, run clubs, Meetup alternatives)

All checks done 2026-10-15 with UA `GetOffTheCouch-research/0.1 (contact: spanglew@amazon.com)`, 2 s between requests. Samples are in `docs/research/samples/`.

### 3.1 Summary table

| Source | Endpoint | Auth | robots.txt | ToS | Recommendation |
|---|---|---|---|---|---|
| UpcomingCons | `https://www.upcomingcons.com/{anime-cons,comic-conventions,furry-conventions,gaming-conventions,...}` (HTML with schema.org `Event` microdata: name, url, addressLocality/Region, startDate, endDate) | none | empty file, so everything is allowed | `/terms` has no scraping or automation clause | **Adapter** (weekly). Best keyless aggregator for fan cons. Sample: `upcomingcons-anime-cons.html` |
| Maker Faire | `https://makerfaire.com/query/?type=map` (JSON, 2,522 Locations: name, event_start_dt/end_dt, city/state/country, lat/lng, faire_url, category, free_event) | none | allows all except /wp-admin/, /invoice/ | make.co terms: no scraping clause found | **Adapter** (weekly). 28 upcoming faires worldwide. Seed-city faires in 2026 are already past. No Twin Cities faire. Sample: `makerfaire-query-map.json` |
| Geeks Who Drink | `GET /wp-admin/admin-ajax.php?action=mb_display_mapped_events&nonce=<gwdNonce from /venues/>&...` (HTML fragment: data-title, data-address, data-lat/lon, data-day, data-time, data-brand). One call returned all 1,064 venues | none (page nonce) | allows `admin-ajax.php` explicitly | T&C: no scraping clause | **Adapter** (weekly, 1 request). Needs the nonce from the page first. Not in MN. Venue counts: Denver 44, Austin 42, Seattle 24, Chicago 20, NYC 12, LA 7, Nashville 6, Boston 6, Miami 2. Sample: `geekswhodrink-venues.html` |
| Luma | per calendar: `https://api.lu.ma/ics/get?entity=calendar&id=cal-…` (ICS with GEO, LOCATION, URL). City discovery: `https://luma.com/<city>` `__NEXT_DATA__` (start_at, geo_address_info, calendar_api_id) | none | luma.com: rules only for Googlebot; api.lu.ma: only `/insights/` disallowed | /terms: no scraping clause | **Adapter** (ICS for curated calendars, 12 h, matching the feed's REFRESH-INTERVAL). Use the city page only to discover calendars. Sample: `luma-calendar-zoma-house.ics` |
| Car Show Radar | `https://carshowradar.com/wp-json/wp/v2/posts?categories=<stateId>` (title, link, date posted, excerpt; the event date is only in free text) | none | standard WP rules, so allowed | /terms: no scraping clause found | **Adapter, low priority**. Needs date extraction. Thin coverage (MN 23 posts total, TX 812, CA 333). Sample: `carshowradar-wp-posts-minnesota.json` |
| Wikidata SPARQL | `https://query.wikidata.org/sparql` | none (UA required) | `Disallow: /sparql` for crawlers. Programmatic API use with a descriptive UA is the sanctioned path (Wikimedia UA policy) | CC0 | **Entity registry only** (names, websites, coordinates). The US anime convention query (Q548126) returned 41 cons and **0 with a 2026+ edition**. A broader 2026+ edition query for fan/furry/comic/faire/maker/auto-show classes returned almost nothing fannish (WonderCon 2026, Open Sauce 2026). Not usable for dates. Samples: `wikidata-sparql-us-anime-cons.{rq,json}` |
| WikiFur | `https://en.wikifur.com/w/api.php` (MediaWiki API works for us) | none | robots.txt is behind a Cloudflare challenge (403), so unknown. Treat as conservative | CC-BY-SA 4.0 (siteinfo) | **Entity metadata only** (Infobox convention: location, url, organizer, first, status). Edition pages are written after the event (e.g. "Anthrocon 2026 ... was held"). "Furry Migration 2026" page missing. FurConCal is defunct (2010–2013). Sample: `wikifur-api-revisions.json` |
| furrycons.com | n/a | n/a | robots.txt itself is a 403 Cloudflare challenge (`cf-mitigated: challenge`), and `/calendar/feed/` is also a 403 | not readable | **Reject** for automation (getting in would mean bypassing a challenge). At most, a human looks at it while curating |
| animecons.com | n/a | n/a | robots.txt and RSS both 403 (Cloudflare) | not readable | **Reject** (same reason). UpcomingCons covers it |
| fancons.com | n/a | n/a | robots.txt and /rss/ both 403 (Cloudflare) | not readable | **Reject** |
| renfaire.com | `http://www.renfaire.com/sitemap-sites.xml` (331 faire pages) | none | `Disallow: /Faires/`. `/Sites/` is allowed | n/a | **Reject for dates**: listings are frozen ("2015 Dates", "Updated 2015-09-14"). Use it once as a discovery list of faire names and official URLs |
| renfaires.com / renaissancefestivals.com | parked (JS redirect to `/lander`) | | | | **Reject** (dead) |
| carshowfinder.org | WP posts | none | allows all | n/a | **Reject**: SEO blog with event-ish posts and no structured dates |
| Trivia Mafia (MN) | `/locations` HTML (venue list only). Day/time lives in Storepoint `api.storepoint.co/v1/164f9e9ab5e100/locations` (JSON: name, streetaddress, lat/long, per-weekday times, tags, description such as "October 20 at 7:00 PM") | none | triviamafia.com disallows `?format=json`, `?format=ical`, and many AI bots. **api.storepoint.co: `Disallow: /`** | n/a | **Curated registry + page-watch** of `/locations`. **Ask Trivia Mafia for permission** to use the Storepoint feed. Don't poll it on our own. No sample saved (robots-disallowed) |
| Sporcle Live | `/events/locations/` is populated via `/ajax/events/` | none | **`Disallow: /ajax/events/`** | n/a | **Reject automation**. Curate manually if needed |
| Strava clubs | `/api/v3/clubs/{id}/group_events` returned 401 without a token | OAuth (per-athlete) | `/api/` disallowed for crawlers | API Agreement: "Strava Data related to other users, even if such data is publicly viewable ... may not be displayed or disclosed"; also "may not ... compete with or replicate Strava functionality" | **Reject** |
| Running stores (Mill City Running, Fleet Feet) | Mill City: `/pages/group-runs` HTML (recurring schedule). Fleet Feet Chicago links its events to Eventbrite organizer `4712910043` | none (Eventbrite API needs an OAuth token: tested, 401 `NO_AUTH`) | Shopify default allows `/pages/`. fleetfeet.com disallows `/feeds/` | n/a | **Curated registry** for recurring runs (they rarely change). For one-off store events, use the Eventbrite adapter with our own private token |
| Meetup | `https://api.meetup.com/gql-ext` (GraphQL) | OAuth Bearer token per docs. Anonymous `{__typename}` works and `groupByUrlname` returned null without auth | `/files/` only | ToS page sits behind a Cloudflare challenge (not read) | **Defer**: get an OAuth client and confirm current API-access terms. I've heard it now requires Meetup Pro but **did not verify**. Prefer Luma ICS plus Eventbrite meanwhile |
| Facebook Events | n/a | Graph API no longer exposes public event search | n/a | prohibits automated collection | **Reject** |

### 3.2 Notes per source

**UpcomingCons**
- Every category page I fetched lists the same set of about 107 upcoming listings. Each listing is an `itemscope itemtype="http://schema.org/Event"` block with clean `startDate`/`endDate` meta tags, so parsing is trivial.
- Seed-city hits on the check date:
  - Minneapolis Anime and Gaming Event, Oct 30–Nov 1, 2026 and Sep 3–5, 2027
  - AniMinneapolis, May 7–9, 2027
  - L.A. Comic Con, Oct 30–Nov 1, 2026
  - Con+Alt+Delete (Rosemont), Dec 18–20, 2026
  - D20 Cruise (LA), Apr 9–15, 2027
  - PAX East, Apr 22–25, 2027
  - Anime Boston, May 28–30, 2027
  - Anime Expo, Jul 2–5, 2027
  - Anime Midwest (Rosemont), Jul 2–4, 2027
  - PAX West, Sep 3–6, 2027
- These are community-entered data. Cross-check against the official site and show `source=upcomingcons` with medium confidence.
- Per-con detail pages are sometimes stale (e.g. /13169-AniMinneapolis is the 2016 edition). Always use the list pages.

**Maker Faire**
- `/query/?type=map` is the JSON behind `/globalmap/` (from `mf-map.min.js`: `axios.get("/query/?type=map")`).
- Dates come as `MM/DD/YYYY hh:mm:ss am`, and `faire_year` is present.
- The feed includes school faires (category values like "School"/"Mini"). Filter to `Featured`/`Flagship`/`Mini` in the seed metros.
- About 1.9 MB per fetch. Weekly is plenty.

**Geeks Who Drink**
- `motherbrain.js` builds the request (`action: 'mb_display_mapped_events'`, `nonce: WP_URL.gwdNonce`).
- Start time comes from `data-time`, a UTC reference timestamp that the site renders with moment-timezone. If we convert it ourselves, use the venue's tz and treat the time as day-of-week + wall time. The reference date may sit in a different DST period, so expect up to a 1 h error unless we normalize.
- Brands in the feed: gwd (Classic), jbl, sbt (themed/bingo variants).

**Luma**
- City pages (`luma.com/minneapolis`) embed about 15 featured events with `calendar_api_id`. Each calendar has a public ICS (tested `cal-ZcUa89sLSrEvGwZ`, ZOMA House Minneapolis, 45 VEVENTs including GEO).
- This is the cleanest keyless "Meetup alternative" path: harvest calendar IDs from city pages, then subscribe to the ICS feeds.

**Trivia Mafia**
- The Storepoint feed is great data: 223 locations with per-weekday times and theme-night descriptions.
- But Storepoint's API host robots.txt is a blanket `Disallow: /`. I made one research request to identify the field shape and did **not** save it as a sample. An adapter should only be built with written permission.

### 3.3 Verified Minneapolis niche dates (quoted)

| Item | Quote | Where |
|---|---|---|
| Furry Migration | "September 10 -12, 2027 Downtown Minneapolis" | furrymigration.org |
| Anime Detour | "March 26th – 28th, 2027 Hyatt Regency Hotel 1300 Nicollet Mall" | animedetour.com |
| Twin Cities Con | "Twin Cities Con returns November 20th – 22nd, 2026! TICKETS ON SALE NOW! USE CODE EARLYBIRD10" | twincitiescon.com |
| MarsCon (MN) | "MarsCon 2027: Sci-Fi? What a Joke! March 5-7 2027" | marscon.org (not marscon.net, which is in Virginia) |
| MSRA Back to the 50's | "53rd Annual MSRA Back to the 50’s Weekend! ... June 18–20, 2027" | msrabacktothe50s.com |
| Mill City Running | "every Monday, Tuesday, and Friday (and some Saturdays) for a free community run" | millcityrunning.com/pages/group-runs |
| AniMinneapolis | "May 7-9, 2027" (aggregator only) | upcomingcons.com/anime-cons |
| Minneapolis Anime and Gaming Event | "Oct 30-Nov 1, 2026" (aggregator only) | upcomingcons.com/anime-cons |

Couldn't fetch: MN Renaissance Festival (403), CONvergence (Cloudflare), renfair.com faires (Bristol/NY/SoCal, 403), Florida Renaissance Festival (Cloudflare). Keep these in the curated registry with blank dates, for manual checks.

### 3.4 Not verified / gaps
- Lululemon and Nike store run-club calendars: not checked. Both are JS apps; expect to curate manually.
- Meetup API-access tier: not confirmed (docs only say OAuth).
- Twin Cities maker faire: none in the Maker Faire feed.
- Car shows in seed metros beyond MN: Car Show Radar has state categories (e.g. Texas 812, Illinois 176, Florida 182). Not sampled.

---

## 4. Samples index (this research area)

| File | Source | Format |
|---|---|---|
| `samples/volo-discover-denver-leagues.html` | Volo discover Denver, 5 cards | HTML fragment |
| `samples/leagueapps-chicagosocial-leagues.html` | LeagueApps legacy listing (CSSC), 5 programs. One research fetch; **not** for automated reuse (ToS) | HTML fragment |
| `samples/leaguelab-nashville-listing.html` | LeagueLab widget (NSL), header + 5 rows. One research fetch; automation needs permission | HTML fragment |
| `samples/mprb-tribe-events.json` | MPRB The Events Calendar REST, volunteer category, 3 events | JSON |
| `samples/handsonconnect-bostoncares-calendar.json` | HandsOn Connect calendar JSON, 5 occurrences | JSON |
| `samples/galaxydigital-handsontwincities-need-rss.xml` | Galaxy Digital need RSS | RSS |
| `samples/galaxydigital-handsontwincities-needs.html` | Galaxy Digital `/need/` table rows | HTML fragment |
| `samples/nyc-parks-socrata-w3wp-dpdi-volunteer.json` | NYC Open Data, NYC Parks events (volunteer) | JSON |
| `samples/upcomingcons-anime-cons.html` | UpcomingCons schema.org Event microdata | HTML fragment |
| `samples/makerfaire-query-map.json` | Maker Faire map JSON | JSON |
| `samples/geekswhodrink-venues.html` | Geeks Who Drink mapped venues fragment | HTML fragment |
| `samples/luma-calendar-zoma-house.ics` | Luma calendar ICS | ICS |
| `samples/carshowradar-wp-posts-minnesota.json` | Car Show Radar WP posts (MN) | JSON |
| `samples/wikidata-sparql-us-anime-cons.rq` / `.json` | Wikidata SPARQL query + result | SPARQL / JSON |
| `samples/wikifur-api-revisions.json` | WikiFur MediaWiki API | JSON |

Other files in `samples/` come from parallel research tracks (open data, tickets, libraries, universities).

## 5. Open questions / next pass
- Get permission or API keys from the outreach list above, then build `leaguelab` and `leagueapps` adapters behind feature flags.
- USBC (bowl.com) league finder: robots `Allow: /`, not deep-checked.
- Sports Monster (NYC/NJ), Chicago Park District adult sports, St. Paul Parks adult sports, Denver Parks & Rec: not checked this pass.
- Lululemon/Nike run clubs: JS apps, not checked.
- Meetup API tier/pricing: unconfirmed.
- Pages that 403 to our UA (MN Renaissance Festival, CONvergence, St. Paul Curling Club, Chaska, ASSC, Mile High United Way) need a one-time human visit to fill the curated entries.
