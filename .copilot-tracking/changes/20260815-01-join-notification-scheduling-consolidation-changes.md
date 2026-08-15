<!-- markdownlint-disable-file -->

# Release Changes: Consolidate join-notification scheduling into shared primitives

**Related Plan**: 20260815-01-join-notification-scheduling-consolidation.plan.md
**Implementation Date**: 2026-08-15

## Summary

Consolidates the scattered "schedule a join notification for a new game participant" logic — currently duplicated across `services/api/services/games.py`, `shared/services/game_schedules.py`, and `services/bot/handlers/join_game.py` — into exactly two shared primitives in `shared/services/game_schedules.py`.

## Changes

### Phase 1: Relocate `schedule_join_notification` primitive to `shared/services/game_schedules.py`

#### Added

- `shared/services/game_schedules.py` - added `schedule_join_notification(db, game_id, participant_id, game_scheduled_at, delay_seconds=60)`, moved verbatim from `services/api/services/notification_schedule.py`, inserted after `_DEFAULT_GAME_DURATION_MINUTES` and before `setup_game_schedules`.
- `tests/unit/shared/services/test_game_schedules.py` - added `test_schedule_join_notification_adds_and_returns_entry` and `test_schedule_join_notification_uses_default_delay`, direct coverage of the relocated primitive's field-construction logic and default-delay behavior.

#### Modified

- `services/api/services/games.py` - removed the standalone `from services.api.services.notification_schedule import schedule_join_notification` import; `schedule_join_notification` is now imported alongside `clone_game_for_recurrence` from `shared.services.game_schedules`.
- `services/bot/handlers/join_game.py` - `handle_join_game` now calls the shared `schedule_join_notification()` primitive instead of constructing `NotificationSchedule` inline; removed now-unused `timedelta`, `utc_now`, and `NotificationSchedule` imports.
- `tests/e2e/test_join_notification.py` - updated the `schedule_join_notification` import to `shared.services.game_schedules` (kept isort-alphabetical order among the `shared.*` imports).

#### Removed

- `services/api/services/notification_schedule.py` - removed the module-level `schedule_join_notification()` function (relocated to `shared/services/game_schedules.py`) and the now-unused `from shared.models.base import utc_now` import.

**Verification**: `uv run pytest tests/unit` (2460 passed), `uv run mypy shared/ services/` (no issues), `uv run ruff check`/`ruff format --check` on all changed files (clean). Scoped re-run of `tests/unit/api/services/test_games.py`, `tests/unit/services/api/services/test_games_edit_participants.py`, `tests/unit/bot/handlers/test_join_game_handler.py`, and `tests/unit/shared/services/test_game_schedules.py` also green (65 passed), confirming patch targets in those files continue to resolve correctly.
