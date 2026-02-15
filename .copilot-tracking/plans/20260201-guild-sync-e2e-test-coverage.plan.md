---
applyTo: '.copilot-tracking/changes/20260201-guild-sync-e2e-test-coverage-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Guild Sync E2E Test Coverage

## Overview

Create comprehensive e2e test suite for guild sync functionality that verifies database state, idempotency, cross-guild isolation, RLS enforcement, and error scenarios.

## Objectives

- Verify complete guild synchronization workflow (guild → channels → templates)
- Test idempotency to ensure repeated syncs don't create duplicates
- Verify cross-guild isolation and RLS enforcement
- Test channel filtering (text channels only)
- Verify template creation edge cases
- Test permission checking and error handling

## Research Summary

### Project Files

- tests/e2e/test_01_authentication.py - Contains minimal guild sync test (lines 55-60) that only verifies response format
- tests/e2e/test_guild_routes_e2e.py - Comprehensive tests for guild route authorization patterns
- tests/e2e/test_guild_isolation_e2e.py - Tests cross-guild isolation for games and templates
- tests/e2e/conftest.py (lines 236-280) - synced_guild and synced_guild_b fixtures
- services/api/services/guild_service.py (lines 210-256) - sync_user_guilds() orchestrates full sync workflow

### External References

- #file:../research/20260201-guild-sync-e2e-test-coverage-research.md - Complete analysis of guild sync implementation, test patterns, and requirements

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/integration-tests.instructions.md - E2E and integration test patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Test Infrastructure Setup

- [x] Task 1.1: Create test_guild_sync_e2e.py file structure
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 15-30)

- [x] Task 1.2: Add database verification helper fixtures
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 32-55)

### [x] Phase 2: Basic Sync Tests

- [x] Task 2.1: Implement complete guild creation verification test
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 57-85)

- [x] Task 2.2: Implement idempotency test (multiple syncs)
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 87-110)

### [x] Phase 3: Multi-Guild and Isolation Tests

- [x] Task 3.1: Implement multi-guild sync test
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 112-135)

- [x] Task 3.2: Implement RLS enforcement verification test
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 137-165)

### [x] Phase 4: Edge Cases and Error Handling

- [x] Task 4.1: Implement channel filtering test (text channels only)
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 167-190)

- [x] Task 4.2: Implement template creation edge cases tests
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 192-220)

- [x] Task 4.3: Implement permission checking test
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 222-240)

### [x] Phase 5: Cleanup and Integration

- [x] Task 5.1: Update existing minimal test or remove if superseded
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 242-255)

- [x] Task 5.2: Verify all tests pass and clean up properly
  - Details: .copilot-tracking/details/20260201-guild-sync-e2e-test-coverage-details.md (Lines 257-270)

## Dependencies

- Existing e2e test infrastructure (authenticated clients, admin_db fixture)
- Real Discord environment configured in config/env.e2e
- Guild A and Guild B test infrastructure
- tests/shared/polling.py utilities
- PostgreSQL RLS implementation
- services/api/services/guild_service.py sync implementation

## Success Criteria

- All 8 test scenarios implemented and passing
- Tests verify both API responses and database state
- Tests are idempotent and can run multiple times
- Tests verify cross-guild isolation
- Tests follow project conventions and patterns
- No test pollution between test runs
- Tests use proper cleanup fixtures
- Line coverage for guild sync functionality increases significantly
