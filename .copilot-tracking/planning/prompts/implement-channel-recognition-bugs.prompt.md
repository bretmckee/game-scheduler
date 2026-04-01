---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Channel Recognition Bug Fixes

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260401-01-channel-recognition-bugs-changes.md` in
#file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement each task in
#file:../plans/20260401-01-channel-recognition-bugs.plan.md

You WILL follow TDD discipline for all Python and TypeScript changes:

- For each bug fix or new behavior, write the `xfail` test first and confirm it
  shows as `xfailed` before implementing the fix
- Remove the `xfail` marker only after the fix makes the test pass
- See #file:../../.github/instructions/test-driven-development.instructions.md

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/reactjs.instructions.md for React components
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260401-01-channel-recognition-bugs-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   .copilot-tracking/planning/plans/20260401-01-channel-recognition-bugs.plan.md,
   .copilot-tracking/planning/details/20260401-01-channel-recognition-bugs-details.md,
   and .copilot-tracking/research/20260401-01-channel-recognition-bugs-research.md
   and recommend cleaning these files up.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] TDD xfail markers written before each fix and removed after
- [ ] `#🍻tavern-generalchat` resolves correctly at create and edit time
- [ ] `<#406497579061215235>` silently accepted when the ID is valid in the guild
- [ ] Suggestion chip click updates the Location field value (Bug 3 fixed)
- [ ] `GameCard` and `GameDetails` display human-readable channel names
- [ ] Edit form pre-populates Location with the human-readable channel name
- [ ] All new and modified code passes lint and unit tests
- [ ] Changes file updated continuously
