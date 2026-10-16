# Competitor and inspiration survey

Researched on 2026-10-15. This survey draws mostly on prior product knowledge [K]. Products change often, so verify a UI before copying it closely. Ticket-marketplace urgency UX (SeatGeek, TickPick, Gametime and others) is covered in `ticketing_and_events_apis.md` §6.

> **File name note (2026-10-16):** requested as `COMPETITORS.md`, but macOS is case-insensitive so it would overwrite this file. Part 1 (2026-10-15) is kept verbatim; Part 2 (live teardown, 2026-10-16) is appended below.

## What each does well and badly

| Product | What it is | Does well | Does badly | Steal this |
|---|---|---|---|---|
| **Fever** | Curated city "experiences" marketplace (35+ US cities); owns formats like Candlelight concerts | Gorgeous imagery and a tight editorial feed. "Selling fast"/"Bestseller" badges. Date-slot picker. Waitlists for future dates. | Heavy bias toward its own paid inventory. Almost no free or community events. Urgency badges feel salesy. Same five experiences in every city. | Visual polish of cards; per-city "Top this week" lists; slot-based date picker for recurring events. |
| **DoStuff (Do312, Do512, DoNYC…)** | Local editorial event calendars plus venue ticketing | Real local curation ("Do" picks), free-event focus, genre/venue browsing, newsletter. Voice feels like a friend who knows the city. | Only about 10 cities. Dated UI. Ad-heavy. No personalization, deadlines or price comparison. | Editorial "Pick" badge with a one-line *why*; "Free this weekend" lane. |
| **Meetup** | Group-based recurring events | Best source for "meet people" (run clubs, trivia, language exchange). RSVP counts and waitlists. Recurring cadence. Newcomer-friendly groups. | Search quality and spam. Organizer paywall drove groups away. Many ghost groups. Discovery outside your groups is weak. | Show the *group's track record* (avg attendance, years active) as a trust signal; "recurring weekly" chips. |
| **Nextdoor** | Hyper-local neighborhood feed | True neighborhood granularity: garage sales, block parties, lost dogs. Verified-address trust. | Negativity and crime posts. Events buried. Needs an address. No structured event data. | Neighborhood-level filter ("within your neighborhood"); block-party and street-fest category. |
| **Time Out** | Editorial city guides plus newsletters | Authoritative "best of" lists, seasonal guides ("rooftop bars open now"), strong SEO. | Static listicles that go stale. Few deadlines. Weak for niche or community events. Ad clutter. | Seasonal "openers" collections (rooftop season, patio season, ski lease deadlines); "New openings this month." |
| **Eventbrite discovery** | Self-serve ticketing with a consumer discovery app | Huge long tail (workshops, classes, mixers, volunteering). "Sales end soon" / "Almost full." Follow organizers. | Low-quality and duplicate listings, MLM "networking" spam, too many online events. Weak ranking. No price comparison. | "Follow organizer" (our version: follow venue, league or org across all sources); "Sales end soon" in our Deadlines view. |
| **Bandsintown** | Artist tracking and concert alerts | Sync your Spotify/Apple library for an instant personal concert feed. "On sale soon" alerts. RSVP counts. | Ticket links only, no price comparison. Push-notification spam. Music only. | **Import your music taste** (Spotify OAuth top artists) to seed concert recommendations; onsale alerts as deadlines. |
| **Songkick** | Concert tracking (Warner-owned) | Clean concert calendar per metro. Artist tracking. Good coverage of small venues. | Has stagnated. Closed API. Music only. | Metro-area calendar as a default view for music. |
| **Volo** | Adult rec sports leagues (kickball, volleyball, pickleball…) in many US cities, plus a membership pass | Frictionless signup, free-agent placement, social-first ("bar after the game"), pickup games, volunteer tie-ins. | Only Volo's own leagues; ZogSports, local clubs and park-district leagues are invisible. Registration deadlines are buried in league pages. | **League card**: sport, night, location, skill level, free-agent vs team price, *registration closes* date, spots left. Our killer "Deadlines" content. |
| **Bumble BFF** | Friend-finding swipe app (relaunched as a standalone app in 2025) | Low-pressure way to meet people one-on-one. Interest badges. Group features. | Swipe fatigue; matches rarely turn into plans. Not tied to real events. | "Go with someone": let users mark events "looking for a buddy" (privacy-first, later phase). |
| **Timeleft** | Dinner with 5 strangers every Wednesday, matched by personality quiz; expanded to many US cities | One weekly ritual, zero decision fatigue, curated restaurant, personality matching, paid subscription. | Fixed format. Uneven matching quality. Subscription cost. | **The "weekly ritual" idea**: a "Your Wednesday" recommendation of one great thing per week. Use a short personality/interest quiz in onboarding. |
| **222** | AI-curated small-group outings (NYC, LA and others) based on a questionnaire | Takes away planning entirely. Balanced group composition. Novelty venues. | Small markets. Opaque matching. Requires trust. | "Explain why this pick" (they hint at it; we should make it explicit). Low-commitment intro experiences. |
| **Local "new in town" subreddits** (r/chicago, r/AskNYC, r/Minneapolis, weekly "what's happening" threads, r/[city]social) | Crowd wisdom | Honest, specific, current ("go to X trivia, it's actually friendly"). Recurring weekly threads. Lists of newcomer groups. | Unstructured. Repetitive questions. Hard to search. Advice goes stale. | Seed "newcomer-friendly" tags and recurring social events from these threads (manual curation, with links and attribution). Treat Reddit as a research input, not a scraped source. |

