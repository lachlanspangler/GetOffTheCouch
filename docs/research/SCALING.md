# Scaling GetOffTheCouch from 10 to 50 and then 100 metros

Research date: 2026-10-16. Every probe below was a single polite request with the UA
`GetOffTheCouch/0.1 (+https://github.com/lachlanspangler/GetOffTheCouch)`, made after reading robots.txt, with
≥1 s between hosts and the published Crawl-delay where one exists. The two exceptions are flagged in §2.10.
Numbers labeled **measured** come from `data/gotc.db` and `web/public/data/` as of run 40. Numbers labeled
**estimate** are extrapolations, and the method is given next to each.

**Short version:**
- Two things don't scale today, and both are about the pipeline, not the product:
  1. **Discovery.** Today's ~20 units per city were found by hand.
  2. **The monolithic hourly job.** It rebuilds every city, persists one SQLite file, and uploads the whole site.
- At 50 cities the current design still fits in an hour (~20 min/run). At 100 it doesn't (~34 min/run against a
  25-min fetch budget).
- The fix is a short list of changes:
  - `gotc discover` to find sources
  - per-city state files
  - a sharded matrix plus one publish job
  - incremental builds and exports
  - one geocoding lane that respects Nominatim's "4 requests/minute for recurring scripts" rule. **We currently
    break that rule** (§4.3).

---

## 1. Top 50 US metros

