<!-- markdownlint-disable-file -->

# Task Details: Consolidate join-notification scheduling into shared primitives

## Research Reference

**Source Research**: .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md

## Phase 1: Relocate `schedule_join_notification` primitive to `shared/services/game_schedules.py`

### Task 1.1: Move `schedule_join_notification()` verbatim into `shared/services/game_schedules.py`

Move the module-level `schedule_join_notification()` function (builds one `NotificationSchedule(notification_type="join_notification", ...)` row, flushes, returns it) out of `services/api/services/notification_schedule.py` and into `shared/services/game_schedules.py`, unchanged. All of its dependencies (`AsyncSession`, `timedelta`, `notification_schedule_model`, `utc_now`) are already imported in `shared/services/game_schedules.py`. Insert it after the `_DEFAULT_GAME_DURATION_MINUTES = 60` constant and before `async def setup_game_schedules`, so it reads as the primitive that later functions in the file build on.

- **Files**:
  - `shared/services/game_schedules.py` - add `schedule_join_notification(db, game_id, participant_id, game_scheduled_at, delay_seconds=60)`, body/docstring identical to the source.
  - `services/api/services/notification_schedule.py` - delete the function (currently lines 150-190); remove the now-unused `from shared.models.base import utc_now` import (currently line 35) — `utc_now` has no other caller in this file. Leave `NotificationScheduleService`, its imports, and `timedelta`/`datetime`/`UTC` (still used by `populate_schedule`) untouched.
- **Success**:
  - `shared.services.game_schedules.schedule_join_notification` exists with the same signature, docstring, and body as the removed function.
  - `services/api/services/notification_schedule.py` no longer defines `schedule_join_notification` and has no unused imports.
  - `uv run mypy shared/ services/` passes.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 20-22) - original location and description of `schedule_join_notification()`.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 157-161) - Recommended Approach primitive (1): moved verbatim, no behavior change.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 178) - Key Tasks item 1.
- **Dependencies**:
  - None (first task).

### Task 1.2: Repoint `services/api/services/games.py`'s import

Update the import so `GameService.join_game` (and the still-present, not-yet-deleted `_schedule_join_notifications_for_game`) resolve `schedule_join_notification` from its new home.

- **Files**:
  - `services/api/services/games.py` - remove the standalone `from services.api.services.notification_schedule import schedule_join_notification` line (currently line 47); extend the existing `from shared.services.game_schedules import clone_game_for_recurrence` line (currently line 67) to `from shared.services.game_schedules import clone_game_for_recurrence, schedule_join_notification`.
- **Success**:
  - `services.api.services.games` module has exactly one import of `schedule_join_notification`, sourced from `shared.services.game_schedules`.
  - `game_service.join_game` and `game_service._schedule_join_notifications_for_game` (unchanged this phase) both still resolve correctly.
  - Existing patches of `"services.api.services.games.schedule_join_notification"` in `tests/unit/api/services/test_games.py` (TestJoinGame, TestScheduleJoinNotifications, TestAddNewMentions, TestUpdatePrefilledParticipants classes) and `tests/unit/services/api/services/test_games_edit_participants.py` continue to pass unmodified — patch-where-used still resolves the same bound name regardless of its import source.
  - `uv run pytest tests/unit/api/services/test_games.py tests/unit/services/api/services/test_games_edit_participants.py` green with no test file changes.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 157-159) - Recommended Approach primitive (1), `join_game` bullet: "update its import."
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 181) - Key Tasks item 4.
- **Dependencies**:
  - Task 1.1 completion.

### Task 1.3: Repoint `services/bot/handlers/join_game.py` to call the shared primitive

Replace the bot's independently hand-copied inline `NotificationSchedule(...)` construction with a call to the shared `schedule_join_notification()`.

**No e2e coverage exists or can exist for `handle_join_game` itself.** Discord's platform provides no mechanism to simulate a component (button) interaction from an automated test, so there is no way to drive this function end-to-end the way `tests/e2e/test_join_notification.py` drives the API's `join_game`. `tests/unit/bot/handlers/test_join_game_handler.py` (unchanged by this task, per Success below) is the correct and only automated verification available for this function — do not go looking for or attempt to add e2e coverage for it.

