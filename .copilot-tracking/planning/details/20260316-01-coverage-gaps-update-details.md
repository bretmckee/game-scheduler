<!-- markdownlint-disable-file -->

# Task Details: Coverage Infrastructure Fix and Gap Analysis Update

## Research Reference

**Source Research**: #file:../research/20260316-01-coverage-gaps-update-research.md

## Phase 1: Fix Coverage Infrastructure

### Task 1.1: Rename test runner COVERAGE_FILE in `compose.int.yaml`

Change line 112 in `compose.int.yaml` from `.coverage.integration` to `runner.integration`.

- **Files**:
  - `compose.int.yaml` — change `COVERAGE_FILE: /app/coverage/.coverage.integration` to `COVERAGE_FILE: /app/coverage/runner.integration`
- **Success**:
  - `grep -n "COVERAGE_FILE" compose.int.yaml` shows only non-hidden file names
  - No `.coverage.*` entries remain in the integration compose file
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 1–30) — file analysis confirming hidden-file locations
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 143–155) — fix specification with before/after YAML for `compose.int.yaml`
- **Dependencies**:
  - None

### Task 1.2: Rename test runner COVERAGE_FILE in `compose.e2e.yaml`

Change line 130 in `compose.e2e.yaml` from `.coverage.e2e` to `runner.e2e`.

- **Files**:
  - `compose.e2e.yaml` — change `COVERAGE_FILE: /app/coverage/.coverage.e2e` to `COVERAGE_FILE: /app/coverage/runner.e2e`
- **Success**:
  - `grep -n "COVERAGE_FILE" compose.e2e.yaml` shows only non-hidden file names
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 1–30) — file analysis confirming hidden-file locations
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 156–165) — fix specification with before/after YAML for `compose.e2e.yaml`
- **Dependencies**:
  - None (independent of Task 1.1)

### Task 1.3: Remove hidden coverage files from `coverage/` if present

Delete `.coverage.integration` and `.coverage.e2e` from the `coverage/` directory if they exist from prior runs.

- **Files**:
  - `coverage/.coverage.integration` — delete if present
  - `coverage/.coverage.e2e` — delete if present
- **Success**:
  - `ls -la coverage/` shows no dotfiles matching `.coverage.*`
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 178–195) — implementation guidance listing this cleanup step
- **Dependencies**:
  - None

### Task 1.4: Verify combined coverage reaches ≥87.69%

After renaming (requires a fresh integration + e2e run to produce `runner.integration` and `runner.e2e`), run `scripts/coverage-report.sh` and confirm the reported total is ≥87.69%.

- **Files**:
  - `coverage/runner.integration` — produced by integration test run
  - `coverage/runner.e2e` — produced by e2e test run
- **Success**:
  - `scripts/coverage-report.sh` total shows ≥87.69%
  - `join_game.py` shows 100%, `leave_game.py` shows 100%, `button_handler.py` shows ≥96%
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 32–55) — coverage combination verification data with expected values
- **Dependencies**:
  - Tasks 1.1, 1.2, 1.3 complete
  - Fresh integration and e2e test runs against updated compose files

## Phase 2: Unit Test `notification_service.py`

### Task 2.1: Write unit tests for `NotificationService.send_game_reminder_due()`

Create `tests/unit/scheduler/test_notification_service.py` with three test cases covering the full execution surface of `send_game_reminder_due()`.

The method (lines 24–106) connects a `SyncEventPublisher`, publishes a message, then closes in a `finally` block. All paths are covered by mocking `SyncEventPublisher`.

Test cases:

1. **Happy path** — publisher connects, publishes successfully, closes; method returns `True`
2. **Exception during publish** — publisher connects but `publish()` raises; returns `False`, `close()` still called via finally
3. **Exception during connect** — `connect()` raises before any publish; returns `False`

- **Files**:
  - `tests/unit/scheduler/test_notification_service.py` — new test file (~30 lines)
- **Success**:
  - `uv run pytest tests/unit/scheduler/test_notification_service.py -v` — all 3 tests pass
  - `services/scheduler/services/notification_service.py` shows 100% coverage
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 58–95) — root cause analysis and impact table
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 163–175) — recommended approach with the three test scenarios
- **Dependencies**:
  - None (independent of Phase 1)

## Phase 3: Unit Test `events/handlers.py`

### Task 3.1: Unit tests for game-created and game-updated handler error paths

Cover error/branch paths in `_handle_game_created` and `_handle_game_updated`, targeting missing lines in the ~155–239 range.

Use `unittest.mock.AsyncMock` / `MagicMock` for the Discord client and `BotEventPublisher` dependencies. Place tests in `tests/unit/bot/events/`.

- **Files**:
  - `tests/unit/bot/events/test_handlers_game_events.py` — new test file
- **Success**:
  - All new tests pass
  - Lines 155, 161–179, 188, 190, 197, 199, 208, 210, 213, 225, 231–232, 234, 237–239 covered
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 100–115) — full missing line list for `handlers.py`
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 175–190) — recommended handler grouping approach
- **Dependencies**:
  - None (independent of Phases 1–2)

### Task 3.2: Unit tests for notification, player-removal, and cancellation handler paths

Cover `_handle_notification_due`, `_handle_player_removed`, `_handle_game_cancelled` error and branch paths targeting missing lines in the ~262–456 range.

- **Files**:
  - `tests/unit/bot/events/test_handlers_lifecycle_events.py` — new test file
- **Success**:
  - All new tests pass
  - Lines 262–276, 282, 284, 289, 291, 297, 306–327, 332, 346, 348–351, 373, 378, 392, 394, 415, 426, 431, 442–445, 453–456 covered
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 100–115) — full missing line list for `handlers.py`
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 175–195) — recommended approach and handler grouping
- **Dependencies**:
  - Task 3.1 complete (shared mock setup pattern established)

### Task 3.3: Unit tests for remaining handler error paths to reach ≥85%

Cover remaining missing lines in `handlers.py` (lines ~464–1408) spread across the remaining handler methods. Split into multiple files by handler group if needed.

- **Files**:
  - `tests/unit/bot/events/test_handlers_misc.py` — new test file (or multiple files by handler group)
- **Success**:
  - All new tests pass
  - Combined coverage of `services/bot/events/handlers.py` reaches ≥85%
- **Research References**:
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 100–115) — full missing line list for `handlers.py`
  - #file:../research/20260316-01-coverage-gaps-update-research.md (Lines 175–195) — recommended approach
- **Dependencies**:
  - Task 3.2 complete

## Dependencies

- `uv` and `pytest` for running tests
- `coverage.py` for measurement
- Docker (for integration/e2e verification in Phase 1 Task 1.4)

## Success Criteria

- `scripts/coverage-report.sh` reports ≥87.69% total without hidden-file workarounds
- `notification_service.py` at 100% coverage
- `events/handlers.py` at ≥85% coverage
- All new tests pass in the full unit suite (`uv run pytest tests/unit/ -qq`)
