from __future__ import annotations

from uuid import uuid4
from xmlrpc import client

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def valid_payload() -> dict[str, object]:
    return {
        "title": "Publish the API contract",
        "description": "Export and review the OpenAPI document.",
        "owner": "platform-team",
        "status": "ready",
        "labels": ["api", "contract"],
    }


def test_health_and_request_id(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "request-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"


def test_write_auth_fails_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    monkeypatch.delenv("MODULE0_API_TOKEN")
    response = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/configuration-error")


def test_wrong_token_is_unauthorised(client: TestClient, auth_headers: dict[str, str]) -> None:
    auth_headers["Authorization"] = "Bearer wrong-token"
    response = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_create_get_and_idempotent_replay(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    assert created.status_code == 201
    assert created.headers["ETag"] == '"1"'
    assert created.headers["Idempotency-Replayed"] == "false"
    item_id = created.json()["id"]

    replayed = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    assert replayed.status_code == 200
    assert replayed.json()["id"] == item_id
    assert replayed.headers["Idempotency-Replayed"] == "true"

    fetched = client.get(f"/api/v1/work-items/{item_id}")
    assert fetched.status_code == 200
    assert fetched.headers["ETag"] == '"1"'


def test_idempotency_conflict_is_problem_details(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    changed = valid_payload()
    changed["title"] = "A different operation"
    response = client.post("/api/v1/work-items", headers=auth_headers, json=changed)
    assert response.status_code == 409
    assert response.json()["type"].endswith("/idempotency-conflict")
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_validation_failure_is_rfc_9457(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/work-items",
        headers=auth_headers,
        json={"title": "x", "owner": "Invalid owner"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["title"] == "Request validation failed"
    assert response.json()["errors"]


def test_conditional_update_rejects_stale_clients(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    item_id = created.json()["id"]
    update_headers = {"Authorization": "Bearer test-token", "If-Match": '"1"'}
    updated = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=update_headers,
        json={"status": "doing"},
    )
    assert updated.status_code == 200
    assert updated.headers["ETag"] == '"2"'

    stale = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers=update_headers,
        json={"status": "done"},
    )
    assert stale.status_code == 412
    assert stale.json()["current_etag"] == '"2"'

    saved = client.get(f"/api/v1/work-items/{item_id}")
    assert saved.json()["status"] == "doing"


def test_update_requires_a_valid_if_match(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    item_id = created.json()["id"]
    no_precondition = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers={"Authorization": "Bearer test-token"},
        json={"status": "doing"},
    )
    assert no_precondition.status_code == 428
    invalid = client.patch(
        f"/api/v1/work-items/{item_id}",
        headers={"Authorization": "Bearer test-token", "If-Match": "not-an-etag"},
        json={"status": "doing"},
    )
    assert invalid.status_code == 400



def test_api_pagination_follows_opaque_cursor(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    item_ids = []

    for number in range(3):
        headers = auth_headers.copy()
        headers["Idempotency-Key"] = f"pagination-test-{number:03d}"
        payload = valid_payload()
        payload["title"] = f"Pagination item {number}"

        created = client.post(
            "/api/v1/work-items",
            headers=headers,
            json=payload,
        )
        assert created.status_code == 201
        item_ids.append(created.json()["id"])

    first_page = client.get("/api/v1/work-items", params={"limit": 1})
    assert first_page.status_code == 200
    assert [item["id"] for item in first_page.json()["items"]] == [item_ids[0]]

    cursor = first_page.json()["next_cursor"]
    assert cursor is not None

    second_page = client.get(
        "/api/v1/work-items",
        params={"limit": 1, "cursor": cursor},
    )
    assert second_page.status_code == 200
    assert [item["id"] for item in second_page.json()["items"]] == [item_ids[1]]

    cursor = second_page.json()["next_cursor"]
    assert cursor is not None

    third_page = client.get(
        "/api/v1/work-items",
        params={"limit": 1, "cursor": cursor},
    )
    assert third_page.status_code == 200
    assert [item["id"] for item in third_page.json()["items"]] == [item_ids[2]]
    assert third_page.json()["next_cursor"] is None


def test_not_found_and_invalid_cursor_are_separate_problems(client: TestClient) -> None:
    missing = client.get(f"/api/v1/work-items/{uuid4()}")
    assert missing.status_code == 404
    invalid_cursor = client.get("/api/v1/work-items?cursor=invalid")
    assert invalid_cursor.status_code == 400


def test_graphql_read_prototype(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/work-items", headers=auth_headers, json=valid_payload())
    item_id = created.json()["id"]
    response = client.post(
        "/graphql",
        json={
            "query": "query($id: ID!) { workItem(id: $id) { id title status } }",
            "variables": {"id": item_id},
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["workItem"]["id"] == item_id

    listed = client.post(
        "/graphql",
        json={"query": '{ workItems(limit: 10, status: "ready") { id title } }'},
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["workItems"][0]["id"] == item_id

    missing = client.post(
        "/graphql",
        json={"query": '{ workItem(id: "not-a-uuid") { id } }'},
    )
    assert missing.status_code == 200
    assert missing.json()["data"]["workItem"] is None
