"""Simpleview CVB adapter against a real recorded Meet Boston response (the live source is disabled: WAF 403)."""

import json

import httpx
import pytest

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import by_id, client, fetch_ctx, parse, unit
from tests.conftest import NOW, FixtureTransport

MB = unit("meet_boston_events")
FX = "meet_boston_events/payload_0.json"


def test_real_fixture_parses_without_rejects():
    parsed = parse(MB, FX)
    assert len(parsed.valid) == 5 and not parsed.rejects


def test_occurrence_date_is_local_and_times_are_wall_clock():
    evs = by_id(parse(MB, FX))
    okt = evs["93621"]
    # date "2026-10-17T03:59:59Z" is the *end of Oct 16* in Boston; startTime 12:00 is Boston wall-clock
    assert okt.start.isoformat() == "2026-10-16T12:00:00-04:00"
    assert okt.end is not None and okt.end.isoformat() == "2026-10-16T19:00:00-04:00"
    assert okt.kind == "recurring" and okt.recurrence == "Through Oct 18"
    assert okt.category == "food_drink.tasting"  # "Craft Beer" beats the generic festival label
    assert okt.location.venue_name == "Dockside Beer Garden"
    assert okt.url is not None and str(okt.url) == "https://www.meetboston.com/event/oktoberfest/93621/"
    hocr = evs["92867"]
    assert hocr.all_day and hocr.start.isoformat() == "2026-10-16T00:00:00-04:00"
    assert hocr.price.is_free  # the board files it under "Free"
    patch = evs["93400"]
    assert patch.price.min == 14 and patch.price.note == "Starting at $14"
    assert evs["93561"].kind == "one_off"


def test_daily_long_runs_are_skipped_and_broken_docs_rejected():
    docs = {
        "docs": {
            "count": 3,
            "docs": [
                {
                    "recid": "1",
                    "title": "Hall of Fame",
                    "date": "2026-10-17T03:59:59.000Z",
                    "startDate": "2025-11-22T05:00:00.000Z",
                    "recurType": 1,
                },
                {
                    "recid": "2",
                    "title": "Trivia Night",
                    "date": "2026-10-21T03:59:59.000Z",
                    "startDate": "2026-01-06T05:00:00.000Z",
                    "recurType": 3,
                    "startTime": "19:00:00",
                    "admission": "Free",
                },
                {"recid": "3", "title": "", "date": None},
            ],
        }
    }
    parsed = parse_payloads(
        get_adapter("simpleview"), MB, [(Payload("u", 200, json.dumps(docs).encode(), NOW), None)], NOW
    )
    evs = by_id(parsed)
    assert "1" not in evs  # a daily attraction since 2025 is not an event
    assert evs["2"].start.isoformat() == "2026-10-20T19:00:00-04:00" and evs["2"].category == "trivia_games.trivia"
    assert len(parsed.rejects) == 1


def test_fetch_gets_token_then_queries_local_window(tmp_path, settings):
    queries = []

    def find(req):
        queries.append(json.loads(req.url.params["json"]))
        assert req.url.params["token"] == "0123456789abcdef0123456789abcdef"
        return httpx.Response(200, json={"docs": {"count": 1, "docs": [{"recid": "x"}]}})

    t = FixtureTransport()
    t.add(r"/plugins/core/get_simple_token/", "0123456789abcdef0123456789abcdef")
    t.add_fn(r"/includes/rest_v2/plugins_events_events_by_date/find/", find)
    fr = get_adapter("simpleview").fetch(fetch_ctx(MB, client(t, tmp_path), settings))
    assert len(fr.payloads) == 1
    rng = queries[0]["filter"]["date_range"]
    assert rng["start"]["$date"] == "2026-10-15T04:00:00.000Z"  # local midnight Oct 15 (EDT) in UTC
    assert rng["end"]["$date"] == "2026-10-22T04:00:00.000Z"


def test_fetch_refuses_a_non_token(tmp_path, settings):
    t = FixtureTransport().add(r"get_simple_token", "<html>blocked</html>")
    with pytest.raises(ValueError, match="token"):
        get_adapter("simpleview").fetch(fetch_ctx(MB, client(t, tmp_path), settings))
