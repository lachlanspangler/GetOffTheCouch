"""`gotc` command line. Every Makefile target is a thin wrapper around one of these commands."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from gotc.config import load_registry
from gotc.settings import ROOT, Settings, load_dotenv
from gotc.storage.db import Database, iso, utcnow


def _db(settings: Settings) -> Database:
    return Database(settings.db_path)


def cmd_run(a: argparse.Namespace, s: Settings) -> int:
    from gotc.pipeline.run import run

    reg = load_registry()
    db = _db(s)
    rep = run(
        db,
        reg,
        s,
        city=a.city,
        source=a.source,
        force=a.force,
        max_seconds=a.max_minutes * 60 if a.max_minutes else None,
        geocode=not a.no_geocode,
        trigger=a.trigger,
    )
    print(rep.summary())
    for u in rep.units:
        if u.status in ("failed",):
            print(f"  ✗ {u.unit}: {u.error_kind} — {u.error}")
    _diary_line(s, rep.summary())
    if a.strict and rep.status != "ok":
        return 1
    return 0


def cmd_build(a: argparse.Namespace, s: Settings) -> int:
    """Rebuild + export from what's already in the DB. No network (unless --geocode)."""
    from gotc.health.report import render
    from gotc.http.client import PoliteClient
    from gotc.pipeline.build import build_city
    from gotc.pipeline.export import export_all
    from gotc.pipeline.geocode import Geocoder

    reg = load_registry()
    db = _db(s)
    now = utcnow()
    http = PoliteClient(s) if a.geocode else None
    geo = Geocoder(db, http)
    for c in reg.cities.values():
        if c.enabled and (a.city is None or c.slug == a.city):
            st = build_city(db, reg, c, now, geo)
            print(
                f"{c.slug:14} records={st.records:<5} events={st.events:<5} merged={st.merged:<4} "
                f"geocoded={st.geocoded:<4} venues={st.venues:<4} deadlines={st.deadlines_extracted} outside={st.outside}"
            )
    export_all(db, reg, s.web_data_dir, now)
    (s.docs_dir / "HEALTH.md").write_text(render(db, reg, now))
    return 0


def cmd_replay(a: argparse.Namespace, s: Settings) -> int:
    """Re-parse the latest stored raw payloads for a unit (after fixing a parser) — no network."""
    from gotc.adapters.base import Payload, get_adapter
    from gotc.pipeline.ingest import mark_gone, parse_payloads, upsert_records
    from gotc.storage.raw import RawStore

    reg = load_registry()
    db = _db(s)
    raw = RawStore(s.raw_dir)
    units = [u for u in reg.units() if a.unit in (None, u.key, u.source.id)]
    for u in units:
        last = db.one("SELECT MAX(fetched_at) t FROM raw_fetches WHERE unit = ?", (u.key,))
        if not last or not last["t"]:
            continue
        rows = db.all("SELECT * FROM raw_fetches WHERE unit = ? AND fetched_at = ?", (u.key, last["t"]))
        from datetime import datetime

        fetched_at = datetime.fromisoformat(last["t"])
        ext_map = {"json": "json", "ics": "ics", "html": "html", "xml": "xml", "yaml": "yaml"}
        payloads = [
            (
                Payload(
                    r["url"],
                    r["status"],
                    raw.get(r["path"]),
                    fetched_at,
                    ext_map.get(r["path"].split(".")[-2], "json"),
                ),
                r["id"],
            )
            for r in rows
            if raw.exists(r["path"])
        ]
        parsed = parse_payloads(get_adapter(u.source.adapter), u, payloads, fetched_at)
        with db.tx():
            upsert_records(db, u, parsed, fetched_at)
            if not parsed.rejects:  # same snapshot semantics as a live fetch
                mark_gone(db, u, {ev.record_id for ev, _ in parsed.valid}, fetched_at)
        print(
            f"{u.key}: replayed {len(payloads)} payload(s) → {len(parsed.valid)} valid, {len(parsed.rejects)} rejected"
        )
        for hint, err, _ in parsed.rejects[:5]:
            print(f"    reject {hint[:60]!r}: {err[:160]}")
    return 0


