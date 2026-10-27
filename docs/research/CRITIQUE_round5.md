# Design review, round 5 (2026-10-27)

A fresh reviewer walked the site as a brand-new resident of 5 cities (Chicago, Atlanta, Phoenix, Seattle, Kansas
City): desktop in light mode and phone in dark mode, plus spot checks of the other two combinations. The report arrived late in the finishing session. Its
findings are below, with what happened to each. The reviewer's text is summarized, not quoted.

## Must-fix
| # | Finding | Status |
|---|---|---|
| 1 | Phoenix deadlines listed "OPENS" rows that were really the show starting. "Add these 0 to your calendar" | **Fixed** (`7eb52d8`). Root cause: Mesa Arts Center copies `startDate` into `offers.validFrom`. The adapter now treats an on-sale time at the show itself as a placeholder. The button hides at 0. |
| 2 | Day-header counts come from the loaded page, not the whole filtered set. "Showing 50 of 254" reads as if the rest are missing | Open |
| 3 | "Critical Mass Big Band" is filed as group rides. A venue's type and the source's category should beat a title keyword | Open. Needs a classifier precedence change checked with the ranking eval. |
| 4 | Miscategorized: a WNBA game and comedy open mics under concerts; "Outdoor yoga" for an indoor class; tree planting as a meeting. Series need collapsing | Open (taxonomy keyword gaps) |
| 5 | Junk venue strings ("Sign in to download the location", "non-library location", permit suffixes); away games in the Kansas City feed | Open |
| 6 | Duplicates: same branch and same time; license rows for one address; the plan lists a weekly habit and its individual dates | Open |
| 7 | Title casing: "Women'S", "MEN'S" | **Fixed** (`8d3439a`) |
| 8 | City switcher: focus doesn't move into it, Escape doesn't close it, focus doesn't return | **Fixed** (`8d3439a`) |
| 9 | The /cities/ table makes the whole page scroll sideways on a phone | **Fixed** (`8d3439a`) |
| 10 | Online events are pinned on the map | **Fixed** (`8d3439a`) |
| 11 | The plan includes audience-specific programs; license records get event-style reasons | Open |

## Should-fix (all open)
- The Today list skews toward senior programs. The pick art is too tall on mobile.
- Location text repeats itself: "IL" twice, "Lee's Summit · Lees Summit".
- The license disclaimer is repeated on every row.
- Counts don't say which time window they cover. Grammar: "1 of 14 sources are behind".
- Category names disagree: "Books & talks" vs "Classes & talks".
- The calendar shows only one week row.
- The Phoenix map starts too zoomed out. Dark-mode tiles show seams.
- The provenance sentence reads robotic. Stray punctuation: "stars….", extra commas in addresses.
- "Why this?" reasons are generic, and the "new" window is wrong.
- The Health page uses jargon. Stale-source labels show internal ids.
- Kansas City needs a Kansas/Missouri toggle.
- The plan asks for the move date twice. "Step 1 of 4" should be "of 3".
