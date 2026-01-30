---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Service Layer Transaction Management and Atomicity

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260130-service-layer-transaction-management-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260130-service-layer-transaction-management-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/coding-best-practices.instructions.md for code quality

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260130-service-layer-transaction-management-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260130-service-layer-transaction-management-plan.instructions.md](../plans/20260130-service-layer-transaction-management-plan.instructions.md), [.copilot-tracking/details/20260130-service-layer-transaction-management-details.md](../details/20260130-service-layer-transaction-management-details.md), and [.copilot-tracking/research/20260130-service-layer-transaction-management-research.md](../research/20260130-service-layer-transaction-management-research.md) documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-service-layer-transaction-management.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All 17 service layer commits removed
- [ ] Transaction atomicity restored for guild sync operations
- [ ] Transaction atomicity restored for game operations
- [ ] Transaction atomicity restored for participant operations
- [ ] All unit tests updated and passing
- [ ] Integration tests verify atomicity
- [ ] Rollback scenarios tested
- [ ] Documentation created
- [ ] Python coding conventions followed
- [ ] All modified code passes ruff linting
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
