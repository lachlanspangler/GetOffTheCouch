"""ADR-0010: mixed calendars (universities, libraries, cities, parks, museums…) may not guess a catch-all category."""

from __future__ import annotations

from gotc.config import load_registry
from gotc.pipeline.category_basis import default_violations, looks_mixed
from tests.conftest import make_source


def test_no_mixed_calendar_in_the_real_config_has_a_catch_all_default():
    sources = list(load_registry().all_sources().values())
    assert default_violations(sources) == []


def test_every_kept_default_on_a_mixed_looking_source_says_why():
    for s in load_registry().all_sources().values():
        if s.params.get("default_category") and looks_mixed(s.id, s.name, s.adapter, s.params):
            assert len(str(s.params.get("single_kind_reason") or "")) >= 15, s.id


def test_the_check_catches_the_fiu_config():
    fiu = make_source(
        "fiu_events", adapter="localist", audience_filter="institution", default_category="learning.networking"
    )
    library = make_source("mdpls_events", adapter="communico", default_category="arts.books")
    comedy = make_source("cap_city_comedy", adapter="jsonld", default_category="nightlife.comedy")
    assert {v.split(":")[0] for v in default_violations([fiu, library, comedy])} == {"fiu_events", "mdpls_events"}
    ok = make_source("fiu_events", adapter="localist", default_category="x.y", single_kind_reason="only concerts")
    assert default_violations([ok]) == []