- **Files**:
  - `services/bot/handlers/join_game.py`:
    - Remove now-unused imports: `from datetime import timedelta` (line 26), `from shared.models.base import utc_now` (line 42), `from shared.models.notification_schedule import NotificationSchedule` (line 44) — none of `timedelta`/`utc_now`/`NotificationSchedule` has any other caller in this file.
    - Add `from shared.services.game_schedules import schedule_join_notification`, placed alphabetically after `from shared.services.game_metrics import record_game_joined`.
    - Replace the inline construction block (currently lines 104-114: `schedule = NotificationSchedule(...); db.add(schedule)`) with:

      ```python
      # Create delayed join notification schedule
      await schedule_join_notification(
          db=db,
          game_id=str(game_id),
          participant_id=participant.id,
          game_scheduled_at=game.scheduled_at,
          delay_seconds=60,
      )
      ```

    - The surrounding structure (participant creation/commit above, `upsert_message_refresh_and_notify` + final `db.commit()` below) is unchanged; `schedule_join_notification`'s internal `db.flush()` plus the handler's own subsequent `db.commit()` preserve the existing non-committing-primitive / committing-caller pattern.
- **Success**:
  - `handle_join_game` no longer imports `NotificationSchedule`, `timedelta`, or `utc_now`.
  - `tests/unit/bot/handlers/test_join_game_handler.py` passes unmodified (it asserts on `message_refresh_queue`/`pg_notify`/`record_game_joined`, not on schedule internals, so no test change is required).
  - `uv run pytest tests/unit/bot/handlers/test_join_game_handler.py` green.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 32-36) - bot's independently-duplicated per-participant scheduling, current inline code.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 159) - Recommended Approach primitive (1), `handle_join_game` bullet.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 182) - Key Tasks item 5.
- **Dependencies**:
  - Task 1.1 completion.

### Task 1.4: Update the e2e test's import

- **Files**:
  - `tests/e2e/test_join_notification.py` - change line 54 from `from services.api.services.notification_schedule import schedule_join_notification` to `from shared.services.game_schedules import schedule_join_notification`. The call site at lines 434-440 is unchanged (same signature).
- **Success**:
  - `tests/e2e/test_join_notification.py` collects without an ImportError. This is a static check only — this file's 5 tests that exercise the consolidated functions behaviorally (`test_join_dm_says_waitlist_for_host_selected_with_waitlist`, `test_join_dm_has_instructions_when_host_adds_directly_to_confirmed_hsw_slot`, `test_join_dm_says_waitlist_for_host_added_self_signup_overflow`, `test_join_notification_with_signup_instructions`, `test_join_notification_without_signup_instructions`) are run once, against the fully-consolidated result, in Phase 3 Task 3.3 — not after every phase.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 184) - Key Tasks item 7 (update patch targets/imports referencing moved functions).
- **Dependencies**:
  - Task 1.1 completion.

### Task 1.5: Add direct unit test coverage for the relocated primitive

No unit test anywhere in the suite currently exercises `schedule_join_notification()`'s own field-construction logic directly (it was previously only exercised indirectly through callers that mock it out, plus one e2e call). Add direct coverage now that it lives in `shared/services/game_schedules.py`, following the "retrofitting tests for correct code" convention (real assertions, no `xfail` — this is a pure relocation of already-correct behavior).

- **Files**:
  - `tests/unit/shared/services/test_game_schedules.py`:
    - Add `schedule_join_notification` to the existing `from shared.services.game_schedules import (...)` block.
    - Add `test_schedule_join_notification_adds_and_returns_entry`: call `await schedule_join_notification(db, game_id="game-1", participant_id="participant-1", game_scheduled_at=<some datetime>, delay_seconds=60)`; assert the object passed to `db.add` is a `notification_schedule_model.NotificationSchedule` with `game_id == "game-1"`, `participant_id == "participant-1"`, `notification_type == "join_notification"`, `sent is False`, `game_scheduled_at` matching the input, `reminder_minutes is None`; assert `db.flush` was awaited once; assert the function's return value is that same object.
    - Add `test_schedule_join_notification_uses_default_delay`: call without `delay_seconds` and assert `notification_time` equals `utc_now() + timedelta(seconds=60)` (patch `shared.services.game_schedules.utc_now` to a fixed value, matching the existing patching pattern used elsewhere in this file).
