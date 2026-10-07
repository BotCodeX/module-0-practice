# Security policy for the learning repository

This repository is deliberately non-production. Report a discovered vulnerability privately to the repository owner rather than opening a public issue that includes exploit details or secrets.

## Supported scope

- The current `main` branch and the latest tagged release candidate.
- Dependency and workflow configuration included in this repository.
- Accidental credential exposure in Git history, logs or artefacts.

## Lab rules

- Use disposable credentials and local data only.
- Never paste a real token into a command that will be stored in shell history.
- Do not weaken authentication to make a test pass.
- Do not upload `.env`, local caches or unreviewed hidden files as CI artefacts.
- Rotate any credential immediately if it appears in a commit, even if the commit is later removed.

