# Ticketing and events APIs: research notes

Researched on 2026-10-15 for GetOffTheCouch. The goal is a US city events dashboard with live prices, "% left", attendance estimates and register-by dates.

**How sure each claim is.** Every claim carries one of these tags:

- **[V-doc]**: I read it in official docs or terms fetched today.
- **[V-probe]**: I saw it in a live keyless or fake-key `curl` today. The exact error bodies are below.
- **[K]**: prior knowledge that I could not re-verify today because the docs are login-gated, blocked by bot protection (DataDome or Cloudflare), or rendered only with JavaScript. Treat [K] as a lead to check, not a fact.

Doc-derived JSON shapes (not live data) are in `docs/research/samples/`.

---

## 0. TL;DR recommendations

| Source | Access | Cost | Verdict | Why |
|---|---|---|---|---|
| **Ticketmaster Discovery v2** | Self-serve API key | Free | **USE (P0)** | Self-serve key; 5k calls/day. Has `priceRanges` (when present), `dates.status.code`, `sales.public/presales` (good for "on sale at" deadlines) and an affiliate link via Impact. |
| TM Inventory Status v1 | Email for approval | Free, by approval | **Apply, then stub** | The only legit source of `FEW_TICKETS_LEFT` / `TICKETS_NOT_AVAILABLE` plus hourly-refreshed face-value min/max. "Authorized clients only." |
| TM Commerce / Partner API | Partner only | n/a | **Reject** | "Typically restricted to a select few business partners." |
| **SeatGeek Platform** | `client_id` (portal now login-gated) | Free | **USE once a key arrives (P0); stub until then** | The best legit resale signal: `stats.lowest_price`, `average_price`, `listing_count`, etc. Snapshot it over time to build price history and supply trend. |
| **Meetup GraphQL** | OAuth client | Free (Pro status unclear) | **USE (P0)** | `eventSearch(filter:{query,lat,lon,radius})` plus `rsvps.yesCount`, `waitlistCount`, `maxTickets`, `feeSettings` and **`attendanceForecast{expected,lowerBound,upperBound,confidenceLevel}`**. This maps directly to our attendance-with-confidence card. |
| **Eventbrite v3** | Private token | Free | **USE, narrow scope (P1)** | No search since 2019-12-12. Usable only by event, organizer or venue ID. Seed it from a curated list of local organizers, or from IDs discovered on other sources. |
| PredictHQ | Paid, trial only | $$$ | **Stub, apply for trial** | Best attendance data (`phq_attendance`, `rank`, `local_rank`, `predicted_event_spend`). No free tier; licensing is enterprise. |
| JamBase Data | Free dev tier | $0 non-commercial; $500+/mo | **USE on the Developer tier for music (P2), behind a flag** | Non-commercial free tier (1,000 calls/mo, 6-month window, attribution required). |
| Vivid Seats | Impact affiliate | Commission | **Affiliate deep links only** | No public feed or API is advertised. |
| StubHub | OAuth API, seller/partner-oriented | n/a | **Stub; apply** | Catalog API has `min_ticket_price` but needs OAuth credentials that StubHub issues by approval. |
| TickPick | Affiliate "coming soon" | 4–5% | **Stub / watch** | The affiliate page promises an "API or custom widgets" but documents nothing. |
| Bandsintown | `app_id` | Free | **Reject for aggregation** | Terms limit use to artists or people working for them and prohibit mixing with third-party content "without distinction." |
| Songkick | Paid license | License fee | **Reject (for now)** | "Not approving API requests for … hobbyist purposes." A license fee is required. |
| DICE | Partner API (promoters' own events) | n/a | **Reject** | No public discovery API. Use DICE links when another source references them. |
| AXS | Partner only | n/a | **Reject** | No public discovery API (site 403s to bots). |
| Resident Advisor | Undocumented GraphQL | n/a | **Reject** | Terms §4.4 ban automated extraction for commercial use or without written authorization. |
| DoStuff (Do312/Do512…) | None public | n/a | **Reject / partner outreach** | No public API (site 403 to bots). Worth a partnership email later. |
| AllEvents.in | Sales-gated trial | Unpublished | **Stub; low priority** | "Request Trial Access" form. Large aggregator, but quality and dedup are unknown. |
| Yelp Events | Bearer key, paid plans | $229+/mo after 30-day trial | **Reject (cost), maybe trial** | The `/v3/events` docs still exist, but Yelp's paid plans start at $229/mo. |
| Google Events (via SerpApi) | API key | 250 free searches/mo; $25/mo for 1k | **Discovery aid only, not a display source** | We would be re-displaying scraped Google results. Use it to *discover* events and canonical ticket links, then fetch the details from the primary source. |
| setlist.fm | `x-api-key` | Free non-commercial | **Optional enrichment** | Past setlists only, no future events. Good for "what will they play" flavor text. |

---

## 1. Ticketmaster

### 1a. Discovery API v2 [V-doc, V-probe]

- **Base:** `https://app.ticketmaster.com/discovery/v2/`
- **Event search:** `GET /events.json?apikey=KEY&...`
- **Event detail:** `GET /events/{id}.json`
- **Other endpoints:** `/venues.json`, `/attractions.json`, `/classifications.json`, `/suggest.json`, `/events/{id}/images.json`.
- **Auth:** an `apikey` query parameter. Register free at developer.ticketmaster.com; per Getting Started, the key works immediately for Discovery (and nominally Commerce).
- **Limits:**
  - The Discovery docs say 5,000 calls/day and 5 req/s. The FAQ says "2 requests per second and 5,000 per day," so **design for 2 rps**.
  - Exceeding the quota returns 429.
  - Headers: `Rate-Limit`, `Rate-Limit-Available`, `Rate-Limit-Over`, `Rate-Limit-Reset`.
  - Quota increases are granted case by case after a ToS, branding and display review. The FAQ steers high-volume users to the **Discovery Feed** (bulk file).
- **Deep paging:** only items where `size * page < 1000` can be retrieved, so **slice queries by date window** (for example one day at a time per DMA) to stay under 1,000.
- **Useful parameters:**
  - Location: `city`, `stateCode`, `countryCode=US`, `postalCode`, `geoPoint` (geohash), `radius` with `unit=miles`, `dmaId`, `marketId`.
  - Dates: `startDateTime`, `endDateTime` (ISO, Z), `onsaleStartDateTime`, `onsaleEndDateTime`.
  - Classification and other filters: `classificationName`, `segmentId`, `genreId`, `source`, `includeTBA`, `includeTBD`, `includeTest`.
  - Sorting and paging: `sort=date,asc`, `size` (max 200), `page`.
- **Key event fields** (see `samples/ticketmaster_events_doc_shape.json`):
  - `id`, `name`, `url` (the buy link), `images[]`
  - `dates.start.dateTime` / `localDate` / `localTime`, `dates.timezone`
  - `dates.status.code` (enum `onsale|offsale|canceled|postponed|rescheduled`)
  - `sales.public.startDateTime` / `endDateTime`, `sales.presales[]`. These give us **"on sale at" and "presale ends" deadlines**.
  - `priceRanges[]{type,currency,min,max}`: **often absent**. Face value, typically excluding fees.
  - `ticketLimit.info`: free text such as "There is an 8 ticket limit." This is a **per-order cap, not inventory**. It is not a "% left" signal.
  - `accessibility.info`, `products[]` (parking/upsells), `seatmap.staticUrl`, `classifications[]`, `promoter`
  - `_embedded.venues[]`: `location.latitude` / `longitude` as strings, `address.line1`, `city.name`, `state.stateCode`, `postalCode`, `timezone`, `markets`, `dmas`, `upcomingEvents`.
  - `_embedded.attractions[]`: includes `externalLinks.spotify` / `musicbrainz`, which help entity resolution.
- **Availability / inventory:** **none in Discovery.** Docs mention filtering by "availability," but no inventory or seat-count fields are documented. `Rate-Limit-Available` is the API quota, not tickets.
- **Errors observed today:**
  - No key → `401 {"fault":{"faultstring":"Failed to resolve API Key variable request.queryparam.apikey","detail":{"errorcode":"steps.oauth.v2.FailedToResolveAPIKey"}}}`
  - Bad key → `401 {"fault":{"faultstring":"Invalid ApiKey","detail":{"errorcode":"oauth.v2.InvalidApiKey"}}}`
- **ToS highlights** (developer.ticketmaster.com/support/terms-of-use) [V-doc]:
  - Cache: "Cache or store any Event Content other than for reasonable periods in order to provide the service" is prohibited. No fixed TTL; we must "remove … within 24 hours" anything the owner asks us to remove. **Design:** keep raw payloads with a retention policy, honor deletes, and refresh frequently.
  - Prohibited: apps that "replicate or attempt to replace the unique essential user experience of Ticketmaster.com". Our model is aggregation plus linking out, so we are fine if we never sell tickets ourselves.
  - Prohibited: sublicensing or "deriv[ing] revenues from the use" of the API "except as set forth" (the affiliate program is the sanctioned revenue path); using TM as an image host for banner ads; spam or incentivized sharing.
  - Follow the TM **branding guide** (it is a condition for quota increases).
  - League creative (NFL/NBA/MLB/NHL) is not licensed by default.
- **Affiliate** [V-doc FAQ]: run through **Impact**. Create an Impact publisher account, put the Impact Publisher ID in the TM developer profile, and tracking is added to `url` in Discovery and the Feed. **No commission** on primary sales during presales or within 24h after public onsale.
- **Price display law:** the FTC "Rule on Unfair or Deceptive Fees" (effective 2025-05-12) requires live-event ticket sellers to show the total price, including mandatory fees, up front [K; widely reported]. TM `priceRanges` is face value *excluding* fees. **We must label TM prices "face value, before fees" and never present them as all-in.** Show the seller's all-in price only when a source provides it.

### 1b. Inventory Status API v1 [V-doc]

- **Endpoint:** `GET https://app.ticketmaster.com/inventory-status/v1/availability?events=ID1,ID2,...&apikey=KEY`.
  - Up to about 350 IDs (7 KB) per call.
  - Batch per source/region; don't mix them.
  - The doc header oddly says POST.
- **Access:** "Access is provided to authorized clients only." Request it at `devportalinquiry@ticketmaster.com`.
- **Response** (array):
  - `eventId`
  - `status ∈ {TICKETS_AVAILABLE, FEW_TICKETS_LEFT, TICKETS_NOT_AVAILABLE, UNKNOWN}`
  - `resaleStatus ∈ {TICKETS_AVAILABLE, TICKETS_NOT_AVAILABLE, UNKNOWN}`
  - `statusDetail` / `resaleStatusDetail ∈ {NOT_SUPPORTED, STATUS_NOT_AVAILABLE, INVALID_EVENT_ID}`
  - `currency`
  - `priceRanges[]{type (primary|resale), minPrice, maxPrice (capped 2000.00), listingsExtendBeyondMax}`
  - Prices exclude fees and refresh at most once per hour, only in some markets.
- With a fake key it returns the same `Invalid ApiKey` fault [V-probe].
- **Recommendation:** email for access on day 1. This is the **only first-party "few tickets left" signal** in the whole landscape. Until it arrives, the adapter returns `availability: unknown`.

### 1c. Commerce / Partner / Publish APIs [V-doc]

Partner tier only. Partner Commerce is "typically restricted to a select few business partners." **Reject.**

---

## 2. SeatGeek Platform API

- **Base:** `https://api.seatgeek.com/2/`
- **Endpoints:** `/events`, `/events/{id}`, `/performers`, `/venues`, `/taxonomies`, `/recommendations` [K].
- **Auth:** `client_id` query parameter (plus optional `client_secret`) [V-probe].
  - No key → `403 {"status":403,"message":"Client is required - visit \"https://seatgeek.com/account/develop\"","errors":[{"message":"…","code":40307}],"meta":{"status":403}}`
  - Bad key → `403 … "Invalid client credentials" code 40302`.
- **Signup status:** **unclear, plan for friction.**
  - The old docs host `platform.seatgeek.com` now 308-redirects to `developer.seatgeek.com`, a **Kong developer portal**.
  - The public portal config at `kong-devportal-api.seatgeek.com/api/v2/portal` reports `"is_public":false`, with OIDC and basic auth enabled and RBAC enabled [V-probe]. That means docs and API catalog are visible only after registering and logging in, and key issuance may need approval.
  - `seatgeek.com/account/develop` is behind DataDome (403 to non-browsers).
  - Anecdotally, many developers have reported slow or no approvals since about 2023 [K].
  - **Action:** register at developer.seatgeek.com in a browser. The user must do this step.
- **Rate limit:** response headers show **`ratelimit-limit: 100`, `x-ratelimit-limit-minute: 100`**, i.e. 100 requests/minute per client [V-probe headers on a keyless request; may differ when keyed].
- **/events parameters** [K]:
  - Location: `venue.city`, `venue.state`, `postal_code`, `lat` / `lon` with `range=25mi`, `geoip`.
  - Dates and type: `datetime_utc.gte` / `.lte`, `taxonomies.name=concert`, `performers.slug`.
  - Price and sort: `lowest_price.lte`, `sort=datetime_utc.asc|score.desc`.
  - Paging: `per_page` (≤ 100 or so), `page`.
- **Key fields** (see `samples/seatgeek_events_doc_shape.json`) [K]:
  - Event: `id`, `title`, `short_title`, `url`, `datetime_local`, `datetime_utc`, `datetime_tbd`, `time_tbd`, `announce_date`, `visible_until_utc`, `status`, `score`, `popularity`, `type`, `taxonomies[]`, `performers[]`.
  - `venue{id,name,address,extended_address,city,state,postal_code,location{lat,lon},timezone,capacity}`. `capacity` is often 0.
  - **`stats`**:
    - `listing_count`: listings, not tickets
    - `visible_listing_count`
    - `lowest_price`
    - `average_price`
    - `median_price`
    - `highest_price`
    - `lowest_price_good_deals`
    - `lowest_sg_base_price`: pre-fee
    - `lowest_sg_base_price_good_deals`
    - `dq_bucket_counts[]`: listings per deal-quality bucket, the raw form of Deal Score
    - Any of these can be `null` when there are no listings.
    - `lowest_price` is historically all-in (with fees) and `lowest_sg_base_price` is pre-fee. **Label which one we show.**
- **ToS** [K]:
  - Attribution to SeatGeek with a link back is required.
  - No reselling or redistributing raw data.
  - Partner revenue goes through the SeatGeek Partner Program, which is Impact-based [K]. Links carry `aid` / `rid` parameters.
  - Re-check the current terms once logged into the portal.
- **Recommendation:** **build the adapter now against recorded fixtures plus this shape, gate it on `SEATGEEK_CLIENT_ID`.**
  - It is the backbone of price comparison and the "% left" proxy (see §6).
  - Snapshot `stats` every 3–6h per upcoming event into a `price_snapshots` table.

---

## 3. Resale marketplaces without open discovery APIs

### StubHub [V-doc sitemap, V-probe]

- `developer.stubhub.com` is live (Docusaurus).
- It documents **Account, Catalog, Inventory, Sales, Webhooks** APIs on `https://api.stubhub.net` (sandbox `sandbox.api.stubhub.net`), with OAuth2: application-only (client credentials) and user-login flows.
- **Catalog API** event endpoints:
  - `GET /catalog/events` with `country_code`, `genre_id`, `latitude`, `longitude`, `max_distance_in_meters`
  - `GET /catalog/events/{eventId}`
  - "Search events" with `q` and `dateLocal`
  - `GET /catalog/events/external_mappings/{platform}/{externalEventId}`. This could map TM IDs to StubHub IDs, which is excellent for dedup.
- **Event fields:**
  - `id`, `name`, `start_date`, `end_date`, `on_sale_date`, `date_confirmed`, `time_confirmed`
  - `type` (Main/Parking), `status` (Normal/Postponed/Cancelled/Deleted)
  - **`min_ticket_price{amount,currency_code,display}`**
  - `_embedded.venue{name,city,state_province,postal_code,latitude,longitude}`, `_embedded.external_mappings`
- No inventory count on the event resource.
- Keyless probe: `GET api.stubhub.net/catalog/events/search` → `401` with an empty body.
- **Access:** credentials are not self-serve. The guides are seller-oriented ("creating a listing"). The 2022 "migrating to new API" post marks the post-viagogo platform.
- **Affiliate:** StubHub runs an affiliate program through Partnerize [K]. The affiliates page is JavaScript-only, so I could not verify it.
- **Recommendation:** stub `stubhub` adapter. Email for Catalog API (application-only) access. Until approved, show nothing from StubHub; never scrape.

### Vivid Seats [V-doc]

- The affiliate program is on **Impact** (signup links to app.impact.com). It pays monthly on completed sales and can "deep-link to any event."
- No API or feed is advertised. Impact sometimes exposes a product catalog for advertisers [K; check after joining].
- **Recommendation:** affiliate deep links only (search-URL deep link, not an event-matched price). Never claim a Vivid price we didn't get from an approved feed.

### TickPick [V-doc]

- Affiliate page says "New Program Coming Soon": 4–5% commission, 30-day cookie.
- Promises inventory via a "well-documented API or custom widgets" and white-label, but no docs exist.
- **Recommendation:** watch; apply via their form.

### DICE [V-probe]

- `partners-endpoint.dice.fm/graphql` exists and returns `401 {"error":"unauthorized",...}`.
- This is DICE's **Partner API for promoters** to read *their own* events and tickets [K]. No public discovery or affiliate API; `dice.fm/partners` 403s to bots.
- **Reject.** Keep DICE URLs when other sources (RA, venue sites, JamBase) reference them.

### AXS [K]

- Partner-only (AXS for venues and Veritix). `developer.axs.com` did not resolve today [V-probe].
- **Reject.**

---

## 4. Event discovery sources

### Eventbrite v3 [V-doc, V-probe]

- **Search is gone:** `GET /v3/events/search/` "was shut down at 11:59 pm PT on Thursday, December 12, 2019." Today it returns `404 {"error":"NOT_FOUND",...}`.
- **Still possible with a free private token** (Account → API Keys):
  - `GET /v3/events/{event_id}/`
  - `GET /v3/organizations/{organization_id}/events/`
  - `GET /v3/venues/{venue_id}/events/`
  - Expansions such as `?expand=venue,ticket_availability,organizer,category`. `ticket_availability` is documented as an "Overview of availability of all Ticket Classes."
  - [K] its fields: `has_available_tickets`, `minimum_ticket_price`, `maximum_ticket_price`, `is_sold_out`, `start_sales_date`, `waitlist_available`.
  - [K] event fields: `name.text`, `start.utc`, `start.timezone`, `url`, `is_free`, `capacity`, `status`, `online_event`.
  - Organizers can set `show_remaining` to expose the remaining-ticket count; most don't.
- **Limit:** "Default rate limits are 2,000 calls per hour" (429 `HIT_RATE_LIMIT`) [V-doc]. The daily cap of 48,000 is [K].
- **Auth error:** `401 {"status_code":401,"error":"NO_AUTH","error_description":"An OAuth token is required for all requests"}`.
- **Strategy:**
  - Maintain a per-city `eventbrite_organizers.yaml` of known local organizers: run clubs, breweries, volunteer orgs, rec leagues.
  - Also harvest Eventbrite event IDs from links found in other sources (Google Events `ticket_info`, Meetup, venue sites), then hydrate them via `/events/{id}`.
  - The Eventbrite **affiliate program** (via Impact) [K] is worth joining.

### Meetup GraphQL [V-doc, V-probe]

- **Endpoint:** `POST https://api.meetup.com/gql-ext`. The docs moved from `/gql`, and `keywordSearch` was split into `eventSearch` / `groupSearch`.
- **Auth:** OAuth2 bearer token from a registered OAuth client.
- **Rate limit:** 500 points per 60s; over it you get `RATE_LIMITED` with `resetAt`.
- **Pro requirement:** the docs I fetched (guide, authentication, OAuth list) **do not state that Meetup Pro is required**. The OAuth client list needs login. Community reports since 2023 say new OAuth consumers need a Pro subscription [K, unconfirmed]. **The user should try creating a client.**
- **Root queries** (from today's introspection): `eventSearch`, `recommendedEvents`, `event`, `events`, `group`, `groupByUrlname`, `groupSearch`, `proNetwork`, `recommendedGroups`, `topicCategories`, `suggestTopics`, `self`.
- **`eventSearch(filter: EventSearchFilter!)`** requires `query`, `lat` and `lon`. Optional fields: `radius`, `startDateRange`, `endDateRange`, `eventType`, `city`, `state`, `zip`, `topicCategoryId`, `categoryId`, `rsvpCountRange`, `isStartingSoon`, `isHappeningNow`, etc.
- **Event fields** include:
  - `id`, `title`, `eventUrl`, `dateTime`, `endTime`, `duration`, `status`, `eventType`
  - `venue{name,address,city,state,postalCode,lat,lon,googleMapsUrl,venueType}`, `group`, `topics`
  - `feeSettings{amount,currency,required,earlyBirdDiscount,refundPolicy}`
  - `maxTickets`, `waitlistMode`
  - `rsvps{totalCount,yesCount,waitlistCount,noCount,attendedCount}`
  - **`attendanceForecast{expected,lowerBound,upperBound,confidenceLevel,dataQuality,historicalEventCount,historicalRsvpCount,rsvpCount,modelVersion}`**
- **Observation:** an unauthenticated `eventSearch` for "trivia" near Chicago **returned real results today**. Do not rely on that. ToS requires a registered client, and anonymous access may be revoked. We will only call it with a token.
- **Recommendation:** **USE (P0).**
  - The best source for the "meeting people" category: run clubs, trivia, board games, newcomer groups.
  - It is also a first-party attendance forecast with bounds. Display it as "Meetup forecast: 25–40 (medium confidence)."

### PredictHQ [V-doc]

- **Endpoint:** `GET https://api.predicthq.com/v1/events/` with `Authorization: Bearer`.
- **Parameters:** `within=10mi@lat,lon`, `category=concerts,sports,festivals,community,...`, `active.gte`, `rank.gte`, `phq_attendance.gte`, `state=active`, `limit`, `offset`, `sort`.
- **Fields:** `id`, `title`, `description`, `category`, `phq_labels`, `rank` (0–100), `local_rank`, **`phq_attendance`**, `predicted_event_spend`, `entities[]` (venues, performers), `geo`, `start`, `start_local`, `end`, `predicted_end`, `timezone`, `state`, `private`. The list envelope is `count`, `next`, `previous`, `overflow`, `results`.
- **Pricing:** "Free Trial - No Credit Card Needed." No public tiers; demo-driven, enterprise pricing [V-doc]. Keyless probe → `401 {"error": "unauthorized"}`.
- **ToS:** PredictHQ licenses data for internal demand forecasting. Public redisplay of `phq_attendance` likely needs a specific license [K; check].
- **Recommendation:** stub. Use the trial to **calibrate our own attendance model** (compare our estimates to `phq_attendance`) rather than to display PHQ numbers.

### JamBase Data [V-doc]

- Bearer key; `GET /v3/events` (current docs v3.1.0). Keyless probe on the legacy `www.jambase.com/jb-api/v1/events` → `400 {"success":false,"errors":[{"code":"missing_api_key",...}]}`.
- **Plans:**

  | Plan | Price | Calls/mo | Calls/hr | Future window | Attribution |
  |---|---|---|---|---|---|
  | Developer | $0 (non-commercial) | 1,000 | 3,600 | 6 months | Required |
  | Startup | $500/mo | 20,000 | — | All future | Requested |
  | Pro | $1,500/mo | — | — | — | — |
  | Pro+ | $2,500/mo | — | — | — | — |

  The table lists $600/$1,800/$3,000 monthly; the plan cards show the annual-billing rates. There is also a 14-day trial and an MCP option.
- **Recommendation:** P2 for music coverage of small clubs that TM misses. The Developer tier fits while the project is non-commercial. Show the attribution.

### Bandsintown [V-doc terms, V-probe]

- **Endpoints:** `https://rest.bandsintown.com/artists/{name}?app_id=…`, `/artists/{name}/events?app_id=…&date=upcoming`. Event data includes `offers[]`, `lineup`, `venue` and `url` (with `app_id` and UTM).
- **Probes:** no `app_id` → `401 {"message":"Unauthorized"}`; fake `app_id` → `403 {"Message":"User is not authorized … explicit deny …"}`.
- **Terms** (corp.bandsintown.com/data-applications-terms):
  - Meant "solely by artists, or people working in connection with or on behalf of artists"; others need specific approval.
  - Attribution is required.
  - Bans aggregating with third-party content "without distinction."
  - Commercial use requires written approval.
  - Caching must be session-based and disclosed.
  - It is also artist-keyed only: there is no city search.
- **Reject** for an aggregator. Revisit only with written approval.

### Songkick [V-doc, V-probe]

- "Currently not approving API requests for student projects, educational purposes or hobbyist purposes." Use requires a partnership agreement and a license fee.
- Probe → `401 {"resultsPage":{"status":"error","error":{"message":"Invalid or missing apikey"}}}`.
- **Reject** unless the user wants to pay.

### Resident Advisor [V-probe, V-doc terms]

- `ra.co/graphql` answers anonymously (`{"data":{"__typename":"Query"}}`), but it is undocumented and internal.
- `robots.txt` disallows `/api/`.
- Terms §4.4(a) and (f) forbid "any automated system or software to extract content or data … for commercial purposes" and access "via a means we have not authorised in writing … scrapers."
- **Reject.** Ask RA for written permission if electronic music becomes a focus.

### DoStuff network (Do312, Do512, DoNYC, DoLA, etc.) [V-probe]

- No public API.
- `do312.com` returns 200 to curl but 403 to the fetcher (bot protection). `dostuff.co` → 404.
- In the past DoStuff offered white-label calendars and ticketing for venues [K].
- **Reject for ingestion.** Their curation, "Do" picks and free-event focus are good competitor inspiration (see competitors.md). Consider partnership outreach later.

### AllEvents.in [V-doc]

- "Events API" page: RESTful JSON with events, venues, organizers and performers. Access via the "Request Trial Access" form, which asks for company, use case, website and LinkedIn. Pricing is "get in touch."
- **Stub, low priority.** Much of it is re-aggregated Facebook and Eventbrite data, so expect heavy dedup work.

### Yelp Events [V-doc]

- `GET https://api.yelp.com/v3/events` (Bearer) is still documented.
  - Parameters: `location` or `latitude` / `longitude`, `radius` ≤ 40,000 m, `start_date` / `end_date` (unix), `categories`, `is_free`, `limit` ≤ 50, `offset` ≤ 1000, `sort_on=popularity|time_start`.
  - Fields: `id`, `name`, `description`, `category`, `cost`, `cost_max`, `is_free`, `time_start`, `time_end`, **`attending_count`**, **`interested_count`**, `tickets_url`, `event_site_url`, `business_id`, `is_canceled`, `is_official`, `latitude`, `longitude`, `location`.
- Keyless probe → `400 {"error":{"code":"VALIDATION_ERROR","description":"Authorization is a required parameter.",...}}`. So the route still exists.
- **Pricing:** Yelp Places API plans are Base $229/mo, Enhanced $299/mo and Premium $643/mo, each with a 30-day / 5,000-call trial. The plans page does not mention Events.
- **Reject (cost).** The Events product has been effectively unmaintained for years, and doc examples show `cost` and `tickets_url` as null [K].

### Google Events (via SerpApi) [V-doc]

- Google has no official events API.
- SerpApi: `GET https://serpapi.com/search?engine=google_events&q=Events+in+Chicago,+IL&api_key=…`, with optional `location`, `htichips` [K: `date:today|tomorrow|week|weekend|next_week|month`, `event_type:Virtual-Event`] and `no_cache`.
- **Fields:** `events_results[]{title, date{start_date, when}, address[], link, event_location_map, venue{name, link}, ticket_info[]{source, link, link_type}, thumbnail}`.
- **Pricing:** free 250 searches/mo at 50/hr; Starter $25/mo for 1,000 searches.
- Keyless probe → `401 {"error":"Invalid API key…"}`.
- **ToS:** this is scraped Google SERP data, a legal gray zone for redisplay.
- **Use only as a discovery and link-harvest signal.** Pull `ticket_info[].link` to find Eventbrite, TM and venue URLs, then hydrate from the primary source. Never display Google's text or images directly.

### setlist.fm [V-doc, V-probe]

- `x-api-key` header; key via setlist.fm/settings/api. "Free for non-commercial projects."
- Endpoints include `/1.0/search/setlists`, `/1.0/artist/{mbid}/setlists`, `/1.0/venue/{venueId}/setlists`.
- Keyless probe → `403 {"message":"Forbidden"}`.
- Past setlists only. Optional enrichment ("typical setlist," "avg songs").

---

## 5. Cross-cutting design implications

1. **Every price carries metadata:** `price_kind ∈ {face_value_ex_fees, all_in, base_ex_fees, unknown}`, `seller`, `fetched_at` and `currency`. TM `priceRanges` is `face_value_ex_fees`; SeatGeek `lowest_price` is (probably) `all_in` and `lowest_sg_base_price` is `base_ex_fees`; StubHub `min_ticket_price` is unknown until verified. The UI must never compare prices of different kinds without a label. This also matters under the FTC fee rule.
2. **Affiliate links are config, not code.**
   - Each seller gets a `link_decorator(url) -> url`: TM via the Impact ID in the developer profile; SeatGeek with `aid`/`rid`; Vivid, Eventbrite and StubHub via Impact or Partnerize parameters.
   - Disclose affiliate links in the UI.
3. **Caching:** all of these terms prefer "reasonable periods." Keep raw payloads for replay (with a TTL such as 30 days), honor upstream deletes and cancellations quickly, and refresh near-term events more often.
4. **Rate budgets per source:**
   - TM: about 2 rps, 5k/day.
   - SeatGeek: 100/min.
   - Eventbrite: 2k/hr.
   - Meetup: 500 points/min.
   - SerpApi: 250/mo free, so budget about 8 searches/day across all cities.
   - JamBase dev: 1,000/mo.
5. **Dedup keys:** TM `id`, plus StubHub `external_mappings`, attraction `externalLinks.musicbrainz`/`spotify`, venue lat/lon and the start time to the minute.

## 6. The price-history and "% tickets left" question

**There is no legitimate source of the number "x% of tickets left" for third-party apps.** The primary sellers do not expose capacity versus sold. Here is what is legitimately available, from strongest to weakest:

| Signal | Source | What it really means | How we can use it |
|---|---|---|---|
| `status = FEW_TICKETS_LEFT` / `TICKETS_NOT_AVAILABLE`, `resaleStatus` | TM Inventory Status API (authorized clients only) | First-party categorical primary-inventory status, near real-time | Show a badge: "Few tickets left (Ticketmaster)". The best signal, and it needs approval. |
| `dates.status.code` (onsale/offsale/canceled/postponed/rescheduled) | TM Discovery | Sale status, not inventory | Show sale state; "offsale" before the event can hint at sold out. Label it as a hint. |
| `ticket_availability.is_sold_out`, `has_available_tickets`; remaining count when the organizer enables `show_remaining` | Eventbrite | First-party for that event | Show it exactly; "% left" only when both capacity and remaining are exposed. |
| `maxTickets`, `rsvps.yesCount`, `waitlistCount`, `waitlistMode` | Meetup | Real cap and real count | **A real "% left" = 1 − yesCount/maxTickets.** Show "Waitlist (n)" when it is full. |
| `stats.listing_count` / `visible_listing_count` over time | SeatGeek | Resale supply (listings, not seats) | Snapshot it. A falling count plus a rising `lowest_price` means "Selling fast (resale supply down 40% in 7 days)". Never convert it to "% of venue left". |
| `stats.lowest_price`, `median_price`, `average_price` over time | SeatGeek (also StubHub `min_ticket_price` if approved) | Resale market price | Price-history sparkline from our own snapshots. Label it "resale, all-in" or whichever kind applies. |
| `ticketLimit.info` | TM Discovery | Per-order cap text | **Not** an availability signal. Show it as "Limit 8 per order" only. |
| Venue capacity (`capacity` on SeatGeek, often 0) plus our venue table | SeatGeek / OSM / Wikidata / manual | Denominator for attendance estimates | Use it for attendance bands, not for "% left". |

**Recommended UI wording:**

- Use "Few tickets left (via Ticketmaster)" or "Resale supply ↓ 38% this week (SeatGeek listings)".
- Use "~60% of Meetup spots taken (24/40)" only when the data really supports it.
- Otherwise show "Availability unknown." Never invent a percentage. Our no-fabrication rule wins.

**How competitors present these signals** (mostly [K]; verify visually before copying):

- **SeatGeek, Deal Score:** rates each listing against historical prices for comparable seats, on a color scale (great, good, fair, bad deal). `dq_bucket_counts` and `lowest_price_good_deals` are its API footprint. Filters show "best deals first."
- **TickPick:** "No hidden fees" all-in pricing is the brand. It has a "Best Deal" rating per listing and a price-history-style "buy now or wait" hint on some events.
- **Gametime:** last-minute focus, with "Lowest price guarantee," "Zone deals," photo-of-the-view, and prices that drop toward show time. Countdown framing is its key UX.
- **Ticketmaster:** "Limited availability," "Few tickets left" and "Selling fast" badges; "Verified Resale" labels; all-in price toggle (all-in by default in the US since the FTC rule).
- **StubHub:** "X people viewing," "Selling fast," "Only N tickets left at this price." These are urgency nudges that are often criticized as dark patterns.
- **Songkick / Bandsintown:** no prices, mostly. "Tickets" CTA plus "on sale now" / "sold out" flags, "RSVP / I'm interested" counts, and artist-tracking alerts ("on sale soon" notifications are the killer feature).
- **Fever:** "Selling fast," "Last tickets," "Bestseller," "Free," and a "waitlist" for future dates. Heavy curated imagery and Fever-produced experiences (Candlelight concerts).
- **DICE:** no resale and face-value-only waitlists. When sold out, "Join waitlist" with transparent queue mechanics. All-in prices up front. "Few tickets left" is rarely shown.
- **Eventbrite:** "Sales end soon," "Almost full," "Going fast" badges (organizer-driven or threshold-driven), and "N remaining" when the organizer enables it.

**Our differentiator:**

- **Show the provenance of every urgency claim and a sparkline of our own snapshots.** Honest urgency ("Resale floor up $22 since Monday") beats fake urgency.
- Add a **"Price watch" alert:** notify the user when SeatGeek `lowest_price` drops below a threshold.

---

## 7. Keys and actions needed from the user

1. Ticketmaster developer key (free, instant) → `TICKETMASTER_API_KEY`.
2. Email `devportalinquiry@ticketmaster.com` to request **Inventory Status API** access.
3. SeatGeek: register at developer.seatgeek.com (browser required) → `SEATGEEK_CLIENT_ID` (+ `SEATGEEK_CLIENT_SECRET`).
4. Meetup: create an OAuth client at meetup.com/api/oauth/list (it may require Pro) → `MEETUP_CLIENT_ID`, `MEETUP_CLIENT_SECRET`, refresh token.
5. Eventbrite private token → `EVENTBRITE_TOKEN`.
6. Optional:
   - JamBase Developer key (`JAMBASE_API_KEY`)
   - SerpApi free key (`SERPAPI_KEY`)
   - setlist.fm key
   - PredictHQ trial
   - Impact publisher account (TM, Vivid Seats, SeatGeek and Eventbrite affiliate programs run through Impact)
   - StubHub API access request
