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
  Localist, LiveWhale, Tribe, Simpleview and Communico all go through the robots check. Every other opt-out is
  listed in "Robots exceptions and API usage policies" below.
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

## Robots exceptions and API usage policies (reviewed 2026-10-16)

Every call made with `respect_robots=False`, and why. robots.txt and the operator's API policy were both re-read
on 2026-10-16 with our UA. **Rule:** an opt-out is allowed only for a documented machine API whose operator
publishes terms for programmatic clients, we follow those terms, and the row is listed here. Where the
operator's own policy discourages our kind of use, the source is off.

| host / path | robots.txt (2026-10-16) | operator API policy | our use | stance |
|---|---|---|---|---|
| `api.us.socrata.com`, `<portal>/resource/*.json` (SODA) | catalog host: 301 to nginx page (no policy) | documented SODA API, app tokens optional | adapters + `gotc discover` | ✅ exception (unchanged) |
| `services*.arcgis.com` FeatureServer | 403 "Invalid URL" (no policy) | documented ArcGIS REST | adapters | ✅ exception (unchanged) |
| `geocoding.geo.census.gov` | 404 (no file) | public geocoder, batch ≤ 10,000 rows | batch first, then single-line (per-city budget `GOTC_GEOCODE_BUDGET`) | ✅ allowed (no robots file) |
| `nominatim.openstreetmap.org/search` | **`User-agent: *` `Disallow: /search`** (also /reverse, /lookup, /details) | [OSMF Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/): "an absolute maximum of 1 request per second"; "Scripts running longer than a day and scripts that are run at regular intervals are restricted to 4 requests per minute"; single thread, one machine, "no distributed scripts"; "Results must be cached on your side"; repeated identical queries "may be classified as faulty and blocked"; "periodic requests from apps are considered bulk geocoding and as such are strongly discouraged"; attribution required | **was:** fallback for every place name at 1.1 s, up to 150/city/run (≈55 req/min bursts, a policy violation). **now:** off by default. `GOTC_NOMINATIM=1` opts one process (never a CI shard) into a compliant lane: ≥ 15 s between requests, hard per-run budget `GOTC_NOMINATIM_BUDGET` (default 20) shared by all cities, every answer (hit or miss) cached forever and never re-sent, Census tried first | ⛔ **off** (robots disallows `/search` and the policy discourages periodic app use). Previously cached Nominatim results keep serving; they are © OpenStreetMap contributors (ODbL), so the dashboard must show "Geocoding © OpenStreetMap contributors" wherever coordinates are shown (web/ change pending, see STATUS). |
| `api.weather.gov` | **`User-agent: *` `Disallow: /`** | NWS API docs ask apps for a UA with contact info; no published rate limit | 1 forecast/city per 3 h (`gotc/pipeline/weather.py`) | ⚠ exception kept: documented public API that explicitly expects application clients; flagged for the user to confirm |
| `query.wikidata.org/sparql` (WDQS) | **`User-agent: *` `Disallow: /sparql`**, `Disallow: /bigdata` | WDQS limits (60 s query time/min per UA+IP, UA policy) | **was:** 1 SPARQL/city/week with `respect_robots=False` for venue capacities (`gotc/pipeline/venue_refs.py`), not listed here | ⛔ **stopped** 2026-10-16 |
| `www.wikidata.org/w/api.php` (wbsearchentities / wbgetentities), `/wiki/Special:EntityData` | **`Disallow: /w/`**, `Disallow: /api/`, `Disallow: /wiki/Special:` for `*` (only `api.php?action=mobileview&` is allowed) | MediaWiki API etiquette (maxlag, UA) | considered as the replacement for SPARQL | ⛔ not used: robots disallows it too |
| `app.ticketmaster.com`, `api.seatgeek.com` | — | keyed developer APIs with ToS | key-gated adapters | ✅ exception (unchanged) |

**Venue capacities after the Wikidata stop:** curated `config/venues/<slug>.yaml` entries (each with a
`capacity_source` URL and a verbatim `evidence` quote) are now the only live source. Rows already in the
`venue_refs` table (fetched before 2026-10-16; Wikidata is CC0) keep serving with their QID as the cited source and
are never refreshed. Attendance bands for venues without a capacity fall back to category priors, as before.
`gotc discover` therefore cannot seed venues from Wikidata (SCALING.md §2.5); it fingerprints operator-supplied
seed URLs instead.

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

## Discovery endpoints (`gotc discover`, 2026-10-16)

These are called only by `gotc discover <city>`, out of band, never by the hourly run. Every request goes
through PoliteClient with robots.txt checked first. Live runs on 2026-10-16 for Phoenix and Philadelphia used
43 and 44 requests.

