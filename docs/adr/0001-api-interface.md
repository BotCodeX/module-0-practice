# ADR 0001: Keep REST as the primary interface

- Status: accepted for the Module 0 baseline
- Date: 17 August 2026

## Context

The service exposes a small collection of work items. Consumers need predictable creation, conditional updates, pagination, filtering, cache-friendly reads and conventional operational tooling. Module 0 also needs a concrete comparison with GraphQL.

## Decision

Keep the versioned REST API as the supported interface. Retain a read-only GraphQL prototype solely as a comparison exercise.

## Reasons

- HTTP methods, status codes, idempotency and conditional requests map directly to the operations.
- OpenAPI provides an explicit contract that is easy to validate in CI.
- The expected clients do not yet need arbitrary traversal across a connected graph or independently evolving field selections.
- A GraphQL endpoint would add resolver-cost, field-authorisation and query-complexity controls without a demonstrated consumer need.

## Consequences

- REST compatibility is release-blocking.
- The GraphQL schema is educational and has no stability promise.
- Reconsider this decision if real consumers require multiple related resources in variable shapes and REST aggregation becomes the dominant source of coupling or over-fetching.

