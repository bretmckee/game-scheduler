---
description: 'Implement the reminder-schedule consolidation plan (public populate_reminder_schedule primitive in shared/services/game_schedules.py, delegating NotificationScheduleService.populate_schedule)'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Consolidate reminder-schedule population into a single shared implementation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260816-01-reminder-schedule-consolidation-changes.md` in `.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260816-01-reminder-schedule-consolidation.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the "retrofitting tests for already-correct code" convention used throughout this plan — this is a pure rename/delegate refactor, not a bug fix, so no xfail/RED-GREEN workflow applies anywhere in this plan
- `.github/instructions/unit-tests.instructions.md` for falsifiable, real-argument mock assertions in the new delegation test (Phase 2 Task 2.2)
- `.github/instructions/fastapi-transaction-patterns.instructions.md` for the non-committing-primitive / committing-caller pattern that both the shared function and the delegating wrapper must preserve
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style
- `.github/instructions/test-execution.instructions.md` for the `scripts/run-integration-tests.sh` output-capture and timeout rules used in Phase 2 Task 2.3 (always use `tee`)

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

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- Phase 2 only, once (Task 2.3, after Task 2.2 reaches GREEN — not after every task): a `scripts/run-integration-tests.sh` run scoped to `tests/integration/test_notification_schedule.py`, confirming the `311e6c48` join-notification-survives-reminder-refresh regression test remains green through the newly-delegated `populate_schedule`. Follow `.github/instructions/test-execution.instructions.md`: capture full output via `tee` before any filtering, and use a timeout of at least 10 minutes.

Frontend build/test gates do not apply to this task (no frontend files change).

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

This plan contains no bug fixes — do NOT apply the xfail/TDD Bug Fix Workflow anywhere in it. Every task is a rename, a delegation, or a verification step over already-correct, unchanged behavior.

Do NOT bundle either of the two optional, out-of-scope follow-ups noted at the end of the details file (having `_setup_game_schedules` call the shared `setup_game_schedules` bundler directly; deleting the dead `NotificationScheduleService.clear_schedule`) into this implementation — the research explicitly flags both as "confirm with user before bundling."

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/changes/20260816-01-reminder-schedule-consolidation-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20260816-01-reminder-schedule-consolidation.plan.md`, `.copilot-tracking/planning/details/20260816-01-reminder-schedule-consolidation-details.md`, and `.copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
