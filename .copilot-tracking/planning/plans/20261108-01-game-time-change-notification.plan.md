---
applyTo: '.copilot-tracking/planning/changes/20261108-01-game-time-change-notification-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Notify participants when a game's details change

## Overview

Send one DM per edit to every confirmed and waitlisted participant when a host changes an announced game's time, expected duration, location or signup instructions.

## Objectives

- Changing `scheduled_at`, `expected_duration_minutes`, `where` or `signup_instructions` on an announced game enqueues exactly one `send_dm` per participant, listing each change old -> new
- No-op saves, unannounced games and edits to excluded fields enqueue no DM
- docs/PLAYER-GUIDE.md describes the shipped behavior

## Research Summary

### Project Files

- services/api/services/games.py - `update_game` (L2122), `_capture_old_state` (L1891), `_update_game_fields` (L1403)
- shared/services/waitlist_transitions.py - `send_dm` enqueue pattern and `_build_jump_url`
- shared/message_formats.py - `DMFormats` DM text builders
- tests/unit/shared/services/test_waitlist_transitions.py - unit test pattern
- tests/integration/test_leave_game_promotion.py - integration test pattern via API + `bot_action_queue`
- tests/e2e/test_waitlist_promotion.py, tests/e2e/test_game_update.py, tests/e2e/helpers/discord.py - e2e DM delivery pattern (`DMType`, `wait_for_recent_dm`)
- docs/PLAYER-GUIDE.md - "Game Updates" and "What if the game time changes?" sections

### External References

- #file:../../research/20261108-01-game-time-change-notification-research.md - root cause, decided notify fields, docs requirements

### Standards References

- #file:../../../.github/instructions/python.instructions.md - Python conventions
- #file:../../../.github/instructions/test-driven-development.instructions.md - RED/GREEN with strict xfail; bug-fix workflow
- #file:../../../.github/instructions/unit-tests.instructions.md - assertion quality
- #file:../../../.github/instructions/fastapi-transaction-patterns.instructions.md - service layer does not commit
- #file:../../../.github/instructions/integration-tests.instructions.md - integration tests

## Implementation Checklist

### [x] Phase 1: Change-notification helper and DM format (TDD)

- [x] Task 1.1: Create stubs for `GameNotifySnapshot`, `capture_notify_snapshot`, `notify_participants_of_changes` and `DMFormats.game_updated`
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 11-32)

- [x] Task 1.2: Write xfail unit tests with real assertions
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 33-59)

- [x] Task 1.3: Implement helper and format; remove xfail markers
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 60-79)

### [ ] Phase 2: Wire the helper into `update_game` (TDD bug fix)

- [ ] Task 2.1: Write xfail regression tests for `GameService.update_game`
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 82-102)

- [ ] Task 2.2: Call the helper from `update_game`; remove xfail markers
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 103-121)

### [ ] Phase 3: Integration test through the API and bot queue

- [ ] Task 3.1: Add integration test (retrofit; no xfail)
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 124-140)

### [ ] Phase 4: E2E test of DM delivery through the bot

- [ ] Task 4.1: Add the `game_updated` DM predicate and e2e `DMType`
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 143-159)

- [ ] Task 4.2: Add e2e test for the change DM (retrofit; no xfail)
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 160-180)

### [ ] Phase 5: Update the player guide

- [ ] Task 5.1: Describe the shipped behavior in docs/PLAYER-GUIDE.md
  - Details: .copilot-tracking/planning/details/20261108-01-game-time-change-notification-details.md (Lines 183-197)

## Dependencies

- Existing `send_dm` handler in services/bot/bot_action_listener.py (no bot changes)
- `uv`, pytest, mypy, `scripts/run-integration-tests.sh`, `scripts/run-e2e-tests.sh` (Discord test guild and users)

## Success Criteria

- Every phase passes `uv run pytest tests/unit` and `uv run mypy shared/ services/`; Phase 3 also passes integration tests; Phase 4 also passes e2e tests
- Exactly one `game_updated` DM per participant per qualifying edit; none for no-op, unannounced or excluded-field edits
- A real participant receives the change DM in Discord with old and new times and the game link
- All five phases land in one PR so the guide never ships ahead of the code
