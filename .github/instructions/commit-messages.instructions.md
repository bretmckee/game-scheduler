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
- **Line length**: keep every line at most 80 characters; long lines break
  `git log`, terminal panes, and GitHub rendering. Enforced by the
  `check-commit-message-lines` pre-commit hook (commit-msg stage); wrap long
  bullets or sentences instead of bypassing it (see
  `.github/instructions/quality-check-overrides.instructions.md`).

## Example

```
feat: add scheduler health endpoint

- add /healthz route with database connectivity check
- include timeout and retry configuration
- update service documentation

Rationale: required for load balancer health checks in staging
```
