# Changes: Recurring Games

## Summary

Add recurring game support: when a game with a `recur_rule` (RFC 5545 RRULE string) completes,
automatically clone it to the next occurrence with host DM confirmation, zombie-game prevention,
and a frontend RRULE builder.

## Added

## Modified

## Removed

---

## Phase 1 Progress (Complete)

### Task 1.1: Alembic migration for `recur_rule`

- Added `alembic/versions/20260615_add_recur_rule_game_sessions.py` — migration adding `recur_rule VARCHAR(200) NULL` to `game_sessions`

### Task 1.2: `recur_rule` field on `GameSession` model

- Modified `shared/models/game.py` — added `recur_rule: Mapped[str | None]` column

### Task 1.3: `recur_rule` in API schemas

- Modified `services/api/schemas/game.py` — added `recur_rule: str | None = None` to `GameCreateRequest`, `GameUpdateRequest`, `GameResponse`

### Task 1.4: `clone_game()` propagation + unit test

- Modified `services/api/services/games.py` — `clone_game()` now copies `recur_rule` to the cloned game
- Added `tests/unit/services/test_clone_game.py` — `test_clone_game_propagates_recur_rule` verifies `recur_rule` is copied

---

## Phase 2 Progress (Complete)

### Task 2.1: `DMFormats.recurrence_confirmation` stub

- Modified `shared/message_formats.py` — added `recurrence_confirmation` stub raising `NotImplementedError`

### Task 2.2: `RecurrenceConfirmationView` stub file

- Added `services/bot/views/recurrence_confirmation_view.py` — stub class with `confirm` and `decline` raising `NotImplementedError`

### Task 2.3: xfail unit tests for `DMFormats.recurrence_confirmation`

- Modified `tests/unit/shared/test_message_formats.py` — appended three `xfail` tests for `recurrence_confirmation`

### Task 2.4: xfail unit tests for `RecurrenceConfirmationView`

- Added `tests/unit/services/bot/views/test_recurrence_confirmation_view.py` — three `xfail` tests for confirm/decline callbacks

---

## Phase 3 Progress (Complete)

### Task 3.1: Implement `DMFormats.recurrence_confirmation`

- Modified `shared/message_formats.py` — replaced `NotImplementedError` stub with the full implementation returning the 🔁 DM string with game title and Discord timestamp

### Task 3.2: Implement full `RecurrenceConfirmationView`

- Modified `services/bot/views/recurrence_confirmation_view.py` — replaced stubs with full implementation: `_ConfirmButton`/`_DeclineButton` inner classes following `CloneConfirmationView` pattern; confirm sets `game.post_at = datetime.now(UTC)`, executes `pg_notify('game_announcement_changed', '')`, and commits; decline sets `game.status = GameStatus.CANCELLED.value` and commits

### Task 3.3: Remove xfail markers; verify all pass

- Modified `tests/unit/shared/test_message_formats.py` — removed `@pytest.mark.xfail` from all three `recurrence_confirmation` tests
- Modified `tests/unit/services/bot/views/test_recurrence_confirmation_view.py` — removed `@pytest.mark.xfail` from all three view tests; all 6 tests pass

---

## Phase 4 Progress (Complete)

### Task 4.1: `_system_clone_for_recurrence` stub

- Modified `services/api/services/games.py` — added `_system_clone_for_recurrence` stub raising `NotImplementedError`

### Task 4.2: xfail unit tests

- Added `tests/unit/services/test_system_clone_for_recurrence.py` — 6 `xfail` tests covering field copying, `post_at=None`, participant carryover, and `_create_game_status_schedules` call

---

## Phase 5 Progress (Complete)

### Task 5.1: Implement `_system_clone_for_recurrence`

- Modified `services/api/services/games.py` — full implementation: copies all source fields, sets `post_at=None`, carries over confirmed participants via `partition_participants`, calls `_create_game_status_schedules`, does NOT call `_publish_game_created` or `_setup_game_schedules`

### Task 5.2: Remove xfail markers; verify all pass

- Modified `tests/unit/services/test_system_clone_for_recurrence.py` — removed all `@pytest.mark.xfail` markers; all 6 tests pass

---

## Phase 6 Progress (Complete)

### Task 6.1: `_handle_recurrence_confirmation` stub

- Modified `services/bot/events/handlers.py` — added `_handle_recurrence_confirmation` stub raising `NotImplementedError`; added `_schedule_recurrence_confirmation_notification` and `_cancel_unconfirmed_recurrence` helper stubs

### Task 6.2: xfail unit tests for handler modifications

- Added `tests/unit/services/bot/events/test_handlers_recurrence.py` — 12 tests covering recurrence clone trigger, zombie cancel, notification dispatch, and helper scheduling; all marked `xfail`

---

## Phase 7 Progress (Complete)

### Task 7.1: `_handle_post_transition_actions` triggers clone

- Modified `services/bot/events/handlers.py` — at COMPLETED transition with `recur_rule IS NOT NULL`, calls `_system_clone_for_recurrence` and schedules recurrence_confirmation notification

### Task 7.2: Zombie cancel in `_handle_status_transition_due`

- Modified `services/bot/events/handlers.py` — at IN_PROGRESS transition: cancels clone if `message_id IS NULL AND recur_rule IS NOT NULL`

### Task 7.3: Implement `_handle_recurrence_confirmation` + dispatch

- Modified `services/bot/events/handlers.py` — `_handle_recurrence_confirmation` fetches game and sends host DM with `RecurrenceConfirmationView`; `_handle_notification_due` dispatches to it on `recurrence_confirmation` type; `_schedule_recurrence_confirmation_notification` and `_cancel_unconfirmed_recurrence` helpers implemented
- Added `types-python-dateutil` dev dependency for mypy stubs

### Task 7.4: Remove xfail markers; verify all pass

- Modified `tests/unit/services/bot/events/test_handlers_recurrence.py` — removed all `@pytest.mark.xfail` markers; all 12 tests pass

---

## Phase 8 Progress (In Progress)

### Task 8.1: Fix `update_game` `clear_post_at` for `post_at=NULL` recurrence clones

- Modified `services/api/services/games.py` — widened `clear_post_at` precondition from `game.post_at is not None` to `(game.post_at is not None or game.recur_rule is not None)`; for `post_at=NULL` clones sets `game.post_at = datetime.now(UTC)` instead of clearing to None
- Modified `tests/unit/services/api/services/test_games_service.py` — added `test_clear_post_at_sets_post_at_for_null_post_at_recurrence_clone` and `test_clear_post_at_is_no_op_for_null_post_at_non_recurrence`; both pass

### Task 8.2: Integration tests for recurrence clone lifecycle

- Added `tests/integration/test_recurrence_clone.py` — 4 integration tests: `test_recur_rule_stored_and_returned`, `test_recur_rule_propagated_through_clone_endpoint`, `test_recurrence_clone_with_null_post_at_is_visible`, `test_clear_post_at_announces_recurrence_clone`
