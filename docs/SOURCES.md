# Source catalogue

Every source the pipeline can fetch, with how we access it and why we trust it. **Verified** = the unit ran live
on 2026-10-16 (UTC) with `gotc run --city <slug> --no-geocode`; the count is valid records from that run. Research
notes and raw samples: `docs/research/city_open_data.md`, `docs/research/ticketing_and_events_apis.md`,
`docs/research/samples/`.

**Grades.** **A** official, documented, refreshed daily. **B** official but thin, quirky or slow to update.
**C** undocumented front-end API or scrape: works today, may change without notice. **D** dead or blocked.

**Shared notes.**
- All sources are keyless. Socrata accepts an optional free `SOCRATA_APP_TOKEN` (`X-App-Token`) that raises the
  throttling ceiling; we saw intermittent keyless 503s on NYC/Chicago/Austin during research, and PoliteClient
  retries 5xx with backoff.
- PoliteClient honors robots.txt (and `Crawl-delay`) for every adapter except documented data APIs, which opt out
  in code: **Socrata** (SODA API) and **ArcGIS** (`services*.arcgis.com/robots.txt` answers HTTP 403 "Invalid URL",
  i.e. no policy is published; PoliteClient would read that as "disallow all"). CKAN, BiblioCommons, Trumba,
  Localist, LiveWhale, Tribe, Simpleview and Communico all go through the robots check.
- **Openings** (`data_type: openings`, `kind: opening`) come from license data. Every record is all-day on the
  license's newness date (application, original issue, or registered start; never a renewal date), its
  description starts with "License signal, not a confirmed opening date", and personal-data columns (owner,
  applicant, manager, contact, phone, e-mail, mailing address) are dropped before mapping
  (`gotc/adapters/mapped.py: PII_KEY`). Legal names that don't look like an organisation are never used as titles.