def cmd_forget(a: argparse.Namespace, s: Settings) -> int:
    """Operator tool after a deliberate config change: drop a unit's records + learned baseline, refetch next run.

    (Without this, the health system would rightly refuse to delete records after a big volume drop.)
    """
    db = _db(s)
    with db.tx():
        n = db.execute("DELETE FROM source_records WHERE unit = ?", (a.unit,)).rowcount
        db.execute("UPDATE unit_health SET baseline_count = NULL, next_due_at = NULL WHERE unit = ?", (a.unit,))
        db.execute(
            "INSERT INTO health_log (at, unit, level, kind, message) VALUES (?, ?, 'info', 'forget', ?)",
            (iso(utcnow()), a.unit, f"operator reset: {n} records dropped ({a.reason})"),
        )
    print(f"{a.unit}: dropped {n} records and the volume baseline; it will refetch on the next run")
    return 0


def cmd_validate(a: argparse.Namespace, s: Settings) -> int:
    """Fast config gate (pre-commit): cities/sources load, adapters exist, categories valid, registries parse."""
    import yaml as _yaml

    from gotc.adapters.base import get_adapter
    from gotc.adapters.curated import CuratedEntry
    from gotc.pipeline.starter_pack import load as load_sp
    from gotc.settings import CONFIG_DIR
    from gotc.taxonomy import load_taxonomy

    errors: list[str] = []
    try:
        tax = load_taxonomy()
        reg = load_registry()
    except Exception as exc:
        print(f"config does not load: {exc}")
        return 1
    for sid, src in reg.all_sources().items():
        try:
            get_adapter(src.adapter).check_config(src)
        except Exception as exc:
            errors.append(f"{sid}: {exc}")
        for cat in [*(src.params.get("category_map") or {}).values(), src.params.get("default_category")]:
            if cat and not tax.is_valid(cat):
                errors.append(f"{sid}: unknown category {cat!r}")
    for path in sorted((CONFIG_DIR / "registry").glob("*.yaml")):
        for raw in _yaml.safe_load(path.read_text()) or []:
            try:
                entry = CuratedEntry.model_validate(raw)
                if not tax.is_valid(entry.category):
                    errors.append(f"{path.name}:{entry.id}: unknown category {entry.category}")
            except Exception as ex:
                errors.append(f"{path.name}: {str(ex)[:200]}")
    for path in sorted((CONFIG_DIR / "starter_pack").glob("*.yaml")):
        try:
            load_sp(path.stem.upper())
        except Exception as ex:
            errors.append(f"starter_pack/{path.name}: {str(ex)[:200]}")
    for msg in errors:
        print("ERROR", msg)
    print(f"validate: {len(reg.cities)} cities, {len(reg.units())} units, {len(errors)} errors")
    return 1 if errors else 0


def cmd_status(a: argparse.Namespace, s: Settings) -> int:
    from gotc.health.report import render

    print(render(_db(s), load_registry(), utcnow()))
    return 0


def cmd_sources(a: argparse.Namespace, s: Settings) -> int:
    reg = load_registry()
    for u in reg.units():
        missing = reg.missing_requirements(u.source)
        flag = "needs " + ",".join(missing) if missing else ("disabled" if not u.source.enabled else "ready")
        print(
            f"{u.key:48} {u.source.adapter:12} {u.source.data_type.value:13} every {reg.cadence_hours(u.source):>5.1f}h  {flag}"
        )
    return 0


def cmd_doctor(a: argparse.Namespace, s: Settings) -> int:
    from gotc.health.doctor import doctor

    return doctor(s, fix=a.fix)


def cmd_schema(a: argparse.Namespace, s: Settings) -> int:
    """Write the CityFeed JSON Schema (source of truth for the dashboard's TypeScript types)."""
    from gotc.schema import SCHEMA_VERSION, CityDetails, CityFeed

    (ROOT / "schema").mkdir(exist_ok=True)
    details = CityDetails.model_json_schema()
    (ROOT / "schema" / "citydetails.schema.json").write_text(json.dumps(details, indent=2, sort_keys=True) + "\n")
    schema = CityFeed.model_json_schema()
    schema["$id"] = f"https://getoffthecouch.app/schema/cityfeed-{SCHEMA_VERSION}.json"
    out = ROOT / "schema" / "cityfeed.schema.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(ROOT)} (schema {SCHEMA_VERSION})")
    return 0


def cmd_demo(a: argparse.Namespace, s: Settings) -> int:
    """Build the fictional demo dataset (web/public/demo) through the real pipeline."""
    from datetime import datetime

    from gotc.demo import build_demo

    anchor = datetime.fromisoformat(a.anchor) if a.anchor else None
    print(f"demo data written to {build_demo(anchor)}")
    return 0


