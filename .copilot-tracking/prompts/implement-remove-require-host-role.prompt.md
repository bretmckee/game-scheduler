---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Remove `require_host_role` Field

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260301-03-remove-require-host-role-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260301-03-remove-require-host-role.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**Note on TDD**: This task is a pure removal. There are no new behaviors to develop or test. TDD phases are skipped. After removing code, run the existing test suite to confirm nothing is broken and that removed mock attributes do not cause `AttributeError` failures.

**Critical note on mocks**: After removing `require_host_role` from the ORM model, any test mock object that sets `mock.require_host_role = ...` will silently pass (MagicMock accepts arbitrary attribute assignment) but the attribute will never appear in serialized responses. Verify that no test assertion expects `require_host_role` in a response dict or Pydantic model after cleanup.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260301-03-remove-require-host-role-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260301-03-remove-require-host-role.plan.md, .copilot-tracking/details/20260301-03-remove-require-host-role-details.md, and .copilot-tracking/research/20260301-03-remove-require-host-role-research.md. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-remove-require-host-role.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented
- [ ] `grep -r "require_host_role" services/ shared/ tests/ frontend/src/ docs/` returns no results
- [ ] `uv run pytest tests/` passes
- [ ] `cd frontend && npm test` passes
- [ ] `uv run alembic upgrade head` applies cleanly
- [ ] Changes file updated continuously
