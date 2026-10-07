# Contributing

Use a short-lived branch and keep commits small enough to review. Before requesting review, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov
uv run python scripts/export_contract.py --check
```

If an API change is intended, export a temporary current contract first and run the compatibility checker before replacing the baseline:

```bash
uv run python scripts/export_contract.py --output /tmp/openapi.current.json
uv run python scripts/check_openapi_compat.py contracts/openapi.baseline.json /tmp/openapi.current.json
uv run python scripts/export_contract.py
```

Review the diff, explain the consumer effect and amend the ADR when the interface decision changes.

## Git safety

- Prefer `git restore --staged` to unstage and `git revert` to undo a shared commit.
- Inspect `git status`, `git diff` and `git log --oneline --decorate --graph` before changing history.
- Use `git reflog` to find lost local references.
- Do not force-push a shared branch unless the team has explicitly coordinated it.

