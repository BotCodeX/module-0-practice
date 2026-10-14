# Lab 4 — Work-Item HTTP Contract

## 1. Consumer Stories

### Story 1: Create a work item
As an authenticated API client, I want to create a work item by submitting valid data, so that the system stores it and returns its identifier and representation.

**Expected guarantee:** Retrying a request after a network timeout must not accidentally create duplicate work items when the same idempotency key and request body are reused.

### Story 2: List work items
As an API client, I want to retrieve work items with pagination and optional owner and status filters, so that I can browse the collection efficiently and find relevant items.

**Expected guarantee:** Pagination must have defined limits and cursor behavior, and the filters must behave consistently across pages.

### Story 3: Conditionally update a work item
As an authenticated API client, I want to update a work item using its current ETag and the If-Match header, so that the update succeeds only if the item has not changed since I retrieved it.

**Expected guarantee:** A stale update must be rejected rather than silently overwriting a newer version.


## 2. HTTP Contract

### Operation 1: Create a work item

- **Method:** POST
- **URI:** `/api/v1/work-items`
- **Request body:** JSON matching `WorkItemCreate`.
- **Success status:** `201 Created`
- **Response body:** JSON representation of the created `WorkItem`.
- **Request headers:**
  - `Authorization: Bearer <token>` — authenticate the client.
  - `Content-Type: application/json` — identify the request body format.
  - `Accept: application/json` — request a JSON response.
  - `Idempotency-Key: <unique-key>` — identify retries of the same logical creation request.
- **Expected behavior:** Repeating a request with the same key and same body must not create a duplicate. Reusing a key with a different body must be rejected with a documented conflict response. The server's replay and key-retention rules must be defined.

### Operation 2: List work items

- **Method:** GET
- **URI:** `/api/v1/work-items`
- **Request body:** None.
- **Success status:** `200 OK`
- **Response body:** JSON representation of a `WorkItemPage`, containing the returned items and pagination information.
- **Query parameters:**
  - `limit` — number of items requested per page; default 20, minimum 1, maximum 100.
  - `cursor` — opaque token used to request the next page.
  - `owner` — optional owner filter.
  - `status` — optional work-item status filter.
- **Request headers:**
  - `Accept: application/json`.
- **Expected behavior:** The server must enforce the page-size limits, define how cursors are created and validated, and apply filters consistently across pages.

### Operation 3: Conditionally update a work item

- **Method:** PATCH
- **URI:** `/api/v1/work-items/{item_id}`
- **Request body:** JSON matching `WorkItemPatch`, containing the fields to update.
- **Success status:** `200 OK`
- **Response body:** Updated JSON representation of the `WorkItem`.
- **Request headers:**
  - `Authorization: Bearer <token>` — authenticate the client.
  - `Content-Type: application/json` — identify the request body format.
  - `Accept: application/json` — request a JSON response.
  - `If-Match: "<etag>"` — require the item to match the version previously retrieved.
- **Response headers:**
  - `ETag: "<new-etag>"` — provide the updated version identifier for a subsequent conditional update.
- **Expected behavior:** The update must only succeed when `If-Match` matches the current representation's ETag. A stale ETag must result in `412 Precondition Failed`. If the contract requires conditional updates, a missing `If-Match` must be rejected with `428 Precondition Required`.



## 3. Failure Responses and Status/Header Decisions

| Condition | Status code | Important headers | Response body |
|---|---|---|---|
| Missing or invalid authentication on a protected operation | `401 Unauthorized` | `WWW-Authenticate: Bearer` | Problem Details JSON |
| Invalid JSON syntax or malformed request content | `400 Bad Request` | None required | Problem Details JSON |
| Valid JSON that fails request-schema or field validation | `422 Unprocessable Content` | None required | Problem Details JSON |
| Requested work item does not exist | `404 Not Found` | None required | Problem Details JSON |
| `If-Match` does not match the current ETag | `412 Precondition Failed` | Current `ETag` may be included | Problem Details JSON |
| Required `If-Match` header is missing | `428 Precondition Required` | None required | Problem Details JSON |
| Idempotency key is reused with a different request body | `409 Conflict` | None required | Problem Details JSON |
| Temporary service failure prevents the request from being completed | `503 Service Unavailable` | `Retry-After` may be included when appropriate | Problem Details JSON |

### Problem Details Format

Error responses must use the media type `application/problem+json` and follow RFC 9457.

The response body should include these standard members as appropriate:

- `type` — URI identifying the problem type.
- `title` — short human-readable summary.
- `status` — HTTP status code.
- `detail` — explanation of this particular occurrence.
- `instance` — URI identifying this occurrence, if provided.
- `request_id` — application-specific extension useful for tracing the request.

The HTTP status line and the `status` member in the body must agree.

### Additional Contract Rules