def cmd_record(a: argparse.Namespace, s: Settings) -> int:
    """Fetch a unit live once and save its raw payloads as test fixtures (tests/fixtures/<source_id>/)."""
    from gotc.adapters.base import FetchContext, get_adapter
    from gotc.http.client import PoliteClient

    reg = load_registry()
    unit = next((u for u in reg.units() if a.unit in (u.key, u.source.id)), None)
    if unit is None:
        print(f"unknown unit {a.unit}", file=sys.stderr)
        return 2
    http = PoliteClient(s)
    fr = get_adapter(unit.source.adapter).fetch(FetchContext(unit=unit, http=http, now=utcnow(), settings=s))
    out = ROOT / "tests" / "fixtures" / unit.source.id
    out.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(fr.payloads[: a.max_payloads]):
        content = p.content
        if a.trim and p.content_type == "json":
            content = _trim_json(content, a.trim)
        (out / f"payload_{i}.{p.content_type}").write_bytes(content)
    meta = {
        "unit": unit.key,
        "recorded_at": iso(utcnow()),
        "payloads": min(len(fr.payloads), a.max_payloads),
        "note": "real response recorded with `gotc record`; trimmed only by record count",
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"saved {meta['payloads']} payload(s) to {out.relative_to(ROOT)}")
    return 0


def _trim_json(content: bytes, n: int) -> bytes:
    data = json.loads(content)
    if isinstance(data, list):
        data = data[:n]
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                data[k] = v[:n]
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if isinstance(v2, list):
                        v[k2] = v2[:n]
    return json.dumps(data, indent=1).encode()


def _diary_line(s: Settings, text: str) -> None:
    path = s.docs_dir / "DIARY.md"
    if not path.exists():
        return
    stamp = utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with path.open("a") as fh:
        fh.write(f"- {stamp} · {text}\n")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    p = argparse.ArgumentParser(prog="gotc", description="GetOffTheCouch pipeline")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="fetch due units, build, export, report")
    r.add_argument("--city")
    r.add_argument("--source")
    r.add_argument("--force", action="store_true", help="ignore next_due_at")
    r.add_argument("--max-minutes", type=float, default=None)
    r.add_argument("--no-geocode", action="store_true")
    r.add_argument("--strict", action="store_true", help="exit 1 if any unit failed")
    r.add_argument("--trigger", default="cli")
    r.set_defaults(fn=cmd_run)

    b = sub.add_parser("build", help="rebuild + export from the DB (offline)")
    b.add_argument("--city")
    b.add_argument("--geocode", action="store_true", help="allow live geocoding lookups")
    b.set_defaults(fn=cmd_build)

    rp = sub.add_parser("replay", help="re-parse stored raw payloads (after a parser fix)")
    rp.add_argument("unit", nargs="?")
    rp.set_defaults(fn=cmd_replay)

    fg = sub.add_parser("forget", help="drop a unit's records + baseline after a deliberate config change")
    fg.add_argument("unit")
    fg.add_argument("--reason", default="config change")
    fg.set_defaults(fn=cmd_forget)

    sub.add_parser("validate", help="fast config validation (pre-commit gate)").set_defaults(fn=cmd_validate)
    sub.add_parser("status", help="print the health table").set_defaults(fn=cmd_status)
    sub.add_parser("sources", help="list units and whether they're ready").set_defaults(fn=cmd_sources)

    d = sub.add_parser("doctor", help="health checks; --fix applies safe repairs")
    d.add_argument("--fix", action="store_true")
    d.set_defaults(fn=cmd_doctor)

    sub.add_parser("schema", help="write schema/cityfeed.schema.json").set_defaults(fn=cmd_schema)

    dm = sub.add_parser("demo", help="build the fictional, clearly-labeled demo dataset")
    dm.add_argument("--anchor", help="ISO datetime the demo is relative to (default: now)")
    dm.set_defaults(fn=cmd_demo)

    rec = sub.add_parser("record", help="record live payloads as test fixtures")
    rec.add_argument("unit")
    rec.add_argument("--max-payloads", type=int, default=1)
    rec.add_argument("--trim", type=int, default=0, help="keep only N records per JSON list")
    rec.set_defaults(fn=cmd_record)

    a = p.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if a.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return int(a.fn(a, Settings()))


if __name__ == "__main__":
    raise SystemExit(main())
