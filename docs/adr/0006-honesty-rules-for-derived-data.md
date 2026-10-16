# ADR-0006: Reported vs. derived vs. estimated, and what the UI may show for each

**Status:** accepted · 2026-10-16

## Decision
| Method | Example | UI rule |
|---|---|---|
| reported | Volo "Closes 11/6"; library "17 of 20 spots taken" | Show plainly |
| extracted | "register by Nov 3" in a description | Show, with the sentence it came from |
| curated | club-page quote, re-verified | Show, with the source and the re-check time |
| derived | league with only an "opens" date → "register before it starts" | **No countdown.** Show "Registration required" or the spots left. Kept apart from published deadlines |
| estimated | crowd size from capacity × fill | Always a band plus method plus confidence. Cards show it only at confidence ≥ 0.4 |

- **"% tickets left" needs a signal.** It's shown only when a source reports counts (exact) or a resale-listing signal exists (labeled "listings are not seats").
- **Free means "the source says free"**, except volunteering, which is labeled as derived.
- **Openings are license signals, never opening dates.** "New" for datasets without an issue date means *first seen by us after the baseline*, and is labeled so.

## Why
Moving to a new city is about trust. One fabricated deadline costs a user a league season. A visible "we don't know" costs nothing.
