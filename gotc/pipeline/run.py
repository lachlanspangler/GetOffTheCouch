"""The scheduler: run every due unit, then build + export + report. Designed to be run by cron every hour.

Freshness is enforced per data type: a unit is *due* when ``next_due_at <= now`` (set from its cadence
on success, or from the retry/backoff policy on failure). Running more often than needed is harmless —
non-due units are skipped in microseconds — so CI just runs ``gotc run`` hourly.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from gotc.config import Registry
from gotc.health.report import render
from gotc.health.store import load_health
from gotc.health.store import log as hlog
from gotc.http.client import PoliteClient
from gotc.pipeline.build import BuildStats, build_city
from gotc.pipeline.export import export_all
from gotc.pipeline.geocode import Geocoder
from gotc.pipeline.ingest import UnitResult, run_unit
from gotc.settings import Settings
from gotc.storage.db import Database, iso, utcnow

log = logging.getLogger(__name__)


@dataclass
class RunReport:
    run_id: int
    started_at: datetime
    units: list[UnitResult] = field(default_factory=list)
    builds: list[BuildStats] = field(default_factory=list)
    status: str = "ok"
    build_errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        by: dict[str, int] = {}
        for u in self.units:
            by[u.status] = by.get(u.status, 0) + 1
        ev = sum(b.events for b in self.builds)
        parts = ", ".join(f"{v} {k}" for k, v in sorted(by.items()))
        return f"run {self.run_id} {self.status}: units[{parts}] → {ev} events in {len(self.builds)} cities"


def run(
    db: Database,
    reg: Registry,
    settings: Settings,
    city: str | None = None,
    source: str | None = None,
    force: bool = False,
    build: bool = True,
    transport: httpx.BaseTransport | None = None,
    now: datetime | None = None,
    max_seconds: float | None = None,
    geocode: bool = True,
    trigger: str = "cli",
    include_demo: bool = False,
    client: PoliteClient | None = None,
) -> RunReport:
    started = now or utcnow()
    cur = db.execute("INSERT INTO runs (started_at, status, trigger) VALUES (?, 'running', ?)", (iso(started), trigger))
    report = RunReport(run_id=int(cur.lastrowid or 0), started_at=started)
    http = client or PoliteClient(settings, transport=transport)
    t0 = time.monotonic()
    units = reg.units(city=city, source=source)
    # most overdue first, so a time-boxed run spends its budget where freshness matters most
    units.sort(key=lambda u: iso(load_health(db, u.key).next_due_at or started.replace(year=2000)))
    try:
        for unit in units:
            if max_seconds and time.monotonic() - t0 > max_seconds:
                log.warning("time budget reached; remaining units stay due for the next run")
                break
            res = run_unit(db, reg, unit, http, settings, now or utcnow(), run_id=report.run_id, force=force)
            report.units.append(res)
            log.info(
                "%-45s %-9s valid=%-5s rej=%-4s %s",
                res.unit,
                res.status,
                res.valid,
                res.rejected,
                res.error or "",
            )
        if build:
            geocoder = Geocoder(db, http if geocode and not settings.offline else None)
            touched = {u.city.slug for u in units} if source else None  # --source X: rebuild only its cities
            for c in reg.cities.values():
                if c.enabled and (city is None or c.slug == city) and (touched is None or c.slug in touched):
                    try:
                        report.builds.append(build_city(db, reg, c, now or utcnow(), geocoder))
                    except Exception as e:  # one city's bug must not blank every city's dashboard
                        log.exception("build failed for %s", c.slug)
                        report.build_errors.append(f"{c.slug}: {type(e).__name__}: {e}")
                        hlog(
                            db,
                            f"build@{c.slug}",
                            "error",
                            "build_error",
                            f"{type(e).__name__}: {e}"[:500],
                            now or utcnow(),
                        )
            if geocode and not settings.offline:
                from gotc.pipeline import starter_pack

                for st in sorted({c.state for c in reg.cities.values() if c.enabled}):
                    starter_pack.verify(db, http, starter_pack.load(st), now or utcnow())
            export_all(db, reg, settings.web_data_dir, now or utcnow(), include_demo=include_demo)
            (settings.docs_dir / "HEALTH.md").write_text(render(db, reg, now or utcnow()))
        failed = [u for u in report.units if u.status == "failed"]
        report.status = "ok" if not failed and not report.build_errors else "partial"
    except BaseException:
        report.status = "failed"
        raise
    finally:
        http.close()
        db.execute(
            "UPDATE runs SET finished_at = ?, status = ?, summary = ? WHERE id = ?",
            (iso(utcnow()), report.status, report.summary(), report.run_id),
        )
    return report
