#!/usr/bin/env bash
# One iteration of the GetOffTheCouch self-healing loop. Safe to run repeatedly (cron, CI, by hand).
#   1. doctor --fix   heal what can be healed (probe quarantined units, prune, rebuild bad exports)
#   2. run            fetch due units → build → export → HEALTH.md
#   3. contract tests the fresh export must validate against the schema
#   4. two-strike     on failure heal + retry once; second failure → diary FAILED line + exit 1
set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
stamp() { date -u "+%Y-%m-%d %H:%M UTC"; }
step() { "$@" >> build.log 2>&1; }

: > build.log
step $PY -m gotc doctor --fix
attempt() {
  step $PY -m gotc run --trigger loop ${GOTC_RUN_ARGS:-} && step $PY -m pytest -q tests/contract
}
if ! attempt; then
  echo "loop: first attempt failed; healing and retrying" >> build.log
  step $PY -m gotc doctor --fix
  if ! attempt; then
    echo "- $(stamp) · loop: FAILED twice — see build.log; needs agent attention (two-strike rule)" >> docs/DIARY.md
    tail -n 40 build.log
    exit 1
  fi
fi
step $PY -m gotc.autoideas || true
echo "loop OK"
tail -n 3 build.log
