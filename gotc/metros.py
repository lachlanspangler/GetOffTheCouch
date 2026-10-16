"""The metro reference table (config/metros.yaml): top-50 US metros from SCALING.md §1, Census CBSA estimates."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gotc.config import load_yaml
from gotc.http.client import FetchError, PoliteClient
from gotc.settings import CONFIG_DIR


class Metro(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rank: int
    cbsa: str = Field(pattern=r"^\d{5}$")
    msa: str
    msa_pop_m: float
    name: str
    state: str = Field(pattern=r"^[A-Z]{2}$")
    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    timezone: str
    center: tuple[float, float]
    center_source: Literal["census_geocoder", "scaling_md"]
    center_address: str | None = None
    center_matched: str | None = None
    radius_km: float
    incumbent: bool = False


def load_metros(path: Path = CONFIG_DIR / "metros.yaml") -> dict[str, Metro]:
    data = load_yaml(path.read_text()) or {}
    out = {m.slug: m for m in (Metro.model_validate(x) for x in data.get("metros", []))}
    if len(out) != len(data.get("metros", [])):
        raise ValueError("config/metros.yaml: duplicate slug")
    return out


@cache
def metros() -> dict[str, Metro]:
    return load_metros()


CENSUS_ONELINE = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
MAX_SHIFT_KM = 5.0  # a re-derived center further than this from the table value is rejected (wrong address)


def census_center(http: PoliteClient, address: str) -> tuple[float, float, str] | None:
    """One Census onelineaddress lookup → (lat, lon, matchedAddress), or None if no match."""
    data = http.get_json(
        CENSUS_ONELINE, params={"address": address, "benchmark": "Public_AR_Current", "format": "json"}
    )
    matches = (data.get("result") or {}).get("addressMatches") or []
    if not matches:
        return None
    c = matches[0].get("coordinates") or {}
    return round(float(c["y"]), 4), round(float(c["x"]), 4), str(matches[0].get("matchedAddress", ""))


def recenter(path: Path, http: PoliteClient, only: str | None = None) -> list[str]:
    """Re-derive centers from ``center_address`` with the Census geocoder; rewrite metros.yaml in place
    (line-based, so comments survive). Returns one log line per metro."""
    from gotc.pipeline.textnorm import haversine_m

    rows = load_metros(path)
    lines = path.read_text().splitlines()
    report: list[str] = []
    for m in rows.values():
        if (only and m.slug != only) or not m.center_address:
            continue
        try:
            hit = census_center(http, m.center_address)
        except (FetchError, ValueError, KeyError) as e:
            report.append(f"{m.slug}: census lookup failed ({e}); kept {m.center_source}")
            continue
        if hit is None:
            report.append(f"{m.slug}: no Census match for {m.center_address!r}; kept {m.center_source}")
            continue
        lat, lon, matched = hit
        if not same_street(m.center_address, matched):
            report.append(f"{m.slug}: Census matched a different street ({matched!r}); kept {m.center_source}")
            continue
        shift = haversine_m(lat, lon, *m.center) / 1000
        if shift > MAX_SHIFT_KM:
            report.append(f"{m.slug}: Census match {matched!r} is {shift:.1f} km from the table center; kept")
            continue
        _set_block(lines, m.slug, lat, lon, matched)
        report.append(f"{m.slug}: {m.center} → ({lat}, {lon}) [{matched}] shift {shift:.2f} km")
    path.write_text("\n".join(lines) + "\n")
    return report


_DIRS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}


def same_street(asked: str, matched: str) -> bool:
    """House number and directional prefix must agree ("260 Broadway" is not "260 E BROADWAY")."""
    a = asked.upper().replace(".", "").split(",")[0].split()
    b = matched.upper().replace(".", "").split(",")[0].split()
    if not a or not b or a[0] != b[0]:
        return False
    da = a[1] if len(a) > 1 and a[1] in _DIRS else None
    db = b[1] if len(b) > 1 and b[1] in _DIRS else None
    return da == db


def _set_block(lines: list[str], slug: str, lat: float, lon: float, matched: str) -> None:
    start = lines.index(f"    slug: {slug}")
    i = start
    while i < len(lines) and not lines[i].startswith("  - rank:"):
        if lines[i].startswith("    center: "):
            lines[i] = f"    center: [{lat}, {lon}]"
        elif lines[i].startswith("    center_source: "):
            lines[i] = "    center_source: census_geocoder"
        elif lines[i].startswith("    center_matched: "):
            lines[i] = f'    center_matched: "{matched}"'
            matched = ""
        i += 1
    if matched:
        at = next(j for j in range(start, i) if lines[j].startswith("    center_address: "))
        lines.insert(at + 1, f'    center_matched: "{matched}"')
