"""Keys-ready: each keyed source works end to end the moment its key exists, and says "needs KEY" (disabled, not
broken) until then. Uses the real config/sources.yaml entries and documented-shape fixtures; never the internet."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from gotc.config import Unit, load_registry
from gotc.health import store as hstore
from gotc.pipeline.ingest import run_unit
from gotc.settings import Settings
from gotc.storage.db import Database
from tests.conftest import FixtureTransport, fast_client, fixture_bytes

NOW = datetime(2026, 10, 16, 15, tzinfo=UTC)
EMPTY = {
    "ticketmaster": b'{"page": {"size": 200, "totalElements": 0, "totalPages": 0, "number": 0}}',
    "seatgeek": b'{"events": [], "meta": {"total": 0, "per_page": 100, "page": 1}}',
    "runsignup": b'{"races": []}',
    "eventbrite": b'{"events": [], "pagination": {"has_more_items": false}}',
}

CASES = {
    "ticketmaster": (
        ["TICKETMASTER_API_KEY"],
        r"app\.ticketmaster\.com",
        "synthetic/ticketmaster_events.json",
        "apikey",
    ),
    "seatgeek": (["SEATGEEK_CLIENT_ID"], r"api\.seatgeek\.com", "synthetic/seatgeek_events.json", "client_id"),
    "runsignup": (
        ["RUNSIGNUP_API_REG", "RUNSIGNUP_API_REG_SECRET"],
        r"runsignup\.com/Rest",
        "runsignup/payload_0.json",
        "rsu_api_reg",
    ),
    # Eventbrite sends its token as a Bearer header, so the check is on the header, not the URL
    "eventbrite": (
        ["EVENTBRITE_TOKEN"],
        r"eventbriteapi\.com/v3/organizers",
        "synthetic/eventbrite_events.json",
        "Bearer",
    ),
}


def unit(source_id: str) -> Unit:
    reg = load_registry()
    src = reg.all_sources()[source_id]
    if source_id == "eventbrite":  # organizer-scoped: follow one (synthetic) organizer in the test city
        src = src.model_copy(update={"params": {**src.params, "organizers": {"minneapolis": ["99999999999"]}}})
    return Unit(source=src, city=reg.cities["minneapolis"])


@pytest.mark.parametrize("source_id", sorted(CASES))
def test_without_a_key_the_unit_is_disabled_and_says_which_key(
    source_id: str, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys, *_ = CASES[source_id]
    for k in keys:
        monkeypatch.delenv(k, raising=False)
        monkeypatch.setattr(Settings, "secret", staticmethod(lambda name: None))
    db = Database(":memory:")
    u = unit(source_id)
    r = run_unit(db, load_registry(), u, fast_client(FixtureTransport()), settings, NOW)
    assert r.status == "disabled"
    h = hstore.load_health(db, u.key)
    assert h.state == "disabled" and h.reason and all(k in h.reason for k in keys)
    assert h.consecutive_failures == 0  # not "broken": no failure counted, nothing quarantined


@pytest.mark.parametrize("source_id", sorted(CASES))
def test_with_a_key_the_unit_fetches_parses_and_is_healthy(
    source_id: str, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys, host, fixture, param = CASES[source_id]
    secrets = {k: f"test-{k.lower()}" for k in keys}
    monkeypatch.setattr(Settings, "secret", staticmethod(lambda name: secrets.get(name)))
    for k, v in secrets.items():
        monkeypatch.setenv(k, v)
    seen: list[httpx.Request] = []
    body = fixture_bytes(fixture)

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        # the documented-shape fixture once; later windows/pages come back empty, as a quiet week would
        content = body if len(seen) == 1 else EMPTY[source_id]
        return httpx.Response(200, content=content, headers={"content-type": "application/json"})

    t = FixtureTransport().add(r"robots\.txt", "User-agent: *\nAllow: /\n").add_fn(host, handler)
    db = Database(":memory:")
    u = unit(source_id)
    r = run_unit(db, load_registry(), u, fast_client(t), settings, NOW, force=True)
    assert seen, "the adapter never called its API"
    assert any(param in str(q.url) or param in q.headers.get("authorization", "") for q in seen), (
        f"the {param} credential wasn't sent"
    )
    assert r.status == "ok" and r.valid > 0, (r.status, r.error)
    assert hstore.load_health(db, u.key).state in ("healthy", "recovering")
    stored = [row["url"] for row in db.all("SELECT url FROM raw_fetches")]
    assert stored and not any(v in u_ for u_ in stored for v in secrets.values()), "a secret leaked into stored URLs"
