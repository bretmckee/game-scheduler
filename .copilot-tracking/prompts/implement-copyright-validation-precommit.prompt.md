---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Pre-commit Copyright Validation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create [20260215-01-copyright-validation-precommit-changes.md](.copilot-tracking/changes/20260215-01-copyright-validation-precommit-changes.md) in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260215-01-copyright-validation-precommit.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for Python TDD implementation (Phase 3 only)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/quality-check-overrides.instructions.md for quality standards

**CRITICAL**: Shell scripts (Phases 2 and 4) do NOT follow TDD methodology - implement directly
**CRITICAL**: Python script (Phase 3) MUST follow TDD: stub → failing tests (defining expected behavior) → implementation (tests pass) → refactor
**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from [20260215-01-copyright-validation-precommit-changes.md](.copilot-tracking/changes/20260215-01-copyright-validation-precommit-changes.md) to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [20260215-01-copyright-validation-precommit.plan.md](.copilot-tracking/plans/20260215-01-copyright-validation-precommit.plan.md), [20260215-01-copyright-validation-precommit-details.md](.copilot-tracking/details/20260215-01-copyright-validation-precommit-details.md), and [20260215-01-copyright-validation-precommit-research.md](.copilot-tracking/research/20260215-01-copyright-validation-precommit-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete [implement-copyright-validation-precommit.prompt.md](.copilot-tracking/prompts/implement-copyright-validation-precommit.prompt.md)

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] Python code follows TDD methodology with passing tests
- [ ] Shell scripts implemented without TDD methodology
- [ ] All new and modified Python code passes lint and has unit tests
- [ ] Pre-commit hook successfully validates copyright headers
- [ ] Integration tests confirm correct behavior for all scenarios
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
