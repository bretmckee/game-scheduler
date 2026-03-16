<!-- markdownlint-disable-file -->

# Task Research Notes: Coverage Infrastructure Fix and Gap Analysis Update

## Research Executed

### File Analysis

- `compose.int.yaml` lines 27–112
  - Service containers (`init`, `api`, `scheduler`, `retry-daemon`) write to non-hidden files: `init.integration`, `api.integration`, `scheduler.integration`, `retry.integration`
  - Test runner service (`integration-tests`) writes to hidden file: `/app/coverage/.coverage.integration` (line 112)
- `compose.e2e.yaml` lines 27–130
  - Service containers write to non-hidden files: `init.e2e`, `api.e2e`, `bot.e2e`, `scheduler.e2e`
  - Test runner service (`e2e-tests`) writes to hidden file: `/app/coverage/.coverage.e2e` (line 130)
- `scripts/coverage-report.sh`
  - Final combine step: `uv run coverage combine --keep coverage/*`
  - No hardcoded references to `.coverage.integration` or `.coverage.e2e`
  - Shell glob `coverage/*` skips dotfiles by POSIX convention — hidden files never included

### Code Search Results

- `grep -n "COVERAGE_FILE"` in both compose files
  - All service containers: non-hidden names (`init.integration`, `api.integration`, etc.)
  - Test runner containers: hidden names (`.coverage.integration`, `.coverage.e2e`)
- `uv run coverage report --data-file=coverage/.coverage.integration`
  - `join_game.py` → 100%, `leave_game.py` → 100%, `button_handler.py` → 96.55%
  - Confirms test runner captures coverage of handler code called directly from tests

### Coverage Combination Verification

- Combining `coverage/*` only (current behavior) → **84.26%** combined
- Combining `coverage/*` + hidden files explicitly → **87.69%** combined
- Difference accounts for test runner process coverage (handler code imported and called in-process)

### Project Conventions

- Non-hidden naming pattern established by all service container entries: `<service>.<testtype>`
- No other hidden coverage files exist; this is an isolated inconsistency from initial setup

---

## Key Discoveries

### Root Cause of Hidden-File Bug

When the integration test infrastructure was established, the test runner containers were configured to
write to `/app/coverage/.coverage.integration` and `/app/coverage/.coverage.e2e`. These mirror the
default `coverage.py` filename convention (`.coverage`). However, the service containers were given
descriptive non-hidden names (`api.integration`, `bot.e2e`, etc.).

The final combine step uses `coverage/*` which, per POSIX glob semantics, excludes dotfiles. The test
runner files are silently excluded from every combined report.

The bot handler tests (`test_join_game.py`, `test_leave_game.py`, `test_button_handler.py`) call
handler functions directly in the test-runner process, not over HTTP. The handler coverage therefore
lands in the test runner's file, not in a service container file. This caused `join_game.py`,
`leave_game.py`, and `button_handler.py` to appear near 0% in combined reports despite being
well-tested.

### Impact of the Bug

| File                                      | Reported (wrong) | Actual     |
| ----------------------------------------- | ---------------- | ---------- |
| `services/bot/handlers/join_game.py`      | 31%              | **100%**   |
| `services/bot/handlers/leave_game.py`     | 27%              | **100%**   |
| `services/bot/handlers/button_handler.py` | 34%              | **96.55%** |
| Combined total                            | 84.26%           | **87.69%** |

### Fix

Rename the test runner `COVERAGE_FILE` values to non-hidden names matching the established convention:

- `compose.int.yaml` line 112: `.coverage.integration` → `runner.integration`
- `compose.e2e.yaml` line 130: `.coverage.e2e` → `runner.e2e`

No changes to `coverage-report.sh` are required — `coverage/*` will pick up the renamed files.

---

## True Coverage Gap Analysis (Post All-File Combine, 87.69% total)

Numbers below are from combining `coverage/*` + hidden files. After the fix, the hidden files
become non-hidden and `coverage/*` will include them automatically.

### Files at 0% Coverage

| File                                                  | Stmts | Why untested                                                                                                  | Action                                     |
| ----------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `services/scheduler/services/notification_service.py` | 30    | Called by scheduler daemon which blocks on `select()` for up to 15 min; SIGKILL arrives before coverage saves | Unit test with mocked `SyncEventPublisher` |
| `services/scheduler/config.py`                        | 13    | Config constants only, no logic                                                                               | Low value; skip                            |
| `shared/database_objects.py`                          | 7     | Infrastructure shim                                                                                           | Low value; skip                            |
| `shared/setup.py`                                     | 2     | Packaging metadata                                                                                            | Skip                                       |

### Prioritized Gap Table

Priority criteria: functional correctness of core user actions > security paths > coverage breadth.

