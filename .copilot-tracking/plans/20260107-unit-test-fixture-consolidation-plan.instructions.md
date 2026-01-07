---
applyTo: ".copilot-tracking/changes/20260107-unit-test-fixture-consolidation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Unit Test Fixture Consolidation

## Overview

Consolidate 96 duplicate test fixtures (72% of all unit test fixtures) across ~50 unit test files into shared conftest.py files, reducing maintenance burden and eliminating copy-paste fixture definitions.

## Objectives

- Eliminate 15 duplicate `mock_db` fixtures into single shared fixture
- Consolidate 28 fixtures from "game service cluster" (4 test files) into 7 shared fixtures
- Reduce overall fixture count from 134 to ~40 (70% reduction)
- Establish consistent mocking patterns across unit tests
- Maintain 100% test pass rate throughout consolidation

## Research Summary

### Project Files Analyzed

- tests/services/api/services/test_games.py (11 fixtures, 7 duplicates)
- tests/services/api/services/test_games_promotion.py (9 fixtures, 7 duplicates)
- tests/services/api/services/test_games_edit_participants.py (7 fixtures, all duplicates)
- tests/services/api/services/test_games_image_upload.py (10 fixtures, 7 duplicates)
- tests/services/bot/auth/test_role_checker.py - mock_db duplicate
- tests/services/api/routes/test_guilds.py - mock_db, mock_current_user duplicates
- tests/shared/data_access/test_guild_queries.py - mock_db, sample fixtures
- Plus ~43 additional unit test files with varying duplication

### External References

- #file:../research/20260107-unit-test-fixture-duplication-research.md - Complete semantic analysis and categorization
- #file:../research/20260104-consolidate-test-fixtures-research.md - Integration/E2E consolidation patterns (proven approach)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../tests/conftest.py - Existing root fixture patterns (factories, cleanup)
- #file:../../tests/integration/conftest.py - Integration test fixture organization

## Implementation Checklist

### [ ] Phase 1: Game Service Cluster Consolidation (Critical Impact)

- [ ] Task 1.1: Create tests/services/api/services/conftest.py with 7 shared fixtures
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 15-45)

- [ ] Task 1.2: Remove 28 duplicate fixtures from 4 game service test files
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 47-70)

- [ ] Task 1.3: Verify game service tests pass with shared fixtures
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 72-85)

### [ ] Phase 2: Mock Object Consolidation (High Impact)

- [ ] Task 2.1: Add mock_db fixture to tests/conftest.py
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 87-105)

- [ ] Task 2.2: Remove 12+ mock_db duplicates from unit test files
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 107-130)

- [ ] Task 2.3: Add mock_discord_api_client to tests/conftest.py
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 132-145)

- [ ] Task 2.4: Add mock_discord_bot to tests/services/bot/conftest.py
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 147-160)

- [ ] Task 2.5: Verify all unit tests pass after mock consolidation
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 162-175)

### [ ] Phase 3: Sample Data Model Consolidation (Medium Impact)

- [ ] Task 3.1: Create model factory fixtures in tests/conftest.py
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 177-210)

- [ ] Task 3.2: Migrate tests to use factory fixtures instead of local sample_* fixtures
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 212-235)

- [ ] Task 3.3: Remove 23 duplicate sample model fixtures
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 237-255)

### [ ] Phase 4: Specialized Fixture Consolidation (Lower Priority)

- [ ] Task 4.1: Consolidate auth fixtures (mock_current_user, mock_tokens)
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 257-275)

- [ ] Task 4.2: Consolidate middleware fixtures (mock_app, mock_request)
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 277-290)

- [ ] Task 4.3: Consolidate bot command fixtures
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 292-310)

- [ ] Task 4.4: Final verification and cleanup
  - Details: .copilot-tracking/details/20260107-unit-test-fixture-consolidation-details.md (Lines 312-330)

## Dependencies

- pytest with fixture discovery
- SQLAlchemy for AsyncSession spec
- unittest.mock for AsyncMock/MagicMock
- Existing test suite must pass before starting
- No breaking changes to test API

## Success Criteria

- All 134 unit tests continue to pass after each phase
- Fixture count reduced from 134 to ~40 (70% reduction)
- No exact duplicate fixtures remain (0 fixtures appearing in multiple files)
- Each conftest.py has clear documentation
- Average fixtures per test file: <3 (down from ~7)
- Consolidation documented in changes file
