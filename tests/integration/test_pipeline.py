"""End-to-end: fetch (fixture transport) → raw → parse → records → build → export → health, offline."""

import json
from datetime import timedelta

from gotc.health.store import load_health
from gotc.pipeline.run import run
from gotc.schema import CityFeed
from tests.conftest import NOW, FixtureTransport, fast_client, fixture_bytes, make_city, make_registry, make_source

TRIBE = make_source(
    "mprb_events",
    "tribe",
    base_url="https://www.minneapolisparks.org",
    category_map={"Environmental Volunteer Opportunities": "volunteer.one_off"},
)
ICS = make_source("test_ics", "ics", url="https://cal.example/feed.ics", horizon_days=30)
CITY = make_city("minneapolis", [TRIBE, ICS])
REG = make_registry(CITY)


def mprb() -> dict:
    data = json.loads(fixture_bytes("mprb_events/payload_0.json"))
    data["total_pages"] = 1  # the recording is page 1 of 2, trimmed; serve it as the whole feed
    return data


def healthy_transport() -> FixtureTransport:
    t = FixtureTransport()
    t.add(r"minneapolisparks\.org/wp-json", mprb())
    t.add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    return t


def feed(settings):
    return CityFeed.model_validate_json((settings.web_data_dir / "cities" / "minneapolis.json").read_text())


