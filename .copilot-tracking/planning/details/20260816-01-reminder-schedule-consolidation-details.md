<!-- markdownlint-disable-file -->

# Task Details: Consolidate reminder-schedule population into a single shared implementation

## Research Reference

**Source Research**: .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md

## Phase 1: Rename `_populate_reminder_schedule` to public `populate_reminder_schedule` in the shared module

### Task 1.1: Rename the function, add logging parity, and update `setup_game_schedules`'s call site

Rename `_populate_reminder_schedule` (`shared/services/game_schedules.py`, currently lines 142-161) to a public `populate_reminder_schedule`, unchanged in behavior. Add a docstring consistent with its siblings (`schedule_join_notification`, `schedule_join_notifications_for_game`) in the same module, and port the `logger.info`/`logger.debug` calls from `NotificationScheduleService.populate_schedule` (`services/api/services/notification_schedule.py`, currently lines 68-99) so no operational log visibility is lost. Update `setup_game_schedules`'s internal call site (currently line 108) to the new name.

- **Files**:
  - `shared/services/game_schedules.py`:
    - Add `import logging` (alphabetically before `import uuid`) and `logger = logging.getLogger(__name__)` immediately after the imports, before `_DEFAULT_GAME_DURATION_MINUTES = 60` — this module currently has no logger.
    - Rename `_populate_reminder_schedule` to `populate_reminder_schedule`; add a docstring:

      ```python
      async def populate_reminder_schedule(
          db: AsyncSession,
          game: game_model.GameSession,
          reminder_minutes: list[int],
      ) -> None:
          """Populate reminder notification schedule for a game session.

          Creates notification_schedule records (notification_type="reminder")
          for each reminder time that falls in the future; reminders whose
          computed notification_time has already passed are skipped.

          Does not commit. Caller must commit transaction.

          Args:
              db: Active async database session.
              game: Game session to schedule reminder notifications for.
              reminder_minutes: Minutes before game start at which to remind.
          """
          if not reminder_minutes:
              logger.info("No reminder minutes configured for game %s", game.id)
              return
          now = datetime.now(UTC).replace(tzinfo=None)
          for reminder_min in reminder_minutes:
              notification_time = game.scheduled_at - timedelta(minutes=reminder_min)
              if notification_time > now:
                  db.add(
                      notification_schedule_model.NotificationSchedule(
                          game_id=game.id,
                          reminder_minutes=reminder_min,
                          notification_time=notification_time,
                          game_scheduled_at=game.scheduled_at,
                          sent=False,
                      )
                  )
                  logger.debug(
                      "Scheduled reminder for game %s at %s (%s min before)",
                      game.id,
                      notification_time,
                      reminder_min,
                  )
              else:
                  logger.debug(
                      "Skipping past reminder for game %s at %s (%s min before)",
                      game.id,
                      notification_time,
                      reminder_min,
                  )
      ```

    - Update `setup_game_schedules`'s call site (currently `await _populate_reminder_schedule(db, game, reminder_minutes)` at line 108) to `await populate_reminder_schedule(db, game, reminder_minutes)`.
- **Success**:
  - `shared.services.game_schedules.populate_reminder_schedule` exists, is public, and is field-for-field identical in the `NotificationSchedule` it constructs to the removed private function.
  - `shared.services.game_schedules._populate_reminder_schedule` no longer exists.
  - `setup_game_schedules` calls the renamed public function.
  - `uv run mypy shared/ services/` passes.