1. Protected operations must authenticate the client before performing the requested action.
2. A client must not silently overwrite a newer work-item version; conditional updates require a matching ETag.
3. A retry using the same idempotency key and same request body must not create another work item.
4. Reusing an idempotency key with a different request body must follow the documented conflict policy.
5. Error responses must use `application/problem+json`, while successful JSON responses use `application/json`.


## 4. Pagination and Filtering Rules

### 4.1 Page Size

- The `limit` query parameter specifies the maximum number of work items returned in one page.
- The default limit is `20`.
- The minimum limit is `1`, and the maximum limit is `100`.
- A request with a limit outside the permitted range is rejected with a documented client-error response.

### 4.2 Cursor Pagination

- The `cursor` query parameter identifies where the next page should begin.
- The server returns pagination information in the `WorkItemPage` response.
- The client treats the cursor as an opaque value and must not construct or modify it.
- The client uses the returned next-page cursor in its subsequent request.
- If no further results exist, the response indicates that there is no next page.
- An invalid cursor is rejected with a documented client-error response.
- The contract must define how cursors behave when the underlying collection changes and whether cursors are bound to the original filters.

### 4.3 Owner Filter

- The optional `owner` query parameter filters work items by owner.
- The owner value must follow the API's owner identifier format: lowercase letters and digits, with hyphens permitted after the first character.
- When `owner` is supplied, only work items matching that owner are returned.

### 4.4 Status Filter

- The optional `status` query parameter filters work items by status.
- The value must match one of the statuses supported by the API's `WorkItemStatus` schema.
- When `status` is supplied, only work items matching that status are returned.

### 4.5 Combining Filters and Pagination

- The client may combine `owner` and `status` filters with `limit` and `cursor`.
- When both owner and status are supplied, both filters must apply to the results.
- Pagination must operate on the filtered result set.
- The server must define consistent ordering so that clients can navigate pages predictably.



## 5. RFC Review

### RFC 9110 — HTTP Semantics

1. **Resource methods:** `GET` retrieves work items, `POST` creates a work item in the collection, and `PATCH` modifies an existing work item.
2. **Authentication failures:** `401 Unauthorized` indicates missing or invalid authentication credentials. A `401` response must include `WWW-Authenticate`.
3. **Request failures:** `400 Bad Request` represents malformed requests, while `422 Unprocessable Content` can represent syntactically valid content that cannot be processed.
4. **Conditional updates:** `If-Match` makes an update conditional on the current entity tag. A failed condition must prevent the update and can be reported using `412 Precondition Failed`.
5. **Temporary failures:** `503 Service Unavailable` indicates temporary inability to handle the request. `Retry-After` may communicate when a retry is appropriate.

### RFC 9457 — Problem Details for HTTP APIs

1. Error response bodies use the `application/problem+json` media type.
2. Standard members include `type`, `title`, `status`, `detail`, and `instance`. Not every member is mandatory in every response.
3. The HTTP response status and the Problem Details `status` member must agree when the member is included.
4. `request_id` is an API-specific extension, not a standard RFC 9457 member.
5. Problem Details provides a consistent error format; it does not prescribe which status code must be used for every application-specific failure.

### Additional Standard — RFC 6585

`428 Precondition Required` is defined by RFC 6585. It can be used when the API requires a conditional request, such as a PATCH request with `If-Match`, to help prevent lost updates.

### Review Conclusion

The proposed contract uses standard HTTP methods, status codes, conditional request headers, and the RFC 9457 error format. Requirements such as mandatory conditional updates, idempotency-key conflict behavior, and the `request_id` extension are API-specific design decisions that must be documented and compared with the existing baseline.



## 6. Baseline Comparison and Discrepancies

### Confirmed Documentation Differences

1. **Conditional update requirement:** The proposed contract requires `If-Match` for PATCH, but the baseline declares this header optional. The contract should be updated to make the requirement explicit.

2. **ETag response header:** The proposed contract requires an updated `ETag` after a successful PATCH. The baseline response details inspected so far do not document this response header. Verify the complete specification before finalizing this finding.

### Areas Requiring Further Verification

3. **Idempotency behavior:** The baseline documents a required `Idempotency-Key` and a `409` response, but the exact behavior for retries, different request bodies, concurrent requests, and key retention still needs verification.

4. **Pagination behavior:** The baseline documents the `limit`, `cursor`, `owner`, and `status` parameters. Cursor validity, ordering, and behavior when the collection changes need further verification.

5. **Error behavior:** The baseline documents Problem Details schemas and several failure responses. Verify that the implementation returns the documented media type, fields, and status codes for each relevant failure.

### Conclusion

The generated baseline already documents much of the proposed HTTP contract. The clearest identified difference is that `If-Match` is optional in the baseline but required by the proposed contract. Other potential gaps must be verified against the implementation before being classified as actual behavior gaps.
