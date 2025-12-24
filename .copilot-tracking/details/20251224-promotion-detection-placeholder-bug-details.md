<!-- markdownlint-disable-file -->

# Task Details: Fix Promotion Detection Bug with Placeholder Participants

## Research Reference

**Source Research**: #file:../research/20251224-promotion-detection-bug.md

## Phase 1: Create Centralized Participant Partitioning Utility

### Task 1.1: Add `PartitionedParticipants` dataclass to `shared/utils/participant_sorting.py`

Create a dataclass to hold the result of participant partitioning, including sorted lists and pre-computed Discord ID sets.

- **Files**:
  - shared/utils/participant_sorting.py - Add dataclass after imports, before `sort_participants()`
- **Success**:
  - Dataclass includes `all_sorted`, `confirmed`, `overflow`, `confirmed_real_user_ids`, `overflow_real_user_ids` fields
  - All fields properly typed with list or set type hints
  - Includes docstring explaining each field
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 156-169) - Dataclass specification
- **Dependencies**:
  - Python dataclasses import
  - TYPE_CHECKING import for forward references

### Task 1.2: Add `partition_participants()` function to `shared/utils/participant_sorting.py`

Create function that sorts participants and partitions them into confirmed and overflow groups, handling placeholders correctly.

- **Files**:
  - shared/utils/participant_sorting.py - Add function after `sort_participants()`
- **Success**:
  - Function accepts `participants` list and `max_players` int (defaults to 10)
  - Returns `PartitionedParticipants` dataclass instance
  - Includes ALL participants (including placeholders) when sorting
  - Correctly slices by max_players to separate confirmed/overflow
  - Extracts Discord IDs only for real users (with `user` and `user.discord_id`)
  - Includes comprehensive docstring with Args, Returns sections
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 171-203) - Function implementation
  - #file:../research/20251224-promotion-detection-bug.md (Lines 78-85) - Bot formatter pattern showing correct handling
- **Dependencies**:
  - Task 1.1 completion (`PartitionedParticipants` dataclass)
  - Existing `sort_participants()` function

### Task 1.3: Add comprehensive unit tests for `partition_participants()`

Create test file with comprehensive coverage of participant partitioning edge cases.

- **Files**:
  - tests/shared/utils/test_participant_sorting.py - Add new test cases or create file if not exists
- **Success**:
  - Test all real users (no placeholders)
  - Test placeholders in confirmed positions
  - Test placeholders in overflow positions
  - Test mixed placeholders and real users
  - Test empty participant list
  - Test max_players=None (defaults to 10)
  - Test max_players=0 (all overflow)
  - Test max_players > participant count (no overflow)
  - All tests verify Discord ID sets match expected values
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 251-258) - Test cases needed
  - #file:../../.github/instructions/python.instructions.md - pytest conventions
- **Dependencies**:
  - Task 1.1 and 1.2 completion
  - pytest fixtures for creating test participants

## Phase 2: Fix Promotion Detection in games.py

### Task 2.1: Update `update_game()` to use `partition_participants()` for old state

Replace buggy promotion detection logic in `update_game()` with new utility.

- **Files**:
  - services/api/services/games.py - Update lines 808-816
- **Success**:
  - Import `partition_participants()` at top of file
  - Replace manual participant filtering/sorting/slicing with `partition_participants()` call
  - Use `old_partitioned.overflow_real_user_ids` instead of manually computed `old_overflow_ids`
  - Pass to `_detect_and_notify_promotions()` without changes to function signature
  - Code is more concise and readable
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 12-27) - Root cause explanation
  - #file:../research/20251224-promotion-detection-bug.md (Lines 171-203) - New utility usage
- **Code Location**:
  - Current code at services/api/services/games.py lines 808-816
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update `_detect_and_notify_promotions()` to use `partition_participants()` for current state

Replace buggy current state detection with new utility.

- **Files**:
  - services/api/services/games.py - Update lines 1198-1206
- **Success**:
  - Replace manual participant filtering/sorting/slicing with `partition_participants()` call
  - Use `current_partitioned.confirmed_real_user_ids` for efficient lookup
  - Compare with `old_overflow_ids` parameter to identify promotions
  - Code matches pattern from Task 2.1
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 12-27) - Root cause explanation
  - #file:../research/20251224-promotion-detection-bug.md (Lines 1195-1210) - Current buggy code
- **Code Location**:
  - Current code at services/api/services/games.py lines 1198-1206
- **Dependencies**:
  - Task 2.1 completion (ensures consistent approach)

### Task 2.3: Add unit tests for promotion detection with placeholders

Create tests specifically for promotion scenarios involving placeholders.

- **Files**:
  - tests/services/api/services/test_games_promotion.py - Add new test methods
- **Success**:
  - Test promotion when placeholder removed from confirmed slot
  - Test promotion when max_players increased with placeholder in confirmed
  - Test no promotion when placeholder added to overflow
  - Test multiple users promoted when multiple placeholders removed
  - All tests verify promotion DMs are sent to correct users
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 29-46) - Failing scenario
  - #file:../research/20251224-promotion-detection-bug.md (Lines 251-258) - Test cases needed
- **Dependencies**:
  - Task 2.1 and 2.2 completion

## Phase 3: Migrate Bot Event Handlers

### Task 3.1: Update `_handle_game_reminder()` to use `partition_participants()`

Replace duplicated sorting/slicing logic with centralized utility in game reminder handler.

