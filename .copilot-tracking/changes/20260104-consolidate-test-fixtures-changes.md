<!-- markdownlint-disable-file -->

# Release Changes: Consolidate Test Fixtures

**Related Plan**: 20260104-consolidate-test-fixtures-plan.instructions.md
**Implementation Date**: 2026-01-04

## Summary

**Phase 0 Complete**: Created comprehensive shared fixtures in [tests/conftest.py](tests/conftest.py) with validation tests in [tests/integration/test_shared_fixtures.py](tests/integration/test_shared_fixtures.py). All 31 validation tests passing without deadlocks.

**Phase 1 Complete**: Migrated all sync-based integration tests to use shared factory fixtures.

**Phase 2 Complete**: Migrated all async ORM integration tests to use shared factory fixtures.

**Phase 3 In Progress**: Task 3.1 complete - identified which E2E fixtures to keep vs migrate. Task 3.2 complete - removed e2e_timeouts backward-compatible alias.

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
- Task 1.4: Migrated test_template_default_overrides.py (tests passing)
- Task 1.5: Migrated test_game_signup_methods.py - replaced custom fixtures with helper functions (3 tests passing)
- Consolidated RabbitMQ helper functions (get_queue_message_count, consume_one_message, purge_queue) to tests/integration/conftest.py
- Eliminated duplicate _create_test_data helper methods across test files
- Task 2.1: Migrated test_guild_queries.py - eliminated 12 local fixtures, reduced test code by 60%
- Task 2.2: Migrated test_games_route_guild_isolation.py - eliminated 14 local fixtures, reduced file by 26%
- **Task 3.1 Complete**: Analyzed tests/e2e/conftest.py and documented migration plan:
  - KEEP: 10 E2E-specific fixtures (Discord tokens/IDs, auth helpers, synced_guild)
  - MIGRATE: 2 new fixtures to shared (create_authenticated_client_async, wait_for_game_message_id)
  - DELETE: 9 duplicate/redundant fixtures (database sessions, data creation, simple clients)
  - Individual test files: Use factory fixtures instead of custom data creation
  - **Timeout consolidation**: Moved TimeoutType enum and test_timeouts fixture from E2E to shared conftest
  - **Duplicate removal**: Deleted api_base_url from e2e conftest (already in shared conftest)
  - **Task 3.2 added**: Remove e2e_timeouts backward-compatible alias (~50 occurrences in 12 files)
- **Task 3.2 Complete**: Removed e2e_timeouts backward-compatible alias from all E2E tests:
  - Replaced all 62 occurrences of e2e_timeouts parameter with test_timeouts in 11 test function signatures
  - Replaced all e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType] across test bodies
  - Deleted e2e_timeouts fixture from tests/e2e/conftest.py
  - All E2E tests now use test_timeouts directly from shared conftest
- **Task 3.3 Complete**: Migrated all 13 E2E test files to use shared fixtures (admin_db):
  - **Completed**: tests/e2e/test_game_announcement.py - Removed all 5 custom fixtures, uses admin_db with inline ID fetching
  - **Completed**: tests/e2e/test_game_cancellation.py - Migrated to admin_db, fixed db_session reference at line 119
  - **Completed**: tests/e2e/test_waitlist_promotion.py - Migrated helper functions to use admin_db
  - **Completed**: tests/e2e/test_game_reminder.py - Migrated to admin_db
  - **Completed**: tests/e2e/test_game_update.py - Migrated to admin_db, fixed db_session reference at line 133
  - **Completed**: tests/e2e/test_game_status_transitions.py - Migrated to admin_db
  - **Completed**: tests/e2e/test_join_notification.py - Both test functions updated with ID fetching
  - **Completed**: tests/e2e/test_player_removal.py - Migrated to admin_db
  - **Completed**: tests/e2e/test_user_join.py - Migrated to admin_db
  - **Completed**: tests/e2e/test_signup_methods.py - 5 test functions migrated
  - **Completed**: tests/e2e/test_game_authorization.py - 3 test functions migrated
  - **Completed**: tests/e2e/test_00_environment.py - Migrated db_session→admin_db, http_client→authenticated_admin_client
  - **Completed**: tests/e2e/test_guild_routes_e2e.py - Migrated to admin_db, added guild_b_db_id fixture
  - **Completed**: tests/e2e/test_guild_isolation_e2e.py - Migrated to admin_db, added guild_b_template_id fixture
  - **Infrastructure**: Added ADMIN_DATABASE_URL to compose.e2e.yaml environment
  - **Infrastructure**: Created synced_guild_b fixture in tests/e2e/conftest.py
  - **Validation**: All 55 E2E tests passing