## City sources

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `mprb_events` | minneapolis | WP The Events Calendar / `tribe` | https://www.minneapolisparks.org/wp-json/tribe/events/v1/events | none | none published; ≤ 2 pages/day | REST allowed; robots asks bots to avoid HTML calendar permutations | title, description (HTML→offers), start/end+tz, venue+geo, categories, cost | events · 24h | A- (official park board feed, staff-edited) | 53 |
| `mpls_downtown_events` | minneapolis | WP The Events Calendar / `tribe` | https://www.mplsdowntown.com/wp-json/tribe/events/v1/events | none | none published; 3 pages/day | REST allowed (robots blocks only HTML Tribe permutations) | as MPRB | events · 24h | B+ (business-district calendar, lots of nightlife/trivia) | 110 |
| `hclib_events` | minneapolis | BiblioCommons RSS / `bibliocommons` | https://gateway.bibliocommons.com/v2/libraries/hclib/rss/events | none | ~17 pages/day; gateway host has no robots.txt (`hclib.bibliocommons.com` sets Crawl-delay 120 — we never hit that host) | published RSS feed linked from the library's events page | title, description, bc:start/end local, branch address+geo, categories, cancelled, registration required/full/capacity/registered | events · 24h | A- (official, rich; countywide so filtered to Minneapolis + inner suburbs) | 254 |
| `umn_events` | minneapolis | LiveWhale JSON / `livewhale` | https://events.tc.umn.edu/live/json/events/max/200 | none | 1 request/day | robots: only `?replytocom` disallowed | title, date_iso, location+geo, event types, tags, cost | events · 24h | A- (official) | 97 |
| `nyc_permitted_events` | nyc | Socrata `tvpp-9vvx` / `socrata` | https://data.cityofnewyork.us/d/tvpp-9vvx | none (optional app token) | Socrata throttling | NYC Open Data ToU (attribution, no warranty) | event name, start/end (local, no tz), location, borough, type, agency | events · 24h | A (official, daily) — filtered to block parties, street events, plazas, open streets, parades, farmers markets, races | 549 |
| `nyc_parks_events` | nyc | Socrata `w3wp-dpdi` / `socrata` | https://data.cityofnewyork.us/d/w3wp-dpdi | none | Socrata throttling; explicit `$select` avoids 503s | Open Data mirror of nycgovparks.org (whose `/xml/` feed is robots-disallowed) | title, description (HTML), park, start/end, categories, "lat, lon" | events · 24h | A- (rolling 14-day window) | 781 |
| `nys_sla_pending_openings` | nyc | Socrata `f8i8-k2gm` (data.ny.gov) / `socrata` | https://data.ny.gov/d/f8i8-k2gm | none | Socrata throttling | NY Open Data ToU | application id, DBA (or org legal name), class, address, received date, status, point | openings · 24h | A (best "coming soon" signal found) | 222 |
| `nys_sla_new_licenses` | nyc | Socrata `9s3h-dpkz` (data.ny.gov) / `socrata` | https://data.ny.gov/d/9s3h-dpkz | none | Socrata throttling | NY Open Data ToU | license id, DBA, class, address, **originalissuedate**, point | openings · 24h | A (original issue date = real newness) | 994 |
| `nyu_events` | nyc | LiveWhale v2 JSON / `livewhale` | https://events.nyu.edu/live/json/events/type/Open%20to%20the%20Public/max/200/… | none | 1 request/day | allowed | title, date_iso, location, types, group | events · 24h | B- (filtered to "Open to the Public"; mostly lectures) | 92 |
| `chicago_park_events` | chicago | Socrata `tn7v-6rnw` / `socrata` | https://data.cityofchicago.org/d/tn7v-6rnw | none | Socrata throttling | Chicago data portal ToU | title, description, start/end, facility, address, lat/lon, category, info link | events · 24h | A (official, daily) | 318 |
| `chicago_park_permits` | chicago | Socrata `pk66-w54g` / `socrata` | https://data.cityofchicago.org/d/pk66-w54g | none | Socrata throttling; `starts_with()` works where `LIKE` 503s | Chicago data portal ToU; `requestor_` (a person) is dropped | event description, dates, park facility, size-tier type, organization | events · 24h | B+ (titles are terse; tier is an attendance input) | 127 |
| `chicago_liquor_openings` | chicago | Socrata `r5kz-chrr` / `socrata` | https://data.cityofchicago.org/d/r5kz-chrr | none | Socrata throttling | Chicago data portal ToU | DBA/org legal name, license description+activity, address, neighborhood, lat/lon, license_start_date (`application_type='ISSUE'` only) | openings · 24h | A | 38 |
| `chicago_restaurant_openings` | chicago | Socrata `r5kz-chrr` / `socrata` | https://data.cityofchicago.org/d/r5kz-chrr | none | Socrata throttling | as above | as above; Retail Food with on-site preparation only | openings · 24h | A | 110 |
| `chipublib_events` | chicago | BiblioCommons RSS / `bibliocommons` | https://gateway.bibliocommons.com/v2/libraries/chipublib/rss/events | none | 40 pages/day (horizon 14 days) | published RSS feed | as HCLib | events · 24h | A- | 969 |
| `uchicago_events` | chicago | LiveWhale v2 JSON / `livewhale` | https://events.uchicago.edu/live/json/events/max/200/… | none | 1 request/day | allowed | as UMN | events · 24h | B | 92 |
| `usc_events` | los_angeles | Localist / `localist` | https://calendar.usc.edu/api/2/events | none | ≤ 5 pages/day | allowed | title, instances, venue+geo, filters, free/ticket url | events · 24h | B | 442 |
| `la_business_openings` | los_angeles | Socrata `6rrh-rzua` / `socrata` | https://data.lacity.org/d/6rrh-rzua | none | Socrata throttling | LA Open Data ToU | DBA/org legal name, NAICS 7224/7225, address, location_start_date (future = pre-registered), point (0,0 dropped) | openings · 24h | B+ (registration, not a license; many future dates) | 105 |
| `ladbs_special_events` | los_angeles | Socrata `8spw-3fhx` / `socrata` | https://data.lacity.org/d/8spw-3fhx | none | Socrata throttling | LA Open Data ToU | event name, dates (all-day), location, point; far-future typos rejected | events · 24h | B- (≈ a dozen future structure permits) | 10 |
| `mdpls_events` | miami | Communico `eeventcaldata` / `communico` | https://www.mdpls.org/eeventcaldata | none | 7 requests/day (one per day of horizon, ~0.5 MB each) | **undocumented** front-end JSON; robots disallows only search/results/contact | title, sub_title, description, local start/end, branch, room, tags, ages, registration (url, capacity, registrants), cost; staff contact never mapped | events · 24h | B (official library data via an undocumented endpoint; "All day" displays skipped) | 490 |
| `fiu_events` | miami | Localist / `localist` | https://calendar.fiu.edu/api/2/events | none | ≤ 5 pages/day | allowed | as USC | events · 24h | B- (mostly academic) | 280 |
| `austin_convention_center_events` | austin | Socrata `p9ma-z6y9` / `socrata` | https://datahub.austintexas.gov/d/p9ma-z6y9 | none | Socrata throttling | Austin Open Data ToU | event name, arrive/depart (all-day), venue, website, expected attendance; industry meetings filtered out | conventions · 168h | A- | 65 |
| `utaustin_events` | austin | Localist / `localist` | https://calendar.utexas.edu/api/2/events | none | ≤ 6 pages/day; robots `Crawl-Delay: 1` | allowed (disallows only HTML `?types`) | as USC | events · 24h | B+ | 600 |
| `tabc_pending_openings_austin` | austin | Socrata `mxm5-tdpj` (data.texas.gov) / `socrata` | https://data.texas.gov/d/mxm5-tdpj | none | Socrata throttling | Texas Open Data ToU; `owner` dropped | trade name, license type (MB/BG/BE), gun_sign (RED = bar), address, submission date, status | openings · 24h | A | 18 |
| `tabc_new_licenses_austin` | austin | Socrata `7hf9-qc9f` (data.texas.gov) / `socrata` | https://data.texas.gov/d/7hf9-qc9f | none | Socrata throttling | as above; `owner`/`mail_*` dropped | trade name, type, gun_sign, address, **original_issue_date** | openings · 24h | A | 33 |
| `denver_liquor_openings` | denver | ArcGIS FeatureServer layer 27 / `arcgis` | https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_BUSN_LIQUORLICENSES_P/FeatureServer/27 | none | server maxRecordCount; 1 request/day | documented ArcGIS REST API; no robots policy published (robots.txt → 403) | business name, license type, address, neighborhood, point (placeholder desert geometry dropped), **ORIGINAL_ISSUE_DATE** | openings · 24h | A- | 10 |
| `denver_pending_food_openings` | denver | ArcGIS FeatureServer table 46 / `arcgis` | https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_pending_business_licenses/FeatureServer/46 | none | 1 request/day | as above; `Entity_Name` never used; rows with no trade name filtered server-side | trade name, address, APPLICATION_DATE (UTC-midnight date), status; no geometry (geocoded later) | openings · 24h | A- (pending = earliest signal) | 71 |
| `colorado_liquor_openings_denver` | denver | Socrata `htyp-tqzh` (data.colorado.gov) / `socrata` | https://data.colorado.gov/d/htyp-tqzh | none | Socrata throttling | Colorado Open Data ToU | licensee name (holds the trade name here), license type, issue date, number, address | openings · 24h | B (rows with issue_date/license_number swapped are rejected by `validate` + `reject_future_start`) | 22 (1 rejected) |
| `spl_events` | seattle | Trumba JSON / `trumba` | https://www.trumba.com/calendars/kalendaro.json | none | 1 request/day (always with `startdate`+`days`) | trumba.com robots allows all; feed published for embedding | title, description, wall-clock start/end + explicit offset, location, room, custom fields, cancel/sign-up flags, repeats | events · 24h | A- | 189 |
| `uw_events` | seattle | Trumba JSON / `trumba` | https://www.trumba.com/calendars/sea_campus.json | none | 1 request/day | as above | as SPL + "Event Types", Google-Maps lat/lon in the location link | events · 24h | B+ | 115 |
| `seattle_business_openings` | seattle | Socrata `wnbq-64tb` (cos-data.seattle.gov) / `socrata` | https://cos-data.seattle.gov/d/wnbq-64tb | none | Socrata throttling | Seattle Open Data ToU; `business_phone` dropped | trade name/org legal name, NAICS, address, license_start_date (YYYYMMDD; future = pre-registered) | openings · 24h | A- (no coordinates; geocoded) | 33 |
| `downtown_seattle_events` | seattle | WP The Events Calendar / `tribe` | https://downtownseattle.org/wp-json/tribe/events/v1/events | none | 1 request/day | allowed | as MPRB | events · 24h | C (official but only ~7 upcoming) | 7 |
| `vanderbilt_events` | nashville | LiveWhale JSON / `livewhale` | https://events.vanderbilt.edu/live/json/events/max/200 | none | 1 request/day | allowed | as UMN | events · 24h | B | 178 |
| `nashville_beer_permit_openings` | nashville | ArcGIS FeatureServer / `arcgis` | https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Beer_Permit_Locations_Feature_Layer_view/FeatureServer/0 | none | 1 request/day | documented ArcGIS REST API; no robots policy (403); `Business_Owner` dropped | business name, permit subtype (on-site sales only), address, point, Date_Entered | openings · 24h | A- | 14 |
| `downtown_boston_events` | boston | WP The Events Calendar / `tribe` | https://www.downtownboston.org/wp-json/tribe/events/v1/events | none | ≤ 10 pages/day | no robots.txt served | as MPRB | events · 24h | B+ | 187 |
| `bpl_events` | boston | BiblioCommons RSS / `bibliocommons` | https://gateway.bibliocommons.com/v2/libraries/bpl/rss/events | none | ~19 pages/day (horizon 10 days) | published RSS feed | as HCLib | events · 24h | A- | 440 |
| `northeastern_events` | boston | Localist / `localist` | https://calendar.northeastern.edu/api/2/events | none | ≤ 5 pages/day | allowed | as USC | events · 24h | B | 124 |
| `meet_boston_events` | boston | Simpleview CVB / `simpleview` | https://www.meetboston.com/includes/rest_v2/plugins_events_events_by_date/find/ | short-lived token from `/plugins/core/get_simple_token/` | robots Crawl-delay 2 | **undocumented**; robots allows; **HTTP 403 "Access Denied" (CDN bot protection) to our client on 2026-10-16** | title, occurrence date, start/end time, location+geo, admission text, categories, link | events · 24h | D for us (disabled) — C+ data quality when it was reachable | disabled |
| `visit_austin_events` | austin | Simpleview CVB / `simpleview` | https://www.austintexas.org/includes/rest_v2/plugins_events_events_by_date/find/ | token | Crawl-delay 2 | as Meet Boston: 403 to our client | as Meet Boston | events · 24h | D for us (disabled) | disabled |
| `visit_denver_events` | denver | Simpleview CVB / `simpleview` | https://visitdenver.com/includes/rest_v2/plugins_events_events_by_date/find/ | token | Crawl-delay 2 | as Meet Boston: 403 to our client | as Meet Boston | events · 24h | D for us (disabled) | disabled |
| `boston_special_events` | boston | CKAN datastore / `ckan` | https://data.boston.gov/api/3/action/datastore_search_sql (resource fb05bfda-…) | none | — | **robots.txt `Disallow: /api/` and `/datastore/*` for all agents** | app name, start/end date, location, address | events · 24h | D for us (disabled; data itself is A-) | disabled |
| `boston_food_openings` | boston | CKAN datastore / `ckan` | https://data.boston.gov/api/3/action/datastore_search_sql (resource f1e13724-…) | none | — | robots disallows `/api/` (as above); `dayphn_cleaned` would be dropped | business/DBA name, address, lat/lon, license_add_dt_tm | openings · 24h | D for us (disabled) | disabled |

