"""City and source configuration (config/cities/*.yaml, config/sources.yaml), validated with pydantic.

Adding a city = adding ``config/cities/<slug>.yaml``. Global sources (``scope: all_cities``) run for every
city automatically using the city's center/radius; city-specific sources are listed in the city file.

A *unit* is one (source, city) pair — the scheduler's atom of work, the health system's atom of state.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from gotc.schema import DataType
from gotc.settings import CONFIG_DIR, Settings


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys (plain YAML silently keeps the last one — a real bug we hit)."""


def _no_dupes(loader: _StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def load_yaml(text: str) -> Any:
    return yaml.load(text, Loader=_StrictLoader)


class _Cfg(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceConfig(_Cfg):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    adapter: str
    name: str
    data_type: DataType
    scope: Literal["city", "all_cities"] = "city"
    cadence_hours: float | None = None  # default: the data type's SLA
    sla_hours: float | None = None  # override the data type's freshness SLA (e.g. curated: weekly)
    requires: list[str] = Field(default_factory=list)  # env vars (API keys) needed
    enabled: bool = True
    homepage: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    min_interval_s: float | None = None  # politeness: seconds between requests to this source's host(s)
    expect_min_records: int = 1  # fewer than this on a successful fetch → "empty results" health failure
    notes: str | None = None


class Neighborhood(_Cfg):
    name: str
    lat: float
    lon: float


class CityConfig(_Cfg):
    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    state: str = Field(pattern=r"^[A-Z]{2}$")
    timezone: str
    center: tuple[float, float]
    radius_km: float = 25.0
    aliases: list[str] = Field(default_factory=list)
    neighborhoods: list[Neighborhood] = Field(default_factory=list)
    sources: list[SourceConfig] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        from zoneinfo import ZoneInfo

        ZoneInfo(v)
        return v


class SourcesFile(_Cfg):
    sla_hours: dict[DataType, float]
    sources: list[SourceConfig]


class Unit(BaseModel):
    """One (source, city) pair."""

    model_config = ConfigDict(frozen=True)
    source: SourceConfig
    city: CityConfig

    @property
    def key(self) -> str:
        return f"{self.source.id}@{self.city.slug}"


class Registry(BaseModel):
    cities: dict[str, CityConfig]
    sources_file: SourcesFile

    def sla_hours(self, source: SourceConfig) -> float:
        return source.sla_hours or self.sources_file.sla_hours[source.data_type]

    def cadence_hours(self, source: SourceConfig) -> float:
        return source.cadence_hours or self.sla_hours(source)

    def units(self, city: str | None = None, source: str | None = None) -> list[Unit]:
        out: list[Unit] = []
        for c in self.cities.values():
            if not c.enabled or (city and c.slug != city):
                continue
            for s in [*self.sources_file.sources, *c.sources]:
                if s.scope == "all_cities" or s in c.sources:
                    if source and s.id != source:
                        continue
                    out.append(Unit(source=s, city=c))
        return out

    def all_sources(self) -> dict[str, SourceConfig]:
        found: dict[str, SourceConfig] = {s.id: s for s in self.sources_file.sources}
        for c in self.cities.values():
            for s in c.sources:
                if s.id in found and found[s.id] != s:
                    raise ValueError(f"source id {s.id} defined twice with different config")
                found[s.id] = s
        return found

    @staticmethod
    def missing_requirements(source: SourceConfig) -> list[str]:
        return [r for r in source.requires if not Settings.secret(r)]


def load_registry(config_dir: Path = CONFIG_DIR) -> Registry:
    sources_file = SourcesFile.model_validate(load_yaml((config_dir / "sources.yaml").read_text()))
    cities: dict[str, CityConfig] = {}
    for path in sorted((config_dir / "cities").glob("*.yaml")):
        city = CityConfig.model_validate(load_yaml(path.read_text()))
        if city.slug != path.stem:
            raise ValueError(f"{path.name}: slug {city.slug!r} must match file name")
        cities[city.slug] = city
    reg = Registry(cities=cities, sources_file=sources_file)
    reg.all_sources()  # validates id uniqueness
    return reg


@cache
def registry() -> Registry:
    return load_registry()
