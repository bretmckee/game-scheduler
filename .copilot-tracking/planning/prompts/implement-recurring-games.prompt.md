---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Recurring Games

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260615-01-recurring-games-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement
#file:../plans/20260615-01-recurring-games.plan.md task-by-task

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/unit-tests.instructions.md for unit test quality
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for API service patterns
- #file:../../.github/instructions/reactjs.instructions.md for React component code
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript code
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

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

**TDD reminder**:

- Phases 2 and 4 and 6 end with xfail tests committed and all gates green (RED phases)
- Phases 3, 5, and 7 end with xfail markers removed and all tests passing (GREEN phases)
- Phase 1 and Phases 8–10 land implementation + tests together (no xfail needed — retrofitting or schema-only work)

**Zombie-prevention reminder** (Phase 7, Task 7.2):
The zombie check belongs INSIDE the DB session block in `_handle_status_transition_due`, before calling `_transition_game_status`. The discriminator is `game.message_id is None AND game.recur_rule is not None`. Regular games without `recur_rule` are never affected regardless of `message_id`.

**`post_at=None` sentinel reminder** (Phase 5, Task 5.1):
`_system_clone_for_recurrence` must set `post_at=None`. The announcement loop filters on `post_at IS NOT NULL`, so clones with `post_at=None` are structurally invisible to it — no race condition is possible and no changes to `AnnouncementLoop` are needed.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260615-01-recurring-games-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   .copilot-tracking/planning/plans/20260615-01-recurring-games.plan.md,
   .copilot-tracking/planning/details/20260615-01-recurring-games-details.md,
   and .copilot-tracking/research/20260615-01-recurring-games-research.md
   documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified Python code passes mypy and has unit tests
- [ ] All new React/TypeScript code passes `npm run build` and has Vitest tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
