"""Open a GitHub issue when a unit is quarantined; close it when it recovers. Idempotent (one issue per unit).

Used by .github/workflows/refresh.yml — failures stay loud even when nobody is looking at the dashboard.
Requires the `gh` CLI and GH_TOKEN; does nothing (exit 0) when they're unavailable, e.g. locally.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HEALTH = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "health.json"
LABEL = "source-health"


MAX_NEW = 10


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    if not shutil.which("gh") or not HEALTH.exists():
        print("gh or health.json unavailable; skipping")
        return 0
    units = json.loads(HEALTH.read_text())["units"]
    with contextlib.suppress(subprocess.CalledProcessError):  # label may already exist
        gh("label", "create", LABEL, "--color", "D93F0B", "--description", "Automated: a data source is broken")
    open_issues = json.loads(
        gh("issue", "list", "--label", LABEL, "--state", "open", "--json", "number,title", "--limit", "200")
    )
    by_title = {i["title"]: i["number"] for i in open_issues}
    opened = 0
    for u in units:
        key = f"{u['source_id']}@{u['city']}"
        title = f"Source quarantined: {key}"
        if u["state"] == "quarantined" and title not in by_title:
            if opened >= MAX_NEW:  # a mass outage (our network, a shared platform) shouldn't open 100 issues at once
                print(f"skipped (cap of {MAX_NEW} new issues per run):", title)
                continue
            opened += 1
            body = (
                f"**{u['name']}** (`{key}`) failed repeatedly and is quarantined. Its last good data is still served, "
                f"marked stale after {u['sla_hours']}h.\n\nLast error: `{u.get('last_error') or '?'}`\n\n"
                "Fix recipe: docs/WORKFLOW.md → *Fix a quarantined unit*. This issue closes itself when the source recovers."
            )
            gh("issue", "create", "--title", title, "--label", LABEL, "--body", body)
            print("opened:", title)
        elif u["state"] in ("healthy", "recovering") and title in by_title:
            gh("issue", "close", str(by_title[title]), "--comment", f"Recovered: state is now **{u['state']}**.")
            print("closed:", title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
