---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Discord REST Elimination — Phase 2

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260422-01-discord-rest-elimination-phase2-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260422-01-discord-rest-elimination-phase2.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow (RED → GREEN for each task pair)
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for API route changes

**TDD CRITICAL**: Every Python and TypeScript change follows the RED→GREEN cycle. Write the `xfail` test first, confirm it shows as XFAIL, then implement. Remove the `xfail` marker only after the test passes.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260422-01-discord-rest-elimination-phase2-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260422-01-discord-rest-elimination-phase2.plan.md, .copilot-tracking/planning/details/20260422-01-discord-rest-elimination-phase2-details.md, and .copilot-tracking/research/20260422-01-discord-rest-elimination-phase2-research.md documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] `grep -r "oauth2.get_user_guilds" services/` returns no results outside `services/api/auth/oauth2.py`
- [ ] `grep -r "bot.fetch_user" services/bot/` returns no results
- [ ] `POST /api/v1/guilds/sync` returns 404
- [ ] `UserInfoResponse` has no `guilds` field; `CurrentUser` has no `guilds` field
- [ ] `discord_format` member lookup makes no `DiscordAPIClient` calls
- [ ] All unit test suites pass with zero skips
- [ ] Changes file updated continuously throughout implementation
