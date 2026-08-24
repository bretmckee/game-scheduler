---
applyTo: '.copilot-tracking/changes/20260823-01-reminder-channel-post-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Move Game Reminders from DMs to Location Channel/Thread Posts (+ Host DM-Only Opt-Out)

## Overview

Deliver game reminders as a single post in the game's location channel/thread
(mentioning confirmed participants + host) when the location resolves to
exactly one channel, plus a DM to the first waitlisted participant, with the
existing full DM fan-out preserved as a fallback; then give hosts a per-game
"Always send reminders as DMs" checkbox (default off) that short-circuits the
channel path entirely.

## Objectives

- Post one reminder message in the location channel/thread when `where`
  contains exactly one `<#id>` token and the bot can access it
- Mention confirmed participants + host in the channel post (exclude waitlist)
- DM the first `_WAITLIST_REMINDER_COUNT` waitlisted participant in the
  channel-post success path
- Fall back to the existing full DM fan-out (confirmed + first waitlisted +
  host) when the location is empty/ambiguous or the channel post fails
  (`discord.Forbidden` / `discord.NotFound`)
- Rewrite the e2e reminder test to verify hybrid delivery (channel post +
  waitlist DM)
- Add a per-game `reminders_as_dms` boolean (default off, game-only — no
  template default) that short-circuits channel resolution so every reminder
  takes the full DM fan-out path
- Expose "Always send reminders as DMs" as a checkbox in the create/edit game
  forms; recurring clones carry the flag over

## Research Summary

### Project Files

- `services/bot/events/handlers.py` - reminder fan-out (`_handle_game_reminder`,
  `_send_participant_reminders`, `_send_host_reminder`, `_send_reminder_dm`,
  `_get_bot_channel`, `_WAITLIST_REMINDER_COUNT`); the delivery branch lands here
- `shared/utils/discord.py` - home for the new `extract_single_channel_id` helper
- `services/bot/formatters/game_message.py` - `create_notification_embed`
  (dead in production, adopted for the channel-post embed)
- `services/api/services/channel_resolver.py` - writes `<#id>` tokens into
  `games.where`; defines the token format the helper parses
- `tests/unit/services/bot/events/test_handlers_game_reminder.py` - six flow
  tests + four `_send_reminder_dm` tests to extend/verify
- `tests/unit/shared/utils/test_discord_utils.py` - unit tests for the new helper
- `tests/unit/services/bot/formatters/test_game_message.py` - embed tests to extend
- `tests/e2e/test_game_reminder.py` - e2e reminder test to rewrite
- `tests/e2e/helpers/discord.py` - e2e helper to extend with
  `wait_for_channel_message`
- `alembic/versions/<new_rev>_add_reminders_as_dms.py` - new migration for the
  host opt-out flag (down_revision `bf79aeffb6b0`)
- `shared/schemas/game.py` - create/update/response fields for
  `reminders_as_dms` (mirrors `remind_host_rewards`)
- `services/api/routes/games.py` + `services/api/services/games.py` - form
  params, `_build_game_session`, `_update_remaining_fields`, clone carry-over
- `shared/services/game_schedules.py` - recurrence clone carry-over
- `frontend/src/types/index.ts`, `GameForm.tsx`, `CreateGame.tsx`,
  `EditGame.tsx` - checkbox wiring (mirrors `remindHostRewards`)

### External References

- .copilot-tracking/research/20260823-01-reminder-channel-post-research.md -
  full research: file analysis, implementation patterns, complete examples,
  recommended hybrid approach
- Source: discordpy.readthedocs.io - `discord.TextChannel` is the base class of
  `discord.Thread`, so existing `isinstance(channel, discord.TextChannel)`
  guards already accept threads; `discord.Forbidden` on missing send permission

### Standards References

- .github/instructions/test-driven-development.instructions.md - TDD
  RED→GREEN→REFACTOR for all new production code
