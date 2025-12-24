---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Magic Number Lint Rule Remediation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20251224-magic-number-lint-remediation-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20251224-magic-number-lint-remediation-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for all TypeScript code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/coding-best-practices.instructions.md for code quality

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20251224-magic-number-lint-remediation-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20251224-magic-number-lint-remediation-plan.instructions.md, .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md, and .copilot-tracking/research/20251224-magic-number-lint-remediation-research.md documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-magic-number-lint-remediation.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] PLR2004 and @typescript-eslint/no-magic-numbers rules enabled
- [ ] http-status-codes npm package installed
- [ ] All Python HTTP status codes use starlette.status constants
- [ ] All TypeScript HTTP status codes use StatusCodes from http-status-codes
- [ ] Four new constant files created (security_constants.py, pagination.py, ui.ts, time.ts)
- [ ] All magic numbers replaced with named constants
- [ ] Zero linter violations for magic numbers (both Python and TypeScript)
- [ ] All tests pass without regressions
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
