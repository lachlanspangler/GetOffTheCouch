import json
from datetime import timedelta

from gotc.pipeline import payload
from gotc.pipeline.payload import check_all, check_city
from tests.conftest import NOW


def _write(tmp_path, n_now: int, n_later: int, pad: int = 1500):
    events = [
        {"id": f"n{i}", "start": (NOW + timedelta(days=1)).isoformat(), "title": "x" * pad} for i in range(n_now)
    ] + [{"id": f"l{i}", "start": (NOW + timedelta(days=60)).isoformat(), "title": "y" * pad} for i in range(n_later)]
    d = tmp_path / "cities"
    d.mkdir(exist_ok=True)
    (d / "testville.json").write_text(json.dumps({"generated_at": NOW.isoformat(), "events": events}))
    (d / "testville.details.json").write_text("{}")
    return d / "testville.json"


def test_small_city_is_within_budget(tmp_path):
    rep = check_city(_write(tmp_path, 100, 100), NOW)
    assert not rep.warnings and not rep.failures
    assert 0 < rep.now_raw < rep.cards_raw


def test_only_the_next_14_days_count_toward_the_now_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "NOW_RAW_WARN", 200_000)
    rep = check_city(_write(tmp_path, 50, 2000), NOW)
    assert not any("next-14-days" in w for w in rep.warnings)
    rep = check_city(_write(tmp_path, 400, 0), NOW)
    assert any("next-14-days" in w for w in rep.warnings)


def test_card_feed_over_the_hard_budget_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(payload, "CARDS_RAW_FAIL", 100_000)
    rep = check_city(_write(tmp_path, 10, 200), NOW)
    assert rep.failures and "card feed" in rep.failures[0]
    assert [r.city for r in check_all(tmp_path, NOW)] == ["testville"]


def _shard(tmp_path, name: str, size: int) -> None:
    d = tmp_path / "cities" / "testville"
    (d / name).parent.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text("{}")
    (d / name).write_text("x" * size)


def test_a_sharded_city_budgets_its_shards_not_the_fallback_file(tmp_path, monkeypatch):
    # the Oct 27–Nov 2 CI failures: NYC's whole feed hit 42 MB once Ticketmaster was keyed, but browsers load shards
    monkeypatch.setattr(payload, "CARDS_RAW_FAIL", 100_000)
    cards = _write(tmp_path, 10, 200)
    _shard(tmp_path, "w/2026-W45.abc.json", 900_000)
    _shard(tmp_path, "d/2026-W45.def.json", 300_000)
    rep = check_city(cards, NOW)
    assert not rep.failures and any("legacy fallback" in w for w in rep.warnings)
    _shard(tmp_path, "w/2026-W46.big.json", payload.SHARD_RAW_FAIL + 1)
    rep = check_city(cards, NOW)
    assert rep.failures == [
        f"testville: shard w/2026-W46.big.json {(payload.SHARD_RAW_FAIL + 1) / 1e6:.2f} MB raw > 1.5 MB"
    ]