- .github/instructions/unit-tests.instructions.md - behavioral assertions on
  real arguments, no coverage theater
- .github/instructions/python.instructions.md - type hints, docstrings, Ruff
- .github/instructions/self-explanatory-code-commenting.instructions.md -
  comment only non-obvious WHY
- .github/instructions/test-execution.instructions.md - e2e runs need `tee`
  capture and ≥900000ms timeout

## Implementation Checklist

### [x] Phase 1: Location Channel Resolution Helper

- [x] Task 1.1: Add unit tests for `extract_single_channel_id` (RED)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 29-66)

- [x] Task 1.2: Implement `extract_single_channel_id` in `shared/utils/discord.py` (GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 67-117)

### [x] Phase 2: Channel-Post Reminder Delivery

- [x] Task 2.1: Extend `create_notification_embed` for optional host + jump link (RED→GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 120-159)

- [x] Task 2.2: Add unit tests for `_post_reminder_to_channel` and the `_handle_game_reminder` branch (RED)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 160-213)

- [x] Task 2.3: Implement `_post_reminder_to_channel` and wire the delivery branch (GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 214-337)

- [x] Task 2.4: Verify existing flow tests still pass via the fallback path
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 338-363)

### [x] Phase 3: E2E Test Rewrite

- [x] Task 3.1: Add `wait_for_channel_message` helper to `tests/e2e/helpers/discord.py`
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 366-425)

- [x] Task 3.2: Rewrite `test_game_reminder_dm_delivery` for hybrid delivery
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 426-466)

### [x] Phase 4: Backend "Always send reminders as DMs" Flag

- [x] Task 4.1: Migration + model column for `reminders_as_dms` (RED→GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 469-516)

- [x] Task 4.2: Schemas — create/update/response fields (RED→GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 517-553)

- [x] Task 4.3: API routes + service wiring with unit tests (RED→GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 554-614)

### [ ] Phase 5: Bot Short-Circuit for DM-Only Reminders

- [ ] Task 5.1: Unit tests for the flag short-circuit (RED)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 617-644)

- [ ] Task 5.2: Implement the short-circuit in `_deliver_game_reminders` (GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 645-689)

### [ ] Phase 6: Frontend Checkbox

- [ ] Task 6.1: Type, form state, checkbox, payloads (RED→GREEN)
  - Details: .copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md (Lines 692-757)

## Dependencies

- Python 3.x with `uv` (dependency + test runner)
- `discord.py` (existing) — `discord.TextChannel`, `discord.Forbidden`,
  `discord.NotFound`, `discord.AllowedMentions`
- `pytest` + `pytest-asyncio` (existing)
- E2E: full stack via `compose.e2e.yaml`, Discord test guild, notification
  daemon (existing e2e prerequisites)
- Alembic migrations (existing tooling; new migration chains from head
  `bf79aeffb6b0`)
- Frontend: React + MUI + vitest (existing) for the opt-out checkbox

## Success Criteria

- When `where` contains exactly one valid `<#id>` and the bot can access that
  channel/thread, exactly one reminder message is posted there mentioning
  confirmed participants + host, and the first `_WAITLIST_REMINDER_COUNT`
  waitlisted participant receives a reminder DM
- When `where` is empty/ambiguous or the channel is inaccessible, the existing
  full DM fan-out still occurs (confirmed + first waitlisted + host) — no
  regression
- `uv run pytest tests/unit` passes; `uv run mypy shared/ services/` passes
- The rewritten e2e reminder test passes with `tee`-captured output
- Extension: when `reminders_as_dms` is true on a game, every reminder takes
  the full DM fan-out path unconditionally — no channel lookup or post is
  attempted regardless of `where`; default-off changes nothing for existing
  games; recurring clones carry the flag over
- Extension: "Always send reminders as DMs" checkbox renders in create/edit
  forms, defaults unchecked, and round-trips through the API; frontend build
  and unit tests pass
