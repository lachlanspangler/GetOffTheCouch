"""`gotc` command line. Every Makefile target is a thin wrapper around one of these commands."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

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
        cities=[x.strip() for x in a.cities.split(",") if x.strip()] if a.cities else None,
        force_build=a.force_build,
        build=not a.no_build,
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
    from gotc.pipeline.incremental import inputs_hash, mark_built, needs_build

    for c in reg.cities.values():
        if c.enabled and (a.city is None or c.slug == a.city):
            if a.incremental and not needs_build(db, c.slug, inputs_hash(db, reg, c), now)[0]:
                print(f"{c.slug:14} unchanged (incremental): not rebuilt")
                continue
            st = build_city(db, reg, c, now, geo)
            mark_built(db, c.slug, inputs_hash(db, reg, c), now)
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


def cmd_gate(a: argparse.Namespace, s: Settings) -> int:
    """Go-live gate (SCALING.md §3, ADR-0008): per-city tier + G1–G11 from what's in the DB. No network."""
    from gotc.pipeline.export import city_feed
    from gotc.pipeline.gate import gate_city

    reg = load_registry()
    db = _db(s)
    now = utcnow()
    cities = [c for c in reg.cities.values() if a.city is None or c.slug == a.city]
    if not cities:
        print(f"unknown city {a.city}", file=sys.stderr)
        return 2
    failed = 0
    out = {}
    for c in cities:
        feed = city_feed(db, reg, c, now) if c.enabled else None
        events = feed.events if feed else _events_for(db, c.slug)
        cov = gate_city(db, reg, c, now, events, persist=not a.dry_run)
        out[c.slug] = json.loads(cov.model_dump_json(exclude_none=True))
        failed += int(not cov.passed_hard)
        if a.json:
            continue
        marks = " ".join(
            f"{cid}{'✓' if cr.pass_hard is not False and cr.pass_soft is not False else ('◐' if cr.pass_hard is not False else '✗')}"
            for cid, cr in cov.criteria.items()
        )
        banner = " (banner)" if cov.banner else ""
        print(f"{c.slug:16} {cov.tier:6}{banner} hard={'pass' if cov.passed_hard else 'FAIL'}  {marks}")
        pills = ", ".join(
            f"{p.label} {p.count}{'' if p.state == 'strong' else ' ' + p.state}" for p in cov.pillars.values()
        )
        print(f"{'':16} sources {cov.sources_healthy}/{cov.sources_total} · geocoded {cov.geocode_rate:.0%} · {pills}")
        for r in cov.reasons if a.verbose_reasons else [r for r in cov.reasons if not r.startswith("thin:")]:
            print(f"{'':16} - {r}")
    if a.json:
        print(json.dumps(out, indent=2))
    return 1 if a.strict and failed else 0


def _rel(path: Any) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _city_for(slug: str) -> Any:
    """A city's config (even if disabled), else a skeleton from config/metros.yaml; None if unknown."""
    from gotc.config import CityConfig
    from gotc.config import load_yaml as _load
    from gotc.metros import metros
    from gotc.settings import CONFIG_DIR

    path = CONFIG_DIR / "cities" / f"{slug}.yaml"
    if path.exists():
        return CityConfig.model_validate(_load(path.read_text()))
    m = metros().get(slug)
    if m is None:
        return None
    return CityConfig(
        slug=m.slug,
        name=m.name,
        state=m.state,
        timezone=m.timezone,
        center=m.center,
        radius_km=m.radius_km,
        cbsa=m.cbsa,
        enabled=False,
    )