## Patterns worth adopting

1. **Deadline-first framing.** Nobody does this well. Volo, Eventbrite and TM each show a deadline only on their own detail page. A cross-source "closing soon" view (leagues, early-bird pricing, presales, volunteer signups, con badge price tiers) is our clearest gap in the market.
2. **Explainable recommendations.** Timeleft and 222 hide the logic. We say *why*: "Because you picked running + new to Logan Square: this run club meets 0.4 mi away, ~30 people, beginner-friendly."
3. **Honest urgency.** Fever, StubHub and Eventbrite urgency badges feel manipulative. Ours carry provenance and a sparkline (see ticketing doc §6).
4. **One ritual a week.** A "Your Wednesday / Your weekend" digest (email/ICS) beats an infinite feed for retention.
5. **Taste import.** Bandsintown's Spotify sync is the fastest onboarding win for concerts. A short interest quiz covers the rest.
6. **Trust signals for community events.** Show group age, average attendance and recurrence. This counters Meetup's and Eventbrite's spam.
7. **Neighborhood granularity.** Nextdoor's strength. Filter by neighborhood polygons, not just radius.
8. **Editorial "pick" layer.** DoStuff and Time Out show that a human-ish one-liner beats raw listings. We can generate a "why it's good" line from structured data, label it as such, and never invent facts.
9. **Seasonal collections.** Time Out-style: rooftop season, haunted houses, holiday markets, ski passes, summer league signups.

## Anti-patterns to avoid

- Fake scarcity ("12 people are looking at this").
- Hidden fees and mixed fee and no-fee prices.
- Spammy push notifications.
- Online-only events polluting a city feed.
- Stale editorial lists without a "last checked" date.
- Requiring an account before showing any value.

## Feature ideas this survey suggests (for docs/ideas_ledger.json)

| Idea | Note |
|---|---|
| Spotify "taste import" → concert recs | Later phase, OAuth |
| League registration tracker with "spots left" and free-agent price | Volo, ZogSports, parks & rec |
| Weekly digest: "Your weekend in {city}" (email + ICS feed) | |
| Follow a venue, organizer or league across all sources | |
| "Newcomer-friendly" tag | From Meetup group descriptions + curated subreddit wisdom + "beginners welcome" text |
| Price watch alerts on resale floor | From SeatGeek snapshots |
| Seasonal collections auto-built from categories plus dates | |
| Neighborhood filter using city open-data neighborhood polygons | |
| "Go with a buddy" opt-in | Privacy-first, later |
| "Last checked N hours ago" on every card | Counter the stale-list problem |

---

# Part 2 — Competitor teardown v2: patterns, anti-patterns, trust

Researched 2026-10-16. This **extends** Part 1 above (2026-10-15, which covers the product landscape: Fever, DoStuff, Meetup, Nextdoor, Time Out, Eventbrite, Bandsintown, Songkick, Volo, Bumble BFF, Timeleft, 222, Reddit). Here the focus is narrower: **IA, URL structure, filters, ranking, imagery, price/scarcity signals, SEO footprint and trust signals**, from live fetches where possible. Ticket-resale urgency UX lives in `ticketing_and_events_apis.md` §6, so it isn't repeated here.

**Evidence tags**
- **[L]** verified live today. I fetched the public HTML with UA `GetOffTheCouch/0.1 (+https://github.com/lachlanspangler/GetOffTheCouch)`, checked robots.txt first, and fetched one page per ~1.5 s. Claims are from server-rendered HTML, JSON-LD, meta tags and visible text. I did not run a JS browser, so anything rendered only client-side is invisible to these checks.
- **[K]** prior knowledge, not re-verified today. Verify before copying.
- **[X]** couldn't verify: blocked (HTTP 403 bot wall) or robots-disallowed. I did not try to work around it.

