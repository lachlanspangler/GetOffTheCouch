# Design critique, round 1 (fresh design-critic agent, 2026-10-16)

Inputs: the 60 before and 60 after screenshots plus the live site, including menus, sheets, hubs and prose pages.

**Verdict:** the visual system now reaches Time Out or Resy level. The data underneath has not caught up: junk listings, wrong ordering, past events and admin posts now look more credible, which is worse.

| Screen | Grade (desktop / mobile) |
|---|---|
| Home | B / B+ |
| Minneapolis feed | C / C- |
| NYC feed | D / D |
| Minneapolis deadlines | B- |
| NYC deadlines | C |
| Calendar | C+ |
| Minneapolis map | C / D |
| NYC map | D |
| Plan | B- |
| Health | B+ / C |
| Minneapolis event | B |
| NYC event | B- |
| About / Methodology / Privacy | A- |

## Top 10 fixes
1. Remove liquor-license records, service permits and campus-only club meetings from the feed, map and calendar.
2. Collapse repeating series and organizers into one row ("Volo · 41 leagues").
3. Sort day groups by start time, hide events that have already started, and purge past dates and stale-month titles.
4. Keep family and kids items and board or admin volunteer roles out of picks and list leaders unless the user opts in.
5. Normalize titles (ALL CAPS, "!"), venues (a name, not a raw address) and cross streets. Down-rank or label far suburbs.
6. Shrink the art in picks so listings show above the fold. Fix the mobile picks margin and the sticky day-header offset.
7. Remove the fake signals:
   - "Selling fast" on free items
   - "Add all 114"
   - "Read from the listing text" repeated on every row
   - "5–150 people" estimates
8. Map: open at city zoom, use light clusters in dark mode, and stack the list on mobile.
9. Calendar: start at the current week, put useful content in cells, list ongoing events last, and fix the dark-mode "today" cell.
10. Make the numbers agree: event and source counts, plurals, zero states, and "this week" versus the 30-day default.

The full per-screen list is in the session transcript. Fixes are tracked in the diary as "critique round 1".
