"""The adapter contract. One adapter class per *kind* of source; one config entry per source *instance*.

An adapter does exactly two things, kept separate so stored raw payloads can be replayed after a fix:

  fetch(ctx)            → FetchResult   (network; returns raw payloads, never parses into events)
  parse(payload, ctx)   → Iterator[dict]  (pure; no network; yields SourceEvent-shaped dicts)

The pipeline validates every yielded dict against ``gotc.schema.SourceEvent``. Invalid records are
counted and stored as rejects — a high reject rate is how *schema drift* is detected.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from gotc.config import CityConfig, SourceConfig, Unit
from gotc.http.client import PoliteClient, Response
from gotc.settings import Settings
from gotc.taxonomy import Taxonomy, taxonomy


class AdapterConfigError(Exception):
    """The source config is wrong (missing param, bad mapping). Fix the YAML, not the adapter."""


class MissingCredentials(Exception):
    """A required API key is not set. The unit is reported as disabled with a reason, not failed."""


@dataclass
class Payload:
    url: str
    status: int
    content: bytes
    fetched_at: datetime
    content_type: str = "json"  # json | ics | html | xml | yaml
    from_cache: bool = False
    elapsed_ms: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(cls, r: Response, fetched_at: datetime, content_type: str, **meta: Any) -> Payload:
        return cls(r.url, r.status, r.content, fetched_at, content_type, r.from_cache, r.elapsed_ms, meta)

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


@dataclass
class FetchResult:
    payloads: list[Payload]
    complete: bool = True  # a full snapshot: records absent from it can be marked gone
    cursor: str | None = None  # new incremental cursor to persist (None = keep the old one)


@dataclass
class FetchContext:
    unit: Unit
    http: PoliteClient
    now: datetime
    settings: Settings
    cursor: str | None = None

    @property
    def city(self) -> CityConfig:
        return self.unit.city

    @property
    def source(self) -> SourceConfig:
        return self.unit.source

    @property
    def params(self) -> dict[str, Any]:
        return self.unit.source.params

    def secret(self, name: str) -> str:
        value = self.settings.secret(name)
        if not value:
            raise MissingCredentials(f"set {name} in the environment (.env) to enable {self.source.id}")
        return value


@dataclass
class ParseContext:
    unit: Unit
    fetched_at: datetime
    tax: Taxonomy = field(default_factory=taxonomy)

    @property
    def city(self) -> CityConfig:
        return self.unit.city

    @property
    def source(self) -> SourceConfig:
        return self.unit.source

    @property
    def params(self) -> dict[str, Any]:
        return self.unit.source.params

    def base(self, record_id: str, **fields: Any) -> dict[str, Any]:
        """Start a SourceEvent dict with the fields every record shares."""
        return {
            "source_id": self.source.id,
            "record_id": record_id,
            "city": self.city.slug,
            "timezone": self.city.timezone,
            "fetched_at": self.fetched_at,
            **fields,
        }


class Adapter(ABC):
    name: ClassVar[str]
    #: Fetch through robots.txt? True for page scrapes / feeds; documented JSON APIs may set False.
    respect_robots: ClassVar[bool] = True

    @abstractmethod
    def fetch(self, ctx: FetchContext) -> FetchResult: ...

    @abstractmethod
    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]: ...

    def required_params(self) -> tuple[str, ...]:
        return ()

    def check_config(self, source: SourceConfig) -> None:
        missing = [p for p in self.required_params() if p not in source.params]
        if missing:
            raise AdapterConfigError(f"{source.id}: missing params {missing}")


_REGISTRY: dict[str, type[Adapter]] = {}


def register(cls: type[Adapter]) -> type[Adapter]:
    if cls.name in _REGISTRY:
        raise ValueError(f"adapter {cls.name} registered twice")
    _REGISTRY[cls.name] = cls
    return cls


def get_adapter(name: str) -> Adapter:
    import gotc.adapters.all  # noqa: F401  (registers every adapter module)

    try:
        return _REGISTRY[name]()
    except KeyError:
        raise AdapterConfigError(f"unknown adapter {name!r}; known: {sorted(_REGISTRY)}") from None


def adapter_names() -> list[str]:
    import gotc.adapters.all  # noqa: F401

    return sorted(_REGISTRY)


def stable_id(*parts: object) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]