def cmd_discover(a: argparse.Namespace, s: Settings) -> int:
    """Probe for candidate sources for a city (live network, polite, robots-first). Writes data/discover/<slug>.yaml."""
    from gotc.discover.engine import FAMILIES, Discoverer, existing_hosts, parse_seed, write_candidates
    from gotc.http.client import PoliteClient
    from gotc.metros import metros

    city = _city_for(a.slug)
    if city is None:
        print(f"unknown city {a.slug}: add it to config/metros.yaml or config/cities/", file=sys.stderr)
        return 2
    families = tuple(f.strip() for f in a.families.split(",")) if a.families else FAMILIES
    unknown = [f for f in families if f not in FAMILIES]
    if unknown:
        print(f"unknown families {unknown}; choose from {', '.join(FAMILIES)}", file=sys.stderr)
        return 2
    record = None
    if a.record:
        import hashlib
        from pathlib import Path

        rec_dir = Path(a.record)
        rec_dir.mkdir(parents=True, exist_ok=True)

        def record(url: str, r: Any) -> None:
            name = hashlib.sha256(r.url.encode()).hexdigest()[:12]
            (rec_dir / f"{name}.body").write_bytes(r.content)
            with (rec_dir / "index.tsv").open("a") as fh:
                fh.write(f"{name}\t{r.status}\t{r.url}\n")

    http = PoliteClient(s, max_attempts=2, timeout_s=30)
    try:
        d = Discoverer(
            city,
            http,
            utcnow(),
            seeds=[parse_seed(x) for x in a.seed or []],
            families=families,
            budget=a.budget_requests,
            existing_hosts=existing_hosts(city),
            record=record,
            address=m.center_address if (m := metros().get(city.slug)) else None,
        )
        doc = d.run()
    finally:
        http.close()
    out = Path(a.out) if a.out else s.data_dir / "discover" / f"{city.slug}.yaml"
    write_candidates(doc, out)
    print(f"{city.slug}: {len(doc['candidates'])} candidates, {len(doc['excluded'])} excluded, "
          f"{doc['requests']['used']} requests → {out}")  # fmt: skip
    for c in doc["candidates"][:25]:
        u = c["unit"]
        print(f"  {c['confidence']:.2f}  {u['adapter']:14} {u['id']:44} {u['name'][:60]}")
    for x in doc["excluded"][:15]:
        print(f"  ---  excluded {x['excluded']:18} {json.dumps(x['unit_hint'])[:90]}")
    return 0


def cmd_city_new(a: argparse.Namespace, s: Settings) -> int:
    """Write config/cities/<slug>.yaml (enabled: false) from the config/metros.yaml row."""
    from gotc.config import CityConfig
    from gotc.metros import metros
    from gotc.settings import CONFIG_DIR

    m = metros().get(a.slug)
    if m is None:
        print(f"{a.slug} is not in config/metros.yaml", file=sys.stderr)
        return 2
    path = CONFIG_DIR / "cities" / f"{m.slug}.yaml"
    if path.exists() and not a.force:
        print(f"{_rel(path)} already exists (use --force to overwrite)", file=sys.stderr)
        return 1
    CityConfig(
        slug=m.slug,
        name=m.name,
        state=m.state,
        timezone=m.timezone,
        center=m.center,
        radius_km=m.radius_km,
        cbsa=m.cbsa,
        enabled=False,
    )  # fmt: skip  — validate before writing
    lat, lon = m.center
    center_note = (
        f"Census geocoder: {m.center_matched}"
        if m.center_source == "census_geocoder"
        else "SCALING.md §1 (general knowledge, not surveyed)"
    )
    path.write_text(
        f"# {m.name}, {m.state}: CBSA {m.cbsa} {m.msa} ({m.msa_pop_m} M, Census V2024). Skeleton from `gotc city new`.\n"
        f"# Draft: enabled stays false until `gotc gate --city {m.slug}` passes (ADR-0008). Candidate sources:\n"
        f"# `gotc discover {m.slug} --seed library=… --seed university=…` → data/discover/{m.slug}.yaml.\n"
        f"# center: {center_note}\n"
        f"# aliases: fill from the OMB CBSA principal-city list (delineation file, list 2), not from memory.\n"
        f"slug: {m.slug}\n"
        f"name: {m.name}\n"
        f"state: {m.state}\n"
        f"timezone: {m.timezone}\n"
        f"center: [{lat}, {lon}]\n"
        f"radius_km: {m.radius_km:g}\n"
        f'cbsa: "{m.cbsa}"\n'
        "aliases: []\n"
        "enabled: false\n"
        "sources: []\n"
    )
    print(f"wrote {_rel(path)}")
    return 0


