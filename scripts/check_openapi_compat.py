from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain an OpenAPI object")
    return value


def _resolve(document: dict[str, Any], value: Any) -> Any:
    if not isinstance(value, dict) or "$ref" not in value:
        return value
    ref = value["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return value
    resolved: Any = document
    for part in ref[2:].split("/"):
        resolved = resolved[part.replace("~1", "/").replace("~0", "~")]
    return resolved


def _schemas(response: dict[str, Any]) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for media in response.get("content", {}).values():
        schema = media.get("schema") if isinstance(media, dict) else None
        if isinstance(schema, dict):
            schemas.append(schema)
    return schemas


def _compare_response_schema(
    baseline_doc: dict[str, Any],
    current_doc: dict[str, Any],
    baseline: dict[str, Any],
    current: dict[str, Any],
    location: str,
    changes: list[str],
) -> None:
    baseline = _resolve(baseline_doc, baseline)
    current = _resolve(current_doc, current)
    if not isinstance(baseline, dict) or not isinstance(current, dict):
        return
    if baseline.get("type") != current.get("type"):
        changes.append(f"{location}: schema type changed")
        return
    baseline_properties = baseline.get("properties", {})
    current_properties = current.get("properties", {})
    if isinstance(baseline_properties, dict) and isinstance(current_properties, dict):
        for name, baseline_property in baseline_properties.items():
            if name not in current_properties:
                changes.append(f"{location}: response property {name!r} was removed")
                continue
            if isinstance(baseline_property, dict) and isinstance(current_properties[name], dict):
                _compare_response_schema(
                    baseline_doc,
                    current_doc,
                    baseline_property,
                    current_properties[name],
                    f"{location}.{name}",
                    changes,
                )
    baseline_items = baseline.get("items")
    current_items = current.get("items")
    if isinstance(baseline_items, dict) and isinstance(current_items, dict):
        _compare_response_schema(
            baseline_doc,
            current_doc,
            baseline_items,
            current_items,
            f"{location}[]",
            changes,
        )


def breaking_changes(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    baseline_paths = baseline.get("paths", {})
    current_paths = current.get("paths", {})
    for path, baseline_path in baseline_paths.items():
        if path not in current_paths:
            changes.append(f"path removed: {path}")
            continue
        current_path = current_paths[path]
        for method, baseline_operation in baseline_path.items():
            if method not in HTTP_METHODS:
                continue
            if method not in current_path:
                changes.append(f"operation removed: {method.upper()} {path}")
                continue
            current_operation = current_path[method]

            baseline_params = {
                (parameter.get("in"), parameter.get("name")): parameter
                for parameter in baseline_operation.get("parameters", [])
            }
            current_params = {
                (parameter.get("in"), parameter.get("name")): parameter
                for parameter in current_operation.get("parameters", [])
            }
            for key, parameter in baseline_params.items():
                if key not in current_params:
                    changes.append(f"{method.upper()} {path}: parameter {key} removed")
                elif not parameter.get("required") and current_params[key].get("required"):
                    changes.append(f"{method.upper()} {path}: parameter {key} became required")
            for key, parameter in current_params.items():
                if key not in baseline_params and parameter.get("required"):
                    changes.append(f"{method.upper()} {path}: new required parameter {key}")

            baseline_responses = baseline_operation.get("responses", {})
            current_responses = current_operation.get("responses", {})
            for code, baseline_response in baseline_responses.items():
                if code not in current_responses:
                    changes.append(f"{method.upper()} {path}: response {code} removed")
                    continue
                baseline_schemas = _schemas(baseline_response)
                current_schemas = _schemas(current_responses[code])
                if baseline_schemas and not current_schemas:
                    changes.append(f"{method.upper()} {path}: response {code} schema removed")
                elif baseline_schemas and current_schemas:
                    _compare_response_schema(
                        baseline,
                        current,
                        baseline_schemas[0],
                        current_schemas[0],
                        f"{method.upper()} {path} response {code}",
                        changes,
                    )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Check an OpenAPI document for breaking changes.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    changes = breaking_changes(load(args.baseline), load(args.current))
    if changes:
        print("Breaking changes detected:")
        for change in changes:
            print(f"- {change}")
        return 1
    print("No breaking changes detected by the Module 0 policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
