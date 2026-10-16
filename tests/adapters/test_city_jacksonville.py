"""Jacksonville (batch D): Comedy Zone's homepage JSON-LD nests every show under a non-standard ``Place.Events``
key (not @graph/itemListElement/subEvent). Real recorded fixture: tests/fixtures/comedy_zone_jax/."""

from __future__ import annotations

import json

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import FIXTURES, NOW


def test_comedy_zone_place_events_list():
    u = unit("comedy_zone_jax")
    meta = json.loads((FIXTURES / "comedy_zone_jax" / "meta.json").read_text())
    payloads = [
        (Payload(url, 200, (FIXTURES / "comedy_zone_jax" / name).read_bytes(), NOW, "html"), None)
        for name, url in meta["files"].items()
    ]
    parsed = parse_payloads(get_adapter("jsonld"), u, payloads, NOW)
    assert len(parsed.valid) == 5 and not parsed.rejects
    for ev, _ in parsed.valid:
        assert ev.category == "nightlife.comedy"
        assert ev.location.venue_name == "Comedy Zone Jacksonville"
        assert ev.url and str(ev.url).startswith("https://www.comedyzone.com/shows/")
    first = min((ev for ev, _ in parsed.valid), key=lambda e: e.start)
    assert first.title == "Ryan Davis"
    assert first.start.isoformat() == "2026-10-16T23:15:00+00:00"  # UTC in the feed (7:15 pm EDT)
