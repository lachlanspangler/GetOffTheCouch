hi i'm starting a new project called **GetOffTheCouch**: "ur city made easy." it's a living, auto-updating dashboard for anyone who just moved to (or is about to move to) a new US city. you pick a city (Minneapolis, Miami, Los Angeles, anywhere in the USA) and it shows you everything worth getting off the couch for, plus every deadline you'd otherwise miss.

my folder is `~/Desktop/GetOffTheCouch`. start there. the repo is https://github.com/lachlanspangler/GetOffTheCouch and i can push it. (if the folder isn't a git repo yet, `git init` it and set that remote. don't push, i'll do that.)

**the most important thing: i want to set you off on this and walk away.** even if it takes hours or days, build it out as far as you can. tokens are not a problem. don't stop to ask me things you can decide yourself. pick the sensible default, write down why in the diary, and keep going. only stop if you're truly blocked on something only i can give you (like a paid API key), and even then, stub it, document it, and move on to the next thing.

## the pitch
- moving to a new city is lonely and the info is scattered across 40 websites. nobody has it all in one place, sorted by city, with deadlines.
- **beer leagues** (kickball, softball, volleyball, pickleball, bowling, broomball, curling): when registration opens, when it closes, cost, skill level, free agent vs team signup.
- **parties and openings**: bar/restaurant openings, block parties, rooftop season openers, pub crawls, holiday events.
- **concerts with live prices**: face value vs resale, lowest price on StubHub / SeatGeek / Ticketmaster / Vivid, price trend, "~x% of tickets left," and a link to buy.
- **volunteer opportunities**: one-off and recurring, with signup deadlines.
- **niche stuff**: furry cons, ren faires, comic cons, anime cons, car shows, maker faires, trivia nights, run clubs. the weird stuff is what makes a city feel like home.
- **recommendations**: "you're new, you like X, here's your first month."
- **every event card has**: title, date/time, address + map, venue, category, price (or price range), link to buy/register, *register-by date*, *estimated attendance* (with a confidence range), ticket availability, source, and when we last checked it.
- **sorted by city.** USA only for now.
- **it must auto-update.** the data can't go stale. this is a pipeline product first and a dashboard second.

## what i want you to set up first (the workflow)
mirror and improve on what worked in my other project, `~/Desktop/GameCred` (look at its `CLAUDE.md`, `docs/WORKFLOW.md`, `docs/DIARY.md`, `docs/IDEAS.md`, `docs/ideas_ledger.json`, `docs/HEALTH.md`, `Makefile`, `.github/`). reuse any code or patterns on this computer that help, but adapt them. don't just copy.

1. **CLAUDE.md**: project rules, architecture map, how to run/test everything, conventions. written so a future you with zero context can pick up where you left off.
2. **docs/WORKFLOW.md**: the loop you run forever: *pick the highest-value idea → plan → build → test → verify in the real app → update diary/status → generate new ideas → repeat.*
3. **docs/IDEAS.md + docs/ideas_ledger.json**: every idea gets an id, a value/effort score, a status, and a reason. generate ideas constantly and creatively (features, new sources, new cities, data quality tricks, UX polish). record the rejected ones too, with why.
4. **docs/DIARY.md**: timestamped log of what you did, what broke, what you decided and why. append-only.
5. **docs/STATUS.md**: current state at a glance: what works, what's stubbed, what's next.
6. **docs/HEALTH.md + a self-healing loop**: every source has a health check. when a scraper breaks (schema drift, 403, empty results, layout changed), the pipeline detects it, quarantines that source, keeps serving last-known-good data marked stale, logs it, and you fix it on the next loop. failures are never silent.
7. **docs/SOURCES.md**: every data source with its API/URL, auth needs, rate limits, ToS/robots stance, fields it provides, refresh cadence, and reliability score.

