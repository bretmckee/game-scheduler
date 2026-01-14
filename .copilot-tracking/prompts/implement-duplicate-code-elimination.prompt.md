---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Duplicate Code Elimination

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260114-duplicate-code-elimination-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260114-duplicate-code-elimination-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/reactjs.instructions.md for all TypeScript code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/coding-best-practices.instructions.md for general coding standards

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

**IMPORTANT**: For each task that includes unit tests, you MUST create both the implementation AND the tests before considering the task complete.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260114-duplicate-code-elimination-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260114-duplicate-code-elimination-plan.instructions.md](.copilot-tracking/plans/20260114-duplicate-code-elimination-plan.instructions.md), [.copilot-tracking/details/20260114-duplicate-code-elimination-details.md](.copilot-tracking/details/20260114-duplicate-code-elimination-details.md), and [.copilot-tracking/research/20260114-duplicate-code-elimination-research.md](.copilot-tracking/research/20260114-duplicate-code-elimination-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete [.copilot-tracking/prompts/implement-duplicate-code-elimination.prompt.md](.copilot-tracking/prompts/implement-duplicate-code-elimination.prompt.md)

## Success Criteria

- [ ] Changes tracking file created
- [ ] Phase 1: Template response helper created with unit tests, all 4 endpoints refactored
- [ ] Phase 2: Discord API base method created with unit tests, 5 methods refactored
- [ ] Phase 3: Game embed helper created with unit tests, 2 commands refactored
- [ ] Phase 4: TypeScript types refactored, compilation verified
- [ ] Phase 5: Channel message helper created with unit tests, 2 handlers refactored
- [ ] Phase 6: Duplication verified < 2%, all tests pass, threshold updated
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint
- [ ] All existing tests still pass
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
