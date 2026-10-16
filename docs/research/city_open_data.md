# City open data and keyless event feeds: research notes

**Date verified:** 2026-10-15 (local), all URLs below were curl-tested that day with
`User-Agent: GetOffTheCouch-research/0.1 (contact: spanglew@amazon.com)`.
**Scope:** keyless (or free optional token) machine-readable feeds for the 10 seed cities:
events, permits, block parties and street fairs, farmers markets, library and university calendars,
plus "new bar/restaurant opening" proxies from liquor and business-license data.
**Fixtures:** one real response per source, trimmed to 5 records or fewer, in `docs/research/samples/`.
They are unmodified apart from trimming. The exceptions are noted per source: Trumba and Communico JSON
were re-serialized with indentation after list slicing, and the FL CSVs were re-quoted with UTF-8 output.

> Other research agents also write into `samples/` (leagues, volunteering, ticketing, cons).
> This document covers only the files listed here.

---

## 1. TL;DR: best sources per city

| City | Best events source | Best "openings" proxy | Other good sources |
|---|---|---|---|
| **Minneapolis** | MPRB parks (WP Tribe REST); Hennepin County Library (BiblioCommons RSS); Mpls Downtown Council (WP Tribe REST, 1,489 upcoming) | Minneapolis On-Sale Liquor (ArcGIS) | UMN LiveWhale JSON + ICS |
| **NYC** | NYC Permitted Events `tvpp-9vvx` (block parties, street fairs, parades); NYC Parks Upcoming 14 Days `w3wp-dpdi` | NY SLA **Pending** licenses `f8i8-k2gm` (pre-opening); SLA Active `9s3h-dpkz` | NYC Farmers Markets `8vwk-6iz2`; NYU LiveWhale; Parks Public Programs attendance history `6v4b-5gp4` |
| **Chicago** | Chicago Park District Activities `tn7v-6rnw`; CPL Events `vsdy-d8k7` | Chicago Business Licenses `r5kz-chrr` (`application_type='ISSUE'`) | Park District Outdoor Event Permits `pk66-w54g`; CPL BiblioCommons RSS |
| **Boston** | Meet Boston (Simpleview, 318 events/wk); Downtown Boston BID (Tribe, 771 upcoming); BPL BiblioCommons RSS | Boston Food Establishment Licenses (CKAN) | Boston Special Event License Apps, One-Day Alcohol, One-Time Entertainment (CKAN SQL); Northeastern Localist |
| **Austin** | Visit Austin (Simpleview, 266 events/wk); Austin Convention Center / Palmer events `p9ma-z6y9` | TABC Pending Original Applications `mxm5-tdpj` + TABC License Info `7hf9-qc9f` | UT Austin Localist; ACE permits `teth-r7k8` (history only) |
| **Denver** | Visit Denver (Simpleview, 510 events/wk) | Denver Pending Business Licenses (ArcGIS); Denver Liquor Licenses (ArcGIS); CO Recently Approved Liquor `htyp-tqzh` | DPL LibCal exists but **robots disallows all** |
| **Seattle** | Seattle Public Library (Trumba JSON); UW (Trumba JSON) | Seattle Active Business License `wnbq-64tb` (future `license_start_date`) | WA LCB Local Authority Letters `vgcw-qfjm` (thin); Downtown Seattle Assoc (Tribe, small) |
| **Nashville** | Vanderbilt LiveWhale JSON | Nashville Beer Permits (ArcGIS, includes "Special Events" temp permits) | Visit Music City, NPL and Metro Parks are behind Cloudflare (403) |
| **Miami** | Miami-Dade Public Library (Communico JSON, 133 events/day) | FL DBPR ABT `daily.csv` (daily statewide transactions, Dade rows) | FL DBPR temporary event alcohol permits `bd4002lic.csv` (festival names + dates); FIU Localist |
| **Los Angeles** | USC Localist | LA Active Businesses `6rrh-rzua` (NAICS 7224/7225, future start dates) | LADBS Temporary Special Event permits `8spw-3fhx` (thin); CA ABC "New Applications" (HTML only) |

**Strongest cities:** Chicago, NYC, Boston (rich, fresh, well-structured open data).
**Weakest cities:** LA (the city events dataset is dead, LAPL and LA Parks have no feed) and Nashville (Cloudflare on most civic sites).

---

## 2. Reusable platform adapters (build these once, use them in many cities)

Most of the value comes from a handful of platforms. One adapter per platform covers many cities.

| Platform | Endpoint pattern | Paging / date filter | Instances verified |
|---|---|---|---|
| **Socrata SODA** | `https://{domain}/resource/{id}.json?$where=...&$order=...&$limit=` | `$where` SoQL, `$offset`; metadata at `/api/views/{id}.json` (`rowsUpdatedAt`) | NYC, NYS, Chicago, Seattle, Austin, TX, WA, CO, LA |
| **ArcGIS FeatureServer** | `{service}/FeatureServer/{layer}/query?where=...&outFields=*&orderByFields=...&resultRecordCount=&f=geojson` | `where=field >= DATE 'YYYY-MM-DD'`, `resultOffset`; `exceededTransferLimit` flag | Minneapolis, Denver, Nashville |
| **CKAN datastore** | `https://data.boston.gov/api/3/action/datastore_search_sql?sql=...` | SQL `WHERE/ORDER/LIMIT`; all columns are `text`, so compare ISO strings | Boston |
| **BiblioCommons Events RSS** | `https://gateway.bibliocommons.com/v2/libraries/{lib}/rss/events?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&page=N` | 25 items/page; `bc:` namespace has local+UTC times, geo, capacity, registrations | `hclib` (Hennepin/Minneapolis), `chipublib`, `bpl` (Boston) |
| **WP "The Events Calendar" REST** | `https://{site}/wp-json/tribe/events/v1/events?start_date=YYYY-MM-DD&end_date=...&per_page=N&page=` | `total`, `total_pages`, `next_rest_url` | minneapolisparks.org, mplsdowntown.com, downtownboston.org, downtownseattle.org |
| **Localist** | `https://{host}/api/2/events?start=YYYY-MM-DD&end=YYYY-MM-DD&pp=N&page=` | `page.total`; `event_instances[].start`; has `num_attending`, `detail_views` | calendar.utexas.edu, calendar.northeastern.edu, calendar.usc.edu, calendar.mit.edu, calendar.fiu.edu |
| **LiveWhale** | `https://{host}/live/json/events/start_date/YYYY-MM-DD/end_date/YYYY-MM-DD/max/N/` (+ `/live/ical/events/...`) | Path-segment filters. Newer installs (NYU) return `{meta,data}` and need `/response_fields/location,description,...` | events.tc.umn.edu, events.vanderbilt.edu, events.nyu.edu, events.uchicago.edu |
| **Trumba** | `https://www.trumba.com/calendars/{webname}.json?startdate=YYYYMMDD&days=N` (also `.ics`, `.rss`) | `startdate`+`days`; whole calendar if unfiltered (1.2 MB) | `kalendaro` (Seattle Public Library), `sea_campus` (UW Seattle) |
| **Communico** | `https://{library-host}/eeventcaldata?event_type=0&req={"private":false,"date":"YYYY-MM-DD","days":N,"locations":[],"ages":[],"types":[]}` | `date`+`days` | www.mdpls.org (Miami-Dade) |
| **Simpleview CVB** | token: `GET https://{cvb}/plugins/core/get_simple_token/`, then `GET /includes/rest_v2/plugins_events_events_by_date/find/?json={filter,options}&token=` | Mongo-style JSON `date_range`, `limit`, `skip`, `count:true` | visitdenver.com, austintexas.org, meetboston.com |

