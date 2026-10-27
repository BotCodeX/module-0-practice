from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from platform_api.cli import idempotency_key, load_work_item_file

pytestmark = pytest.mark.unit


def test_valid_yaml_is_loaded() -> None:
    path = Path("examples/work-items.yaml")
    loaded = load_work_item_file(path)
    assert len(loaded.items)==2
    assert idempotency_key(loaded.items[0]).startswith("cli-")


def test_invalid_yaml_contract_is_rejected() -> None:
    with pytest.raises(ValidationError):
        load_work_item_file(Path("examples/invalid-work-items.yaml"))


def test_duplicate_labels_in_yaml_are_rejected() -> None:
    with pytest.raises(ValidationError, match="labels must be unique"):
        load_work_item_file(Path("examples/duplicate-labels.yaml"))
