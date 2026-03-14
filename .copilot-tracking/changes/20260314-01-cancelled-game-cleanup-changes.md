<!-- markdownlint-disable-file -->

# Change Record: Cancelled Game Cleanup

**Plan**: `.copilot-tracking/planning/plans/20260314-01-cancelled-game-cleanup.plan.md`
**Details**: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md`
**Date**: 2026-03-14

## Summary

Delete the game row from the database on cancellation and delete the Discord
announcement message instead of editing it.

## Added

- `tests/integration/services/api/services/test_game_image_integration.py` — Added `test_delete_game_removes_row_from_db` and `test_delete_game_cascades_participants_gone` asserting game row and participant rows are absent after `delete_game()` (Task 1.1 RED → Task 1.2 GREEN)
- `tests/integration/services/api/services/test_game_image_integration.py` — Added `test_delete_game_no_images_succeeds`, `test_delete_game_shared_image_persists`, and `test_delete_game_status_schedules_removed` edge case tests (Task 1.3)
- `tests/unit/services/bot/events/test_handlers.py` — Added `test_handle_game_cancelled_calls_message_delete` and `test_handle_game_cancelled_does_not_fetch_game_from_db` (Task 2.1 RED → Task 2.2 GREEN)
- `tests/unit/services/bot/events/test_handlers.py` — Added `test_handle_game_cancelled_not_found_handled_gracefully` for `discord.NotFound` edge case (Task 2.3)

## Modified

- `services/api/services/games.py` — Replaced `game.status = CANCELLED` + schedule-loop with `await self.db.delete(game)`; removed redundant manual `GameStatusSchedule` deletion loop (Task 1.2)
- `services/bot/events/handlers.py` — Replaced DB fetch + `message.edit()` in `_handle_game_cancelled()` with direct `message.delete()` and `discord.NotFound` guard; removed `get_db_session` usage from this handler (Task 2.2)
- `tests/unit/services/api/services/test_games.py` — Updated `test_delete_game_success` to assert `db.delete()` called instead of `status == CANCELLED` (Task 1.2)
- `tests/unit/services/bot/events/test_handlers.py` — Updated `test_handle_game_cancelled_success`, `test_handle_game_cancelled_game_not_found`, `test_handle_game_cancelled_channel_invalid`, `test_handle_game_cancelled_handles_exception` to match new delete-based behaviour (Task 2.2)
- `tests/integration/services/api/services/test_game_image_integration.py` — Added `GameSession`, `GameParticipant`, and `GameStatusSchedule` imports (Tasks 1.1, 1.3)
- `tests/e2e/test_game_cancellation.py` — Replaced `status == CANCELLED` DB assertion with game row absent check; replaced Discord embed footer assertion with `wait_for_message_deleted`; removed unused `discord` import (Task 3.1)

## Removed
