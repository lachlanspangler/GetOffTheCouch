"""Write docs/research/NON_EVENTS_AUDIT.md from the DB's quarantine (gated_listings) after a build (ADR-0010).

    .venv/bin/python scripts/non_events_audit.py [--db data/gotc.db]

Per source: listings kept vs held back (gate + ingest), the top rules, and a random sample of kept and held-back
titles so a person can sanity-check each feed; the top rejected patterns overall; the golden set's precision/recall.
Deterministic (seeded) so a re-run on the same DB writes the same file.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gotc.config import load_registry  # noqa: E402
from gotc.pipeline.category_basis import looks_mixed  # noqa: E402


def family(src) -> str:  # type: ignore[no-untyped-def]
    if src is None:
        return "other"
    n = f"{src.name} {src.id}".lower()
    if src.params.get("audience_filter") == "institution" or src.adapter in ("localist", "livewhale"):
        return "university"
    if src.adapter in ("bibliocommons", "communico") or "librar" in n:
        return "library"
    if looks_mixed(src.id, src.name, src.adapter, src.params):
        return "city & civic calendars"
    return "venues & other"


def md(s: str) -> str:
    return s.replace("|", "/").replace("\n", " ").strip()


def golden_line() -> tuple[str, list[str]]:
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-s",
            "tests/unit/test_listing_gate_golden.py",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    m = re.search(r"listing gate on (\d+) golden listings: precision ([\d.]+), recall ([\d.]+) (\{.*\})", out.stdout)
    if not m:
        return "golden set: could not run (see `pytest tests/unit/test_listing_gate_golden.py -s`)", []
    return f"**{m.group(1)} labelled listings · precision {m.group(2)} · recall {m.group(3)}** `{m.group(4)}`", []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "gotc.db"))
    ap.add_argument("--out", default=str(ROOT / "docs" / "research" / "NON_EVENTS_AUDIT.md"))
    a = ap.parse_args()
    con = sqlite3.connect(a.db)
    con.row_factory = sqlite3.Row
    reg = load_registry()
    sources = reg.all_sources()
    rnd = random.Random(20261102)

    held = con.execute("SELECT * FROM gated_listings").fetchall()
    kept_rows = con.execute(
        "SELECT em.source_id, em.city, json_extract(e.data, '$.title') title FROM events e"
        " JOIN event_members em ON em.event_id = e.id"
    ).fetchall()
    kept: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in kept_rows:
        kept[(r["source_id"], r["city"])].append(r["title"])
    by_unit: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for r in held:
        by_unit[(r["source_id"], r["city"])].append(r)

    total_kept = sum(len(v) for v in kept.values())
    gate_n = sum(1 for r in held if r["stage"] == "build")
    ingest_n = sum(1 for r in held if r["stage"] == "ingest")
    rules = Counter(r["rule"] for r in held)
    distinct = {rule: len({r["title"] for r in held if r["rule"] == rule}) for rule in rules}
    fams = Counter(r["family"] for r in held)

    L: list[str] = []
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    L += [
        "# Non-events audit (ADR-0010)",
        "",
        f"_Generated {now} by `scripts/non_events_audit.py` from `{Path(a.db).name}` after a full build. Re-run after any"
        " rule change._",
        "",
        "## Summary",
        "",
        f"- **{total_kept:,}** listings published (per source membership), **{gate_n:,}** held back by the build-time"
        f" gate, **{ingest_n:,}** skipped at ingest (online-only, excluded places, campus-internal) — every one"
        " quarantined in `gated_listings` with its rule and reason, never silently dropped.",
        f"- Golden set (`tests/fixtures/listing_gate/golden.yaml`, labelled blind to the rules): {golden_line()[0]}."
        " **Caveat:** 245 listings under-sample the campus audience-tag rule, so the per-rule false-positive rates the"
        " cold data review measured (below) matter more than this headline number.",
        "- Ingest-stage counts appear after each source's next fetch. A DB built only from older records shows build-stage"
        " rows only.",
        "- The FIU withdrawal deadline that started this: see *FIU* below.",
        "",
        "## Top rules",
        "",
        "| Rule | Held back (rows) | Distinct titles | Family |",
        "|---|---|---|---|",
    ]
    fam_of = {r["rule"]: r["family"] for r in held}
    L += [f"| `{rule}` | {n:,} | {distinct[rule]:,} | {fam_of[rule]} |" for rule, n in rules.most_common()]
    L += ["", "## Top rejected patterns (matched text)", "", "| Rule | Matched text | Count |", "|---|---|---|"]
    ev = Counter((r["rule"], (r["evidence"] or r["reason"])[:60].lower()) for r in held)
    L += [f"| `{rule}` | {md(e)} | {n} |" for (rule, e), n in ev.most_common(40)]

    # per source, grouped by family, hardest families first
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key in set(kept) | set(by_unit):
        groups[family(sources.get(key[0]))].append(key)
    order = ["university", "library", "city & civic calendars", "venues & other"]
    L += [
        "",
        "## Per source",
        "",
        "Kept = published listings from this source; held = quarantined (gate + ingest). Samples are random (seeded):",
        "read the held-back column for anything real, and the kept column for anything that isn't.",
    ]
    for fam in order:
        keys = sorted(groups.get(fam, []), key=lambda k: (-len(by_unit.get(k, [])), k))
        if not keys:
            continue
        n_held = sum(len(by_unit.get(k, [])) for k in keys)
        n_kept = sum(len(kept.get(k, [])) for k in keys)
        L += [
            "",
            f"### {fam.title()} ({len(keys)} units · {n_kept:,} kept · {n_held:,} held back)",
            "",
            "| Unit | Kept | Held | Share held | Top rules |",
            "|---|---|---|---|---|",
        ]
        for k in keys:
            h, kp = by_unit.get(k, []), kept.get(k, [])
            if not h and fam == "venues & other":
                continue
            share = len(h) / max(1, len(h) + len(kp))
            top = ", ".join(f"{r} {n}" for r, n in Counter(x["rule"] for x in h).most_common(3))
            L.append(f"| `{k[0]}@{k[1]}` | {len(kp)} | {len(h)} | {share:.0%} | {top} |")
        L += ["", "<details><summary>Samples: kept vs held back</summary>", ""]
        for k in keys:
            h, kp = by_unit.get(k, []), kept.get(k, [])
            if not h and fam == "venues & other":
                continue
            hc = Counter((x["title"], x["rule"]) for x in h)
            kc = Counter(kp)
            hs = rnd.sample(sorted(hc), min(4, len(hc)))
            ks = rnd.sample(sorted(kc), min(5 if not h else 3, len(kc)))
            L.append(f"**`{k[0]}@{k[1]}`**")
            L += [f"- ✕ {md(t)[:110]}{f' ×{hc[(t, r)]}' if hc[(t, r)] > 1 else ''} — _{r}_" for t, r in hs]
            L += [f"- ✓ {md(t)[:110]}{f' ×{kc[t]}' if kc[t] > 1 else ''}" for t in ks]
            L.append("")
        L += ["</details>"]

    fiu = con.execute(
        "SELECT title, rule, reason FROM gated_listings WHERE source_id = 'fiu_events' AND title LIKE '%withdraw%'"
    ).fetchall()
    fiu_pub = con.execute(
        "SELECT COUNT(*) c FROM events WHERE city = 'miami' AND json_extract(data, '$.title') LIKE '%withdraw%'"
    ).fetchone()
    L += ["", "## FIU", "", f'Published Miami listings mentioning "withdraw": **{fiu_pub["c"]}**. Held back:', ""]
    L += [f"- {md(r['title'])} — `{r['rule']}`: {r['reason']}" for r in fiu] or ["- (none in this DB)"]
    L += [
        "",
        "## Known gaps and judgment calls",
        "",
        "- **Golden-set disagreements I left as labelled.** Labels are the blind labeller's; where I disagree I say so"
        " here instead of editing the label. See `pytest tests/unit/test_listing_gate_golden.py -s` for the current"
        " misses.",
        '- **Placeholder opponents** ("Cavaliers vs. TBD") are kept: the game happens. The labeller called one a'
        " non-event (unsure).",
        "- **Cancelled listings** stay in the export marked cancelled (the city page hides them; a saved event still"
        " says it was cancelled), so the gate doesn't hold them back.",
        '- **License-signal openings** ("— new business registration") are a separate kind (`opening`), shown as'
        " openings, not events; the gate doesn't apply to them.",
        "- **Public board/commission meetings** are held back as administration (soft rule): a newcomer rarely wants a"
        " zoning board's business meeting. Community and neighborhood meetings, public input sessions, town halls and"
        " candidate forums are kept.",
        "- **Campus audience tags.** A campus listing tagged only for current students / faculty / staff (no public tag)"
        " is held back unless its title or description says it's a performance, exhibition, game, talk, screening,"
        ' celebration or fair. A bare "Students" tag doesn\'t count: campuses put it on public events too.',
        "- **Uncategorized campus listings are published** (as uncategorized, with no estimates). A rule that held them"
        " back was retired after the cold data review found about 55% of them were real talks and exhibitions.",
        "- **Same title, different verdicts.** A campus can tag occurrences of one program differently, so one date may"
        " be held and another published. The audit shows both.",
        '- **Away games** ("Football at Missouri") on campus athletics feeds aren\'t gated by title: many "X at Y"'
        " games are crosstown. That needs a venue-distance check (idea ledger).",
    ]
    Path(a.out).write_text("\n".join(L) + "\n")
    print(f"wrote {a.out}: {gate_n} gate + {ingest_n} ingest held back, {total_kept} kept")
    json.dump({"gate": gate_n, "ingest": ingest_n, "kept": total_kept, "rules": dict(rules), "families": dict(fams)},
              open(Path(a.out).with_suffix(".json"), "w"), indent=1)  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
