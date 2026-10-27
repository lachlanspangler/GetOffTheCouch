# After you push: checklist

Pushing `main` brings three changes:
- **Sharded hourly refresh:** `refresh.yml` runs `prepare` → `shard` ×N → `publish`.
- **Pre-rendered site at real paths:** about 20k pages under `/GetOffTheCouch/`.
- **Two new workflows:** `keepalive.yml`, and `refresh-monolithic.yml` as a manual fallback.

Nothing in the repo settings needs to change.

## 0. Before pushing (2 minutes)
- [ ] **Settings → Pages:** Source must be **GitHub Actions**.
- [ ] **Settings → Actions → General → Workflow permissions:** **Read and write**.
- [ ] **Optional, Settings → Secrets and variables → Actions:** add any of these you have:
  - `TICKETMASTER_API_KEY`
  - `SEATGEEK_CLIENT_ID`
  - `RUNSIGNUP_API_REG` and `RUNSIGNUP_API_REG_SECRET`
  - `SOCRATA_APP_TOKEN`

  Each source without its key shows as "Waiting on an API key", not as broken.
- [ ] **Private repo only:** the hourly sharded refresh (about 13 shards plus a publish job) uses many Actions minutes. Public repos don't pay for minutes.

## 1. Push, then watch CI (5–10 min)
- [ ] **Actions → CI:** both jobs (`pipeline` and `web`) go green. `web` builds the demo dataset, runs the tests, builds the site, checks the JS/CSS budgets and runs the Playwright + axe tests.
- [ ] **If CI fails:** the failure is in the code, not your settings. The site keeps serving the last deploy.

## 2. Start the first refresh by hand (don't wait for :17)
- [ ] **Actions → Refresh data → Run workflow** on `main`. Keep shard size at the default of 4.
- [ ] **`prepare`** (about 1 min) prints a matrix of about 13 shards.
- [ ] **`shard (…)`** jobs: each fetches its cities and uploads a `shard-N` artifact.
  - The first run is the slowest: most of the 50 cities have never run in CI. Each shard stops itself at 20 minutes.
  - A red shard doesn't block the deploy. Its units are simply due again next hour.
- [ ] **`publish`** (expect 15–30 minutes on the first run): merges deltas, then builds, exports and runs the contract tests.
  - Next, it pre-renders about 20k pages (about 2 min) and deploys Pages.
  - Last, it persists the state to the `pipeline-state` branch.
- [ ] **Job summary:** HEALTH.md, the `check-dist` result (expect 0 problems) and the budgets.

## 3. Check the live site
- [ ] https://lachlanspangler.github.io/GetOffTheCouch/ shows the home page with all 50 cities.
- [ ] A city page, e.g. `/GetOffTheCouch/chicago/`, and an event page load.
- [ ] View source on a city page: there's real HTML inside `<div id="app" data-ssr="1">`, plus a canonical link and Open Graph tags.
- [ ] An old link like `/GetOffTheCouch/#/chicago/feed` redirects to `/GetOffTheCouch/chicago/`.
- [ ] `/GetOffTheCouch/sitemap.xml` lists the per-city sitemaps.
- [ ] `/GetOffTheCouch/cities/` shows every city with Live/Beta.
- [ ] `/GetOffTheCouch/chicago/deadlines.ics` downloads a calendar.

## 4. The next few hours
- [ ] **Hourly runs:** each one should take under about 30 minutes end to end. If `publish` creeps toward its 45-minute timeout, lower `GOTC_GEOCODE_BUDGET` in refresh.yml (it's 10 now) or raise the shard size.
- [ ] **After 48 hours of green runs,** the go-live gate promotes beta cities that pass every check on its own. Watch `/cities/` and the "gate@…" lines in HEALTH.md.
- [ ] **Auto-opened issues** labeled `source-health` mean a source broke. They're informational: the site keeps last-known-good data, marked stale.

## Rollback: if the sharded refresh misbehaves
1. **Actions → Refresh data (monolithic fallback) → Run workflow.** This is the single-job refresh. It uses the same state branch and the same Pages deploy.
2. **To make the fallback the scheduled job:**
   - In `.github/workflows/refresh-monolithic.yml`, uncomment `schedule: [{ cron: "17 * * * *" }]`.
   - In `.github/workflows/refresh.yml`, comment out the `schedule:` line.
   - Commit and push. Both workflows share the `refresh` concurrency group, so they never overlap.
3. **If the deployed site itself is bad:** Actions → pick the last good "Refresh data" run → Re-run jobs. Or Settings → Pages: GitHub keeps the previous deployment until a new one succeeds.
4. **If the state branch is ever corrupted:** delete the `pipeline-state` branch. The next run starts fresh and refetches everything. It's slower once, but nothing is lost from `main`.
