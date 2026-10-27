"""Curated venue files (config/venues/<slug>.yaml) never carry an unsourced fact (CLAUDE.md rule 1)."""

from pathlib import Path

import yaml

from gotc.config import CONFIG_DIR, load_registry


def test_every_curated_fact_cites_its_source() -> None:
    cities = set(load_registry().cities)
    for path in sorted((CONFIG_DIR / "venues").glob("*.yaml")):
        assert path.stem in cities, f"{path.name}: no such city"
        for it in yaml.safe_load(path.read_text()) or []:
            where = f"{path.name}: {it.get('name')}"
            assert it.get("name"), where
            if it.get("capacity") is not None:
                assert it.get("capacity_source") and it.get("evidence"), f"{where}: capacity without source/evidence"
            if it.get("address") and it.get("capacity") is None:
                assert it.get("address_source"), f"{where}: address without address_source"
            if it.get("lat") is not None:
                assert -90 <= it["lat"] <= 90 and -180 <= it["lon"] <= 180, where
                assert it.get("coords_source") or it.get("capacity_source"), f"{where}: coordinates without a source"


def test_paths_exist() -> None:
    assert Path(CONFIG_DIR / "venues").is_dir()
