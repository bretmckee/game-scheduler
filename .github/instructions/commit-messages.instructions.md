---
description: 'Write clear, detailed git commit messages with summaries and rationale; branch policy for AI agents'
applyTo: '**'
---

# Commit Message Guidelines

## Branch Policy

When asked to commit, commit to whatever branch is currently checked out —
do not create a new branch on your own initiative. The one exception: if the
current branch is `staging` or `main`, stop and ask what to do instead of
committing or branching automatically. `develop` is not an exception; it is
fine to commit to directly.

When creating git commits, use a multi-line message format:

- **Subject line**: short, imperative summary (no trailing period)
- **Body**: bullet list of notable changes
- **Rationale**: include a brief reason when the change is non-obvious

## Example

```
feat: add scheduler health endpoint

- add /healthz route with database connectivity check
- include timeout and retry configuration
- update service documentation

Rationale: required for load balancer health checks in staging
```
