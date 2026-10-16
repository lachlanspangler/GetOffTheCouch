"""Portland openings: OLCC liquor license applications received (data.oregon.gov Socrata, no record id column)."""

from tests.adapters._util import parse, unit

U = unit("olcc_new_applications_portland")


def test_new_applications_become_openings():
    parsed = parse(U, "olcc_new_applications_portland/payload_0.json")
    assert len(parsed.valid) == 6 and not parsed.rejects
    titles = {ev.title: ev for ev, _ in parsed.valid}
    taq = titles["Taqueria El Paisano Restaurant and Bar LLC — new liquor license application"]
    assert taq.kind == "opening"
    assert taq.category == "nightlife.opening"  # "Bar" in the trade name
    assert taq.start.date().isoformat() == "2026-10-02"
    assert "82ND AVE PORTLAND OR" in (taq.location.address or "")
    assert "Limited On-Premises Sales" in (taq.description or "")


def test_record_ids_are_stable_without_an_id_column():
    a = {ev.record_id for ev, _ in parse(U, "olcc_new_applications_portland/payload_0.json").valid}
    b = {ev.record_id for ev, _ in parse(U, "olcc_new_applications_portland/payload_0.json").valid}
    assert a == b and len(a) == 6
