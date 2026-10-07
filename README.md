# Module 0 Platform API

This repository is the practical spine for Module 0 of the Gated Platform Engineering Roadmap. It contains a versioned REST API, a YAML-driven CLI, a small GraphQL read prototype, automated tests, a compatibility baseline and a CI workflow.

The domain is intentionally simple: teams create and inspect work items. The engineering behaviours are the point.

## What the repository demonstrates

- Resource-oriented HTTP endpoints under `/api/v1`.
- Pagination and filtering with an opaque cursor.
- Idempotent creation through the `Idempotency-Key` header.
- Optimistic concurrency with `ETag` and `If-Match`.
- RFC 9457 problem details using `application/problem+json`.
- Fail-closed bearer-token authentication for write operations.
- OpenAPI output, a checked-in compatibility baseline and a GraphQL read path.
- Unit, integration, contract and backward-compatibility tests.
- Lint, formatting, type, test, build and checksum stages in CI.

This is a learning system, not a production service. It keeps data in memory and uses one static bearer token from an environment variable. Those constraints are explicit so that the code remains small enough to rebuild during the exit gate.

## Quick start with uv

Install `uv`, then run:

```bash
uv python install 3.14.6
uv sync --locked --all-extras
export MODULE0_API_TOKEN="choose-a-local-lab-token"
uv run platform-api
```

Open `http://127.0.0.1:8000/docs` for interactive REST documentation. The OpenAPI document is at `http://127.0.0.1:8000/api/v1/openapi.json`, and GraphQL is at `http://127.0.0.1:8000/graphql`.

On Windows PowerShell, set the token with:

```powershell
$env:MODULE0_API_TOKEN = "choose-a-local-lab-token"
uv run platform-api
```

## Use the CLI

In a second terminal, set the same token and create the sample work items:

```bash
export MODULE0_API_TOKEN="choose-a-local-lab-token"
uv run platform-work-items apply --file examples/work-items.yaml
uv run platform-work-items list --status ready
```

Successful command output is JSON on standard output. Human-readable failures are written to standard error. Exit codes are documented by `uv run platform-work-items --help`.

## Run the quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov --cov-report=term-missing
uv run python scripts/export_contract.py --check
uv build
```

## Repository map

```text
src/platform_api/      API, CLI, repository and GraphQL implementation
tests/                 Unit, integration, contract and compatibility tests
contracts/             OpenAPI baseline and GraphQL SDL
examples/              Valid and deliberately invalid learner inputs
docs/                  ADR, runbook, defect note and gate brief
scripts/               Contract export and compatibility helpers
.github/workflows/     CI example
```

## Security boundary

- The service refuses write requests if `MODULE0_API_TOKEN` is absent.
- The example token is never a usable default in the application.
- Secrets must be supplied through the environment and must not appear in Git history, logs or build artefacts.
- The CI workflow requests only `contents: read`. No cloud deployment is performed, so it does not request OIDC permissions.

## Contract policy

FastAPI currently emits an OpenAPI 3.1 document for this project. Module 0 also teaches the published OpenAPI 3.2 specification, but the checked-in contract reports the version actually produced by the implementation. Do not change the `openapi` field merely to claim a newer standard.

`contracts/openapi.baseline.json` is the consumer compatibility baseline. A change may add optional fields, endpoints or response codes. Removing an existing path, operation or successful response, or making a previously optional response field required, is treated as breaking by the included checker.

## Suggested learning sequence

1. Run the repository unchanged and explain every quality check.
2. Add a backward-compatible `priority` filter and its tests.
3. Introduce one controlled failure from the assessor guide and diagnose it from evidence.
4. Rebuild the feature on a branch, resolve a merge conflict and tag `v0.2.0-rc.1`.

See `docs/gate-brief.md` for the exit-gate evidence bundle.

