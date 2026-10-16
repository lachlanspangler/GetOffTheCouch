"""config/pending_sources/<city>.yaml holds source entries for cities whose city file lands separately.
They must be valid SourceConfig entries for known adapters, with ids unique across the whole registry."""

from pathlib import Path

import pytest
import yaml

from gotc.adapters.base import get_adapter
from gotc.config import SourceConfig, load_registry
from gotc.settings import CONFIG_DIR

PENDING = sorted((CONFIG_DIR / "pending_sources").glob("*.yaml"))


@pytest.mark.parametrize("path", PENDING, ids=lambda p: Path(p).stem)
def test_pending_sources_are_valid(path):
    entries = yaml.safe_load(path.read_text())["sources"]
    assert entries
    for raw in entries:
        src = SourceConfig.model_validate(raw)
        adapter = get_adapter(src.adapter)
        adapter.check_config(src)
        assert src.scope == "city"


def test_pending_ids_are_unique_and_do_not_clash_with_the_registry():
    ids = [raw["id"] for p in PENDING for raw in yaml.safe_load(p.read_text())["sources"]]
    assert len(ids) == len(set(ids))
    registry_ids = set(load_registry().all_sources())
    for p in PENDING:
        city_file = CONFIG_DIR / "cities" / p.name
        if city_file.exists():  # once merged, the city file owns these ids
            continue
        clash = {raw["id"] for raw in yaml.safe_load(p.read_text())["sources"]} & registry_ids
        assert not clash, f"{p.name}: ids already defined elsewhere: {clash}"
