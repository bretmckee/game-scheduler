---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Mention and Emoji Resolution Test Coverage

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260530-01-mention-emoji-test-coverage-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260530-01-mention-emoji-test-coverage.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD rules; all tests here retrofit already-correct production code, so no stubs and no xfail markers
- #file:../../.github/instructions/unit-tests.instructions.md — test quality standards (real assertions, no coverage theater)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify the full unit test suite passes. A phase is not done until tests are green.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260530-01-mention-emoji-test-coverage-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260530-01-mention-emoji-test-coverage.plan.md, .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md, and .copilot-tracking/research/20260530-01-mention-emoji-test-coverage-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] `tests/integration/test_games_field_display.py` created with 3 passing tests (emoji round-trip, channel mention, user mention)
- [ ] `tests/e2e/test_channel_mentions.py` augmented with description field and `embed.description` assertions
- [ ] `tests/e2e/test_join_notification.py` augmented with channel mention and optional emoji in signup_instructions
- [ ] `config.template/env.template` updated with `DISCORD_TEST_EMOJI_NAME` commented-out entry
- [ ] `compose.e2e.yaml` updated with `DISCORD_TEST_EMOJI_NAME: ${DISCORD_TEST_EMOJI_NAME:-}`
- [ ] `docs/developer/TESTING.md` updated with Custom Emoji E2E Testing section
- [ ] All new and modified code passes lint
- [ ] Changes file updated continuously
