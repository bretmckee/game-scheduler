---
description: 'Execute the Participant Reposition Bug Fix implementation plan phase-by-phase'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Participant Reposition Bug Fix

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260716-01-participant-reposition-bug-changes.md` in `.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260716-01-participant-reposition-bug.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the RED→GREEN→REFACTOR "bug fix" workflow (no stub, `xfail(strict=True)`/`test.failing` then remove) that governs Phases 1-3 of this plan; Phase 4's integration tests are written after the fix exists, so no RED phase applies there
- `.github/instructions/unit-tests.instructions.md` for every new or rewritten test — falsifiable assertions, no coverage theater
- `.github/instructions/reactjs.instructions.md` and `.github/instructions/typescript-5-es2022.instructions.md` for the `EditGame.tsx`/`EditableParticipantList.tsx` changes in Phase 3
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
- `cd frontend && npm run build` — TypeScript build, required once Phase 3 touches frontend files
- `cd frontend && npm run test` — frontend unit tests, required once Phase 3 touches frontend files
- `uv run alembic upgrade head` / `uv run alembic downgrade -1` / `uv run alembic upgrade head` — required once, at the end of Phase 1 (Task 1.3), to verify the new migration applies and reverses cleanly
- `scripts/run-integration-tests.sh tests/integration/test_games_crud.py |& tee output-integration.txt` — required once, at the end of Phase 4 (Task 4.1, which covers both the plain self-added and the `ROLE_BASED` conversion scenarios, and again as part of Task 4.3), per `.github/instructions/test-execution.instructions.md`: always capture full output with `tee` before filtering, allow adequate timeout

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/changes/20260716-01-participant-reposition-bug-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20260716-01-participant-reposition-bug.plan.md`, `.copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md`, and `.copilot-tracking/research/20260716-01-participant-reposition-bug-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
- [ ] `ROLE_BASED` reordering is implemented per the decision recorded in the plan (Phase 2, Tasks 2.4-2.6): an explicitly-repositioned `ROLE_MATCHED` participant converts to `SELF_ADDED` with an explicit `position`; untouched `ROLE_MATCHED` participants keep their type and priority-index `position`; `shared/utils/participant_sorting.py` has zero diff
