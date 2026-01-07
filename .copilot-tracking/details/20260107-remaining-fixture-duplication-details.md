<!-- markdownlint-disable-file -->

# Task Details: Remaining Test Fixture Duplication Cleanup

## Research Reference

**Source Research**: #file:../research/20260107-remaining-fixture-duplication-research.md

## Phase 1: Consolidate Integration Test Database Session Fixtures

### Task 1.1: Replace bot_db_session with shared bot_db fixture in test_rls_bot_bypass.py

Remove the duplicate `bot_db_session` fixture and update test to use the shared `bot_db` fixture from tests/conftest.py.

- **Files**:
  - tests/integration/test_rls_bot_bypass.py - Remove lines 48-75 (bot_db_session fixture), update test function parameter
- **Success**:
  - bot_db_session fixture removed from file
  - Test function uses bot_db parameter instead of bot_db_session
  - Test passes without modification to test body
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 72-93) - bot_db_session duplicate fixture code
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 308-323) - Consolidation approach
- **Dependencies**:
  - Shared bot_db fixture in tests/conftest.py (already exists)

### Task 1.2: Replace app_db_session with shared app_db fixture in test_rls_api_enforcement.py

Remove the duplicate `app_db_session` fixture and update test to use the shared `app_db` fixture from tests/conftest.py.

- **Files**:
  - tests/integration/test_rls_api_enforcement.py - Remove lines 47-73 (app_db_session fixture), update test function parameter
- **Success**:
  - app_db_session fixture removed from file
  - Test function uses app_db parameter instead of app_db_session
  - Test passes without modification to test body
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 95-116) - app_db_session duplicate fixture code
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 325-338) - Consolidation approach
- **Dependencies**:
  - Shared app_db fixture in tests/conftest.py (already exists)

### Task 1.3: Verify RLS integration tests pass with shared fixtures

Run RLS-specific integration tests to verify functionality with shared fixtures.

- **Success**:
  - test_rls_bot_bypass.py passes all tests
  - test_rls_api_enforcement.py passes all tests
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 238-245) - CONFIRMED DUPLICATES section
- **Dependencies**:
  - Task 1.1 and 1.2 completion

## Phase 2: Consolidate E2E Main Bot Helper Fixture

### Task 2.1: Add main_bot_helper fixture to tests/e2e/conftest.py

Create the shared main_bot_helper fixture in e2e conftest to eliminate duplication across 4 test files.

- **Files**:
  - tests/e2e/conftest.py - Add main_bot_helper fixture (append to end of file)
- **Success**:
  - main_bot_helper fixture added to tests/e2e/conftest.py
  - Fixture creates DiscordTestHelper with main bot token
  - Fixture properly connects and disconnects helper
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 183-195) - main_bot_helper duplicate fixture code
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 340-351) - Consolidation approach
- **Dependencies**:
  - None - independent addition

### Task 2.2: Remove main_bot_helper from test_join_notification.py

Remove duplicate fixture after consolidation to conftest.

- **Files**:
  - tests/e2e/test_join_notification.py - Remove lines 56-62 (main_bot_helper fixture)
- **Success**:
  - Fixture removed from file
  - Tests use fixture from conftest without changes
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 183-195) - Duplicate instances
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Remove main_bot_helper from test_game_reminder.py

Remove duplicate fixture after consolidation to conftest.

- **Files**:
  - tests/e2e/test_game_reminder.py - Remove lines 58-64 (main_bot_helper fixture)
- **Success**:
  - Fixture removed from file
  - Tests use fixture from conftest without changes
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 183-195) - Duplicate instances
- **Dependencies**:
  - Task 2.1 completion

### Task 2.4: Remove main_bot_helper from test_player_removal.py

Remove duplicate fixture after consolidation to conftest.

- **Files**:
  - tests/e2e/test_player_removal.py - Remove lines 56-62 (main_bot_helper fixture)
- **Success**:
  - Fixture removed from file
  - Tests use fixture from conftest without changes
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 183-195) - Duplicate instances
- **Dependencies**:
  - Task 2.1 completion

### Task 2.5: Remove main_bot_helper from test_waitlist_promotion.py

Remove duplicate fixture after consolidation to conftest.

- **Files**:
  - tests/e2e/test_waitlist_promotion.py - Remove lines 34-40 (main_bot_helper fixture)
- **Success**:
  - Fixture removed from file
  - Tests use fixture from conftest without changes
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 183-195) - Duplicate instances
- **Dependencies**:
  - Task 2.1 completion

### Task 2.6: Verify all e2e tests pass with consolidated fixture

Run e2e tests that previously had duplicate fixtures to verify consolidation.

- **Success**:
  - test_join_notification.py passes
  - test_game_reminder.py passes
  - test_player_removal.py passes
  - test_waitlist_promotion.py passes
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 247-253) - E2E Test Duplicates section
- **Dependencies**:
  - Tasks 2.1-2.5 completion

## Phase 3: Final Validation

### Task 3.1: Run full test suite to verify no regressions

Execute complete test suite to ensure all consolidation changes work correctly.

- **Success**:
  - All integration tests pass
  - All e2e tests pass
  - No new test failures introduced
  - All tests use shared fixtures correctly
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 367-371) - Success criteria
- **Dependencies**:
  - All Phase 1 and Phase 2 tasks complete

### Task 3.2: Verify net code reduction achieved

Confirm that duplicate fixture code has been eliminated as expected.

- **Success**:
  - Approximately 60 lines removed from integration tests (2 fixtures × ~30 lines each)
  - Approximately 24 lines removed from e2e tests (4 duplicates × ~6 lines each, net ~24 after adding to conftest)
  - Total net reduction: ~80 lines
- **Research References**:
  - #file:../research/20260107-remaining-fixture-duplication-research.md (Lines 405-407) - Estimated effort and impact
- **Dependencies**:
  - All tasks complete

## Dependencies

- tests/conftest.py shared fixtures (bot_db, app_db) already implemented
- tests/e2e/conftest.py for e2e fixture consolidation
- pytest test framework

## Success Criteria

- All integration tests pass with shared bot_db and app_db fixtures
- All e2e tests pass with shared main_bot_helper fixture
- Net reduction of 80-100 lines of duplicate fixture code
- No new fixture implementations required
- Zero test failures after consolidation
