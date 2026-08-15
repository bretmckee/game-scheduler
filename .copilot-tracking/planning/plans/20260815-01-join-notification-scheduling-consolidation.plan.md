---
applyTo: '.copilot-tracking/changes/20260815-01-join-notification-scheduling-consolidation-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Consolidate join-notification scheduling into shared primitives

## Overview

Consolidate the scattered "schedule a join notification for a new game participant" logic — currently duplicated across `services/api/services/games.py`, `shared/services/game_schedules.py`, and `services/bot/handlers/join_game.py` — into exactly two shared primitives in `shared/services/game_schedules.py`: `schedule_join_notification` (per-participant) and `schedule_join_notifications_for_game` (bulk sweep), fixing two newly-discovered bugs along the way.

## Objectives

- Move `schedule_join_notification(db, game_id, participant_id, game_scheduled_at, delay_seconds=60)` from `services/api/services/notification_schedule.py` into `shared/services/game_schedules.py`, unchanged, and repoint every caller (`GameService.join_game`, `services/bot/handlers/join_game.py::handle_join_game`, later `GameService._add_new_mentions`) at the new location.
- Rename the private `_schedule_join_notifications` in `shared/services/game_schedules.py` to public `schedule_join_notifications_for_game`, fix it to iterate all of `game.participants` (not confirmed-only), and have it delegate to the moved primitive instead of constructing `NotificationSchedule` inline.
- Delete `GameService._schedule_join_notifications_for_game` outright and repoint its two callers (`_setup_game_schedules`, `_add_new_mentions`) directly at the appropriate shared function.
- Fix the `_add_new_mentions` duplicate-scheduling bug (it currently re-sweeps and would re-notify every pre-existing participant on every host edit that adds a mention) using the project's bug-fix TDD workflow.
- Update every existing unit/integration/e2e test whose patch target or import references a function being moved, renamed, or deleted.
- Verify the fully-consolidated result (end of Phase 3) against the existing integration and e2e suites that exercise these functions through real API+DB and real Discord DM delivery — not just unit tests + mypy.
- Remove the dead-code `shared/data_access/guild_queries.py::add_participant` (zero production callers) and its dedicated tests, fixing the unrelated tests that used it only as setup scaffolding.

## Research Summary

### Project Files

- `services/api/services/notification_schedule.py` - source location of `schedule_join_notification()`, being relocated.
- `shared/services/game_schedules.py` - target module for both consolidated primitives; already contains the buggy `_schedule_join_notifications` and its caller `setup_game_schedules`.
- `services/api/services/games.py` - `GameService.join_game`, `_setup_game_schedules`, `_add_new_mentions`, and the to-be-deleted `_schedule_join_notifications_for_game`.
- `services/bot/handlers/join_game.py` - `handle_join_game`'s independently hand-copied inline schedule construction.
- `tests/unit/shared/services/test_game_schedules.py`, `tests/unit/api/services/test_games.py`, `tests/unit/services/api/services/test_games_edit_participants.py`, `tests/unit/services/api/services/test_games_service.py`, `tests/e2e/test_join_notification.py` - tests whose patch targets/imports reference the functions being moved, renamed, or deleted.
- `shared/data_access/guild_queries.py` - dead-code `add_participant` function, zero production callers.
- `tests/unit/shared/data_access/test_guild_queries_unit.py`, `tests/integration/test_guild_queries_integration.py` - dedicated `add_participant` test coverage to remove, plus incidental `add_participant`-as-setup usages in unrelated `remove_participant`/`list_user_games` tests to fix.

### External References

- .copilot-tracking/research/20260815-01-join-notification-scheduling-consolidation-research.md - full research findings, Recommended Approach, and Implementation Guidance (Key Tasks 1-8, all in scope; the "Explicitly out of scope" section covers only `clone_game_for_recurrence` and `_populate_reminder_schedule` follow-ups) backing this plan.

### Standards References

- .github/instructions/test-driven-development.instructions.md - Bug Fix Workflow (xfail regression test → fix → remove marker) applied to the two newly-discovered bugs; "retrofitting tests for correct code" convention applied to the pure relocations.
- .github/instructions/unit-tests.instructions.md - falsifiable, real-argument mock assertions required for all new/rewritten tests.
- .github/instructions/fastapi-transaction-patterns.instructions.md - both primitives remain non-committing; callers commit.

## Implementation Checklist

### [ ] Phase 1: Relocate `schedule_join_notification` primitive to `shared/services/game_schedules.py`

- [ ] Task 1.1: Move `schedule_join_notification()` verbatim into `shared/services/game_schedules.py`; delete it from `services/api/services/notification_schedule.py`
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 11-28)

- [ ] Task 1.2: Repoint `services/api/services/games.py`'s import to the new location
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 29-45)

- [ ] Task 1.3: Repoint `services/bot/handlers/join_game.py`'s `handle_join_game` to call the shared primitive instead of constructing `NotificationSchedule` inline (note: no e2e coverage exists or can exist for this handler — see task details)
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 46-80)

- [ ] Task 1.4: Update `tests/e2e/test_join_notification.py`'s import (static/import check only — behavioral verification happens once in Phase 3 Task 3.3)
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 81-91)