def cmd_city_recenter(a: argparse.Namespace, s: Settings) -> int:
    """Re-derive config/metros.yaml centers from city-hall addresses with the Census geocoder (live, ~50 calls)."""
    from gotc.http.client import PoliteClient
    from gotc.metros import recenter
    from gotc.settings import CONFIG_DIR

    http = PoliteClient(s, max_attempts=2)
    try:
        for line in recenter(CONFIG_DIR / "metros.yaml", http, a.slug):
            print(line)
    finally:
        http.close()
    return 0


def _events_for(db: Database, city: str) -> list[Any]:
    from gotc.schema import Event

    out = []
    for r in db.all("SELECT data FROM events WHERE city = ? ORDER BY start_at", (city,)):
        try:
            out.append(Event.model_validate_json(r["data"]))
        except ValueError:
            continue
    return out


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
    r.add_argument("--cities", help="comma list: only these cities' units (a CI shard)")
    r.add_argument("--no-build", action="store_true", help="fetch only (CI shards; the publish job builds)")
    r.add_argument("--force-build", action="store_true", help="rebuild every city even if its inputs didn't change")
    r.add_argument("--strict", action="store_true", help="exit 1 if any unit failed")
    r.add_argument("--trigger", default="cli")
    r.set_defaults(fn=cmd_run)

    b = sub.add_parser("build", help="rebuild + export from the DB (offline)")
    b.add_argument("--city")
    b.add_argument("--geocode", action="store_true", help="allow live geocoding lookups")
    b.add_argument("--incremental", action="store_true", help="skip cities whose build inputs didn't change")
    b.set_defaults(fn=cmd_build)

    rp = sub.add_parser("replay", help="re-parse stored raw payloads (after a parser fix)")
    rp.add_argument("unit", nargs="?")
    rp.set_defaults(fn=cmd_replay)

    fg = sub.add_parser("forget", help="drop a unit's records + baseline after a deliberate config change")
    fg.add_argument("unit")
    fg.add_argument("--reason", default="config change")
    fg.set_defaults(fn=cmd_forget)

    sub.add_parser("validate", help="fast config validation (pre-commit gate)").set_defaults(fn=cmd_validate)
    g = sub.add_parser("gate", help="go-live gate: per-city tier + coverage (G1–G11), from the DB")
    g.add_argument("--city")
    g.add_argument("--json", action="store_true")
    g.add_argument("--dry-run", action="store_true", help="don't persist the tier")
    g.add_argument("--strict", action="store_true", help="exit 1 if any city fails a hard criterion")
    g.add_argument("--all-reasons", dest="verbose_reasons", action="store_true", help="also list soft misses")
    g.set_defaults(fn=cmd_gate)

    dc = sub.add_parser("discover", help="probe for candidate sources (live, polite) → data/discover/<slug>.yaml")
    dc.add_argument("slug")
    dc.add_argument("--seed", action="append", help="kind=URL (library|university|venue|parks|volunteer|other)")
    dc.add_argument("--families", help="comma list: socrata,datagov,arcgis,library,university,venue,volunteer,…")
    dc.add_argument("--budget-requests", type=int, default=400)
    dc.add_argument("--out")
    dc.add_argument("--record", help="save every response body here (for fixtures)")
    dc.set_defaults(fn=cmd_discover)

    cy = sub.add_parser("city", help="city scaffolding")
    cy_sub = cy.add_subparsers(dest="city_cmd", required=True)
    cn = cy_sub.add_parser("new", help="write config/cities/<slug>.yaml (enabled: false) from config/metros.yaml")
    cn.add_argument("slug")
    cn.add_argument("--force", action="store_true")
    cn.set_defaults(fn=cmd_city_new)
    cr = cy_sub.add_parser("recenter", help="re-derive config/metros.yaml centers via the Census geocoder (live)")
    cr.add_argument("--slug")
    cr.set_defaults(fn=cmd_city_recenter)

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
