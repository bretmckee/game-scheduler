---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Incremental Redis Projection Updates

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260606-01-incremental-projection-updates-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260606-01-incremental-projection-updates.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD cycle (RED xfail → GREEN → remove xfail)
- #file:../../.github/instructions/unit-tests.instructions.md for assertion quality
- #file:../../.github/instructions/integration-tests.instructions.md for integration test conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**TDD NOTE — Phase 1 exception**: Phase 1 tests target `repopulate_all`, which is already implemented. Do NOT use the xfail cycle for Phase 1. Write the tests directly and confirm they pass.

**TDD NOTE — Phases 2–5**: Each new production function (`update_member`, `update_user`, `add_member`, `remove_member`, `on_guild_available`, and the `on_resumed` change) requires the full RED → GREEN cycle:

1. Write unit tests marked `@pytest.mark.xfail(strict=True, reason="not yet implemented")`
2. Run `uv run pytest tests/unit` to confirm failure (RED)
3. Implement the production code
4. Remove xfail markers
5. Run `uv run pytest tests/unit` to confirm all pass (GREEN)

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- `scripts/run-integration-tests.sh tests/integration/test_guild_projection_writes.py |& tee output-integration-phase.txt` — run after each phase that adds integration tests; follow #file:../../.github/instructions/test-execution.instructions.md for output capture rules

A phase is not done until all applicable gates are green.

**Phase boundary rule**: Each phase must leave the codebase in a committable state. In particular:

- Phase 2 removes the `on_member_update` test case from `TestMemberEventHandlers` **in the same phase** as changing the handler
- Phase 4 removes `TestMemberEventHandlers` and `TestSignalRepopulation` classes **in the same phase** as changing `on_member_add`/`on_member_remove`
- Phase 6 deletes `test_bot_member_event_worker.py` **in the same phase** as removing `_member_event_worker` and `_signal_repopulation`

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260606-01-incremental-projection-updates-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260606-01-incremental-projection-updates.plan.md, .copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md, and .copilot-tracking/research/20260606-01-incremental-projection-updates-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] All new integration tests in `test_guild_projection_writes.py` pass
- [ ] No existing integration tests regress
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
