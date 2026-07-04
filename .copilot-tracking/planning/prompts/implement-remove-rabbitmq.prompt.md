---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Remove RabbitMQ

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260704-01-remove-rabbitmq-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260704-01-remove-rabbitmq.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow (RED xfail -> GREEN remove xfail)
- #file:../../.github/instructions/unit-tests.instructions.md for test quality
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for API service patterns
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Docker cleanup
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - <description>

- <change bullet 1>
- <change bullet 2>

Rationale: <why this phase does what it does>
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- `cd frontend && npm run build` — TypeScript build (if any frontend files changed)
- `cd frontend && npm run test` — frontend tests (if any frontend files changed)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — if the phase writes or modifies integration tests; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — if the phase writes or modifies e2e tests; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules

A phase is not done until all applicable gates are green.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260704-01-remove-rabbitmq-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260704-01-remove-rabbitmq.plan.md, .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md, and .copilot-tracking/research/20260408-02-remove-rabbitmq-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Integration and e2e tests pass without `rabbitmq` container
- [ ] `shared/messaging/` deleted
- [ ] `services/retry/` deleted
- [ ] `grep -r "aio_pika|pika" services/ shared/` returns nothing
