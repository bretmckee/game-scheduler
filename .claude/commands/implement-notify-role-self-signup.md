---
description: 'Implement suppression of the notify_role_ids Discord ping for HOST_SELECTED games'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Suppress Notify-Role Ping for HOST_SELECTED Games

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260913-01-notify-role-self-signup-changes.md` in `.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260913-01-notify-role-self-signup.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the RED/GREEN cycle (Tasks 1.1/1.2) and the already-correct-code rule (Task 1.3)
- `.github/instructions/unit-tests.instructions.md` for falsifiable assertions and negative-assertion sibling-path coverage
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style
- `.github/instructions/integration-tests.instructions.md` and `.github/instructions/test-execution.instructions.md` for Task 1.4's e2e additions (always capture full output with `tee`; never run with `--testmon`)

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may tell you at the start of the session (or at any point) to run through multiple phases or tasks without stopping — follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - {{description, including feature context if non-obvious}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking the Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — Python type checking; mypy failures are build failures and equally block commits

Frontend gates do not apply — this change touches only `services/bot/formatters/game_message.py`, its unit test file, and `tests/e2e/test_signup_methods.py`. Integration test scripts do not apply. Task 1.4's e2e gate (`SKIP_STARTUP=1 SKIP_CLEANUP=1 ./scripts/run-e2e-tests.sh tests/e2e/test_signup_methods.py`, output captured with `tee`) is required before the phase is complete — do not skip it just because it is slower than the unit gates.

The phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When the Phase is checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/changes/20260913-01-notify-role-self-signup-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20260913-01-notify-role-self-signup.plan.md`, `.copilot-tracking/planning/details/20260913-01-notify-role-self-signup-details.md`, and `.copilot-tracking/research/20260913-01-notify-role-self-signup-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed, including TDD RED/GREEN for Tasks 1.1/1.2 and no xfail markers left in the suite
- [ ] All new and modified code passes lint and has unit tests
- [ ] Task 1.4's e2e additions pass against the real Discord test guild (`tests/e2e/test_signup_methods.py`)
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
