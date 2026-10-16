"""Birmingham, AL platform variants (real recorded pages in tests/fixtures/<source_id>/, no network).

* bham_bjcc_concerts — WordPress Modern Events Calendar JSON-LD whose clock times are wrong ("14:00-05:00" for a
  7 pm show) and whose offers are placeholders (price 0, validFrom = event date): `date_only` keeps dates only and
  no price/on-sale is reported.
* bham_saturn — Opendate show pages: MusicEvent JSON-LD with a UTC start.
"""

from __future__ import annotations

import json

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import Parsed, parse_payloads
from tests.adapters._util import unit as real_unit
from tests.conftest import FIXTURES, NOW


def _real(source_id: str) -> Parsed:
    u = real_unit(source_id)
    meta = json.loads((FIXTURES / source_id / "meta.json").read_text())
    payloads = [
        (Payload(url, 200, (FIXTURES / source_id / name).read_bytes(), NOW, "html"), None)
        for name, url in meta["files"].items()
    ]
    return parse_payloads(get_adapter("jsonld"), u, payloads, NOW)


def test_bjcc_mec_dates_only_and_no_placeholder_prices():
    parsed = _real("bham_bjcc_concerts")
    assert parsed.valid and not parsed.rejects
    for ev, _ in parsed.valid:
        assert ev.all_day, ev.title  # the JSON-LD clock time is not trusted
        assert ev.category == "music.concert"
        assert not ev.price.is_free and ev.price.min is None  # "price": "0" is a placeholder, not free
        assert ev.location.venue_name


def test_saturn_opendate_utc_start():
    parsed = _real("bham_saturn")
    assert len(parsed.valid) == 2 and not parsed.rejects
    for ev, _ in parsed.valid:
        assert ev.start.tzinfo is not None and not ev.all_day
        assert ev.start.utcoffset() is not None
        assert ev.url and "saturnbirmingham.com/shows/" in str(ev.url)
