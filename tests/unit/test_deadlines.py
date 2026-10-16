from datetime import UTC, datetime

import pytest

from gotc.pipeline.deadlines import extract_deadlines

NOW = datetime(2026, 10, 16, 3, tzinfo=UTC)
TZ = "America/Chicago"
START = datetime(2027, 1, 10, 18, tzinfo=UTC)


@pytest.mark.parametrize(
    ("text", "field", "expect"),
    [
        ("Register by November 3 to secure your spot.", "closes_at", (2026, 11, 3, 23, 59)),
        ("Registration closes Dec 1, 2026 at 11:59 pm", "closes_at", (2026, 12, 1, 23, 59)),
        ("Deadline: 12/15", "closes_at", (2026, 12, 15, 23, 59)),
        ("Early-bird pricing ends Nov. 1st", "early_bird_ends_at", (2026, 11, 1, 23, 59)),
        ("Registration opens Monday, October 20 at 9am", "opens_at", (2026, 10, 20, 9, 0)),
        ("Sign-ups due by Jan 5", "closes_at", (2027, 1, 5, 23, 59)),
    ],
)
def test_extracts(text, field, expect):
    found = {d.field: d for d in extract_deadlines(text, TZ, NOW, START)}
    assert field in found, found
    at = found[field].at
    assert (at.year, at.month, at.day, at.hour, at.minute) == expect
    assert found[field].evidence and at.tzinfo is not None


def test_ignores_deadline_after_event_start():
    assert extract_deadlines("Register by March 3", TZ, NOW, START) == []


def test_ignores_long_past_dates_and_plain_text():
    assert extract_deadlines("Registration closed on Sep 1, 2026", TZ, NOW, START) == []
    assert extract_deadlines("Join us for a fun night!", TZ, NOW, START) == []


def test_keeps_earliest_when_multiple():
    text = "Register by Dec 10. Final deadline: Dec 20"
    d = {x.field: x for x in extract_deadlines(text, TZ, NOW, START)}
    assert d["closes_at"].at.day == 10