- [ ] Task 1.5: Add direct unit test coverage for the relocated primitive in `tests/unit/shared/services/test_game_schedules.py`
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 92-109)

### [ ] Phase 2: Fix the confirmed-only bug and rename `_schedule_join_notifications` to public `schedule_join_notifications_for_game`

- [ ] Task 2.1: Write the `xfail` regression test proving the confirmed-only bug (RED)
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 112-141)

- [ ] Task 2.2: Rename, fix (iterate all participants), and delegate to the moved primitive (GREEN); remove the `xfail` marker; update `setup_game_schedules`'s call site and docstring
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 142-180)

### [ ] Phase 3: Delete `GameService._schedule_join_notifications_for_game` and repoint its callers

- [ ] Task 3.1: Write the `xfail` regression test proving the `_add_new_mentions` duplicate-scheduling bug (RED)
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 183-212)

- [ ] Task 3.2: Repoint `_setup_game_schedules` and `_add_new_mentions` at the shared functions directly; delete `_schedule_join_notifications_for_game` (GREEN); remove the `xfail` marker; update `test_games.py` and `test_games_service.py`
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 213-270)

- [ ] Task 3.3: Run the existing integration suite (scoped to the 4 files confirmed to exercise these functions) and the existing e2e suite (`tests/e2e/test_join_notification.py`) once, now that Phase 3's GREEN state is reached
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 271-285)

### [ ] Phase 4: Remove dead code — `shared/data_access/guild_queries.py::add_participant`

- [ ] Task 4.1: Re-confirm zero production callers (re-run the research doc's grep)
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 290-301)

- [ ] Task 4.2: Remove `add_participant` from `shared/data_access/guild_queries.py` and delete its dedicated `TestAddParticipant` class in `tests/unit/shared/data_access/test_guild_queries_unit.py`
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 302-317)

- [ ] Task 4.3: Delete `add_participant`'s dedicated integration tests in `tests/integration/test_guild_queries_integration.py`; replace the incidental `add_participant`-as-setup calls in `remove_participant`/`list_user_games` tests with a direct-insert helper
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 318-356)

- [ ] Task 4.4: Full-suite confirmation (unit, mypy, scoped integration)
  - Details: .copilot-tracking/planning/details/20260815-01-join-notification-scheduling-consolidation-details.md (Lines 357-368)

## Dependencies

- No schema/migration changes, no new third-party dependencies — pure internal refactor plus dead-code removal.
- `uv run pytest tests/unit` and `uv run mypy shared/ services/` runnable locally (standard pre-commit gates for this repo).
- `scripts/run-integration-tests.sh` runnable locally (needed for Phase 3 Task 3.3's and Phase 4's integration-test verification) and `scripts/run-e2e-tests.sh` runnable locally (needed for Phase 3 Task 3.3's e2e verification); both must be run per `.github/instructions/test-execution.instructions.md` (full output captured via `tee` before any filtering; timeout of at least 10 minutes for integration, at least 15 minutes for e2e).
- Sequencing is load-bearing: Phase 1 (move the primitive) must land before Phase 2 (the sweep function needs to call the already-relocated primitive); Phase 3 depends on both Phase 1 and Phase 2 being in place, and its Task 3.3 integration/e2e verification runs only once, after Task 3.2 reaches GREEN — not after every task or every phase. Phase 4 (dead-code removal) is independent of Phases 1-3 and could in principle run first, but is sequenced last per the coordinator's request.

## Success Criteria

- `shared/services/game_schedules.py` contains exactly two public join-notification primitives: `schedule_join_notification` and `schedule_join_notifications_for_game`, the latter delegating to the former.
- `GameService._schedule_join_notifications_for_game` no longer exists anywhere in the codebase.
- `schedule_join_notifications_for_game` schedules notifications for waitlisted participants, not just confirmed ones.
- `_add_new_mentions` schedules exactly one notification per newly-created participant and never re-sweeps pre-existing ones.
- `handle_join_game` (bot) and `join_game` (API) both call the same shared `schedule_join_notification` primitive; no inline `NotificationSchedule` construction remains outside the two shared primitives.
- Both newly-discovered bugs (confirmed-only sweep, `_add_new_mentions` duplicate scheduling) were fixed via the project's xfail-regression-test bug-fix workflow, with the markers removed after the fix.
- `shared/data_access/guild_queries.py::add_participant` no longer exists; no test file references it; the tests that used it only for setup now seed participants via direct insert and still pass.
- `uv run pytest tests/unit` and `uv run mypy shared/ services/` are green.
- The integration suite scoped to `tests/integration/test_game_signup_methods.py`, `tests/integration/test_games_crud.py`, `tests/integration/test_leave_game_promotion.py`, and `tests/integration/test_player_removed_queue.py` (33 tests) passes against the fully-consolidated Phase 3 result, matching the pre-refactor baseline.
- `tests/e2e/test_join_notification.py` passes in full against the fully-consolidated Phase 3 result, including its 5 tests exercising the consolidated functions end-to-end.
- `tests/integration/test_guild_queries_integration.py` passes.
