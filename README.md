# GetOffTheCouch

**ur city made easy.** A living, auto-updating dashboard for anyone who just moved to (or is about to move to) a US city. It shows everything worth getting off the couch for, plus every deadline you'd otherwise miss:
- beer leagues and run clubs
- block parties and new bar openings
- concerts with live prices
- volunteering
- cons and ren faires
- trivia

It's a **pipeline product first**:
- **Sources:** official APIs and open data, polite and robots-aware.
- **One strict schema:** cross-source dedup, estimates with honest ranges, and freshness SLAs.
- **Self-healing:** broken sources are quarantined, but their last-known-good data keeps serving, marked stale.
- **Dashboard:** static and fast, refreshed hourly by GitHub Actions.

```bash
make setup      # venv + deps + web deps + pre-commit
make pipeline   # live: fetch due sources → build → export (writes web/public/data)
make dev        # dashboard at http://localhost:5173  (add ?demo=1 for the fictional demo dataset)
make check      # lint, mypy --strict, all tests, web typecheck + tests
make e2e        # browser smoke tests (needs `python -m gotc demo --anchor 2026-10-16T15:00:00+00:00`)
```

API keys are optional. See `.env.example`. Sources without a key show as "needs key" on the Health page.

**Where to read next:**
- [`CLAUDE.md`](CLAUDE.md): architecture map and rules
- [`docs/STATUS.md`](docs/STATUS.md): what works and what's next
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md): the build loop and the self-healing loop
- [`docs/SOURCES.md`](docs/SOURCES.md): every data source
- [`docs/adr/`](docs/adr/): design decisions
