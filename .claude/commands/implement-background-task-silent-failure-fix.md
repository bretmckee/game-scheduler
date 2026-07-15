---
description: 'Execute the Background-Task Silent-Failure Fix implementation plan phase-by-phase'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Background-Task Silent-Failure Fix

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260715-01-background-task-silent-failure-fix-changes.md` in `.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260715-01-background-task-silent-failure-fix.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the RED→GREEN→REFACTOR "bug fix" workflow (no stub, `xfail(strict=True)` then remove) that governs every task in this plan
- `.github/instructions/unit-tests.instructions.md` for every new or rewritten test — falsifiable assertions, no coverage theater
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may tell you at the start of the session (or at any point) to run through multiple phases or tasks without stopping — follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - {{description, including feature context if non-obvious}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests (never `pytest --testmon` manually — see `CLAUDE.md`'s testmon warning; if `.testmondata` becomes stale, delete it before retrying a commit)
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- `scripts/run-integration-tests.sh tests/integration/test_scheduler_loop.py |& tee output-integration.txt` — required once, at the end of Phase 3 (Task 3.3), per `.github/instructions/test-execution.instructions.md`: always capture full output with `tee` before filtering, allow at least 10 minutes

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/changes/20260715-01-background-task-silent-failure-fix-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20260715-01-background-task-silent-failure-fix.plan.md`, `.copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md`, and `.copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
