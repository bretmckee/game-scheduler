---
applyTo: '.copilot-tracking/changes/20260816-01-reminder-schedule-consolidation-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Consolidate reminder-schedule population into a single shared implementation

## Overview

Rename the private `_populate_reminder_schedule` in `shared/services/game_schedules.py` to a public `populate_reminder_schedule`, and make `NotificationScheduleService.populate_schedule` a thin delegating wrapper around it, eliminating the byte-for-byte duplicated reminder-population logic between the bot's shared module and the API's `notification_schedule.py`.

## Objectives

- Exactly one implementation of "populate reminder-notification rows for a game" exists, in `shared/services/game_schedules.py`, importable by both the bot and the API service.
- `NotificationScheduleService.populate_schedule`'s body becomes a single delegating call to the shared primitive; `update_schedule`'s already-correct DELETE-scoping fix (from commit `311e6c48`) and `clear_schedule` are left structurally untouched.
- No behavior change: identical field construction, identical future/past reminder gating, no new commit points.

## Research Summary

### Project Files

- `shared/services/game_schedules.py` - contains the private `_populate_reminder_schedule` (to be renamed public) and its sole in-module caller `setup_game_schedules`.
- `services/api/services/notification_schedule.py` - contains `NotificationScheduleService.populate_schedule` (duplicate logic, to become a delegating wrapper), `update_schedule` (untouched), and `clear_schedule` (untouched).
- `tests/unit/shared/services/test_game_schedules.py` - tests importing/patching `_populate_reminder_schedule` by its current private name; must reference the renamed public function.
- `tests/unit/services/api/services/test_notification_schedule.py` - existing `populate_schedule` tests (assert on `mock_db.add`, not on which function performed the add) plus `update_schedule`/`clear_schedule` tests that must remain green unmodified.
- `tests/integration/test_notification_schedule.py` - `test_update_schedule_preserves_join_notification_row`, the `311e6c48` regression test exercising `update_schedule` → `populate_schedule` against real PostgreSQL; must remain green unmodified.
- `services/api/services/games.py` - `_setup_game_schedules` and `_process_game_update_schedules`, the only production callers of `NotificationScheduleService`; unaffected by this consolidation (signature unchanged).

### External References

- .copilot-tracking/research/20260815-02-reminder-schedule-consolidation-research.md - full research findings, confirmed byte-for-byte duplication, Recommended Approach, and Implementation Guidance backing this plan.

### Standards References

- .github/instructions/test-driven-development.instructions.md - "retrofitting tests for already-correct code" convention (no stub/xfail; this is a pure rename/delegate, not a bug fix).
- .github/instructions/unit-tests.instructions.md - falsifiable, real-argument mock assertions for the new delegation test.
- .github/instructions/fastapi-transaction-patterns.instructions.md - both the shared primitive and the delegating wrapper remain non-committing; callers commit.

## Implementation Checklist

### [ ] Phase 1: Rename `_populate_reminder_schedule` to public `populate_reminder_schedule` in the shared module

- [ ] Task 1.1: Rename the function, add logging parity, and update `setup_game_schedules`'s call site
  - Details: .copilot-tracking/planning/details/20260816-01-reminder-schedule-consolidation-details.md (Lines 11-40)

- [ ] Task 1.2: Update `tests/unit/shared/services/test_game_schedules.py` to reference the renamed public function
  - Details: .copilot-tracking/planning/details/20260816-01-reminder-schedule-consolidation-details.md (Lines 41-63)

### [ ] Phase 2: Make `NotificationScheduleService.populate_schedule` a thin delegating wrapper

- [ ] Task 2.1: Replace `populate_schedule`'s body with a delegated call; remove now-unused imports
  - Details: .copilot-tracking/planning/details/20260816-01-reminder-schedule-consolidation-details.md (Lines 66-92)

- [ ] Task 2.2: Add a delegation-assertion test; confirm existing `populate_schedule`/`update_schedule`/`clear_schedule` tests remain green unmodified
  - Details: .copilot-tracking/planning/details/20260816-01-reminder-schedule-consolidation-details.md (Lines 93-118)

- [ ] Task 2.3: Verify the `311e6c48` integration regression test remains green against the delegated implementation
  - Details: .copilot-tracking/planning/details/20260816-01-reminder-schedule-consolidation-details.md (Lines 119-136)

## Dependencies

- No schema/migration changes, no new third-party dependencies, no behavior change — pure internal refactor.
- `uv run pytest tests/unit` and `uv run mypy shared/ services/` runnable locally (standard pre-commit gates for this repo).
- `scripts/run-integration-tests.sh` runnable locally (needed for Phase 2 Task 2.3's scoped verification), run per `.github/instructions/test-execution.instructions.md` (full output captured via `tee` before any filtering; timeout of at least 10 minutes).
- Sequencing is load-bearing: Phase 1 (the public primitive must exist) must land before Phase 2 (the delegating wrapper imports and calls it).

## Success Criteria

- `grep -rn "_populate_reminder_schedule\b" services/ shared/` finds no references anywhere.
- `shared.services.game_schedules.populate_reminder_schedule` is public, has a docstring consistent with its siblings in the same module, and is the sole implementation constructing reminder `NotificationSchedule` rows.
- `NotificationScheduleService.populate_schedule`'s body is a single delegating call to `populate_reminder_schedule(self.db, game, reminder_minutes)`.
- `update_schedule`'s DELETE-scoping behavior (from `311e6c48`) and `clear_schedule` are unchanged, with zero modifications to their own code.
- `uv run pytest tests/unit` and `uv run mypy shared/ services/` are green.
- `tests/unit/services/api/services/test_notification_schedule.py` and `tests/unit/shared/services/test_game_schedules.py` are green, including the new delegation-assertion test.
- `tests/integration/test_notification_schedule.py` (`test_update_schedule_preserves_join_notification_row`) remains green with zero modifications to that test.
