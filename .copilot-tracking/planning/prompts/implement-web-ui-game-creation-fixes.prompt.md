---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Web UI Game Creation Fixes

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260529-01-web-ui-game-creation-fixes-changes.md` in
#file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement
#file:../plans/20260529-01-web-ui-game-creation-fixes.plan.md task-by-task.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow
- #file:../../.github/instructions/unit-tests.instructions.md for assertion quality
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify the full unit test suite passes. A phase is not done until tests are green.

### Implementation Notes

- **Phase 1** (GIF fix) has no dependencies on other phases and is the lowest-risk
  starting point. Complete it first and verify tests are green before proceeding.
- **Phase 2** (integer passthrough) is also low-risk and independent. It can be done
  before or after Phase 3.
- **Phase 3** (@mentions in text) depends on `ParticipantResolver` already existing.
  No infrastructure changes required.
- **Phase 4** (emoji resolution) is the most complex. Complete Tasks 4.1 → 4.2 → 4.3 →
  4.4 → 4.5 in strict order; each task depends on the previous.
- **Phase 5** (docs) is a markdown-only update with no code. No TDD applies.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260529-01-web-ui-game-creation-fixes-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to:
   - .copilot-tracking/planning/plans/20260529-01-web-ui-game-creation-fixes.plan.md
   - .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md
   - .copilot-tracking/research/20260529-01-web-ui-game-creation-fixes-research.md

   You WILL recommend cleaning these files up after the implementation is verified.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified Python code follows TDD (RED → xfail → GREEN → REFACTOR)
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously throughout implementation
- [ ] Line numbers updated if any referenced files changed
