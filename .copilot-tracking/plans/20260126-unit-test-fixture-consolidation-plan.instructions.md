---
applyTo: ".copilot-tracking/changes/20260126-unit-test-fixture-consolidation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Unit Test Fixture Consolidation

## Overview

Consolidate 59 duplicate test fixtures across 91 unit test files into shared conftest.py files, reducing fixture count by 43% and eliminating maintenance burden.

## Objectives

- Eliminate 35 duplicate fixtures from game service test cluster (81% reduction)
- Create service-level conftest.py for shared mocks and sample data
- Add unit test mock fixtures to root conftest.py for cross-service usage
- Achieve 100% test pass rate after consolidation
- Reduce average fixtures per file from 1.7 to 0.5

## Research Summary

### Project Files

- tests/services/api/services/test_games.py - 11 fixtures (mock_db, game_service, sample data)
- tests/services/api/services/test_games_promotion.py - 9 fixtures (identical to test_games)
- tests/services/api/services/test_games_edit_participants.py - 8 fixtures (identical subset)
- tests/services/api/services/test_games_image_upload.py - 10 fixtures (identical subset)
- tests/services/api/services/test_update_game_fields_helpers.py - 5 fixtures (mock subset)
- tests/conftest.py - Current integration test fixtures (need unit test versions)

### External References

- #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md - Current state analysis with line numbers
- #file:../research/20260107-unit-test-fixture-duplication-research.md - Original duplication research
- #file:../research/20260104-consolidate-test-fixtures-research.md - Integration test consolidation patterns

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python testing conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Fixture documentation style

## Implementation Checklist

### [x] Phase 1: Game Service Cluster Consolidation

- [x] Task 1.1: Create tests/services/api/services/conftest.py with 8 shared fixtures
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 15-95)

- [x] Task 1.2: Remove duplicate fixtures from test_games.py
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 97-110)

- [x] Task 1.3: Remove duplicate fixtures from test_games_promotion.py
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 112-125)

- [x] Task 1.4: Remove duplicate fixtures from test_games_edit_participants.py
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 127-140)

- [x] Task 1.5: Remove duplicate fixtures from test_games_image_upload.py
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 142-155)

- [x] Task 1.6: Remove duplicate fixtures from test_update_game_fields_helpers.py
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 157-170)

- [x] Task 1.7: Run game service tests to verify consolidation
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 172-185)

### [x] Phase 2: Root-Level Mock Consolidation

- [x] Task 2.1: Add unit test mock fixtures to tests/conftest.py
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 187-270)

- [x] Task 2.2: Update routes tests to use shared mock_current_user fixture
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 272-295)

- [x] Task 2.3: Update dependencies tests to use shared mock_role_service fixture
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 297-320)

- [x] Task 2.4: Run full unit test suite to verify consolidation
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 322-340)

### [ ] Phase 3: Verification and Cleanup

- [ ] Task 3.1: Verify fixture discovery with pytest --collect-only
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 342-360)

- [ ] Task 3.2: Run coverage report to verify no test regressions
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 362-380)

- [ ] Task 3.3: Document fixture locations and usage patterns
  - Details: .copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md (Lines 382-400)

## Dependencies

- Python 3.13+ with pytest
- Docker compose for running tests in containers
- Current test suite passing (baseline)
- SQLAlchemy AsyncSession for mock specs
- unittest.mock for AsyncMock and MagicMock

## Success Criteria

- 35 fixtures removed from game service cluster (81% reduction)
- 23 additional fixtures removed from root consolidation
- All 91 unit test files still pass
- Fixture discovery works correctly (pytest --collect-only succeeds)
- Coverage remains at or above current levels
- No shared mutable state between tests
- Clear documentation for fixture usage