## Global sources (key-gated)

| id | platform / adapter | auth | rate limits | ToS highlights | fields | data_type · cadence | grade | status |
|---|---|---|---|---|---|---|---|---|
| `ticketmaster` | Ticketmaster Discovery API v2 / `ticketmaster` | `TICKETMASTER_API_KEY` (self-serve, free) | 5,000 calls/day; docs say 5 req/s, FAQ says 2 req/s (design for 2); deep paging capped at 1,000 items; headers `Rate-Limit-*` | developer.ticketmaster.com terms: no sublicensing or deriving revenue except via the affiliate program; branding rules | events, venues, `priceRanges` (when present), `dates.status`, public/presale windows, affiliate URL | ticket_prices · 6h | A | disabled until the key is set (STATUS.md "Keys needed") |
| `seatgeek` | SeatGeek Platform API / `seatgeek` | `SEATGEEK_CLIENT_ID` (portal is login-gated; approval may be slow) | ~100 requests/minute per client | attribution + link back required; no redistribution of raw data; partner revenue via Impact | events, venue, `stats.lowest_price/average_price/listing_count/...` (snapshotted for price trend) | ticket_prices · 4h | A | disabled until the key is set |

Rejected ticketing/discovery platforms (Bandsintown, Songkick, Resident Advisor, DICE, AXS, DoStuff, Yelp, …) and
their reasons are in `docs/research/ticketing_and_events_apis.md` §0.

