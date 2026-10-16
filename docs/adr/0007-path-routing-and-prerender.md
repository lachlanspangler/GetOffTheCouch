# ADR-0007: Real paths, pre-rendered pages, and an absolute base

**Status:** accepted · 2026-10-16

## Decision
- **Paths, not hashes.**
  - `/chicago/` is the city feed and `/chicago/concerts/` (`/this-weekend/`, `/free/`, …) are landing hubs: preset filters, listed in `web/src/lib/site.ts` `HUBS`.
  - `/chicago/deadlines/` and the other views; `/chicago/events/<title-slug>-<hex>/` for events. The hex id is authoritative and the slug is cosmetic.
  - Site-wide pages: `/about/`, `/privacy/`, `/methodology/`, `/health/`.
  - Extra filters stay in the query string, and the canonical points to the clean path.
  - Old `#/…` links are translated on boot with `history.replaceState`, so every link shared before this change keeps working.
- **Absolute base from env.** `GOTC_BASE` (`/` in dev, `/GetOffTheCouch/` on GitHub Pages) and `GOTC_SITE_ORIGIN`. Moving to a custom domain is one env change plus a rebuild. Every href goes through `site.ts` (`url`, `absolute`, `eventPath`).
- **404.html is the app shell.** Pages serves it with a real 404 status, so it is only a fallback: deep links work before or without pre-rendering, and it is never indexed.
- **Pre-rendering** (phase 2): an SSR bundle plus `scripts/prerender.mjs` writes `<path>/index.html` for the home page, cities, hubs, views and events:
  - The head carries title, description, canonical, OG tags and JSON-LD.
  - Event pages go through a lifecycle: full page with an "ended" banner for 0–7 days after the event, then a meta-refresh stub to the city page for 7–60 days, then deletion.
- **Event JSON-LD** only for kinds that are real events (`one_off`, `recurring` occurrences). Never for openings (license signals), deadlines or seasons. Prices are included only when reported.

## Why
Hash URLs make the whole site one URL that Google ignores and link previews can't read. A newcomer's first touch is usually a search ("things to do in Chicago this weekend") or a shared link. Both need a real page with real content in the HTML. GitHub Pages has no server, so static pre-rendering is the only way to get there; research is in `docs/research/SEO_ACCESS.md`.

## Consequences
- The refresh workflow sets `GOTC_BASE=/GetOffTheCouch/`. Without it, assets would load from `/` and the live site would break. This ships in the same commit as the router.
- Pre-rendering adds build time and files to the Pages artifact. A CI guard fails the build above 800 MB or 60k files.
- If a custom domain arrives, switch early. Pages 301s `github.io` to it, which Google treats as a site move.
