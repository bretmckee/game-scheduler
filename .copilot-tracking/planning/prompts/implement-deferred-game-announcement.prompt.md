---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Deferred Game Announcement

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260530-01-deferred-game-announcement-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement #file:../plans/20260530-01-deferred-game-announcement.plan.md task-by-task, following the TDD cycle (RED xfail → implement → GREEN) for every task that involves new production code.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow
- #file:../../.github/instructions/unit-tests.instructions.md for test quality and assertion standards
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for service/route patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/reactjs.instructions.md for Phase 5 frontend work
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for Phase 5 TypeScript

**Phase isolation is mandatory.** Each phase must leave the full unit test suite green before committing. Do NOT proceed to the next phase until `uv run pytest tests/unit` passes cleanly.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Key implementation notes

- **`clear_post_at` sentinel**: `GameUpdateRequest` uses a separate `clear_post_at: bool = False` field (not a null `post_at`) to distinguish "explicitly clear and announce now" from "leave post_at unchanged." This mirrors the `remove_thumbnail`/`remove_image` pattern in the update route. The `_parse_update_form_data` helper must be extended to accept and return this bool.
- **`_persist_and_publish` reload**: the immediate path reloads `game` via `get_game` between `_setup_game_schedules` and `_publish_game_created`. Preserve this reload in the conditional block for the immediate path; the deferred path skips both calls so no reload is needed.
- **`clone_game` is unaffected**: cloned games are constructed without `post_at`, so they fall through to the immediate path in `_persist_and_publish` without any change.
- **`AnnouncementLoop` selectinload**: the `_process_due` query must load the same relationships as `get_game` (guild, channel, host, participants, template) to avoid lazy-load errors when `_announce` calls `_create_game_announcement`. Mirror the `selectinload` chain from `GameService.get_game`.
- **`update_game` channel_config for clear path**: when `clear_post_at=True` triggers immediate announcement, `update_game` needs the `channel_config` to call `_publish_game_created`. Retrieve it the same way `create_game` does — via `game.channel`.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. Provide a markdown style link and a summary of all changes from #file:../changes/20260530-01-deferred-game-announcement-changes.md to the user:
   - Keep the overall summary brief
   - Add spacing around any lists
   - Wrap any reference to a file in a markdown style link

2. Provide markdown style links to:
   - [.copilot-tracking/planning/plans/20260530-01-deferred-game-announcement.plan.md](../plans/20260530-01-deferred-game-announcement.plan.md)
   - [.copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md](../details/20260530-01-deferred-game-announcement-details.md)
   - [.copilot-tracking/research/20260530-01-deferred-game-announcement-research.md](../research/20260530-01-deferred-game-announcement-research.md)

   Recommend cleaning up these tracking files once the work is merged.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified Python code has TDD unit tests; all new and modified TypeScript code has vitest tests
- [ ] Full unit test suite passes after each phase commit (`uv run pytest tests/unit`)
- [ ] Changes file updated continuously