Notes that apply to every platform:
- **Socrata keyless works but gets throttled.** We hit intermittent `503 service-unavailable` on NYC, Chicago and Austin, on both heavy and trivial queries, and once a `500 internal-error` on Chicago `xgse-8eg7`. Mitigations: register a **free Socrata app token** (`X-App-Token` header; it's optional and raises the throttling ceiling), use exponential backoff with retry, keep `$limit` modest, and use an explicit `$select` list. NYC `w3wp-dpdi` returned 503 for `SELECT *` but 200 with an explicit column list.
- **Socrata `rowsUpdatedAt`** (from `/api/views/{id}.json`) is a cheap staleness probe for HEALTH.md checks.
- **ArcGIS:** `editingInfo.lastEditDate` on the layer JSON is the staleness probe. Dates are epoch milliseconds. Some layers have `geometry:null` with State Plane `X_COORD/Y_COORD` (Denver), so you need to reproject or geocode them.

---

## 3. Per-city detail

Reliability guess scale: **A** = official, documented, fresh daily; **B** = official but thin, quirky, or weekly; **C** = undocumented front-end API or scrape (works today, may change without notice); **D** = dead or blocked.

### 3.1 Minneapolis (vertical-slice candidate)

#### MN-1 Minneapolis Park & Recreation Board events (WP Tribe REST): **A-/B+**
- **URL:** `https://www.minneapolisparks.org/wp-json/tribe/events/v1/events?start_date=2026-10-16&end_date=2026-10-31&per_page=5`
- **Auth:** none. **robots.txt:** `/wp-json/` is not disallowed. The file explicitly asks crawlers to avoid calendar *query-string permutations* on HTML pages (`tribe-bar-date`, `eventDisplay`, `ical=`), because they caused backend load. Keep to the REST API, at most one paged pull a day, `per_page<=50`.
- **Fields:** `id, title, description, excerpt, url, start_date, end_date, utc_start_date, utc_end_date, timezone, all_day, cost, cost_details, website, categories[].name, tags, venue{venue,address,city,zip,geo_lat,geo_lng}, organizer, image, is_virtual, modified`
- **Filter:** `start_date` / `end_date` params. Categories endpoint `/wp-json/tribe/events/v1/categories` lists: Environmental Volunteer Opportunities (302), Events- All (438), Events- MPRB (366), Events- Non-MPRB (74), Music & Movies in the Parks (139), Music in the Parks (106), Movies in the Parks (33), Pop-Up Park (13), Public Meetings (38). Filter out Public Meetings. Volunteer events map to the volunteering vertical.
- **Volume:** 33 events for Oct 16-31 (off-season). **Cadence:** edited by staff continuously; refresh daily.
- **Sample:** `samples/mprb_tribe_events.json`

#### MN-2 Hennepin County Library events (BiblioCommons RSS): **A-**
- **URL:** `https://gateway.bibliocommons.com/v2/libraries/hclib/rss/events?startDate=2026-10-17&endDate=2026-10-18` (`&page=2` etc.)
- **Auth:** none. This is the published RSS feed linked from `hclib.bibliocommons.com/v2/events`. `hclib.bibliocommons.com/robots.txt` sets `Crawl-delay: 120` and allows `/*`. The gateway host has no robots.txt (404).
- **Fields (RSS + `bc:` namespace):** `title, description(html), link, guid, category[]` (types, audiences, languages), `enclosure` (image), `bc:start_date` (UTC), `bc:start_date_local`, `bc:end_date`, `bc:end_date_local`, `bc:is_cancelled`, `bc:is_featured`, `bc:is_virtual`, `bc:location{id,name,number,street,city,zip,state,latitude,longitude}`, `bc:registration_info{is_required,is_full,capacity,number_registered}`
- **Attendance signal:** `capacity` and `number_registered` are a real RSVP-based attendance input.
- **Filter:** `startDate`/`endDate` work on the RSS endpoint only. The JSON gateway `/v2/libraries/hclib/events` ignores date params and is undocumented, so avoid it. 25 items/page. Note that hclib covers all of Hennepin County (e.g., Maple Plain), so filter by `bc:city`/lat-lng if you need the city proper.
- **Volume:** about 1,700 upcoming. **Cadence:** refresh daily.
- **Sample:** `samples/hclib_bibliocommons_events.rss.xml`

#### MN-3 Minneapolis Downtown Council events (WP Tribe REST): **B+**
- **URL:** `https://www.mplsdowntown.com/wp-json/tribe/events/v1/events?start_date=2026-10-16&per_page=5`
- **Auth:** none. robots disallows only HTML Tribe permutations (`*post_type=tribe_events*`, `*eventDate=*`, etc.). The REST API is not disallowed.
- **Fields:** same Tribe schema as MN-1. **Volume:** `total: 1489` upcoming, including trivia nights, theatre, concerts and taproom events. This is a great "niche stuff" feed.
- **Sample:** `samples/mpls_downtown_council_tribe_events.json`

#### MN-4 University of Minnesota Twin Cities (LiveWhale JSON + iCal): **A-**
- **JSON:** `https://events.tc.umn.edu/live/json/events/start_date/2026-10-16/end_date/2026-10-31/max/5/`
- **ICS:** `https://events.tc.umn.edu/live/ical/events/max/5/`
- **Auth:** none. robots: only `Disallow: *?replytocom`.
- **Fields:** `id, gid, group_title, title, url, date_iso, date2_iso, date_utc, timezone, is_all_day, repeats, is_canceled, is_online, online_url, description, cost, location, location_title, location_latitude, location_longitude, has_registration, registration_limit, rsvp_total, rsvp_waitlist_total, event_types, event_types_audience, tags, thumbnail, last_modified`
- **Filter:** path segments `start_date/…/end_date/…/max/N`. Also supports `/group/<name>/`, `/tag/<tag>/`, `/type/<type>/`. Includes the Arboretum (Chaska), so filter by lat/lng.
- **Samples:** `samples/umn_livewhale_events.json`, `samples/umn_livewhale_events.ics` (useful as the canonical ICS fixture)

#### MN-5 Minneapolis On-Sale Liquor licenses (ArcGIS): **B** (openings proxy)
- **URL:** `https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/On_Sale_Liquor/FeatureServer/0/query?where=issueDate%20%3E%3D%20DATE%20%272026-06-01%27&outFields=*&orderByFields=issueDate%20DESC&resultRecordCount=5&f=geojson`
- **Auth:** none. **Fields:** `licenseNumber, licenseType (BLLiquor|BLWine|BLBeer|BLBrewery|BLDistill), licenseStatus, liquorType, issueDate, expirationDate, licenseName, address, endorsements, ward, neighborhood, lat, long, lastUpdateDate`
- **Caveat:** `issueDate` is the *latest* issuance (renewals included: the Sheraton showed up as "recent"). There is no original-issue date. **Detect openings by diffing `licenseNumber` across daily snapshots**: a new number is a new place. Only 654 rows, so pull the full set daily.
- **Cadence:** layer `lastEditDate` = 2026-09-25 (looks weekly to monthly). The companion `Off_Sale_Liquor` layer is also available. Also on the hub: `Food_Inspections` (updated 2026-10-02).
- **Sample:** `samples/minneapolis_on_sale_liquor.geojson`

**Minneapolis failures/gaps:** The Minneapolis hub (`opendata.minneapolismn.gov`) has **no special-event-permit, block-party or farmers-market dataset**. `minneapolismn.gov` has no robots.txt, and its events URL returned 404. Meet Minneapolis (`minneapolis.org`, Craft CMS) has HTML only. Its JSON-LD on detail pages lacks dates, so it's low value (robots allows all). Walker Art Center disables WP feeds. First Avenue and Mill City Farmers Market have no Tribe API. artsmia returned 429. Explore Minnesota is behind Cloudflare.

### 3.2 New York City (vertical-slice candidate)

#### NYC-1 NYC Permitted Event Information `tvpp-9vvx` (Socrata): **A**
- **URL (fun event types, future):** `https://data.cityofnewyork.us/resource/tvpp-9vvx.json?$where=start_date_time%3E%272026-10-15%27%20AND%20event_type%20in(%27Block%20Party%27,%27Street%20Event%27,%27Parade%27,%27Single%20Block%20Festival%27,%27Plaza%20Event%27,%27Open%20Street%20Partner%20Event%27)&$order=start_date_time&$limit=5`
- **Auth:** none (free app token recommended). **Rate:** Socrata throttling. ToS: NYC Open Data Terms of Use (attribution, no warranty).
- **Fields:** `event_id, event_name, start_date_time, end_date_time, event_agency, event_type, event_borough, event_location, event_street_side, street_closure_type, community_board, police_precinct, cemsid`
- **event_type counts for future rows (as of 2026-10-15):** Sport - Youth 19,329 · Sport - Adult 4,352 · Special Event 2,820 · Street Event 208 · Farmers Market 164 · Production Event 58 · Parade 49 · Sidewalk Sale 47 · Open Street Partner Event 47 · Plaza Partner Event 42 · Block Party 33 · Plaza Event 23 · Religious Event 18 · Athletic Race / Tour 8 · Single Block Festival 3 · Health Fair 1.
- **Data quality:** many "Special Event" rows are private (weddings, "closed", lawn closures, "contract work"), so you need a title denylist or classifier. "Sport - Adult" is a **beer-league signal** (park field permits). Times are local (no TZ suffix, America/New_York). Data goes out to 2027.
- **Cadence:** `rowsUpdatedAt` = 2026-10-15 (daily). Historical companion: `bkfu-528j`.
- **Sample:** `samples/nyc_permitted_events.json`

#### NYC-2 NYC Parks Public Events, Upcoming 14 Days `w3wp-dpdi` (Socrata): **A-**
- **URL:** `https://data.cityofnewyork.us/resource/w3wp-dpdi.json?$select=title,instructor,guid,link,description,registration_url,registration_description,parkids,parknames,starttime,endtime,contact_phone,location,categories,coordinates,image&$where=starttime%3E%3D%272026-10-17T00:00:00%27&$order=starttime&$limit=5`
- **Auth:** none. **Important:** use an explicit `$select`. `$limit=3` with no select returned 503 repeatedly, while the explicit select returned 200 (a later bare request also succeeded, so it's intermittent).
- **Fields:** `title (HTML entities), instructor, guid, link{url}, description (HTML), registration_url{url}, registration_description, parkids, parknames, starttime, endtime, contact_phone, location, categories ("A | B | C"), coordinates ("lat, lng" string), image{url}`
- **Volume:** 869 rows (a rolling 14-day window). **Cadence:** daily.
- **Why this and not nycgovparks.org:** the same data is at `https://www.nycgovparks.org/xml/events_300_rss.json`, but **nycgovparks.org robots.txt disallows `/xml/` and `/*xml` for `User-agent: *`**. Use the Open Data mirror. The old "NYC Parks Events Listing" datasets (`fudw-fgrp`, `cpcm-i88g`, `xtsw-fqvh`, etc.) are **dead**: last row is 2019-12-28 and they were last updated 2021.
- **Sample:** `samples/nyc_parks_events_14d.json`

#### NYC-3 NY State Liquor Authority Pending Licenses `f8i8-k2gm` (data.ny.gov): **A** (best "opening soon" proxy found anywhere)
- **URL:** `https://data.ny.gov/resource/f8i8-k2gm.json?$where=received_date%20IS%20NOT%20NULL%20AND%20premises_county%20in(%27New%20York%27,%27Kings%27,%27Queens%27,%27Bronx%27,%27Richmond%27)%20AND%20description%20in(%27Restaurant%27,%27Food%20%26%20Beverage%20Business%27,%27Cabaret%27,%27Club%27)&$order=received_date%20DESC&$limit=5`
- **Fields:** `application_id, premises_county (Title Case!), type, class, description, legalname, dba, actual_address_of_premises, additional_address_information, city, state_name, zip_code, received_date, status (Under Review | IntakeComplete | Conditionally Approved | Reconsideration), aka_address, georeference{Point}`
- **Description counts:** Restaurant 1,157 · Grocery 810 · Food & Beverage Business 456 · Liquor Store 165 · Catering 71 · Hotel 45 · Summer Restaurant 15 · Cabaret 11 · Club 11 · Farm Brewer 9.
- **Use:** "Coming soon: Ronnie Scott's Jazz Club, 250 Mercer St (Under Review)". A status change to Conditionally Approved, followed by the record appearing in the Active list, gives an "opening" timeline. 33 of 2,915 rows have null `received_date`.
- **Cadence:** `rowsUpdatedAt` 2026-10-16 (daily). Gotcha: county values are Title Case (`'Kings'`, not `'KINGS'`).
- **Sample:** `samples/nys_sla_pending_licenses.json`

#### NYC-4 NY SLA Current Active Licenses `9s3h-dpkz`: **A**
- **URL:** `https://data.ny.gov/resource/9s3h-dpkz.json?$where=premisescounty%20in(%27New%20York%27,%27Kings%27,%27Queens%27,%27Bronx%27,%27Richmond%27)%20AND%20originalissuedate%3E%3D%272026-09-15%27%20AND%20description%20in(%27Restaurant%27,%27Food%20%26%20Beverage%20Business%27,%27Cabaret%27,%27Club%27,%27Tavern%27)&$order=originalissuedate%20DESC&$limit=5`
- **Fields:** `licensepermitid, premisescounty, type, class, description, legalname, dba, actualaddressofpremises, city, zipcode, originalissuedate, lastissuedate, effectivedate, expirationdate, georeference`. Use **`originalissuedate`** (true first issuance, unlike Minneapolis). `effectivedate` is often about 2 weeks later, which approximates the opening date.
- Also `6dg3-2z7i` (Inactive), which gives closures.
- **Sample:** `samples/nys_sla_active_licenses.json`

#### NYC-5 NYC Farmers Markets `8vwk-6iz2`: **B+**
- **URL:** `https://data.cityofnewyork.us/resource/8vwk-6iz2.json?$where=year=%272026%27&$limit=5`
- **Fields:** `year, marketname, borough, streetaddress, community_district, latitude, longitude, daysoperation, hoursoperations, season_begin, accepts_ebt, open_year_round, nyc_dept_of_health_cooking`. These are recurring-schedule rows, so generate occurrences from `daysoperation` + `hoursoperations` + season.
- 103 markets for 2026. **Cadence:** yearly-ish (updated 2026-07-15).
- **Sample:** `samples/nyc_farmers_markets.json`

#### NYC-6 NYC Parks Public Programs Special Events `6v4b-5gp4` (history with **attendance**): **B** (enrichment, not a live feed)
- **URL:** `https://data.cityofnewyork.us/resource/6v4b-5gp4.json?$where=date_and_time%3E%272026-08-01%27&$order=date_and_time%20DESC&$limit=5`
- **Fields:** `unit, group_name_partner, date_and_time, borough, locationtype, location, event_name, event_type, category, classification, attendance, audience, source`
- 23,068 rows from 2002-06 to 2026-08-16. Past events with **counted attendance**, which makes it training data for the attendance-estimation model (e.g., "Movies Under the Stars").
- **Sample:** `samples/nyc_parks_public_programs_special_events_attendance.json`

#### NYC-7 NYU events (LiveWhale v2 JSON): **B-**
- **URL:** `https://events.nyu.edu/live/json/events/start_date/2026-10-16/end_date/2026-10-31/max/5/response_fields/location,description,event_types,tags,registration,group_title,image`
- Newer LiveWhale shape: `{meta:{total_results,per_page,page,total_pages,supported_fields}, data:[...]}`. Mostly student/internal, so filter `event_types` contains "Open to the Public".
- **Sample:** `samples/nyu_livewhale_events.json`

**NYC failures/gaps:** NYPL is not on BiblioCommons Events (403 "Events feature is not available"). Brooklyn Public Library redirects to a custom `discover.bklynlibrary.org`, and Queens Library has no obvious feed (not pursued). Columbia Localist is behind Cloudflare (403). NYC DCWP Issued Licenses `w7w3-xahh` was last updated 2026-08-20 (stale-ish, not sampled). NYC Tourism has no Simpleview API.

### 3.3 Chicago

#### CHI-1 Chicago Park District Activities `tn7v-6rnw`: **A**
- **URL:** `https://data.cityofchicago.org/resource/tn7v-6rnw.json?$where=type=%27Event%27%20AND%20start_date%3E%3D%272026-10-16T00:00:00%27&$order=start_date&$limit=5`
- **Fields:** `activity_id, type (Event|Program), title, description, start_date, end_date, date_notes, season, zone, location_facility, location_notes, age_range, activity_type, category, fee, image_link, movie_rating, movie_title, restrictions, information_link, registration_link, registration_date, event_cancelled, address, zip, latitude, longitude`
- **Beer-league gold:** `type='Program'` includes `Sports - Volleyball`, `Sports - Basketball`, `Sports - Soccer`, etc. with `fee`, `age_range` and **`registration_date`**. Filter `age_range` to adults to feed the Deadlines view. Events include "Holidays, Night Out in the Parks, Halloween". Category strings contain HTML entities (`&amp;`).
- **Cadence:** daily (2026-10-15). **Sample:** `samples/chicago_park_district_activities.json`

#### CHI-2 Chicago Public Library Events `vsdy-d8k7`: **A**
- **URL:** `https://data.cityofchicago.org/resource/vsdy-d8k7.json?$where=start%3E%3D%272026-10-17T00:00:00%27&$order=start&$limit=5`
- **Fields:** `title, description, event_types, event_audiences, event_languages, event_page, location_name, location_details, start, end, featured, cancelled, recurring, registration_starts, registration_ends, registration_closed, registration_status, location_address, location_zip, location, day_of_the_week, event_id`
- `registration_ends` gives a Deadlines-view input. Adding `AND cancelled=false` to the `$where` produced a 503 once; retry, or filter client-side.
- Alternative path to the same data: BiblioCommons RSS `https://gateway.bibliocommons.com/v2/libraries/chipublib/rss/events?startDate=2026-10-17&endDate=2026-10-18` (`samples/chipublib_bibliocommons_events.rss.xml`), which adds capacity and number_registered.
- **Sample:** `samples/chicago_cpl_events.json`

#### CHI-3 Chicago Business Licenses `r5kz-chrr` (openings proxy): **A**
- **URL:** `https://data.cityofchicago.org/resource/r5kz-chrr.json?$where=application_type=%27ISSUE%27%20AND%20license_description%20in(%27Tavern%27,%27Consumption%20on%20Premises%20-%20Incidental%20Activity%27,%27Retail%20Food%20Establishment%27,%27Special%20Event%20Liquor%27)%20AND%20date_issued%3E%272026-09-15T00:00:00%27&$order=date_issued%20DESC&$limit=5`
- **Key fields:** `id, license_id, legal_name, doing_business_as_name, address, ward, community_area_name, neighborhood, license_description, business_activity, application_type (ISSUE|RENEW|C_LOC|C_CAPA|C_EXPA|C_SBA), application_created_date, conditional_approval, license_start_date, date_issued, license_status, latitude, longitude`
- **New-license descriptions since 2026-09-01:** Limited Business 203 · **Pop-Up Retail User 110** · Retail Food Establishment 93 · Regulated Business 91 · **Special Event Food 80** · Peddler 44 · **Special Event Liquor 29** · Consumption on Premises 22. "Special Event Food/Liquor" and "Pop-Up Retail" double as **event and pop-up signals**.
- **Gotcha:** `$where=... date_issued > '2026-09-01'` without a time component gave a 503 once; use the full `T00:00:00`.
- **Sample:** `samples/chicago_business_licenses_new.json`

#### CHI-4 Chicago Park District Outdoor Event Permits `pk66-w54g`: **B+**
- **URL:** `https://data.cityofchicago.org/resource/pk66-w54g.json?$where=starts_with(event_type,%27Permit%20-%20Event%27)%20AND%20reservation_start_date%3E%3D%272026-10-16T00:00:00%27&$order=reservation_start_date&$limit=5`
- **Fields:** `requestor_, organization, park_number, park_facility_name, reservation_start_date, reservation_end_date, event_type, event_description, permit_status (Tentative/Approved...)`
- `event_type` encodes **size tier**: e.g., `Permit - Event 6/10,000+`, `Permit - Event 5 Cluster 3`. That is an attendance-band input. `Permit - Athletic T Cluster 3` is sports. Exclude `Administrative Reservation*` and `Venue Rental - Wedding`. Note: `LIKE 'Permit - Event%'` returned 503 but `starts_with()` worked.
- **Sample:** `samples/chicago_park_outdoor_event_permits.json`

**Chicago failures:** `xgse-8eg7` "Special Events" returned `500 internal-error`, then 503 (last updated 2026-01-08), so treat it as dead. Farmers Markets dataset is 2012 only. Movies in the Parks datasets are 2017/2019 only. "Halloweek On the Block" is 2023. UChicago LiveWhale responds (`events.uchicago.edu/live/json/...` returns 200) but wasn't sampled.

### 3.4 Boston

#### BOS-1 Meet Boston events (Simpleview CVB API): **C+**
- **Step 1:** `GET https://www.meetboston.com/plugins/core/get_simple_token/` returns a 32-hex token (text/plain).
- **Step 2:** `GET https://www.meetboston.com/includes/rest_v2/plugins_events_events_by_date/find/?json=<urlencoded>&token=<token>` with
  `{"filter":{"active":true,"$and":[{"categories.catId":{"$exists":true}}],"date_range":{"start":{"$date":"2026-10-16T04:00:00.000Z"},"end":{"$date":"2026-10-23T04:00:00.000Z"}}},"options":{"limit":5,"skip":0,"count":true,"castDocs":false,"fields":{...},"sort":{"date":1,"rank":1,"title_sort":1}}}`
- **Fields (requested):** `_id, recid, title, date, startDate, endDate, nextDate, recurType, location, address1, city, zip, latitude, longitude, url, linkUrl, admission (free-text price, e.g., "$41-$373" or "Free"), startTime, endTime, categories[{catName,catId}], listing.title`
- **ToS/robots:** robots disallows only `/plugins/crm/count/` with `Crawl-delay: 2`. This is an **undocumented front-end API**, so it could change. Use it sparingly (one weekly window pull per day), cache, and show "via Meet Boston".
- **Volume:** 318 events in the week (Head of the Charles, Oktoberfest, pumpkin patches). **Sample:** `samples/meetboston_simpleview_events.json`

#### BOS-2 Downtown Boston BID (WP Tribe REST): **B+**
- **URL:** `https://www.downtownboston.org/wp-json/tribe/events/v1/events?start_date=2026-10-16&per_page=5` (`total: 771`). Tribe schema as above. No robots.txt was returned.
- **Sample:** `samples/downtown_boston_bid_tribe_events.json`

#### BOS-3 Boston Public Library (BiblioCommons RSS): **A-**
- **URL:** `https://gateway.bibliocommons.com/v2/libraries/bpl/rss/events?startDate=2026-10-17&endDate=2026-10-18`. About 3,700 upcoming. Fields as MN-2.
- **Sample:** `samples/bpl_boston_bibliocommons_events.rss.xml`

#### BOS-4 Boston Special Event License Applications (CKAN): **A-**
- **URL:** `https://data.boston.gov/api/3/action/datastore_search_sql?sql=SELECT%20*%20FROM%20%22fb05bfda-a57e-4d97-948b-4f1949ba3c8a%22%20WHERE%20%22Start%20Date%20and%20Time%22%20%3E%3D%20%272026-10-16%27%20ORDER%20BY%20%22Start%20Date%20and%20Time%22%20LIMIT%205`
- **Fields (all text):** `App Number, App Name, Status (Open|Closed...), Application Date, Issued Date, Location Description, Street Number, Street Name, Street Suffix, City, Zip Code, Start Date and Time, End Date and Time`. CKAN adds `_id` and `_full_text`. 8,555 rows total.
- e.g., "Boston Rodeo", 306 Northern Ave, 2026-10-16.
- **Sample:** `samples/boston_special_event_license_applications.json`

#### BOS-5 Boston Special One-Day Alcohol Licenses (CKAN `957dc193-d66b-443c-b240-beaa6d822bc9`): **A-**
- **URL:** `https://data.boston.gov/api/3/action/datastore_search_sql?sql=SELECT%20*%20FROM%20%22957dc193-d66b-443c-b240-beaa6d822bc9%22%20WHERE%20expires%20%3E%3D%20%272026-10-16%27%20ORDER%20BY%20expires%20LIMIT%205`
- **Fields:** `license_num, license_type (Special 1-Day Malt Wine / All Alcohol), issued, expires (≈ event day), business_name, dba_name (venue), applicant (organizer, e.g. "Light the Night Boston"), manager, capacity, opening, closing, address, city, zip, gpsx, gpsy` (gpsx/gpsy are MA State Plane feet, not lat/lng). `day_phone`/`evening_phone` exist but are usually null. **Drop phone and manager fields** (personal data).
- **Sample:** `samples/boston_special_one_day_alcohol_licenses.json`

#### BOS-6 Boston One-Time Entertainment Licenses (CKAN `ea7f0605-ffc0-4ad4-a786-02c50b276f54`): **B+**
- Same SQL pattern (`WHERE expires >= '2026-10-16' ORDER BY expires`). **Fields:** `license_num, status, license_type (e.g., One-Time Carnival Ent), issued, expires, dba_name, comments (often contains the time window and description), location_comments, applicant, contact, manager, address, city, zip, gpsx, gpsy`.
- **Sample:** `samples/boston_one_time_entertainment_licenses.json`

#### BOS-7 Boston Active Food Establishment Licenses (CKAN `f1e13724-284d-478c-b8bc-ef042aa5b70b`): **A-** (openings proxy)
- **URL:** `...datastore_search_sql?sql=SELECT * FROM "f1e13724-284d-478c-b8bc-ef042aa5b70b" WHERE descript = 'Eating & Drinking' ORDER BY license_add_dt_tm DESC LIMIT 5` (URL-encode it)
- **Fields:** `businessname, dbaname, address, city, zip, licstatus, licensecat (FS|FT|...), descript, license_add_dt_tm, dayphn_cleaned, property_id, latitude, longitude`. Also `liquor-licenses` (`aab353c1-…`), but it has no reliable issued date.
- **Sample:** `samples/boston_food_establishment_licenses_new.json`

#### BOS-8 Northeastern University (Localist): **B**
- **URL:** `https://calendar.northeastern.edu/api/2/events?start=2026-10-16&end=2026-10-30&pp=5`. MIT also works (`calendar.mit.edu`, Cambridge).
- **Sample:** `samples/northeastern_localist_events.json`

CKAN notes: `package_show?id=<slug>` returns the current resource id. Resource ids can change if the city re-publishes, so resolve by slug at runtime. All datastore columns are `text`, so ISO date strings compare correctly but `M/D/YYYY` would not. Boston's formats are ISO.

### 3.5 Austin

#### AUS-1 Visit Austin events (Simpleview): **C+**
- Same two-step pattern as BOS-1 on `https://www.austintexas.org` (`/plugins/core/get_simple_token/`, then `/includes/rest_v2/plugins_events_events_by_date/find/?json=…&token=…`). robots: `Crawl-delay: 2`, disallows `/plugins/crm/count/` only.
- 266 events in the week (Boo at the Zoo, Hot Luck Live "$41-$373", "333 at Tiny Minotaur Tavern $11").
- **Sample:** `samples/visitaustin_simpleview_events.json`

#### AUS-2 Austin Convention Center / Palmer Events Center listings `p9ma-z6y9`: **A-**
- **URL:** `https://datahub.austintexas.gov/resource/p9ma-z6y9.json?$where=arrive_date%3E%3D%272026-10-16%27&$order=arrive_date&$limit=5`
- **Fields:** `arrive_date, depart_date, location (Austin Convention Center | Palmer Events Center), event_name, attendance (expected, sometimes blank), phone_number, website`. 68 future rows, out to 2027-09. Conventions, festivals (Austin Coffee Festival, Markets for Makers). Updated daily.
- **Sample:** `samples/austin_convention_center_events.json`

#### AUS-3 TABC Pending Original License Applications `mxm5-tdpj` (data.texas.gov): **A** (openings and event proxy)
- **URL:** `https://data.texas.gov/resource/mxm5-tdpj.json?$where=city=%27Austin%27&$order=submission_date%20DESC&$limit=5`
- **Fields:** `master_file_id, applicationid, license_type, applicationstatus (Received | Pending – In Review ...), primary_license_id, subordinate_license_id, submission_date, trade_name, owner, wine_percent, gun_sign, address, address_2, city (Title Case), state, zip (9-digit), county, country`
- **Austin types right now:** MB (Mixed Beverage, i.e., bars and restaurants) 13 · FB (Food & Beverage cert.) 9 · BG (Wine & Beer Retailer On-Premise) 8 · **NT (Nonprofit Temporary Event)** 5 · LH, Q, LP, BB, W, BQ, P. **NT rows are upcoming charity events** (e.g., "Shoal Creek Conservancy, 828 W 6th St"). MB/BG/FB rows are upcoming bars/restaurants (e.g., "It's Italian Cucina, 1500 S Lamar Blvd Unit 110").
- Statewide: Houston 130, San Antonio 61, Dallas 57, Austin 46. Updated daily.
- **Sample:** `samples/tabc_pending_applications_austin.json`

#### AUS-4 TABC License Information `7hf9-qc9f`: **A**
- **URL:** `https://data.texas.gov/resource/7hf9-qc9f.json?$where=upper(city)=%27AUSTIN%27%20AND%20license_type%20in(%27MB%27,%27BG%27,%27BE%27)%20AND%20original_issue_date%3E%3D%272026-09-01%27&$order=original_issue_date%20DESC&$limit=5`
- **Fields:** `master_file_id, license_type, license_id, primary_status, license_status, current_issued_date, status_change_date, expiration_date, trade_name, owner, original_issue_date, tier, subordinates, address, city, zip, county, mail_*`. Since 2026-08-01 Austin had MB 29 · NT 26 · BG 12 · Q 5 · BQ 4. `city` casing is inconsistent, so use `upper(city)`.
- **Sample:** `samples/tabc_licenses_new_austin.json`

#### AUS-5 UT Austin (Localist): **B+**
- **URL:** `https://calendar.utexas.edu/api/2/events?start=2026-10-16&end=2026-10-30&pp=5` (518 items in window). robots: `Crawl-Delay: 1`; disallows only HTML `?types` permutations.
- **Localist fields:** `id, title, url, updated_at, first_date, last_date, location_name, room_number, address, geo{latitude,longitude,street,city,state,zip}, free, ticket_url, ticket_cost, has_register, experience (inperson|virtual|hybrid), status, recurring, description_text, tags, keywords, departments, filters{event_types,...}, event_instances[{event_instance{start,end,all_day,num_attending,ranking}}], detail_views, localist_url, localist_ics_url, photo_url, venue_url`. `num_attending` and `detail_views` are attendance and popularity signals.
- **Sample:** `samples/utaustin_localist_events.json`

#### AUS-6 Austin Center for Events (ACE) permits `teth-r7k8`: **B-** (history only)
- **URL:** `https://datahub.austintexas.gov/resource/teth-r7k8.json?$where=start_date%20like%20%27%25%202026%25%27&$order=report_date%20DESC,folderrsn&$limit=5`
- **Fields:** `folderrsn, foldertype, foldername, status, tier_type, event_history, event_applicant_*, start_date (TEXT like "September 26, 2026 07:30" or "Apr 01, 2023 08:00"), end_date, event_length, event_setup, event_teardown, event_cost_on_coa_propety, amplified_sound, alcohol_served, report_date, road_closure, type_of_road_closure, date_of_road_closure, gpslatitude, gpslongitude`
- **Gotchas:** dates are text in two formats, so `>` comparisons are meaningless. There is one row per road-closure segment, so dedupe on `folderrsn`. **Every 2026 row is `status=Expired`. Only past permits are published**, so there is no future feed. Useful for "past editions" and for `alcohol_served`, `tier_type` (size) and `event_history` (edition count) features. 52k rows.
- **Sample:** `samples/austin_ace_event_permits.json`

**Austin failures:** Austin Public Library is not on BiblioCommons Events (403), and `library.austintexas.gov` has no Communico. Downtown Austin Alliance has no Tribe route. Do512 was not checked (it's commercial).

### 3.6 Denver

#### DEN-1 Visit Denver events (Simpleview): **C+**
- Two-step token pattern on `https://visitdenver.com` (www redirects there). robots `Crawl-delay: 2`.
- 510 events in the week (e.g., "90s Til Dawn @ Tailgate Tavern", Denver Arts Week deals with `admission` "$40").
- **Sample:** `samples/visitdenver_simpleview_events.json`

#### DEN-2 Denver Pending Business Licenses (ArcGIS table 46): **A-** (openings proxy)
- **URL:** `https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_pending_business_licenses/FeatureServer/46/query?where=License_Type%3D%27Retail%20Food%27&outFields=*&orderByFields=APPLICATION_DATE%20DESC&resultRecordCount=5&f=geojson`
- **Fields:** `RECORD_ID, License_Type, license_sub_type, License_Status (Pending), Entity_Name, TRADE_NAME, APPLICATION_DATE, Expiration_Date, ADDRESS, ZIP, X_COORD, Y_COORD (State Plane CO Central ftUS, EPSG:2232), PRIMARY_ADDRESS_FLAG, TYPE, REPORT_DATE, DADID, ADDRESS_NO_UNIT`. **`geometry` is null**, so reproject X/Y or geocode.
- Types: Residential Rental 437 · **Retail Food 290** · Combined License 110 · Short Term Rental 98 · ... Edited daily (2026-10-15). Note: it's layer id **46**, not 0. Also available: `ODC_active_business_licenses`.
- **Sample:** `samples/denver_pending_business_licenses_food.geojson`

#### DEN-3 Denver Liquor Licenses (ArcGIS layer 27): **A-**
- **URL:** `https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/ODC_BUSN_LIQUORLICENSES_P/FeatureServer/27/query?where=ORIGINAL_ISSUE_DATE%3E%3DDATE%20%272026-08-01%27&outFields=*&orderByFields=ORIGINAL_ISSUE_DATE%20DESC&resultRecordCount=5&outSR=4326&f=geojson`
- **Fields:** `BFN, BUS_PROF_NAME, FULL_ADDRESS, LICENSES (e.g., "LIQUOR - TASTINGS"), LIC_STATUS, END_DATE, ORIGINAL_ISSUE_DATE, MOST_RECENTLY_ISSUED_DATE, EVENT_LOCATION, NEIGHBORHOOD, ZONE_DISTRICT, COUNCIL_DIST, ...`. Real point geometry (use `outSR=4326`). Edited daily.
- **Sample:** `samples/denver_liquor_licenses_new.geojson`

#### DEN-4 Colorado Recently Approved Liquor Licenses `htyp-tqzh` (data.colorado.gov): **B** (has data-quality bugs)
- **URL:** `https://data.colorado.gov/resource/htyp-tqzh.json?$where=upper(city)=%27DENVER%27%20AND%20issue_date%3C%3D%272026-10-16%27&$order=issue_date%20DESC&$limit=5`
- **Fields:** `licensee_name, doing_business_as, license_type, issue_date, license_number, street_address, city, state, zip ("80211.0" float-ified!), location`
- **Bug:** some rows have **`issue_date` and `license_number` swapped**, e.g., `issue_date: "2257-03-01"`, `license_number: "2025-05-21"`. Guard with `issue_date <= today`, validate the `license_number` pattern `^\d{2}-\d+$`, and quarantine bad rows. The dirty rows are saved as a test fixture.
- **Samples:** `samples/colorado_recently_approved_liquor_denver.json`, `samples/colorado_recently_approved_liquor_denver_anomalies.json`

**Denver failures:** **Denver Public Library uses LibCal (`denverlibrary.libcal.com`), whose robots.txt says `User-agent: * / Disallow: /`**. Don't use it without written permission. The Denver open data hub has **no events/permits dataset** (an "event" search returns only FEMA layers). CU Denver, MSU Denver and DU have no Localist/LiveWhale found. Downtown Denver Partnership, RiNo and Cherry Creek North have no Tribe API.

### 3.7 Seattle

#### SEA-1 Seattle Public Library (Trumba JSON, webname `kalendaro`): **A-**
- **URL:** `https://www.trumba.com/calendars/kalendaro.json?startdate=20261017&days=2` (29 events). Also `.ics` / `.rss` variants. Trumba robots: `Disallow:` (allows all).
- **Fields:** `eventID, title (HTML entities), description (HTML), location, webLink, startDateTime, endDateTime (local, no offset), startTimeZoneOffset ("-0700"), allDay, canceled, openSignUp, reservationFull, pastDeadline, requiresPayment, waitingListAvailable, repeats, seriesID, eventImage, detailImage, customFields[{label,value}] ("Registration Required", "Event Logistics", ...), permaLinkUrl, eventActionUrl, categoryCalendar`
- Without `startdate`/`days`, the whole calendar comes back (1.27 MB, 200 events), so always filter.
- **Sample:** `samples/spl_seattle_trumba_events.json`

#### SEA-2 University of Washington (Trumba JSON, webname `sea_campus`): **B+**
- **URL:** `https://www.trumba.com/calendars/sea_campus.json?startdate=20261017&days=3`. Same schema. `customFields` include "Event Types", "Campus location", "Campus room".
- **Sample:** `samples/uw_seattle_trumba_events.json`

#### SEA-3 Seattle Active Business License Tax Certificate `wnbq-64tb` (cos-data.seattle.gov): **A-** (openings proxy)
- **URL:** `https://cos-data.seattle.gov/resource/wnbq-64tb.json?$where=starts_with(naics_code,%277224%27)%20OR%20starts_with(naics_code,%27722511%27)&$order=license_start_date%20DESC&$limit=5`
- **Fields:** `business_legal_name, trade_name, ownership_type, naics_code, naics_description, license_start_date (TEXT "YYYYMMDD", sorts correctly), street_address, city, state, zip, business_phone, city_account_number, ubi`
- **Future `license_start_date` values (e.g., 20261218, 20261201) are pre-registered upcoming openings**, e.g., "VIRTUE COFFEE AND COCKTAILS, 1321 Madison St, Drinking Places". NAICS 722410 = bars, 722511 = full-service restaurants. **Drop `business_phone`.** No lat/lng, so geocode. Daily.
- **Note:** Seattle's Socrata domain is **`cos-data.seattle.gov`**. `data.seattle.gov` returns nothing in the catalog API.
- **Sample:** `samples/seattle_business_license_new_food_drink.json`

#### SEA-4 WA LCB Local Authority Letters `vgcw-qfjm` (data.wa.gov): **B-**
- **URL:** `https://data.wa.gov/resource/vgcw-qfjm.json?$where=l_a_type=%27NEW%20LICENSE%20APPLICATION%27&$order=applicationdate%20DESC&$limit=5`
- **Fields:** `license, ubi, applicationdate (YYYYMMDD text), cityname, l_a_type (NEW LICENSE APPLICATION | ASSUMPTION | CHANGE OF LOCATION ...), licenseename, tradename, streetaddress, city, zipcode, privdesc01..08 (privilege, e.g., "S/B/W RESTAURANT LOUNGE (+)"), la_posted_date, location`
- **Only 18 rows statewide** (a rolling window of recent notices) and **0 for Seattle today**, so you'd need daily snapshotting to build history. Low yield.
- **Sample:** `samples/wa_lcb_local_authority_letters.json`

#### SEA-5 Downtown Seattle Association (WP Tribe): **C** (small)
- `https://downtownseattle.org/wp-json/tribe/events/v1/events?start_date=2026-10-16&per_page=5`. Only 7 upcoming (Occidental Square Flea, Bell Street Park Halloween Bash). **Sample:** `samples/downtown_seattle_dsa_tribe_events.json`

**Seattle failures:** Special Events Permits `dm95-f8w5` is **dead** (last `event_start_date` 2025-10-10, updated 2025-01-08). SPL is not on BiblioCommons Events. Seattle Center and Visit Seattle have no Tribe/Simpleview API. Seattle Parks has no Trumba webname found (guessed several).

### 3.8 Nashville

#### NSH-1 Nashville Beer Permits (ArcGIS, Metro Beer Board): **A-** (openings and events proxy)
- **URL:** `https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Beer_Permit_Locations_Feature_Layer_view/FeatureServer/0/query?where=Date_Entered%3E%3DDATE%20%272026-09-01%27&outFields=*&orderByFields=Date_Entered%20DESC&resultRecordCount=5&f=geojson`
- **Fields:** `Permit__ (e.g., T26-30199), Status (TEMPORARY|ISSUED), Permit_Type, Permit_Sub_Type (ONSALES|SPECIAL|...), Permit_Subtype_Description ("BB - On Site Sales", "BB - Special Events", ...), Date_Entered, Date_Issued, Parcel, Business_Name, Business_Owner, Address, City, ZIP, Council_Dist, Census_Tract, Lon, Lat`
- Since 2026-08-01: **10 "BB - Special Events" temporary permits** (event signal, e.g., "RACE JUDICATA") and about 23 new on-site/on-and-off-site permits (e.g., "LUCKY'S PUB"). Edited daily (2026-10-15). The data portal is `datanashvillegov-nashville.hub.arcgis.com`.
- **Sample:** `samples/nashville_beer_permits_new.geojson`

#### NSH-2 Vanderbilt University (LiveWhale JSON): **B**
- **URL:** `https://events.vanderbilt.edu/live/json/events/start_date/2026-10-16/end_date/2026-10-31/max/5`. Classic LiveWhale array shape (like UMN). robots allows.
- **Sample:** `samples/vanderbilt_livewhale_events.json`

**Nashville failures:** `library.nashville.gov`, `nashville.gov/departments/parks/events` and `visitmusiccity.com` (including its Simpleview token endpoint) all returned **403 Cloudflare challenges** to curl. Don't try to bypass them. If needed, ask for API access. Nashville Downtown Partnership and Nashville Farmers' Market have no Tribe API. No Nashville events/permits dataset found on the hub (an "event" search returns police calls only). Tennessee ABC has no open data.

### 3.9 Miami

#### MIA-1 Miami-Dade Public Library System (Communico JSON): **B+** (undocumented front-end endpoint)
- **URL:** `https://www.mdpls.org/eeventcaldata?event_type=0&req=%7B%22private%22%3Afalse%2C%22date%22%3A%222026-10-17%22%2C%22days%22%3A1%2C%22locations%22%3A%5B%5D%2C%22ages%22%3A%5B%5D%2C%22types%22%3A%5B%5D%7D`
- robots: disallows only `/results*`, `/sitesearch*` and `/contact-us`.
- **Fields:** `id, recurring_id, title, sub_title, description, raw_start_time, raw_end_time (local), start_time, end_time, location, library, location_id, venue_name, venue_room, url, event_contact, allow_reg, reg_url, reg_opens, registration_close, max_attendee, total_registrants, total_waitlist, registration_cost, tags, ages, event_type, tagsArray, agesArray, changed, changed_reason, private_event, image`
- 133 events for one day (about 525 KB/day, so request `days=1` and loop). `total_registrants` vs `max_attendee` is an attendance signal.
- **Sample:** `samples/mdpls_communico_events.json`

#### MIA-2 Florida DBPR ABT daily transactions `daily.csv`: **A-** (openings and events proxy)
- **URL:** `https://www2.myfloridalicense.com/sto/file_download/extracts/daily.csv` (about 79 KB, statewide, **headerless**, rebuilt daily around 10:45 UTC. The `Last-Modified` header works for conditional GET.)
- **Columns (positional):** `profession_code (4002=temp permits, 4006=retail), county name ("Dade"), license_number, series (e.g., ODP, 2COP, 4COP, SFS), modifier, DBA (event or business name), owner, address1, address2, address3, city, state, zip, transaction_date (MM/DD/YYYY), transaction_code, transaction_description ("Limited One Two Three Day Permit", "Issue Permanent License (From Temp)", "Stand Alone Permanent Licensure", "Set to Closed", ...), flag`
- 45 Dade rows on 2026-10-14, e.g., "URGE MIAMI BEACH PARTY FBO MIAMI BEACH GAY PRIDE INC, Lummus Park" (temporary event permit). Openings are `Issue Permanent License (From Temp)` and `Stand Alone Permanent Licensure` with 4006 + COP series.
- robots: allows `/sto/` (it only blocks WP internals). The page is the official "Public Records" download page.
- **Sample:** `samples/fl_dbpr_abt_daily_transactions_dade.csv`

#### MIA-3 Florida DBPR Temporary Alcoholic Beverage Permits `bd4002lic.csv`: **A-**
- **URL:** `https://www2.myfloridalicense.com/sto/file_download/extracts/bd4002lic.csv` (about 1 MB statewide, with header row, daily)
- **Columns:** `Board, Profession, Owner Name, Series (ODP), Modifier, Mail Address 1-3, Mail City/State/ZIP/County, DBA (event name), Location Address 1-3, Location City, Location State, Location ZIP, Location County ("23" = Dade), License Number, Primary Status, Secondary Status, Original Licensure Date, Effective Date, Expiration Date, ...`
- 14 Dade rows with `Expiration Date >= 2026-10-16`: "2026 MIAMI BEACH HALLOWEEN HALFMARATHON & 4 MILER" (exp 10/24), "SOUTH BEACH SEAFOOD FESTIVAL" (10/25), "PERUFEST USA" (11/15), "HISPANIC HERITAGE WEEKEND" (Hialeah). `Expiration Date` approximates the event's last day. Retail licenses for openings are in `bd4006lic.csv` (14 MB, statewide), which has `Original Licensure Date`.
- Encoding: the source file is latin-1. The fixture was re-written as UTF-8 with QUOTE_ALL.
- **Sample:** `samples/fl_dbpr_temporary_alcohol_permits_dade.csv`

#### MIA-4 FIU (Localist): **B-**
- `https://calendar.fiu.edu/api/2/events?start=2026-10-16&end=2026-10-30&pp=5` (152 items, mostly academic). **Sample:** `samples/fiu_localist_events.json`

**Miami failures:** Miami-Dade hub "Tbl Calendar Wiz Event" is **dead** (50 rows, data last edited 2021-05). The City of Miami hub has transit and GIS layers only. Greater Miami CVB (`miamiandbeaches.com`) has no Simpleview endpoint. `calendar.miami.edu` (UM) connection failed. The Miami Beach city calendar URL returned 404. MDPLS is not on BiblioCommons.

### 3.10 Los Angeles

#### LA-1 USC (Localist): **B**
- `https://calendar.usc.edu/api/2/events?start=2026-10-16&end=2026-10-30&pp=5`. **Sample:** `samples/usc_localist_events.json`

#### LA-2 LA Listing of Active Businesses `6rrh-rzua` (openings proxy): **B+**
- **URL:** `https://data.lacity.org/resource/6rrh-rzua.json?$where=starts_with(naics,%277224%27)%20OR%20starts_with(naics,%277225%27)&$order=location_start_date%20DESC&$limit=5`
- **Fields:** `location_account, business_name, dba_name, street_address, city, zip_code, location_description, mailing_*, naics, primary_naics_description, council_district, location_start_date, location_end_date, location_1{latitude,longitude}`. Future start dates (to 2027-04) indicate upcoming openings. **`location_1` is often `0.0,0.0`**, so treat it as null and geocode. 2,231 rows with start date after 2026-09-01 across all NAICS.
- **Sample:** `samples/la_active_businesses_new_food_drink.json`

#### LA-3 LADBS Temporary Special Event (TSE) Permits `8spw-3fhx`: **B-** (thin)
- **URL:** `https://data.lacity.org/resource/8spw-3fhx.json?$where=event_start_date%3E%3D%272026-10-01%27%20AND%20event_start_date%3C%272027-12-31%27&$order=event_start_date&$limit=5`
- **Fields:** `permitno, per_type, per_sub_type (Commercial...), address_*, zip_code, work_desc, location, event_name, event_start_date, event_end_date, lat_lon`. Only 11 future rows, and one has a bogus 2109 date (needs a guard). These are structure permits (stages, tents), so they skew to big branded events (e.g., "FIGMA MOTION").
- **Sample:** `samples/la_ladbs_temporary_special_event_permits.json`

#### LA-4 California ABC "New Applications" daily report: **C** (HTML only, not sampled)
- `https://www.abc.ca.gov/licensing/licensing-reports/new-applications/` renders about 30 statewide items for the latest day as HTML (`License Number`, `Status: PEND`, `Type|Dup` (47 = on-sale general eating place, 41 = beer & wine eating place), DBA, owner, premises address, `Orig. Iss. Date`). Other dates need a WP form POST with nonce (`abclqs-date`). robots allows (blocks only `/wp-admin/`). Worth an HTML adapter later. Filter on `LOS ANGELES, CA 9xxxx`.

**LA failures:** LA City Events `9aw9-mn4p` ("2022-2025") has **0 future rows**, so it's dead for our purposes. "What's Happening LA" datasets are archived 2015-2018. El Pueblo special events were last updated 2025-08. LAPL (Drupal) has no feed/ICS/RSS found. **laparks.org returns 403**. LA County Parks, Grand Park and LA County Library have no Tribe route. UCLA, LMU and CSULB have no Localist. Discover LA has no Simpleview endpoint or JSON:API.

---

## 4. Dead, blocked, or rejected (do not build)

| Source | City | Status | Evidence |
|---|---|---|---|
| nycgovparks.org `/xml/events_300_rss.json` | NYC | **robots-disallowed** (`Disallow: /xml/`, `/*xml`) | Use Open Data `w3wp-dpdi` instead |
| NYC Parks Events Listing `fudw-fgrp` + child tables | NYC | Dead | `max(date)=2019-12-28`, updated 2021-08 |
| NYPL / Seattle PL / Austin PL on BiblioCommons Events | NYC/SEA/AUS | Not enabled | 403 "Events feature is not available" |
| BiblioCommons JSON `gateway…/v2/libraries/{lib}/events` | all | Undocumented; ignores date params | Use the `/rss/events` feed |
| Denver Public Library LibCal | Denver | **robots `Disallow: /`** | `denverlibrary.libcal.com/robots.txt` |
| Chicago "Special Events" `xgse-8eg7` | Chicago | Broken | 500 internal-error, then 503; last update 2026-01-08 |
| Seattle Special Events Permits `dm95-f8w5` | Seattle | Dead | last event 2025-10-10 |
| LA City Events `9aw9-mn4p` | LA | No future rows | `count where start>2026-10-15 = 0` |
| Miami-Dade "Tbl Calendar Wiz Event" | Miami | Dead | 50 rows, last data edit 2021 |
| Austin ACE `teth-r7k8` | Austin | Past-only | all 2026 rows `Expired` (kept as enrichment) |
| Nashville library, Metro Parks, Visit Music City | Nashville | Cloudflare 403 | don't bypass |
| laparks.org | LA | 403 | |
| Columbia Localist, Explore Minnesota | NYC/MN | Cloudflare | |
| Walker Art Center feeds | MN | Disabled | WP "Feeds are not available" |
| artsmia.org | MN | 429 on first request | |
| Chicago Farmers Markets / Movies in Parks datasets | Chicago | Stale (2012/2017/2019) | |

---

## 5. Implementation recommendations

1. **Vertical slice (Minneapolis):** MPRB Tribe (MN-1) + HCLib RSS (MN-2) + Mpls Downtown Council Tribe (MN-3). That's one Tribe adapter plus one BiblioCommons-RSS adapter, and it yields about 3,000 upcoming events, with geo, capacity and RSVP counts. Add UMN LiveWhale and On-Sale Liquor (snapshot-diff) next.
   **Vertical slice (NYC):** a single Socrata adapter covers NYC-1, -2, -3, -4 and -5 with different configs. Use SLA Pending to drive a "Coming soon" card type.
2. **Adapter-per-platform, config-per-city.** A city config becomes a list of `{platform, base_url, dataset_id/lib/webname, filters, field_map}`. That satisfies the "adding a city is config, not code" requirement.
3. **Health checks per source:** Socrata `rowsUpdatedAt`, ArcGIS `editingInfo.lastEditDate`, CKAN `metadata_modified`, HTTP `Last-Modified` (FL DBPR), and row counts per window (e.g., alert if MPRB returns 0 in the next 30 days). Treat Socrata 503 as transient: retry with backoff before you quarantine the source.
4. **"Openings" pipeline:** prefer *pending* or *future-dated* signals (NY SLA Pending, TABC Pending, Denver Pending, Seattle future `license_start_date`, LA future `location_start_date`). Use *issued* signals (NY SLA Active `originalissuedate`, Chicago ISSUE, Denver `ORIGINAL_ISSUE_DATE`, Boston `license_add_dt_tm`, Nashville Beer Permits, FL daily) to confirm. For Minneapolis, diff snapshots because there is no original-issue date. Label these "license signals", not confirmed openings.
5. **Event-from-permit pipeline:** temporary or one-day alcohol permits (Boston one-day, FL ODP, TABC NT, Nashville BB-Special Events, Chicago Special Event Liquor/Food) are a strong, under-used signal for festivals and parties. Many lack times or descriptions, so mark them `confidence: low` and enrich by name-matching against the CVB and Tribe feeds.
6. **Attendance modelling inputs:** BiblioCommons `capacity` and `number_registered`, Communico `max_attendee` and `total_registrants`, Localist `num_attending` and `detail_views`, LiveWhale `rsvp_total` and `registration_limit`, Chicago permit size tiers, Austin Convention Center `attendance`, NYC Parks Public Programs historical `attendance`, Austin ACE `tier_type` and `event_history`.
7. **PII hygiene:** drop phone, manager, applicant-person and owner-person fields (Boston, Seattle, TABC, FL, Nashville `Business_Owner`) at the ingest boundary. Keep business and organization names only.
8. **ToS risk ranking:** official open data (Socrata, ArcGIS, CKAN, FL DBPR public records) is lowest risk. Published feeds (BiblioCommons RSS, LiveWhale/Trumba/Localist public APIs, WP REST) are low. Undocumented front-end JSON (Simpleview CVB, Communico `eeventcaldata`) is medium: they're allowed by robots, but you should cache aggressively, attribute, and be ready to drop them.