| Site | Fetch result today |
|---|---|
| Eventbrite `/d/il--chicago/events--this-weekend/`, `/d/il--chicago/free--events/`, one `/e/…` page | [L] 200 |
| Meetup `/find/?location=us--il--Chicago`, `/cities/us/il/chicago/`, one group page | [L] 200 |
| Fever `/en/chicago`, one `/m/689305` page | [L] 200 |
| DICE `/browse/chicago` | [L] 200 |
| Time Out Chicago `/things-to-do`, the Chicago and NYC "this weekend" pages | [L] 200 |
| Luma `/discover`, `/chicago` | [L] 200 |
| Partiful `/`, `/explore`, `/explore/chi` | [L] 200 |
| Patch `/illinois/chicago/calendar` | [L] 200 |
| Chicago Reader `/events/`, Racket home, Austin Chronicle `/calendar/` | [L] 200 |
| NYC Tourism `/things-to-do/`, Choose Chicago `/events/`, Visit Seattle `/things-to-do/events/` | [L] 200 |
| The Infatuation `/chicago`, one review | [L] 200 |
| Airbnb `/s/Chicago/experiences`, Resy `/cities/chicago-il` | [L] 200, but JS shells only (little content) |
| Do512 / Do312 (DoStuff), EverOut (The Stranger), Resident Advisor `ra.co` | [X] 403 on robots.txt and on pages |
| Nextdoor `/events/` | [X] robots.txt disallows us |

---

## 1. Per-competitor teardown

### Eventbrite (discovery pages) [L]
- **URL grammar:** `/d/{state}--{city}/{category-or-price}--{facet}/`, e.g. `/d/il--chicago/events--this-weekend/`, `/d/il--chicago/free--events/`. Suburbs get `/ttd/il--evanston`, `/ttd/il--oak-park` and others ("Things to do in…" link farm, ~20 suburbs per page). Events are `/e/{slug}-tickets-{id}`. There's also `/trending/searches/il--chicago`.
- **SEO footprint:** `robots: index, follow`, a canonical equal to the facet URL, a keyword-stuffed `<title>` ("Things to Do in Chicago, IL This Weekend - Events & Activities"). The JSON-LD on each listing page is an `ItemList` of 20 `Event`s with `Place`/`GeoCoordinates`/`PostalAddress`, plus `BreadcrumbList` and an **`FAQPage`** (8 Q&As) aimed at rich results. Detail pages carry `AggregateOffer` (lowPrice 5.0, highPrice 49.74, `InStock`) and a `SpeakableSpecification`. This is the strongest SEO footprint in the set.
- **Filters:** neighborhood (West Side, The Loop…), Price Free/Paid, Format (Class/Conference/Festival/Party), Language, Currency, "Only show events from organizers I follow", "Search for online events".
- **Scarcity badges:** on the Chicago weekend page I counted "Almost full" ×14, "Sales end soon" ×20 and "Going fast" ×4 across about 40 cards. **Most cards carry a badge**, so the badges carry no signal. A "Promoted" label exists (2 hits).
- **Images:** imgix-style proxy `img.evbuc.com/{encoded cdn url}?crop=focalpoint&fit=crop&w=…&fp-x=0.5&fp-y=…`. Focal-point cropping keeps faces in frame at any aspect ratio.
- **Trust:** a **"Good to know"** block on every event shows "Refund Policy: No refunds" and "all ages / In person". Ticket refunds are set per organizer. The robots.txt has a full `Disallow: /` for `Python-urllib` and a list of scraper UAs, which tells us their stance.
- **Annoying:** a multi-date event that started Sep 19 shows up on the "this weekend" page as "Multiple dates". About 53 mentions of "online" appear on a *Chicago* page. A neighboring page also shows 15+ sign-in/sign-up CTAs.
- **Gap for us:** use the badges only when the claim is true and sourced. Collapse multi-date events (we already do: I-013). Exclude online events by default.

