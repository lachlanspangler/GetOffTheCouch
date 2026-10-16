from datetime import UTC, datetime

from gotc.pipeline.weather import attach, hourly, is_outdoor
from gotc.schema import Event
from gotc.taxonomy import taxonomy
from tests.conftest import FixtureTransport, fast_client, make_city

T = datetime(2026, 10, 17, 14, 30, tzinfo=UTC)
PERIODS = [
    {
        "start": "2026-10-17T09:00:00-05:00",
        "end": "2026-10-17T10:00:00-05:00",
        "temp_f": 41,
        "precip_pct": 10,
        "short": "Sunny",
    }
]


def ev(**kw):
    d = {
        "id": "e",
        "city": "c",
        "title": "Buckthorn Removal",
        "kind": "one_off",
        "category": "volunteer.one_off",
        "start": T,
        "timezone": "America/Chicago",
        "location": {"venue_name": "Minnehaha Park"},
        "price": {},
        "sources": [],
        "first_seen": T,
        "last_checked": T,
    }
    d.update(kw)
    return Event.model_validate(d)


def test_outdoor_detection():
    assert is_outdoor(ev(), taxonomy())  # "Park" in venue
    assert not is_outdoor(ev(title="Book club", category="arts.books", location={"venue_name": "Library"}), taxonomy())
    assert not is_outdoor(ev(tags=["indoor"]), taxonomy())


def test_attach_matches_start_hour_and_skips_all_day():
    a, b = ev(), ev(all_day=True)
    assert attach([a, b], PERIODS, T, taxonomy()) == 1
    assert a.weather and a.weather.short == "Sunny" and a.weather.temp_f == 41 and b.weather is None


def test_hourly_fetches_once_then_uses_cache_and_survives_outage(db):
    t = FixtureTransport()
    t.add(
        r"api\.weather\.gov/points/",
        {"properties": {"forecastHourly": "https://api.weather.gov/gridpoints/MPX/1,1/forecast/hourly"}},
    )
    t.add(
        r"forecast/hourly",
        {
            "properties": {
                "periods": [
                    {
                        "startTime": PERIODS[0]["start"],
                        "endTime": PERIODS[0]["end"],
                        "temperature": 41,
                        "probabilityOfPrecipitation": {"value": 10},
                        "shortForecast": "Sunny",
                    }
                ]
            }
        },
    )
    city = make_city()
    periods, at = hourly(db, fast_client(t), city, T)
    assert periods[0]["short"] == "Sunny" and at == T
    assert len(t.calls) == 2
    hourly(db, fast_client(t), city, T)
    assert len(t.calls) == 2  # cached
    down = FixtureTransport().add(r"api\.weather\.gov", status=500)
    later = datetime(2026, 10, 17, 20, tzinfo=UTC)
    periods2, _ = hourly(db, fast_client(down), city, later)
    assert periods2 == periods  # outage → last good forecast, never a crash
