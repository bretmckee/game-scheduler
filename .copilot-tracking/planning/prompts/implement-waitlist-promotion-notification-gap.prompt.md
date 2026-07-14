---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Waitlist Promotion DM on Leave

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260714-01-waitlist-promotion-notification-gap-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260714-01-waitlist-promotion-notification-gap.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for the RED-GREEN-REFACTOR cycle in Phases 1 and 3, and the xfail-regression workflow in Phases 4 and 5
- #file:../../.github/instructions/unit-tests.instructions.md for falsifiable, non-theater test assertions
- #file:../../.github/instructions/integration-tests.instructions.md for the real-DB integration tests in Phases 2, 4, and 5
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for transaction/commit boundaries
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
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
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — Phases 2, 4, and 5 write/modify integration tests; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — Phase 6 writes an e2e test; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

**Testmon note**: never run `pytest --testmon`/`--testmon-nocollect` manually — it corrupts `.testmondata` for the pre-commit hook. Use `uv run pytest tests/unit` (no `--testmon`).

**Phase-specific reminders**:

- Phase 1 and Phase 3 create brand-new functions: stub with `NotImplementedError` first, write tests with real assertions marked `xfail(strict=True)`, confirm they show as `xfailed`, then implement and remove only the `xfail` markers (never change the assertions).
- Phase 2 is a behavior-preserving refactor of already-correct code — no `xfail` cycle; just verify existing tests still pass.
- Phase 4 and Phase 5 are bug fixes to existing functions — no stub, but a regression test marked `xfail(strict=True)` that must be confirmed as `xfailed` before the fix lands, per the "TDD for Bug Fixes" workflow.
- Phase 5 also requires updating two already-passing host-added-dropout tests whose expected delivery mechanism intentionally changes (direct `discord.Client.send()` → `BotActionQueue`) — this is a deliberate behavior change called out in the plan, not a regression to avoid.
- Phase 6 is e2e coverage for already-implemented behavior — no `xfail`, write the assertion and run it immediately.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260714-01-waitlist-promotion-notification-gap-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260714-01-waitlist-promotion-notification-gap.plan.md, .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md, and .copilot-tracking/research/20260714-01-waitlist-promotion-notification-gap-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
