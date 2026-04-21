---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Bot REST API Elimination

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260421-02-bot-rest-api-elimination-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260421-02-bot-rest-api-elimination.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow (update tests first for modifications; stub + xfail for new functions in Phase 4)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/quality-check-overrides.instructions.md — no lint suppressions or pre-commit bypasses without explicit user approval

**Phase dependency rules:**

- Phases 1–3 (role_checker, handlers) are independent and may be done in any order
- Phase 4 must complete before Phase 5 Tasks 5.1 and 5.2 (new sync functions must exist before bot.py references them)
- Phase 5 Task 5.3 (`_run_sweep_worker`) is independent of Tasks 5.1 and 5.2

**TDD rules by phase:**

- Phases 1–3 and 5: modifying existing code — update test assertions first to reflect new behavior, confirm the updated tests fail against current code (RED), then fix production code (GREEN)
- Phase 4: new production functions — create stubs raising `NotImplementedError`, write `xfail` tests, confirm `xfailed`, implement, remove `xfail` markers

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260421-02-bot-rest-api-elimination-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260421-02-bot-rest-api-elimination.plan.md, .copilot-tracking/planning/details/20260421-02-bot-rest-api-elimination-details.md, and .copilot-tracking/research/20260421-02-bot-rest-api-elimination-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] TDD followed: tests updated/written first, RED confirmed before GREEN for every task
- [ ] No `fetch_member`, `fetch_user`, `discord_api.fetch_user`, or `fetch_channel` (non-message) calls remain in role_checker.py, handlers.py, or bot.py
- [ ] `sync_all_bot_guilds` removed from setup_hook and on_guild_join call paths
- [ ] All unit test suites pass with no skips
- [ ] Changes file updated continuously
