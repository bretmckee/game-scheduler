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

### Phase 3: Delete `GameService._schedule_join_notifications_for_game` and repoint its callers

#### Added

- `tests/unit/api/services/test_games.py` - added `TestAddNewMentions.test_only_schedules_notification_for_newly_added_participant`, the bug-fix regression test (initially `xfail(strict=True)`, confirmed `xfailed` before the fix, marker removed after); builds a game with one pre-existing (already-scheduled) participant, adds one new mention, and asserts `schedule_join_notification` is called exactly once, for the newly-added participant only.

#### Modified

- `services/api/services/games.py`:
  - Extended the `shared.services.game_schedules` import into a parenthesized multi-import block adding `schedule_join_notifications_for_game`.
  - `_setup_game_schedules` - replaced `await self._schedule_join_notifications_for_game(game)` with `await schedule_join_notifications_for_game(self.db, game)`.
  - `_add_new_mentions` - fixed the duplicate-scheduling bug: added a local `new_participants` list, appended each newly-created participant to it inside the creation loop, and replaced the closing `await self._schedule_join_notifications_for_game(game)` bulk-sweep with a loop that calls `schedule_join_notification` directly for each entry in `new_participants` only (participants with a `user_id`) - no longer re-sweeps or re-notifies participants already scheduled on a prior edit. Updated the inline comment above `game.participants.append(new_participant)` to no longer reference the deleted method by name.
  - Deleted `_schedule_join_notifications_for_game` in its entirety - its only two callers (`_setup_game_schedules`, `_add_new_mentions`) now call the shared module-level functions directly.
- `tests/unit/api/services/test_games.py`:
  - Removed the "`- _schedule_join_notifications_for_game with confirmed participants`" bullet from the module docstring.
  - Deleted the entire `TestScheduleJoinNotifications` class - its target method no longer exists; equivalent coverage (confirmed-and-overflow participants scheduled, no-`user_id` participants skipped) lives in `tests/unit/shared/services/test_game_schedules.py` (added in Phase 2).
- `tests/unit/services/api/services/test_games_service.py`:
  - `test_setup_game_schedules_with_reminders_and_duration` and `test_setup_game_schedules_without_duration` - changed `patch.object(game_service, "_schedule_join_notifications_for_game", ...)` to `patch("services.api.services.games.schedule_join_notifications_for_game", ...)`; changed `mock_join_notifications.assert_called_once_with(game)` to `mock_join_notifications.assert_called_once_with(game_service.db, game)`.

**Verification**: `uv run pytest tests/unit/api/services/test_games.py -k only_schedules_notification_for_newly_added -v` showed `xfailed` before the fix (RED confirmed) and `passed` after the marker was removed. `uv run pytest tests/unit` (2459 passed), `uv run mypy shared/ services/` (no issues), `uv run ruff check`/`ruff format --check` on all three changed files (clean). `grep -rn "\b_schedule_join_notifications_for_game\b" services/ tests/unit tests/integration` returns no matches, confirming the dead method is fully removed.

#### Task 3.3: Full-consolidation verification against integration and e2e suites

No files modified — verification only, run once after Task 3.2 reached GREEN.

- `scripts/run-integration-tests.sh tests/integration/test_game_signup_methods.py tests/integration/test_games_crud.py tests/integration/test_leave_game_promotion.py tests/integration/test_player_removed_queue.py` - 33 passed, matching the pre-refactor baseline. Exercises `join_game`, `_setup_game_schedules`, `_add_new_mentions`, and `shared/services/game_schedules.py` through real API + DB.
- `scripts/run-e2e-tests.sh tests/e2e/test_join_notification.py` - 5 passed (322.75s), including all 5 tests named in the plan's success criteria, exercising the consolidated functions end-to-end through real Discord DM delivery.

**Verification**: Both runs' full output was captured via `tee` per `.github/instructions/test-execution.instructions.md` before any inspection; both scripts reported their own pass/fail status ("Integration tests passed!", "End-to-end tests passed!") in addition to pytest's summary line. No coverage was added for `services/bot/handlers/join_game.py::handle_join_game` in this task, per the plan's explicit note.

### Phase 4: Remove dead code — `shared/data_access/guild_queries.py::add_participant`

Plain dead-code removal (no xfail/TDD workflow) per `.github/instructions/test-driven-development.instructions.md` - `add_participant` behaved correctly, it simply had no production caller.

#### Added

- `tests/integration/test_guild_queries_integration.py` - added `_seed_participant(game_id, user_id)` helper (after `make_game_data`, before the `# Game Operations Integration Tests` section header) that builds a `GameParticipant` row directly for test setup, replacing the removed `guild_queries.add_participant` as scaffolding.

#### Modified

- `tests/integration/test_guild_queries_integration.py`:
  - Import block: added `GameParticipant` to the existing `from shared.models.participant import ParticipantType` line.
  - `test_remove_participant_validates_game_belongs_to_guild`, `test_remove_participant_succeeds_for_correct_guild`, `test_list_user_games_returns_only_guild_games` - replaced their `await guild_queries.add_participant(...)` setup calls with `admin_db.add(_seed_participant(...))`, keeping the existing `await admin_db.commit()` calls unchanged.

#### Removed

- `shared/data_access/guild_queries.py` - deleted `add_participant` in its entirety (zero production callers, re-confirmed before removal).
- `tests/unit/shared/data_access/test_guild_queries_unit.py` - deleted the entire `TestAddParticipant` class (5 tests). `GameParticipant` import and `sample_game` fixture retained - still used by `TestRemoveParticipant` and other classes.
- `tests/integration/test_guild_queries_integration.py` - deleted `test_add_participant_validates_game_belongs_to_guild` and `test_add_participant_succeeds_for_correct_guild` in their entirety (exercised `add_participant` directly, no other purpose).

**Verification**: `grep -rn "guild_queries\.add_participant\|guild_queries import.*add_participant" services/ shared/` (excluding the definition site) returned no matches both before and after removal, confirming zero production callers. `grep -rn "add_participant" services/ shared/ tests/` after the phase shows only the `_seed_participant` helper's docstring text and the unrelated `_add_participant_carryover_schedules`/`_add_participant_fields` functions (different names, substring false positives) - no stray reference to the removed function survives. `uv run pytest tests/unit` (2454 passed - 5 fewer than Phase 3's 2459, matching the deleted `TestAddParticipant` class), `uv run mypy shared/ services/` (no issues), `uv run ruff check`/`ruff format --check` on all three changed files (clean). `scripts/run-integration-tests.sh tests/integration/test_guild_queries_integration.py` - 19 passed (down from 21 pre-removal, matching the 2 deleted dedicated tests), full output captured via `tee` per `.github/instructions/test-execution.instructions.md`.