- **Success**:
  - Both new tests pass immediately (no `xfail`), with falsifiable field-level assertions.
  - `uv run pytest tests/unit/shared/services/test_game_schedules.py` green.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 150) - "must remain non-committing" technical requirement.
  - .github/instructions/test-driven-development.instructions.md - "Retrofitting tests for already-correct code" row (no stub/xfail; real assertions required).
- **Dependencies**:
  - Task 1.1 completion.

## Phase 2: Fix the confirmed-only bug and rename `_schedule_join_notifications` to public `schedule_join_notifications_for_game`

### Task 2.1: Write the regression test for the confirmed-only bug (RED)

Prove `shared/services/game_schedules.py`'s bulk-sweep function skips waitlisted (overflow) participants — the same bug already fixed in `games.py`'s now-to-be-deleted copy, but never fixed here.

- **Files**:
  - `tests/unit/shared/services/test_game_schedules.py`:
    - Update the import block: replace `_schedule_join_notifications` with `schedule_join_notifications_for_game`.
    - Add a new test, `test_schedule_join_notifications_for_game_includes_overflow_participant`, marked:

      ```python
      @pytest.mark.xfail(
          strict=True,
          reason=(
              "Bug: schedule_join_notifications_for_game (née _schedule_join_notifications) "
              "only scheduled game.participants that partition_participants placed in "
              "the confirmed group, silently skipping waitlisted/overflow participants"
          ),
      )
      ```

      Build a `game` with `max_players=1` and two `MagicMock` participants with `user_id` set — one that `partition_participants` (unpatched, run for real against this game) will place in `confirmed` and one that lands in `overflow` — patch `shared.services.game_schedules.schedule_join_notification` (`AsyncMock`), call `await schedule_join_notifications_for_game(db, game)`, and assert `mock_schedule.call_count == 2` (one call per participant, confirmed and overflow alike).
- **Success**:
  - `uv run pytest tests/unit/shared/services/test_game_schedules.py -k includes_overflow -v` shows the test as `xfailed` (not `failed`, not `passed`), proving it currently detects the bug.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 26-27) - description of the still-present confirmed-only bug.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 84-107) - the buggy code excerpt this test targets.
  - .github/instructions/test-driven-development.instructions.md - Bug Fix Workflow (Step 1/Step 2: write regression test, confirm `xfailed`).
- **Dependencies**:
  - Phase 1 completion (`schedule_join_notification` must already live in this module for the fixed version to delegate to it).

### Task 2.2: Rename, fix, and delegate (GREEN), then remove the `xfail` marker

