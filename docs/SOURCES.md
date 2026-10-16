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
| Florida DBPR ABT CSV extracts | Miami | now used: `fl_dbpr_openings_miami` (csvfile, `bd4006lic.csv`). See "Races, openings, trivia (session 2)" | research §3.9 |
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

## Races, openings, trivia (session 2)

Added 2026-10-16. Every robots.txt and terms page below was fetched live that day with the project UA. "Live" means
valid records on the first `gotc run --city X --source Y --force --no-geocode`, with 0 rejects unless noted.

| Source id | City | Adapter | Endpoint | Auth | robots.txt | ToS | Cadence | Live (2026-10-16) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| `runsignup` | all cities (global) | runsignup | `GET runsignup.com/Rest/races?format=json&events=T&zipcode=Z&radius=R&start_date&end_date&sort=date ASC` | **free API caller registration** (`RUNSIGNUP_API_REG` + `RUNSIGNUP_API_REG_SECRET`) | `runsignup.com`: `/Rest/` allowed. `api.runsignup.com/robots.txt` is `Disallow: /`, so that host is never called | API Terms of Use (runsignup.com/About-Us/APIDeveloper-Contract): "You must register and agree to these Terms before accessing the RunSignup API"; max 2 concurrent calls; no competing apps; no bulk extraction beyond the app's ordinary function | 24 h, ≥2 s/req | **disabled: needs caller registration** (STATUS "Keys needed"). Recorded Chicago response: 45 races, 0 rejects, **42 with a reported close date**, 15 early-bird price steps | Registration times are Eastern Time (per the docs), race start times use the race's zone. Price = cheapest paid entry among periods still open. Private, draft, virtual-only and already-started (add-on store) races are skipped. `postponed_cancelled_text` marks cancellations |
| `fl_dbpr_openings_miami` | miami | csvfile | `GET www2.myfloridalicense.com/sto/file_download/extracts/bd4006lic.csv` (14 MB, header row, UTF-8 today; cp1252 fallback) | none | allows `/sto/` (blocks only WordPress internals) | official Public Records download page | 24 h, conditional GET (`Last-Modified`) | **66** | Newness = `Original Licensure Date` (never Effective Date). County 23 (Dade), on-premises series (`*COP`); package stores, caterers and inactive quota licenses held in escrow ("NO CITY CODE") are filtered out. `Owner Name` and `Mail Address *` are dropped by the PII scrub (headers are snake_cased first so `PII_KEY` sees them). A DBA that just repeats the owner's legal name is used only if it looks like an organisation |
| `boston_food_openings_csv` | boston | csvfile (`link_regex`) | `GET data.boston.gov/dataset/active-food-establishment-licenses`, then the page's `/dataset/…/resource/f1e13724-…/download/<tmp>.csv` link (302 to S3) | none | `/dataset/<slug>` pages and resource downloads are not disallowed. `/api/` and `/datastore/*` are, and we never call them. Crawl-delay 10 honoured | Analyze Boston open data | 24 h, ≥10 s/req | **21** | Newness = `license_add_dt_tm` (UTC timestamp → local date). `dayphn_cleaned` is dropped. The download file name changes when the city re-publishes, so the link is re-read from the dataset page every run. The stored URL is the data.boston.gov link, not the pre-signed S3 URL |
| `teamtrivia_denver` | denver | teamtrivia | `GET teamtrivia.com/trivia-in-denver/` → `GET teamtrivia.com/venue/<slug>` (29 venues) | none | region and venue pages allowed, and listed in the site's own sitemaps. The zip-code gate (`/enter-site.php`) and finder (`/getlocation.php`) are disallowed and never used | `/terms` sits behind the zip gate (every gated URL returns the gate to a cookieless client), so it couldn't be read. Nothing on the public pages restricts reuse | 48 h, ≥3 s/req | **120** (29 venues). Replay after the guard below: 119 + 1 reject | Dates come from schema.org `Event` JSON-LD on each venue page (the next 4 games, correct DST offsets). If a page had a schedule table but no JSON-LD, the weekly rows would be expanded to 4 dates (labeled derived). Guard: a JSON-LD date whose weekday isn't on the posted schedule is rejected. Seen live: a Thursday game stamped with Friday's date |
| `challenge_trivia_nashville` | nashville | challenge | `GET challengeentertainment.com/wp-json/ce/v1/shows` (one ~0.9 MB array, 937 shows nationwide) | none | Yoast `User-agent: * / Disallow:` (everything allowed) | no terms page exists (page sitemap: privacy policy only; no automation clause) | 48 h | **172** (35 venues) | Undocumented show-finder JSON (grade C). `day` 1 = Sunday. Weekly shows get 4 dates and bi-weekly 4 fortnights (next_date reported, the rest derived and labeled). Monthly / n×-per-month shows get next_date only. If `day` disagrees with `next_date`, next_date is trusted and not expanded. City filter = `metro-<slug>` and ≤ 2× city radius. Xtreme/Ballistic bar bingo → `trivia_games.bingo` |
| `challenge_trivia_austin` | austin | challenge | same | none | same | same | 48 h | **56** (14 venues) | Killeen/Bastrop-range shows beyond 50 km are filtered |
| `challenge_trivia_denver` | denver | challenge | same | none | same | same | 48 h | **41** (9 venues) | mostly suburbs (Thornton, Commerce City, Aurora) |