## Rejected, blocked and dead sources

| Source | City | Why it isn't used | Evidence |
|---|---|---|---|
| Simpleview CVB APIs (Meet Boston, Visit Austin, Visit Denver) | BOS/AUS/DEN | 403 "Access Denied" from the CDN to our client on the first live run, though robots allows. We don't evade bot protection. Configs kept, `enabled: false`. | `gotc run` 2026-10-16, HEALTH.md |
| data.boston.gov CKAN API (special events, one-day alcohol, entertainment, food licenses) | Boston | robots.txt `Disallow: /api/`, `/datastore/*` | https://data.boston.gov/robots.txt |
| Visit Music City (incl. Simpleview token), Nashville Public Library, Metro Parks events | Nashville | Cloudflare 403 challenge | research 2026-10-15 |
| Denver Public Library (LibCal) | Denver | robots `User-agent: * / Disallow: /` | denverlibrary.libcal.com/robots.txt |
| nycgovparks.org `/xml/events_300_rss.json` | NYC | robots disallows `/xml/` | use `nyc_parks_events` (Open Data mirror) |
| NYC Parks Events Listing `fudw-fgrp` and child tables | NYC | dead (last row 2019-12) | research |
| NYPL, Seattle PL, Austin PL on BiblioCommons Events | NYC/SEA/AUS | "Events feature is not available" (403) | research |
| BiblioCommons JSON gateway `/v2/libraries/{lib}/events` | all | undocumented, ignores date filters | use the RSS feed |
| Chicago "Special Events" `xgse-8eg7` | Chicago | 500/503, last updated 2026-01 | research |
| Seattle Special Events Permits `dm95-f8w5` | Seattle | dead (last event 2025-10) | research |
| LA City Events `9aw9-mn4p` | LA | 0 future rows | research |
| laparks.org, Columbia Localist, Explore Minnesota | LA/NYC/MN | 403 / Cloudflare | research |
| Miami-Dade "Tbl Calendar Wiz Event" | Miami | dead (last edit 2021) | research |
| Austin ACE permits `teth-r7k8` | Austin | past permits only (every 2026 row "Expired"); enrichment only | research |
| Minneapolis On-Sale Liquor (ArcGIS) | Minneapolis | `issueDate` includes renewals and there is no original-issue date, so it can't signal newness by itself (snapshot-diff idea in the ledger) | research §3.1 |
| WA LCB Local Authority Letters `vgcw-qfjm` | Seattle | only ~18 rows statewide, 0 for Seattle | research |
| Florida DBPR ABT CSV extracts | Miami | usable (robots allows `/sto/`) but needs a CSV adapter — idea in the ledger | research §3.9 |
| Walker Art Center, artsmia.org | Minneapolis | feeds disabled / 429 | research |

