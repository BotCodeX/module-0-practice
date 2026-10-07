# Local service runbook

## Start

1. Run `uv sync --locked --all-extras`.
2. Set `MODULE0_API_TOKEN` to a local value.
3. Run `uv run platform-api`.
4. Confirm `curl -fsS http://127.0.0.1:8000/healthz` returns a healthy response.

## Symptoms and checks

### Write requests return 503

The service has failed closed because `MODULE0_API_TOKEN` is absent. Set the variable in the service process, restart the service and repeat the request. Do not add a token default to source code.

### Write requests return 401

Confirm the client uses `Authorization: Bearer <token>` and that the value matches the service process. Do not print the token while troubleshooting.

### Update returns 412

The `If-Match` value is stale. Fetch the work item, read the current `ETag`, reconcile the intended change and retry with the new value.

### Create returns 409 for an idempotency key

The key was already used with a different request body. Generate a key for the logical operation, or replay the exact original body. Do not silently reuse the key for another operation.

## Evidence to retain

- Request ID from the response header and problem body.
- HTTP method, path, status and response media type.
- Relevant test output and the smallest reproducing request.
- The commit that introduced the behaviour and the commit that fixed it.
- No bearer tokens, environment dumps or private data.

