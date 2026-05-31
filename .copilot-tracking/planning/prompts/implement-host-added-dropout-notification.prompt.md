---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Host Notification When HOST_ADDED Player Drops Out

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260531-01-host-added-dropout-notification-changes.md` in
#file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement
#file:../plans/20260531-01-host-added-dropout-notification.plan.md task-by-task

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/unit-tests.instructions.md for unit test quality
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for API service patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- `cd frontend && npm run build` — TypeScript build (if any frontend files changed)
- `cd frontend && npm run test` — frontend tests (if any frontend files changed)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — if the phase writes or modifies integration tests; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — if the phase writes or modifies e2e tests; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules

A phase is not done until all applicable gates are green.

**TDD reminder**: Each RED phase (Phases 1, 3, 5) ends with xfail tests committed and all gates
green. Each GREEN phase (Phases 2, 4, 6) ends with xfail markers removed and all tests passing.
Phase 7 retrofits e2e coverage for already-implemented code — no xfail needed.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260531-01-host-added-dropout-notification-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   .copilot-tracking/planning/plans/20260531-01-host-added-dropout-notification.plan.md,
   .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md,
   and .copilot-tracking/research/20260531-01-host-added-dropout-notification-research.md
   documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
