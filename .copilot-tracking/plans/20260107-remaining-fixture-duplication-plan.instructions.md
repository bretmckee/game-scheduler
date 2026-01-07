---
applyTo: ".copilot-tracking/changes/20260107-remaining-fixture-duplication-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remaining Test Fixture Duplication Cleanup

## Overview

Eliminate remaining duplicate test fixtures in integration and e2e tests by using shared fixtures from tests/conftest.py and consolidating the main_bot_helper fixture.

## Objectives

- Remove duplicate database session fixtures from RLS integration tests
- Consolidate main_bot_helper fixture across e2e tests
- Reduce duplicate fixture code by ~80-100 lines
- Maintain 100% test pass rate after consolidation

## Research Summary

### Project Files

- tests/conftest.py - Comprehensive shared fixtures including bot_db and app_db
- tests/integration/test_rls_bot_bypass.py - Contains duplicate bot_db_session fixture
- tests/integration/test_rls_api_enforcement.py - Contains duplicate app_db_session fixture
- tests/e2e/conftest.py - E2E-specific fixtures, missing main_bot_helper
- tests/e2e/test_join_notification.py - Contains duplicate main_bot_helper fixture
- tests/e2e/test_game_reminder.py - Contains duplicate main_bot_helper fixture
- tests/e2e/test_player_removal.py - Contains duplicate main_bot_helper fixture
- tests/e2e/test_waitlist_promotion.py - Contains duplicate main_bot_helper fixture

### External References

- #file:../research/20260107-remaining-fixture-duplication-research.md - Complete fixture inventory and duplication analysis

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting style

## Implementation Checklist

### [x] Phase 1: Consolidate Integration Test Database Session Fixtures

- [x] Task 1.1: Replace bot_db_session with shared bot_db fixture in test_rls_bot_bypass.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 28-55)

- [x] Task 1.2: Replace app_db_session with shared app_db fixture in test_rls_api_enforcement.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 57-84)

- [x] Task 1.3: Verify RLS integration tests pass with shared fixtures
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 86-95)

### [x] Phase 2: Consolidate E2E Main Bot Helper Fixture

- [x] Task 2.1: Add main_bot_helper fixture to tests/e2e/conftest.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 97-119)

- [x] Task 2.2: Remove main_bot_helper from test_join_notification.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 121-129)

- [x] Task 2.3: Remove main_bot_helper from test_game_reminder.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 131-139)

- [x] Task 2.4: Remove main_bot_helper from test_player_removal.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 141-149)

- [x] Task 2.5: Remove main_bot_helper from test_waitlist_promotion.py
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 151-159)

- [x] Task 2.6: Verify all e2e tests pass with consolidated fixture
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 161-170)

### [ ] Phase 3: Final Validation

- [ ] Task 3.1: Run full test suite to verify no regressions
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 172-183)

- [ ] Task 3.2: Verify net code reduction achieved
  - Details: .copilot-tracking/details/20260107-remaining-fixture-duplication-details.md (Lines 185-194)

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