## How to add a source

1. **Find the platform.** Most city data is on a platform we already support: `socrata`, `arcgis`, `ckan`
   (tabular open data, config-driven field mapping in `gotc/adapters/mapped.py`), `tribe`, `localist`,
   `livewhale`, `trumba`, `bibliocommons`, `communico`, `simpleview`, `ics`. A new source is then YAML only.
2. **Check robots.txt and the ToS** for the exact host and path you'll call. If robots disallows it, or the site
   answers 403/Cloudflare/"Access Denied", stop: add it to the rejected table above instead.
3. **Add the entry** to `config/cities/<slug>.yaml`: unique `id` (`^[a-z0-9_]+$`), `adapter`, `name`, `data_type`,
   `homepage`, `expect_min_records`, `params`. Use only category ids from `config/taxonomy.yaml`. Push filtering
   into the server query (`where`) and use `include`/`exclude`/`include_regex`/`exclude_regex`/`exclude_title`
   for the rest. For openings: `kind: opening`, `lookback_days`, a newness date (never a renewal date), a
   `title_template` like `"{title} — new liquor license"`, a `description_template` starting with "License
   signal, not a confirmed opening date", and `entity_only_fields` for legal-name columns.
4. **Run it live once:** `gotc run --city <slug> --source <id> --force --no-geocode`, then read `docs/HEALTH.md`
   and the rejects table. Look at a few stored records for title, local time, category and address.
