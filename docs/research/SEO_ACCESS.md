# Findability, performance and access: research and plan

Researched on 2026-10-16. Sources are cited inline. **[V]** means I checked it against our live site or repo today (curl, file sizes). **[K]** means it comes from prior knowledge of the cited docs; re-read the linked page before relying on an exact number. Google's docs change often, and the event rich result in particular has been reshaped more than once.

## 0. Where we are today [V]

| Fact | Value | Why it matters |
|---|---|---|
| Routing | Hash only: `#/chicago/feed`, `#/chicago/event/evt_…` (`web/src/lib/router.ts`) | Google ignores fragments for indexing. To a crawler our whole site is **one URL** with an empty `<div id="app">`. |
| HTML shell | `web/index.html`: one title, one description, `<noscript>` message, no OG tags, no JSON-LD | Share previews are the same for every city and event. Nothing in it can rank. |
| Vite `base` | `"./"` (relative) | Works for a single page. Breaks the moment a page lives at `/chicago/concerts/`, because `./assets/…` then resolves under that folder. |
| Initial JS / CSS | 33.4 KB / 6.5 KB gzip (live `index-*.js`, `index-*.css`) | Already well under budget. Leaflet is already `import()`-ed lazily in `LeafletMap.tsx`. |
| Fonts | System stacks only (`--font`, `--font-display` in `app.css`) | No web-font cost and no font-swap CLS. Keep it that way. |
| City feed JSON | 0.77 to 3.3 MB raw, **170 to 470 KB gzip**, plus `*.details.json` at 84 to 245 KB gzip | This is our real LCP problem. Nothing renders until the whole city file has downloaded and parsed. |
| Events | About 12.3k across 10 cities: one_off 5.1k, recurring 4.3k, opening 1.6k, season 0.4k. **0 have an image.** | Sets the page count and shapes the structured-data choices below. |
| Pages compression | `content-encoding: gzip` even when the request sends `Accept-Encoding: br, gzip`. **No brotli.** | Gzip is all we get, so payload budgets should be set in gzip bytes. |
| Pages caching | `cache-control: max-age=600` on every file, weak `ETag`, `Last-Modified` | We can't change these headers. `data.ts` uses `cache: "no-cache"`, which revalidates and gets a cheap 304 when nothing changed. |
| Pages 404 | Unknown paths return a real **HTTP 404** with `404.html` | The "404.html SPA trick" can never get a page indexed (§1.4). |
| Trailing slash | `/GetOffTheCouch` → **301** → `/GetOffTheCouch/` | Pages already normalizes directories to a trailing slash. Make our canonicals agree. |
| robots.txt | `https://lachlanspangler.github.io/robots.txt` → 404 | A project site **cannot own robots.txt**, which lives at the host root (§3.2). |
| a11y tests | `web/e2e/a11y.spec.ts` runs axe with tags `wcag2a, wcag2aa` on 5 views | It misses the WCAG 2.1 and 2.2 rule tags and the map view, and never tests with the drawer open. |

---

## 1. From hash routes to real, pre-rendered paths