### Meetup [L]
- **URL grammar:** `/find/us--il--chicago/` is the canonical city hub, and `/cities/us/il/chicago/` canonicalizes to it. `/find/?location=…` is **`noindex, follow`**, so faceted search is kept out of the index while the city hub is indexed. Groups are `/{group-slug}/` and events `/{group-slug}/events/{id}`.
- **City hub IA (h2s):** "Events in Chicago today" → "this weekend" → "Most popular groups" → FAQ → "Meet new people in Chicago" → "Outdoor activities" → "Sports & Fitness" → "Live music". It's built as **intent lanes**, not a category tree. "Meet new people" is a lane title we should copy outright.
- **Group trust block:** "4.8 • 1276 ratings · 8,415 members · Past events 359 · Upcoming 22", a Code of Conduct link, named organizers, and per-event "62 attendees" plus "Waitlist". This is the best **track-record** display in the set (it confirms Part 1 pattern #6).
- **Annoying:** online events are mixed into the Chicago results ("Online by EMDR Therapist Circle (online) 1 attendee"). The generic `meetup-flyer.png` is used as og:image on city pages. Joining and RSVPing require an account [K].

### Fever [L]
- **URL grammar:** `/en/{city}` hub, `/en/{city}/{category}` (`/halloween`, `/candlelight`, `/when`, `/fever-originals`, `/city-tours`, `/stand-up`, `/diy-workshops`…), `/en/{city}/venue/…`, and **opaque `/m/{id}`** for experiences (with `/m/{id}/es` etc. for languages). The hub links ~250 `/m/` pages.
- **IA:** H1 "Chicago Things to Do", then **"Pick your vibe AI"** chips (Live Music, Nightlife, Tourist, Romantic, Luxe, Foodie, With friends, Creative, Adventurer, Detective, Family), "Top 10 in Chicago", "Fever Originals", then seasonal and category rails. The hub also has a suburb switcher (Downers Grove, Palatine, Naperville).
- **Price presentation:** "From $40.50". About 240 "From $" strings. Discounts show as **"- 20%"** with a struck price ("From $46.00 $36.80"). Every card carries a star rating ("4.9 · Arts Center of Oak Park").
- **Images:** Cloudinary transforms `f_auto,w_360,h_251,c_lfill,g_auto`. `g_auto` gives automatic subject-aware cropping. A user-photo gallery appears on detail pages. Detail pages also carry `Product` + `AggregateRating` + a 13-Q `FAQPage` in JSON-LD.
- **Trust/annoying:** the refund policy sits in an FAQ: "No refunds are permitted under any circumstances", with date changes allowed up to 48 h before. "Waitlist" items still appear in the top rails. The hub is almost entirely its own inventory (Candlelight ×many, Jury Experience, Ballet of Lights); this confirms Part 1.

### DICE [L]
- **URL grammar:** `/browse/chicago-5b238ca66e4bcd93783835b0` (city slug plus an opaque Mongo-style id) and `/browse/{city-id}/music`, `/culture`. That's ugly, but the canonical is set.
- **Price presentation:** **all-in prices with odd cents**: "$41.93", "From $33.99", "$23.09". This shows fees are included up front [K: DICE markets "no hidden fees"]. "Free" appears as a first-class price. The DICE format is title · date · venue · price, and nothing else.
- **Filters:** Date, Price, and genre chips (Gigs, DJ, Party, Theatre, Art, Comedy, Social, Film, Food & drink, Wellbeing, Sport, Talk).
- **SEO:** a weak footprint, with no Event JSON-LD in the SSR HTML (only WebSite/Organization) and a generic social image. Square artwork through imgix `rect=` crops.
- **Trust:** "Request a refund" is linked in the global footer [L]. DICE also runs a waitlist for sold-out shows, with face-value resale [K].
- **Gap:** "Popular" ordering isn't chronological. One promoter appears twice (Earlybirds Club, Dec 12 and Oct 17).

### Time Out (city guides) [L]
- **URL grammar:** `/{city}/things-to-do/{evergreen-slug}`. The **same URL is rewritten every week**, and only the `<title>` changes: "The best things to do in NYC this weekend: Oct 16–18" and "The Best Things to Do in Chicago This Weekend: October 16-18". Chicago's slug is `best-things-to-do-this-weekend-in-chicago`, NYC's is `things-to-do-in-nyc-this-weekend`; slugs aren't consistent across cities (my first guess 404'd). Monthly pages are `/chicago/events-calendar/october-events-calendar`. There are also `/chicago/news/{slug}-{MMDDYY}` and neighborhood hubs.
- **Bylines and freshness:** JSON-LD `Article` with `author` "Lauren Brocato" (Chicago) and "Rachel Askinasi, Christina Izzo" (NYC). `datePublished 2026-10-14`, `dateModified 2026-10-16T17:35Z`. A visible date ("Wednesday October 14 2026") shows on the page. Every image has a credit line ("Photograph: Courtesy Chicago Loop Alliance"). A "Recommended" badge marks critic picks.
- **Item format:** title → category · neighborhood → date range ("Oct 17 – Oct 18, 2026") → photo credit → 2–4 sentences of voice → "Tickets start at $29" inside the prose. Price is never structured.
- **Annoying:** **three newsletter modals** in the SSR HTML (main, "The best of Chicago for free", magazine). Copy like "consent to receive… partner promotions". `ogimg` is empty on the Chicago hub. A GetYourGuide affiliate widget is embedded.
- **Gap:** editorial quality is high but the format is listicle-only, with no filters, no deadlines and no structured price.

### DoStuff (Do512/Do312/DoNYC) [X]/[K]
- Blocked today (403 on robots.txt and pages). From prior knowledge: `/events/today`, `/events/this-weekend`, `/events/{yyyy}/{mm}/{dd}/{slug}`, `/venues/{slug}`, and "Do Picks" plus "Free" lanes. Each event shows a big square flyer image. RSVP "I'm going" counts. Sponsored "Presented by" slots. Their ticketing arm sells for small venues. Ledger I-043 already rejects scraping them, and today's 403 reinforces that.

### Resident Advisor [X]/[K]
- Blocked (403). From prior knowledge: `/events/us/chicago`, `/events/{id}`, `/clubs/{id}`, `/dj/{slug}`. A strong taxonomy of genres, venues and artists. **An "Attending" count and a ticket tier ladder** that shows sold-out early tiers struck through and the next tier's price ("1st release SOLD OUT · 2nd release $25"), which is honest scarcity. A **resale queue at face value**. This is the best model for the "tier ladder" price display.