def test_end_to_end_dedup_export_and_health(db, settings):
    rep = run(db, REG, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    assert rep.status == "ok", rep.summary()
    f = feed(settings)
    # the Rose Garden event appears in both sources → one canonical event with two source refs
    rose = [e for e in f.events if "Rose Garden" in e.title and e.start.day == 17]
    assert len(rose) == 1 and {s.source_id for s in rose[0].sources} == {"mprb_events", "test_ics"}
    assert rose[0].title == "Rose Garden Volunteering"  # most-trusted / first source's title
    # deadline extracted from the ICS description, with evidence + extracted provenance
    assert rose[0].registration and rose[0].registration.closes_at
    from gotc.schema import CityDetails

    det = CityDetails.model_validate_json((settings.web_data_dir / "cities" / "minneapolis.details.json").read_text())
    assert det.events[rose[0].id].provenance["registration"].method == "extracted"
    # weekly trivia expanded into a series, collapsed via series_id
    trivia = [e for e in f.events if e.title == "Tuesday Trivia"]
    assert len(trivia) >= 2 and len({e.series_id for e in trivia}) == 1
    assert "solo_friendly" in trivia[0].tags and trivia[0].price.is_free
    # every event has attendance with a band and method; nothing is demo
    assert all(e.attendance and e.attendance.method for e in f.events)
    assert not any(e.is_demo for e in f.events)
    # ranking hints are precomputed from the full description (before the card feed trims it)
    assert all(e.rank and e.rank.fp for e in f.events)
    assert rose[0].rank and rose[0].rank.desc_len == len(det.events[rose[0].id].summary or "")
    # index + health exports exist and agree
    idx = json.loads((settings.web_data_dir / "index.json").read_text())
    assert idx["cities"][0]["events"] == len(f.events)
    assert load_health(db, "mprb_events@minneapolis").state == "healthy"
    assert (settings.docs_dir / "HEALTH.md").read_text().count("healthy") >= 2


def test_not_due_units_are_skipped_so_reruns_are_cheap_and_resumable(db, settings):
    run(db, REG, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    t = healthy_transport()
    rep = run(db, REG, settings, client=fast_client(t), now=NOW + timedelta(minutes=10), geocode=False)
    assert {u.status for u in rep.units} == {"skipped"}
    assert t.calls == []


def test_broken_source_quarantines_keeps_last_known_good_and_marks_stale(db, settings):
    run(db, REG, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    n_before = len(feed(settings).events)
    broken = FixtureTransport()
    broken.add(r"minneapolisparks\.org/wp-json", status=503)
    broken.add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    t = NOW
    for _ in range(3):
        t += timedelta(hours=9)
        run(db, REG, settings, client=fast_client(broken), now=t, geocode=False, force=True)
    h = load_health(db, "mprb_events@minneapolis")
    assert h.state == "quarantined" and h.last_error_kind == "server_error"
    f = feed(settings)
    mprb_only = [e for e in f.events if {s.source_id for s in e.sources} == {"mprb_events"}]
    assert mprb_only, "last-known-good data must keep serving"
    assert all(e.stale and "freshness SLA" in (e.stale_reason or "") for e in mprb_only)
    assert len(f.events) >= n_before - 2  # nothing deleted because a source broke
    status = next(s for s in f.sources if s.source_id == "mprb_events")
    assert status.state == "quarantined" and status.stale
    assert "Needs attention" in (settings.docs_dir / "HEALTH.md").read_text()
    # recovery: probe succeeds twice → healthy, stale flags clear
    for _ in range(2):
        t += timedelta(days=3)
        run(db, REG, settings, client=fast_client(healthy_transport()), now=t, geocode=False, force=True)
    assert load_health(db, "mprb_events@minneapolis").state == "healthy"


def test_schema_drift_detected_and_valid_records_kept(db, settings):
    run(db, REG, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    data = mprb()
    for e in data["events"][2:]:
        e.pop("title")  # upstream renamed a field
    t = FixtureTransport()
    t.add(r"minneapolisparks\.org/wp-json", data)
    t.add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    rep = run(db, REG, settings, client=fast_client(t), now=NOW + timedelta(hours=25), geocode=False, force=True)
    u = next(x for x in rep.units if x.unit == "mprb_events@minneapolis")
    assert u.error_kind == "schema_drift" and u.rejected == 10 and u.valid == 2
    rows = db.all("SELECT COUNT(*) c FROM rejects WHERE unit = 'mprb_events@minneapolis'")
    assert rows[0]["c"] == 10
    # nothing was marked gone because the snapshot was not trusted
    gone = db.one("SELECT COUNT(*) c FROM source_records WHERE gone_at IS NOT NULL")
    assert gone["c"] == 0


def test_missing_key_reports_disabled_not_failed(db, settings, monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
    tm = make_source("ticketmaster", "ticketmaster")
    tm.requires.append("TICKETMASTER_API_KEY")
    tm.scope = "all_cities"
    reg = make_registry(CITY, global_sources=[tm])
    rep = run(db, reg, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    u = next(x for x in rep.units if x.unit == "ticketmaster@minneapolis")
    assert u.status == "disabled" and "needs TICKETMASTER_API_KEY" in u.notes[0]
    assert rep.status == "ok"
    st = next(s for s in feed(settings).sources if s.source_id == "ticketmaster")
    assert st.state == "disabled" and st.reason == "needs TICKETMASTER_API_KEY"


def test_records_removed_upstream_are_marked_gone(db, settings):
    run(db, REG, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    data = mprb()
    removed = data["events"].pop(5)
    t = FixtureTransport()
    t.add(r"minneapolisparks\.org/wp-json", data)
    t.add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    run(db, REG, settings, client=fast_client(t), now=NOW + timedelta(hours=25), geocode=False, force=True)
    row = db.one("SELECT gone_at FROM source_records WHERE record_id = ?", (str(removed["id"]),))
    assert row["gone_at"] is not None
    assert not any(str(removed["id"]) in [s.record_id for s in e.sources] for e in feed(settings).events)


def test_canonical_ids_are_stable_across_runs(db, settings):
    run(db, REG, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    ids1 = {e.id for e in feed(settings).events}
    run(
        db,
        REG,
        settings,
        client=fast_client(healthy_transport()),
        now=NOW + timedelta(hours=25),
        geocode=False,
        force=True,
    )
    ids2 = {e.id for e in feed(settings).events}
    assert ids1 == ids2


def test_new_badge_only_for_records_after_initial_backfill(db, settings):
    data = mprb()
    held_back = data["events"].pop(4)
    first = FixtureTransport()
    first.add(r"minneapolisparks\.org/wp-json", data)
    first.add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    run(db, REG, settings, client=fast_client(first), now=NOW, geocode=False)
    assert not any(e.is_new for e in feed(settings).events), "initial backfill is not 'new'"
    data["events"].append(held_back)
    later = FixtureTransport()
    later.add(r"minneapolisparks\.org/wp-json", data)
    later.add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    run(db, REG, settings, client=fast_client(later), now=NOW + timedelta(hours=25), geocode=False, force=True)
    new = [e for e in feed(settings).events if e.is_new]
    assert [s.record_id for e in new for s in e.sources] == [str(held_back["id"])]


def test_recent_openings_stay_visible_old_ones_drop(db, settings):
    from gotc.pipeline.build import load_live_records
    from gotc.pipeline.ingest import Parsed, upsert_records
    from gotc.schema import SourceEvent
    from tests.conftest import unit_for

    unit = unit_for(TRIBE, CITY)

    def opening(rid, days_ago):
        return SourceEvent(
            source_id="mprb_events",
            record_id=rid,
            city="minneapolis",
            title=f"New Bar {rid}",
            category="nightlife.opening",
            kind="opening",
            all_day=True,
            timezone="America/Chicago",
            start=NOW - timedelta(days=days_ago),
            fetched_at=NOW,
        )

    with db.tx():
        upsert_records(db, unit, Parsed(valid=[(opening("fresh", 10), None), (opening("old", 90), None)]), NOW)
    ids = {e.record_id for e in load_live_records(db, "minneapolis", NOW)}
    assert "fresh" in ids and "old" not in ids


def test_a_crashing_city_build_does_not_blank_other_cities(db, settings, monkeypatch):
    import gotc.pipeline.run as runmod

    other = make_city("testville", [make_source("test_ics2", "ics", url="https://cal.example/feed.ics")])
    reg = make_registry(CITY, other)
    real = runmod.build_city

    def flaky(db_, reg_, city, *a, **k):
        if city.slug == "minneapolis":
            raise RuntimeError("boom")
        return real(db_, reg_, city, *a, **k)

    monkeypatch.setattr(runmod, "build_city", flaky)
    rep = run(db, reg, settings, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    assert rep.status == "partial" and rep.build_errors and "boom" in rep.build_errors[0]
    assert (settings.web_data_dir / "cities" / "testville.json").exists()
    assert db.one("SELECT kind FROM health_log WHERE unit = 'build@minneapolis'")["kind"] == "build_error"


def test_openings_by_first_seen_baseline_is_silent_new_licenses_show(db, settings):
    from gotc.pipeline.build import load_live_records
    from gotc.pipeline.ingest import Parsed, upsert_records
    from gotc.schema import SourceEvent
    from tests.conftest import unit_for

    lic = make_source("mpls_liq", "arcgis", service_url="https://x", openings_by_first_seen=True, kind="opening")
    city = make_city("minneapolis", [lic])
    reg = make_registry(city)
    unit = unit_for(lic, city)

    def rec(rid):  # issueDate is a renewal date in this dataset — deliberately old
        return SourceEvent(
            source_id="mpls_liq",
            record_id=rid,
            city="minneapolis",
            title=f"Bar {rid} — new liquor license",
            category="nightlife.opening",
            kind="opening",
            all_day=True,
            timezone="America/Chicago",
            start=NOW - timedelta(days=900),
            fetched_at=NOW,
        )

    with db.tx():
        upsert_records(db, unit, Parsed(valid=[(rec("old1"), None), (rec("old2"), None)]), NOW)
    assert load_live_records(db, "minneapolis", NOW, reg) == []  # baseline: existing businesses aren't news
    later = NOW + timedelta(days=2)
    with db.tx():
        upsert_records(db, unit, Parsed(valid=[(rec("old1"), None), (rec("old2"), None), (rec("fresh"), None)]), later)
    got = load_live_records(db, "minneapolis", later, reg)
    assert [e.record_id for e in got] == ["fresh"]
    assert got[0].start.date() == later.astimezone(got[0].start.tzinfo).date() and got[0].all_day
    assert "First appeared in the city's license data" in (got[0].description or "")


def test_institution_fallback_point_is_labeled_approximate(db, settings):
    ics = make_source(
        "campus_ics",
        "ics",
        url="https://cal.example/feed.ics",
        horizon_days=30,
        fallback_point={"lat": 44.974, "lon": -93.2277, "label": "University of Minnesota East Bank"},
    )
    reg = make_registry(make_city("minneapolis", [ics]))
    t = FixtureTransport().add(r"cal\.example/feed\.ics", fixture_bytes("synthetic/dup_calendar.ics"))
    run(db, reg, settings, client=fast_client(t), now=NOW, geocode=False)
    ev = next(e for e in feed(settings).events if e.title == "Tuesday Trivia")
    assert ev.location.lat == 44.974 and ev.location.geocode_confidence == 0.3
    assert "approximate: University of Minnesota East Bank" in (ev.location.address or "")
