# GetOffTheCouch — every workflow step is one target. `make help` lists them.
PY  := .venv/bin/python
UV  ?= uv
NPM := npm --prefix web


.PHONY: demo help setup check lint fmt typecheck test test-py test-web e2e pipeline build dev preview doctor heal loop schema ideas status sources clean

help:          ## list targets
	@grep -E '^[a-z0-9-]+:.*##' Makefile | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup:         ## one-command setup: Python venv + deps, web deps, pre-commit hooks
	$(UV) sync
	$(UV) pip install -e . -q
	$(NPM) ci || $(NPM) install
	.venv/bin/pre-commit install || true
	@test -f .env || cp .env.example .env
	@echo "setup done → try: make pipeline && make dev"

lint:          ## config validation + ruff lint + format check
	$(PY) -m gotc validate
	.venv/bin/ruff check gotc tests
	.venv/bin/ruff format --check gotc tests

fmt:           ## auto-format + autofix lint
	.venv/bin/ruff format gotc tests
	.venv/bin/ruff check --fix gotc tests

typecheck:     ## mypy --strict on the pipeline, tsc on the web app
	.venv/bin/mypy
	$(NPM) run typecheck

test-py:       ## Python tests (unit, adapters/fixtures, contract, integration) — no network
	$(PY) -m pytest

test-web:      ## dashboard unit tests (vitest)
	$(NPM) test

e2e:           ## dashboard smoke tests in a real browser (Playwright, frozen-clock demo data)
	$(PY) -m gotc demo --anchor 2026-10-16T15:00:00+00:00
	$(NPM) run e2e

test: test-py test-web  ## all tests

check: lint typecheck test  ## everything CI runs (run before every commit)

pipeline:      ## live: fetch due units → build → export → HEALTH.md
	$(PY) -m gotc run -v

build:         ## offline: rebuild + export from the DB
	$(PY) -m gotc build

dev:           ## dashboard dev server (http://localhost:5173)
	$(NPM) run dev

preview:       ## production build of the dashboard, served locally
	$(NPM) run build && $(NPM) run preview

doctor:        ## health checks, report only
	$(PY) -m gotc doctor

heal:          ## health checks + safe automatic repairs
	$(PY) -m gotc doctor --fix

loop:          ## one unattended iteration of the self-healing loop
	bash scripts/loop.sh

demo:          ## (re)build the fictional demo dataset → web/public/demo (use ?demo=1)
	$(PY) -m gotc demo

schema:        ## regenerate JSON Schema + TypeScript types from gotc/schema.py
	$(PY) -m gotc schema
	$(NPM) run gen:types

ideas:         ## top open ideas
	$(PY) -m gotc.ideas next

status:        ## health table in the terminal
	$(PY) -m gotc status

sources:       ## every unit and whether it's ready
	$(PY) -m gotc sources

clean:         ## remove caches (keeps the DB and raw payloads)
	rm -rf .pytest_cache .mypy_cache .ruff_cache data/http_cache web/dist