- **Files**:
  - `shared/services/game_schedules.py`:
    - Rename `_schedule_join_notifications` (currently lines 68-87) to public `schedule_join_notifications_for_game`, with an updated docstring explaining it (a) schedules every Discord participant, confirmed or waitlisted, and (b) is safe only when the entire `game.participants` list is known to contain no previously-scheduled rows (bulk "activation" moments), contrasted with `schedule_join_notification` for the single-new-participant case.
    - Replace the `partition_participants(...)` call and `for participant in partitioned.confirmed:` loop with `for participant in game.participants:`.
    - Replace the inline `NotificationSchedule(...)` construction + `db.add(...)` + `await db.flush()` with a delegated call:

      ```python
      if participant.user_id:
          await schedule_join_notification(
              db=db,
              game_id=game.id,
              participant_id=participant.id,
              game_scheduled_at=game.scheduled_at,
              delay_seconds=60,
          )
      ```

    - Update `setup_game_schedules`'s call site (currently line 64) from `await _schedule_join_notifications(db, game)` to `await schedule_join_notifications_for_game(db, game)`.
    - Update `setup_game_schedules`'s docstring line "Creates join-notification entries for confirmed participants and populates the reminder schedule." to no longer say "confirmed" (e.g. "Creates join-notification entries for every Discord participant, confirmed or waitlisted, and populates the reminder schedule.").
  - `tests/unit/shared/services/test_game_schedules.py`:
    - Rewrite `test_setup_game_schedules_delegates_to_helpers` (currently lines 63-77): patch target `shared.services.game_schedules._schedule_join_notifications` → `shared.services.game_schedules.schedule_join_notifications_for_game`; rename `mock_join` accordingly; assertion becomes `mock_join.assert_awaited_once_with(db, game)`.
    - Rewrite `test_schedule_join_notifications_adds_entry_for_confirmed_participant_with_user_id` (currently lines 80-110) → rename to `test_schedule_join_notifications_for_game_delegates_for_confirmed_participant`: drop the `partition_participants` patch; patch `shared.services.game_schedules.schedule_join_notification` instead; call `await schedule_join_notifications_for_game(db, game)` with one participant with a `user_id`; assert `mock_schedule.assert_called_once_with(db=db, game_id=game.id, participant_id=participant.id, game_scheduled_at=game.scheduled_at, delay_seconds=60)`.
    - Rewrite `test_schedule_join_notifications_skips_participant_without_user_id` (currently lines 113-125) similarly: drop `partition_participants` patch, patch `schedule_join_notification`, assert `mock_schedule.assert_not_called()`.
    - Remove the `@pytest.mark.xfail(...)` decorator added in Task 2.1 from `test_schedule_join_notifications_for_game_includes_overflow_participant` — no other change to that test.
- **Success**:
  - `shared.services.game_schedules._schedule_join_notifications` no longer exists (confirm via `grep -rn "_schedule_join_notifications\b" shared/`).
  - `schedule_join_notifications_for_game` iterates all of `game.participants` and delegates to `schedule_join_notification` for each participant with a `user_id`.
  - `test_schedule_join_notifications_for_game_includes_overflow_participant` now passes without `xfail` (strict mode would otherwise error on an unexpected pass, confirming the marker was actually removed).
  - `uv run pytest tests/unit/shared/services/test_game_schedules.py` and `uv run mypy shared/ services/` both green.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 162-166) - Recommended Approach primitive (2).
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 179) - Key Tasks item 2.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 183) - Key Tasks item 6 (bug-fix TDD workflow for this bug).
  - .github/instructions/test-driven-development.instructions.md - Bug Fix Workflow (Step 3/Step 4: fix, remove marker).
- **Dependencies**:
  - Task 2.1 completion (regression test must exist and be confirmed `xfailed` first).

## Phase 3: Delete `GameService._schedule_join_notifications_for_game` and repoint its callers

### Task 3.1: Write the regression test for the `_add_new_mentions` duplicate-scheduling bug (RED)

Prove that adding one new mention to a game that already has other, previously-scheduled participants currently re-schedules (and would re-notify) everyone, not just the new participant.

