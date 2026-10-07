.PHONY: sync run lint format type test contract build check

sync:
	uv sync --locked --all-extras

run:
	uv run platform-api

lint:
	uv run ruff check .

format:
	uv run ruff format .

type:
	uv run mypy src

test:
	uv run pytest --cov --cov-report=term-missing

contract:
	uv run python scripts/export_contract.py --check

build:
	uv build
	sha256sum dist/* > SHA256SUMS

check: lint type test contract build

