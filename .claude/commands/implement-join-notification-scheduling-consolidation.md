---
description: 'Implement the join-notification scheduling consolidation plan (two shared primitives in shared/services/game_schedules.py)'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Consolidate join-notification scheduling into shared primitives

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260815-01-join-notification-scheduling-consolidation-changes.md` in `.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260815-01-join-notification-scheduling-consolidation.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the bug-fix (xfail → fix → remove marker) workflow used in Phase 2 Task 2.1/2.2 and Phase 3 Task 3.1/3.2, the "retrofitting tests for correct code" convention used in Phase 1, and the plain dead-code-removal guidance (no xfail/TDD workflow) used in Phase 4
- `.github/instructions/unit-tests.instructions.md` for falsifiable, real-argument mock assertions in every new/rewritten test
- `.github/instructions/fastapi-transaction-patterns.instructions.md` for the non-committing-primitive / committing-caller pattern that both shared functions must preserve
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style
- `.github/instructions/test-execution.instructions.md` for the `scripts/run-integration-tests.sh` / `scripts/run-e2e-tests.sh` output-capture and timeout rules used in Phase 3 Task 3.3 and Phase 4 (always use `tee`)

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
- Phase 3 only, once (Task 3.3, after Task 3.2 reaches GREEN — not after every task): a `scripts/run-integration-tests.sh` run scoped to `tests/integration/test_game_signup_methods.py`, `tests/integration/test_games_crud.py`, `tests/integration/test_leave_game_promotion.py`, and `tests/integration/test_player_removed_queue.py`, and a `scripts/run-e2e-tests.sh` run scoped to `tests/e2e/test_join_notification.py`. Both exercise the functions consolidated across Phases 1-3 through real API+DB / real Discord DM delivery, which unit tests and mypy alone cannot catch. Follow `.github/instructions/test-execution.instructions.md` for both: capture full output via `tee` before any filtering, and use a timeout of at least 10 minutes for the integration run and at least 15 minutes for the e2e run.
- Phase 4 only: `scripts/run-integration-tests.sh` scoped to `tests/integration/test_guild_queries_integration.py`, since that phase modifies integration tests — same output-capture and timeout rules apply.

Frontend build/test gates do not apply to this task (no frontend files change).

Do NOT add or attempt to add e2e coverage for `services/bot/handlers/join_game.py::handle_join_game` (the Discord "Join Game" button handler) at any point in this plan — Discord's platform provides no mechanism to simulate a component interaction from a test, so its unit test coverage (preserved by Phase 1 Task 1.3) is the correct and only automated verification available for it. See the note in Phase 1 Task 1.3's details.

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

For each bug-fix task (Phase 2 Task 2.1, Phase 3 Task 3.1), you WILL confirm the regression test shows as `xfailed` (not `failed`, not `passed`) before touching production code, per the Bug Fix Workflow in `.github/instructions/test-driven-development.instructions.md`.

Phase 4 is plain dead-code removal, not a bug fix — do NOT apply the xfail/TDD workflow to it. Task 4.1 requires re-running the "no production callers" grep to confirm it still holds before removing anything.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/changes/20260815-01-join-notification-scheduling-consolidation-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20260815-01-join-notification-scheduling-consolidation.plan.md`, `.copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md`, and `.copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
