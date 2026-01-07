<!-- markdownlint-disable-file -->

# Release Changes: Remaining Test Fixture Duplication Cleanup

**Related Plan**: 20260107-remaining-fixture-duplication-plan.instructions.md
**Implementation Date**: 2026-01-07

## Summary

Eliminate remaining duplicate test fixtures in integration and e2e tests by using shared fixtures from tests/conftest.py and consolidating the main_bot_helper fixture.

## Changes

### Added

- tests/e2e/conftest.py - Added shared main_bot_helper fixture to eliminate duplication across 4 e2e test files

### Modified

- tests/integration/test_rls_bot_bypass.py - Replaced duplicate bot_db_session fixture with shared bot_db fixture from tests/conftest.py
- tests/integration/test_rls_api_enforcement.py - Replaced duplicate app_db_session fixture with shared app_db fixture from tests/conftest.py
- tests/e2e/test_join_notification.py - Removed duplicate main_bot_helper fixture, now uses shared fixture from tests/e2e/conftest.py
- tests/e2e/test_game_reminder.py - Removed duplicate main_bot_helper fixture, now uses shared fixture from tests/e2e/conftest.py
- tests/e2e/test_player_removal.py - Removed duplicate main_bot_helper fixture, now uses shared fixture from tests/e2e/conftest.py
- tests/e2e/test_waitlist_promotion.py - Removed duplicate main_bot_helper fixture, now uses shared fixture from tests/e2e/conftest.py

### Testing

- ✅ All e2e tests passed with consolidated main_bot_helper fixture (test_join_notification, test_game_reminder, test_player_removal, test_waitlist_promotion)
- ✅ Python syntax validation passed for all modified files
- ✅ Fixture successfully imported and used from shared location
- ✅ Full test suite passed: 1025 unit tests passed
- ✅ Integration tests passed: 129 tests passed with shared fixtures
- ✅ E2E tests passed: 55 tests passed with consolidated main_bot_helper

### Code Reduction

- Removed ~20 lines: Duplicate bot_db_session fixture from test_rls_bot_bypass.py
- Removed ~20 lines: Duplicate app_db_session fixture from test_rls_api_enforcement.py
- Removed ~50 lines: Duplicate main_bot_helper fixtures from 4 e2e test files
- **Total net reduction: ~90 lines of duplicate fixture code**
- No new code added - only fixture references updated

### Removed