### Luma (discover) [L]
- **URL grammar:** city slugs at the root, `luma.com/chicago` plus `/chicago/map`; category slugs at the root too (`/tech`, `/running`, `/books`, `/climate`, `/ai`, `/crypto`); events are 8-char ids (`/zdw79cgk`) or vanity slugs. `lu.ma` now canonicalizes to `luma.com`.
- **Discover IA:** Popular Events (geo-guessed **Minneapolis** for our server) → Browse by Category with counts ("Tech 4K Events", "Running 655 Events") → **Featured Calendars** you can Follow → Explore Local Events.
- **City page:** "What's Happening in Chicago", a 2-sentence city blurb, **"Subscribe Chicago — get notified of new events before they sell out"**, and "Submit Event". Cards show title · "By {host}" · venue · price ("$85") or status (**"Sold Out"**, **"Near Capacity"**) · going count as "+22". JSON-LD is 20 `Event` + `Offer` + `Person` (hosts) + `GeoCoordinates`.
- **Images:** Cloudflare Images `cdn-cgi/image/format=auto,fit=cover,dpr=2,…`. A per-city generated social card (`discovery/chicago-social.png`) and city icon.
- **Gap:** the city mix tilts heavily to tech/AI/startup (OpenAI Forum, Investor Ready Workshop, TechNexus). "Near Capacity" is a binary state with no number.

### Partiful [L]
- **URL grammar:** `/explore/{city-code}` (`/explore/chi`, `/explore/nyc`, `/explore/la`, `/explore/sf`), `/explore/local`, events `/e/{20-char id}`.
- **Card format:** title · **relative time** ("Tomorrow at 12pm", "Next Fri at 7pm", "Sun at 11am") · city · **"570 Interested"**. Themed collections such as "all things fall" and "trending in chicago".
- **Standout trust pattern:** on events it didn't host, Partiful writes **"This event is not hosted by Partiful. It is an event we recommend, hosted by {Org}. Find more details at the link above."** Its editorial blurbs carry **newcomer-grade logistics**: "Street parking nearby is paid, so take the Pink Line to 18th & Ashland instead", "Arrive early… try the south end if the north end is crowded", "rain or shine, so bring layers". That is exactly the voice a newcomer needs.
- **Annoying:** "See more on the app" and "Get the app" gates. Host-written titles can be crude or odd. No price on most cards.

### Nextdoor events [X]/[K]
- Disallowed by robots.txt for us. Prior knowledge: requires a verified address; events sit in the feed, not in a calendar; the neighborhood granularity is unmatched. Nothing new beyond Part 1.

### Patch [L]
- **URL grammar:** `/{state}/{community}/calendar`, with neighborhoods as separate "communities" (`/illinois/lincolnpark`, `/illinois/bucktown-wickerpark`, `/illinois/lakeview`, `/illinois/hydepark`). The `<title>` carries the date ("Chicago Events Calendar for October 16, 2026"), a cheap daily-fresh SEO trick. Events are grouped by day headings ("Friday, October 16").
- **Annoying:** "Featured" is **paid placement** ("Promote Your Event", ~78 "promoted" strings in HTML). The first Featured item was a **gym opening ad**. There's no JSON-LD and the og:image is the Patch logo. I found a `polyfill.io` script reference in the HTML; that domain was compromised in a 2024 supply-chain attack, a red flag for a trust reference [K for the attack].
- **Gap:** neighborhood-community IA is good; the content is user-posted and promotional.

### Alt-weeklies [L]
- **Chicago Reader `/events/`:** shows **only two items, dated Sept 10 and Aug 25**. It's stale. The real calendar has moved to **EverOut Chicago** (linked in the header). The site is otherwise rich in trust: staff page, freelance guidelines, "local news public good", donate, print distribution map.
- **Racket (Twin Cities):** "writer-owned, reader-funded". Author pages (`/author/jessica-armbruster`) and a commenting policy. The weekly **"Freeloader Friday: 113 Free Things To Do This Weekend"** is a recurring, bylined, free-only roundup and a great format to emulate. Calendar is `/category/events`.
- **Austin Chronicle:** the calendar lives on a subdomain (`calendar.austinchronicle.com/austin/EventSearch?v=g`), `robots: nofollow`. **22 "Promoted" events stacked above the organic list**, then "This Weekend: **2,817 results, page 1 of 71**", which is too many results to scan. Category tabs include Queer, Out of Town, Family. "Submit an Event" is linked. Image proxy `/imager/{slug}/u/r-bigsquare/{id}`.
- **The Stranger / EverOut:** [X] 403. Prior knowledge: EverOut runs Seattle, Portland and Chicago (with the Reader) with **"Staff Pick"** badges, an "Event categories × this weekend" grid and ticketing.

