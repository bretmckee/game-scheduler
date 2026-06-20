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

### Modified

- `services/api/services/games.py` — replaced `_system_clone_for_recurrence` stub with full implementation: copies all source fields, sets `post_at=None`/`message_id=None`/`status=SCHEDULED`, carries over confirmed participants via `partition_participants`, calls `_create_game_status_schedules`, does not call `_publish_game_created` or `_setup_game_schedules`
- `tests/unit/services/test_system_clone_for_recurrence.py` — removed all 6 xfail markers; all tests pass GREEN

## Phase 6: Handler Modifications Stubs + RED Unit Tests

### Added

- `tests/unit/services/bot/events/test_handlers_recurrence.py` — 6 tests (3 xfail + 3 pass): recurrence clone trigger at COMPLETED, zombie cancel for unannounced clones, DM dispatch test for `_handle_recurrence_confirmation`

### Modified

- `services/bot/events/handlers.py` — added `_handle_recurrence_confirmation` stub raising `NotImplementedError` after `_handle_clone_confirmation`

## Phase 7: Handler Modifications GREEN

### Added

- `pyproject.toml` (dev deps) — added `types-python-dateutil` stub package to fix mypy `import-untyped` error

### Modified

- `services/bot/events/handlers.py`:
  - Added top-level imports: `rrulestr` (dateutil), `GameService`, `DeferredEventPublisher`, `EventPublisher`, `RecurrenceConfirmationView`, `NotificationSchedule`
  - `_handle_post_transition_actions` — added recurrence clone trigger: calls `_system_clone_for_recurrence` and `_schedule_recurrence_confirmation_notification` when `target_status=COMPLETED` and `game.recur_rule` is set
  - `_handle_status_transition_due` — added zombie-clone cancel: if `target_status=IN_PROGRESS` and `game.message_id is None` and `game.recur_rule is not None`, calls `_cancel_unconfirmed_recurrence` and returns early
  - `_handle_notification_due` — added `elif notification_type == "recurrence_confirmation"` dispatch branch
  - Replaced `_handle_recurrence_confirmation` stub with full implementation: fetches game, builds `RecurrenceConfirmationView`, sends DM to host via `bot.get_user`
  - Added `_schedule_recurrence_confirmation_notification(db, clone)` helper: inserts `NotificationSchedule` row with `notification_type="recurrence_confirmation"` at `now() + 60s`
  - Added `_cancel_unconfirmed_recurrence(db, game)` helper: sets `game.status=CANCELLED` and commits
- `tests/unit/services/bot/events/test_handlers_recurrence.py` — removed all 3 xfail markers; all 6 tests pass GREEN
- `tests/unit/bot/events/test_handlers_misc.py` — added `game.recur_rule = None` to 3 existing `_handle_post_transition_actions` tests (required to prevent new recurrence branch firing on MagicMock games)

## Phase 8: Integration Tests

_(not started)_

## Phase 9: E2E Tests

_(not started)_

## Phase 10: Frontend `RecurrenceSelector`

_(completed in prior session — see RecurrenceSelector component and related tests)_

## Phase 11: Pending Confirmation UI

### Added

- `tests/unit/services/api/test_games_display_status.py` — 7 unit tests for `display_status` computation via `_build_game_response`; written as xfail (Task 11.1), then xfail markers removed after implementation (Task 11.2)

### Modified

- `shared/schemas/game.py` — added `display_status: str` required field to `GameResponse` with description
- `services/api/routes/games.py` — `_build_game_response` now computes and passes `display_status`; returns `"PENDING_CONFIRMATION"` when `status == "SCHEDULED"`, `recur_rule is not None`, `post_at is None`, and `message_id is None`; otherwise passes through `game.status`
- `tests/unit/shared/schemas/test_game_schema.py` — added `display_status="SCHEDULED"` to both `GameResponse` instantiations that were now missing the required field
- `frontend/src/types/index.ts` — added `display_status?: string` to `GameSession` interface
- `frontend/src/components/GameCard.tsx` — added `"PENDING_CONFIRMATION": "warning"` case to `getStatusColor()`; chip label and color now use `game.display_status ?? game.status`
- `frontend/src/components/__tests__/GameCard.test.tsx` — added `GameCard display_status chip` describe block with 2 tests: warning chip for `PENDING_CONFIRMATION`, fallback to `status` when `display_status` absent
- `frontend/src/pages/GameDetails.tsx` — added `"PENDING_CONFIRMATION": "warning"` to `getStatusColor()`; chip uses `game.display_status ?? game.status`; renders MUI `Alert severity="info"` when `display_status === "PENDING_CONFIRMATION"` and `canEdit`
- `frontend/src/pages/__tests__/GameDetails.test.tsx` — added `GameDetails - pending confirmation alert` describe block with 3 tests: alert shown when editable, alert absent when not editable, alert absent when `display_status === "SCHEDULED"`
