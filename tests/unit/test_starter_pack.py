from datetime import UTC, datetime, timedelta

import pytest
import yaml

from gotc.pipeline import starter_pack as sp
from gotc.settings import CONFIG_DIR
from tests.conftest import FixtureTransport, fast_client

NOW = datetime(2026, 10, 16, tzinfo=UTC)
ITEM = {
    "id": "zz-license",
    "title": "Get a license",
    "kind": "license",
    "days_after_move": 60,
    "summary": "Within 60 days.",
    "action_url": "https://dmv.example.gov/",
    "evidence": "must apply within 60 days ... of moving",
    "source_url": "https://dmv.example.gov/new",
    "verified_at": "2026-10-15",
}


def write(tmp_path, state="ZZ", items=(ITEM,)):
    (tmp_path / "starter_pack").mkdir(exist_ok=True)
    (tmp_path / "starter_pack" / f"{state.lower()}.yaml").write_text(
        yaml.safe_dump({"state": state, "items": list(items)})
    )


def test_load_and_verify_present_then_changed(tmp_path, db):
    write(tmp_path)
    items = sp.load("ZZ", tmp_path)
    ok = FixtureTransport().add(r"dmv\.example\.gov/new", "New residents must apply within 60 days of moving here.")
    assert sp.verify(db, fast_client(ok), items, NOW) == 1
    assert sp.with_status(db, items)[0].check_status == "evidence_present"
    assert sp.verify(db, fast_client(ok), items, NOW + timedelta(hours=2)) == 0  # rechecked at most daily
    changed = FixtureTransport().add(r"dmv\.example\.gov/new", "We changed the rules.")
    sp.verify(db, fast_client(changed), items, NOW + timedelta(days=2))
    assert sp.with_status(db, items)[0].check_status == "page_changed"


def test_wrong_state_and_missing_evidence_rejected(tmp_path):
    write(tmp_path, items=({**ITEM, "evidence": ""},))
    with pytest.raises(ValueError):
        sp.load("ZZ", tmp_path)
    (tmp_path / "starter_pack" / "yy.yaml").write_text(yaml.safe_dump({"state": "ZZ", "items": []}))
    with pytest.raises(ValueError, match="state field"):
        sp.load("YY", tmp_path)


@pytest.mark.parametrize("path", sorted((CONFIG_DIR / "starter_pack").glob("*.yaml")), ids=lambda p: p.stem)
def test_real_starter_packs_validate(path):
    assert sp.load(path.stem.upper())
