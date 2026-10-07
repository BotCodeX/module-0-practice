from __future__ import annotations

import json
from pathlib import Path

import pytest

from platform_api.main import app

pytestmark = pytest.mark.contract


def test_openapi_baseline_matches_implementation() -> None:
    baseline = json.loads(Path("contracts/openapi.baseline.json").read_text(encoding="utf-8"))
    assert app.openapi() == baseline


def test_contract_exposes_versioned_paths_and_problem_details() -> None:
    contract = app.openapi()
    assert contract["openapi"].startswith("3.1.")
    assert "/api/v1/work-items" in contract["paths"]
    response_409 = contract["paths"]["/api/v1/work-items"]["post"]["responses"]["409"]
    assert "application/problem+json" in response_409["content"]