- **Files**:
  - `tests/unit/api/services/test_games.py`:
    - In `TestAddNewMentions` (class starts at line 737), add `test_only_schedules_notification_for_newly_added_participant`, marked:

      ```python
      @pytest.mark.xfail(
          strict=True,
          reason=(
              "Bug: _add_new_mentions calls the bulk-sweep "
              "_schedule_join_notifications_for_game after the loop, re-scheduling "
              "(and re-notifying) every pre-existing participant on every host edit "
              "that adds even one more mention"
          ),
      )
      ```

      Build a `game` (via `_make_game()`) whose `game.participants` already contains one existing `MagicMock(spec=participant_model.GameParticipant)` with `.id`/`.user_id` set (representing a participant added and scheduled on a prior edit); mock `participant_resolver.resolve_initial_participants`/`ensure_user_exists` to resolve exactly one new discord mention (same pattern as `test_adds_discord_participant`); patch `services.api.services.games.schedule_join_notification` (`AsyncMock`); call `await game_service._add_new_mentions(game, [("@user", 1)])`; assert `mock_schedule.assert_called_once_with(db=mock_db, game_id=game.id, participant_id=<newly-added participant>.id, game_scheduled_at=game.scheduled_at, delay_seconds=60)`, where `<newly-added participant>` is retrieved via `mock_db.add.call_args_list[-1][0][0]` (the object created by `_add_new_mentions`, not the pre-existing one).
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py -k only_schedules_notification_for_newly_added -v` shows the test as `xfailed`.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 14-15) - description of the bug.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 79-80) - the two conflated usage patterns; `_add_new_mentions` "incorrectly not used" per-participant scheduling.
  - .github/instructions/test-driven-development.instructions.md - Bug Fix Workflow (Step 1/Step 2).
- **Dependencies**:
  - Phase 2 completion (`schedule_join_notifications_for_game` must exist so `_setup_game_schedules` can be repointed in this same phase).

### Task 3.2: Repoint `GameService`, delete the dead method (GREEN), remove the `xfail` marker

- **Files**:
  - `services/api/services/games.py`:
    - Extend the `shared.services.game_schedules` import (currently line 67, after Phase 1's Task 1.2 edit reads `from shared.services.game_schedules import clone_game_for_recurrence, schedule_join_notification`) into a parenthesized multi-import block:

      ```python
      from shared.services.game_schedules import (
          clone_game_for_recurrence,
          schedule_join_notification,
          schedule_join_notifications_for_game,
      )
      ```

    - `_setup_game_schedules` (currently lines 565-585): replace `await self._schedule_join_notifications_for_game(game)` with `await schedule_join_notifications_for_game(self.db, game)`.
    - `_add_new_mentions` (currently lines 1498-1587):
      - Add a local `new_participants: list[participant_model.GameParticipant] = []` before the participant-creation loop.
      - Inside the loop, after `game.participants.append(new_participant)`, add `new_participants.append(new_participant)`.
      - Update the inline comment above `game.participants.append(new_participant)` to no longer reference `_schedule_join_notifications_for_game` by name (it now only concerns other consumers of `game.participants`, not scheduling).
      - After the existing `await self.db.flush()`, replace `await self._schedule_join_notifications_for_game(game)` with:

        ```python
        # Schedule a join notification for each participant just created here --
        # not the whole of game.participants, which may already contain other
        # participants scheduled (and notified) on a previous edit.
        for new_participant in new_participants:
            if new_participant.user_id:
                await schedule_join_notification(
                    db=self.db,
                    game_id=game.id,
                    participant_id=new_participant.id,
                    game_scheduled_at=game.scheduled_at,
                    delay_seconds=60,
                )
        ```

    - Delete `_schedule_join_notifications_for_game` (currently lines 1564-1587) in its entirety.
    - Remove the `@pytest.mark.xfail(...)` decorator added in Task 3.1 from `test_only_schedules_notification_for_newly_added_participant` — no other change to that test.
  - `tests/unit/api/services/test_games.py`:
    - Remove the "`- _schedule_join_notifications_for_game with confirmed participants`" bullet from the module docstring (currently line 31).
    - Delete the entire `TestScheduleJoinNotifications` class (currently lines 632-730) — its target method no longer exists; equivalent coverage (confirmed-and-overflow participants scheduled, no-`user_id` participants skipped) now lives in `tests/unit/shared/services/test_game_schedules.py` from Phase 2.
  - `tests/unit/services/api/services/test_games_service.py`:
    - `test_setup_game_schedules_with_reminders_and_duration` (currently lines 1275-1309): change `patch.object(game_service, "_schedule_join_notifications_for_game", new_callable=AsyncMock)` to `patch("services.api.services.games.schedule_join_notifications_for_game", new_callable=AsyncMock)`; change `mock_join_notifications.assert_called_once_with(game)` to `mock_join_notifications.assert_called_once_with(game_service.db, game)`.
    - `test_setup_game_schedules_without_duration` (currently lines 1312-1346): same two changes.
- **Success**:
  - `grep -rn "_schedule_join_notifications_for_game" services/ tests/unit tests/integration` returns no matches (aside from any unrelated historical `.copilot-tracking/changes/` records, which are not modified).
  - `test_only_schedules_notification_for_newly_added_participant` passes without `xfail`.
  - `grep -rn "GameParticipant(" services/ shared/` shows every non-test "create participant, then schedule" call site delegating to `schedule_join_notification` (per-participant) or `schedule_join_notifications_for_game` (bulk).
  - `uv run pytest tests/unit` and `uv run mypy shared/ services/` both green.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 157-166) - Recommended Approach (both primitives, plus explicit deletion of the wrapper).
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 180) - Key Tasks item 3.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 183) - Key Tasks item 6 (bug-fix TDD workflow for this bug).
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 187) - Success Criteria.
  - .github/instructions/test-driven-development.instructions.md - Bug Fix Workflow (Step 3/Step 4).
- **Dependencies**:
  - Task 3.1 completion (regression test must exist and be confirmed `xfailed` first).

### Task 3.3: Verify the full consolidation against the existing integration and e2e suites

Phases 1-3's own gates (`uv run pytest tests/unit`, `uv run mypy shared/ services/`) never exercise `services/api/services/games.py` or `shared/services/game_schedules.py` through a real API + real database, and never exercise the bot's DM-delivery path end-to-end — yet both are exactly what several existing integration and e2e tests already do. Close that verification gap once, here, after Phase 3 reaches its GREEN state (both `_setup_game_schedules` and `_add_new_mentions` repointed at the shared functions, `_schedule_join_notifications_for_game` deleted) — not after every task, and not after Phases 1 or 2 individually, since these suites exercise the end-to-end result of all three phases combined, not any single phase in isolation.

- **Files**: none modified — verification only.
- **Success**:
  - An integration run scoped to the four files confirmed (against the pre-refactor code, earlier this session) to exercise `join_game`, `_setup_game_schedules`, `_add_new_mentions`, and `shared/services/game_schedules.py` through real API + DB — `tests/integration/test_game_signup_methods.py`, `tests/integration/test_games_crud.py`, `tests/integration/test_leave_game_promotion.py`, `tests/integration/test_player_removed_queue.py` — passes (all 33 tests green, matching that earlier baseline). Follow `.github/instructions/test-execution.instructions.md` for output capture (`tee`, before any filtering) and use a timeout of at least 10 minutes.
  - An e2e run scoped to `tests/e2e/test_join_notification.py` passes, including its 5 tests that exercise the consolidated functions end-to-end (`test_join_dm_says_waitlist_for_host_selected_with_waitlist`, `test_join_dm_has_instructions_when_host_adds_directly_to_confirmed_hsw_slot`, `test_join_dm_says_waitlist_for_host_added_self_signup_overflow`, `test_join_notification_with_signup_instructions`, `test_join_notification_without_signup_instructions`). Follow `.github/instructions/test-execution.instructions.md` for output capture and use a timeout of at least 15 minutes.
  - No coverage is added or expected for `services/bot/handlers/join_game.py::handle_join_game` in this task — see the note in Task 1.3.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 187) - Success Criteria: "full unit + integration + e2e suites green."
  - .github/instructions/test-execution.instructions.md - output-capture and timeout rules for `scripts/run-integration-tests.sh` / `scripts/run-e2e-tests.sh`.
- **Dependencies**:
  - Task 3.2 completion (Phase 3's GREEN state: both callers repointed, dead method deleted, unit + mypy gates green).

## Phase 4: Remove dead code — `shared/data_access/guild_queries.py::add_participant`

This is plain dead-code removal (Key Tasks item 8), not a bug fix: `add_participant` behaves correctly, it simply has no production caller. No `xfail`/TDD workflow applies — per the "retrofitting tests for correct code" / removal guidance in `.github/instructions/test-driven-development.instructions.md`, just remove the code and its dedicated tests, then confirm the suite is still green. Unlike a pure delete, two of the surrounding integration tests use `add_participant` only as setup scaffolding for a _different_ function under test; those call sites must be swapped for a direct DB insert in the same phase (per the Ordering Rule — every caller, including test callers used only for setup, must be updated in the same phase as the removal) rather than left broken.

### Task 4.1: Re-confirm zero production callers

- **Files**: none modified — verification only.
- **Success**:
  - `grep -rn "guild_queries\.add_participant\|guild_queries import.*add_participant" services/ shared/` (excluding `shared/data_access/guild_queries.py`'s own definition) returns no matches.
  - `grep -rln "add_participant" tests/` shows only `tests/unit/shared/data_access/test_guild_queries_unit.py` and `tests/integration/test_guild_queries_integration.py`.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 37-39) - original "no production callers" finding, being re-confirmed since time has passed.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 185) - Key Tasks item 8.
- **Dependencies**:
  - None (can run independently of Phases 1-3, but sequenced last per the coordinator's request).

### Task 4.2: Remove `add_participant` from production code and its dedicated unit tests

- **Files**:
  - `shared/data_access/guild_queries.py` - delete `add_participant` (currently lines 206-249) in its entirety, including its blank-line separators from the surrounding `delete_game`/`remove_participant` functions.
  - `tests/unit/shared/data_access/test_guild_queries_unit.py` - delete the entire `TestAddParticipant` class (currently lines 367-423), leaving `TestRemoveParticipant` and every other class untouched. The `GameParticipant` import (line 41) stays — still used by `TestRemoveParticipant`. The `sample_game` fixture stays — still used by many other classes.
- **Success**:
  - `shared.data_access.guild_queries` no longer defines `add_participant`.
  - `TestAddParticipant` no longer exists in the unit test file; every other class in the file is unchanged.
  - `uv run pytest tests/unit/shared/data_access/test_guild_queries_unit.py` green.
  - `uv run mypy shared/ services/` green (no dangling references).
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Lines 37-39) - `add_participant` definition and dead-code finding.
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 185) - Key Tasks item 8.
- **Dependencies**:
  - Task 4.1 completion.

### Task 4.3: Remove `add_participant`'s dedicated integration tests, and fix the tests that used it only as setup scaffolding

- **Files**:
  - `tests/integration/test_guild_queries_integration.py`:
    - Delete `test_add_participant_validates_game_belongs_to_guild` and `test_add_participant_succeeds_for_correct_guild` in their entirety (currently lines 262-309, including their `@pytest.mark.asyncio` decorators) — these exercise `add_participant` directly and have no other purpose. Leave the `# Participant Operations Integration Tests` section header (lines 257-259) in place; it still applies to the remaining `remove_participant`/`list_user_games` tests.
    - Add a small setup helper near `make_game_data` (after it, before the `# Game Operations Integration Tests` section header):

      ```python
      def _seed_participant(game_id: str, user_id: str) -> GameParticipant:
          """Build a GameParticipant row for test setup only.

          guild_queries.add_participant was removed as dead production code;
          these tests only need a participant to already exist so they can
          exercise remove_participant / list_user_games, not add_participant
          itself.
          """
          return GameParticipant(
              id=str(uuid.uuid4()),
              game_session_id=game_id,
              user_id=user_id,
              position_type=ParticipantType.SELF_ADDED,
              position=0,
          )
      ```

      Add `from shared.models.participant import GameParticipant, ParticipantType` (extending the existing `from shared.models.participant import ParticipantType` import line) — `uuid` is already imported at the top of the file.

    - In `test_remove_participant_validates_game_belongs_to_guild` (currently lines 313-334): replace the `await guild_queries.add_participant(admin_db, guild_a["id"], game.id, user["id"], {"position_type": ParticipantType.SELF_ADDED, "position": 0})` call with `admin_db.add(_seed_participant(game.id, user["id"]))`, keeping the following `await admin_db.commit()` unchanged.
    - In `test_remove_participant_succeeds_for_correct_guild` (currently lines 338-362): same replacement.
    - In `test_list_user_games_returns_only_guild_games` (currently lines 366-409): replace both `await guild_queries.add_participant(...)` calls (one for `game_a`/`guild_a`, one for `game_b`/`guild_b`) with `admin_db.add(_seed_participant(game_a.id, user["id"]))` and `admin_db.add(_seed_participant(game_b.id, user["id"]))` respectively, keeping the single trailing `await admin_db.commit()` unchanged.
