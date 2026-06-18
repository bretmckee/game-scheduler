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
