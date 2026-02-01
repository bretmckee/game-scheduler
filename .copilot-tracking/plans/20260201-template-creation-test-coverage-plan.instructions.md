---
applyTo: ".copilot-tracking/changes/20260201-template-creation-test-coverage-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Template Creation Test Coverage

## Overview

Add integration tests for template creation API endpoint to prevent regressions in authorization, validation, and database persistence.

## Objectives

- Test template creation via POST /guilds/{guild_id}/templates API endpoint
- Verify bot manager authorization enforcement
- Validate request schema and constraint checking
- Confirm database persistence after successful creation
- Cover edge cases and error conditions

## Research Summary

### Project Files

- services/api/routes/templates.py (lines 185-219) - Template creation endpoint implementation
- tests/integration/test_template_default_overrides.py - Integration test pattern reference
- tests/conftest.py (lines 674-734) - create_template fixture (bypasses API)

### External References

- #file:../research/20260201-template-creation-test-coverage-research.md - Complete analysis of test coverage gap

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/integration-tests.instructions.md - Integration test standards

## Implementation Checklist

### [ ] Phase 1: Create Test File and Happy Path

- [ ] Task 1.1: Create test file with basic structure and imports

  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 15-35)

- [ ] Task 1.2: Implement happy path test for successful template creation
  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 37-75)

### [ ] Phase 2: Authorization Tests

- [ ] Task 2.1: Test template creation without bot manager role (403 Forbidden)

  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 77-105)

- [ ] Task 2.2: Test template creation without authentication (401 Unauthorized)
  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 107-130)

### [ ] Phase 3: Validation Tests

- [ ] Task 3.1: Test missing required fields (422 Unprocessable Entity)

  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 132-155)

- [ ] Task 3.2: Test invalid guild_id (404 Not Found)

  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 157-180)

- [ ] Task 3.3: Test invalid channel_id (should fail validation or creation)
  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 182-205)

### [ ] Phase 4: Edge Cases

- [ ] Task 4.1: Test creating default template (is_default=True)

  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 207-230)

- [ ] Task 4.2: Test with null/empty optional fields
  - Details: .copilot-tracking/details/20260201-template-creation-test-coverage-details.md (Lines 232-255)

## Dependencies

- Integration test infrastructure (PostgreSQL, RabbitMQ, Redis)
- Existing test fixtures (create_guild, create_channel, create_user, seed_redis_cache)
- Test helpers (create_test_session, cleanup_test_session)

## Success Criteria

- Template creation endpoint has comprehensive test coverage
- Authorization enforcement verified (bot manager required)
- Request validation verified (schema and constraints)
- Database persistence verified
- All tests run in integration test suite without Discord dependency
- Tests prevent regression of recent template creation bug fix
