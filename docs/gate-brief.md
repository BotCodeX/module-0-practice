# Module 0 exit-gate brief

Timebox: four hours. Work from an empty repository or a supplied minimal scaffold.

## Scenario

Add a backward-compatible `priority` field and list filter. Create the work on a branch, resolve an injected conflict in the API model, add provider and consumer tests, demonstrate a failing then passing pipeline, and tag `v0.2.0-rc.1`.

## Required evidence

- Understandable Git history and a reviewed diff.
- OpenAPI document and compatibility result.
- REST tests and one GraphQL comparison note.
- CI record, build artefact and SHA-256 checksum.
- README update, ADR amendment if needed and a concise defect note.
- A tag from which the assessor can reproduce the checks.

## Pass conditions

- Unit, integration, contract, compatibility, lint, format and type checks pass.
- Existing consumers that ignore the optional field still work.
- No secrets are committed or printed.
- The REST versus GraphQL decision is reasoned from consumer needs and operational cost.
- The candidate artefact is reproducible from the tag.