### City tourism sites [L]
- **Choose Chicago `/events/`:** **date-stamped instance URLs** `/event/{slug}/2026-10-16`, plus `/event/series/{slug}` for recurring events. This is The Events Calendar (Tribe) markup ("Events Search and Views Navigation"), which our `tribe` adapter family already speaks. JSON-LD: 24 `Event` with `Offer` and `Person`, and an `FAQPage`. Header IA: "First-time visit", "On a budget", "Hidden gems", "LGBTQ+", "Chicago Greeter", **"The 77: A City of Neighborhoods"**, "Things to do this weekend / this month", "Submit an event". All copy is visitor-framed, with nothing for residents.
- **NYC Tourism `/things-to-do/`:** category hubs (`/things-to-do/nightlife`, `/sports`, "On a budget", "Browse by season"), an "AI-powered" discovery tool, photo credits ("Photo: Natasha Gornik and Jason Robinette"), `max-snippet:-1`. Ad tags (GPT) and Osano consent.
- **Visit Seattle `/things-to-do/events/`:** the calendar renders in JS, so almost nothing is in the SSR HTML. A **land acknowledgement** ("Seattle is Built on Native Land"), an **Accessible Travel Guide**, "Submit Your Event", and a DMAP accreditation seal (destination-marketing accreditation, an institutional trust badge).

### Trust and polish references
- **The Infatuation [L]:** a numeric score ("8.4") with a **"What Our Ratings Mean" explainer** ("An 8 should be on your must-try list…"). Bylines with contributor pages (`/contributor/nick-allen`). Each review shows **both a 2022 publish date and a 2026-09-18 re-review date**, so freshness is visible. A "Perfect for: BYOB · Fine Dining" intent tag. "The Hit List" and "Just Published" lanes. Photographer credit embedded in the Cloudinary asset names. URLs: `/{city}/reviews/{slug}`, `/{city}/guides/{slug}`, `/{city}/neighborhoods/{slug}`, `/{city}/cuisines/{slug}`. The annoying part is a "Chase customers" exclusive-content upsell.
- **Resy [L, shallow]:** a pure Angular SPA; the SSR HTML is a 5 KB shell with no crawlable content at `/cities/chicago-il`. That's an **SEO counterexample** for us, since our dashboard is also hash-routed. [K] Resy's polish comes from editorial "Hit List"s and a calm, image-first card UI with no urgency badges.
- **Airbnb Experiences [L, shallow]:** `/s/Chicago/experiences` is `noindex, nofollow`, and its SSR HTML holds placeholder text only. [K] Its trust stack is the reference: host identity verification, review count + star average, a "Superhost"-style badge, a clear cancellation policy ("Free cancellation up to 24 h before"), and a guarantee page.

---

## 2. Cross-cutting observations

**URL patterns observed [L]**

| Pattern | Who | Note |
|---|---|---|
| `/{city}/things-to-do/{evergreen}` rewritten weekly | Time Out | One URL accumulates ranking; the title carries the dates |
| `/d/{st}--{city}/{facet}--{facet}/` | Eventbrite | Facet combos are indexable, with canonical = self |
| `/find/{country}--{st}--{city}/` indexed; `/find/?…` noindex | Meetup | Index the hub, noindex the faceted search |
| `/en/{city}/{category}` + opaque `/m/{id}` | Fever | Category hubs indexed; detail ids opaque |
| `/{city}` + `/{city}/map` + `/{category}` at the root | Luma | Shortest URLs in the set |
| `/explore/{citycode}` | Partiful | |
| `/event/{slug}/{yyyy-mm-dd}` + `/event/series/{slug}` | Choose Chicago (Tribe) | Best model for recurring instances |
| `/{state}/{neighborhood}/calendar` + date in title | Patch | Neighborhood as a first-class page |
| `/browse/{city}-{hexid}` | DICE | Anti-pattern: id in the city URL |

**Images [L]:** everyone serves through a transform CDN (imgix, Cloudinary, Cloudflare Images) with **subject-aware crops** (`g_auto`, `crop=focalpoint&fp-x/fp-y`, `fit=cover`). Card ratios: Fever ~3:2, DICE/Luma/DoStuff 1:1 flyers, Time Out 4:3 (750×562), Infatuation 16:9 and 4:3. Editorial sites always **credit** photos. Event-host artwork is often text-heavy flyers, which crop badly in landscape. DICE and DoStuff use square cards for that reason.

**Price and scarcity signals [L]**

| Site | Price | Scarcity |
|---|---|---|
| Eventbrite | Price often missing from SSR cards; `AggregateOffer` low/high in JSON-LD | "Almost full", "Sales end soon", "Going fast" on most cards (no signal) |
| DICE | All-in, cents-exact ("$41.93") | Mostly none on the browse page |
| Fever | "From $X", "- 20%" with a struck price | "Waitlist", ratings |
| Luma | "$85" or nothing | "Sold Out", "Near Capacity", "+22" going |
| Partiful | Rarely | "570 Interested" |
| Time Out | In prose ("Tickets start at $29") | "limited capacity" in prose |
| RA [K] | Tier ladder | Struck-through sold-out tiers |

**Freshness:** the only sites that expose a machine-readable "last updated" are Time Out (`dateModified`, same day) and The Infatuation (re-review date). Patch puts today's date in the title. No calendar shows **when an individual listing was last checked**. Our I-035 "checked 2h ago" is unique in this set.

---

## 3. Fifteen adoptable patterns (ranked)