- **Success**:
  - `grep -n "add_participant" tests/integration/test_guild_queries_integration.py` shows only the new `_seed_participant` helper's docstring/name, no `guild_queries.add_participant` call.
  - `test_remove_participant_validates_game_belongs_to_guild`, `test_remove_participant_succeeds_for_correct_guild`, and `test_list_user_games_returns_only_guild_games` still pass, exercising the same behavior (guild-scoped removal / guild-scoped listing) as before, now seeded via direct insert instead of the removed function.
  - `scripts/run-integration-tests.sh` (scoped to `tests/integration/test_guild_queries_integration.py`) passes, per `.github/instructions/test-execution.instructions.md` output-capture rules.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 39) - "Only referenced from `tests/unit/shared/data_access/test_guild_queries_unit.py` and `tests/integration/test_guild_queries_integration.py`."
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 185) - Key Tasks item 8.
- **Dependencies**:
  - Task 4.2 completion (production function must already be gone so these tests can't accidentally keep exercising it).

### Task 4.4: Full-suite confirmation

- **Files**: none — verification only.
- **Success**:
  - `grep -rn "add_participant" services/ shared/ tests/` returns no matches other than `remove_participant`/unrelated substrings (e.g. confirm no stray reference survives anywhere).
  - `uv run pytest tests/unit` and `uv run mypy shared/ services/` both green.
  - `scripts/run-integration-tests.sh` (scoped appropriately) green, per `.github/instructions/test-execution.instructions.md`.
- **Research References**:
  - .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md (Line 185) - Key Tasks item 8.
- **Dependencies**:
  - Task 4.3 completion.

## Out of Scope (noted, not planned)

Per the research document's "Explicitly out of scope" section, these are separate follow-up candidates and have no phases here:

- `clone_game_for_recurrence`'s absence of join-notification scheduling for carried-over participants.
- `shared/services/game_schedules.py::_populate_reminder_schedule` vs. `NotificationScheduleService.populate_schedule` duplication.

## Dependencies

- No schema/migration changes, no new third-party dependencies.
- `uv run pytest tests/unit`, `uv run mypy shared/ services/` available locally (project's standard pre-commit gates).
- `scripts/run-integration-tests.sh` available locally for Phase 4's integration-test verification (per `.github/instructions/test-execution.instructions.md`).

## Success Criteria

- Exactly two shared primitives exist in `shared/services/game_schedules.py`: `schedule_join_notification` (per-participant) and `schedule_join_notifications_for_game` (bulk sweep, delegating to the former).
- `GameService._schedule_join_notifications_for_game` no longer exists anywhere.
- `schedule_join_notifications_for_game` schedules waitlisted participants, not just confirmed ones.
- `_add_new_mentions` schedules exactly one notification per newly-created participant, never re-sweeping pre-existing ones.
- `handle_join_game` (bot) and `join_game` (API) both call the same shared `schedule_join_notification` primitive.
- `shared/data_access/guild_queries.py::add_participant` no longer exists; its dedicated tests are gone; the tests that used it only as setup scaffolding (`test_remove_participant_validates_game_belongs_to_guild`, `test_remove_participant_succeeds_for_correct_guild`, `test_list_user_games_returns_only_guild_games`) still pass via direct-insert seeding.
- Full unit test suite (`uv run pytest tests/unit`) and `uv run mypy shared/ services/` green; e2e suite (`tests/e2e/test_join_notification.py`) collects and its import-only change does not alter behavior; `tests/integration/test_guild_queries_integration.py` green.
