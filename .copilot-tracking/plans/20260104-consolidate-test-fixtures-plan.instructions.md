---
applyTo: ".copilot-tracking/changes/20260104-consolidate-test-fixtures-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Consolidate Test Fixtures

## Overview

Consolidate 100+ duplicated test fixtures into a single shared location with factory-based patterns, eliminating fixture duplication across integration and e2e tests.

## Objectives

- Reduce fixture duplication from 100+ scattered fixtures to ~15 shared factory fixtures
- Implement factory pattern for flexible test data creation
- Add comprehensive fixture tests to prevent deadlocks and cleanup conflicts
- Migrate all integration and e2e tests to use shared fixtures
- Delete redundant fixtures from `tests/integration/conftest.py` and individual test files

## Research Summary

### Project Files

- [tests/integration/conftest.py](tests/integration/conftest.py) - 24 fixtures to consolidate/delete
- [tests/e2e/conftest.py](tests/e2e/conftest.py) - 20+ fixtures to consolidate
- [tests/integration/test_notification_daemon.py](tests/integration/test_notification_daemon.py) - Custom fixtures to migrate
- [tests/integration/test_status_transitions.py](tests/integration/test_status_transitions.py) - Custom fixtures to migrate
- [tests/integration/test_template_default_overrides.py](tests/integration/test_template_default_overrides.py) - Conflicting cleanup fixture
- [tests/integration/test_game_signup_methods.py](tests/integration/test_game_signup_methods.py) - Redis cache duplication

### External References

- [Research Document](..//research/20260104-consolidate-test-fixtures-research.md) - Comprehensive fixture analysis
- #file:../../.github/instructions/python.instructions.md - Python conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Testing best practices

### Key Insights

- Hermetic tests (create what you need, automatic cleanup) prevent conflicts
- Factory pattern provides flexibility over fixed A/B fixtures
- Sync-first implementation with async wrappers avoids duplication
- DELETE (not TRUNCATE) with explicit rollback prevents deadlocks

## Implementation Checklist

### [ ] Phase 0: Create and Test Shared Fixtures

- [ ] Task 0.1: Create `tests/conftest.py` with all core fixtures
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 1-80)

- [ ] Task 0.2: Create comprehensive fixture validation tests
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 82-120)

- [ ] Task 0.3: Verify fixture tests pass without deadlocks
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 122-135)

### [ ] Phase 1: Migrate Sync-Based Integration Tests

- [ ] Task 1.1: Migrate `test_notification_daemon.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 137-165)

- [ ] Task 1.2: Migrate `test_status_transitions.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 167-185)

- [ ] Task 1.3: Migrate `test_retry_daemon.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 187-205)

- [ ] Task 1.4: Migrate `test_template_default_overrides.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 207-230)

- [ ] Task 1.5: Migrate `test_game_signup_methods.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 232-260)

### [ ] Phase 2: Migrate Async ORM Integration Tests

- [ ] Task 2.1: Migrate `test_guild_queries.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 262-280)

- [ ] Task 2.2: Migrate `test_games_route_guild_isolation.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 282-305)

### [ ] Phase 3: Consolidate E2E Test Fixtures

- [ ] Task 3.1: Identify e2e-specific vs shared fixtures
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 307-330)

- [ ] Task 3.2: Migrate 12 e2e test files to shared fixtures
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 332-360)

### [ ] Phase 4: Delete Redundant Fixtures

- [ ] Task 4.1: Delete deprecated fixtures from `tests/integration/conftest.py`
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 362-385)

- [ ] Task 4.2: Verify all tests still pass after cleanup
  - Details: [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md) (Lines 387-400)

## Dependencies

- SQLAlchemy (sync and async engines)
- pytest and pytest-asyncio
- Redis client from `shared.cache.client`
- PostgreSQL with admin, app, and bot database users
- RabbitMQ (for daemon tests)

## Success Criteria

- All 100+ duplicated fixtures consolidated to ~15 shared factory fixtures in `tests/conftest.py`
- All integration tests migrated and passing
- All e2e tests migrated and passing
- No deadlocks or cleanup conflicts
- Redundant fixtures deleted from subdirectories
- Comprehensive fixture tests validate behavior
