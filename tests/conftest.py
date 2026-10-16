"""Shared test fixtures. Nothing here touches the network: HTTP goes through ``FixtureTransport``."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from gotc.config import CityConfig, Registry, SourceConfig, SourcesFile, Unit
from gotc.schema import DataType
from gotc.settings import Settings
from gotc.storage.db import Database

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 16, 3, 0, tzinfo=UTC)  # 2026-10-15 22:00 in Minneapolis


def fixture_bytes(rel: str) -> bytes:
    return (FIXTURES / rel).read_bytes()


class FixtureTransport(httpx.BaseTransport):
    """Routes requests to canned responses. Unmatched requests fail loudly (no accidental network)."""

    def __init__(self) -> None:
        self.routes: list[tuple[re.Pattern[str], Callable[[httpx.Request], httpx.Response]]] = []
        self.calls: list[str] = []

    def add(
        self,
        pattern: str,
        body: bytes | str | dict[str, Any] | list[Any] | None = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> FixtureTransport:
        if isinstance(body, dict | list):
            content = json.dumps(body).encode()
        elif isinstance(body, str):
            content = body.encode()
        else:
            content = body or b""
        self.routes.append(
            (re.compile(pattern), lambda req: httpx.Response(status, content=content, headers=headers or {}))
        )
        return self

    def add_fn(self, pattern: str, fn: Callable[[httpx.Request], httpx.Response]) -> FixtureTransport:
        self.routes.append((re.compile(pattern), fn))
        return self

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            for pat, fn in self.routes:
                if pat.search(url):
                    return fn(request)
            return httpx.Response(404)
        for pat, fn in self.routes:
            if pat.search(url):
                return fn(request)
        raise AssertionError(f"unexpected request in test: {url}")


@pytest.fixture
def transport() -> FixtureTransport:
    return FixtureTransport()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "DIARY.md").write_text("# Diary\n")
    return Settings(data_dir=tmp_path / "data", web_data_dir=tmp_path / "web", docs_dir=docs)


@pytest.fixture
def db() -> Iterator[Database]:
    d = Database(":memory:")
    yield d
    d.close()


def make_city(slug: str = "testville", sources: list[SourceConfig] | None = None) -> CityConfig:
    return CityConfig(
        slug=slug,
        name="Minneapolis" if slug == "minneapolis" else "Testville",
        state="MN",
        timezone="America/Chicago",
        center=(44.9778, -93.2650),
        radius_km=20,
        sources=sources or [],
    )


def make_source(
    id: str = "src", adapter: str = "tribe", data_type: DataType = DataType.EVENTS, **params: Any
) -> SourceConfig:
    return SourceConfig(id=id, adapter=adapter, name=id.title(), data_type=data_type, params=params)


def make_registry(*cities: CityConfig, global_sources: list[SourceConfig] | None = None) -> Registry:
    return Registry(
        cities={c.slug: c for c in cities},
        sources_file=SourcesFile(
            sla_hours=dict.fromkeys(DataType, 24.0) | {DataType.TICKET_PRICES: 4.0},
            sources=global_sources or [],
        ),
    )


def unit_for(source: SourceConfig, city: CityConfig) -> Unit:
    return Unit(source=source, city=city)
