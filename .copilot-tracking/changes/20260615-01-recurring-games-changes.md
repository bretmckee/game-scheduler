<!-- markdownlint-disable-file -->

# Changes: Recurring Games

## Phase 1: DB Migration + Model + API Schemas + Clone Propagation

### Added

- `alembic/versions/20260615_add_recur_rule_game_sessions.py` — Alembic migration adding `recur_rule VARCHAR(200) NULL` to `game_sessions` table
- `tests/unit/services/test_clone_game.py::test_clone_game_propagates_recur_rule` — unit test verifying `clone_game()` copies `recur_rule` from source

### Modified

- `shared/models/game.py` — added `recur_rule: Mapped[str | None]` field to `GameSession` after `post_at`
- `shared/schemas/game.py` — added `recur_rule: str | None = None` to `GameCreateRequest`, `GameUpdateRequest`, and `GameResponse`
- `services/api/services/games.py` — added `recur_rule=source_game.recur_rule` to the `GameSession` constructor in `clone_game()`
- `.copilot-tracking/planning/plans/20260615-01-recurring-games.plan.md` — marked Phase 1 tasks complete

## Phase 2: DM Format + `RecurrenceConfirmationView` Stubs + RED Unit Tests

### Added

- `services/bot/views/recurrence_confirmation_view.py` — stub `RecurrenceConfirmationView` with `confirm` and `decline` raising `NotImplementedError`
- `tests/unit/services/bot/views/test_recurrence_confirmation_view.py` — xfail unit tests for `confirm` (sets `post_at`, sends pg_notify) and `decline` (cancels game)

### Modified

- `shared/message_formats.py` — added `DMFormats.recurrence_confirmation(game_title, next_at_unix)` stub raising `NotImplementedError`
- `tests/unit/shared/test_message_formats.py` — appended 3 xfail tests for `DMFormats.recurrence_confirmation` (title, timestamp, confirmation action); added `import pytest`

## Phase 3: DM Format + `RecurrenceConfirmationView` GREEN

### Modified

- `shared/message_formats.py` — implemented `DMFormats.recurrence_confirmation` returning DM text with game title and Discord timestamp
- `services/bot/views/recurrence_confirmation_view.py` — implemented full `RecurrenceConfirmationView` with Confirm/Decline buttons; confirm sets `post_at=now()` and sends pg_notify; decline sets `game.status=CANCELLED`
- `tests/unit/shared/test_message_formats.py` — removed xfail markers from Phase 2 tests; added button-dispatch tests
- `tests/unit/services/bot/views/test_recurrence_confirmation_view.py` — removed xfail markers from Phase 2 tests

## Phase 4: `_system_clone_for_recurrence` Stub + RED Unit Tests

### Added

- `tests/unit/services/test_system_clone_for_recurrence.py` — 6 xfail unit tests for `_system_clone_for_recurrence` (post_at=None, recur_rule copy, scheduled_at=next_at, confirmed player carryover, no \_publish_game_created, status schedules created)

### Modified

- `services/api/services/games.py` — added `_system_clone_for_recurrence` stub raising `NotImplementedError` after `clone_game`

## Phase 5: `_system_clone_for_recurrence` GREEN

_(not started)_

## Phase 6: Handler Modifications Stubs + RED Unit Tests

_(not started)_

## Phase 7: Handler Modifications GREEN

_(not started)_

## Phase 8: Integration Tests

_(not started)_

## Phase 9: E2E Tests

_(not started)_

## Phase 10: Frontend `RecurrenceSelector`

_(not started)_