1. **Pre-rendered, indexable city × intent landing pages** (`/chicago/this-weekend`, `/chicago/free`, `/chicago/meet-people`, `/chicago/deadlines`) with `ItemList` + `Event` JSON-LD and canonical = self. *Why:* Eventbrite, Meetup and Fever win search with exactly this. Our hash-routed SPA is invisible to search, the same failure as Resy's and Airbnb's shells. A static build step can emit HTML per city/lane from the JSON we already export.
2. **Evergreen URL with dated title**: `/chicago/this-weekend` rewritten each run, titled "Things to do in Chicago this weekend: Oct 16–18", with `dateModified` set to build time. *Why:* Time Out's trick: one URL accumulates links, and the title shows freshness.
3. **"Not hosted by us. We recommend it; hosted by {Org}" provenance line** on every card or drawer, linked to the source. *Why:* Partiful's line is the clearest provenance copy in the set, and it maps directly onto our `source` field.
4. **Newcomer logistics line**: transit stop, parking reality, "arrive early", rain plan, generated only from structured facts (GTFS stop distance, outdoor flag, weather). *Why:* Partiful's best blurbs are logistics, and newcomers lack exactly that knowledge. Label it as derived.
5. **Intent lanes on the city home**: Today → This weekend → Meet new people → Free → Closing soon → Sports & fitness → Live music. *Why:* Meetup's hub IA beats category trees for a newcomer, and "Meet new people" is our core promise.
6. **Group/organizer track-record chip**: "Meets weekly since 2019 · ~30 people · 359 past events", from our own history or the source. *Why:* Meetup's "4.8 · 1,276 ratings · 8,415 members · 359 past events" is the most persuasive trust block observed.
7. **All-in price, rendered DICE-style**: one price string per card, "Free" as a first-class value, "from" only when tiers exist, plus a "fees included?" marker when the source tells us. *Why:* DICE's cents-exact all-in prices read as honest. Eventbrite and Fever lead with base "From" prices.
8. **Tier-ladder display for price steps**: "Early bird $40 (ended) · Regular $55 · closes Nov 2". *Why:* RA's ladder [K] is honest scarcity. We already track Volo price steps (I-077), so this renders data we have.
9. **Recurring-instance URLs**: `/{city}/e/{slug}` for the series and `/{city}/e/{slug}/2026-10-16` per occurrence. *Why:* the Choose Chicago (Tribe) model. It pairs with series collapse (I-013) and gives each occurrence a shareable deep link.
10. **Weekly bylined-style roundup: "Free this weekend: N things"**, generated from data with a fixed format and a count in the title. *Why:* Racket's "Freeloader Friday: 113 Free Things" and Time Out's weekend list show the format drives return visits. The count is a cheap trust and value signal.
11. **"What our signals mean" explainer** linked from every badge (social score, attendance band, "closing soon", "checked 2h ago"). *Why:* The Infatuation's "What Our Ratings Mean" turns a number into a trust asset, and our estimates already carry a method.
12. **Subject-aware image pipeline with square-first cards and credits**: choose 1:1 for flyers, 4:3 for venue photos, and show "Image: {source}" credit. *Why:* every polished site crops with focal points, and editorial sites always credit. Flyers crop badly to landscape.
13. **Neighborhood as a first-class page** (`/chicago/n/logan-square`). *Why:* Patch and Choose Chicago ("The 77") both do this. It also lines up with our neighborhood polygons and vibe cards (I-051).
14. **Follow and subscribe per city or lane via ICS/RSS/email, no account**. *Why:* Luma's "Subscribe Chicago: get notified before they sell out" and its followable calendars, without Luma's sign-in.
15. **Relative time on cards, absolute in the drawer**: "Tomorrow 12pm", "Next Fri 7pm" on cards; the full date and timezone in detail. *Why:* Partiful's cards are the most scannable in the set, and Time Out spells out full date ranges. Use both, each in its place.

## 4. Ten anti-patterns to avoid

1. **Badge inflation.** Eventbrite showed "Almost full / Sales end soon / Going fast" on most of ~40 weekend cards, which turns the badges into noise. Cap badges to sourced facts, at most one per card.
2. **Paid placement disguised as editorial.** Patch's "Featured" items are paid (one was a gym opening), and the Austin Chronicle stacks 22 "Promoted" events above organic results. If we ever take money, label it and never rank it inside organic lanes.
3. **Stale calendar pages left live.** Chicago Reader `/events/` shows only Aug–Sep items in mid-October. Auto-hide lanes with zero future items and show "last updated" on every list.
4. **Online events in a city feed.** Eventbrite and Meetup both mix in online events. Exclude them by default.
5. **Multi-date events shown as "this weekend"** without the actual date (Eventbrite "Multiple dates"). Always show the next occurrence date.
6. **Modal and newsletter stacking.** Time Out ships three newsletter modals per page. Offer one inline, dismissible subscribe at most, never on first paint.
7. **App gates and sign-in walls for browsing.** Partiful ("See more on the app"), Airbnb/Resy JS-only shells, Meetup RSVP. All value has to stay readable without an account.
8. **Unreadable or opaque URLs.** DICE `/browse/chicago-5b238ca66e4bcd93783835b0`, Fever `/m/689305`. Use human slugs, keep ids internal, keep URLs stable.
9. **Hidden refund terms.** Fever buries "No refunds are permitted under any circumstances" in FAQ #n. When a source exposes a refund policy (Eventbrite "Good to know"), show it on the card's ticket offer.
10. **Third-party script risk and ad clutter.** Patch still references `polyfill.io`; tourism sites load GPT ad tags and multiple trackers. Ship zero third-party JS by default and self-host fonts.