5. **Record a fixture:** `gotc record <id> --trim 8` (or copy the research sample into `tests/fixtures/<id>/`
   with a `meta.json` noting provenance) and add assertions to `tests/adapters/test_<adapter>.py`.
6. **Add a row to this file** with the stance, rate limits, fields and grade.

## Leagues, volunteering, cons, Luma (added 2026-10-16)

Added by the leagues/volunteer/niche adapter pass (2026-10-16). Every robots.txt below was fetched live on
2026-10-16 through `PoliteClient` (UA `GetOffTheCouch/0.1`); ToS stances are from `docs/research/leagues_volunteer_niche.md`
(2026-10-15) unless noted. "Live" = valid records on the first live run (`gotc run --city X --source Y --force --no-geocode`),
0 rejects unless noted. Units whose city file wasn't in this branch were run against a temporary copy of the other
agent's city header; their entries live in `config/pending_sources/<city>.yaml`.

| Source id | City | Adapter | Endpoint | Auth | robots.txt | ToS | Cadence | Live (2026-10-16) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `volo_boston` | boston (pending) | volo | `GET volosports.com/discover/boston?category=leagues&includeFees=true[&page=N]` | none | `Allow: /`; only /rfo /admin /staff disallowed | personal-use licence, no scraping clause | 24 h, ≥3 s/req | 91 (4 pages) | prices incl. fees; year-less dates inferred (see adapter) |
| `volo_denver` | denver (pending) | volo | `…/discover/denver?category=leagues[&page=N]` | none | same | same | 24 h | 98 (5 pages) | |
| `volo_los_angeles` | los_angeles (pending) | volo | `…/discover/los-angeles?category=leagues&includeFees=true` | none | same | same | 24 h | 47 (2 pages) | |
| `volo_miami` | miami (pending) | volo | `…/discover/miami?category=leagues` | none | same | same | 24 h | 17 (1 page) | Miami uses a different title layout ("Sport (fmt) - Day - Venue (Hood) - Month YYYY") |
| `volo_nyc` | nyc (pending) | volo | `…/discover/new-york-metro-area?category=leagues` | none | same | same | 24 h | 123 (6 pages) | includes Jersey City/Hoboken (NYC aliases) |
| `boston_cares` | boston (pending) | handsonconnect | `POST bostoncares.org/search/getOpportunitiesCalendar` (block 589) | none | 404 (no rules) | none found | 24 h, 2-day windows × 14 days | 541 | undocumented endpoint used by the site's own calendar |
| `hands_on_nashville` | nashville (pending) | handsonconnect | `POST handson.unitedwaygreaternashville.org/…` (block 2009) | none | 404 | none found | 24 h | 405 | `events` = campaign banners, skipped |
| `la_works` | los_angeles (pending) | handsonconnect | `POST volunteer.laworks.com/…` (no block id) | none | 404 | none found | 24 h | 244 | |
| `nyc_service` | nyc (pending) | handsonconnect | `POST nycservice.org/…` (block 2073) | none | 404 | none found | 24 h | 168 | |
| `uw_austin_volunteer` | austin (pending) | handsonconnect | `POST volunteer.uwatx.org/…` (block 447) | none | 404 | none found | 24 h | **0** (calendar empty) | `expect_min_records: 0`; empty for 14 days with and without block id |
| `handson_twin_cities` | minneapolis | galaxydigital | `GET handsontwincities.galaxydigital.com/need/rss/` + `/need/detail/?need_id=N` | none (API = tenant Bearer key) | `*`: empty Disallow (SEO bots blocked by name) | no scraping clause | 24 h, ≥3 s/req, ≤15 detail pages | 35 (15 needs) | RSS = discovery only; ask for an API key |
| `uwkc_volunteer` | seattle (pending) | galaxydigital | `GET volunteer.uwkc.org/need/rss/` + detail pages | none | same as above | same | 24 h | 15 | |
| `upcomingcons` | all cities (global) | upcomingcons | `GET upcomingcons.com/{anime-cons,comic-conventions,gaming-conventions,science-fiction-conventions}` | none | empty file (all allowed) | /terms: no scraping clause | 168 h, ≥3 s/req | MPLS 3 · CHI 2 · LA 2 · BOS 1 · SEA 1 · others 0 | city filter = locality ∈ name/aliases (+`extra_localities`) and same state; category pages return inconsistent lists |
| `makerfaire` | all cities (global) | makerfaire | `GET makerfaire.com/query/?type=map` | none | allows all but /wp-admin/, /invoice/ | make.co terms: no scraping clause | 168 h | **disabled** | Cloudflare 403 "Just a moment…" to our client on 2026-10-16; not worked around. Parser tested on the research sample |
| `luma_zoma_house` | minneapolis | ics | `GET api.lu.ma/ics/get?entity=calendar&id=cal-ZcUa89sLSrEvGwZ` | none | api.lu.ma: only /insights/ disallowed | no scraping clause | 12 h (feed says PT12H) | 6 | calendars found via luma.com/<city> `__NEXT_DATA__`; org calendars only, never "Personal" |
| `luma_mpls_journaling_club` | minneapolis | ics | `…id=cal-vIvBKQ0GdZ1C2hH` | none | same | same | 12 h | 2 | |
| `luma_minnestar` | minneapolis | ics | `…id=cal-tXboXaBmfSTKWBC` | none | same | same | 12 h | 1 | |
| `luma_sew_it_together` | minneapolis | ics | `…id=cal-mu5aaSRoSxi1ZRK` | none | same | same | 12 h | 22 (30-day horizon) | sewing classes |
| `luma_startup_boston` | boston (pending) | ics | `…id=cal-BI22W7AXNavDI82` | none | same | same | 12 h | 6 | most addresses hidden until RSVP |
| `luma_mhub_chicago` | chicago (pending) | ics | `…id=cal-2MaopjwQTRbceSD` | none | same | same | 12 h | 1 | |
| `luma_venice_book_club` | los_angeles (pending) | ics | `…id=cal-E8al8GRIz3vkQrj` | none | same | same | 12 h | 6 | |
| `luma_mana_tech` | miami (pending) | ics | `…id=cal-NgTwepzMKeP3Xlg` | none | same | same | 12 h | 10 | |
| `luma_run_gables` | miami (pending) | ics | `…id=cal-GC5KnPoGH2C76rp` | none | same | same | 12 h | 6 | run club |
| `luma_lit_club_nyc` | nyc (pending) | ics | `…id=cal-ItTR6nQ7r4wIvFf` | none | same | same | 12 h | 7 | |
| `luma_ny_philosophy_club` | nyc (pending) | ics | `…id=cal-dGP82mVkrg1FRmr` | none | same | same | 12 h | 13 | |
| `luma_corgi_nyc` | nyc (pending) | ics | `…id=cal-H1FY60pnZtchaf4` | none | same | same | 12 h | 9 | run club |
| `luma_atx_backgammon` | austin (pending) | ics | `…id=cal-rwQQdIctP4pVyr7` | none | same | same | 12 h | 1 | |

**Not added:** Volo has no Minneapolis, Chicago, Seattle, Austin or Nashville market (sitemap, 2026-10-16). Luma calendars
that span several cities (ALO, Claude Community, Longevity Cities) were skipped because the ICS has no per-city filter;
calendars whose events mostly hide the address (ATX Writing Club, City Folk Seattle) were skipped too.
