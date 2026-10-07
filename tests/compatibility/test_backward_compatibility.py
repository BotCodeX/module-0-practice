from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_api.main import app
from scripts.check_openapi_compat import breaking_changes

pytestmark = pytest.mark.compatibility


def test_current_contract_is_compatible_with_baseline() -> None:
    baseline = json.loads(Path("contracts/openapi.baseline.json").read_text(encoding="utf-8"))
    assert breaking_changes(baseline, app.openapi()) == []
