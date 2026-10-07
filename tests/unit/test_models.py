from __future__ import annotations

import pytest
from pydantic import ValidationError

from platform_api.models import WorkItemCreate, WorkItemPatch

pytestmark = pytest.mark.unit


def test_labels_are_normalised() -> None:
    item = WorkItemCreate(title="A valid item", owner="platform-team", labels=["API", "contract"])
    assert item.labels == ["api", "contract"]


def test_duplicate_labels_are_rejected() -> None:
    with pytest.raises(ValidationError, match="labels must be unique"):
        WorkItemCreate(title="A valid item", owner="platform-team", labels=["api", "API"])


def test_empty_patch_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least one field"):
        WorkItemPatch()