## 5. Trust checklist (what GetOffTheCouch should meet)

- [ ] **Provenance on every item:** source name + link + "not hosted by us" wording (Partiful pattern). Already partly in schema.
- [ ] **Per-item freshness:** "checked N h ago" (I-035, done), plus a page-level `dateModified`.
- [ ] **Stale lanes self-hide** and show the reason (no future items, source degraded) and a link to Health.
- [ ] **Signal explainer page** for social score, attendance band, deadlines and price trend, with methods (links to METHODOLOGY).
- [ ] **Honest price:** all-in when known, "Free" verified or derived (labeled), fees disclosed, no struck-through "discounts" we can't source.
- [ ] **Scarcity only with evidence:** sold out, closing date, tier ended. No "% left" (I-045 rejected), no "N people viewing".
- [ ] **Refund/cancellation terms** shown on ticket offers when the source provides them.
- [ ] **Organizer track record** (recurrence, age, typical size) on community events.
- [ ] **No paid placement** (or if ever, a labeled lane, separate from ranking). Say so on About.
- [ ] **About page:** who runs it, how events are chosen, what's automated vs curated, the source list (link to SOURCES.md), and the robots/ToS stance.
- [ ] **Privacy page:** no accounts needed, localStorage only, no third-party trackers, and how share links encode state.
- [ ] **Corrections path:** "report a problem" on every card (I-052, done) + a public changelog/diary.
- [ ] **Image credits** and no hot-linking of images whose terms forbid it. Fall back to category art.
- [ ] **Accessibility statement** + accessible/sober filters (I-069, done), following the Visit Seattle accessible-travel guide.
- [ ] **Structured data validity:** `Event` JSON-LD with `eventStatus`, `offers.availability`, `isAccessibleForFree`, and no fabricated fields (validate in CI).
- [ ] **Demo data never mixed in** (`is_demo`), visibly banner-labeled when shown.

## 6. Idea candidates (for `python -m gotc.ideas add`)

`title | area | value 1-5 | effort 1-5 | why`

1. Static pre-render of city × lane pages with Event/ItemList JSON-LD | features | 5 | 3 | The hash-routed SPA is invisible to search; Eventbrite, Meetup and Fever win SEO with indexable city/facet hubs [L]
2. Evergreen `/{city}/this-weekend` page with dated title and `dateModified` | design | 4 | 2 | Time Out rewrites one URL weekly with "Oct 16–18" in the title [L]; freshness doubles as a trust signal
3. "Not hosted by us. Recommended, hosted by {Org}" provenance line on cards | trust | 4 | 1 | Partiful's wording is the clearest provenance copy observed [L]; the data is already in `source`
4. Derived newcomer logistics line (nearest transit stop, outdoor/rain, arrive-early for free fests) | features | 4 | 3 | Partiful's best blurbs are logistics ("take the Pink Line instead") [L]; pairs with I-067 GTFS and I-018 weather
5. Organizer track-record chip from our own history (first seen, occurrences, typical size) | trust | 4 | 2 | Meetup's ratings/members/past-events block is the strongest trust display [L]; we can compute it from `first_seen` and series
6. Badge budget: at most one urgency badge per card, each must cite evidence | ranking | 4 | 1 | Eventbrite badges cover most cards, so they carry no signal [L]
7. Price tier ladder render (ended tiers struck, next step + date) | design | 3 | 2 | RA's honest ladder [K]; we already capture Volo price steps (I-077)
8. Weekly "Free this weekend in {city}: N things" auto-roundup page + ICS/RSS | features | 4 | 2 | Racket's "Freeloader Friday: 113 Free Things" is a proven recurring format [L]
9. Auto-hide empty or stale lanes with a visible reason | trust | 3 | 1 | Chicago Reader's events page shows only Aug–Sep items in October [L]
10. Ingest Choose Chicago via the existing Tribe adapter (date-stamped `/event/{slug}/{date}` instances) | sources | 3 | 2 | The SSR HTML exposes 24 Event JSON-LD items with Offers in Tribe markup [L]; check robots/ToS per SOURCES.md first

---

*Method notes:* fetch script = stdlib `urllib.robotparser` + `urllib.request`. Raw HTML was kept in `/tmp` only (not committed). No pages behind a 403 or a robots disallow were retried with other UAs. Counts ("×14", "~240") are string occurrences in the SSR text of a single page load on 2026-10-16, so treat them as indicative, not exact.
