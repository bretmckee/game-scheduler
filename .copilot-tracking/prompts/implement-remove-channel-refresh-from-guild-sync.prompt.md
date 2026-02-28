---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Remove Channel Refresh from Guild Sync

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260228-01-remove-channel-refresh-from-guild-sync-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260228-01-remove-channel-refresh-from-guild-sync.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/quality-check-overrides.instructions.md before suppressing any lint or test check

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260228-01-remove-channel-refresh-from-guild-sync-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260228-01-remove-channel-refresh-from-guild-sync.plan.md, .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md, and .copilot-tracking/research/20260228-01-remove-channel-refresh-from-guild-sync-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-remove-channel-refresh-from-guild-sync.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] `sync_all_bot_guilds` no longer calls `_refresh_guild_channels`
- [ ] `updated_channels` removed from schema, route handler, frontend interface, and frontend UI
- [ ] All Python unit tests pass: `uv run pytest tests/services/bot/test_guild_sync.py tests/services/api/routes/test_guilds.py`
- [ ] All frontend unit tests pass: `npm run test` inside `frontend/`
- [ ] `grep -r updated_channels services/ shared/ frontend/src tests/` returns no results
- [ ] Changes file updated continuously