**Rejected or not added (this session)**

| Source | Why | Evidence |
|---|---|---|
| Race Roster (raceroster.com) | Registrant ToS: "post any Site Content on any other web site … strictly prohibited without the express prior written permission of Race Roster". robots allows event pages; ToS does not | raceroster.com/legal/tos-for-event-registrants |
| CARA race calendar (cararuns.org) | Wix site; no feed or REST API to read | `/wp-json/` → 404 |
| Boston liquor licenses (CSV download) | robots allows the file, but `issued` is re-stamped in bulk (1,057 of 1,535 rows dated 2013-11; existing breweries re-issued 2026-09), so it isn't a newness date. Idea I-094 (first-seen diff) | download of `aab353c1-…` 2026-10-16 |
| FL DBPR `daily.csv` (as the Miami openings source) | Only one day of transactions per file and no original-licensure column. `bd4006lic.csv`'s `Original Licensure Date` is the real newness date and backfills 60 days. `csvfile` still supports headerless files (`columns:`), tested on the research sample | research §3.9 |
| Team Trivia: Chicagoland, Miami, Nashville | region pages list **0 venues** today | trivia-in-{chicagoland,miami,nashville} |
| Challenge Entertainment: south-florida, chicagoland, southern-california | no shows inside our cities (Broward, Chicago suburbs/Peoria, Long Beach only) | wp-json/ce/v1/shows 2026-10-16 |
| TriviaPalooza (triviapalooza.com) | Orlando private-events company; no public venue schedule | Wix home page |
| Quizmasters (quizmasters.biz) | UK quiz-content seller, not a venue host | home page |
| Pub Geeks (pubgeeks.com) | only NH/VT venues | static location list |
| OpenAir Trivia, Trivia Time Live, Brainstorm Trivia, Riddlers Trivia | no official domain found (every likely domain fails to resolve or redirects elsewhere; no web search available this session). Not assessed | DNS checks 2026-10-16 |
| District Trivia | DC only (skipped by design) | — |
## Denver / Seattle / Austin coverage (session 2)