### 1.1 Why
- Google: "use the History API instead of fragments… Googlebot can't reliably resolve URLs with fragments" ([JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)). The old `#!` AJAX crawling scheme was deprecated in 2015 [K].
- Google can render JS, but rendering is deferred, and every page needs its own URL, `<title>`, description and links in the HTML anyway ([JS SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics); [Links crawlable](https://developers.google.com/search/docs/crawling-indexing/links-crawlable): links must be `<a href>`, not `onclick`).
- Social scrapers (Facebook, iMessage, Slack, Discord, X) **do not run JS**. OG tags must be in the static HTML.
- web.dev's rendering guidance recommends static rendering for content that is the same for everyone ([Rendering on the Web](https://web.dev/articles/rendering-on-the-web)). A city's event list fits that exactly: it is rebuilt hourly and identical for every visitor.

### 1.2 Path scheme (proposal)

All paths sit under `BASE` (`/GetOffTheCouch/` today, `/` on a custom domain). Every page path ends with a trailing slash and is served from `<path>/index.html`.

| Path | Page | Indexable | Notes |
|---|---|---|---|
| `/` | Home and city picker | yes | |
| `/chicago/` | City feed, next 7 days, top ~30 events | yes | the main landing page |
| `/chicago/this-weekend/` `/chicago/today/` `/chicago/this-week/` `/chicago/free/` | Time and price slices | yes | high-intent queries ("things to do in chicago this weekend") |
| `/chicago/concerts/`, `/chicago/trivia/`, `/chicago/run-clubs/`, `/chicago/beer-leagues/`, `/chicago/volunteering/` … | Category hubs, one per top-level `taxonomy.yaml` id, with human slugs | yes, but only if ≥ 5 upcoming items | below the threshold: `noindex` (avoids thin pages, §1.8) |
| `/chicago/deadlines/` | Deadlines | yes | our differentiator. No Event markup (§2.4) |
| `/chicago/openings/` | New bars and restaurants | yes | no Event markup |
| `/chicago/events/<slug>-<id>/` | Event detail | yes | slug from the title (`kebab`, ≤ 60 chars), id = the trailing hex part of `evt_…`. The id is authoritative and the slug is cosmetic. |
| `/chicago/series/<slug>-<id>/` | Recurring series (trivia every Tue) | yes | **one page per series**, not one per occurrence. Cuts page count by about 35%. |
| `/chicago/calendar/`, `/chicago/map/`, `/chicago/plan/`, `/chicago/saved/`, `/health/`, `/about/` | App views | calendar, map and plan: `noindex,follow`. Health and about: yes | pre-render a shell only |
| `?when=…&cats=…&free=1&near=…` | Filter state | no; canonical points to the path without the query | filters stay in the query string so every view remains shareable |

Legacy links: on boot, `if (location.hash.startsWith("#/"))`, translate the hash with the existing `parse()` and call `history.replaceState` to the new path. Every link shared so far keeps working. Keep `parse()`/`build()` as pure functions with the existing `router.test.ts`, and add path cases.

### 1.3 Pre-rendering with Vite + Preact

Two workable options:

**A. `@preact/preset-vite` built-in prerender** (`prerender: { enabled: true, renderTarget: "#app", additionalPrerenderRoutes: [...] }`). The entry exports `prerender(data)` returning `{ html, links, head }`, and it crawls `links` ([preset-vite README](https://github.com/preactjs/preset-vite#prerendering-configuration)) [K]. Good for the ~400 hub pages. For 10k to 100k event pages it is less controllable: memory, concurrency, and no incremental skip.

**B. Our own Node prerender script (recommended).**
1. `vite build` builds the client as today, with `base` from an env var (§1.5).
2. `vite build --ssr src/entry-server.tsx --outDir dist-ssr` produces an SSR bundle that exports `render(route, data): { html, head }` using `preact-render-to-string`'s `renderToString` ([preact-render-to-string](https://github.com/preactjs/preact-render-to-string)).
3. `node scripts/prerender.mjs` reads `public/data/index.json` and the city files. For each route it renders the app tree, injects the HTML into `#app`, injects `<head>` tags (title, description, canonical, OG, JSON-LD) into `dist/index.html`'s template, and writes `dist/<path>/index.html`. It streams writes, uses a small worker pool, and skips writing when the content hash is unchanged so `mtime` and `lastmod` stay honest.
4. In the client entry, call `hydrate(<App/>, el)` when `el.firstChild` exists and `render` otherwise ([Preact hydrate](https://preactjs.com/guide/v10/api-reference/#hydrate)). Hydration needs the same data the server used. See §4.6 for inlining a small payload.
5. Event pages don't need to hydrate the whole app. Ship them as **mostly static HTML** plus the normal app bundle loaded with `type="module"` (it's 33 KB). The bundle takes over on the first interaction or navigation. This is an islands approach in spirit, and it keeps INP trivially good.

Things that must be SSR-safe in components: no `window`, `localStorage` or `matchMedia` during render. `store.ts` (saved events) and the time helpers must accept "now" as a parameter. Render relative dates ("tonight") on the client only, and server-render absolute dates (`Sat Oct 18, 7 PM`) in the **city's** timezone. Otherwise hydration mismatches and CLS follow.

### 1.4 The 404.html trick and why it isn't enough
The common GitHub Pages SPA hack copies `index.html` to `404.html` so any path boots the app ([rafgraph/spa-github-pages](https://github.com/rafgraph/spa-github-pages)). Pages serves that file **with status 404** [V], and Google doesn't index 404s ([HTTP status codes and Google](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)). Use 404.html only as a **fallback**:
- It contains the app shell plus a script that tries to route the path client-side. That covers event ids not yet pre-rendered, expired events, and typos.
- It renders "This event has ended or moved. Here's what's on in Chicago this week" and links to `/chicago/`. Never a blank page.
- It keeps `noindex`, which is implied by the 404 anyway.

### 1.5 Base path, custom domain, canonicals, trailing slashes
- `vite.config.ts`: `base: process.env.GOTC_BASE ?? "/GetOffTheCouch/"`, an absolute path. Add a `SITE_ORIGIN` env (`https://lachlanspangler.github.io`). Put a single `site.ts` helper in `web/src/lib/` that exports `BASE`, `ORIGIN`, `url(path)` and `canonical(path)`. Every `<a href>`, canonical, sitemap entry, OG URL and JSON-LD URL goes through it. `data.ts` already uses `import.meta.env.BASE_URL`.
- Custom domain later: set it in repo Settings → Pages. With an Actions-based deploy, a `CNAME` file in the artifact isn't required ([Managing a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)) [K]. Then flip `GOTC_BASE=/`. Pages 301-redirects the `github.io` URL to the custom domain, and Google treats that as a site move ([Site moves](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes)). So **decide on the domain early**, before Google has indexed many `github.io` URLs.
- Canonical: every indexable page carries `<link rel="canonical" href="https://…/GetOffTheCouch/chicago/concerts/">`, absolute and self-referencing with a trailing slash. Filtered and query URLs point to the clean path ([Consolidate duplicate URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)).
- Trailing slash: Pages already 301s `/x` → `/x/` for directories [V]. Always link to the slash form so crawlers never hit the redirect.
- hreflang: **not needed**. The site is English-only and US-only ([Localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions) applies only to multiple language or region variants).

### 1.6 How big can it get on GitHub Pages?
From [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) [K]: the published site is **≤ 1 GB**, bandwidth has a **soft 100 GB/month** cap, and **deployments time out after 10 minutes**. The 10 builds/hour soft limit does not apply to custom Actions workflows. Pages documents no file-count limit.

Budget math. Pre-rendered event HTML without inline app data is about 5 to 8 KB raw, assuming the CSS and JS stay external and cached.

| Scenario | Pages | Raw size (event pages) | Verdict |
|---|---|---|---|
| Today: ~12k events, series collapsed (~8k pages) | ~8.5k | ~60 MB | fine |
| 30 cities, upcoming 60 days only | ~30k | ~220 MB | fine |
| 100k pages | 100k | ~700 MB, plus ~40 MB data JSON plus OG images | **too close to 1 GB**. Needs pruning or a move off Pages. |

The bigger risk is **deploy time**: tarring, uploading and propagating 100k files every hour against the 10-minute deploy timeout and the 45-minute job. Mitigations:
1. **Only upcoming events**: `end ≥ now − 1 day` and `start ≤ now + 90 days`. Openings older than 90 days drop out.
2. **One page per recurring series**, not per occurrence.
3. **Skip unchanged writes** (content-hash cache in `data/prerender-cache.json` persisted with the pipeline state). This doesn't shrink the artifact, because Pages always uploads the full site, but it keeps build CPU low and `lastmod` truthful.
4. Hard CI guard: fail the build when `du -sb dist` exceeds 800 MB or the file count exceeds 60k. That gives an early warning well before the platform limit.
5. Escape hatch, if we ever outgrow this: Cloudflare Pages has a 20k-file limit on the free tier [K]. Cloudflare in front of Pages, or S3 + CloudFront, adds brotli, real 301 and 410 responses, and custom headers. Write an ADR if we take it.

### 1.7 Expiring event pages
Pages can't send 301 or 410 responses. A three-stage lifecycle, computed at build time from `end`/`start`:

| Age after event end | What's served | Why |
|---|---|---|
| 0 to 7 days | The full page with a visible "This event has ended" banner. **Remove the Event JSON-LD**, because Google doesn't show past events and the markup should match reality. Add `robots: noindex` and links to similar upcoming events. | Shared links still land somewhere useful. |
| 7 to 60 days | A tiny stub: `<meta http-equiv="refresh" content="0; url=/…/chicago/">`, `noindex`, canonical pointing to the city, and a visible link. Google treats an instant meta refresh as a permanent redirect ([Redirects](https://developers.google.com/search/docs/crawling-indexing/301-redirects#metarefresh)). | The closest thing to a 301 we can get on Pages. |
| > 60 days | Delete the file. The path returns a 404 via 404.html, which offers the city fallback. Google treats 404 and 410 nearly the same over time ([HTTP status codes](https://developers.google.com/search/docs/crawling-indexing/http-network-errors)). | Keeps the site size bounded. |

Cancelled and postponed events keep their page with `eventStatus` set (§2) instead of being deleted.

### 1.8 Quality guardrails (spam policy)
Mass-generated pages with little value can fall under Google's **scaled content abuse** policy ([Spam policies](https://developers.google.com/search/docs/essentials/spam-policies#scaled-content)). Our pages carry real, sourced data, but:
- `noindex` any hub with fewer than 5 upcoming items, and never emit empty category × city pages.
- Each event page shows source attribution and the "last checked" time (we have `sources[]`, `last_checked`). These are E-E-A-T trust signals ([Creating helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)).
- Don't pre-render demo data. `is_demo: true` pages must never reach `dist/` on the production deploy. The refresh job runs `gotc demo` before the build, so the prerender script must skip `public/demo/`.

---

## 2. schema.org Event structured data

### 2.1 What Google requires and recommends
From [Google Event structured data](https://developers.google.com/search/docs/appearance/structured-data/event) [K] and [schema.org/Event](https://schema.org/Event):

| Property | Google status | Our source field | Rule for us |
|---|---|---|---|
| `name` | **required** | `title` | Strip our own suffixes like " — new liquor license". |
| `startDate` | **required** | `start` | ISO 8601 **with the UTC offset** (`2026-10-18T19:00:00-05:00`). For all-day events, a date only (`2026-10-18`). We already store offset-aware datetimes in the city tz. |
| `location` | **required** | `location` | `Place{ name, address: PostalAddress{ streetAddress, addressLocality, addressRegion, postalCode, addressCountry: "US" } }`. Add `geo` if we have it. Online: `VirtualLocation{url}`. Mixed: an array of both. If we only have lat/lon with no street address, **omit the markup**, because an address is required for physical events. |
| `description` | recommended | `summary` (details file has full) | Must match visible text. |
| `endDate` | recommended | `end` | Same format as `startDate`. |
| `eventStatus` | recommended | (new: `status`) | `EventScheduled` / `EventCancelled` / `EventPostponed` / `EventRescheduled` (+ `previousStartDate`) / `EventMovedOnline`. Never delete a cancelled event page; mark it. |
| `eventAttendanceMode` | recommended | derived | `OfflineEventAttendanceMode` / `OnlineEventAttendanceMode` / `MixedEventAttendanceMode`. |
| `image` | recommended | none (0/12k have one) | Google: several high-res images, aspect ratios 16:9, 4:3 and 1:1, each with at least 50k pixels (w×h). See §2.3. |
| `offers` | recommended | `offers[]`, `price` | `Offer{ url, price, priceCurrency: "USD", availability, validFrom }`. `availability`: `InStock` / `SoldOut` / `PreOrder` (from `tickets.availability`). **Only reported prices.** Never put estimates or trend-derived numbers in markup (ADR 0006). Free: `price: 0`. Multiple tiers: `AggregateOffer{lowPrice, highPrice, offerCount}` [K]. `validFrom` = onsale time when known. |
| `organizer` | recommended | source org / venue operator | `Organization{name, url}`. Omit if unknown. |
| `performer` | recommended | ticketing performers (TM/SeatGeek) | `PerformingGroup` or `Person {name}`. Omit if unknown. |

Use `@id` = canonical URL + `#event`, and `url` = canonical URL. Put it in a `<script type="application/ld+json">` in `<head>`, server-rendered (Google can read JS-injected JSON-LD, but static is more reliable: [Generate structured data with JavaScript](https://developers.google.com/search/docs/appearance/structured-data/generate-structured-data-with-javascript)).

### 2.2 Which of our `kind`s get markup

| kind | Markup | Reason |
|---|---|---|
| `one_off` | `Event` | It's a dated happening. |
| `recurring` | Series page: one `Event` per **next ≤ 5 occurrences**, each with its own `startDate` | Google wants each occurrence as its own Event [K]. More than a few becomes spammy. |
| `season` (league) | **No Event markup.** Mark up individual dated games or tryouts if we have them. | A season or registration window isn't a single event, and Google warns against marking multi-week spans as one event [K]. `EventSeries` isn't a supported rich result. |
| `opening` | **None** | A license signal isn't an event. Marking it up breaks the content guidelines. |
| `deadline` | **None** | Google's guidelines explicitly exclude non-events such as deadlines, sales and business hours. |

Google's event content policies [K] ([Event guidelines](https://developers.google.com/search/docs/appearance/structured-data/event#guidelines); [General structured data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)):
- Don't mark up non-events (coupons, packages, "sale ends", business hours) as events.
- Markup must describe content visible on the page and be accurate. Wrong dates and prices can earn a manual action.
- Multi-day events need correct start and end dates. Multiple performances each get their own Event.
- Don't mark up events on a page that isn't about that event. Hubs and lists should link to detail pages, not carry 30 inline Events. We choose **detail pages only**.

Also mark up the site as a whole: `WebSite` (name, url) on the home page ([Site names](https://developers.google.com/search/docs/appearance/site-names)) and `BreadcrumbList` on event and hub pages ([Breadcrumb](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb)).

Caveat [K]: Google has narrowed rich-result features over 2023 to 2025. The events experience is region- and language-limited and has been reworked several times. Even without a rich result, markup still feeds Google's understanding of the page, and it is the same data that calendar apps and other consumers parse. That makes it worth doing, but don't count on traffic from a rich result.

### 2.3 Images when we have none
- Omitting `image` produces only a *warning*, not an error. Start without it.
- Don't hot-link or republish source images until each source's ToS allows it. Track this in `docs/SOURCES.md` per source. Ticketmaster's Discovery API returns images with license terms. Respect them.
- Our generated OG card (§3.4) at 1200×630, about 756k px, technically satisfies the size rule. Google says images should be "relevant to the event", so a text card carrying title, date and venue is acceptable but low value. Use it for OG/X. Add it to JSON-LD only if Search Console shows the missing-image warning blocking eligibility.

### 2.4 Validation offline in CI
The Rich Results Test ([search.google.com/test/rich-results](https://search.google.com/test/rich-results)) and the Schema Markup Validator ([validator.schema.org](https://validator.schema.org/)) are web-only and have no public API for bulk use. Use them manually on a sample after each schema change. For CI:
1. **Typed builder**: generate JSON-LD in `web/src/lib/seo/jsonld.ts` typed with Google's [`schema-dts`](https://github.com/google/schema-dts) package (`WithContext<Event>`). Wrong property names fail `tsc`.
2. **Rule tests (vitest)**: our own assertions mirroring Google's required and recommended table above: offset in `startDate`, `PostalAddress` complete, `priceCurrency` present when `price` is, no markup for `opening`/`deadline`/`season`, no price unless the offer is reported, `url` equals canonical. This is the reliable offline check.
3. **Post-build crawl (Node)**: parse every `dist/**/index.html`, extract `application/ld+json`, run (2) on each, and confirm the JSON parses. Optional third-party validators to evaluate: [`@adobe/structured-data-validator`](https://github.com/adobe/structured-data-validator), which mimics Google's rich-result rules, and [`structured-data-testing-tool`](https://github.com/glitchdigital/structured-data-testing-tool), which has Google presets but is less maintained [K]. Pin whichever passes a known-good fixture.
4. Python side (optional): [`extruct`](https://github.com/scrapinghub/extruct) can extract JSON-LD from fixtures for a contract test in `tests/contract/`.
5. After launch, the Search Console **Enhancements → Events** report is the ground truth.

---

## 3. Sitemaps, robots, feeds, share previews

### 3.1 Sitemaps
Rules ([Build a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap); [Sitemap index](https://developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps); [sitemaps.org](https://www.sitemaps.org/protocol.html)):
- Each file holds at most 50,000 URLs and 50 MB uncompressed. An index lists at most 50,000 sitemaps.
- Google ignores `priority` and `changefreq`. It uses `<lastmod>` **only if it is consistently accurate**. Set it to the max of the event's `last_checked` change (real content change, not the hourly fetch) and the template version. Our content-hash skip (§1.6) gives this for free.
- A sitemap may only list URLs at or below its own directory, so `/GetOffTheCouch/sitemap.xml` can list everything under `/GetOffTheCouch/`.

Layout:
```
sitemap.xml                    ← index
sitemaps/hubs.xml              ← home, cities, slices, categories (indexable only)
sitemaps/chicago-events.xml    ← per city; split -1, -2 … if > 45k
```
Only indexable, canonical, 200-status URLs go in. No `noindex` pages and no stubs. Google also accepts RSS/Atom as sitemaps ([Sitemap formats](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap#rss)), so the per-city "new this week" feed can be submitted as a fast-moving sitemap.

### 3.2 robots.txt: the project-site catch
robots.txt is only read at the **host root** ([robots.txt intro](https://developers.google.com/search/docs/crawling-indexing/robots/intro)). For `lachlanspangler.github.io/GetOffTheCouch/` that file belongs to the `lachlanspangler.github.io` user-site repo, and it currently 404s [V], which Google treats as allow-all. So, until a custom domain exists:
- Submit the sitemap in **Search Console** under a URL-prefix property `https://lachlanspangler.github.io/GetOffTheCouch/`, verified with an HTML file or meta tag that we ship in `dist/` ([Verify ownership](https://support.google.com/webmasters/answer/9008080)).
- Use per-page `<meta name="robots" content="noindex">` for anything we don't want indexed. robots.txt `Disallow` would actually prevent Google from seeing `noindex` ([Block indexing](https://developers.google.com/search/docs/crawling-indexing/block-indexing)).
- With a custom domain, ship `robots.txt` (`User-agent: *`, `Allow: /`, `Sitemap: https://…/sitemap.xml`). Don't disallow `/data/`: Google needs the JSON to render client-side views, and blocking resources breaks rendering.

### 3.3 RSS and ICS per city
- `/<city>/feed.xml` (Atom 1.0 or RSS 2.0, [RSS 2.0 spec](https://www.rssboard.org/rss-specification)): new upcoming events, sorted by `first_seen`, last 100 items. Add `<link rel="alternate" type="application/atom+xml">` in the city `<head>` so readers auto-discover it.
- `/<city>/calendar.ics`, plus `/<city>/<category>/calendar.ics` for the top categories ([RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)). Reuse `web/src/lib/ics.ts`. Offer it as a `webcal://` subscribe link. Google Calendar polls subscribed ICS feeds only every several hours [K], which is fine for us. Keep each file ≤ 1 MB (next 60 days). Include `DTSTAMP`, a stable `UID` (`<event id>@getoffthecouch`) and `URL` = canonical. **Deadlines** become all-day `VEVENT`s in a separate `deadlines.ics`. That's our differentiator, so make it one tap away.

### 3.4 Open Graph and X cards
- Required OG tags ([ogp.me](https://ogp.me/)): `og:title`, `og:type` (`website`), `og:url` (canonical), `og:image` (**absolute URL**), plus `og:description`, `og:site_name`, `og:image:width`/`height`/`alt`. X: `twitter:card=summary_large_image` and `twitter:image:alt` ([X cards markup](https://developer.x.com/en/docs/x-for-websites/cards/overview/markup)). X falls back to OG for title, description and image.
- Size: 1200×630 (1.91:1) is the de-facto standard (Facebook's [sharing best practices](https://developers.facebook.com/docs/sharing/webmasters/images/)). X `summary_large_image` accepts up to 5 MB [K].
- Generate at build time with [satori](https://github.com/vercel/satori) (JSX → SVG) and [@resvg/resvg-js](https://github.com/yisibl/resvg-js) (SVG → PNG). satori needs a TTF, OTF or WOFF font buffer (**not WOFF2**). Bundle one OFL font, e.g. Inter or Nunito, in `web/scripts/og/fonts/` for build use only, so the site itself stays on system fonts.
- **Budgets**: about 25 to 60 KB per PNG (flat colors compress well; use a palette PNG or quantize). Per city plus per hub: about 400 images ≈ 20 MB. **Event pages get the generated card only for the top N** (say upcoming within 14 days, ≤ 2k images ≈ 80 MB). Others reuse their category hub image, so the site stays far below 1 GB. Cache by a content hash of (title, date, venue, template version) so an hourly build re-renders only changed cards. Satori+resvg runs at roughly tens of ms per image [K], so 2k images take about a minute. Measure it.
- Check with the [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) and the LinkedIn Post Inspector (both manual). The post-build crawl test asserts every page has `og:image` and that the file exists and is ≤ 100 KB.

---

## 4. Core Web Vitals budgets (mid-range phone on 4G)

### 4.1 Targets
- **LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1**, at the 75th percentile of page loads ([Web Vitals](https://web.dev/articles/vitals); [Defining thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds)). Page experience is a ranking input, but only a light one ([Page experience](https://developers.google.com/search/docs/appearance/page-experience)).
- Lab proxy: Lighthouse mobile defaults emulate a **Moto G Power** with simulated throttling of about 150 ms RTT, ~1.6 Mbps down and 4× CPU slowdown ([Lighthouse throttling](https://github.com/GoogleChrome/lighthouse/blob/main/docs/throttling.md)) [K]. INP can't be measured in the lab, so use **TBT ≤ 200 ms** as its proxy ([TBT](https://web.dev/articles/tbt)).
- Field data: once there's traffic, use the CrUX API or PageSpeed Insights, which need enough traffic for an origin or URL to appear ([CrUX](https://developer.chrome.com/docs/crux)). The [`web-vitals`](https://github.com/GoogleChrome/web-vitals) library could log to the console in dev builds. We have no backend for RUM, and we shouldn't add trackers.

### 4.2 Budgets (gzip bytes; GitHub Pages serves gzip only [V])

| Resource | Budget | Today | Notes |
|---|---|---|---|
| Initial JS (entry + preloaded chunks) | **≤ 60 KB** (hard ceiling 100 KB) | 33 KB | Keep Leaflet (~40 KB gz plus markercluster) out of the entry. It already is. |
| Leaflet chunk (map view only) | ≤ 60 KB | lazy | Load on the Map tab or on an IntersectionObserver hit on the map container, never on feed pages. |
| CSS | **≤ 15 KB**, critical inline ≤ 8 KB | 6.5 KB | At this size, inlining the whole CSS in pre-rendered HTML is cheaper than a request. Measure both. |
| Fonts | **0 bytes** | 0 | System stacks. If a brand font is ever added: one WOFF2 subset ≤ 25 KB, `<link rel=preload as=font crossorigin>`, `font-display: swap` plus a `size-adjust`/`ascent-override` fallback face to avoid CLS ([Optimize web fonts](https://web.dev/articles/font-best-practices); [CSS size-adjust](https://web.dev/articles/css-size-adjust)). |
| Images above the fold | ≤ 100 KB total | none | When images arrive: `width`/`height` attributes (CLS), `loading="lazy"` below the fold, `fetchpriority="high"` only on an LCP image ([Optimize LCP](https://web.dev/articles/optimize-lcp); [Browser-level lazy loading](https://web.dev/articles/browser-level-image-lazy-loading)). |
| Pre-rendered HTML per page | **≤ 50 KB** (city hub incl. inline data), ≤ 15 KB (event) | n/a | |
| **Initial data needed to render a city** | **≤ 30 KB** | **170 to 470 KB** | The main fix. See §4.6. |
| Full city data (lazy, for filters) | ≤ 150 KB per shard | 170 to 470 KB single file | Week shards (§6.3). |

### 4.3 What will hit each metric
- **LCP**: currently the hero or first card can't paint until `cities/<slug>.json` downloads (up to 470 KB gz at about 1.6 Mbps ≈ 2.4 s plus parse) **after** the JS boots. Pre-rendered HTML puts the LCP element in the first response, so on lab 4G LCP should land well under 1.5 s.
- **CLS**: the risks are hydration swapping absolute dates for relative ones, the filter bar appearing after data loads, and the map container lacking a fixed height. Reserve space (`aspect-ratio`, `min-height`) and render identical markup on server and client ([Optimize CLS](https://web.dev/articles/optimize-cls)).
- **INP**: filtering 3k events on every keystroke on a 4× slowed CPU. Debounce search (150 ms), precompute lowercase search keys once, use `startTransition`-like yielding (`scheduler.yield()` where supported, else `setTimeout`) for list re-renders, and virtualize or cap the rendered list to 50 cards at a time ([Optimize INP](https://web.dev/articles/optimize-inp); [Optimize long tasks](https://web.dev/articles/optimize-long-tasks)).

### 4.4 Enforcing in CI
- **size-limit** ([ai/size-limit](https://github.com/ai/size-limit)) or a 30-line Node script over `dist/assets` with gzip sizes: fail if the entry JS exceeds 60 KB, CSS exceeds 15 KB, or any `*.js` chunk exceeds 80 KB. Run it in `make check` and on every build.
- **Payload budgets per city JSON**: a script that fails when any `data/cities/<slug>/initial.json` exceeds 30 KB gz or a week shard exceeds 150 KB gz. It warns (doesn't fail) in the hourly refresh, because data growth shouldn't block publishing fresh data, and it shows in `HEALTH.md`. This fits the "never silently fail" rule.
- **Lighthouse CI** ([@lhci/cli](https://github.com/GoogleChrome/lighthouse-ci)) with `preset: lighthouse:recommended`, mobile emulation and default simulated throttling. Assert `largest-contentful-paint ≤ 2500`, `cumulative-layout-shift ≤ 0.1`, `total-blocking-time ≤ 200`, `categories:accessibility ≥ 0.95`, `categories:seo ≥ 0.95`, `resource-summary:script:size ≤ 61440`. Run 3 times per URL and take the median. Test URLs: `/`, `/demoville/`, `/demoville/this-weekend/`, one event page, and `/demoville/map/`. Run it on PRs and nightly against the **demo dataset** (deterministic), not on the hourly refresh.
- Lighthouse [performance budgets](https://web.dev/articles/use-lighthouse-for-performance-budgets) (`budget.json`) are an alternative to the assertions.

### 4.5 Lazy Leaflet (already started)
`LeafletMap.tsx` already dynamic-imports `leaflet`, its CSS and markercluster. Keep that, and add:
- Don't import `LeafletMap` statically from `MapView`. Use a `lazy()`-style wrapper so the component code is in the map chunk too.
- Prefetch the chunk on hover or focus of the Map tab (`<link rel="modulepreload">` injected on intent), not at startup.
- Pre-rendered map page: render the **list alternative** server-side (§5) and mount tiles after the user activates the map, or on IntersectionObserver. Tile requests to OSM must follow the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/) (attribution, no bulk prefetch).

### 4.6 Data strategy for pre-rendered pages
- **Inline only what the first view needs.** The city hub page embeds `<script type="application/json" id="gotc-initial">` holding the ~30 cards it rendered (minimal fields: id, title, start, venue name, neighborhood, category, price flag, url_path). Target ≤ 20 KB gz. Hydration reads it, so there's no hydration fetch.
- Then `requestIdleCallback` (fallback `setTimeout`) fetches the **current week shard** for filters, and later shards only when the user picks "next week" or the calendar. Details (provenance, long descriptions) stay lazy per event, as today.
- Event pages inline nothing beyond what's rendered. The drawer and "similar events" fetch the shard on interaction.
- The pipeline (Python `export.py`) owns the shape: emit `cities/<slug>/initial.json`, `cities/<slug>/w/<YYYY-Www>.json` and `cities/<slug>/details/<shard>.json`, plus a `manifest.json` with hashes. Shard file names can carry the content hash (`w/2026-W42.ab12cd.json`) so even Pages' `max-age=600` never serves a stale shard after a deploy. The manifest itself stays `no-cache`. This is a schema change: bump `SCHEMA_VERSION` and run `make schema`.

---

## 5. Accessibility to WCAG 2.2 AA

Reference: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [What's new in 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/), [ARIA Authoring Practices Guide (APG)](https://www.w3.org/WAI/ARIA/apg/). WCAG 2.2 removed 4.1.1 Parsing and added 2.4.11, 2.5.7, 2.5.8 and 3.3.8 at AA, plus 3.2.6 and 3.3.7 at A.

### 5.1 Checklist mapped to our UI

| SC | Requirement | Where it bites us | Check |
|---|---|---|---|
| 1.4.3 / 1.4.11 Contrast | text 4.5:1 (large 3:1); UI components and focus rings 3:1 | Category tint chips (`hsl(var(--h) var(--tint-s) var(--tint-l))`), the `#ff5a36` accent on white (≈ 3.0:1, so **fails for body text** and passes only for large text and non-text), sparkline lines, muted metadata text | Script: compute contrast for every category hue × light/dark theme in vitest. axe `color-contrast`. |
| 2.4.7 Focus visible + **2.4.11 Focus not obscured (min)** | the focused item is never fully hidden | `:focus-visible` exists (3 px accent). Risks: the sticky header or filter bar and the bottom drawer covering focused cards. | `scroll-padding-top` = header height. Manual Tab-through on mobile size. |
| 2.4.3 Focus order | logical | Drawer opening moves focus in; closing returns focus to the card that opened it | Playwright test: open drawer → `Escape` → focus is on the trigger. |
| **2.5.8 Target size (min)** | ≥ 24×24 CSS px or enough spacing | Filter chips, calendar day cells on a 360 px phone, sparkline hit areas, Leaflet `+/−` (Leaflet defaults are 30 px, which is fine), "save" heart icon | Playwright: assert `getBoundingClientRect()` ≥ 24 for `button, a, [role=button]` in the mobile project. |
| **2.5.7 Dragging movements** | any drag has a single-pointer alternative | Map panning: Leaflet has zoom buttons and keyboard pan, and **the list view is the alternative**. Any future drag-to-reorder in Plan needs up/down buttons. | Manual. |
| 2.4.1 Bypass blocks | skip link | `<a class="skip" href="#main">` exists. **With hash routing, `href="#main"` changes the route.** After the move to paths it works natively. Until then, handle it with JS focus. | e2e: activate the skip link, focus lands on `main`. |
| 1.3.1 / 2.4.6 / 2.4.2 | landmarks (`header`, `nav`, `main`, `footer`), one `h1` per page, ordered headings, unique `<title>` per route | Pre-rendering gives a real `<title>` per page. In the SPA, update `document.title` on route change and move focus to the `h1` (or announce it) after navigation ([Gatsby a11y routing study](https://www.gatsbyjs.com/blog/2019-07-11-user-testing-accessible-client-routing/)). | axe `page-has-heading-one`, `landmark-one-main`, `region`. |
| Maps (1.1.1, 2.1.1) | non-visual equivalent | The Map view must offer a visible "List" toggle with the same filtered events sorted by distance. Markers need accessible names (`title`/`alt` = event name). Clusters need "12 events" labels. The map container gets `role="region"` and `aria-label="Map of events"`, and keyboard focus must not get trapped (2.1.2). | Manual with VoiceOver plus keyboard. axe on `/map`. |
| Calendar grid (1.3.1, 4.1.2) | semantic structure | Either a real `<table>` with `<th scope=col>` weekdays and each day a `<button aria-label="Sat Oct 18, 6 events">`, or the [APG grid pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/) with roving tabindex and arrow keys. The table plus buttons is simpler and sufficient. Selected day: `aria-pressed` or `aria-current="date"`. | axe. Manual arrow/Tab test. |
| Dialogs and drawers (2.1.2, 2.4.3, 4.1.2) | modal semantics | `EventDrawer`: use native `<dialog>` + `showModal()` (built-in focus trap, `Esc`, inert background) or follow the [APG dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/): `role="dialog"`, `aria-modal="true"`, `aria-labelledby` = title, return focus on close. | e2e with drawer open + axe. |
| 4.1.3 Status messages | announce changes without moving focus | "128 events match" after filtering, "Saved", data-stale banners, loading/error states | `role="status"` (polite) live region. |
| 1.4.10 Reflow / 1.4.12 Text spacing / 1.4.4 Resize | 320 px width, no horizontal scroll; survive the text-spacing bookmarklet; 200% zoom | Card date column, filter bar overflow | Playwright at 320×640 asserting `scrollWidth ≤ clientWidth`. |
| 2.3.3 (AAA, but do it) / reduced motion | respect `prefers-reduced-motion` | Already globally disables animations in `app.css` (line 109). Also turn off Leaflet `zoomAnimation`/`fadeAnimation` and smooth scroll when it's set. | Unit-check the CSS. Manual. |
| 3.1.1 Language | `<html lang="en">` | Present in `index.html`. The prerender template must keep it. | axe `html-has-lang`. |
| 1.4.1 Use of color | don't rely on color alone | Category colors, "selling fast", stale-data states, sparkline trends: pair each with an icon or text | Manual. |
| 3.2.6 Consistent help (A) | help or contact in the same place | Put the About/Health link in the same footer spot on every page | Manual. |
| 2.4.4 Link purpose | "Tickets" links need context | `aria-label="Tickets for <event> on SeatGeek"` or visually hidden text | axe can't fully check this. Manual. |

### 5.2 Automated checks (we have axe + Playwright)
Upgrade `web/e2e/a11y.spec.ts`:
- Tags: `["wcag2a","wcag2aa","wcag21a","wcag21aa","wcag22aa"]`. Without `wcag22aa` axe won't run `target-size` ([axe rule tags](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md#axe-core-tags)).
- Add views: `map`, `saved`, `about`, home `/`, one event detail page, and the feed **with the drawer open** and **with filters applied**.
- Run in both the `desktop` and `mobile` (Pixel 7) projects. Some violations (target size, reflow) only show on mobile.
- Also fail on `moderate` impact for a set allowlist of rules once clean, ratcheting up.
- Extra Playwright assertions that axe can't make: focus return from the drawer, skip link target, 320 px reflow, ≥ 24 px targets, `document.title` changes per route, and live-region text after filtering.
- Automated tools find only part of WCAG issues (Deque reports about 57% by volume: [Deque study](https://www.deque.com/automated-accessibility-coverage-report/)) [K]. So also do:

### 5.3 Manual checks (each release touching UI, ~20 min)
1. Keyboard only: Tab through home → city → filters → card → drawer → tickets link → close → calendar → map list toggle.
2. VoiceOver (iOS Safari) and NVDA or VoiceOver (desktop): headings list, landmarks rotor, drawer announcement, filter count announcement.
3. 200% zoom and 320 px width. Windows High Contrast or `forced-colors` mode, where focus rings and chip borders must stay visible.
4. `prefers-reduced-motion` and dark mode contrast spot checks.

---

## 6. Slow and flaky connections

### 6.1 What Pages gives and doesn't give [V]
- gzip only (no brotli even when the client offers `br`). We can't upload `.br` files and have them served with `content-encoding: br`. Brotli would save another ~15 to 20% on JSON [K] but needs a CDN in front (Cloudflare) or a different host.
- `max-age=600` on everything, weak ETags. Content-hashed asset and shard names (§4.6) make the 10-minute cache harmless. The non-hashed `manifest.json` and HTML are fetched with `no-cache` and revalidate to a 304.

### 6.2 Service worker
A handwritten SW of about 2 KB, or [Workbox](https://developer.chrome.com/docs/workbox) (`workbox-build` `generateSW` or `injectManifest`; the runtime adds a few KB). Use **scope `BASE`**. The SW file must be served from `BASE`, which works on a project site ([Service worker lifecycle](https://web.dev/articles/service-worker-lifecycle); [Offline cookbook](https://web.dev/articles/offline-cookbook)).

| Request | Strategy | Why |
|---|---|---|
| `/assets/*` (hashed) | cache-first, precached at install | immutable |
| Pre-rendered HTML | network-first with a 3 s timeout, then cache | fresh if possible, still works in a subway |
| `manifest.json`, week shards, `initial.json` | **stale-while-revalidate** | instant render, refresh in the background |
| `details/*` | cache-first after first fetch, LRU at 50 entries | rarely changes |
| OSM tiles | network-only (don't cache third-party tiles in bulk; OSM policy) | |
| Offline, nothing cached | `offline.html`: "You're offline. Saved events:" rendered from `localStorage` `saved` | |

**Staleness honesty (non-negotiable rule 2):** whenever the UI renders from the SW cache, show "Data as of 3:17 PM (offline)" using `generated_at` from the payload. Raise a stronger warning when it's older than the SLA. Never present cached data as live. Put a cache version into the SW and delete old caches on `activate`. Add an e2e test using Playwright's `context.setOffline(true)`.

Other niceties: `navigator.connection.saveData` (Chromium-only, [Save-Data](https://web.dev/articles/optimizing-content-efficiency-save-data)) → skip prefetching later shards and the map chunk. Show a skeleton, not a spinner, and show a visible retry with a reason on fetch errors.

### 6.3 Splitting data per week
- `cities/<slug>/initial.json`: city meta, neighborhoods, starter pack, the next 7 days' top ~60 events in minimal fields. ≤ 30 KB gz.
- `cities/<slug>/w/<ISO-week>.<hash>.json`: full card fields for that week. ≤ 150 KB gz. For recurring events, one series record per shard with its occurrence dates.
- `cities/<slug>/deadlines.<hash>.json`: deadlines are small and needed across all time windows.
- `cities/<slug>/search.<hash>.json` (optional): id, title, venue and category tokens for all upcoming events, so search works across weeks without loading every shard.
- The existing `*.details.json` split per week the same way.
- Keep the monolithic `cities/<slug>.json` for one release for backward compatibility and external users, then drop it.

---

## 7. Implementation plan for this repo

### 7.1 Phases (each is a small, independently shippable set of commits)

**Phase 0: decisions (1 ADR).** `docs/adr/0007-path-routing-and-prerender.md` covers the path scheme, absolute base, custom domain (yes or no and when), the event page lifecycle, and the "detail pages only" JSON-LD policy.

**Phase 1: real paths, still client-rendered.**
- `web/vite.config.ts`: `base: process.env.GOTC_BASE ?? "/GetOffTheCouch/"`. Define `__SITE_ORIGIN__`.
- `web/src/lib/site.ts` (new): `BASE`, `ORIGIN`, `url()`, `canonical()`, `eventPath(e)`, `slugify()`.
- `web/src/lib/router.ts`: parse and build **paths**, keep the query for filters, use `popstate` + `history.pushState`, add legacy hash → path `replaceState`, and intercept `<a>` clicks for same-origin links.
- `web/tests/router.test.ts`: path cases, legacy hash cases, base-path cases.
- `dist/404.html` = app shell (copied in a tiny Vite plugin or post-build step), so deep links work immediately even before pre-rendering lands.

**Phase 2: pre-render hubs and events.**
- `gotc/schema.py` + `gotc/pipeline/export.py`: add `slug`, `url_path`, `status` (`scheduled|cancelled|postponed|rescheduled|moved_online`), optional `end`, `organizer`/`performers` where reported, and `expires_at` (end + 7 d). Bump `SCHEMA_VERSION`, run `make schema`, update contract tests.
- `web/src/entry-server.tsx` (new): `render(route, data) → { html, head }`.
- `web/src/main.tsx`: `hydrate` when pre-rendered, read `#gotc-initial`.
- `web/src/lib/seo/head.ts` (new): title, description, canonical, robots, OG/X tags.
- `web/src/lib/seo/jsonld.ts` (new, typed with `schema-dts`): `eventJsonLd()`, `breadcrumbJsonLd()`, `websiteJsonLd()`. Kind gating per §2.2. Unit tests in `web/tests/jsonld.test.ts` with golden fixtures.
- `web/scripts/prerender.mjs` (new): routes from data, a worker pool, content-hash skip, lifecycle stubs (§1.7), demo exclusion, file-count and size guard.
- `web/scripts/sitemaps.mjs`, `web/scripts/feeds.mjs` (Atom + ICS per city and category, reusing `src/lib/ics.ts`).
- `web/package.json` scripts: `"build": "vite build && vite build --ssr src/entry-server.tsx --outDir dist-ssr && node scripts/prerender.mjs"`, `"check:dist": "node scripts/check-dist.mjs"`.

**Phase 3: data split + SW.**
- `gotc/pipeline/export.py`: `initial.json`, week shards, `manifest.json` with hashed names (schema bump).
- `web/src/lib/data.ts`: manifest-driven loading, idle prefetch of the current week, `saveData` awareness.
- `web/public/sw.js` (or `injectManifest` with Workbox) plus registration in `main.tsx` (production only). `web/public/offline.html`.
- UI "data as of …" badge wired to `generated_at` and the cache source.

**Phase 4: OG images.**
- `web/scripts/og.mjs` (satori + resvg-js, bundled OFL TTF), cache keyed by content hash in `data/og-cache/`. Persist via the Actions cache alongside `data/raw`.

**Phase 5: quality gates.**
- `web/scripts/check-dist.mjs`: per page, verify a parseable `<title>`, description, absolute canonical, `og:image` file exists and is ≤ 100 KB, JSON-LD parses and passes the rules, `noindex` pages are absent from sitemaps, sitemap URL counts are ≤ 45k per file, there are no `href="#/` links, total size ≤ 800 MB, and the file count ≤ 60k.
- `web/scripts/check-budgets.mjs` (or `.size-limit.json`): gzip sizes for entry JS ≤ 60 KB, CSS ≤ 15 KB, chunks ≤ 80 KB, `initial.json` ≤ 30 KB, shards ≤ 150 KB.
- `web/lighthouserc.json` + `.github/workflows/web-quality.yml` (on PR + nightly): `gotc demo --anchor …` → build with `GOTC_BASE=/` → `lhci autorun` on 5 URLs, plus `npm run e2e` (axe with WCAG 2.2 tags).
- `web/e2e/a11y.spec.ts`: §5.2 upgrades. `web/e2e/seo.spec.ts` (new): JS disabled (`javaScriptEnabled: false`) → the city page still shows events and links. Also legacy hash redirects, canonical present, offline mode shows the stale banner.

### 7.2 Changes to `.github/workflows/refresh.yml`
```yaml
      - name: Build dashboard with fresh data
        working-directory: web
        env: { GOTC_BASE: "/GetOffTheCouch/", GOTC_SITE_ORIGIN: "https://lachlanspangler.github.io" }
        run: ../.venv/bin/python -m gotc demo && npm ci && npm run build   # build now includes prerender, sitemaps, feeds, OG
      - name: Check dist (SEO + budgets; budgets warn-only here)
        working-directory: web
        run: node scripts/check-dist.mjs && (node scripts/check-budgets.mjs --warn >> "$GITHUB_STEP_SUMMARY")
```
Persist `data/og-cache/` and `data/prerender-cache.json` with the Actions cache, like `data/raw`. Time the prerender step and the deploy step, and record both in the diary. The deploy must stay well under the 10-minute Pages limit.

### 7.3 One-time manual steps (only the user can do these; list under "Keys needed" in STATUS.md)
- Create a Search Console URL-prefix property and add the verification file to `web/public/`. Submit `sitemap.xml`.
- Decide on a custom domain **before** Phase 2 ships widely, to avoid a site move later.
- Optional: a Bing Webmaster Tools import from Search Console. Optional: IndexNow (Bing, Yandex and others; the key file can live under our path; Google doesn't support it) ([indexnow.org](https://www.indexnow.org/documentation)). Note that Google's Indexing API is only for JobPosting and BroadcastEvent, **not** regular events ([Indexing API](https://developers.google.com/search/apis/indexing-api/v3/quickstart)).

---

## 8. Idea candidates

Format: `title | area | value 1-5 | effort 1-5 | why`

1. Path routing with legacy hash redirect + 404.html shell | seo/routing | 5 | 2 | Prerequisite for everything else. Every shared `#/…` link keeps working. Unblocks real URLs, titles and share previews.
2. Pre-render city, slice and category hubs (preact-render-to-string + hydrate) | seo/perf | 5 | 3 | Turns one invisible URL into ~400 indexable landing pages that answer "things to do in <city> this weekend". LCP drops from data-bound to HTML-bound.
3. Pre-rendered event and series detail pages with expiry lifecycle (page → meta-refresh stub → 404) | seo | 5 | 3 | Long-tail search plus unique share URLs. The lifecycle keeps the site under Pages' 1 GB and avoids stale indexed events.
4. Kind-gated Event JSON-LD (no markup for openings, deadlines or seasons; reported prices only) + offline rule tests | seo/structured-data | 4 | 2 | Eligibility for event features without breaking Google's content policies or our no-fabrication rule. `schema-dts` + vitest makes it CI-checkable.
5. Sitemap index + per-city sitemaps with honest lastmod (content-hash skip) + Search Console URL-prefix submit | seo | 4 | 2 | A project site can't own robots.txt, so sitemaps through Search Console are our only crawl hint. An accurate lastmod gets fresh events crawled.
6. Week-sharded city data + ≤ 30 KB `initial.json` inlined in hub HTML | perf | 5 | 3 | The city JSON is 170 to 470 KB gz today and gates first paint. Sharding cuts the first-view payload by more than 10× on 4G phones.
7. Service worker: SWR for data, network-first HTML, offline page, "data as of" badge | perf/offline | 4 | 3 | Works on subways and spotty LTE. The visible staleness badge keeps us honest per non-negotiable rule 2.
8. Per-city and category ICS + Atom feeds with a deadlines.ics subscribe link | distribution | 4 | 2 | "Subscribe to Chicago beer-league deadlines" puts our differentiator inside users' calendars. Feeds double as fast sitemaps.
9. Build-time OG cards (satori + resvg) for cities, hubs and next-14-day events, hash-cached | social | 3 | 3 | Today every share shows the same generic preview. Rich cards raise click-through from group chats, which is how newcomers find things.
10. CI quality gates: check-dist (SEO invariants) + gzip budgets + Lighthouse CI on demo data + axe WCAG 2.2 tags incl. map/drawer/mobile | quality/a11y | 4 | 2 | Locks in LCP ≤ 2.5 s, CLS ≤ 0.1, TBT ≤ 200 ms, 33 KB JS and WCAG 2.2 AA (target-size isn't tested today) so regressions fail before they ship.

Smaller follow-ups for the ledger: a contrast test over all category hues (the `#ff5a36` accent is ≈ 3:1 on white and fails for small text), `<dialog>`-based EventDrawer with focus return, a calendar as `<table>` + day buttons, a map "List" toggle, `document.title` + focus-to-h1 on SPA navigation, and custom domain + Cloudflare for brotli and real 301/410 (ADR first).
