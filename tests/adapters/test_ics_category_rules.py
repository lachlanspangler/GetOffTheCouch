"""ics ``category_rules``: title regex → category, before the keyword classifier (Corona library's real config)."""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:a1
SUMMARY:Math Tutor
DESCRIPTION:Volunteer tutors help students with math homework.
DTSTART:20261020T230000Z
DTEND:20261021T000000Z
LOCATION:Study Room
END:VEVENT
BEGIN:VEVENT
UID:a2
SUMMARY:Volunteer Orientation
DESCRIPTION:Learn how to volunteer at the library.
DTSTART:20261022T230000Z
END:VEVENT
END:VCALENDAR
"""


def test_title_rule_beats_keyword_classifier_and_leaves_other_titles_alone():
    u = unit("corona_library_events")
    p = Payload(u.source.params["url"], 200, ICS, NOW, "ics")
    parsed = parse_payloads(get_adapter("ics"), u, [(p, None)], NOW)
    assert not parsed.rejects
    cats = {ev.title: ev.category for ev, _ in parsed.valid}
    assert cats["Math Tutor"] == "family.kids"  # without the rule: volunteer.recurring ("tutor" keyword)
    assert cats["Volunteer Orientation"].startswith("volunteer")
