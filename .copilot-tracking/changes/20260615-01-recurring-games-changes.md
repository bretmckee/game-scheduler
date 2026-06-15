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

_(not started)_

## Phase 3: DM Format + `RecurrenceConfirmationView` GREEN

_(not started)_

## Phase 4: `_system_clone_for_recurrence` Stub + RED Unit Tests

_(not started)_

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
