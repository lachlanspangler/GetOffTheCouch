# Competitor and inspiration survey

Researched on 2026-10-15. This survey draws mostly on prior product knowledge [K]. Products change often, so verify a UI before copying it closely. Ticket-marketplace urgency UX (SeatGeek, TickPick, Gametime and others) is covered in `ticketing_and_events_apis.md` §6.

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
