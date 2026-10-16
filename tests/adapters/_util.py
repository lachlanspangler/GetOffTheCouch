"""Helpers for adapter fixture tests. Tests use the *real* city configs, so a config typo fails a test."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gotc.adapters.base import FetchContext, Payload, get_adapter
from gotc.config import Unit, load_registry
from gotc.http.client import PoliteClient
from gotc.pipeline.ingest import Parsed, parse_payloads
from gotc.schema import SourceEvent
from gotc.settings import Settings
from tests.conftest import NOW, FixtureTransport, fixture_bytes


def unit(source_id: str, **param_overrides: Any) -> Unit:
    u = next(u for u in load_registry().units() if u.source.id == source_id)
    if not param_overrides:
        return u
    src = u.source.model_copy(update={"params": {**u.source.params, **param_overrides}})
    return Unit(source=src, city=u.city)


def payload(rel: str, url: str = "https://example.test/fixture") -> Payload:
    kind = "xml" if rel.endswith(".xml") else "json"
    return Payload(url, 200, fixture_bytes(rel), NOW, kind)


def parse(u: Unit, *rels: str) -> Parsed:
    return parse_payloads(get_adapter(u.source.adapter), u, [(payload(r), None) for r in rels], NOW)


def by_id(parsed: Parsed) -> dict[str, SourceEvent]:
    return {ev.record_id: ev for ev, _ in parsed.valid}


def raw_records(u: Unit, rel: str) -> list[dict[str, Any]]:
    from gotc.adapters.base import ParseContext

    return list(get_adapter(u.source.adapter).parse(payload(rel), ParseContext(u, NOW)))


def client(transport: FixtureTransport, tmp_path: Path) -> PoliteClient:
    return PoliteClient(transport=transport, sleep=lambda s: None, cache_dir=tmp_path / "cache", min_interval_s=0)


def fetch_ctx(u: Unit, http: PoliteClient, settings: Settings) -> FetchContext:
    return FetchContext(unit=u, http=http, now=NOW, settings=settings)


def dump(parsed: Parsed) -> str:
    """Everything a parsed batch would store, as one string (for "this value must never appear" checks)."""
    return "\n".join(ev.model_dump_json() for ev, _ in parsed.valid)
