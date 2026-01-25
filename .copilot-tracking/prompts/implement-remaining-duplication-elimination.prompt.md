---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Remaining Code Duplication Elimination

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260125-remaining-duplication-elimination-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260125-remaining-duplication-elimination-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/coding-best-practices.instructions.md for refactoring patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**:
- For each "extract..." task, you MUST create unit tests alongside the helper function
- Unit tests MUST be created in the appropriate test directory matching the source file location
- All unit tests MUST pass before marking a task complete
- Use pytest fixtures and mocking as needed for isolated unit tests
- Ensure test coverage for success cases, edge cases, and error conditions

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Verification

After each phase, you WILL:
1. Run all affected tests to ensure no regressions
2. Run jscpd to verify duplication reduction
3. Update changes file with test results and duplication metrics

### Step 4: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL run jscpd and compare final clone count to baseline (22 clones)
2. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260125-remaining-duplication-elimination-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link
   - You WILL include before/after duplication metrics

3. You WILL provide markdown style links to [.copilot-tracking/plans/20260125-remaining-duplication-elimination-plan.instructions.md](.copilot-tracking/plans/20260125-remaining-duplication-elimination-plan.instructions.md), [.copilot-tracking/details/20260125-remaining-duplication-elimination-details.md](.copilot-tracking/details/20260125-remaining-duplication-elimination-details.md), and [.copilot-tracking/research/20260125-remaining-code-duplication-analysis-research.md](.copilot-tracking/research/20260125-remaining-code-duplication-analysis-research.md) documents. You WILL recommend cleaning these files up as well.

4. **MANDATORY**: You WILL attempt to delete [.copilot-tracking/prompts/implement-remaining-duplication-elimination.prompt.md](.copilot-tracking/prompts/implement-remaining-duplication-elimination.prompt.md)

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All new helper functions have comprehensive unit tests
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] All existing tests continue to pass
- [ ] Code duplication reduced from 22 to 11 or fewer clone pairs
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
