---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Ruff Linting Rules Expansion

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260125-ruff-rules-expansion-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260125-ruff-rules-expansion-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL WORKFLOW**: For each Phase and Task:
1. Run `ruff check --select <RULES> --exclude tests` to identify violations
2. Fix ALL violations for the rule category (zero tolerance)
3. Verify zero violations: `ruff check --select <RULES> --exclude tests` must return clean
4. Update pyproject.toml to enable the rules in select list
5. Run full test suite to ensure no regressions
6. Commit the changes with descriptive message
7. ONLY THEN proceed to next task

**IMPLEMENTATION PATTERN**: Fix violations FIRST, enable rules SECOND. Never enable rules with existing violations.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260125-ruff-rules-expansion-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260125-ruff-rules-expansion-plan.instructions.md](.copilot-tracking/plans/20260125-ruff-rules-expansion-plan.instructions.md), [.copilot-tracking/details/20260125-ruff-rules-expansion-details.md](.copilot-tracking/details/20260125-ruff-rules-expansion-details.md), and [.copilot-tracking/research/20260125-ruff-rules-expansion-research.md](.copilot-tracking/research/20260125-ruff-rules-expansion-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-ruff-rules-expansion.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan phases implemented with zero violations per rule category
- [ ] Each rule category enabled in pyproject.toml only after achieving zero violations
- [ ] Project conventions followed
- [ ] Full test suite passes after each phase
- [ ] pyproject.toml updated incrementally with each phase
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
