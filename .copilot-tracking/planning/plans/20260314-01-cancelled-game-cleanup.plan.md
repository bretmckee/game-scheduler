---
applyTo: '.copilot-tracking/changes/20260314-01-cancelled-game-cleanup-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Cancelled Game Cleanup

## Overview

Delete the game row from the database on cancellation and delete the Discord
announcement message instead of editing it.

## Objectives

- Replace the status-set pattern in `delete_game()` with an actual DB row deletion
- Remove redundant manual cascade loop (DB handles via FK CASCADE)
- Delete the Discord announcement message in `_handle_game_cancelled()` instead of editing it
- Update E2E test assertions to reflect new behaviour

## Research Summary

### Project Files

- `services/api/services/games.py` — `delete_game()` at line 1712; `_publish_game_cancelled()` at line 2019
- `services/bot/events/handlers.py` — `_handle_game_cancelled()` at line 1119
- `tests/e2e/test_game_cancellation.py` — Assertions to update
- `tests/integration/services/api/services/test_game_image_integration.py` — Passes unchanged

### External References

- #file:../research/20260314-01-cancelled-game-cleanup-research.md — Full research notes

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md — Service/transaction patterns

## Implementation Checklist

### [x] Phase 1: Update `delete_game()` in API service

- [x] Task 1.1: Write integration tests asserting game row absent from DB after cancel (xfail — RED)
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 11-26)

- [x] Task 1.2: Implement `delete_game()` changes and remove xfail markers (GREEN)
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 28-47)

- [x] Task 1.3: Add edge case tests and verify image reference counts
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 49-64)

### [x] Phase 2: Update `_handle_game_cancelled()` in bot

- [x] Task 2.1: Write unit tests for message deletion behaviour (xfail — RED)
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 68-82)

- [x] Task 2.2: Implement handler changes and remove xfail markers (GREEN)
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 84-100)

- [x] Task 2.3: Add `discord.NotFound` edge case test and verify
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 102-115)

### [x] Phase 3: Update E2E test assertions

- [x] Task 3.1: Update `test_game_cancellation.py` to assert game row absent and Discord message deleted
  - Details: `.copilot-tracking/planning/details/20260314-01-cancelled-game-cleanup-details.md` (Lines 119-132)

## Dependencies

- SQLAlchemy `db.delete()` session API
- `discord.py` `Message.delete()` and `discord.NotFound`
- Existing `release_image()` utility (unchanged)
- Existing deferred event publisher (unchanged)

## Success Criteria

- `DELETE /api/v1/games/{id}` returns 204 and game row is absent from DB
- Discord announcement message is deleted (not edited) on cancellation
- Image reference counts correctly decremented; orphaned images deleted
- All existing integration tests pass without modification
- E2E cancellation test passes with updated assertions
