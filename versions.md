# Version register

Reviewed: 17 August 2026

| Component | Baseline | Policy |
| --- | --- | --- |
| Python | 3.14.6 for learner work; package supports 3.12-3.14 | Use a stable maintenance release. Python 3.15 is pre-release at this baseline. |
| uv | 0.11.33 used to create the lock file | Run CI with the lock file and an explicitly selected uv version. |
| OpenAPI | 3.2.0 for study; implementation output is 3.1.x | Record the version the framework actually emits. |
| GraphQL | September 2025 specification | Use the latest published edition, not the working draft, for the learning baseline. |
| HTTP | RFC 9110 | Treat method and status semantics as protocol rules, not framework conventions. |
| Problem details | RFC 9457 | Use `application/problem+json` for machine-readable API errors. |
| Semantic Versioning | 2.0.0 | Version the public contract, not internal implementation details. |

Dependency patch versions are fixed in `uv.lock`. Review the lock file monthly during this module and before any release candidate. Read release notes before updating a major or minor dependency.