Added 2026-10-16 to lift the thinnest cities. Every unit ran live once with
`gotc run --city <slug> --source <id> --force --no-geocode` from our UA (robots enforced by `PoliteClient`); the
count is valid records after the final config (0 rejects everywhere). New adapter: **`rss_events`** (RSS 2.0 +
the RSS event module, `ev:startdate`/`ev:location`; carbonhouse venue sites serve it at `/events/rss`). Adapter
tweaks: `jsonld` `date_only` + cancelled/postponed titles + no prices from `$`-less text; `tribe` `venue` fallback;
`ics` `force_category`.

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `jeffco_library_events` | denver | BiblioCommons RSS / `bibliocommons` | https://gateway.bibliocommons.com/v2/libraries/jeffcolibrary/rss/events | none | ~12 pages/day | gateway host has no robots.txt; published feed | as `hclib_events`; `cities` keeps Lakewood/Arvada/Wheat Ridge/Golden/Edgewater/Littleton | events · 24h | A- | 210 |
| `arapahoe_library_events` | denver | BiblioCommons RSS / `bibliocommons` | …/libraries/arapahoelibraries/rss/events | none | ~7 pages/day | same | as above; Centennial/Denver/Englewood/Littleton/Sheridan branches; trustee meetings skipped | events · 24h | A- | 108 |
| `cervantes_denver` | denver | Rockhouse WP + Event JSON-LD / `jsonld` (follow) | https://cervantesmasterpiece.com/ | none | 1 listing + ≤40 detail pages at ≥2 s | robots: only wp-admin etc. | name, start (offset), room, Etix offer link | concerts · 12h | C+ (scrape of structured data) | 40 |
| `denver_arts_venues` | denver | carbonhouse RSS / `rss_events` | https://www.artscomplex.com/events/rss | none | 1 request/day | robots allows all; city-owned (Denver Arts & Venues) | title, link, ev:startdate/enddate (UTC), ev:location (room → category, Dazzle address) | concerts · 24h | B+ (official city venue feed) | 110 |
| `denver_coliseum` | denver | carbonhouse RSS / `rss_events` | https://www.denvercoliseum.com/events/rss | none | 1 request/day | robots allows all; city-owned | as above | events · 24h | B+ | 26 |
| `denver_pioneers_athletics` | denver | SIDEARM ICS / `ics` | https://denverpioneers.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day | robots allows it; subscription feed | SUMMARY, DTSTART, LOCATION (home = starts with "Denver") | events · 24h | B | 32 |
| `kcls_events` | seattle | BiblioCommons RSS / `bibliocommons` | …/libraries/kcls/rss/events | none | ≤30 pages/day, 7-day horizon | gateway host, no robots.txt | as `hclib_events`; branches within ~20 km of downtown | events · 24h | A- | 258 |
| `seattle_city_events` | seattle | Trumba JSON / `trumba` | https://www.trumba.com/calendars/seattlegov-city-wide.json | none | 1 request/day | trumba.com robots allows all; the calendar seattle.gov embeds | title, offset times, location, Event Types; council/committee/board meetings and WebEx skipped | events · 24h | A- (official city calendar) | 87 |
| `mohai_events` | seattle | WP The Events Calendar / `tribe` | https://mohai.org/wp-json/tribe/events/v1/events | none | ≤3 pages/day | REST allowed | as `mprb_events` | events · 24h | B+ | 11 |
| `town_hall_seattle` | seattle | WP The Events Calendar / `tribe` | https://townhallseattle.org/wp-json/tribe/events/v1/events | none | ≤4 pages/day | REST allowed by robots and answered 200; the HTML site shows a Cloudflare challenge we never attempt | as above + sliding-scale prices | events · 24h | B (could start challenging) | 59 |
| `visit_ballard_events` | seattle | WP The Events Calendar / `tribe` | https://www.visitballard.com/wp-json/tribe/events/v1/events | none | ≤8 pages/day | REST allowed | as above (trivia, open mics, markets, classes) | events · 24h | B+ | 87 |
| `stg_presents` | seattle | Modern Events Calendar JSON-LD / `jsonld` (listing only) | https://www.stgpresents.org/calendar/ | none | 1 page/day | robots allows it | name, date, theatre + address; `date_only` (stated times are 7 h early), `trust_valid_from: false` ("0" price, validFrom = event date); classes/tours skipped | concerts · 24h | C+ (dates only) | 44 |
| `uw_athletics` | seattle | SIDEARM ICS / `ics` | https://gohuskies.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day | robots allows it; subscription feed | SUMMARY, DTSTART (UTC/all-day), LOCATION (home = starts with "Seattle"); `force_category: sports_watch.game` | events · 24h | B | 31 |
| `earshot_jazz` | seattle | WP The Events Calendar / `tribe` | https://www.earshot.org/wp-json/tribe/events/v1/events | none | ≤8 pages/day | REST allowed | regional jazz gigs with venue + geo + cost; far-off towns skipped | concerts · 24h | B+ | 274 |
| `laughs_comedy_seattle` | seattle | WP The Events Calendar / `tribe` | https://laughscomedyclub.com/wp-json/tribe/events/v1/events | none | ≤3 pages/day | REST allowed | as above | events · 24h | B | 16 |
| `unexpected_productions` | seattle | WP The Events Calendar / `tribe` | https://www.unexpectedproductions.org/wp-json/tribe/events/v1/events | none | ≤4 pages/day | REST allowed | as above | events · 24h | B | 49 |
| `flamingo_cantina` | austin | WP The Events Calendar / `tribe` | https://flamingocantina.com/wp-json/tribe/events/v1/events | none | ≤3 pages/day | REST allowed | as above; blank venues filled from `venue` | concerts · 12h | B | 11 |
| `wildflower_center_events` | austin | WP The Events Calendar / `tribe` | https://www.wildflower.org/wp-json/tribe/events/v1/events | none | ≤4 pages/day | REST allowed (UT Austin's botanic garden) | as above; member-only events skipped | events · 24h | B+ | 57 |
| `contemporary_austin_events` | austin | WP The Events Calendar / `tribe` | https://thecontemporaryaustin.org/wp-json/tribe/events/v1/events | none | ≤2 pages/day | REST allowed by robots and answered 200; HTML pages show a Cloudflare challenge we never attempt | as above | events · 24h | B (could start challenging) | 14 |
| `austin_parks_foundation_events` | austin | Modern Events Calendar JSON-LD / `jsonld` (listing only) | https://austinparks.org/event-calendar/ | none | 1 page/day | robots allows it | name, date (all-day), park + address; validFrom not trusted | events · 24h | B- (dates only) | 17 |
| `acl_live` | austin | carbonhouse RSS / `rss_events` | https://www.acllive.com/events/rss | none | 2 requests/day | robots allows all; terms (Ryman Hospitality) have no automated-access clause | title, link, ev:startdate (UTC), room | concerts · 12h | B+ | 91 |
| `heb_center` | austin | carbonhouse RSS / `rss_events` | https://www.hebcenter.com/events/rss | none | 1 request/day | robots allows it; City of Cedar Park arena | as above (Texas Stars, Austin Spurs, concerts) | events · 24h | B+ | 49 |
| `cap_city_comedy` | austin | Event JSON-LD on the homepage / `jsonld` | https://www.capcitycomedy.com/ | none | 1 page/day | robots allows all; terms have no automated-access clause | name, start (UTC), club address (one Place block with an `Events` list) | events · 24h | C+ | 102 |

