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


def test_venue_part_last_makes_the_branch_the_venue():
    # LOCATION "Gellman Room - Main Library" + venue_part: last / venue_sep " - " → the branch is the venue, so one
    # curated entry (config/venues/richmond.yaml) places every room; the room string stays in the address
    locs = {(ev.location.venue_name, ev.location.address) for ev, _ in _parse().valid}
    assert ("Main Library", "Gellman Room - Main Library") in locs
    assert ("Main", "Main") in locs  # no separator: the whole LOCATION


def test_venue_part_defaults_to_the_first_comma_part():
    from gotc.adapters.ics import _venue_name

    assert _venue_name("Harmon Library, 1325 S 5th Ave", {}) == "Harmon Library"
    assert _venue_name("Meeting Room, Mesquite Library", {"venue_part": "last"}) == "Mesquite Library"
