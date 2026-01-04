<!-- markdownlint-disable-file -->

# Release Changes: Consolidate Test Fixtures

**Related Plan**: 20260104-consolidate-test-fixtures-plan.instructions.md
**Implementation Date**: 2026-01-04

## Summary

**Phase 0 Complete**: Created comprehensive shared fixtures in [tests/conftest.py](tests/conftest.py) with validation tests in [tests/integration/test_shared_fixtures.py](tests/integration/test_shared_fixtures.py). All 31 validation tests passing without deadlocks.

**Key Achievements**:
- Consolidated database session fixtures (admin_db_sync, admin_db, app_db, bot_db) with automatic cleanup
- Implemented factory pattern for data creation (create_guild, create_channel, create_user, create_template, create_game)
- Created Redis cache seeding fixture (seed_redis_cache) that works in both sync and async contexts
- Composite fixture (test_environment) for common test patterns
- All fixtures tested for deadlock-free operation

**Next Steps**: Phase 1 - Migrate sync-based integration tests to use new shared fixtures

## Changes

### Added

- tests/conftest.py - Comprehensive shared fixture file with database sessions (admin_db_sync, admin_db, app_db, bot_db), Redis client (sync and async), factory fixtures for data creation (create_guild, create_channel, create_user, create_template, create_game), Redis cache seeding (seed_redis_cache), and composite fixtures (test_environment)
- tests/integration/test_shared_fixtures.py - Comprehensive validation tests for all shared fixtures with 31 test cases covering factory fixtures, composite fixtures, Redis cache seeding, database session handling, and full workflow integration

### Modified

- tests/conftest.py - Fixed admin_db_url_sync to properly remove asyncpg driver, implemented event loop management for sync Redis client fixture, added sync wrapper for seed_redis_cache to work in both sync and async contexts
- tests/integration/test_shared_fixtures.py - Fixed Redis client assertions, updated seed_redis_cache calls to use sync wrapper instead of asyncio.run(), added module-level @pytest.mark.integration marker

### Removed
