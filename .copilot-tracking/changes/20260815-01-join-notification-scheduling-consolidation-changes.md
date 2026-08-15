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

### Phase 2: Fix the confirmed-only bug and rename `_schedule_join_notifications` to public `schedule_join_notifications_for_game`

#### Note on task sequencing vs. the plan text

The plan's Task 2.1 file list only touches the test file, and assigns the actual production rename to Task 2.2. In practice the RED-phase regression test needs to call the function under its final public name (`schedule_join_notifications_for_game`) to get a real `xfailed` result instead of an `ImportError`/collection failure, so the mechanical, behavior-preserving rename (symbol name + `setup_game_schedules` call site only — no logic change) was done as the first step of Task 2.1, alongside the three pre-existing tests' patch-target/call-site renames (also mechanical, no assertion changes). Task 2.2 then did the actual behavioral fix (iterate all participants, delegate to `schedule_join_notification`) and updated the two tests whose assertions depend on that behavior. Net result matches the plan's intent and Success Criteria; only the internal split of "which task touches the rename line" differs from the literal file lists.

#### Added

- `tests/unit/shared/services/test_game_schedules.py` - added `test_schedule_join_notifications_for_game_includes_overflow_participant`, the bug-fix regression test (initially `xfail(strict=True)`, confirmed `xfailed` before the fix, marker removed after); asserts, using a real (unpatched) `partition_participants` call with `max_players=1` and two participants, that both the confirmed and the overflow participant get scheduled.

#### Modified

- `shared/services/game_schedules.py`:
  - Renamed `_schedule_join_notifications` to public `schedule_join_notifications_for_game`; updated `setup_game_schedules`'s call site accordingly.
  - Fixed the confirmed-only bug: now iterates all of `game.participants` (was `partition_participants(...).confirmed` only), so waitlisted/overflow participants are scheduled too.
  - Replaced the inline `NotificationSchedule(...)` construction with a delegated call to `schedule_join_notification(db=db, game_id=game.id, participant_id=participant.id, game_scheduled_at=game.scheduled_at, delay_seconds=60)`.
  - Added a docstring to `schedule_join_notifications_for_game` explaining its bulk "activation moment" contract (safe only when `game.participants` is known to contain no previously-scheduled rows) versus `schedule_join_notification`'s single-new-participant contract.
  - Updated `setup_game_schedules`'s docstring to no longer say "confirmed participants" (now "every Discord participant, confirmed or waitlisted").
- `tests/unit/shared/services/test_game_schedules.py`:
  - Import block: replaced `_schedule_join_notifications` with `schedule_join_notifications_for_game`; added `participant_model` and `SignupMethod` imports for the new regression test.
  - `test_setup_game_schedules_delegates_to_helpers` - patch target updated to `shared.services.game_schedules.schedule_join_notifications_for_game`; assertion unchanged.
  - `test_schedule_join_notifications_adds_entry_for_confirmed_participant_with_user_id` → renamed to `test_schedule_join_notifications_for_game_delegates_for_confirmed_participant`; dropped the `partition_participants` patch; now patches `schedule_join_notification` and asserts it's called once with the exact keyword arguments the sweep function must pass through.
  - `test_schedule_join_notifications_skips_participant_without_user_id` - dropped the `partition_participants` patch; now patches `schedule_join_notification` and asserts it's not called for a participant without a `user_id`.

**Verification**: `uv run pytest tests/unit/shared/services/test_game_schedules.py -k includes_overflow -v` showed `xfailed` before the fix (RED confirmed) and `passed` after the marker was removed (strict mode would otherwise error on an unexpected pass). `uv run pytest tests/unit` (2461 passed), `uv run mypy shared/ services/` (no issues), `uv run ruff check`/`ruff format --check` on both changed files (clean). `grep -rn "_schedule_join_notifications\b" --include="*.py" .` confirms the old private name no longer exists anywhere in the codebase.