**Next Steps**: Task 3.3 complete. Phase 3 complete.

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
- tests/integration/test_game_signup_methods.py - Replaced custom test_user, test_template, and authenticated_client fixtures with helper functions (_create_test_user, _create_test_template, _create_authenticated_client), updated all tests to use shared factory fixtures and manage session cleanup, fixed parameter names (discord_user_id not discord_id), all 3 tests passing
- tests/integration/test_guild_queries.py - Completely rewritten to use shared fixtures (admin_db, create_guild, create_channel, create_user), removed all local fixture definitions (db_url, async_engine, async_session_factory, db, guild_b_config, channel_id, user_id, sample_game_data, sample_template_data), simplified test code by 60%, all 21 tests passing
- tests/integration/test_games_route_guild_isolation.py - Completely rewritten to use shared fixtures (admin_db, create_guild, create_channel, create_user, create_template, create_game), removed all local fixture definitions (db_url, async_engine, async_session_factory, db, redis_client, guild_a_id, guild_b_id, guild_a_config, guild_b_config, channel_a, channel_b, template_a, template_b, user_a, user_b, game_a, game_b), simplified from 434 lines to 319 lines (26% reduction), all 6 tests passing
- tests/conftest.py - Added TimeoutType enum and test_timeouts fixture (session-scoped) to provide standard timeout values for polling operations in both integration and E2E tests
- tests/e2e/conftest.py - Removed duplicate TimeoutType enum and e2e_timeouts implementation, added import of TimeoutType from tests.conftest, replaced e2e_timeouts with backward-compatible alias that wraps test_timeouts fixture
- tests/e2e/conftest.py - Removed duplicate api_base_url fixture (already exists in shared tests/conftest.py with environment variable support)
- tests/e2e/test_game_announcement.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced e2e_timeouts[TimeoutType] usage with test_timeouts[TimeoutType]
- tests/e2e/test_game_cancellation.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 3 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_game_reminder.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 4 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_game_status_transitions.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 6 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_game_update.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 3 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_join_notification.py - Replaced e2e_timeouts parameter with test_timeouts in 2 test function signatures, replaced 6 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_player_removal.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 4 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_signup_methods.py - Replaced e2e_timeouts parameter with test_timeouts in 5 test function signatures, replaced 10 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_user_join.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 3 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/test_waitlist_promotion.py - Replaced e2e_timeouts parameter with test_timeouts in test function signature, replaced 4 e2e_timeouts[TimeoutType] usages with test_timeouts[TimeoutType]
- tests/e2e/conftest.py - Removed e2e_timeouts backward-compatible alias fixture
- tests/e2e/conftest.py - Removed duplicate database fixtures (database_url, db_engine, db_session, http_client, guild_b_db_id, guild_b_template_id), cleaned up unused imports (async_sessionmaker, create_async_engine)
- tests/e2e/test_game_announcement.py - Removed all custom fixtures (clean_test_data, test_guild_id, test_channel_id, test_host_id, test_template_id), updated test to use admin_db and fetch IDs directly with inline SQL queries
- tests/e2e/test_waitlist_promotion.py - Removed all custom fixtures (clean_test_data, test_guild_id, test_template_id), updated test and helper functions (trigger_promotion_via_removal, trigger_promotion_via_max_players_increase) to use admin_db and fetch IDs directly

### Removed
