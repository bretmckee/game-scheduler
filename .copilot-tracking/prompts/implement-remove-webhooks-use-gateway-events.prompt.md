---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Remove Discord Webhooks and Use Gateway Events

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260226-01-remove-webhooks-use-gateway-events-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260226-01-remove-webhooks-use-gateway-events.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD phases (Phases 3 and 4)
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for FastAPI patterns
- #file:../../.github/instructions/api-authorization.instructions.md for API authorization
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

**TDD PHASES REMINDER**:

- For Phases 3 and 4 (new functionality), you MUST follow Red-Green-Refactor:
  - RED: Create stub with NotImplementedError (or 501) and write tests with @pytest.mark.xfail expecting real behavior
  - GREEN: Implement functionality and remove xfail markers ONLY (do NOT modify test assertions)
  - REFACTOR: Improve code quality and add edge case tests

**DELETION PHASES**:

- Phases 1, 2, 5, and 6 are cleanup/deletion - no TDD needed, just remove code and update tests

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260226-01-remove-webhooks-use-gateway-events-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260226-01-remove-webhooks-use-gateway-events.plan.md, .copilot-tracking/details/20260226-01-remove-webhooks-use-gateway-events-details.md, and .copilot-tracking/research/20260226-01-remove-webhooks-use-gateway-events-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-remove-webhooks-use-gateway-events.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
- [ ] Webhook infrastructure completely removed
- [ ] Bot automatically syncs guilds on join
- [ ] GUI sync endpoint has rate limiting
- [ ] All tests pass
