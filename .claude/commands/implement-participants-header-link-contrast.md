---
description: 'Implement the GameDetails participants header link contrast fix (MUI Link with inherited color instead of a bare RouterLink)'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Participants Header Link Contrast (Visited Color)

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20261109-01-participants-header-link-contrast-changes.md` in `.copilot-tracking/planning/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20261109-01-participants-header-link-contrast.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/reactjs.instructions.md` for React components
- `.github/instructions/typescript-5-es2022.instructions.md` for TypeScript code
- `.github/instructions/test-driven-development.instructions.md` (TDD for Bug Fixes) for the RED/GREEN cycle
- `.github/instructions/unit-tests.instructions.md` for test quality
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may tell you at the start of the session (or at any point) to run through multiple phases or tasks without stopping — follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
fix: Phase N - {{description, including feature context if non-obvious}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `cd frontend && npm run build` — TypeScript build
- `cd frontend && npm run test` — frontend tests
- `uv run pytest tests/unit` and `uv run mypy shared/ services/` — only if any Python files changed (none are expected)

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/planning/changes/20261109-01-participants-header-link-contrast-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20261109-01-participants-header-link-contrast.plan.md`, `.copilot-tracking/planning/details/20261109-01-participants-header-link-contrast-details.md`, and `.copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] Regression test passes with `.fails` removed and assertions unchanged
- [ ] Frontend build and tests pass
- [ ] Changes file updated continuously