- **Research References**:
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Lines 73-96) - verbatim current implementation being renamed.
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Lines 159-160) - logging parity is safe to port; no test asserts on log text either way.
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 167) - Recommended Approach step 1 (rename, port logging, update call site).
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 183) - Key Tasks item 1.
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 184) - Key Tasks item 2 (update `setup_game_schedules`'s call site).
- **Dependencies**:
  - None (first task).

### Task 1.2: Update `tests/unit/shared/services/test_game_schedules.py` to reference the renamed public function

Every reference to `_populate_reminder_schedule` in this file's import block, patch target, and three dedicated test names/bodies must be updated to the new public name — this is a caller (test code counts as a caller per the Phase Isolation rule) and must be updated in the same phase as the rename.

- **Files**:
  - `tests/unit/shared/services/test_game_schedules.py`:
    - Update the `from shared.services.game_schedules import (...)` block (currently line 35): replace `_populate_reminder_schedule` with `populate_reminder_schedule`.
    - `test_setup_game_schedules_delegates_to_helpers` (currently lines 107-121): change the patch target `"shared.services.game_schedules._populate_reminder_schedule"` (currently line 115) to `"shared.services.game_schedules.populate_reminder_schedule"`; the assertion `mock_reminder.assert_awaited_once_with(db, game, [30])` is unchanged.
    - Rename and update the three dedicated tests (currently lines 189-219):
      - `test_populate_reminder_schedule_skips_empty_list` → body calls `await populate_reminder_schedule(db, game, reminder_minutes=[])` (function name only changes; test name and assertions unchanged).
      - `test_populate_reminder_schedule_adds_entry_for_future_reminder` → body calls `await populate_reminder_schedule(db, game, reminder_minutes=[30])` (assertions unchanged).
      - `test_populate_reminder_schedule_skips_past_reminder` → body calls `await populate_reminder_schedule(db, game, reminder_minutes=[30])` (assertions unchanged).
- **Success**:
  - `grep -n "_populate_reminder_schedule" tests/unit/shared/services/test_game_schedules.py` returns no matches.
  - `uv run pytest tests/unit/shared/services/test_game_schedules.py` green, with no test behavior change (same assertions, same coverage, only the referenced name changed).
- **Research References**:
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 187) - Key Tasks item 5 (update this file's three tests and its `setup_game_schedules` patch target).
  - .github/instructions/test-driven-development.instructions.md - "retrofitting tests for already-correct code" convention: no stub/xfail, keep real assertions, keep tests green before/after.
- **Dependencies**:
  - Task 1.1 completion (the public name must exist before tests can import/patch it).

## Phase 2: Make `NotificationScheduleService.populate_schedule` a thin delegating wrapper

### Task 2.1: Replace `populate_schedule`'s body with a delegated call; remove now-unused imports

Replace `NotificationScheduleService.populate_schedule`'s body (currently `services/api/services/notification_schedule.py` lines 51-99) with a single delegating call to the shared `populate_reminder_schedule`. `update_schedule` (currently lines 101-134) and `clear_schedule` (currently lines 136-153) are structurally untouched — `update_schedule` continues to call `self.populate_schedule(...)` at its existing line 134, which now delegates transitively.

- **Files**:
  - `services/api/services/notification_schedule.py`:
    - Add `from shared.services.game_schedules import populate_reminder_schedule`, placed alphabetically among the existing `from shared...` imports (after the `from shared.models import notification_schedule as notification_schedule_model` line).
    - Remove the now-unused `from datetime import UTC, datetime, timedelta` import (currently line 28) — `update_schedule` and `clear_schedule` never reference `datetime`/`UTC`/`timedelta`; only the old `populate_schedule` body did.
    - Replace `populate_schedule`'s body:

      ```python
      async def populate_schedule(
          self,
          game: game_model.GameSession,
          reminder_minutes: list[int],
      ) -> None:
          """
          Populate notification schedule for a game session.

          Delegates to the shared populate_reminder_schedule primitive in
          shared.services.game_schedules so the API and bot services share
          exactly one implementation of reminder-row construction.

          Does not commit. Caller must commit transaction.

          Args:
              game: Game session to schedule notifications for
              reminder_minutes: List of reminder times in minutes before game
          """
          await populate_reminder_schedule(self.db, game, reminder_minutes)
      ```

    - `update_schedule` and `clear_schedule` are otherwise unchanged; `logger`/`logging` (used by both) remain imported.
- **Success**:
  - `NotificationScheduleService.populate_schedule`'s body is exactly one `await populate_reminder_schedule(self.db, game, reminder_minutes)` statement (plus docstring).
  - `services/api/services/notification_schedule.py` has no unused imports (`datetime`/`UTC`/`timedelta` removed; `logging`, `notification_schedule_model`, `game_model`, `delete`, `AsyncSession` all still used by `update_schedule`/`clear_schedule`).
  - `update_schedule`'s DELETE statement and its scoping to `notification_type == "reminder"` are byte-for-byte unchanged from before this task.
  - `uv run mypy shared/ services/` passes.
- **Research References**:
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Lines 168-173) - Recommended Approach step 2, exact delegating wrapper shape.
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 161) - `update_schedule`'s DELETE scoping is independent of this consolidation and must not be touched.
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 186) - Key Tasks item 4 (update this file's imports).
- **Dependencies**:
  - Phase 1 completion (`populate_reminder_schedule` must be public and importable).

### Task 2.2: Add a delegation-assertion test; confirm existing tests remain green unmodified

Add one new test proving `populate_schedule` delegates to the shared primitive with the correct arguments, matching the delegation-test pattern already used for `schedule_join_notification`'s consumers in the prior consolidation. The three existing `populate_schedule` tests exercise real field-construction logic through a mock `db` and are expected to keep passing unmodified now that they run against the real `populate_reminder_schedule` implementation instead of the old inline body — re-run them to confirm.

- **Files**:
  - `tests/unit/services/api/services/test_notification_schedule.py`:
    - Add `from unittest.mock import patch` to the existing `from unittest.mock import AsyncMock, MagicMock` import line (as `AsyncMock, MagicMock, patch`).
    - Add a new test, placed after `test_populate_schedule_with_empty_reminders`:

      ```python
      @pytest.mark.asyncio
      async def test_populate_schedule_delegates_to_shared_primitive():
          """populate_schedule must delegate to the shared populate_reminder_schedule."""
          mock_db = AsyncMock()
          service = NotificationScheduleService(mock_db)
          game = MagicMock(spec=GameSession)
          game.id = "test-game-id"
          reminder_minutes = [30, 60]

          with patch(
              "services.api.services.notification_schedule.populate_reminder_schedule",
              new_callable=AsyncMock,
          ) as mock_populate:
              await service.populate_schedule(game, reminder_minutes)

          mock_populate.assert_awaited_once_with(mock_db, game, reminder_minutes)
      ```

  - No changes to `test_populate_schedule_creates_future_notifications`, `test_populate_schedule_skips_past_notifications`, `test_populate_schedule_with_empty_reminders`, `test_update_schedule_deletes_and_creates`, `test_update_schedule_delete_is_scoped_to_reminder_rows`, or `test_clear_schedule_deletes_all_notifications` — all assert on `mock_db.add`/`mock_db.execute` call counts and fields, not on which function performed the work.
- **Success**:
  - The new delegation test passes, with a falsifiable assertion on the exact `(db, game, reminder_minutes)` arguments passed through.
  - `uv run pytest tests/unit/services/api/services/test_notification_schedule.py` green, with the same 6 pre-existing tests passing unmodified plus the 1 new test.
  - `uv run pytest tests/unit` and `uv run mypy shared/ services/` both green.
- **Research References**:
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 188) - Key Tasks item 6: existing tests should continue to pass unchanged; add one delegation-assertion test.
  - .github/instructions/unit-tests.instructions.md - falsifiable, real-argument mock assertions required.