| host / endpoint | robots.txt (2026-10-16, our UA) | use | stance |
|---|---|---|---|
| `api.us.socrata.com/api/catalog/v1` | no robots file (301 to nginx page) | cross-tenant dataset search, filtered to the place/county/state | ✅ documented Discovery API |
| `catalog.data.gov/search` | allowed, `Crawl-Delay: 10` (honored) | local/state datasets; a Socrata `/api/views/<id>` identifier maps straight to a unit | ✅ |
| `hub.arcgis.com/api/search/v1/collections/site/items` | allowed for `/api/`, `Crawl-delay: 60` (honored) | find the official Hub site and its orgId | ✅ one request per city |
| `www.arcgis.com/sharing/rest/search` | allowed | org-scoped Feature Service search | ✅ |
| `services*.arcgis.com/…/FeatureServer/0?f=json` | 403 "Invalid URL" (no policy) | layer fields (date columns) for the top 4 candidates | ✅ the existing ArcGIS exception |
| `geocoding.geo.census.gov/geocoder/geographies/onelineaddress` | no robots file | city hall → county (joins the place terms) | ✅ |
| `geocoding.geo.census.gov/geocoder/locations/onelineaddress` | no robots file | `gotc city recenter`: 49 lookups re-derived 43 of 50 metro centers (6 kept: no match, a different street, or > 5 km away; Hampton Roads has no single address) | ✅ |
| `gateway.bibliocommons.com/v2/libraries/<code>/rss/events` | no robots file | 1-day window per guessed or linked code; 404 = unknown code | ✅ (never `<code>.bibliocommons.com`, Crawl-delay 120) |
| `<tenant>.galaxydigital.com/need/rss/` | marketing paths only | tenant probe; unknown tenants answer 200 "Bad Domain" | ✅ |
| `www.volosports.com/discover[/<market>]` | allows all but /rfo /admin /staff | market list + "N ways to play" | ✅ |
| `www.teamtrivia.com/sitemap-locations.php` | allowed (the site's own sitemap) | region list | ✅ |
| `challengeentertainment.com/wp-json/ce/v1/shows` | Yoast default (all allowed) | national feed filtered to the radius → `metro-*` classes | ✅ |
| LibCal (`<host>/calendar`, `ical_subscribe.php`) | Crawl-delay 10 on `*.libcal.com` (honored) | public calendar ids → one ICS per calendar | ✅ |
| Localist `/api/2/events`, LiveWhale `/live/json/…`, WP `/wp-json/`, carbonhouse `/events/rss` | per host, checked | endpoint probes on seed domains | ✅ when allowed |
| Live Nation / Ticketmaster / AEG / Prekindle / LeagueLab hosts | — | never requested (`config/discovery_denylist.yaml`) | ⛔ ToS |

**Found blocked during the first live runs** (recorded, not worked around):
- `www.freelibrary.org` and `www.upenn.edu`: robots.txt answers HTTP 403, so PoliteClient treats it as "disallow all" (RFC 9309).
- `www.phoenix.gov/parks` links the city's ActiveNet registration (`anc.apm.activecommunities.com`). It's flagged `manual_review`, because its ToS is unread.
- `events.mcldaz.org` (Maricopa County Library District) runs an events platform we have no adapter for.

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

## Batch D cities

Onboarded 2026-10-16: Tampa, Orlando, Jacksonville, Charlotte, Raleigh, Memphis, Birmingham, Oklahoma City,
Providence, Hartford. Same columns as the city sources table. **Verified** = valid records on the first live
run (`gotc run --city <slug> --no-geocode`, 2026-10-16). Every fetched URL was re-audited against robots.txt
with RFC 9309 wildcard semantics (the parser PoliteClient now uses); units on hosts that serve our client a
Cloudflare challenge anywhere are disabled even when an API path on the same host answered.

### Tampa

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `tampa_hcplc_events` | tampa | Communico `eeventcaldata` / `communico` | https://attend.hcplc.org/eeventcaldata | none | 7 requests/day (one per day of horizon, ~60 KB each) | **undocumented** front-end JSON; robots disallows only /results*, /sitesearch* | title, sub_title, description, local start/end, branch, room, tags, ages, registration; staff contact never mapped | events · 24h | B (official library data via an undocumented endpoint) | 152 |
| `tampa_ut_events` | tampa | Trumba JSON / `trumba` | https://www.trumba.com/calendars/ut-events.json | none | 1 request/day | trumba.com robots allows all; ut.edu robots allows the calendar page | title, start/end+offset, location, "Type of Event" (Student Event → skipped as campus catch-all) | events · 24h | C+ (≈90% student-only items filtered out; ~10 public items left) | 13 (of 200; rest skipped) |
| `tampa_usf_athletics` | tampa | SIDEARM ICS / `ics` | https://gousfbulls.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day | robots blocks only named bots + /admin/, /services/ | SUMMARY, DTSTART, LOCATION (home = starts with "Tampa") | events · 24h | A- | 33 |
| `tampa_downtown_events` | tampa | schema.org JSON-LD (listing page) / `jsonld` | https://www.tampasdowntown.com/all-events/ | none | 1 request/day | robots allows all | name, date-only start/end, place name+address | events · 24h | B- (date-only; multi-week exhibits) | 21 |
| `tampa_benchmark_arena` | tampa | WP The Events Calendar / `tribe` | https://www.benchmarkintlarena.com/wp-json/tribe/events/v1/events | none | ≤ 4 pages/12h | robots allows all; arena's own site (county-owned, Vinik Sports Group), not a Live Nation/TM site | title, start/end+tz, venue, categories, cost | concerts · 12h | B+ | 69 |
| `tampa_yuengling_center` | tampa | WP The Events Calendar / `tribe` | https://www.yuenglingcenter.com/wp-json/tribe/events/v1/events | none | ≤ 3 pages/12h | robots allows all | as above | concerts · 12h | B+ | 18 |
| `tampa_ruth_eckerd_hall` | tampa | carbonhouse RSS / `rss_events` | https://www.rutheckerdhall.com/events/rss | none | 1 request/12h | robots allows all | title, ev:startdate/enddate, ev:location (REH, Capitol Theatre, BayCare Sound, Jannus Live, Tampa Theatre), link | concerts · 12h | A- | 139 |
| `tampa_volunteer_suncoast` | tampa | HandsOn Connect / `handsonconnect` | `POST www.volunteersuncoast.org/search/getOpportunitiesCalendar` (block 1935) | none | 7 POSTs/day (2-day windows × 14 days), ≥3 s | robots.txt 404 (no rules); no ToS clause found | title, shift start/end, organization, address, volunteersStillNeeded | volunteer · 24h | B (undocumented endpoint used by the site's own calendar) | 40 |
| `teamtrivia_tampa` | tampa | Team Trivia venue pages / `teamtrivia` | https://www.teamtrivia.com/trivia-in-tampa/ | none | 1 region + ~3 venue pages / 48h, ≥3 s | allowed + in the site's sitemap; zip gate never used | venue, JSON-LD dated games | recurring · 48h | B (small market: 3 venues) | 8 |
| `challenge_trivia_tampa` | tampa | Challenge Entertainment JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request/48h | robots allows all; no terms page | as Nashville; metro-tampa within 2× radius | recurring · 48h | C (undocumented) | 72 |
| `fl_dbpr_openings_tampa` | tampa | Florida DBPR CSV extract / `csvfile` | https://www2.myfloridalicense.com/sto/file_download/extracts/bd4006lic.csv | none | 1 request/day (~14 MB, conditional GET) | robots allows /sto/ | DBA, series (COP only), address, **Original Licensure Date**; Location County 39 (Hillsborough) + 62 (Pinellas); owner dropped | openings · 24h | A- | 67 |

Rejected / not used (Tampa):

- St. Petersburg Library System (splibraries.org): robots `User-agent: * / Crawl-delay: 10 / Disallow: /`.
- Clearwater Public Library (myclearwaterlibrary.librarymarket.com): robots.txt → HTTP 403 → treated as disallow-all.
- USF events: www.usf.edu robots `Disallow: /calendar`; calendar.usf.edu doesn't resolve; events.usf.edu → 503 (Dynamics portal error).
- tampa.gov: 403 (Cloudflare-style error page) — not pursued.
- Straz Center: robots.txt redirect loop; not pursued.
- Mahaffey Theater, Tampa Theatre, Jannus Live: WordPress without Tribe or Event JSON-LD (Jannus links to Ticketmaster; its shows partly arrive via the REH feed).
- Side Splitters Comedy: listings are punchup.live links (third-party ticketing), no JSON-LD — not added.
- Open data: Socrata catalog `q=tampa` → only USDOT/VA datasets; ArcGIS Online search (Tampa/Hillsborough/Pinellas × event/permit/license) → no events/special-event/business-license layers (only building/historic permits, floods, trails).
- Galaxy Digital guesses (uwsuncoast, unitedwaysuncoast, volunteertampabay, hillsborough) → "Bad Domain"; the real platform is HandsOn Connect (volunteersuncoast.org).
- Live Nation-owned MidFlorida Credit Union Amphitheatre: skipped by policy.

### Orlando

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `ocls_events` | orlando | Communico `eeventcaldata` (attend.ocls.org) / `communico` | https://attend.ocls.org/eeventcaldata | none | 10 requests/day (one per day of horizon, ~150 KB each) | **undocumented** front-end JSON; robots disallows only /results*, /sitesearch* | title, description, local start/end, branch, tags, ages, registration (close, capacity, registrants), cost; staff contact never mapped | events · 24h | B (official library data via an undocumented endpoint; online classes, social-worker hours and studio reservations skipped) | 381 |
| `ucf_events` | orlando | UNIFY events ICS / `ics` | https://events.ucf.edu/calendar/1/events-at-ucf/this-month/feed.ics (+ `/upcoming/feed.ics`) | none | 2 requests/day | robots.txt 404 (no rules); feeds linked from the calendar page | summary, start/end, location, URL, description | events · 24h | B (official; no audience field, institution filter screens internal items; "this-month" thins out late in the month) | 60 (4 rejected: invalid URL) |
| `orlando_museum_of_art` | orlando | WP The Events Calendar / `tribe` | https://omart.org/wp-json/tribe/events/v1/events | none | ≤ 4 pages/day | robots disallows only /wp-admin/ and `*ical=*` | as MPRB | events · 24h | B+ | 38 |
| `ivanhoe_village_events` | orlando | WP The Events Calendar / `tribe` | https://ivanhoevillage.org/wp-json/tribe/events/v1/events | none | Crawl-delay 3 | **robots `Disallow: /*?`** covers the API query string | — | events · 24h | D for us (disabled) | disabled |
| `kia_center` | orlando | carbonhouse events RSS / `rss_events` | https://www.kiacenter.com/events/rss | none | 2 requests/day | robots `User-agent: *` with no rules; city-owned (Orlando Venues) | title, ev:startdate/enddate, link, description ticket links | concerts · 12h | A- (Magic and Solar Bears games → spectator sports) | 104 |
| `camping_world_stadium` | orlando | carbonhouse events RSS / `rss_events` | https://www.campingworldstadium.com/events/rss | none | 1 request/day | as Kia Center | as Kia Center | events · 24h | B+ (few, big events) | 7 |
| `challenge_trivia_orlando` | orlando | Challenge show-finder JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request/48h | robots allows all; no terms page | as Nashville | recurring · 48h | C (undocumented) | 36 |
| `orlando_restaurant_openings` | orlando | Socrata `7388-4re5` (data.cityoforlando.net) / `socrata` | https://data.cityoforlando.net/d/7388-4re5 | none | Socrata throttling | City of Orlando open data; owner/phone/e-mail/mailing address dropped | business name, license type (RESTAURANT / TAKE OUT RESTAU), address, neighborhood, point, **business_open_date** | openings · 24h | A- | 9 |
| `fl_dbpr_openings_orlando` | orlando | Florida DBPR ABT CSV / `csvfile` | https://www2.myfloridalicense.com/sto/file_download/extracts/bd4006lic.csv | none | 1 download/day (~14 MB, Last-Modified honoured) | robots allows /sto/ | as Miami; Location County 58 (Orange) + 69 (Seminole), COP series | openings · 24h | A | 59 |

Rejected / not used (Orlando):

- Dr. Phillips Center: `/events/rss` → 403 Bunny Shield "Establishing a secure connection" challenge (and robots `Disallow: /*?*`).
- Heart of Florida United Way (hfuw.org): robots.txt answers 403 → treated as disallow-all. Its portal volunteer.hfuw.org is **Golden Volunteer** (cdn.goldenvolunteer.com), no adapter. Galaxy guesses hfuw / volunteerorlando / heartofflorida → "Galaxy Digital: Bad Domain".
- UCF Knights athletics: not SIDEARM; `calendar.ashx/calendar.ics` and `/calendar` → 404.
- Plaza Live: Webflow, JSON-LD is injected by client-side JS; tickets on AXS (AEG).
- Will's Pub: own WP site with TicketWeb listings but no Event JSON-LD (Crawl-delay 10).
- The Social / The Beacham: Duda sites with a tkx.live widget, no JSON-LD.
- orlando.gov/Events and downtownorlando.com/Fun/Events: Granicus OpenCities HTML, no ICS/RSS/JSON-LD.
- Orlando Science Center (tribe works, 487 events) — skipped: daily building hours/exhibit schedule, would flood the feed.
- Orlando Shakes tribe: 0 events. Lake Nona, Leu Gardens, Mills 50, downtownorlando: no tribe route.
- Timucua: robots `Disallow: /`. Winter Park Library, Seminole County library pages: robots disallow. City of Winter Park, SAK Comedy Lab: Cloudflare.
- Rollins (calendar./events. Localist/LiveWhale probes) and Valencia Localist: connection timeouts; rollins.edu/events has no feed links.
- Orlando sidewalk café permits (6sbc-v4b9): only ~8 applications in 3.5 months and contact-heavy; not added.
- Volo: no Orlando market. Team Trivia: no Orlando region.

### Jacksonville

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `jax_library_events` | jacksonville | Communico `eeventcaldata` / `communico` | https://jaxpubliclibrary.libnet.info/eeventcaldata | none | 7 requests/day (one per day of horizon, ~60 KB each) | **undocumented** front-end JSON on the vendor host; libnet.info robots disallows only /results*, /sitesearch* (jaxpubliclibrary.org itself answers robots 403 and is never fetched) | title, sub_title, description, local start/end, branch, room, tagsArray, agesArray, registration (capacity, registrants), cost | events · 24h | B (official library data via an undocumented endpoint) | 180 |
| `unf_events` | jacksonville | Localist / `localist` | https://events.unf.edu/api/2/events?type=41614676488110 | none | ≤ 5 pages/day; robots `Crawl-Delay: 1` | allowed (disallows only HTML ?types, old calendar paths) | title, instances, venue+geo, filters, free/ticket url; server-side "Event Audience: Public" filter + `audience_filter: institution` | events · 24h | B (public subset incl. MOCA Jacksonville workshops; some academic talks) | 92 |
| `fl_dbpr_openings_jacksonville` | jacksonville | Florida DBPR ABT CSV / `csvfile` | https://www2.myfloridalicense.com/sto/file_download/extracts/bd4006lic.csv | none | 1 × ~14 MB/day, conditional GET | robots allows /sto/ (blocks only WP internals) | DBA (org legal name only if it looks like an organisation), series (COP only), address, **Original Licensure Date**; Location County 26 (Duval) + 20 (Clay); Owner Name dropped | openings · 24h | A- | 29 |
| `florida_theatre_jax` | jacksonville | carbonhouse events RSS / `rss_events` | https://www.floridatheatre.com/events/rss | none | 1 request/12h (~2.2 MB) | robots allows; public syndication feed | title, ev:startdate/enddate (UTC), ev:type (Concerts/Comedy/Family Shows/Theater/Dance), link | concerts · 12h | B+ (carbonhouse feed; blank line before `<?xml` handled by safe_xml since e9381ee) | 113 |
| `ponte_vedra_concert_hall` | jacksonville | carbonhouse events RSS / `rss_events` | https://www.pvconcerthall.com/events/rss | none | 1 request/12h | robots `User-agent: *` with no rules; St. Johns County Cultural Events venue | title, ev:startdate/enddate, ev:type, link | concerts · 12h | A- | 48 |
| `comedy_zone_jax` | jacksonville | schema.org JSON-LD / `jsonld` | https://www.comedyzone.com/ | none | 1 request/12h | robots.txt has no rules (all commented out); no terms page linked | Event name, startDate (UTC), url, venue (Place 3130 Hartley Rd) — nested under a non-standard `Place.Events` key | events · 12h | B (official club calendar; no prices in the LD) | 87 |
| `unf_athletics` | jacksonville | SIDEARM calendar.ics / `ics` | https://unfospreys.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day | robots allows /calendar.ashx | SUMMARY, DTSTART, LOCATION (home = starts "Jacksonville") | events · 24h | A- | 33 |
| `ju_athletics` | jacksonville | SIDEARM calendar.ics / `ics` | https://judolphins.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day | robots allows /calendar.ashx | as UNF | events · 24h | A- | 47 |
| `jax_icemen` | jacksonville | team ICS / `ics` | https://jacksonvilleicemen.com/schedule-home.ics | none | 1 request/day | robots allows; subscription feed linked from the homepage | SUMMARY (promo-night name), DESCRIPTION (matchup), DTSTART (TZID), LOCATION, URL | events · 24h | B+ (titles are promo names like "Halloween") | 15 |
| `uw_nefl_volunteer` | jacksonville | Galaxy Digital / `galaxydigital` | https://uwnefl.galaxydigital.com/need/rss/ + detail pages | none | 24 h, ≥3 s/req, ≤15 detail pages | Galaxy robots: `*` empty Disallow; tenant title "Needs on United Way of Northeast Florida" | need title, date line/shifts, address, nonprofit, registration closes | volunteer · 24h | B | 25 (2 rejected: no date line) |
| `volo_jacksonville` | jacksonville | Volo discover pages / `volo` | https://www.volosports.com/discover/jacksonville?category=leagues | none | ≤3 pages/day, ≥3 s | robots allows all but /rfo /admin /staff | as other Volo markets | leagues · 24h | C (market listed in sitemap; "0 ways to play" on 2026-10-16) | 0 |
| `teamtrivia_jacksonville` | jacksonville | Team Trivia venue pages / `teamtrivia` | https://www.teamtrivia.com/trivia-in-jacksonville-fl/ | none | 48 h | as teamtrivia_denver | as teamtrivia_denver | recurring · 48h | — **disabled**: region page says "0 venues, 0 nights a week" | disabled |

Rejected / not used (Jacksonville):

| Source | Why it isn't used | Evidence |
|---|---|---|
| jaxpubliclibrary.org (main site) | robots.txt answers HTTP 403 → treated as disallow-all (events come from its Communico tenant instead) | probe 2026-10-16 |
| Downtown Jacksonville / DTJax (dtjax.com, The Events Calendar, 721 events) | robots.txt `Disallow: /*?*`; the Tribe REST API needs query parameters | dtjax.com/robots.txt |
| jaxevents.com (VyStar Veterans Memorial Arena, Times-Union Center/PAC, Ritz Theatre, ballpark, convention center; JSON-LD present) | Legends Global Terms of Use prohibit "spiders, robots … to harvest or collect such information" | legendsglobal.com/terms-of-use/ |
| Jack Rabbits, Underbelly (music clubs) | robots.txt disallows all | robots.txt |
| Cummer Museum events | Cloudflare "Just a moment…" challenge | probe 2026-10-16 |
| Daily's Place carbonhouse RSS | empty channel | probe |
| City of Jacksonville (jacksonville.gov, events.jacksonville.gov) | Kentico pages; no feed/JSON-LD | probe |
| Jacksonville open data | no Socrata tenant; ArcGIS Online search found no events/permit/license layers from COJ | catalog + arcgis search 2026-10-16 |
| Jacksonville Symphony, MOSH | no machine-readable calendar (Elementor / no JSON-LD) | probe |
| Challenge Entertainment | no shows within 60 km | national feed 2026-10-16 |

### Charlotte

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `clt_cmlibrary_events` | charlotte | BiblioCommons RSS / `bibliocommons` | https://gateway.bibliocommons.com/v2/libraries/cmlibrary/rss/events | none | ~20 pages/day (horizon 10 days); gateway host has no robots.txt | published RSS feed linked from cmlibrary.org | title, description, bc:start/end local, branch address+geo, categories, registration | events · 24h | A- (official; countywide, filtered to Charlotte, Matthews, Mint Hill, Huntersville, Pineville) | 440 |
| `clt_uncc_events` | charlotte | Localist / `localist` | https://campusevents.charlotte.edu/api/2/events | none | ≤ 5 pages/day; robots `Crawl-Delay: 1` | allowed (disallows only HTML calendar permutations) | title, instances, venue+geo, filters, free/ticket url; 49ers games excluded (see athletics unit) | events · 24h | B (official; mostly student life) | 172 |
| `clt_49ers_athletics` | charlotte | SIDEARM calendar.ics / `ics` | https://charlotte49ers.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots Crawl-delay 30 | allowed (robots blocks admin/assets only) | SUMMARY, DTSTART, LOCATION (home games only: LOCATION starts with "Charlotte") | events · 24h | A- | 22 |
| `clt_cmpd_community_events` | charlotte | ArcGIS Server MapServer table / `arcgis` (`format: json`, `respect_robots: true`) | https://gis.charlottenc.gov/arcgis/rest/services/CMPD/CMPDEvents_tb/MapServer/0 | none | 1 request/day | self-hosted city server, robots.txt 404 (no rules); listed on data.charlottenc.gov; DEPARTMENTCONTACTPHONE dropped by the privacy scrub | description, category, division, start/end (epoch ms), location description, street number/name, notes; cancelled and virtual rows filtered server-side | events · 24h | B+ (official police-division community meetings/outreach; no geometry, geocoded) | 168 |
| `clt_spectrum_center` | charlotte | carbonhouse events RSS / `rss_events` | https://www.spectrumcentercharlotte.com/events/rss | none | 1 request/12h | robots `User-agent: *` with no rules | title, ev:startdate, link (Hornets games → sports_watch.game) | concerts · 12h | B+ | 65 |
| `clt_blumenthal_arts` | charlotte | carbonhouse events RSS / `rss_events` | https://www.blumenthalarts.org/events/rss | none | 1 request/day | robots `User-agent: *` with no rules | title, ev:startdate, ev:location (room → address for the four PAC theaters; off-site rooms keep their name), ev:type → category | concerts · 24h | A- (nonprofit PAC; Broadway, symphony, ballet, comedy) | 93 |
| `clt_amos_southend` | charlotte | Rockhouse WordPress JSON-LD / `jsonld` | https://amossouthend.com/ (+ ≤ 40 event pages) | none | ≤ 41 pages/12h, 2 s apart | robots disallows only /wp-admin/ | Event name, startDate (offset), location, Etix offer url (price 0 = unknown) | concerts · 12h | B | 15 |
| `clt_comedy_zone` | charlotte | SeatEngine JSON-LD / `jsonld` | https://www.cltcomedyzone.com/ | none | 1 page/day | robots.txt rules all commented out (allows all) | Event name, startDate (UTC), location (events nested in the Place block) | events · 24h | B | 68 |
| `teamtrivia_charlotte` | charlotte | Team Trivia venue pages / `teamtrivia` | https://www.teamtrivia.com/trivia-in-charlotte/ | none | region page + ≤ 60 venue pages / 48h, 3 s apart | allowed and in the site's sitemap (gate helpers never touched) | dated games (JSON-LD), venue, geo | recurring · 48h | B | 80 |

Rejected / not used (Charlotte):

- Neighborhood Theatre, Middle C Jazz: Cloudflare "Just a moment…" 403 — not touched further.
- Hands On Charlotte (handsoncharlotte.org): legacy Salesforce HOC site; calendar page still shows 2015 — dead.
- Galaxy Digital guesses (handsoncharlotte, volunteercharlotte, sharecharlotte, unitedwaygreaterclt, uwgc,
  cltvolunteers): all "Bad Domain" (607-byte page). United Way of Greater Charlotte links no volunteer platform.
- Queens University /events/, CPCC /events: robots-disallowed. calendar.charlotte.edu is WordPress, not Localist
  (the Localist tenant is campusevents.charlotte.edu).
- boplex.com (Bojangles Coliseum / Ovens Auditorium): Next.js page, no RSS/JSON-LD (tickets via Ticketmaster).
- Visulite Theatre (no JSON-LD on show pages), Snug Harbor (WP without Tribe/LD), Evening Muse (Eventbrite — ToS),
  uptowncharlotte.com events (loaded from /_feeds/, robots-disallowed), Mint Museum / Whitewater Center (WP
  without Tribe), Charlotte Symphony (redirect loop; its concerts arrive via Blumenthal's feed anyway),
  bankofamericastadium.com/events/rss (404), Charlotte Checkers (no LD).
- Mecklenburg Park & Rec: calendar.mecknc.gov is public-meeting notices only; programs presumably in a
  registration system (not probed; manual ToS review per SCALING §2.6).
- Openings: NC has no city business license; NC ABC "Permanent Permit Notifications" (abc2.nc.gov/Permit/Subscribe)
  is an e-mail list for local officials; abc2 Search/Permit is an interactive form; city/county ArcGIS orgs have
  no license layers (Mobile Food Vendor Permit / Special Use Permits are zoning). Luma has no Charlotte page
  (luma.com/charlotte → /discover). Volo: no market. Challenge: 0 shows within 50 km.
- LN/TM/AEG venues skipped by policy: Fillmore, The Underground, PNC Music Pavilion, Skyla Amphitheatre.

### Raleigh

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `raleigh_special_events` | raleigh | ArcGIS FeatureServer `Special_Events_Next_31_Days` (org v400IkDOw1ad7Yad, owner RaleighGIS) / `arcgis` | https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Special_Events_Next_31_Days/FeatureServer/0 | none | 1 request/day | documented ArcGIS REST API; no robots policy (403); `out_fields` never requests EVENT_CONTACT/PHONE/EMAIL | event name, start date (all-day; the permit times are the street-closure window), event type, status (Cancelled dropped); private-party titles excluded | events · 24h | B+ (official, rolling 31 days; polyline routes → no location yet) | 38 |
| `ncsu_events` | raleigh | Localist / `localist` | https://calendar.ncsu.edu/api/2/events | none | ≤ 6 pages/day; robots `Crawl-Delay: 1` | allowed (disallows only HTML `?types` views) | as USC; `audience_filter: institution` | events · 24h | B+ | 232 |
| `ncsu_athletics` | raleigh | SIDEARM calendar.ics / `ics` | https://gopack.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots `Crawl-delay: 30` | `/calendar.ashx` allowed | summary, start, location (Raleigh/Reynolds only = home games) | events · 24h | A- | 20 |
| `ncma_events` | raleigh | WP The Events Calendar / `tribe` | https://ncartmuseum.org/wp-json/tribe/events/v1/events | none | ≤ 6 pages/day | REST allowed (robots: /wp-admin/ only); the HTML /events/ page serves a Cloudflare challenge, never fetched | as MPRB; rooms pinned to the museum (approximate) | events · 24h | D for us — **disabled**: HTML /events/ is a Cloudflare challenge; the same-host REST API answered (97 in one verification run) but using it reads as working around the challenge | disabled |
| `ncmns_events` | raleigh | WP The Events Calendar / `tribe` (under /calendar/) | https://www.naturalsciences.org/calendar/wp-json/tribe/events/v1/events | none | ≤ 6 pages/day | allowed | as MPRB | events · 24h | A- (state museum) | 88 |
| `lenovo_center_raleigh` | raleigh | carbonhouse events RSS / `rss_events` | https://www.lenovocenter.com/events/rss | none | 1 request/12h | robots allows all | title, ev:startdate/enddate, link; Hurricanes/NC State → sports_watch.game | concerts · 12h | A- | 71 |
| `martin_marietta_center` | raleigh | carbonhouse events RSS / `rss_events` | https://www.martinmariettacenter.com/events/rss | none | 1 request/day | robots allows all | title, start/end, ev:location (hall), ev:type (NC Symphony, Carolina Ballet, NC Opera…) | concerts · 24h | A- (city-owned complex) | 65 |
| `red_hat_amphitheater` | raleigh | carbonhouse events RSS / `rss_events` | https://www.redhatamphitheater.com/events/rss | none | 1 request/day | robots allows all; city venue site (tickets sold via Live Nation, links only) | as above | concerts · 24h | B (seasonal; 2 shows left in 2026) | 2 |
| `koka_booth_amphitheatre` | raleigh | carbonhouse events RSS / `rss_events` | https://www.boothamphitheatre.com/events/rss | none | 1 request/day | robots allows all | as above (ev:location is "…Official Site", so the venue label is clumsy) | concerts · 24h | B (seasonal, Town of Cary) | 5 |
| `lincoln_theatre_raleigh` | raleigh | Rockhouse WP Event JSON-LD / `jsonld` | https://lincolntheatre.com/ | none | ≤ 46 pages/12h, ≥ 2 s apart | robots: /wp-admin/ only | name, startDate (offset), offers/Etix link | concerts · 12h | B | 36 |
| `goodnights_comedy` | raleigh | SeatEngine Place JSON-LD ("Events" list) / `jsonld` | https://www.goodnightscomedy.com/ | none | 1 page/12h | robots.txt fully commented out (allows all) | name, startDate (UTC), location | events · 12h | B (same variant as `cap_city_comedy`) | 147 |
| `teamtrivia_raleigh` | raleigh | Team Trivia venue pages / `teamtrivia` | https://www.teamtrivia.com/trivia-in-raleigh-eastern-north-carolina/ | none | ≤ 71 pages/48h, ≥ 3 s apart | sitemap-listed pages; gate/getlocation never used | as `teamtrivia_denver`; Wilmington/Greenville venues dropped by the geofence | recurring · 48h | B | 160 |

Rejected / not used (Raleigh):

- raleighnc.gov (city events + parks calendar): Cloudflare "Just a moment…" 403 on robots.txt and /events. Not touched again.
- Wake County Public Libraries: events are plain Drupal HTML on wake.gov/events (no ICS, no JSON-LD, no platform feed). No adapter.
- Wake County restaurant permits (`maps.wake.gov/.../RestaurantInspectionsOpenData`): robots.txt `User-agent: * / Disallow: /`. The data.wake.gov hub download wasn't used, because it would serve the same blocked service from another host.
- Activate Good (activategood.org), United Way of the Greater Triangle: Cloudflare 403. Activate Good's portal volunteer.activategood.org runs on **Golden Volunteer**, which has no adapter. `activategood.galaxydigital.com` → "Galaxy Digital: Bad Domain".
- Town of Cary (carync.gov): Akamai "Access Denied", including robots.txt.
- Downtown Raleigh Alliance (downtownraleigh.org): custom CMS (ctycms) loading events by JS; no feed or JSON-LD.
- Kings (kingsraleigh.com): only Etix links, no JSON-LD. Pour House (pourhouseraleigh.com): no structured data.
- Live Nation-owned venues skipped: Coastal Credit Union Music Park at Walnut Creek, The Ritz.
- City SpecialEvents permit-application layer (`service_48a189…`): 392 rows, none in the future, and full of applicant PII columns. Not used.
- Socrata: no Raleigh/NC tenant (catalog `q=raleigh` → 0). No Volo market, no Challenge shows nearby.
- Not probed: Visit Raleigh (Simpleview, the same CDN blocks seen elsewhere), Meredith/Shaw/Wake Tech calendars, NC ABC Commission permits.

### Memphis

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `memphis_fedexforum` | memphis | carbonhouse RSS / `rss_events` | https://www.fedexforum.com/events/rss | none | 1 request/12h | robots: `User-agent: *`, no rules | title, ev:startdate (UTC), link; Grizzlies/Tigers titles → sports_watch.game | concerts · 12h | A- (official venue feed; mostly Grizzlies games) | 61 |
| `memphis_landers_center` | memphis | carbonhouse RSS / `rss_events` | https://www.landerscenter.com/events/rss | none | 1 request/12h | robots: `User-agent: *`, no rules | as FedExForum; Monarchs → sports_watch.game. Feed starts with a newline before `<?xml` (needs the safe_xml lstrip) | concerts · 12h | B+ (Southaven MS, ~20 km out) | 58 |
| `memphis_overton_park_shell` | memphis | Squarespace Event JSON-LD / `jsonld` | https://overtonparkshell.org/eventpage | none | listing + ≤25 detail pages/day, ≥2 s | Squarespace robots: `?format=`/`?view=`… query URLs disallowed (wildcards); plain event paths allowed | name, startDate/endDate with offset, location name+address | concerts · 24h | B+ (nonprofit bandshell; free concerts, fitness, pop-ups) | 19 |
| `memphis_symphony` | memphis | Squarespace Event JSON-LD / `jsonld` | https://memphissymphony.org/calendar | none | listing + ≤30 detail pages/day | as above | as above | concerts · 24h | B+ | 16 |
| `memphis_gpac` | memphis | Squarespace Event JSON-LD / `jsonld` | https://www.gpacweb.com/event-list | none | listing + ≤30 detail pages/day | as above (AI-crawler names blocked; `*` gets Squarespace defaults) | as above | concerts · 24h | B+ (Germantown) | 30 |
| `memphis_river_parks` | memphis | Squarespace Event JSON-LD / `jsonld` | https://www.memphisriverparks.org/events | none | listing + ≤30 detail pages/day | as above | as above | events · 24h | B (riverfront parks nonprofit: fitness, walks, kids' festivals) | 22 |
| `memphis_tigers_athletics` | memphis | SIDEARM ICS / `ics` | https://gotigersgo.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots Crawl-delay 30 (min_interval_s 30) | robots allows `/calendar.ashx` (disallows /common/, /services/, `*.js$`…) | SUMMARY, DTSTART, LOCATION (home = starts "Memphis") | events · 24h | A- | 29 |
| `memphis_uw_midsouth_volunteer` | memphis | Galaxy Digital / `galaxydigital` | https://uwmidsouth.galaxydigital.com/need/rss/ | none | RSS + ≤15 detail pages/day, 10 s apart (Crawl-delay 10) | robots `*`: allowed; linked from uwmidsouth.org/volunteer | need title, date/shifts, address, agency, register-by | volunteer · 24h | B (some needs in outlying counties; geofence drops those) | 15 |
| `challenge_trivia_memphis` | memphis | Challenge Entertainment JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request/48h | Yoast robots allows all; no terms page | show title, venue+geo, day/time, next_date | recurring · 48h | C (undocumented) | 84 |
| `memphis_wiseacre` | memphis | WP The Events Calendar / `tribe` | https://wiseacrebrew.com/wp-json/tribe/events/v1/events | none | ≤3 pages/day | robots disallows only /wp/wp-admin/ | title, start/end+tz, venue, cost, categories | events · 24h | B- (taproom: trivia, workouts, rides, parties; pint-night specials) | 30 |
| `memphis_meddlesome` | memphis | WP The Events Calendar / `tribe` | https://meddlesomebrewing.com/wp-json/tribe/events/v1/events | none | ≤3 pages/day | robots disallows /page/, /events/list/page/ only | as Wiseacre | events · 24h | B- (Cordova taproom: trivia, poker, songwriters, drag) | 30 |

Rejected / not used (Memphis):

- **Memphis Public Libraries** (memphislibrary.org): Cloudflare "Just a moment" 403. BiblioCommons codes `memphis` and `memphislibrary` return 404. memphislibrary.libnet.info 302s to google (no tenant). memphislibrary.libcal.com says "site no longer online".
- **City of Memphis** events (memphistn.gov/events): Cloudflare 403.
- **data.memphistn.gov:** Socrata answers "Domain not found". The city is on ArcGIS now (orgId `saWmpKJIUAjyyNVc`, 37 services). None are events, event permits, or business/beer/liquor licenses. Shelby County's hub is 911 data only. **Result: no openings source.**
- **Germantown, Collierville, Bartlett Library:** robots.txt answers 403 (Akamai), which counts as disallow-all.
- **Cannon Center:** Cloudflare challenge plus robots disallow. **Crosstown Arts:** Cloudflare 403.
- **University of Memphis /calendar:** a static OmniUpdate page with no feed. calendar.memphis.edu and events.memphis.edu timed out. libcal.memphis.edu (campus library) exists but is campus-facing, so it was skipped.
- **Rhodes College:** 25Live Publisher (Trumba) ICS `25livepub.collegenet.com/calendars/rhodes-college-calendar.ics` has 200 events, but about 75% are "Student Led". Not public-facing, so skipped. The Trumba JSON for that webname 404s on www.trumba.com.
- **Orpheum Theatre:** a nonprofit Craft CMS site. Its event JSON-LD has no startDate, so it can't be used without an HTML scraper.
- **Dixon Gallery:** Event JSON-LD exists, but it is one record per open day of an exhibition, and the times are local times mislabeled `+00:00`.
- **Hi-Tone:** tickets go through Etix, whose event pages answer 202 with an empty body (bot challenge). The Hi-Tone site itself has no event JSON-LD.
- **Other dead ends:** minglewoodhall.com is a hijacked spam domain. Chuckles Comedy is a static clone with no feed. Downtown Memphis Commission's calendar is a JS app on ctycms with no public feed. memphis901fc.com redirects to a SportsEngine template.
- **Timed out from our client:** Memphis Botanic Garden, Stax, Pink Palace.
- **Memphis Zoo:** wp-json 403, Crawl-delay 30.
- **Shelby Farms Park:** /events 404. **Graceland:** no Tribe.
- **No Team Trivia or Volo market.**

### Birmingham

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `bham_bpl_events` | birmingham | Trumba JSON / `trumba` | https://www.trumba.com/calendars/BPL-calendar.json | none | 1 request/day (startdate + 14 days, ~0.4 MB) | trumba.com robots allows all; the library's own embedded calendar (cobpl.org/calendar spud) | title, description, wall-clock start/end + offset, branch, Event Type, registration flags; staff contact fields never mapped | events · 24h | A- (official; no geo, branch names geocoded later) | 134 |
| `bham_homewood_library_events` | birmingham | Communico `eeventcaldata` / `communico` | https://homewood.libnet.info/eeventcaldata | none | 7 requests/day | **undocumented** front-end JSON; robots disallows only /results*, /sitesearch* | as MDPLS | events · 24h | B | 34 |
| `bham_hoover_library_events` | birmingham | Communico `eeventcaldata` / `communico` | https://events.hooverlibrary.org/eeventcaldata | none | 7 requests/day | as Homewood | as MDPLS (tags are verbs, so ages decide kids' events) | events · 24h | B | 24 |
| `bham_uab_events` | birmingham | Localist / `localist` | https://calendar.uab.edu/api/2/events | none | ≤ 8 pages/day; robots `Crawl-Delay: 1` | allowed (wildcard disallows cover only HTML calendar/search views) | as USC; `audience_filter: institution`; athletics + employee screenings/trainings skipped | events · 24h | B (≈680 items/30 d, mostly internal) | 245 |
| `bham_bjcc_concerts` | birmingham | WP Modern Events Calendar JSON-LD / `jsonld` | https://www.bjcc.org/contact/news/mec-category/concerts/ | none | 1 page/12h | robots (Yoast) allows all; BJCC is a public civic-center authority | name, date (clock time wrong in JSON-LD → `date_only`), location room; placeholder price 0 / validFrom ignored | concerts · 12h | B- (12 per list ≈ 2 months; dates only) | 12 |
| `bham_bjcc_comedy` | birmingham | as above | https://www.bjcc.org/contact/news/mec-category/comedy/ | none | 1 page/12h | as above | as above | events · 12h | B- | 3 |
| `bham_bjcc_performing_arts` | birmingham | as above | https://www.bjcc.org/contact/news/mec-category/performing-arts/ | none | 1 page/12h | as above | as above (Broadway in Birmingham, Alabama Ballet) | events · 12h | B- | 11 |
| `bham_bjcc_sports` | birmingham | as above | https://www.bjcc.org/contact/news/mec-category/sports/ | none | 1 page/12h | as above | as above; "… Schedule" season placeholders skipped | events · 12h | B- | 12 |
| `bham_alabama_theatre` | birmingham | WP The Events Calendar / `tribe` | https://alabamatheatre.com/wp-json/tribe/events/v1/events | none | 1 request/12h | robots has no rules | as MPRB; categories Movies/Comedy/Ballet/Concerts mapped | concerts · 12h | B+ | 32 |
| `bham_lyric_theatre` | birmingham | WP The Events Calendar / `tribe` | https://lyricbham.com/wp-json/tribe/events/v1/events | none | 1 request/12h | robots has no rules | as MPRB; Comedy/Drag/Ballet/Concert mapped | concerts · 12h | B+ | 19 |
| `bham_saturn` | birmingham | Opendate show pages JSON-LD / `jsonld` | https://www.saturnbirmingham.com/ (+ ≤ 40 /shows/ pages) | none | ≤ 41 pages/12h, ≥ 2 s apart | robots lists only the sitemap | MusicEvent name, UTC start, location, url | concerts · 12h | B | 40 |
| `bham_stardome` | birmingham | SeatEngine show pages JSON-LD / `jsonld` | https://www.stardome.com/ (+ ≤ 25 /events/ pages) | none | ≤ 26 pages/day | robots has no active rules | Event name, UTC start, url (no offers in JSON-LD) | events · 24h | B | 75 |
| `bham_uab_athletics` | birmingham | SIDEARM ICS / `ics` | https://uabsports.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots `Crawl-delay: 30` | robots disallows only assets/admin (calendar.ashx allowed) | SUMMARY, DTSTART, LOCATION (home = starts "Birmingham") | events · 24h | B+ | 20 |
| `bham_samford_athletics` | birmingham | SIDEARM ICS / `ics` | https://samfordsports.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots `Crawl-delay: 30` | as UAB | as UAB (home = "Birmingham"/"Homewood") | events · 24h | B+ | 24 |
| `challenge_trivia_birmingham` | birmingham | Challenge show-finder JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request/48h | robots allows all; no terms page | as other Challenge units; `metros: [north-alabama]` within 2× radius | recurring · 48h | C (undocumented) | 233 |
| `upcomingcons` (global) | birmingham | upcomingcons | — | none | — | — | — | conventions · 168h | — | 0 for Birmingham |
| Hands On Birmingham / United Way of Central Alabama | birmingham | — | handsonbirmingham.org, uwca.org, volunteer.handsonbirmingham.org | — | — | **Cloudflare 403 / 525** to our client 2026-10-16; not worked around | — | — | D for us | not added |
| Birmingham Botanical Gardens | birmingham | — | https://www.bbgardens.org/ | — | — | **robots.txt disallows all** | — | — | D for us | not added |
| Birmingham Museum of Art | birmingham | — | https://www.artsbma.org/ | — | — | Cloudflare "Just a moment" challenge | — | — | D for us | not added |
| City of Birmingham open data (CKAN) | birmingham | `ckan` | https://data.birminghamal.gov/ | — | robots Crawl-delay 10 | robots disallows /api/ and /datastore/*; "New Business Licenses Issued" CSVs end in 2017 | — | openings | D (dead + robots) | not added |
| BJCC "Family" list | birmingham | `jsonld` | https://www.bjcc.org/contact/news/mec-category/family/ | none | — | allowed | — | — | dropped: the Family label is applied to bowl games, orchestras and cheer meets, mislabeling events shared with the other BJCC lists | not added |

Rejected / not used (Birmingham):

- bham_bjcc_events (single "all events" list) → replaced by per-category units (forgotten in the DB).
- bham_bjcc_family → removed: BJCC tags bowl games, TSO and cheer meets as Family, so merged events got family.kids.
- Hands On Birmingham (handsonbirmingham.org 403, volunteer.handsonbirmingham.org Cloudflare 525), United Way of
  Central Alabama (uwca.org 403); Galaxy tenant `handsonbirmingham` → "Galaxy Digital: Bad Domain".
- Birmingham Botanical Gardens: robots disallows all. Birmingham Museum of Art: Cloudflare challenge.
- data.birminghamal.gov: CKAN, robots `Disallow: /api/` + `/datastore/*`; "New Business Licenses Issued" ends 2017.
  ArcGIS Hub search for "Birmingham Alabama open data": no site.
- Iron City (Ticketmaster links, Hive terms; no Event JSON-LD on detail pages), WorkPlay (Yoast graph only),
  Avondale Brewing (Squarespace page, no events JSON-LD, ?format=ical returns HTML): HTML-only, skipped.
- Birmingham Zoo (Tribe): 17 of 19 items are one daily exhibit; skipped. Railroad Park: no machine-readable calendar.
- Sloss Furnaces: TLS chain failed verification from our client (not retried with verify off).
- Samford events page: no calendar platform fingerprint.

### Oklahoma City

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `okc_paycom_center` | oklahoma_city | carbonhouse events RSS / `rss_events` | https://www.paycomcenter.com/events/rss | none | 1 request / 12 h | robots.txt `User-agent: *` with no rules; public syndication feed | title, ev:startdate/enddate (UTC), ev:location, ev:type (Sports → game, Concerts), link | concerts · 12h | A- (city-owned arena; Thunder home games + tours) | 73 |
| `okc_civic_center` | oklahoma_city | carbonhouse events RSS / `rss_events` | https://www.okcciviccenter.com/events/rss | none | 1 request/day | robots.txt has no rules | as Paycom; ev:type Orchestra/Choral/Theatre/Ballet mapped; Rose State PAC (Midwest City) room → its own address | concerts · 24h | A- (city-owned hall: Philharmonic, Broadway, ballet, opera) | 49 |
| `okc_downtown_events` | oklahoma_city | WP The Events Calendar / `tribe` | https://downtownokc.com/wp-json/tribe/events/v1/events | none | ≤ 12 pages/day at robots Crawl-delay 10 | robots allows /wp-json/ (disallows /wp-admin/ only). HTML /events/ serves a Cloudflare challenge — never fetched; the REST API is not challenged | title, description, start/end (site tz misconfigured "UTC+0", wall time read in city tz), venue+geo, categories (district), cost | events · 24h | D for us — **disabled**: HTML /events/ is a Cloudflare challenge; the same-host REST API answered (151 in one verification run) but using it reads as working around the challenge | disabled |
| `okc_science_museum` | oklahoma_city | WP The Events Calendar / `tribe` | https://www.sciencemuseumok.org/wp-json/tribe/events/v1/events?categories=events,community-events | none | ≤ 4 pages/day, Crawl-delay 10 | Yoast robots allows all | as above; "activities" (daily planetarium/live-show schedule) excluded | events · 24h | B (few special events: SMO21+, talks, teen café) | 6 |
| `okc_cowboy_museum` | oklahoma_city | WP The Events Calendar / `tribe` | https://nationalcowboymuseum.org/wp-json/tribe/events/v1/events?categories=event,annual-event,special-programs,education,adults | none | ≤ 4 pages/day | robots disallows only HTML /calendar/ views | as above; daily drop-in activity excluded by category | events · 24h | B | 9 |
| `okc_scissortail_park` | oklahoma_city | EventON listing JSON-LD / `jsonld` | https://www.scissortailpark.org/events/ | none | 1 request/day | robots disallows /wp-json/ and `/*?` — only the plain listing page is fetched | name, startDate (date-only), location | events · 24h | B- (city park foundation; current month only, date-only) | 12 |
| `okc_uco_events` | oklahoma_city | LiveWhale v2 JSON / `livewhale` | https://calendar.uco.edu/live/json/events/max/200/response_fields/location,summary,event_types,tags,group_title | none | 1 request/day | robots disallows only `*?replytocom` | title, date_iso, location, event types, group; audience_filter institution | events · 24h | B (Edmond campus; mostly arts/jazz lab) | 33 |
| `okc_uco_athletics` | oklahoma_city | SIDEARM calendar.ics / `ics` | https://bronchosports.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day (robots Crawl-delay 30) | robots `*` group allows /calendar.ashx | SUMMARY, DTSTART/END, LOCATION (only "EDMOND, …" home venues kept) | events · 24h | B+ | 19 |
| `okc_ocu_athletics` | oklahoma_city | SIDEARM calendar.ics / `ics` | https://www.ocusports.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day (Crawl-delay 30) | as above | as above; only "Oklahoma City, <campus venue>" kept | events · 24h | B+ | 15 |
| `okc_volunteer_central_ok` | oklahoma_city | Galaxy Digital / `galaxydigital` | https://www.volunteercentraloklahoma.org/need/rss/ + /need/detail/?need_id=N | none | 1 RSS + ≤ 15 detail pages/day, ≥ 3 s | robots: named SEO bots blocked, `*` empty Disallow | need title, dates/shifts, address, nonprofit, registration close | volunteer · 24h | B (United Way of Central Oklahoma; RSS = 15 newest needs) | 15 |
| `challenge_trivia_okc` | oklahoma_city | Challenge Entertainment JSON / `challenge` | https://challengeentertainment.com/wp-json/ce/v1/shows | none | 1 request / 48 h | robots allows all; no terms page | show title, day/time, next_date, venue + lat/lon (metro-oklahoma-city + metro-norman within 50 km) | recurring · 48h | C (undocumented front-end JSON) | 40 |

Rejected / not used (Oklahoma City):

| unit | valid |
|---|---|
| okc_downtown_events (tribe, Downtown OKC Partnership) | 151 |
| okc_paycom_center (rss_events) | 73 |
| okc_civic_center (rss_events, incl. Rose State PAC) | 49 |
| challenge_trivia_okc (challenge; metros oklahoma-city + norman) | 40 |
| okc_uco_events (livewhale, institution filter) | 33 |
| okc_uco_athletics (ics, home only) | 19 |
| okc_volunteer_central_ok (galaxydigital) | 15 |
| okc_ocu_athletics (ics, home only) | 15 |
| okc_scissortail_park (jsonld) | 12 |
| okc_cowboy_museum (tribe, category-filtered) | 9 |
| okc_science_museum (tribe, category-filtered) | 6 |
| upcomingcons (global) | 0 (no OKC cons listed) |

Upcoming events after build: **414** (133 in the next 14 days; 8 merged). Categories: sports_watch 99, community 88, arts 79, music 59, trivia_games 49, volunteer 15, outdoors 11, nightlife 6, family 5, fitness 2. Coordinates: ~50% before geocoding (pipeline geocodes later). robots audit: 34 URLs, 0 disallowed (RFC 9309 parser).

Fix during verification: SIDEARM ICS `location_skip` text is "venue_name address title" (venue_name = part before the comma), so the OCU regex anchors on `.*` (`'^(?!.*Oklahoma City, (?!OK\b))'`) — first run returned 0.

### Providence

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `pvd_brown_events` | providence | LiveWhale JSON / `livewhale` | https://events.brown.edu/live/json/events/type/%20Open%20to%20the%20Public/max/200/… | none | 1 request/day; server caps a response at 100 events (~2–3 days ahead) | robots disallows only `?replytocom` | title, date_iso, location+geo, event types, tags, cost; athletics/away games excluded (SIDEARM unit covers home games) | events · 24h | B (official; rolling short window) | 35 |
| `pvd_pawtucket_library_events` | providence | Springshare LibCal ICS / `ics` | https://pawtucketlibrary.libcal.com/ical_subscribe.php?src=p&cid=12088 | none | 1 request/day; robots `Crawl-delay: 10` | robots: named crawlers + `/process_` disallowed; `*` allowed | SUMMARY, DTSTART/END, room, CATEGORIES, URL; ESOL/citizenship course sessions, meetings, closings skipped by title; pinned to the library (approximate) | events · 24h | B+ (official) | 50 |
| `pvd_east_providence_library_events` | providence | LibCal ICS / `ics` | https://eplib.libcal.com/ical_subscribe.php?src=p&cid=20146 | none | 1 request/day; Crawl-delay 10 | as above | as above; branch in LOCATION; fallback Weaver Library (approximate) | events · 24h | B+ | 103 |
| `pvd_cranston_library_events` | providence | LibCal ICS / `ics` | https://events.cranstonlibrary.org/ical_subscribe.php?src=p&cid=15394 | none | 1 request/day; Crawl-delay 10 | as above | as above; "Sunday Hours"/closings skipped; fallback Central Library (approximate) | events · 24h | B+ | 105 |
| `pvd_serve_ri_volunteer` | providence | Galaxy Digital / `galaxydigital` | https://serverhodeisland.galaxydigital.com/need/rss/ + detail pages | none | ≤ 16 requests/day, ≥ 3 s apart | galaxydigital robots: named SEO bots only | as `handson_twin_cities` (RSS title "Needs on United Way of Rhode Island") | volunteer · 24h | B (statewide needs; RSS = 15 newest) | 25 |
| `pvd_amica_mutual_pavilion` | providence | carbonhouse RSS / `rss_events` | https://www.amicamutualpavilion.com/events/rss | none | 2 requests/day | robots: empty `User-agent: *` | title, ev:startdate (UTC), link | concerts · 12h | A- (arena: Friars, P-Bruins, concerts) | 35 |
| `pvd_ppac` | providence | carbonhouse RSS / `rss_events` | https://www.ppacri.org/events/rss | none | 2 requests/day | robots: empty | as above | concerts · 12h | A- | 25 |
| `pvd_ri_convention_center` | providence | carbonhouse RSS / `rss_events` | https://www.riconvention.com/events/rss | none | 1 request/day | robots: empty | as above (Rhode Island Comic Con, home show, expos) | conventions · 24h | B+ | 5 |
| `pvd_fete_music_hall` | providence | Squarespace Event JSON-LD / `jsonld` | https://www.fetemusic.com/all-shows (+ ≤ 40 show pages) | none | ≤ 41 requests/run, ≥ 2 s apart | Squarespace robots: `?format=`/`?tag=`… query variants disallowed (wildcards; `follow` never requests a query string) | name, startDate/endDate with offset, location | concerts · 12h | B (independent venue; no prices in LD) | 23 |
| `pvd_as220` | providence | Squarespace Event JSON-LD / `jsonld` | https://as220.org/calendar (+ ≤ 30 pages) | none | ≤ 31 requests/run | as Fete | as Fete | concerts · 12h | B | 30 |
| `pvd_the_met` | providence | Rockhouse WP Event JSON-LD / `jsonld` | https://themetri.com/ (+ ≤ 40 event pages) | none | ≤ 41 requests/run | robots: only /wp-admin/ | name, startDate, Etix offer link | concerts · 12h | B | 22 |
| `pvd_comedy_connection` | providence | ComedyEvent JSON-LD / `jsonld` | https://www.ricomedyconnection.com/ (+ ≤ 30 show pages) | none | ≤ 31 requests/run | robots: `User-Agent: *` with Content-Signal search/ai allowed, nothing disallowed | name, startDate per show time, offer price | events · 12h | B+ (prices published) | 23 |
| `pvd_brown_athletics` | providence | SIDEARM ICS / `ics` | https://brownbears.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots `Crawl-delay: 30` | `/calendar*` allowed | SUMMARY, DTSTART, LOCATION ("Providence, R.I., <facility>" only) | events · 24h | A- | 58 |
| `pvd_friars_athletics` | providence | SIDEARM ICS / `ics` | https://friars.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; Crawl-delay 30 | as above | as above | events · 24h | A- (some home games also in the Amica feed; only 2 merged) | 39 |
| `upcomingcons` (global) | providence | upcomingcons | https://www.upcomingcons.com/ | none | weekly | see global table | — | conventions · 168h | B | 1 (RI Anime Con) |

Rejected / not used (Providence):

- data.providenceri.gov Socrata: Special Events `rv3y-tq8q` and Active Business Licenses `ui7z-kv69` last updated 2021 (catalog `data_updated_at`); Monthly Entertainment Licenses `2f79-9nkc` 2020. Dead. No RI state Socrata tenant; ArcGIS Online search (owner PVD_DPWGIS, URIEDC_RIGIS) found no license/event layers.
- Providence Public Library (provlib.org): robots.txt → HTTP 403 (= disallow all).
- Community Libraries of Providence (clpvd.org, The Events Calendar, 1,655 events!): robots.txt `Disallow: /wp-json/` for `*`. **One probe request was sent before this was noticed** because Python's RobotFileParser ends the `*` group at the blank line after `Crawl-delay: 5` and so reported "allowed" (see "PoliteClient bug" below). Not used.
- City of Providence calendar (providenceri.gov, Tribe): robots disallows `/events/` and `/*?*` (every query string) → the Tribe API can't be called as the adapter needs.
- downtownprovidence.com, unitedwayri.org, provath.org (Athenaeum): Cloudflare "Just a moment" challenge. risd.edu: robots 403.
- The Strand (Rockhouse WP): event pages carry no Event JSON-LD. Trinity Rep Tribe API: total 0. WaterFire: EventOn plugin (no adapter). Columbus Theatre: expired TLS certificate + connection reset. JWU LiveWhale: student-life items, mixes the Charlotte campus.
- pclib.libcal.com (linked from pclib.org) is **Poplar Creek Public Library (IL)** — name collision, not Providence.
- Galaxy tenants `uwri`, `unitedwayri`, `serveri`, `volunteerri` → "Bad Domain".
- Lupo's / Live Nation-ticketed rooms: not probed (ToS denylist).

### Hartford

| id | city | platform / adapter | URL | auth | rate limits | robots / ToS | fields we use | data_type · cadence | grade | verified |
|---|---|---|---|---|---|---|---|---|---|---|
| `hfd_public_library_events` | hartford | Communico `eeventcaldata` / `communico` | https://hplct.libnet.info/eeventcaldata | none | 14 requests/day (one per day of horizon, ~85 KB each) | **undocumented** front-end JSON (linked from hplct.org); robots disallows only /results*, /sitesearch* | title, description, local start/end, branch, room, tags, ages, registration; staff contact never mapped | events · 24h | B (official library data via an undocumented endpoint) | 244 |
| `hfd_trinity_arts_events` | hartford | LiveWhale JSON / `livewhale` (`/group/Cinestudio\|Austin Arts Center/`) | https://events.trincoll.edu/live/json/events/group/Cinestudio%7CAustin%20Arts%20Center/max/200 | none | 1 request/day | robots disallows only `*?replytocom` | title, date_iso, location, event types, cost, group | events · 24h | B (official; group filter keeps the public cinema + arts center, drops student-club items) | 26 (1 rejected: end before start in source) |
| `hfd_ct_museum_history` | hartford | WP The Events Calendar / `tribe` | https://chs.org/wp-json/tribe/events/v1/events | none | ≤ 3 pages/day; robots Crawl-delay 10 | REST allowed (`Disallow:` empty) | as MPRB | events · 24h | B+ (Connecticut Museum of Culture and History, staff-edited) | 29 |
| `hfd_mark_twain_house` | hartford | WP The Events Calendar / `tribe` | https://marktwainhouse.org/wp-json/tribe/events/v1/events | none | ≤ 2 pages/day | REST allowed (robots blocks only HTML `/events/…` permutations and `?tribe*` query views) | as MPRB | events · 24h | B | 15 |
| `hfd_bushnell` | hartford | carbonhouse events RSS / `rss_events` | https://www.bushnell.org/events/rss | none | 1 request / 12 h | `User-agent: *` with no disallows | title, ev:startdate/enddate, ev:location (hall), ev:type, link | concerts · 12h | A- (nonprofit performing-arts center; also the Hartford Symphony's home) | 44 |
| `hfd_peoplesbank_arena` | hartford | carbonhouse events RSS / `rss_events` | https://www.peoplesbankarena.com/events/rss | none | 1 request / 12 h | `User-agent: *` with no disallows | as Bushnell | events · 12h | A- (arena's own feed: UConn basketball/hockey, Hartford Wolf Pack, tours) | 63 |
| `hfd_comedy_craft_beer` | hartford | schema.org JSON-LD / `jsonld` | https://www.comedycraftbeer.com/calendar | none | 1 request/day; robots Crawl-Delay 3 (we use 5) | `User-agent: *` Allow: / | ComedyEvent name, startDate, location+address, offers | events · 24h | C (promoter page; statewide rooms, only Hartford-area addresses kept) | 5 |
| `hfd_trinity_bantams` | hartford | SIDEARM calendar.ics / `ics` | https://bantamsports.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; robots Crawl-delay 30 | no rule on /calendar* | SUMMARY, DTSTART, LOCATION (home = starts with "Hartford") | events · 24h | B+ | 31 |
| `hfd_hartford_hawks` | hartford | SIDEARM calendar.ics / `ics` | https://hartfordhawks.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day; Crawl-delay 30 | as above | as above (home = "West Hartford") | events · 24h | B+ | 21 |
| `hfd_uconn_football_east_hartford` | hartford | SIDEARM calendar.ics / `ics` | https://uconnhuskies.com/calendar.ashx/calendar.ics?sport_id=0 | none | 1 request/day | as above | as above (kept: "East Hartford" = Pratt & Whitney Stadium; arena games come from the arena feed, Storrs is out of radius) | events · 24h | B+ (seasonal) | 4 |
| `hfd_ct_liquor_openings` | hartford | Socrata `ngch-56tr` (data.ct.gov) / `socrata` | https://data.ct.gov/d/ngch-56tr | none (optional app token) | Socrata throttling | CT Open Data ToU | credentialid, businessname (legal entity; org-looking names only), credential class, status, **issuedate** (first issue; renewals change effectivedate), address, city | openings · 24h | A- (state DCP register; no DBA, so titles are LLC names) | 6 |
| `hfd_wethersfield_library_events` | hartford | LibCal ICS / `ics` | https://wethersfieldlibrary.libcal.com/ical_subscribe.php?src=p&cid=15232 | none | Crawl-delay 10 | robots allows (`*`: Crawl-delay 10, /process_ only) | — | events · 24h | D for us (disabled: 39/46 items are "LIBRARY CLOSED", the talks are virtual with no LOCATION) | disabled |

Rejected (Hartford):

| Source | City | Why it isn't used | Evidence |
|---|---|---|---|
| CT Liquor Permits `gwv2-eswx` | Hartford | no newness date: `effective_date` is a renewal-cycle text date, pending new applications are undated | Socrata probe 2026-10-16 |
| Hartford food establishment licenses (ArcGIS `HartfordOpenDataTables/FeatureServer/2`) | Hartford | no date column (snapshot-diff only) | layer metadata 2026-10-16 |
| hartford.com (Hartford Business Improvement District events), riverfront.org, handsonhartford.org | Hartford | Cloudflare "Just a moment…" challenge | probe 2026-10-16 |
| West Hartford Public Library, Windsor Public Library (LibraryMarket / librarycalendar.com) | Hartford | robots.txt answers 403 → treated as disallow-all | `*.librarymarket.com/robots.txt`, `*.librarycalendar.com/robots.txt` |
| ctconventions.com (CT Convention Center) | Hartford | robots.txt 403 | probe 2026-10-16 |
| Glastonbury library page, Elizabeth Park, Hill-Stead, Hartford Marathon (`/wp-json/`) | Hartford | robots disallows the path | probe 2026-10-16 |
| University of Hartford Trumba `Uhart-Home-Page-Public-Calendar` | Hartford | 410 Gone (spud still on hartford.edu/calendar) | trumba.com 2026-10-16 |
| United Way of Central & Northeastern CT volunteering | Hartford | e-CImpact login portal only; no Galaxy/HandsOn tenant (`uwcnct` → "Bad Domain") | unitedwayinc.org 2026-10-16 |
| Infinity Music Hall, Hartford Stage, Hartford Symphony, Real Art Ways, TheaterWorks | Hartford | no Event JSON-LD / no Tribe REST / no ICS | probe 2026-10-16 |
| Sea Tea Comedy | Hartford | tickets on Eventbrite (excluded platform) | homepage |
| hartfordct.gov events | Hartford | events listing is empty (data-total-results="0") | homepage |
