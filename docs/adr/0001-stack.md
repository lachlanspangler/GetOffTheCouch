# ADR-0001: Python pipeline + static TypeScript dashboard

**Status:** accepted · 2026-10-15

## Context
The product is a pipeline first: dozens of sources × cities refreshed on per-type SLAs, with self-healing health tracking. The dashboard is read-only for the public; personalization (interests, saved events, reminders) is per-user and private.

## Decision
- **Pipeline in Python 3.12.** We use pydantic v2 for schema validation at every boundary, httpx for HTTP, and icalendar/recurring-ical-events for ICS. Python has the best libraries for parsing messy web data. It's also what GameCred used, so patterns carry over.
- **Dashboard as a static site.** It's built with Vite + Preact + TypeScript and reads JSON exported by the pipeline (`web/public/data`). We deploy it to GitHub Pages, and an hourly GitHub Actions cron refreshes it.
- **Personalization stays in the browser.** Interests, saved events, the first-30-days plan and reminders live in localStorage and are exported as .ics with alarms. There are no accounts and no PII on a server.
- **Types end to end.** `CityFeed.model_json_schema()` → `schema/cityfeed.schema.json` → generated TypeScript types. A contract test fails if the generated types are stale.

## Consequences
- **Hosting:** zero hosting cost, zero ops, and nothing to keep alive at 3am.
- **Freshness** is bounded by the cron interval (1h). Ticket prices meet a 4h SLA comfortably.
- **No server-side push.** "Remind me" uses calendar alarms (.ics VALARM) and in-tab notifications. True push or email would need a backend (see idea ledger).
- **Payload size:** a city JSON must stay small enough to load on mobile. Export windows are limited to 180 days, and descriptions are capped at 600 chars.