- **Dependencies**:
  - Task 2.1 completion (the delegating wrapper must exist before its delegation can be asserted).

### Task 2.3: Verify the `311e6c48` integration regression test remains green against the delegated implementation

`tests/integration/test_notification_schedule.py::test_update_schedule_preserves_join_notification_row` exercises `update_schedule` → `self.populate_schedule(...)` against real PostgreSQL. Since `update_schedule` and its DELETE scoping are unmodified by this consolidation, and `populate_schedule` now only changes _which_ function performs the identical `db.add` work, this test is expected to remain green with zero modifications — run it once, here, to confirm.

- **Files**: none modified — verification only.
- **Success**:
  - A `scripts/run-integration-tests.sh` run scoped to `tests/integration/test_notification_schedule.py` passes (`test_update_schedule_preserves_join_notification_row` green), confirming the join_notification row still survives a reminder-schedule refresh through the newly-delegated `populate_schedule`. Follow `.github/instructions/test-execution.instructions.md` for output capture (`tee`, before any filtering) and use a timeout of at least 10 minutes.
  - No modification to `tests/integration/test_notification_schedule.py` is made or needed.
- **Research References**:
  - .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md (Line 193) - Success Criteria: `_process_game_update_schedules`'s DELETE-scoping behavior and its integration test remain green with zero modifications; full unit + integration test suites green.
  - .github/instructions/test-execution.instructions.md - output-capture and timeout rules for `scripts/run-integration-tests.sh`.
- **Dependencies**:
  - Task 2.2 completion (Phase 2's GREEN state at the unit-test/mypy level reached first).

## Out of Scope (noted, not planned)

Per the research document's Recommended Approach items 3 and 4, these are separate, optional, lower-priority follow-up candidates the research explicitly flags as "confirm with user before bundling" — they have no phases here:

- Having `services/api/services/games.py::_setup_game_schedules` call the shared `setup_game_schedules` bundler directly instead of manually re-composing `schedule_join_notifications_for_game` + `NotificationScheduleService.populate_schedule`.
- Deleting the dead `NotificationScheduleService.clear_schedule` (zero production callers) and its test.

## Dependencies

- No schema/migration changes, no new third-party dependencies.
- `uv run pytest tests/unit`, `uv run mypy shared/ services/` available locally (project's standard pre-commit gates).
- `scripts/run-integration-tests.sh` available locally for Phase 2 Task 2.3's scoped verification (per `.github/instructions/test-execution.instructions.md`).

## Success Criteria

- `shared.services.game_schedules.populate_reminder_schedule` is the sole, public implementation of reminder-row construction, used by both `setup_game_schedules` (bot path) and `NotificationScheduleService.populate_schedule` (API path).
- `_populate_reminder_schedule` no longer exists anywhere in the codebase.
- `NotificationScheduleService.populate_schedule`'s body is a single delegating call.
- `update_schedule`'s DELETE-scoping fix (`311e6c48`) and `clear_schedule` are unchanged.
- Full unit test suite (`uv run pytest tests/unit`) and `uv run mypy shared/ services/` green.
- `tests/integration/test_notification_schedule.py` green with zero modifications.
