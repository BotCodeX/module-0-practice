from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any

import httpx
import pytest

from platform_api import cli

pytestmark = pytest.mark.unit


class StubClient:
    def __init__(
        self,
        *,
        post_responses: list[httpx.Response] | None = None,
        get_response: httpx.Response | None = None,
    ) -> None:
        self.post_responses = post_responses or []
        self.get_response = get_response
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def __enter__(self) -> StubClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        self.posts.append((path, kwargs))
        return self.post_responses.pop(0)

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        assert self.get_response is not None
        return self.get_response


def response(status: int, body: object | None = None, text: str | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://module0.example/test")
    if body is not None:
        return httpx.Response(status, json=body, request=request)
    return httpx.Response(status, text=text or "", request=request)


def test_apply_sends_each_item_and_prints_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MODULE0_API_TOKEN", "test-token")
    stub = StubClient(
        post_responses=[
            response(201, {"id": "one"}),
            response(201, {"id": "two"}),
        ]
    )
    result = cli._apply(stub, Path("examples/work-items.yaml"))  # type: ignore[arg-type]
    assert result == cli.EXIT_OK
    assert len(stub.posts) == 2
    assert json.loads(capsys.readouterr().out)["items"] == [{"id": "one"}, {"id": "two"}]


def test_apply_stops_on_problem_response(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MODULE0_API_TOKEN", "test-token")
    stub = StubClient(
        post_responses=[
            response(
                409,
                {"title": "Conflict", "detail": "Key reused", "request_id": "request-1"},
            )
        ]
    )
    result = cli._apply(stub, Path("examples/work-items.yaml"))  # type: ignore[arg-type]
    assert result == cli.EXIT_API
    assert "request-1" in capsys.readouterr().err


def test_list_and_get_cover_success_and_error(capsys: pytest.CaptureFixture[str]) -> None:
    listed = StubClient(get_response=response(200, {"items": [], "next_cursor": None}))
    assert cli._list(listed, "ready", "platform-team") == cli.EXIT_OK  # type: ignore[arg-type]
    assert json.loads(capsys.readouterr().out)["items"] == []

    failed = StubClient(get_response=response(404, text="not json"))
    assert cli._get(failed, "missing") == cli.EXIT_API  # type: ignore[arg-type]
    assert "HTTP 404" in capsys.readouterr().err


def test_missing_write_token_is_input_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MODULE0_API_TOKEN", raising=False)
    stub = StubClient(post_responses=[])
    monkeypatch.setattr(cli.httpx, "Client", lambda **_: stub)
    result = cli.main(["apply", "--file", "examples/work-items.yaml"])
    assert result == cli.EXIT_INPUT
    assert "MODULE0_API_TOKEN" in capsys.readouterr().err


def test_main_dispatches_list(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubClient(get_response=response(200, {"items": [], "next_cursor": None}))
    monkeypatch.setattr(cli.httpx, "Client", lambda **_: stub)
    assert cli.main(["list", "--status", "ready"]) == cli.EXIT_OK


def test_main_reports_transport_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(**_: object) -> StubClient:
        raise httpx.ConnectError("offline", request=httpx.Request("GET", "https://example.test"))

    monkeypatch.setattr(cli.httpx, "Client", fail)
    assert cli.main(["list"]) == cli.EXIT_TRANSPORT
    assert "transport error" in capsys.readouterr().err
