"""San Jose platform variant against a real recorded page (batch B onboarding, 2026-10-16).

``montalvo_arts``: schema.org ``EventSeries`` nodes inside an ``@graph`` whose ``startDate`` carries local
wall-clock time mislabeled ``+00:00``; ``ignore_offset: true`` re-reads it in the city's zone.
"""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes


def _parse():
    u = unit("montalvo_arts")
    p = Payload(u.source.params["urls"][0], 200, fixture_bytes("montalvo_arts/payload_0.html"), NOW, "html")
    return parse_payloads(get_adapter("jsonld"), u, [(p, None)], NOW)


def test_event_series_graph_parses_without_rejects():
    parsed = _parse()
    assert not parsed.rejects and len(parsed.valid) == 5
    assert {ev.location.venue_name for ev, _ in parsed.valid} == {"Montalvo Arts Center"}


def test_bogus_utc_offset_is_ignored():
    evs = {ev.title: ev for ev, _ in _parse().valid}
    abba = evs["Direct from Sweden: The Music of ABBA"]
    # the page says "2026-10-28T19:30:00+00:00" for a 7:30 PM show; read as Pacific wall-clock time
    assert abba.start.isoformat() == "2026-10-28T19:30:00-07:00"
