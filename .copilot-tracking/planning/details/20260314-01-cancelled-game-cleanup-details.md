<!-- markdownlint-disable-file -->

# Task Details: Cancelled Game Cleanup

## Research Reference

**Source Research**: #file:../research/20260314-01-cancelled-game-cleanup-research.md

## Phase 1: Update `delete_game()` in API service

### Task 1.1: Write integration tests for new `delete_game()` behaviour (xfail — RED)

Write integration tests that verify after `delete_game()` completes: the game row no
longer exists in the DB, and image reference counts are decremented correctly.
Mark all new assertions with `@pytest.mark.xfail(strict=True, reason="not yet implemented")`.

- **Files**:
  - `tests/integration/services/api/services/test_games_service.py` — Add test cases asserting game row absent
- **Success**:
  - New tests are collected by pytest and marked xfail
  - Tests fail as expected (current code sets status=CANCELLED, does not delete row)
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 100-116) — Test changes and implementation guidance
- **Dependencies**:
  - Research validation complete

### Task 1.2: Implement `delete_game()` changes and remove xfail markers (GREEN)

Modify `services/api/services/games.py` `delete_game()`:

1. Capture `message_id = game.message_id` and `channel_id = game.channel.channel_id` before any mutations
2. Keep `release_image()` calls unchanged — must precede deletion
3. Remove the manual `GameStatusSchedule` deletion loop (CASCADE handles it)
4. Replace `game.status = CANCELLED` and the subsequent reload with `await self.db.delete(game)`
5. Keep `_publish_game_cancelled()` call unchanged — payload shape is already correct
6. Remove `@pytest.mark.xfail` from the tests added in Task 1.1

- **Files**:
  - `services/api/services/games.py` — Modify `delete_game()` (currently at line 1712)
  - `tests/integration/services/api/services/test_games_service.py` — Remove xfail markers
- **Success**:
  - All Task 1.1 tests pass green without xfail
  - `test_delete_game_releases_images` integration test continues to pass unchanged
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 80-97) — Recommended API approach
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Add edge case tests and verify image reference counts

Add integration tests for corner cases:

- Game with no images (`thumbnail_id` and `banner_image_id` are None) — must not error
- Game with a shared image (`reference_count > 1` after release) — image row must persist
- Verify that related rows (participants, schedules) are gone after deletion

- **Files**:
  - `tests/integration/services/api/services/test_games_service.py` — Additional edge case tests
- **Success**:
  - All edge case tests pass green (no xfail needed — written post-GREEN)
  - No regressions in existing integration tests
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 41-73) — Key Discoveries (cascade chain, image reference counting)
- **Dependencies**:
  - Task 1.2 complete

## Phase 2: Update `_handle_game_cancelled()` in bot

### Task 2.1: Write unit tests for message deletion behaviour (xfail — RED)

Write unit tests in the bot handler test file that verify:

- `_handle_game_cancelled()` calls `message.delete()` (not `message.edit()`)
- The handler does NOT attempt a DB fetch of the game row

Mark all assertions with `@pytest.mark.xfail(strict=True, reason="not yet implemented")`.

- **Files**:
  - `tests/services/bot/events/test_handlers.py` — Add tests for new handler behaviour
- **Success**:
  - New tests are collected by pytest and fail as xfail (current code calls `message.edit`)
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 13-18) — `_handle_game_cancelled()` current behaviour
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Implement `_handle_game_cancelled()` changes and remove xfail markers (GREEN)

Modify `services/bot/events/handlers.py` `_handle_game_cancelled()`:

1. Remove the DB fetch of the game (row no longer exists post-cancel)
2. Use `message_id` and `channel_id` from the event payload directly to retrieve the Discord message
3. Call `await message.delete()` instead of `await message.edit(...)`
4. Remove `@pytest.mark.xfail` from Task 2.1 tests

- **Files**:
  - `services/bot/events/handlers.py` — Modify `_handle_game_cancelled()` (currently at line 1119)
  - `tests/services/bot/events/test_handlers.py` — Remove xfail markers
- **Success**:
  - All Task 2.1 tests pass green
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 86-93) — Recommended bot changes
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Add `discord.NotFound` edge case test and verify

Add a unit test for graceful handling when the Discord message is already deleted:

- Mock `message.delete()` to raise `discord.NotFound`
- Assert the handler does not re-raise the exception and completes gracefully

- **Files**:
  - `tests/services/bot/events/test_handlers.py` — Add `NotFound` edge case test
- **Success**:
  - `discord.NotFound` is caught and handled gracefully; no exception propagates to the caller
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 86-93) — "Handle `discord.NotFound` gracefully"
- **Dependencies**:
  - Task 2.2 complete

## Phase 3: Update E2E test assertions

### Task 3.1: Update `test_game_cancellation.py` to match new behaviour

Modify `tests/e2e/test_game_cancellation.py`:

1. Replace `assert game.status == "CANCELLED"` with an assertion that the game row is absent from the DB
2. Replace the assertion that the embed footer contains "cancelled" with an assertion that the Discord message no longer exists

- **Files**:
  - `tests/e2e/test_game_cancellation.py` — Update both existing assertions
- **Success**:
  - E2E test passes end-to-end with the new behaviour (game absent, message deleted)
- **Research References**:
  - #file:../research/20260314-01-cancelled-game-cleanup-research.md (Lines 100-107) — E2E test changes
- **Dependencies**:
  - Phase 1 and Phase 2 complete

## Dependencies

- SQLAlchemy `db.delete()` session API
- `discord.py` `Message.delete()` and `discord.NotFound`

## Success Criteria

- `DELETE /api/v1/games/{id}` returns 204 and game row is absent from DB
- Discord announcement message is deleted on cancellation
- Image reference counts correctly decremented; orphaned images deleted
- All existing integration and unit tests pass
- E2E cancellation test passes with updated assertions
