from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from platform_api.main import app
from platform_api.repository import repository


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("MODULE0_API_TOKEN", "test-token")
    repository.clear()
    with TestClient(app) as test_client:
        yield test_client
    repository.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token", "Idempotency-Key": "test-key-0001"}
