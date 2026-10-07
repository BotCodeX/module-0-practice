from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from pydantic import ValidationError

from platform_api.models import WorkItemCreate, WorkItemFile

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_TRANSPORT = 3
EXIT_API = 4


def load_work_item_file(path: Path) -> WorkItemFile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return WorkItemFile.model_validate(raw)


def idempotency_key(item: WorkItemCreate) -> str:
    canonical = json.dumps(item.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return "cli-" + hashlib.sha256(canonical.encode()).hexdigest()


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _problem_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"API returned HTTP {response.status_code}"
    if isinstance(body, dict):
        title = str(body.get("title", "API request failed"))
        detail = str(body.get("detail", "No detail was supplied."))
        request_id = str(body.get("request_id", "unavailable"))
        return f"{title}: {detail} (request_id={request_id})"
    return f"API returned HTTP {response.status_code}"


def _headers(write: bool) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if write:
        token = os.getenv("MODULE0_API_TOKEN")
        if not token:
            raise ValueError("MODULE0_API_TOKEN is required for write commands")
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _apply(client: httpx.Client, path: Path) -> int:
    work_file = load_work_item_file(path)
    results: list[dict[str, Any]] = []
    for item in work_file.items:
        headers = _headers(write=True)
        headers["Idempotency-Key"] = idempotency_key(item)
        response = client.post(
            "/api/v1/work-items",
            headers=headers,
            json=item.model_dump(mode="json"),
        )
        if response.is_error:
            print(_problem_message(response), file=sys.stderr)
            return EXIT_API
        body = response.json()
        assert isinstance(body, dict)
        results.append(body)
    _print_json({"items": results})
    return EXIT_OK


def _list(client: httpx.Client, status: str | None, owner: str | None) -> int:
    params = {key: value for key, value in {"status": status, "owner": owner}.items() if value}
    response = client.get("/api/v1/work-items", params=params, headers=_headers(write=False))
    if response.is_error:
        print(_problem_message(response), file=sys.stderr)
        return EXIT_API
    _print_json(response.json())
    return EXIT_OK


def _get(client: httpx.Client, item_id: str) -> int:
    response = client.get(f"/api/v1/work-items/{item_id}", headers=_headers(write=False))
    if response.is_error:
        print(_problem_message(response), file=sys.stderr)
        return EXIT_API
    _print_json(response.json())
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="platform-work-items",
        description="Read YAML, call the Module 0 API and write structured JSON.",
        epilog="Exit codes: 0 success, 2 invalid input, 3 transport failure, 4 API failure.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("MODULE0_BASE_URL", "http://127.0.0.1:8000"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply", help="create work items from validated YAML")
    apply_parser.add_argument("--file", type=Path, required=True)

    list_parser = subparsers.add_parser("list", help="list work items")
    list_parser.add_argument("--status", choices=["backlog", "ready", "doing", "done"])
    list_parser.add_argument("--owner")

    get_parser = subparsers.add_parser("get", help="get one work item")
    get_parser.add_argument("item_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with httpx.Client(base_url=args.base_url, timeout=5.0, trust_env=False) as client:
            if args.command == "apply":
                return _apply(client, args.file)
            if args.command == "list":
                return _list(client, args.status, args.owner)
            if args.command == "get":
                return _get(client, args.item_id)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except httpx.RequestError as exc:
        print(f"transport error: {exc}", file=sys.stderr)
        return EXIT_TRANSPORT
    return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