- **Files**:
  - services/bot/events/handlers.py - Update lines 390-403
- **Success**:
  - Import `partition_participants()` if not already imported
  - Replace manual sorting/slicing of real_participants with `partition_participants()` call
  - Use `partitioned.confirmed` and `partitioned.overflow` instead of manual slicing
  - Maintain existing behavior - only notify real participants (filter out placeholders when needed)
  - Code is more concise and consistent with other locations
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 240-249) - Code duplication audit location 1
  - #file:../research/20251224-promotion-detection-bug.md (Lines 171-203) - Utility usage pattern
- **Code Location**:
  - Current code at services/bot/events/handlers.py lines 390-403
- **Dependencies**:
  - Phase 1 completion

### Task 3.2: Update `_handle_join_notification()` to use `partition_participants()`

Replace duplicated sorting/slicing logic with centralized utility in join notification handler.

- **Files**:
  - services/bot/events/handlers.py - Update lines 508-513
- **Success**:
  - Replace manual sorting/slicing of real_participants with `partition_participants()` call
  - Use `partitioned.confirmed` for checking if participant is waitlisted
  - Maintain existing behavior - check if new participant is in confirmed list
  - Code is more concise and consistent
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 240-249) - Code duplication audit location 2
  - #file:../research/20251224-promotion-detection-bug.md (Lines 171-203) - Utility usage pattern
- **Code Location**:
  - Current code at services/bot/events/handlers.py lines 508-513
- **Dependencies**:
  - Task 3.1 completion (consistent approach)

### Task 3.3: Update `_handle_game_cancelled()` to use `partition_participants()`

Replace duplicated sorting/slicing logic with centralized utility in game cancelled handler.

- **Files**:
  - services/bot/events/handlers.py - Update lines 855-862
- **Success**:
  - Replace manual sorting/slicing with `partition_participants()` call
  - Use `partitioned.confirmed` and `partitioned.overflow` lists
  - Extract Discord IDs and display names from partitioned lists
  - Maintain existing behavior - include both real users and placeholders
  - Code is more concise and consistent
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 240-249) - Code duplication audit location 3
  - #file:../research/20251224-promotion-detection-bug.md (Lines 171-203) - Utility usage pattern
- **Code Location**:
  - Current code at services/bot/events/handlers.py lines 855-862
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Migrate API Routes

### Task 4.1: Update `download_calendar()` to use `partition_participants()`

Replace manual participant sorting in calendar download route with centralized utility.

- **Files**:
  - services/api/routes/games.py - Update line 566
- **Success**:
  - Import `partition_participants()` if not already imported
  - Replace `participant_sorting.sort_participants()` call with `partition_participants()` call
  - Use `partitioned.all_sorted` for the sorted participant list
  - Maintain existing behavior - only extracting Discord IDs for display name resolution
  - Code is consistent with other locations
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 240-249) - Code duplication audit location 6
  - #file:../research/20251224-promotion-detection-bug.md (Lines 171-203) - Utility usage pattern
- **Code Location**:
  - Current code at services/api/routes/games.py line 566
- **Dependencies**:
  - Phase 3 completion

## Phase 5: Verification and Testing

### Task 5.1: Run existing unit tests to verify no regressions

Ensure all existing promotion tests still pass with the new implementation.

- **Files**:
  - tests/services/api/services/test_games_promotion.py - Run existing tests
- **Success**:
  - All existing tests pass without modification
  - No test failures or unexpected behavior changes
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 251-258) - Test case 1 should still work
- **Dependencies**:
  - Phase 2 completion

### Task 5.2: Run E2E test to verify bug fix

Run the E2E test that originally exposed the bug to verify it now passes.

- **Files**:
  - tests/e2e/test_waitlist_promotion.py - Run test that was failing
- **Success**:
  - E2E test passes showing promotion DM sent when placeholder removed
  - E2E test passes showing promotion DM sent when max_players increased with placeholder
  - Test output shows promotion DM received by user
- **Research References**:
  - #file:../research/20251224-promotion-detection-bug.md (Lines 48-61) - Original test failure
  - #file:../research/20251224-promotion-detection-bug.md (Lines 273-276) - E2E test status
- **Dependencies**:
  - Phase 2 completion
  - Docker environment running

### Task 5.3: Verify all new code passes linting

Run linting tools on all modified and new files.

- **Files**:
  - All files modified in Phases 1-4
- **Success**:
  - No ruff errors or warnings
  - No mypy type checking errors
  - Code follows project Python conventions
- **Research References**:
  - #file:../../.github/instructions/python.instructions.md - Linting standards
- **Dependencies**:
  - Phases 1-4 completion

## Dependencies

- Python 3.11+ with dataclasses support
- SQLAlchemy models (GameParticipant, User)
- pytest testing framework
- Docker environment for E2E tests
- ruff and mypy for linting

## Success Criteria

- Bug fixed: Users receive promotion DMs when placeholders are removed from confirmed slots
- Bug fixed: Users receive promotion DMs when max_players increased with placeholders present
- All 6 locations migrated to use centralized utility (consistent implementation)
- Bot event handlers use consistent participant partitioning logic
- API routes use consistent participant partitioning logic
- All new code has comprehensive unit test coverage
- All existing tests pass without modification
- E2E test passes demonstrating bug fix
- Code follows project conventions and passes all linting checks
- No regressions in existing promotion detection functionality
- Eliminated code duplication across the codebase