## the pipeline (this is the heart of it, make it a masterclass)
- **ingest layer**: one pluggable adapter per source behind a common interface. examples to research and pick from: Ticketmaster Discovery API, SeatGeek API, Eventbrite, StubHub/Vivid (affiliate feeds or other legit access), Bandsintown/Songkick, Meetup, VolunteerMatch / Idealist / JustServe / city volunteer portals, Volo / ZogSports / local league sites, city open-data portals (Socrata), parks & rec calendars, furrycons.com-style directories, ren faire directories, local alt-weekly calendars. favor official APIs. respect robots.txt and ToS. rate limit, cache, back off politely.
- **normalize**: everything maps into one strict, versioned event schema (validated, typed). timezones correct. addresses geocoded. categories from a real taxonomy, not free text.
- **entity resolution / dedup**: the same concert shows up on 5 sites. merge it into one canonical event that keeps per-source prices and links. venues and organizers are entities too.
- **enrichment**: estimated attendance (model it from venue capacity, past editions, RSVP counts, ticket availability, social signals. show the method and a confidence band, never fake precision), price history snapshots, "selling fast" signals, deadline extraction ("register by").
- **freshness SLAs per data type**: ticket prices refresh every few hours, league signups daily, cons/faires weekly. every field carries `source`, `fetched_at`, and `confidence`.
- **scheduling**: cron-driven refreshes (GitHub Actions or a local scheduler), idempotent and resumable jobs, incremental fetches, so a run that dies halfway can just run again.
- **storage**: pick something boring and solid (SQLite/DuckDB locally, Postgres-ready), with migrations, raw payloads kept for replay and debugging, and snapshot tables for price/availability history.
- **observability**: per-source run stats, row counts, error rates, staleness, and a pipeline health page in the dashboard itself.
- **no fabricated data, ever.** if something is estimated, label it. if a source is down, say so. demo/seed data must be clearly flagged and separable from real data.
- **secrets**: API keys in env vars / `.env` (gitignored) with a `.env.example`. never commit keys.

## the dashboard (the product people see)
- city picker (start with ~10 seed cities: Minneapolis, Miami, Los Angeles, Chicago, NYC, Austin, Denver, Seattle, Nashville, Boston), architected so adding a city is config, not code.
- views: **calendar**, **list/feed**, **map**, and a **"Deadlines" view** (register-by dates, leagues closing soon, early-bird pricing ending, volunteer signups) sorted by urgency.
- filters: category, date range, price, distance/neighborhood, attendance size, free only, "good for meeting people."
- concert cards with live price comparison across sellers + price-over-time sparkline + "~x% left."
- a **"New in town" onboarding**: pick your interests and get a personalized first-30-days plan. a recommendations engine that explains *why* it picked each thing.
- calendar export (.ics), shareable links, saved events, and "remind me before registration closes."
- it should look amazing: modern, fast, accessible, mobile-first, dark mode. a polished product, not a dev tool.

## engineering bar: "mind numbingly well engineered"
- clean architecture with clear boundaries (adapters / pipeline / storage / api / web), typed end to end, schema-validated at every boundary.
- tests at every layer: unit tests, adapter tests against recorded fixtures (so tests never hit the live internet), contract tests for the schema, pipeline integration tests, and UI smoke tests. CI runs all of it.
- linting, formatting, type-checking, pre-commit hooks, one-command setup (`make setup`, `make dev`, `make test`, `make pipeline`).
- small, frequent, well-described commits, one logical change each.
- ADRs (`docs/adr/`) for big decisions.
- **verify, don't assume.** after each feature, actually run the pipeline and open the dashboard to confirm it works. log the result in the diary. if a test fails, fix the root cause, not the symptom.

## how to work
- start by researching: what sources exist, what their APIs and terms allow, what similar products do well or badly. write that up, then design, then build.
- get a thin vertical slice working end to end first (1 city, 2–3 real sources → normalized DB → dashboard), then widen: more sources, more cities, more features, more polish.
- be creative. i want ideas i didn't think of. every loop, add at least a few new ideas to the ledger and build the best ones.
- keep the diary and status current so i can open the folder at any point and know exactly where things stand.
- when you hit a natural milestone, write a short summary at the top of STATUS.md: what's done, what's real vs stubbed, what API keys i need to get, and what you'd build next.

go. build as much of this as you possibly can.
