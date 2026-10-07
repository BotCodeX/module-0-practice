from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from platform_api.main import app

DEFAULT_OUTPUT = Path("contracts/openapi.baseline.json")


def render_contract() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or verify the OpenAPI contract.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_contract()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print(
                "contract drift: run "
                f"{sys.executable} scripts/export_contract.py and review the diff",
                file=sys.stderr,
            )
            return 1
        print("OpenAPI contract matches the checked-in baseline")
        return 0
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