| Priority | File                                                  | True % | Miss | Test type                        | Rationale                                                                                                                                                  |
| -------- | ----------------------------------------------------- | ------ | ---- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1        | `services/bot/events/handlers.py`                     | 69%    | 169  | Unit (mock Discord)              | Core event dispatcher — game created/updated, reminders, DMs, join notifications, participant removal. 30+ methods. Largest single gap by statement count. |
| 2        | `services/scheduler/services/notification_service.py` | 0%     | 30   | Unit (mock `SyncEventPublisher`) | Entire reminder notification pipeline. Small file, easy to test.                                                                                           |
| 3        | `services/api/routes/games.py`                        | 83%    | 43   | Integration                      | Largest route file. Error paths, permission guards, edge cases.                                                                                            |
| 4        | `shared/data_access/guild_queries.py`                 | 75%    | 44   | Unit / Integration               | DB query error paths and edge queries throughout.                                                                                                          |
| 5        | `services/bot/guild_sync.py`                          | 71%    | 26   | Unit (mock Discord)              | Startup guild sync + member event handlers. Error paths when Discord returns unexpected data.                                                              |
| 6        | `shared/cache/client.py`                              | 64%    | 48   | Unit (mock Redis)                | Redis error and expiry paths. Used by bot auth throughout.                                                                                                 |
| 7        | `services/api/routes/auth.py`                         | 77%    | 21   | Integration                      | Auth token validation and refresh error paths.                                                                                                             |
| 8        | `services/api/routes/templates.py`                    | 83%    | 18   | Integration                      | Update/delete/reorder template paths partially uncovered.                                                                                                  |
| 9        | `services/bot/utils/discord_format.py`                | 70%    | 22   | Unit                             | String formatting utilities; error/edge branches.                                                                                                          |
| 10       | `shared/discord/client.py`                            | 85%    | 47   | Unit (mock Discord API)          | Broad Discord API wrapper; many error-handling branches untested.                                                                                          |

### Detailed Missing Line Ranges (for implementation)

| File                                                  | Missing lines                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/bot/events/handlers.py`                     | 155, 161–179, 188, 190, 197, 199, 208, 210, 213, 225, 231–232, 234, 237–239, 262–276, 282, 284, 289, 291, 297, 306–327, 332, 346, 348–351, 373, 378, 392, 394, 415, 426, 431, 442–445, 453–456, 464, 475, 478–483, 510–513, 536, 546, 614, 629–630, 633–636, 669, 694, 738, 788, 800–803, 806–811, 822, 860–877, 885, 898, 902, 910, 955–960, 978, 991, 1003, 1013–1018, 1020–1023, 1038, 1043, 1065, 1067, 1070–1072, 1081, 1083–1084, 1090–1094, 1097, 1102, 1119, 1122–1124, 1132, 1137, 1142, 1145–1147, 1150–1155, 1175, 1181, 1194–1197, 1222–1224, 1241, 1271, 1274–1276, 1279–1281, 1289, 1296, 1301–1303, 1309–1326, 1337, 1353–1354, 1382, 1408 |
| `services/scheduler/services/notification_service.py` | 24–106                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `services/api/routes/games.py`                        | (43 lines across error paths — run `coverage report -m` for current list)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `shared/data_access/guild_queries.py`                 | 66–67, 100–101, 129–130, 160–161, 163–164, 191–192, 194–195, 228–229, 231–232, 234–235, 269–270, 272–273, 275–276, 313–314, 316–317, 350–351, 353–354, 384–385, 413–414, 450–451, 453–454, 512–513                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `services/bot/guild_sync.py`                          | (26 lines — run `coverage report -m` for current list)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `shared/cache/client.py`                              | (48 lines — run `coverage report -m` for current list)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

---

## Recommended Approach

### Step 1 — Rename test runner COVERAGE_FILE values (immediate fix)

Change two lines in the compose override files:

**`compose.int.yaml` line 112:**

```yaml
# Before
COVERAGE_FILE: /app/coverage/.coverage.integration
# After
COVERAGE_FILE: /app/coverage/runner.integration
```

**`compose.e2e.yaml` line 130:**

```yaml
# Before
COVERAGE_FILE: /app/coverage/.coverage.e2e
# After
COVERAGE_FILE: /app/coverage/runner.e2e
```

No other file changes needed. `coverage-report.sh` already uses `coverage/*` which will pick up the renamed files.

### Step 2 — Address Priority 2 gap: `notification_service.py` (small, high value)

Unit test `NotificationService.send_game_reminder_due()` by mocking `SyncEventPublisher`:

- Happy path: publisher connects, publishes, closes; returns `True`
- Exception in publish: returns `False`, publisher still closed (finally block)
- Exception in connect: returns `False`

Estimated: ~30 lines of test code for 100% coverage of a security-relevant notification path.

### Step 3 — Address Priority 1 gap: `events/handlers.py` (large, most impactful)

169 uncovered statements across ~25 methods. Approach:

- Unit tests in `tests/unit/bot/events/` with mocked `discord.Client` and mocked `BotEventPublisher`
- Group by handler method: `_handle_game_created` error paths, `_handle_game_updated` error paths,
  `_handle_notification_due` branches, `_handle_player_removed`, `_handle_game_cancelled`
- Estimated 3–5 test files covering distinct event type clusters

---

## Implementation Guidance

- **Objectives**: Eliminate hidden-file coverage gap; establish accurate baseline; prioritize test gaps by risk
- **Key Tasks**:
  1. Rename `.coverage.integration` → `runner.integration` in `compose.int.yaml:112`
  2. Rename `.coverage.e2e` → `runner.e2e` in `compose.e2e.yaml:130`
  3. Delete old hidden files from `coverage/` directory if present
  4. Unit test `notification_service.py` (Priority 2, ~1 hour)
  5. Unit test `events/handlers.py` error paths (Priority 1, multi-session effort)
- **Dependencies**: Step 1 is a prerequisite for accurate reporting; Steps 4–5 are independent
- **Success Criteria**:
  - After fix: `scripts/coverage-report.sh` reports ≥87.69% without manually specifying hidden files
  - `join_game.py`, `leave_game.py`, `button_handler.py` show correct coverage in terminal report
  - `notification_service.py` reaches 100% with new unit tests
  - `events/handlers.py` reaches ≥85% with new unit tests
