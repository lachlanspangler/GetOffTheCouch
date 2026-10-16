from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from gotc.schema import Estimate, Location, Price, SourceEvent

NOW = datetime(2026, 10, 16, tzinfo=UTC)


def base(**kw):
    d = {
        "source_id": "s",
        "record_id": "1",
        "city": "c",
        "title": "Kickball",
        "category": "sports_league.kickball",
        "start": NOW,
        "timezone": "America/Chicago",
        "fetched_at": NOW,
    }
    d.update(kw)
    return d


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValidationError, match="timezone-aware"):
        SourceEvent.model_validate(base(start=datetime(2026, 10, 16, 19, 0)))


def test_end_before_start_rejected():
    with pytest.raises(ValidationError, match="end before start"):
        SourceEvent.model_validate(base(end=datetime(2026, 10, 15, tzinfo=UTC)))


def test_unknown_fields_rejected_at_boundary():
    with pytest.raises(ValidationError):
        SourceEvent.model_validate(base(surprise="field"))


def test_price_free_cannot_have_cost_and_min_max_are_ordered():
    with pytest.raises(ValidationError):
        Price(is_free=True, min=5)
    p = Price(min=50, max=20)
    assert (p.min, p.max) == (20, 50)


def test_estimate_requires_ordered_band():
    with pytest.raises(ValidationError):
        Estimate(low=10, mid=5, high=20, method="x", confidence=0.5)


def test_location_requires_both_coordinates():
    with pytest.raises(ValidationError):
        Location(lat=44.9)
