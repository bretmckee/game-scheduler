<!-- markdownlint-disable-file -->

# Release Changes: Consolidate Test Fixtures

**Related Plan**: 20260104-consolidate-test-fixtures-plan.instructions.md
**Implementation Date**: 2026-01-04

## Summary

**Phase 0 Complete**: Created comprehensive shared fixtures in [tests/conftest.py](tests/conftest.py) with validation tests in [tests/integration/test_shared_fixtures.py](tests/integration/test_shared_fixtures.py). All 31 validation tests passing without deadlocks.

**Phase 1 In Progress**: Migrating sync-based integration tests to use shared factory fixtures.

**Key Achievements**:
- Consolidated database session fixtures (admin_db_sync, admin_db, app_db, bot_db) with automatic cleanup
- Implemented factory pattern for data creation (create_guild, create_channel, create_user, create_template, create_game)
- Created Redis cache seeding fixture (seed_redis_cache) that works in both sync and async contexts
- Composite fixture (test_environment) for common test patterns
- Extended composite fixture (test_game_environment) for daemon integration tests
- All fixtures tested for deadlock-free operation
- Task 1.1: Migrated test_notification_daemon.py to use shared fixtures (6 tests: 5 passed, 1 xpassed)
- Task 1.2: Migrated test_status_transitions.py to use shared fixtures (3 tests passed)
- Task 1.3: Migrated test_retry_daemon.py to use shared RabbitMQ fixtures (5 tests passed)
- Consolidated RabbitMQ helper functions (get_queue_message_count, consume_one_message, purge_queue) to tests/integration/conftest.py
- Eliminated duplicate _create_test_data helper methods across test files

**Next Steps**: Continue Phase 1 - Tasks 1.4-1.5

## Changes

### Added

- tests/conftest.py - Comprehensive shared fixture file with database sessions (admin_db_sync, admin_db, app_db, bot_db), Redis client (sync and async), factory fixtures for data creation (create_guild, create_channel, create_user, create_template, create_game), Redis cache seeding (seed_redis_cache), and composite fixtures (test_environment, test_game_environment)
- tests/integration/test_shared_fixtures.py - Comprehensive validation tests for all shared fixtures with 31 test cases covering factory fixtures, composite fixtures, Redis cache seeding, database session handling, and full workflow integration
- tests/integration/conftest.py - Added RabbitMQ helper functions (get_queue_message_count, consume_one_message, purge_queue) for use across all integration tests

### Modified

- tests/conftest.py - Fixed admin_db_url_sync to properly remove asyncpg driver, implemented event loop management for sync Redis client fixture, added sync wrapper for seed_redis_cache to work in both sync and async contexts, added test_game_environment composite fixture for daemon integration tests
- tests/integration/test_shared_fixtures.py - Fixed Redis client assertions, updated seed_redis_cache calls to use sync wrapper instead of asyncio.run(), added module-level @pytest.mark.integration marker
- tests/integration/test_notification_daemon.py - Replaced custom test_game_session fixture with shared factory fixtures (create_guild, create_channel, create_user, create_game), removed db_session fixture in favor of admin_db_sync, updated all test functions to use factory pattern with dictionary access, removed duplicate _create_test_data helper methods in favor of shared test_game_environment fixture, removed duplicate get_queue_message_count and consume_one_message functions
- tests/integration/test_status_transitions.py - Removed custom db_url, db_session, and test_game_session fixtures, replaced with shared admin_db_sync and test_game_environment fixtures, updated all test functions to use factory pattern, removed unused sqlalchemy imports (create_engine, sessionmaker), removed duplicate get_queue_message_count and consume_one_message functions
- tests/integration/test_retry_daemon.py - Removed duplicate rabbitmq_url, rabbitmq_connection, and rabbitmq_channel fixtures in favor of shared fixtures from tests/integration/conftest.py, removed duplicate get_queue_message_count, consume_one_message, and purge_queue functions, removed unused helper functions (publish_event_with_ttl, get_queue_arguments)
- tests/integration/test_game_signup_methods.py - Removed duplicate consume_one_message function, now imports from tests/integration/conftest.py

### Removed
