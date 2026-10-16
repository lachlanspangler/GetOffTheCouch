"""The metro reference table (config/metros.yaml): top-50 US metros from SCALING.md §1, Census CBSA estimates."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from gotc.config import load_yaml
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