**Tried and not added (session 2).**

| Source | City | Why it isn't used | Evidence |
|---|---|---|---|
| Live Nation venue sites (Marquis, Summit, Fillmore; Emo's, Scoot Inn) | DEN/AUS | Event JSON-LD is there, but Live Nation/Ticketmaster terms forbid automated access; their shows arrive via the Ticketmaster API once a key is set | 2026-10-16 probe |
| Prekindle organizer pages (Mohawk Austin and others) | AUS | Rich JSON-LD with face-value prices, but prekindle.com/terms-of-use: "You may not use any software, tool… to 'scrape' or otherwise compile data" | https://www.prekindle.com/terms-of-use |
| AEG Presents venue JSON (`aegwebprod.blob.core.windows.net/json/events/<id>/events.json`: Mission Ballroom, Bluebird, Ogden, Gothic, Fiddler's Green) | DEN | Undocumented blob behind AEG's Next.js sites; AEG's terms page didn't render to us, so we couldn't confirm automated use is allowed. Ask AEG first | 2026-10-16 probe |
| Neumos / Showbox carbonhouse RSS | SEA | Feed has no `ev:` dates (title text only, ~10 items) | /events/rss |
| Red Rocks (redrocksonline.com) | DEN | No JSON-LD; custom `clique/v1` WP endpoints without event dates; WP feed has publish dates only | 2026-10-16 probe |
| Come and Take It Live | AUS | Rockhouse site without Event JSON-LD on its pages (0 records on the live run) — removed | `gotc run` 2026-10-16 |
| Goosetown Tavern, Antone's, Tractor Tavern, The Crocodile | DEN/AUS/SEA | No JSON-LD / JS-only ticketing widgets (Rockhouse without SEO markup, TicketWeb plugin, Webflow + TicketWeb links) | probe |
| Austin Public Library (Drupal) | AUS | Event JSON-LD has no branch/location (all events would map to one point); 60 listing pages | probe |
| austintexas.gov events (Drupal) | AUS | JSON-LD times are UTC labeled `-05:00` (10 AM event stamped 15:00-05:00) | probe |
| Denver Botanic Gardens | DEN | JSON-LD times are UTC without an offset and the HTML inside is mangled | probe |
| DU calendar (LiveWhale v2) | DEN | Mostly internal/student items, "Sign in to download the location"; first 100 items cover ~4 days | probe |
| Seattle Art Museum, Hole in the Wall, Empire Control Room, Cactus Cafe, Texas Performing Arts, Arvada, Englewood, Auraria | SEA/AUS/DEN | robots.txt disallows | probe |
| Pike Place Market, Stubb's, Long Center, Continental Club, Chop Suey, Dazzle (own site), Swallow Hill, Denver Zoo, Clyfford Still, Kirkland Museum, MSU Denver, Bullock Museum | SEA/AUS/DEN | Cloudflare challenge (403 "Just a moment…") — not attempted | probe |
| History Colorado | DEN | HTTP 202 with an empty body (bot challenge) | probe |
| "aurora" BiblioCommons library | DEN | It is Aurora, **Ontario** | feed `bc:state` |
| Levitt Pavilion Denver | DEN | Squarespace, season over (0 upcoming); revisit in spring | probe |
| Westminster / Lakewood / Littleton city calendars (CivicPlus, Granicus OpenCities) | DEN | Usable (CivicPlus iCalendar), but tiny (≤ 10 events each) | probe |

## Batch A cities

Onboarded 2026-10-16 (dallas, houston). Every unit ran live once with
`gotc run --city <slug> --no-geocode` from our UA (robots enforced by `PoliteClient`, ≥2 s per host); the count is
valid records from that run (0 rejects unless noted). The global `upcomingcons` unit covers cons in each city
automatically; Ticketmaster/SeatGeek/RunSignup stay key-gated.

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `downtown_dallas_events` | dallas | WP The Events Calendar / `tribe` | https://www.downtowndallas.com/wp-json/tribe/events/v1/events | none | ≤6 pages/day; robots `Crawl-delay: 10` (honored) | REST allowed by robots | as `mprb_events` (happy hours, markets, museum programs, comedy, fitness) | events · 24h | B+ (business-district calendar) | 163 |
| `dallas_parks_events` | dallas | CivicPlus iCalendar / `ics` | https://www.dallasparks.org/common/modules/iCalendar/iCalendar.aspx?catID=14&feed=calendar (+ catID 39, 31) | none | 3 requests/day | robots disallows only admin/search/`RSS.aspx`; the iCalendar module is allowed | SUMMARY, TZID DTSTART/DTEND, LOCATION; park-board meetings skipped | events · 24h | A- (official, small: ~30 dated items) | 86 |
| `dallas_arboretum` | dallas | WordPress + Event JSON-LD / `jsonld` (listing only) | https://www.dallasarboretum.org/events-activities/ | none | 1 page/day | robots allows it | name, start (offset), garden area | events · 24h | B- (season-long programs, ~13) | 13 |
| `utdallas_events` | dallas | Localist / `localist` (`type` = Target audience "General Public") | https://calendar.utdallas.edu/api/2/events | none | ≤4 pages/day; robots `Crawl-delay: 1` | allowed | as `usc_events`; campus fallback point | events · 24h | B (public filter cuts 660 → ~90 items) | 59 |
| `uta_events` | dallas | Localist / `localist` (`type` = "Events for: Local Community") | https://events.uta.edu/api/2/events | none | ≤4 pages/day; robots `Crawl-delay: 1` | allowed | as `usc_events`; event types → categories | events · 24h | B- | 72 |
| `smu_athletics` | dallas | SIDEARM ICS / `ics` | https://smumustangs.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day (robots `Crawl-delay: 30`) | robots allows it; subscription feed | SUMMARY, DTSTART, LOCATION (home = starts with "Dallas") | events · 24h | B | 45 |
| `american_airlines_center` | dallas | carbonhouse RSS / `rss_events` | https://www.americanairlinescenter.com/events/rss | none | 1 request/12h | robots allows all | title, link, ev:startdate (UTC) | concerts · 12h | B+ (Mavericks, Stars, arena concerts) | 93 |
| `tabc_pending_openings_dallas` | dallas | Socrata `mxm5-tdpj` (data.texas.gov) / `socrata` | https://data.texas.gov/d/mxm5-tdpj | none | Socrata throttling | as `tabc_pending_openings_austin`; Dallas + 11 inner-ring cities | as Austin | openings · 24h | A | 32 |
| `tabc_new_licenses_dallas` | dallas | Socrata `7hf9-qc9f` (data.texas.gov) / `socrata` | https://data.texas.gov/d/7hf9-qc9f | none | Socrata throttling | as `tabc_new_licenses_austin` | as Austin (**original_issue_date**) | openings · 24h | A | 48 |
| `teamtrivia_dallas` | dallas | Team Trivia venue pages / `teamtrivia` | https://www.teamtrivia.com/trivia-in-dallas-fort-worth/ | none | 1 region page + ≤60 venue pages / 48h, ≥3 s | region/venue pages allowed and in the site's sitemap; zip gate never used | as `teamtrivia_denver` | recurring · 48h | B | 64 |
| `challenge_trivia_dallas` | dallas | Challenge Entertainment JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request/48h | robots allows all | as `challenge_trivia_nashville`; metro-dallas-ft-worth within 60 km | recurring · 48h | C+ (undocumented JSON) | 176 |
| `hcpl_events` | houston | BiblioCommons RSS / `bibliocommons` | https://gateway.bibliocommons.com/v2/libraries/hcpl/rss/events | none | ≤20 pages/day, 10-day horizon | gateway host has no robots.txt; published feed (code confirmed by the channel title "Harris County Public Library") | as `hclib_events`; `cities` keeps Houston + inner-ring branches | events · 24h | A- | 260 |
| `buffalo_bayou_events` | houston | WP The Events Calendar / `tribe` | https://buffalobayou.org/wp-json/tribe/events/v1/events | none | ≤3 pages/day | REST allowed | as `mprb_events` (tours, paddles, volunteer workdays) | events · 24h | B+ | 41 |
| `hermann_park_events` | houston | WP The Events Calendar / `tribe` | https://www.hermannpark.org/wp-json/tribe/events/v1/events | none | ≤2 pages/day | REST allowed | as above | events · 24h | B | 9 |
| `levy_park_events` | houston | WP The Events Calendar / `tribe` | https://www.levyparkhouston.org/wp-json/tribe/events/v1/events | none | ≤4 pages/day | REST allowed | as above; blank venues → the park | events · 24h | B+ (free fitness classes, markets) | 57 |
| `memorial_park_events` | houston | WP The Events Calendar / `tribe` | https://www.memorialparkconservancy.org/wp-json/tribe/events/v1/events | none | ≤3 pages/day | REST allowed | as above | events · 24h | B | 26 |
| `houston_arboretum_events` | houston | WP The Events Calendar / `tribe` | https://houstonarboretum.org/wp-json/tribe/events/v1/events | none | ≤3 pages/day | REST allowed | as above; blank venues → the arboretum | events · 24h | B | 30 |
| `rice_events` | houston | LiveWhale JSON / `livewhale` | https://events.rice.edu/live/json/events/max/300 | none | 1 request/day | allowed | as `umn_events` (audience filter; the type-path filter is ignored by this install) | events · 24h | B | 72 |
| `uh_athletics` | houston | SIDEARM ICS / `ics` | https://uhcougars.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day (robots `Crawl-delay: 30`) | robots allows it; subscription feed | SUMMARY, DTSTART, LOCATION (home = starts with "Houston") | events · 24h | B | 38 |
| `rice_athletics` | houston | SIDEARM ICS / `ics` | https://riceowls.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day (robots `Crawl-delay: 30`) | as above | home = "Houston…" or a Rice venue | events · 24h | B | 29 |
| `toyota_center` | houston | carbonhouse RSS / `rss_events` | https://www.toyotacenter.com/events/rss | none | 1 request/12h | robots allows all | title, link, ev:startdate (UTC) | concerts · 12h | B+ | 65 |
| `volunteer_houston` | houston | Galaxy Digital / `galaxydigital` | https://www.volunteerhou.org/need/rss/ | none | 1 RSS + ≤15 detail pages/day, ≥3 s | robots allows need pages | as `uwkc_volunteer`; tenant verified by RSS title "Needs on Volunteer Houston" and Houston addresses | volunteer · 24h | B+ | 15 |
| `tabc_pending_openings_houston` | houston | Socrata `mxm5-tdpj` (data.texas.gov) / `socrata` | https://data.texas.gov/d/mxm5-tdpj | none | Socrata throttling | as Austin; Houston + 10 inner-ring cities | as Austin | openings · 24h | A | 47 |
| `tabc_new_licenses_houston` | houston | Socrata `7hf9-qc9f` (data.texas.gov) / `socrata` | https://data.texas.gov/d/7hf9-qc9f | none | Socrata throttling | as Austin | as Austin (**original_issue_date**) | openings · 24h | A | 76 |
| `challenge_trivia_houston` | houston | Challenge Entertainment JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request/48h | robots allows all | metro-houston within 60 km | recurring · 48h | C+ | 86 |

**Tried and not added (batch A).**

| Source | City | Why it isn't used | Evidence |
|---|---|---|---|
| Dallas Public Library (LibraryMarket `dallaslibrary.librarymarket.com`) | dallas | robots.txt answers HTTP 403, which RFC 9309 (and PoliteClient) treat as disallow-all | probe 2026-10-16 |
| dallasopendata.com (Socrata) | dallas | No current event, special-event or license datasets (newest building-permit data 2020; inspections end 2024) | catalog API `domains=www.dallasopendata.com` |
| Volunteer Now (`www.volunteernow.org/need/rss/`) | dallas | The Galaxy Digital RSS on that domain is titled "Center for Volunteer & Nonprofit Leadership" and its needs are in Santa Rosa, CA (wrong tenant); `volunteernow.galaxydigital.com` is Washington County | need 1330101 address |
| Dallas Symphony Orchestra | dallas | Cloudflare challenge (403) — not attempted | probe |
| AT&T Performing Arts Center (attpac.org) | dallas | No RSS/Tribe/JSON-LD on listing or event pages | probe |
| Granada Theater, Kessler Theater, Klyde Warren Park (Squarespace / custom) | dallas | No Event JSON-LD, no Tribe | probe |
| Addison Improv (improvtx.com) | dallas | JSON-LD only on detail pages and the listing shows ~6 shows; not worth the scrape yet | probe |
| Frisco Public Library (BiblioCommons `friscolibrary`) | dallas | Works (6 items / 2 days) but Frisco is ~42 km from the center, outside the 30 km circle | gateway RSS |
| Fair Park, Deep Ellum (deepellumtexas.com), Texas Live! | dallas | No feed (404 / WordPress without Tribe / Netlify site without events JSON) | probe |
| data.houstontx.gov (CKAN) | houston | robots.txt `Disallow: /api/` and `/datastore/*` (Crawl-delay 10) | robots.txt 2026-10-16 |
| Houston Public Library (LibCal `calendar.houstonlibrary.org`, cid 15272) | houston | robots allows it (Crawl-delay 10), but `ical_subscribe.php` returns a fixed 500 items starting a month back (all past); the `ct=` filter is ignored. Needs a LibCal JSON adapter (idea) | ICS DTSTART range 2026-09-16…09-24 |
| Team Trivia (trivia-in-houston) | houston | region page lists 0 venues today (live run: empty results) | region page |
| Discovery Green | houston | robots.txt disallows `/wp-json/` | robots |
| MFAH (mfah.org) | houston | robots.txt answers 403 (disallow-all) | probe |
| Hobby Center | houston | Cloudflare challenge — not attempted | probe |
| Smart Financial Centre | houston | redirects to ATG Tickets (no feed) | probe |
| McGonigel's Mucky Duck, Houston Symphony, Da Camera, Menil | houston | no Event JSON-LD / no Tribe | probe |
| Warehouse Live, calendar.uh.edu | houston | TLS certificate errors (can't verify robots) | probe |