**Source:** U.S. Census Bureau, *Vintage 2024 Population Estimates, Metropolitan and Micropolitan Statistical Areas
(CBSA-EST2024-alldata)*, https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/metro/totals/cbsa-est2024-alldata.csv
(fetched 2026-10-16; robots allows).
- The table is ranked by `POPESTIMATE2024` (1 July 2024) over the 2023 OMB delineations.
- `ESTIMATESBASE2020` is the April 2020 base.
- Connecticut uses planning regions now, so Hartford is the new CBSA 25540.
- Buffalo (#51, 1.16 M) and Tucson (#52, 1.08 M) are the next two, if we want a buffer.

**Columns:**
- **Center:** the principal city's downtown or city hall, to 4 dp. These are from general knowledge, not a
  surveyed source. `gotc discover` should re-derive them with one Census geocoder call on the city-hall address and
  keep that call's output as provenance.
- **radius_km:** follows today's convention (20 for compact cores, 25–30 for sprawling or polycentric metros). It
  covers the core plus the inner ring, not the whole MSA.
- **tz:** the IANA zone. It can be cross-checked with `api.weather.gov/points/{lat},{lon}` → `timeZone`. One probe:
  Phoenix → `America/Phoenix`.

| # | CBSA | MSA (2024 pop.) | principal city | ST | slug | center (lat, lon) | radius_km | IANA tz | have? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 35620 | New York-Newark-Jersey City (19.94 M) | New York | NY | nyc | 40.7128, -74.0060 | 25 | America/New_York | ✅ |
| 2 | 31080 | Los Angeles-Long Beach-Anaheim (12.93 M) | Los Angeles | CA | los_angeles | 34.0522, -118.2437 | 30 | America/Los_Angeles | ✅ |
| 3 | 16980 | Chicago-Naperville-Elgin (9.41 M) | Chicago | IL | chicago | 41.8781, -87.6298 | 25 | America/Chicago | ✅ |
| 4 | 19100 | Dallas-Fort Worth-Arlington (8.34 M) | Dallas | TX | dallas | 32.7767, -96.7970 | 30 | America/Chicago | |
| 5 | 26420 | Houston-Pasadena-The Woodlands (7.80 M) | Houston | TX | houston | 29.7604, -95.3698 | 30 | America/Chicago | |
| 6 | 33100 | Miami-Fort Lauderdale-West Palm Beach (6.46 M) | Miami | FL | miami | 25.7617, -80.1918 | 30 | America/New_York | ✅ |
| 7 | 47900 | Washington-Arlington-Alexandria (6.44 M) | Washington | DC | washington_dc | 38.9072, -77.0369 | 20 | America/New_York | |
| 8 | 12060 | Atlanta-Sandy Springs-Roswell (6.41 M) | Atlanta | GA | atlanta | 33.7490, -84.3880 | 25 | America/New_York | |
| 9 | 37980 | Philadelphia-Camden-Wilmington (6.33 M) | Philadelphia | PA | philadelphia | 39.9526, -75.1652 | 20 | America/New_York | |
| 10 | 38060 | Phoenix-Mesa-Chandler (5.19 M) | Phoenix | AZ | phoenix | 33.4484, -112.0740 | 30 | America/Phoenix | |
| 11 | 14460 | Boston-Cambridge-Newton (5.03 M) | Boston | MA | boston | 42.3601, -71.0589 | 20 | America/New_York | ✅ |
| 12 | 40140 | Riverside-San Bernardino-Ontario (4.74 M) | Riverside | CA | riverside | 33.9806, -117.3755 | 30 | America/Los_Angeles | |
| 13 | 41860 | San Francisco-Oakland-Fremont (4.65 M) | San Francisco | CA | san_francisco | 37.7749, -122.4194 | 20 | America/Los_Angeles | |
| 14 | 19820 | Detroit-Warren-Dearborn (4.40 M) | Detroit | MI | detroit | 42.3314, -83.0458 | 25 | America/Detroit | |
| 15 | 42660 | Seattle-Tacoma-Bellevue (4.15 M) | Seattle | WA | seattle | 47.6062, -122.3321 | 20 | America/Los_Angeles | ✅ |
| 16 | 33460 | Minneapolis-St. Paul-Bloomington (3.76 M) | Minneapolis | MN | minneapolis | 44.9778, -93.2650 | 20 | America/Chicago | ✅ |
| 17 | 45300 | Tampa-St. Petersburg-Clearwater (3.42 M) | Tampa | FL | tampa | 27.9506, -82.4572 | 25 | America/New_York | |
| 18 | 41740 | San Diego-Chula Vista-Carlsbad (3.30 M) | San Diego | CA | san_diego | 32.7157, -117.1611 | 25 | America/Los_Angeles | |
| 19 | 19740 | Denver-Aurora-Centennial (3.05 M) | Denver | CO | denver | 39.7392, -104.9903 | 25 | America/Denver | ✅ |
| 20 | 36740 | Orlando-Kissimmee-Sanford (2.94 M) | Orlando | FL | orlando | 28.5384, -81.3789 | 25 | America/New_York | |
| 21 | 16740 | Charlotte-Concord-Gastonia (2.88 M) | Charlotte | NC | charlotte | 35.2271, -80.8431 | 25 | America/New_York | |
| 22 | 12580 | Baltimore-Columbia-Towson (2.86 M) | Baltimore | MD | baltimore | 39.2904, -76.6122 | 20 | America/New_York | |
| 23 | 41180 | St. Louis (2.81 M) | St. Louis | MO | st_louis | 38.6270, -90.1994 | 25 | America/Chicago | |
| 24 | 41700 | San Antonio-New Braunfels (2.76 M) | San Antonio | TX | san_antonio | 29.4241, -98.4936 | 25 | America/Chicago | |
| 25 | 12420 | Austin-Round Rock-San Marcos (2.55 M) | Austin | TX | austin | 30.2672, -97.7431 | 25 | America/Chicago | ✅ |
| 26 | 38900 | Portland-Vancouver-Hillsboro (2.54 M) | Portland | OR | portland | 45.5152, -122.6784 | 20 | America/Los_Angeles | |
| 27 | 40900 | Sacramento-Roseville-Folsom (2.46 M) | Sacramento | CA | sacramento | 38.5816, -121.4944 | 20 | America/Los_Angeles | |
| 28 | 38300 | Pittsburgh (2.43 M) | Pittsburgh | PA | pittsburgh | 40.4406, -79.9959 | 20 | America/New_York | |
| 29 | 29820 | Las Vegas-Henderson-North Las Vegas (2.40 M) | Las Vegas | NV | las_vegas | 36.1699, -115.1398 | 20 | America/Los_Angeles | |
| 30 | 17140 | Cincinnati (2.30 M) | Cincinnati | OH | cincinnati | 39.1031, -84.5120 | 20 | America/New_York | |
| 31 | 28140 | Kansas City (2.25 M) | Kansas City | MO | kansas_city | 39.0997, -94.5786 | 25 | America/Chicago | |
| 32 | 18140 | Columbus (2.23 M) | Columbus | OH | columbus | 39.9612, -82.9988 | 20 | America/New_York | |
| 33 | 26900 | Indianapolis-Carmel-Greenwood (2.17 M) | Indianapolis | IN | indianapolis | 39.7684, -86.1581 | 20 | America/Indiana/Indianapolis | |
| 34 | 17410 | Cleveland (2.17 M) | Cleveland | OH | cleveland | 41.4993, -81.6944 | 20 | America/New_York | |
| 35 | 34980 | Nashville-Davidson–Murfreesboro–Franklin (2.15 M) | Nashville | TN | nashville | 36.1627, -86.7816 | 25 | America/Chicago | ✅ |
| 36 | 41940 | San Jose-Sunnyvale-Santa Clara (2.00 M) | San Jose | CA | san_jose | 37.3382, -121.8863 | 20 | America/Los_Angeles | |
| 37 | 47260 | Virginia Beach-Chesapeake-Norfolk (1.79 M) | Virginia Beach | VA | hampton_roads | 36.8500, -76.1500 ¹ | 30 | America/New_York | |
| 38 | 27260 | Jacksonville (1.76 M) | Jacksonville | FL | jacksonville | 30.3322, -81.6557 | 30 | America/New_York | |
| 39 | 39300 | Providence-Warwick (1.70 M) | Providence | RI | providence | 41.8240, -71.4128 | 15 | America/New_York | |
| 40 | 33340 | Milwaukee-Waukesha (1.57 M) | Milwaukee | WI | milwaukee | 43.0389, -87.9065 | 20 | America/Chicago | |
| 41 | 39580 | Raleigh-Cary (1.56 M) | Raleigh | NC | raleigh | 35.7796, -78.6382 | 20 | America/New_York | |
| 42 | 36420 | Oklahoma City (1.50 M) | Oklahoma City | OK | oklahoma_city | 35.4676, -97.5164 | 25 | America/Chicago | |
| 43 | 31140 | Louisville/Jefferson County (1.39 M) | Louisville | KY | louisville | 38.2527, -85.7585 | 20 | America/Kentucky/Louisville | |
| 44 | 40060 | Richmond (1.37 M) | Richmond | VA | richmond | 37.5407, -77.4360 | 20 | America/New_York | |
| 45 | 32820 | Memphis (1.34 M) | Memphis | TN | memphis | 35.1495, -90.0490 | 20 | America/Chicago | |
| 46 | 41620 | Salt Lake City-Murray (1.30 M) | Salt Lake City | UT | salt_lake_city | 40.7608, -111.8910 | 20 | America/Denver | |
| 47 | 13820 | Birmingham (1.19 M) | Birmingham | AL | birmingham | 33.5186, -86.8104 | 20 | America/Chicago | |
| 48 | 23420 | Fresno (1.19 M) | Fresno | CA | fresno | 36.7378, -119.7871 | 15 | America/Los_Angeles | |
| 49 | 24340 | Grand Rapids-Wyoming-Kentwood (1.18 M) | Grand Rapids | MI | grand_rapids | 42.9634, -85.6681 | 15 | America/Detroit | |
| 50 | 25540 | Hartford-West Hartford-East Hartford (1.17 M) | Hartford | CT | hartford | 41.7658, -72.6734 | 15 | America/New_York | |

¹ Hampton Roads is polycentric. The center is placed between downtown Norfolk (36.8508, -76.2859) and the
Virginia Beach oceanfront, with a 30 km radius.

**Notes:**
- **Have:** 10 of the top 50 (ranks 1, 2, 3, 6, 11, 15, 16, 19, 25, 35).
- **Polycentric metros.** Dallas–Fort Worth, SF–Oakland, Tampa–St. Pete, Riverside–San Bernardino and
  Minneapolis–St. Paul are poorly served by one circle. Two options:
  - a second "satellite" city sharing the metro's sources: `fort_worth` (32.7555, -97.3308), `oakland`
    (37.8044, -122.2712), `st_petersburg` (27.7676, -82.6403)
  - `extra_centers:` on one city config
  - Minneapolis already handles this with `aliases`.
- **Aliases** should come from the CBSA's principal-city list (OMB delineation file, list 2), not from memory.
- **Choosing cities 51–100.** Continue the same ranking (Buffalo, Tucson, Tulsa, Urban Honolulu, Rochester,
  Omaha, …). Add college towns that rank below 100 but punch above their weight for newcomers (Durham–Chapel Hill
  #~80, Madison #~85, Boise #~75, Ann Arbor) once the quality bar (§3) is in force. Small metros will fail it more
  often.

Config skeleton (one row → one file, the rest filled by `gotc discover`):

```yaml
slug: phoenix
name: Phoenix
state: AZ
timezone: America/Phoenix
center: [33.4484, -112.0740]
radius_km: 30
cbsa: "38060"                       # new: ties the city to Census/Scorecard/IMLS lookups
aliases: [Tempe, Mesa, Scottsdale, Chandler, Glendale, Gilbert]   # from OMB principal cities
enabled: false                      # flips to true only when the §3 gate passes
sources: []                         # candidates arrive via config/cities/_candidates/phoenix.yaml
```

---

## 2. Automatic source discovery

### 2.1 What's automatable

Today's 196 units by adapter family (from `config/`): ics 23, jsonld 22, tribe 20, socrata 17, rss_events 13
(mostly carbonhouse), curated 6, bibliocommons 6, volo 5, handsonconnect 5, localist 4, livewhale 4, arcgis 4,
trumba 3, challenge 3, simpleview 3 (all disabled), galaxydigital 2, ckan 2 (disabled), csvfile 2, communico 1,
teamtrivia 1, plus the global units.

Nearly every family has a **platform fingerprint** plus a **machine-readable endpoint**, so discovery means two
steps: (1) find the organizations a newcomer cares about (the government open-data portal, the library system,
the big universities, the venues, the parks department, the volunteer center); (2) fingerprint each one's website
and probe the endpoint.

**Estimate:** about 60–70% of a hand-built city's units are reachable this way. That's every family above except
curated, Luma org calendars and the ToS-sensitive jsonld venues. Backtesting against the 10 existing cities (idea #1
in §5) would turn this into a measured recall number.

### 2.2 Government open data

#### Socrata Discovery API ✅ verified keyless

- **Request:** `GET https://api.us.socrata.com/api/catalog/v1?domains=<d1,d2>&q=<terms>&only=datasets&limit=100`
- **Without `domains`, it searches every Socrata tenant.** That's the useful mode for discovery, because we don't
  yet know the city's portal hostname.
- **Response:** `{"results":[…], "resultSetSize": N}`. Each result has:
  - `resource.{id, name, description, updatedAt, data_updated_at, columns_field_name[], columns_datatype[], page_views.page_views_last_month}`
  - `metadata.domain`
  - `classification.{domain_category, domain_tags, categories}`
  - `permalink`
- Those fields are enough to auto-generate a candidate `socrata` unit: `domain` + `dataset` id, plus a column
  mapping guessed from `columns_field_name`, e.g. `*_start_date`/`date` → start, `location`/`latitude` → geo,
  `dba_name`/`trade_name` → title.
- **Probes, 2026-10-16:**
  - `domains=data.cityofchicago.org&q=events` → 35 datasets in 0.49 s. Found our `pk66-w54g` plus two we don't
    use: `xgse-8eg7` "Special Events" and `38sz-xyf4` "Public Health Department Events" (updated today).
  - Cross-tenant `q=special events` → 235 hits. Top domains: data.cityofchicago.org 11, datahub.austintexas.gov 9,
    data.ny.gov 9, data.cityofnewyork.us 8, mesa, norfolk, seattle, lacity, providence, cincinnati, richmond, Baton Rouge…
  - Cross-tenant `q=liquor license` → 61 hits. Domains: data.colorado.gov 13, data.mo.gov 10, data.oregon.gov 8,
    Prince George's 6, dallasopendata.com 4, data.ny.gov 3, data.wa.gov 3, data.texas.gov 2, …
  - Cross-tenant `q=business license` → 564 hits. Includes data.nola.gov 9, data.kcmo.org 2, data.cityoforlando.net,
    data.richmondgov.com, data.cincinnati-oh.gov, data.delaware.gov.
- **No domain list.** `/api/catalog/v1/domains` returns 404. To get a tenant list, aggregate `metadata.domain` over
  broad queries, or use `GET /api/catalog/v1/domains/<domain>/facets` (works; returns datatype, category and tag
  counts).
- **robots:** `api.us.socrata.com/robots.txt` is a 301 to an nginx page, i.e. no policy. It's a documented API, so
  it fits the existing Socrata exception.
- **Filtering:** keep a result when `metadata.domain` or `resource.attribution` names the city, county or state.
  Drop non-US tenants (`.ca`, `.au`) and `*.demo.socrata.com` / `integration-*` sandboxes, which showed up in
  results.

#### data.gov catalog ✅ verified (new API, not CKAN)

- **catalog.data.gov is no longer CKAN.** `/api/3/action/package_search` → 404 `{"message":"Not Found"}`. The new
  service publishes `GET /openapi.json`, with:
  - `GET /search?q=&per_page=&after=&org_slug=&publisher=&keyword=&spatial_filter=&spatial_within=&spatial_geometry=&theme=&has_download=`
  - `/api/organizations`, `/api/publishers`, `/api/dataset/{slug}`, `/api/locations/search`, `/api/keywords`
- **Probe:** `/search?q=special events&per_page=5` → results with `identifier`, `publisher`, `slug`, `title`,
  `keyword`, `organization`. The identifier is a Socrata `.../api/views/<id>` URL, which tells us the platform and
  dataset id directly: Austin `nryc-8bbh`, Providence `rv3y-tq8q`, Seattle `dm95-f8w5` "Special Events Permits".
- **robots:** `Crawl-Delay: 10`, no disallows. Keep to ≤6 req/min.
- **Use:** a second index that also covers ArcGIS and CKAN portals harvested into data.gov, via the `publisher` →
  portal host mapping. The spatial parameters weren't exercised (the Crawl-Delay made the probe budget tight).
  Verify `spatial_within` with a city bbox before relying on it.

#### ArcGIS Hub + ArcGIS Online ✅ verified (two-step)

- **Step 1: find the city's Hub site and orgId.** `GET https://hub.arcgis.com/api/search/v1/collections/site/items?q=<City> open data&limit=5`
  (OGC API Records). Feature `properties.{title, source, orgId, url, owner}`. Probe: "Nashville open data" →
  `Nashville Open Data`, source `Nashville GIS`, `orgId=HdTo6HJqh92wn4D8`, url
  `https://datanashvillegov-nashville.hub.arcgis.com`.
  - hub.arcgis.com robots: `Crawl-delay: 60`. It disallows /sites/, /admin/ and similar, but not /api/. One request
    per city is fine.
- **Step 2: list that org's services.** `GET https://www.arcgis.com/sharing/rest/search?q=orgid:<orgId> AND type:"Feature Service" AND (permit OR event OR license)&num=100&f=json`
  - www.arcgis.com robots: `User-agent: *` with nothing disallowed.
  - Results carry `title, owner, url, modified, numViews, extent, access`.
  - Probe: 49 hits for Nashville. They include our `Beer_Permit_Locations_Feature_Layer_view` and "Residential
    Short Term Rental Permits", "Trade Permits", "Building Permit Applications".
  - The `url` is the FeatureServer. `<url>/<layer>?f=json` gives the fields for an auto-mapping (`*_DATE` with
    esriFieldTypeDate → start).
- **Don't use bbox search alone.** It matches global-extent items. Probe: Phoenix bbox + "liquor license" → 14
  hits, 0 local; Denver bbox + "liquor" → 197 hits, mostly student projects and choropleths. The OGC
  `collections/dataset/items?bbox=` has the same problem. Always scope by the official orgId, and keep the owner
  string (e.g. `The_City_and_County_of_Denver`, `NashvilleOpenData`) as evidence.

#### CKAN ✅ shape known, ⚠ robots usually say no

- **Request:** `GET <portal>/api/3/action/package_search?q=<terms>&rows=50` → `result.{count, results[].{name, title, metadata_modified, resources[].{format, url, datastore_active}}}`.
- **robots is the blocker.** data.boston.gov disallows `/api/` and `/datastore/*` (already documented).
  phoenixopendata.com disallows `/api/` and `/datastore/*` too (2026-10-16, see §2.10).
- **Rule for discover:** a CKAN portal whose robots disallows `/api/` is recorded as `blocked_by_robots`. Check
  whether the same dataset is mirrored on a state Socrata/ArcGIS portal, or offered as a plain CSV download outside
  `/api/` (the `csvfile` adapter), and robots-check that URL too.

#### State liquor and business licenses ("openings")

- **The best automated path is the cross-tenant Socrata query** above. State portals with liquor/license data
  found: CO, MO, OR, NY, WA, TX, DE, MD (Montgomery and Prince George's counties). City portals: Dallas, NOLA, KCMO,
  Orlando, Cincinnati, Richmond, Seattle, Chicago, Providence.
- **ArcGIS orgs** cover others (Nashville beer permits).
- **States not on Socrata** need manual research: CA ABC, PA PLCB, GA, AZ DLLC, NC ABC, MA ABCC (local boards),
  FL DBPR (we already use its CSV files). These weren't probed this session, so mark them "unverified" until
  checked.
- **Auto-config rule:** prefer columns named `original_issue_date`, `license_start_date`, `application_date` or
  `submission_date`. Refuse `renewal`/`expiration` as the newness date (ADR-0006). Apply the existing `PII_KEY` drop
  list before any sample is written to a candidate file.

### 2.3 Libraries

**Finding the systems:** the IMLS *Public Libraries Survey* administrative-entity file has system name, service-area
population, address and lat/lon. Take the top 3 systems by service population whose address falls within
`radius_km × 1.5`. (Not fetched this session. It's an annual bulk CSV, so download it once, store it in
`docs/research/`, and cite its version.) Then fetch each system's homepage **once** and fingerprint its outbound
links:

| platform | fingerprint on the library homepage | endpoint | verified 2026-10-16 |
|---|---|---|---|
| **BiblioCommons** | link to `([a-z0-9]+)\.bibliocommons\.com` → that subdomain is the code | `https://gateway.bibliocommons.com/v2/libraries/<code>/rss/events?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&page=N` | ✅ status codes are a classifier: **200 + items**: `kcls` 22 items (no window), `chipublib` 72 KB for one day, 0.8 s. **200 + empty channel**: `sfpl` (catalog on BC, events elsewhere; the `<title>` "Events \| San Francisco Public Library" still confirms the code). **404**: unknown code (`phoenix`, `dclibrary`, `sacramento`, `dallaslibrary`, `houston`). **410** `{"classification":"SiteDisabledError","meta":{"homeLink":"https://sdpl.na5.iiivega.com/"}}`: `sandiego` moved to Vega. **504 after 35 s**: `austin`, `multcolib`, `nypl`, even with a one-day window, so retry later and treat as unknown. Gateway has no robots.txt (404). **Never crawl `<code>.bibliocommons.com`**: it sets `Crawl-delay: 120`. |
| **Communico** | link to `<x>.libnet.info`, or `eeventcaldata` in page JS | `GET <base>/eeventcaldata?event_type=0&req={"private":false,"date":"YYYY-MM-DD","days":1,…}` | ✅ `hcpl.libnet.info` → 13 events/day, fields include `close_registration`, `max_attendee`, `allow_reg`, `location`, `library`. `sjpl.libnet.info` → 200 `[]`. An unknown subdomain answers **302 → google.co.uk** (negative signal). ⚠ **Name collisions:** `hcpl` is *Harford* County (MD), not Harris County (Houston). Match the page `<title>` ("Events - Harford County Public Library") and the branch locations against the city before accepting. robots: only `/results*`, `/sitesearch*`. |
| **LibCal (Springshare)** | `static-assets-us.libcal.com` or a link to `*.libcal.com` | `GET <host>/ical_subscribe.php?src=p&cid=<calendar_id>` (ICS). `cid` comes from `baseCalendarId: N` / `cal_id="N"` in `<host>/calendar` | ✅ `calendar.library.ucla.edu/calendar` → `baseCalendarId: 4759` → ICS with 75 VEVENTs. `rss.php?…&cid=-1` returned an empty channel, so use ICS. **robots:** `User-agent: *` gets `Crawl-delay: 10`. Named crawlers (crawl, crawler, discobot, Yandex…) are fully disallowed; we're not on that list. Respect 10 s. Many public-library LibCal sites are appointments only (`sfpl.libcal.com`), so require ≥1 calendar with future VEVENTs. |
| **Trumba** | `trumba.com/scripts/spuds.js` + `$Trumba.addSpud({webName: "<name>"…})` | `https://www.trumba.com/calendars/<webName>.json?startdate=YYYYMMDD&days=N` | ✅ `washington.edu/calendar/` → `webName: "sea_campus"` → JSON with `eventID,title,startDateTime,startTimeZoneOffset,location,customFields,canceled,openSignUp,pastDeadline,reservationFull,waitingListAvailable`. Unknown webName → 404. robots allows all. |
| **The Events Calendar (WP)** | `GET <site>/wp-json/` → `namespaces` contains `tribe/events/v1` | `<site>/wp-json/tribe/events/v1/events?start_date=…&per_page=50` | ✅ see §2.5 |
| others to fingerprint (no adapter yet) | LibraryMarket/LibraryCalendar (`/events/feed/ical`), Assabet, Evanced, BiblioEvents, Vega Events | — | not probed |

### 2.4 Universities

- **Finding the big ones:** College Scorecard API. Probe:
  `GET https://api.data.gov/ed/collegescorecard/v1/schools?api_key=DEMO_KEY&school.state=AZ&latest.student.size__range=15000..&fields=school.name,school.school_url,school.city,location.lat,location.lon,latest.student.size`
  → 200, 7 schools with URL and lat/lon.
  - It supports `zip=<zip>&distance=<n>mi`, so use the city-hall ZIP and the radius.
  - **Filter online-only and remote campuses** with `school.online_only=0` and a non-empty campus lat/lon inside the
    radius. The AZ probe returned "University of Phoenix-Arizona", "ASU Digital Immersion" and "UA Global Campus"
    (lat/lon in San Diego!).
  - `DEMO_KEY` is rate-limited (api.data.gov documents 30/h and 50/day per IP). Register a free api.data.gov key
    (`DATA_GOV_API_KEY`), which also covers other federal APIs.
  - ⚠ The **Urban Institute Education Data API**, which has the same IPEDS data with a `cbsa=` filter, answered fine
    (`cbsa=38060` → 78 institutions). But `educationdata.urban.org/robots.txt` says `Disallow: /api/`, so **don't use
    it** (§2.10).
- **Calendars:** from `school_url`, probe the common hosts in order and stop at the first hit:

| platform | probe | verified |
|---|---|---|
| **Localist** | `https://calendar.<domain>/api/2/events?pp=1&days=14`, then `events.<domain>` | ✅ `calendar.unc.edu` → `page.{current,size,total,total_items}` and `events[].event.{id,title,url,first_date,last_date,location_name,address,geo,filters,ticket_url,free,…}`. `calendar.gatech.edu` / `events.rice.edu` → 404 (not Localist). `calendar.asu.edu` → 522 (origin down; retry). |
| **LiveWhale** | `https://events.<domain>/live/json/events/max/1` | ✅ `events.rice.edu` → array with `id,gid,group_title,title,url,date_iso,date2_iso,timezone,is_all_day,repeats,is_canceled,is_online,location,…`. `events.emory.edu`, `events.tufts.edu` → 404. `events.ucsd.edu` → 302 (follow once, re-probe). |
| **Trumba** | spud scan of `/<calendar\|events>` pages | ✅ (UW above) |
| **SIDEARM athletics** | `https://<athletics-domain>/calendar.ashx/calendar.ics?sport_id=0` | ✅ `smumustangs.com` → 247 VEVENTs. `uhcougars.com` → 309 VEVENTs, `X-WR-CALNAME`, `X-PUBLISHED-TTL:PT120M`, SUMMARY prefixes `[H]/[A]/[N]/[L]`. `sundevils.com` → 404 (ASU isn't SIDEARM). No robots rule on `/calendar*`. Find the athletics domain from the school homepage's "Athletics" link or Wikidata P856 of the team item. |

Rule: keep only `audience`/type filters equivalent to "open to the public". That's what NYU/UMN use today
(`audience_filter`), which keeps campus noise out of the feed.

### 2.5 Venues

- **Seed list:** the Wikidata venue query we already run (`gotc/pipeline/venue_refs.py`). Add
  `OPTIONAL { ?v wdt:P856 ?site }` to get official websites. Sort by capacity and take the top ~40 per city.
- **Probes per site** (stop at the first hit):

| platform | probe | verified 2026-10-16 |
|---|---|---|
| **carbonhouse** | `<site>/events/rss` → `application/rss+xml` with `xmlns:ev` (`ev:startdate, ev:enddate, ev:location, ev:type`) | ✅ americanairlinescenter.com (Dallas) 94 items. toyotacenter.com (Houston) 69 items. footprintcenter.com → 301 (follow and re-probe). robots had no `/events` rule on any. |
| **The Events Calendar** | `<site>/wp-json/` namespaces ∋ `tribe/events/v1` → `/wp-json/tribe/events/v1/events?start_date=…&per_page=50` | ✅ atlantabg.org (Atlanta Botanical Garden): `total` 89, `total_pages`, events with `start_date, utc_start_date, timezone, venue.{geo_lat,geo_lng}, cost, categories, organizer`. dallasarboretum.org, deepellumtexas.com, downtownsandiego.org → WP but no tribe. |
| **schema.org JSON-LD** | `<script type="application/ld+json">`, walk `@graph`/`itemListElement`/`subEvent` for `@type` containing `Event` | ✅ fingerprint works. thefillmore.com had 25 Events (name, startDate). thecrocodile.com had 3 LD blocks, 0 events. **But thefillmore.com is a Live Nation site; its terms forbid automated collection (diary, session 2). The ToS denylist must run before anything is proposed.** |

- **ToS denylist** (`config/discovery_denylist.yaml`, new): Live Nation / Ticketmaster venue sites (`*.livenation.com`
  and LN-owned house domains, matched by footer/`og:site_name` and by the LN asset CDN), Prekindle, LeagueLab, and
  AEG/AXS until I-092 is resolved. Cloudflare challenge pages are recorded as `blocked`, never retried with
  workarounds.

### 2.6 Parks and city calendars

- **CivicPlus:** `/RSSFeed.aspx?ModID=58&CID=All-calendar.xml` gives an RSS with a `calendarEvent:` namespace
  (`EventDates, EventTimes, Location`).
  - Probe: friscotexas.gov → 200, 30 items. Its robots disallows only admin paths plus `Baiduspider`/`Yandex`
    entirely; `RSSFeed.aspx` is allowed.
  - `/common/modules/iCalendar/iCalendar.aspx?catID=All&feed=calendar` → 404, so the iCal path needs a real
    `catID`, taken from `calendar.aspx` links.
  - Fingerprint: `/RSSFeed.aspx` or `CivicPlus` in the footer.
  - CivicPlus hosts many suburbs and mid-size cities, which matters most for metros 30–100. A small `civicplus`
    RSS adapter (or an `rss_events` mapping) is the missing piece.
- **Other city/parks platforms:**
  - Tribe, Localist and Trumba are the same as above.
  - Granicus/OpenCities and Drupal "Events" views need a JSON-LD check.
  - **ActiveNet** (`anc.apm.activecommunities.com/<org>/…`), RecDesk and Rec1 run registrations (real deadlines!).
    robots.txt on those hosts was a 301 or empty, so **read the ToS manually** before any adapter. Treat them as
    "manual review" candidates.
- **Where to find the parks site:** Wikidata item of "<City> Parks and Recreation Department", or the city domain's
  `/parks` path. Discovery proposes; a human confirms.

### 2.7 Volunteering, leagues, trivia

| source | discovery | verified 2026-10-16 |
|---|---|---|
| **Galaxy Digital** | Guess the tenant slug `<slug>.galaxydigital.com/need/rss/` from the local United Way / volunteer center name, or find the link on that org's site | ✅ `handsontwincities` → `<title>Opportunities on HandsOn Twin Cities`, 15 items. Bad slugs (`volunteerphoenix`, `uwmh`, `zzgotc…`) → **HTTP 200** with `<title>Galaxy Digital: Bad Domain`, so check the title, not the status. robots on galaxydigital.com: marketing paths only. |
| **HandsOn Connect** | Points of Light Global Network affiliate list (manual seed). Fingerprint `handsonconnect` in the HTML + hidden `calendar-search-block-id` | ✅ bostoncares.org/calendar → 5× `handsonconnect`, `getOpportunitiesCalendar`, block id `589` (matches config). |
| **Volo Sports** | `https://www.volosports.com/discover` lists markets (`/discover/<slug>`) | ✅ page lists baltimore, boston, charleston, jacksonville, miami, morristown, new-york-metro-area, philadelphia, washington-dc. Our config also uses `denver` and `los-angeles`, which the page didn't list, so probe `/discover/<candidate-slug>?category=leagues` for each city as well. robots allows all but /rfo /admin /staff. |
| **Team Trivia** | `https://www.teamtrivia.com/sitemap-locations.php` (the site's own sitemap) | ✅ 38 regions, including trivia-in-{atlanta, baltimore-delaware, charlotte, chicagoland, dallas-fort-worth, denver, houston, jacksonville-fl, kansas-city, miami, nashville, phoenix-tempe, raleigh-…, san-diego, st-louis, tampa, washington-d-c, western-ny, western-pa, ne-ohio, virginia, michigan}. Map region → city by name/state. |
| **Challenge Entertainment** | **No mapping needed.** The national feed (`/wp-json/ce/v1/shows`, 857 KB, 933 shows) carries `venue.latitude/longitude`, so filter by radius. | ✅ 64 `metro-*` classes, including san-antonio 88, central-indiana 66, dallas-ft-worth 46, new-orleans 37, houston 27, memphis 21, tampa 21, dc 15+6, austin 15, denver 12, orlando 10, milwaukee 9, oklahoma-city 6, phoenix 5, kansas-city 5, charlotte 2. Fetch once per run and share across cities (§4.5). Today each city unit refetches it. |
| **RunSignup** | ZIP + radius per city (already designed). ZIP from the Census geocoder of the city-hall address | (gated on caller registration) |

### 2.8 `gotc discover <city>`: design

```
gotc discover phoenix [--cbsa 38060] [--families socrata,arcgis,library,university,venue,parks,volunteer,leagues]
                      [--budget-requests 400] [--out config/cities/_candidates/phoenix.yaml] [--verify]
```

**Inputs:** the city skeleton (§1 row: slug, name, state, center, radius, tz, cbsa). Optionally an operator-supplied
seed list of URLs, e.g. the parks site or the volunteer center.

**Probe stages.** All requests go through `PoliteClient`, with robots checked first, a host budget and a
discovery-specific cache. The approximate request budget is ~250–400 requests per city, spread over 30–60 minutes
because of Crawl-delays.

1. **Context:** Census geocoder (city hall → ZIP, county FIPS); NWS points (tz cross-check); OMB principal cities
   (aliases).
2. **Open data:** Socrata cross-tenant queries (`special events`, `events`, `permits`, `liquor license`,
   `business license`, `farmers market`, `park events`) filtered to the city, county and state; data.gov `/search`
   (≤6/min); ArcGIS Hub site → orgId → org-scoped search; CKAN only if robots allows `/api/`.
3. **Institutions:** IMLS (libraries, top 3), College Scorecard (≥10k students, top 6), Wikidata venues (top 40 by
   capacity, with P856), plus the parks and volunteer seeds.
4. **Fingerprint:** one GET of each homepage (or `/events`, `/calendar`). Regex table per platform (§2.3–2.7), then
   one endpoint probe per detected platform with a 14-day window.
5. **National feeds:** Challenge (geo filter), Team Trivia sitemap, Volo market probe, SIDEARM for each university.

**Scoring** (0–1, written into the candidate):

| signal | weight | how |
|---|---|---|
| endpoint works | 0.30 | 2xx, parses with the target adapter's `parse`, ≥ `expect_min_records` future records in 14–60 days |
| geo fit | 0.20 | share of parsed records inside `radius_km` (geocoded/geo fields) or whose locality ∈ aliases |
| officialness | 0.15 | publisher is the city/county/state/library/university itself (.gov/.edu, orgId owner, Socrata domain) |
| freshness | 0.10 | `data_updated_at`/`modified` < 14 days; feed has items starting within 7 days |
| category value | 0.15 | fills a category the city lacks (from §3 gaps) and has registration/deadline fields (Communico `close_registration`, Trumba `pastDeadline`, Galaxy shifts) |
| novelty | 0.10 | not a duplicate host/dataset of an existing unit; sample titles don't fuzzy-match >50% of existing events |

**Hard excludes, not scored:**
- robots disallow
- denylist / ToS
- Cloudflare challenge
- requires a key we don't have (recorded as `needs_key`)
- PII-only datasets
- non-US tenants

**Output** (`config/cities/_candidates/<slug>.yaml`, never loaded by `gotc run` until promoted):

```yaml
city: phoenix
generated_at: 2026-10-16T20:00:00Z
candidates:
  - confidence: 0.86
    unit:                                  # paste-ready into config/cities/phoenix.yaml
      id: phoenix_mesa_library_events
      adapter: bibliocommons
      name: Mesa Public Library events
      data_type: events
      enabled: false
      params: { library: mesa, horizon_days: 14, venue_label: Mesa Public Library, default_category: arts.books }
    evidence:
      discovered_via: "imls:AZ0016 homepage link → mesa.bibliocommons.com"
      probe_url: https://gateway.bibliocommons.com/v2/libraries/mesa/rss/events?startDate=…&endDate=…
      probe_status: 200
      robots: { host: gateway.bibliocommons.com, checked_at: …, verdict: no_robots_txt }
      sample: { future_records: 41, in_radius: 1.0, titles: ["Teen Anime Club", "Storytime", "…"] }
      fills: [arts.books, learning.class]
      score: { works: 0.3, geo: 0.2, official: 0.15, fresh: 0.1, value: 0.06, novelty: 0.05 }
  - confidence: 0.0
    excluded: robots_disallowed
    unit_hint: { adapter: ckan, base_url: https://www.phoenixopendata.com }
    evidence: { robots: "Disallow: /api/" }
```

**Review and verify:**
1. An agent or human reads the candidates (sorted by confidence), picks or edits them, and sets `category_map` /
   filters.
2. `gotc discover phoenix --verify` copies the chosen units into a **scratch DB** (`--db data/discover/phoenix.db`)
   and runs `gotc run --city phoenix --source <id> --force --no-geocode` for each. It writes a per-unit report:
   valid/rejected, reject reasons, top categories, geofence drops and duplicate rate against already-promoted units.
3. Promote: the units move into `config/cities/phoenix.yaml`, fixtures are recorded with
   `gotc record <unit> --trim 5`, and each source gets a row in `docs/SOURCES.md` with its robots/ToS stance.
4. `gotc gate phoenix` (§3) decides `enabled: true`.

Everything stays YAML, so promoting a candidate needs no code.

---

## 3. Per-city quality bar ("go-live gate")

**Today's 10 cities (measured from the current exports):**

| city | events | next 14 d | top-level cats | top cat share | top source share | events with coords | published deadlines |
|---|---|---|---|---|---|---|---|
| Austin | 1,026 | 441 | 15 | music 37% | 23% | **77%** | **1** |
| Boston | 1,567 | 1,159 | 14 | volunteer 35% | 34% | 90% | 91 |
| Chicago | 1,806 | 1,333 | 14 | arts 33% | **53%** (chipublib) | 94% | **0** |
| Denver | 970 | 492 | 11 | family 23% | 21% | 94% | 99 |
| Los Angeles | 886 | 444 | 12 | arts 26% | 34% | 83% | 50 |
| Miami | 831 | 585 | 15 | arts 26% | **58%** (mdpls) | **79%** | 17 |
| Minneapolis | 872 | 454 | 15 | music 27% | 30% | 84% | 3 |
| Nashville | 878 | 584 | 13 | volunteer 46% | 46% | 100% | **1** |
| NYC | 3,040 | 1,360 | 14 | food_drink 36% | 32% | 89% | 122 |
| Seattle | 1,306 | 930 | 14 | music 33% | 21% | 97% | 7 |

**Proposed gate** (`gotc gate <slug>` computes it, `index.json` publishes it). **Hard** criteria block `enabled:
true`. **Soft** criteria publish a visible "thin coverage" note.

| # | criterion | threshold | kind |
|---|---|---|---|
| G1 | healthy enabled units | ≥ 8, from ≥ 4 distinct adapter families, and ≥ 1 "official" (gov/library/university) | hard |
| G2 | events starting in the next 14 days | ≥ 250 (≥ 150 if MSA < 1.5 M) | hard |
| G3 | top-level categories with ≥ 3 events in the next 30 days | ≥ 10 of 15 | hard |
| G4 | newcomer pillars in the next 30 days | music ≥ 20, trivia/games ≥ 5, volunteer ≥ 5, outdoors/fitness ≥ 10, leagues ≥ 1 (live or curated) | 4 of 5 hard, 5 of 5 soft |
| G5 | published (non-derived) deadlines in the next 60 days | ≥ 1 hard, ≥ 10 soft | hard/soft |
| G6 | category balance | no top-level category > 60% (hard), > 45% (soft) | hard/soft |
| G7 | source balance | no single unit > 60% of events (hard), > 50% (soft) | hard/soft |
| G8 | geocode coverage (events with lat/lon, excluding online) | ≥ 80% hard, ≥ 90% soft | hard/soft |
| G9 | recency | ≥ 90% of events come from units within their SLA; no enabled unit without a success in 48 h | hard |
| G10 | stability | ≥ 3 consecutive green runs spanning ≥ 48 h, reject rate < 10%, geofence drops < 5% | hard |
| G11 | duplicates | post-cluster duplicate-title-same-day rate < 3% | soft |

Against the current data:
- Chicago (0 deadlines → G5) and Miami (58% from one library → G7 soft) would show thin-coverage notes.
- Austin (77% geocoded) and Miami (79%) fail G8 hard. That's correct: it's the known Census-batch gap.
- Nashville (1 deadline) passes G5 hard and fails G5 soft.

So the thresholds are calibrated to flag the problems we already know about without blocking everything.

**Displaying coverage honestly:**
- **City picker:** a "Live" or "Beta" chip, plus "N sources · updated 23 min ago". Beta cities are listed, but under
  a "Coming soon (thin coverage)" heading.
- **Per-city coverage strip** (top of the dashboard, collapsible): one pill per pillar, in three states:
  - ✓ strong: "Music · 237 this month"
  - ◐ thin: "Leagues · 6, all curated"
  - ✕ none: "Openings · we have no license data for this city"
  The ✕ state links to "Know a source? Tell us."
- **Empty states name the gap.** For example, "No published registration deadlines in Chicago yet. Race deadlines
  arrive when RunSignup access is approved." Never just an empty list.
- **Coverage page:** a matrix of cities × pillars, built from the same `coverage` block, next to the existing Health
  page.
- **Export:** `index.json.cities[].coverage = {gate: "live"|"beta", criteria: {G1: {value, threshold, pass}, …},
  pillars: {...}}`. The UI never computes coverage itself, so the contract test covers it.
- **Regression:** a live city that fails a hard criterion for more than 72 h shows a banner. It's demoted to Beta
  automatically only after 7 days, so one bad week doesn't flap the picker. Each transition is logged to
  health_log.

---

## 4. Capacity at 50 and 100 cities

### 4.1 What we measured today (10 cities, 196 units, 154 enabled)

| metric | value | source |
|---|---|---|
| events | 13,212 | `events` table |
| fetches in the first full day | 901 non-cached requests, 160 MB raw bodies, mean 575 ms each | `raw_fetches` |
| run 38 (23 units fetched + build/export of 10 cities) | 289 s | `runs` |
| build/export only, 10 cities (runs 21–23, 1 trivial unit each) | 60–86 s → **~7.5 s per city** (~6 ms/event) | `runs` |
| fetch time per unit, all-in (incl. throttles, multi-page) | ~9 s ((289 − 75) / 23) | runs 38 |
| full DB | 97 MB: `events` 52 MB, `source_records` 35 MB | `dbstat` |
| slimmed state (`slim_state.py`) | 44 MB → **6.2 MB gzip -9** | measured now |
| `data/raw` | 28 MB (gzip) after ~1 day | `du` |
| exported data | 35.6 MB raw: cards 1.47–5.0 MB/city, details 0.69–2.4 MB. NYC cards gzip 462 KB, details 223 KB; Austin cards gzip 236 KB. **~1.8 KB per event card raw**, ~10:1 gzip | `web/public/data` |
| geocode cache | 1,485 queries (≈150/city): census 425, census_batch 170, nominatim 494, none 394 | `geocode_cache` |

### 4.2 Platform limits (verified 2026-10-16 on docs.github.com)

- **Actions minutes.** "GitHub Actions usage is free for self-hosted runners and for public repositories that use
  standard GitHub-hosted runners." A private repo on the Free plan gets **2,000 min/month**, and **we already use
  ~4,700 (§4.4)**. Making the repo private would break the hourly refresh on day 13 of each month.
- **Job and run limits.** Jobs: 6 h max. 20 concurrent jobs (Free). Matrix: ≤ 256 jobs per run. `GITHUB_TOKEN`:
  1,000 API requests/hour/repo.
- **Cache.** 10 GB per repo, LRU eviction, not raisable by support.
- **Schedule.** Can be delayed under load. Shortest interval 5 min. **Disabled automatically after 60 days without
  repository activity** in a public repo. Because the bot only force-pushes the orphan `pipeline-state` branch, it's
  unclear whether that counts. Add a monthly keep-alive (a small commit to main or a `workflow_dispatch` ping) and a
  HEALTH.md check on "last scheduled run age".
- **Pages.**
  - Published site ≤ 1 GB.
  - Soft bandwidth limit 100 GB/month.
  - The "soft limit of 10 builds per hour … doesn't apply if you build and publish with a custom GitHub Actions
    workflow". We use one, so staggered multi-deploys are allowed. Still, aim for ≤ 1–2 deploys/hour.
  - Deployments time out after 10 minutes.
  - Git push: files over 50 MB warn and over 100 MB are rejected. That matters for `gotc.db.gz` on the state branch.

### 4.3 Third-party rate limits at scale

| service | published limit | today | 50 cities | 100 cities | action |
|---|---|---|---|---|---|
| **Nominatim** | 1 req/s absolute max. Results must be cached. **"Scripts running longer than a day, or run at regular intervals, are limited to 4 requests per minute"**. Single thread, single machine, no distributed scripts | 1.1 s interval, up to 40 lookups/run (`GOTC_GEOCODE_BUDGET`) → **~55 req/min bursts, above the 4/min rule** | onboarding 40 cities × ~150 queries × ~35% Nominatim share ≈ 2,100 lookups | ≈ 5,000 | **Fix now:** set `host_intervals["nominatim.openstreetmap.org"] = 15.0` and run Nominatim in one lane only (never in matrix shards). At 4/min a cold city's ~50 Nominatim lookups take ~13 min, and a 40-city onboarding takes ~9 h, spread over runs. Route US addresses to the Census batch geocoder first. |
| **Census geocoder** | no published rate limit; batch ≤ 10,000 records/file | single + batch | ~6,000 cold queries → 1 batch file | ~15,000 → 2 files | batch-first, as planned (STATUS "Next" #4). Raises coverage for Austin/Miami-type gaps. |
| **NWS api.weather.gov** | not public ("typically clears within 5 seconds"). UA with contact required | 1 forecast/city per 3 h TTL | 400 req/day | 800 req/day | fine. Cache `/points` grid forever. Put a contact address in the UA (`GOTC_USER_AGENT` should include an e-mail). |
| **Wikidata WDQS** | 60 s query time per minute per UA+IP, 5 parallel/IP, 30 errors/min, 60 s timeout. UA policy enforced | 1 SPARQL/city/week | 50/week | 100/week | fine. ⚠ `query.wikidata.org/robots.txt` says `Disallow: /sparql`. `venue_refs.py` uses `respect_robots=False` because it's a documented API, like Socrata/ArcGIS. **Record this exception in SOURCES.md**, which doesn't list it today. |
| **Socrata (SODA)** | no numbers published. With app token: "we do not throttle … unless abusive". Without: a much lower shared per-IP pool, 429 on throttle | 17 units, keyless; intermittent 503s seen | ~80 units | ~160 units | **set `SOCRATA_APP_TOKEN` before 50 cities.** GitHub runner IPs are shared with everyone else's keyless jobs. |
| **Ticketmaster** | 5,000 calls/day, 2–5 req/s | gated; config estimates ~12 calls/city/run × 4 runs/day = 48/city/day | 2,400/day (48%) | **4,800/day (96%)** | at 100 cities: 12 h cadence for metros outside the top 25, or a single nationwide geo-paged sweep. Ask for a quota raise. |
| **SeatGeek** | ~100 req/min | gated, up to 20 pages/city/run, 6 runs/day | ≤ 6,000/day | ≤ 12,000/day | fine per minute; spread across the hour. |
| **BiblioCommons gateway** | none published; 504s after 35 s on big systems | 6 units | ~40 | ~80 | one-day windows, ≥ 2 s apart, honest `timeout` health state |
| **RunSignup** | ≤ 2 concurrent (ToS) | gated | 50 cities × ≤ 5 pages/day | 500/day | stay sequential, 2 s apart |
| **hub.arcgis.com / data.gov** | Crawl-delay 60 / 10 | discovery only | discovery only | discovery only | discovery runs out of band, never in the hourly job |

### 4.4 Runtime and minutes

Model: hourly run = **overhead** + **fetch** (units due this hour × 9 s) + **build** (cities rebuilt × 7.5 s) +
**export** + **state persist**.
- Overhead covers checkout, uv sync, DB restore, npm ci + vite build, Pages upload/deploy and issues. It's ~4 min,
  an estimate: CI has never run successfully yet (Pages isn't enabled).
- Units fetched per day ≈ enabled units × 1.1, which reflects the cadence mix (24 h dominant, some 4–12 h, some 48–168 h).
- Assumes ~16 enabled units per city (today's ratio) and ~1,100 events per city on average. Smaller metros pull the
  average down from today's 1,321.

| | today (10) | 50, monolithic | 100, monolithic | 100, sharded + incremental (§4.5) |
|---|---|---|---|---|
| enabled units | 154 | ~800 | ~1,600 | ~1,600 |
| fetch per hourly run | 7 units ≈ 1 min | 37 units ≈ 5.5 min | 73 units ≈ 11 min | 8 shards × ~9 units ≈ 1.4 min wall |
| build/export per run | 10 × 7.5 s ≈ 1.3 min | 50 × 7.5 s ≈ 6.3 min | 100 × 7.5 s ≈ 12.5 min | only touched cities (~40%) ≈ 0.6 min per shard |
| state slim + gzip + push | ~0.7 min (44 MB) | ~2.5 min (~185 MB slim) | ~4 min (~300 MB slim) | ~0.3 min per shard (per-city files) |
| **wall time per run** | **~7 min** | **~19–20 min** | **~32–34 min** | **~9–10 min** (longest shard + publish) |
| **billed minutes/month** (×720 runs) | ~4,700 | ~14,000 | ~24,000 | ~30,000 (per-job overhead outweighs the savings) |
| cost (public repo) | $0 | $0 | $0 | $0 |
| fits the 25-min `--max-minutes` / 45-min timeout? | yes | yes, but a cold-geocode or Ticketmaster day pushes it | **no:** units starve, runs back up behind `concurrency: refresh` | yes |

**Monolithic stops working at ~60–70 cities.** At that point a run passes ~25 min, the `--max-minutes 25` budget
starts deferring due units, and freshness SLAs slip. Billed minutes are not the constraint (they're free); wall
time, DB file size and site upload size are.

### 4.5 Payloads, state and storage at scale

**Payloads (estimate: 1.8 KB per card plus ~0.9 KB of details per event):**
- 50 cities × ~1,100 events → cards ~100 MB + details ~50 MB ≈ 150 MB per deploy.
- 100 cities ≈ 300 MB. That's under the 1 GB site cap, but it means re-uploading a 300 MB artifact every hour
  against a 10-min deploy timeout.
- First paint stays OK: Pages gzips, and NYC cards are 462 KB.

**Bandwidth (estimate):** a first visit costs index (2.4 KB gz) + one city's cards (250–460 KB gz) ≈ 0.35 MB. The
100 GB/month soft cap allows ~285k first visits per month. Pages sets short cache TTLs, so hourly repeat visitors
re-download. Past ~150k visits a month, put the data on a CDN with free egress (Cloudflare R2/Pages), leaving the
app shell on GitHub Pages.

**State (estimate, linear in events):**
- Full DB: ~400 MB at 50 cities, ~650 MB at 100.
- Slimmed: ~185 / ~300 MB.
- gzip: **~26 / ~42 MB**, before price snapshots. Once Ticketmaster and SeatGeek are keyed, `price_snapshots` grows
  by roughly 5k priced events × 24 snapshots/day ≈ 3.6 M rows/month at 50 cities. Without downsampling, the single
  `gotc.db.gz` crosses GitHub's 50 MB warning within weeks and its 100 MB hard limit soon after.

**Raw payloads:** ~28 MB/day of gzip today becomes ~140 MB/day at 50 cities and ~280 MB/day at 100.
- At the documented 30-day retention, that's 4.2 / 8.4 GB, too close to the 10 GB Actions cache.
- Worse, `key: raw-${{ github.run_id }}` saves the **whole directory as a new cache entry every hour**, so at 50
  cities every run uploads gigabytes.

### 4.6 Proposed architecture changes (in order)

1. **Nominatim compliance (now, at any scale).**
   - 15 s interval on Nominatim; a budget of ≤ 4 lookups/min.
   - Census batch first. Nominatim only for addresses Census misses.
   - A single geocoding lane: shards never call Nominatim; they enqueue misses into `geocode_queue`.
2. **Split state.**
   - **Per-city DB files:** `state/cities/<slug>.db.gz` holds source_records, events (slim), event_members, venues,
     price_snapshots and unit_health for that city's units.
   - **Global DB:** `state/global.db.gz` holds geocode_cache, venue_refs, weather_cache, runs, global units and fact
     checks.
   - Each file is about 0.3–0.6 MB gz. The `pipeline-state` branch keeps a single force-pushed commit with ~101
     files (~45 MB total), so no file gets anywhere near 100 MB.
   - DB code change: `Database(path_for(city))`. Cross-city readers (health report, reliability) iterate files or
     read the per-city `health.json` fragments.
3. **Sharded matrix + publish job.**
   - `prepare` job: list due cities and pack them into N ≈ ceil(cities / 12) shards, balanced by due-unit seconds
     from last run's timings. Output the matrix JSON.
   - `shard` job (matrix, `max-parallel: 8`): restore its city DBs + a read-only global DB → `gotc run --cities a,b,c
     --no-nominatim --no-export-index`. Upload an artifact: changed city JSONs, `health/<slug>.json` fragments,
     updated city DBs, geocode deltas (Census results) and `geocode_queue` additions.
   - `publish` job (needs: shard):
     - merge the geocode deltas into global.db (`INSERT OR IGNORE`)
     - run the Nominatim lane for ≤ 10 min at 4/min (≤ 40 lookups)
     - write `index.json` and `health.json` from the fragments
     - overlay changed city files onto the previous site data
     - vite build and deploy Pages once
     - commit all state files in one force-push, so shards never race on git
   - The ~20 concurrent-job limit allows 8 shards plus prepare/publish with headroom.
4. **Incremental builds and exports.**
   - Rebuild a city only when (a) any of its units changed `content_hash` this run, (b) its last build is older than
     6 h (so events rolling into "past" and "this weekend" stay correct), or (c) its config/taxonomy hash changed.
   - Export writes a city file only when the feed hash, excluding `generated_at`, changed.
   - Move `stale` to the client: the UI already gets `last_success_at` and `sla_hours`, so per-hour staleness no longer
     dirties every file.
   - Expected: ~30–40% of cities rebuilt per hour at 50–100 cities, which is about 8× less build CPU.
5. **Per-city payload budget.**
   - `cards/<slug>/now.json` = the next 14 days, budget ≤ 1.5 MB raw (≤ 250 KB gz).
   - `cards/<slug>/w<ISO-week>.json` for days 15–180, lazy-loaded when the user scrolls or filters ahead.
   - `plan.json` for leagues, cons and faires (the 400-day horizon).
   - `details/<slug>/<bucket>.json` sharded by id hash (16 buckets), so opening one drawer doesn't pull NYC's 2.4 MB.
   - When `now.json` goes over budget: cap any single unit at 35% of the window's cards (G7 in reverse), and collapse
     repeats into `series_dates` before dropping anything. Count what was dropped in `index.json`, never silently.
6. **Shared national fetches.** A `global` prepare step fetches the one-payload national feeds once per run
   (Challenge 0.9 MB, UpcomingCons, Ticketmaster/SeatGeek nationwide sweeps if we move to them) and hands the raw
   body to shards as an artifact. Today Challenge is fetched once per city.
7. **Raw payload retention in CI.**
   - Cache only the newest payload per unit (what replay needs), keyed `raw-<shard>-<week>` and restored by prefix:
     ~1 entry per shard per week instead of 24 full copies a day.
   - Keep 7 days in CI. The full 30-day history stays a local/dev feature.
   - Optionally put weekly tarballs on a GitHub Release (≤ 2 GB per asset).
8. **Price snapshot downsampling.** Hourly for 72 h, then daily min/median/max per event, then delete after the
   event. That bounds `price_snapshots` to O(live priced events × ~100).
9. **Schedule tiers and staggering.**
   - Tier A (top 25 metros, or ticket-price units): every hour.
   - Tier B: every 3 h at a fixed minute offset per shard (`cron: "17 * * * *"` plus `if: hour % 3 == shard % 3`).
   - Discovery (`gotc discover`) and the weekly Wikidata/IMLS syncs run in a separate nightly workflow, so polite
     Crawl-delays never eat the hourly budget.
   - Monthly keep-alive against the 60-day schedule auto-disable.

Rough effort: 1 and 7 are small. 2–3 is the real project (≈ 2–3 sessions, mostly Database plumbing and the
workflow). 4 and 5 are 1 session each, and 5 needs a schema bump plus web changes. Do 1 now, 2–4 before city ~40,
and 5 before NYC cards pass ~8 MB raw (they're at 5.0 MB today).

---

## 5. Idea candidates

`title | area | value 1-5 | effort 1-5 | why`

1. Backtest `gotc discover` on the 10 live cities | discovery | 5 | 2 | Running discovery blind on cities we built by hand gives measured recall and precision per family before we trust it on 40 new metros, and it will likely surface missed sources (Chicago `xgse-8eg7`, `38sz-xyf4` on the first probe).
2. Nominatim 4-req/min compliance + single geocode lane | pipeline/geocode | 5 | 1 | OSMF policy limits recurring scripts to 4/min; we burst ~55/min. It's a policy violation at 10 cities and an IP ban risk at 50.
3. Per-city state files on the pipeline-state branch | pipeline/storage | 5 | 3 | The single gz DB reaches ~26–42 MB before price history and approaches GitHub's 100 MB file limit. Per-city files also make sharding and `gotc forget city` trivial.
4. Sharded matrix refresh + single publish job | ci | 5 | 3 | Monolithic runs pass 25 min at ~60–70 cities. Sharding keeps wall time ~10 min at 100 cities, and the minutes stay free on a public repo.
5. Incremental build/export with client-side staleness | pipeline/export | 4 | 2 | Every city is rebuilt and re-exported hourly even when nothing changed. Hash-gated builds cut build CPU ~8× and make deploys smaller.
6. `coverage` block + Live/Beta gate in index.json | product/honesty | 5 | 2 | Makes thin cities honest ("no license data here") instead of quietly sparse. Gives agents a single number to drive source hunting.
7. Week-sharded card files (`now.json` + `w<week>.json`) | web/payload | 4 | 3 | Keeps first paint ≤ 250 KB gz for any city regardless of how many sources we add. NYC is 5 MB raw today.
8. CivicPlus calendar RSS adapter | adapters | 4 | 2 | CivicPlus runs city and parks calendars for many suburbs and mid-size cities (metros 30–100). The RSS is robots-allowed and structured (`calendarEvent:` namespace), and Frisco returned 30 items.
9. LibCal ICS + Communico discovery fingerprints | discovery/libraries | 3 | 2 | Both verified keyless (UCLA cid 4759 → 75 events; Communico has `close_registration` = real deadlines). They need name and location matching (Harford ≠ Harris) to avoid wrong-city tenants.
10. College Scorecard–driven university + SIDEARM discovery | discovery/universities | 4 | 2 | One keyed query per city finds the ≥10k-student campuses (with online-only filtering). Localist/LiveWhale/SIDEARM probes then verified on UNC, Rice, SMU and Houston. Replaces the Urban API, whose robots disallows /api/.

---

### 2.10 Probe log and two robots slips

- **Probes, all 2026-10-16:**
  - api.us.socrata.com catalog: 5 requests
  - catalog.data.gov: 6, at 10 s spacing
  - hub.arcgis.com: 3
  - www.arcgis.com search: 6
  - gateway.bibliocommons.com: 15
  - libnet.info: 6
  - LibCal: 6, at ≥10 s
  - Trumba: 2
  - Localist/LiveWhale: 8
  - carbonhouse: 5
  - WP `/wp-json`: 7
  - JSON-LD homepages: 5
  - Galaxy Digital: 4
  - bostoncares.org: 1
  - Volo: 1
  - Team Trivia sitemap: 1
  - Challenge: 1
  - SIDEARM: 3
  - CivicPlus: 2
  - api.weather.gov: 1
  - Census geocoder: 1
  - College Scorecard (DEMO_KEY): 1
  - www2.census.gov CBSA CSV: 1
- **Two probes were sent before robots was read, and both turned out disallowed.** Each was a single request and
  will not be repeated:
  - `www.phoenixopendata.com/api/3/action/package_search` (robots: `Disallow: /api/`)
  - `educationdata.urban.org/api/v1/...` (robots: `Disallow: /api/`)

  `gotc discover` must make the robots check structural (PoliteClient default), not a step the operator remembers.
  That's the lesson recorded here.
- **Not probed:** IMLS PLS file, ActiveNet/RecDesk/Rec1 ToS, state ABC portals outside Socrata, data.gov spatial
  filters. Each is marked "unverified" in the text above.
