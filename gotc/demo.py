"""`gotc demo`: build the clearly-labeled demo dataset by running the *real* pipeline on fictional records.

Writes only to data/demo/ and web/public/demo/. Three fetches 48h/24h/0h before the anchor create
price/listing history so trends and "selling fast" render. The export sets ``is_demo`` everywhere.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import datetime, timedelta

from gotc.config import CityConfig, Neighborhood, Registry, SourceConfig, SourcesFile
from gotc.pipeline.run import run
from gotc.schema import DataType
from gotc.settings import ROOT, Settings
from gotc.storage.db import Database, utcnow


def build_demo(anchor: datetime | None = None) -> str:
    anchor = anchor or utcnow()
    data_dir = ROOT / "data" / "demo"
    out = ROOT / "web" / "public" / "demo"
    shutil.rmtree(data_dir, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    settings = replace(Settings(), data_dir=data_dir, web_data_dir=out, docs_dir=data_dir / "docs")
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    srcs = [
        SourceConfig(
            id=f"demo_{s}",
            adapter="demo",
            name=f"Demo source {s.upper()}",
            data_type=DataType.EVENTS,
            params={"src": s, "anchor": anchor.isoformat()},
        )
        for s in ("a", "b")
    ]
    city = CityConfig(
        slug="demoville",
        name="Demoville",
        state="MN",
        timezone="America/Chicago",
        center=(44.9778, -93.2650),
        neighborhoods=[
            Neighborhood(name="Downtown", lat=44.9765, lon=-93.27),
            Neighborhood(name="Uptown", lat=44.949, lon=-93.298),
        ],
        sources=srcs,
    )
    reg = Registry(
        cities={"demoville": city}, sources_file=SourcesFile(sla_hours=dict.fromkeys(DataType, 24.0), sources=[])
    )
    db = Database(settings.db_path)
    for hours in (48, 24, 0):
        run(
            db,
            reg,
            settings,
            now=anchor - timedelta(hours=hours),
            force=True,
            geocode=False,
            include_demo=True,
            trigger="demo",
        )
    return str(out.relative_to(ROOT))
