"""Richmond (batch A): Springshare LibCal ``ical_subscribe.php`` export (Richmond Public Library) via ``ics``.

LibCal is a new platform variant for us: UTC DTSTART/DTEND, ``CATEGORIES`` as a comma list ("Art, Performances"),
``LOCATION`` = "<room> - <branch>". Real recorded feed, trimmed to 6 VEVENTs.
"""

from datetime import UTC

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

RPL = unit("rpl_events")


def _parse():
    p = Payload(str(RPL.source.params["url"]), 200, fixture_bytes("rpl_events/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), RPL, [(p, None)], NOW)


def test_libcal_ics_parses_all_items():
    parsed = _parse()
    assert not parsed.rejects
    assert len(parsed.valid) == 6


def test_categories_map_and_utc_times():
    evs = {ev.title: ev for ev, _ in _parse().valid}
    concert = evs["Fall Concert Series: Chamber Music Society of Central Virginia"]
    assert concert.category == "music.concert"  # "Art, Performances": the unmapped "Art" is skipped, Performances wins
    assert concert.start.astimezone(UTC).isoformat() == "2026-10-17T18:00:00+00:00"  # DTSTART:20261017T180000Z
    workshop = evs["An Homage to Home: A Workshop and Reading"]
    assert workshop.category == "arts.workshop"
