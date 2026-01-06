<!-- markdownlint-disable-file -->

# Task Details: Consolidate Test Fixtures

## Research Reference

**Source Research**: [../research/20260104-consolidate-test-fixtures-research.md](../research/20260104-consolidate-test-fixtures-research.md)

## Phase 0: Create and Test Shared Fixtures

### Task 0.1: Create `tests/conftest.py` with all core fixtures

Create the master fixture file with all shared fixtures organized into sections:
- Database URL fixtures (session scope)
- Database session fixtures (function scope) with automatic cleanup
- Redis client fixtures (sync primary, async wrapper)
- Redis cache seeding factory fixture
- Data creation factory fixtures (guild, channel, user, template, game)
- Composite fixtures (test_environment)

Implementation must follow architecture principles from research:
- Factory pattern: fixtures return functions, not data
- Sync-first: primary implementation is sync, async is wrapper
- Hermetic: automatic cleanup via admin_db_sync
- RLS safe: always use admin user for fixture creation

- **Files**:
  - [tests/conftest.py](tests/conftest.py) - Create with ~500 lines of fixture code
- **Success**:
  - File exists with all fixtures defined
  - Fixtures follow factory pattern
  - admin_db_sync includes automatic cleanup with DELETE (not TRUNCATE)
  - redis_client uses sync implementation
  - seed_redis_cache factory consolidates inline cache seeding
- **Research References**:
  - [Research Lines 180-700](../research/20260104-consolidate-test-fixtures-research.md#L180-L700) - Complete fixture implementations
  - [Research Lines 107-130](../research/20260104-consolidate-test-fixtures-research.md#L107-L130) - Deadlock prevention pattern
  - [Research Lines 133-145](../research/20260104-consolidate-test-fixtures-research.md#L133-L145) - Factory pattern rationale
- **Dependencies**:
  - None (creates foundation for all other tasks)

### Task 0.2: Create comprehensive fixture validation tests

Create `tests/integration/test_shared_fixtures.py` to validate:
- Each factory fixture works independently
- Multiple calls to same factory create distinct objects
- Composite fixtures create connected objects
- Redis cache seeding populates all expected keys
- Automatic cleanup removes all test data
- No deadlocks occur with long-running connections

Tests must cover failure scenarios from debugging session.

- **Files**:
  - [tests/integration/test_shared_fixtures.py](tests/integration/test_shared_fixtures.py) - Create with ~300 lines
- **Success**:
  - test_admin_db_sync_fixture_only passes
  - test_create_guild_factory passes
  - test_create_multiple_guilds passes
  - test_test_environment_composite passes
  - test_seed_redis_cache passes
  - All tests pass without hanging
- **Research References**:
  - [Research Lines 860-920](../research/20260104-consolidate-test-fixtures-research.md#L860-L920) - Fixture validation test examples
  - [Research Lines 740-760](../research/20260104-consolidate-test-fixtures-research.md#L740-L760) - Implementation plan Phase 0
- **Dependencies**:
  - Task 0.1 (fixtures must exist)

### Task 0.3: Verify fixture tests pass without deadlocks

Run fixture validation tests and verify:
- All tests pass
- No hanging or timeouts
- Automatic cleanup works correctly
- Run existing tests to ensure no breaking changes

- **Files**:
  - N/A (verification step)
- **Success**:
  - `docker compose run integration-tests tests/integration/test_shared_fixtures.py` passes
  - No deadlocks or hanging
  - Existing integration tests still pass
- **Research References**:
  - [Research Lines 750-760](../research/20260104-consolidate-test-fixtures-research.md#L750-L760) - Phase 0 success criteria
- **Dependencies**:
  - Task 0.2 (tests must exist)

## Phase 1: Migrate Sync-Based Integration Tests

### Task 1.1: Migrate `test_notification_daemon.py`

Replace custom `test_game_session` fixture with factory fixtures.

Pattern transformation:
- OLD: Single fixture creates guild+channel+user+game, returns game_id
- NEW: Test directly calls create_guild(), create_channel(), create_user(), create_game()
- DELETE: `test_game_session` fixture after migration
- VERIFY: All notification daemon tests pass

- **Files**:
  - [tests/integration/test_notification_daemon.py](tests/integration/test_notification_daemon.py) - Update all test functions
- **Success**:
  - `test_game_session` fixture deleted
  - All test functions updated to use factory fixtures
  - All tests pass
  - Tests are more readable
- **Research References**:
  - [Research Lines 762-790](../research/20260104-consolidate-test-fixtures-research.md#L762-L790) - Phase 1 migration pattern
  - [Research Lines 922-955](../research/20260104-consolidate-test-fixtures-research.md#L922-L955) - Before/after example
- **Dependencies**:
  - Phase 0 complete (shared fixtures available)

### Task 1.2: Migrate `test_status_transitions.py`

Replace identical `test_game_session` fixture with factory fixtures.

Same pattern as Task 1.1 - this test has the exact same fixture.

- **Files**:
  - [tests/integration/test_status_transitions.py](tests/integration/test_status_transitions.py) - Update all test functions
- **Success**:
  - `test_game_session` fixture deleted
  - All test functions updated
  - All tests pass
- **Research References**:
  - [Research Lines 762-790](../research/20260104-consolidate-test-fixtures-research.md#L762-L790) - Phase 1 migration pattern
  - [Research Lines 82-83](../research/20260104-consolidate-test-fixtures-research.md#L82-L83) - Duplicate fixture noted
- **Dependencies**:
  - Phase 0 complete

### Task 1.3: Migrate `test_retry_daemon.py`

Simplify test setup using factory fixtures.

This test may have simpler custom fixtures or inline setup - replace with factory pattern.

- **Files**:
  - [tests/integration/test_retry_daemon.py](tests/integration/test_retry_daemon.py) - Update test functions
- **Success**:
  - Custom fixtures deleted
  - Test functions use factory fixtures
  - All tests pass
- **Research References**:
  - [Research Lines 762-790](../research/20260104-consolidate-test-fixtures-research.md#L762-L790) - Phase 1 migration pattern
- **Dependencies**:
  - Phase 0 complete

### Task 1.4: Migrate `test_template_default_overrides.py`

Remove conflicting `clean_test_data` fixture and use hermetic test pattern.

Critical: This test has cleanup fixture that conflicts with automatic cleanup.

Pattern transformation:
- OLD: `clean_test_data` fixture deletes before/after test
- NEW: Test creates what it needs, relies on automatic cleanup
- DELETE: `clean_test_data` fixture
- VERIFY: Tests pass, "No channels found" error resolved

- **Files**:
  - [tests/integration/test_template_default_overrides.py](tests/integration/test_template_default_overrides.py) - Remove fixture, update tests
- **Success**:
  - `clean_test_data` fixture deleted
  - Tests use factory fixtures
  - No "No channels found" errors
  - All tests pass
- **Research References**:
  - [Research Lines 86-105](../research/20260104-consolidate-test-fixtures-research.md#L86-L105) - Cleanup conflict explanation
  - [Research Lines 762-790](../research/20260104-consolidate-test-fixtures-research.md#L762-L790) - Migration pattern
- **Dependencies**:
  - Phase 0 complete

### Task 1.5: Migrate `test_game_signup_methods.py`

Remove custom fixtures and replace inline Redis cache seeding with `seed_redis_cache` fixture.

This test has:
- Custom `test_user`, `test_template`, `authenticated_client` fixtures
- Inline Redis cache seeding code (5 cache keys duplicated)

Pattern transformation:
- OLD: Custom fixtures + inline asyncio.run(redis_client.set_json(...))
- NEW: Factory fixtures + asyncio.run(seed_redis_cache(...))
- DELETE: All custom fixtures
- CONSOLIDATE: 5 inline cache operations → 1 seed_redis_cache call

- **Files**:
  - [tests/integration/test_game_signup_methods.py](tests/integration/test_game_signup_methods.py) - Remove fixtures, update tests
- **Success**:
  - Custom fixtures deleted
  - Inline cache seeding replaced with seed_redis_cache
  - All tests pass
  - Code is simpler
- **Research References**:
  - [Research Lines 8-9](../research/20260104-consolidate-test-fixtures-research.md#L8-L9) - Redis cache duplication problem
  - [Research Lines 340-465](../research/20260104-consolidate-test-fixtures-research.md#L340-L465) - seed_redis_cache fixture implementation
- **Dependencies**:
  - Phase 0 complete

## Phase 2: Migrate Async ORM Integration Tests

### Task 2.1: Migrate `test_guild_queries.py`

Update async tests to use shared fixtures consistently.

Remove any local fixtures that duplicate shared fixtures.

- **Files**:
  - [tests/integration/test_guild_queries.py](tests/integration/test_guild_queries.py) - Remove local fixtures, use shared
- **Success**:
  - Local fixtures deleted
  - Tests use fixtures from `tests/conftest.py`
  - All tests pass
- **Research References**:
  - [Research Lines 792-805](../research/20260104-consolidate-test-fixtures-research.md#L792-L805) - Phase 2 goals
- **Dependencies**:
  - Phase 0 complete

### Task 2.2: Migrate `test_games_route_guild_isolation.py`

Update async tests to use shared fixtures consistently.

This test validates RLS - ensure it uses admin_db for setup, app_db for testing.

- **Files**:
  - [tests/integration/test_games_route_guild_isolation.py](tests/integration/test_games_route_guild_isolation.py) - Remove local fixtures
- **Success**:
  - Local fixtures deleted
  - Tests use shared fixtures correctly
  - RLS validation still works
  - All tests pass
- **Research References**:
  - [Research Lines 792-805](../research/20260104-consolidate-test-fixtures-research.md#L792-L805) - Phase 2 goals
- **Dependencies**:
  - Phase 0 complete

## Phase 3: Consolidate E2E Test Fixtures

### Task 3.1: Identify e2e-specific vs shared fixtures

Audit `tests/e2e/conftest.py` and determine which fixtures should:
- KEEP: E2E-specific (Discord tokens, authenticated clients, helpers)
- MIGRATE: Data creation (guild/channel/user/game factories)
- MIGRATE: Database access (use admin_db from tests/conftest.py)
- DELETE: Duplicate fixtures (api_base_url, http_client, timeouts)

Document migration plan for e2e fixtures and remove duplicates.

**E2E FIXTURE MIGRATION PLAN**:

**USE from shared tests/conftest.py (already exist)**:
- `api_base_url` - API base URL (already removed duplicate ✓)
- `test_timeouts` - Timeout values (already consolidated with alias ✓)
- `admin_db` / `admin_db_sync` - Database sessions with automatic cleanup
- `create_guild()` - Guild factory
- `create_channel()` - Channel factory
- `create_user()` - User factory
- `create_template()` - Template factory
- `create_game()` - Game factory
- `seed_redis_cache()` - Redis cache seeding factory
- `test_environment()` - Composite fixture (guild + channel + user)
- `test_game_environment()` - Composite fixture with game
- `create_authenticated_client()` - Sync authenticated client factory

**USE from tests/shared/polling.py (already exist)**:
- `wait_for_db_condition_async()` - Async database polling
- `wait_for_db_condition_sync()` - Sync database polling

**MIGRATE to shared tests/conftest.py (create new)**:
- `create_authenticated_client_async()` - Async authenticated client factory
  - Replaces: `authenticated_admin_client`, `authenticated_client_b` fixtures
  - Tests call: `await create_authenticated_client_async(token, discord_id)`

**MIGRATE to tests/shared/polling.py (create new)**:
- `wait_for_game_message_id()` - Poll for game message_id population
  - Useful for both integration and E2E tests

**DELETE from tests/e2e/conftest.py (duplicates or replaced)**:
- `database_url` - Use `admin_db_url` from shared
- `db_engine` - Use `admin_db` session fixture from shared
- `db_session` - Use `admin_db` session fixture from shared
- `guild_b_db_id` - Tests call `create_guild(discord_guild_id=discord_guild_b_id)`
- `guild_b_template_id` - Tests call `create_template(guild_id=...)`
- `authenticated_admin_client` - Tests call async factory
- `authenticated_client_b` - Tests call async factory
- `http_client` - Tests use authenticated clients or httpx.Client directly
- `wait_for_db_condition()` - Wrapper unnecessary, use shared polling directly
- `e2e_timeouts` - Remove alias, use `test_timeouts` directly (Task 3.2)

**KEEP in tests/e2e/conftest.py (truly E2E-specific)**:
- `discord_token` - Discord admin bot A token (session)
- `discord_main_bot_token` - Main bot token for notifications (session)
- `discord_guild_id` - Test Discord guild A ID (session)
- `discord_channel_id` - Test Discord channel A ID (session)
- `discord_user_id` - Test Discord user ID (session)
- `discord_guild_b_id` - Guild B for isolation testing (session)
- `discord_channel_b_id` - Channel in Guild B (session)
- `discord_user_b_id` - User B ID (session)
- `discord_user_b_token` - User B bot token (session)
- `discord_helper` - Discord test helper wrapper (function)
- `bot_discord_id` - Extract bot ID from token (session)
- `synced_guild` - Guild sync workflow fixture (function)

**RESULT**: E2E conftest reduced from ~24 fixtures to ~12 fixtures (all truly E2E-specific)

- **Files**:
  - [tests/e2e/conftest.py](tests/e2e/conftest.py) - Analyze fixtures, delete duplicates
  - [tests/conftest.py](tests/conftest.py) - Already has api_base_url, test_timeouts
- **Success**:
  - Clear migration plan documented above
  - Duplicate fixtures removed from e2e conftest (api_base_url ✓)
  - Timeout consolidation complete (test_timeouts ✓)
- **Duplicates Removed**:
  - `api_base_url` - deleted from e2e, use shared version ✓
  - `TimeoutType` and timeouts - migrated to shared conftest as `test_timeouts` ✓
- **Research References**:
  - [Research Lines 807-825](../research/20260104-consolidate-test-fixtures-research.md#L807-L825) - Phase 3 approach
  - [Research Lines 58-75](../research/20260104-consolidate-test-fixtures-research.md#L58-L75) - E2E fixture landscape
- **Dependencies**:
  - Phase 0 complete

### Task 3.2: Remove e2e_timeouts backward-compatible alias

Replace all uses of `e2e_timeouts` fixture with `test_timeouts` across E2E tests.

Simple mechanical replacement:
- Change function parameter: `e2e_timeouts` → `test_timeouts`
- All usage already via dict keys (no code changes in function bodies)
- Remove `e2e_timeouts` fixture from tests/e2e/conftest.py

Affected files (~50 occurrences across 12 test files):
- test_game_announcement.py
- test_game_cancellation.py
- test_game_reminder.py
- test_game_status_transitions.py
- test_game_update.py
- test_join_notification.py
- test_player_removal.py
- test_signup_methods.py
- test_user_join.py
- test_waitlist_promotion.py
- (and 2 more)

- **Files**:
  - [tests/e2e/conftest.py](tests/e2e/conftest.py) - Remove e2e_timeouts alias fixture
  - [tests/e2e/*.py](tests/e2e/) - Replace e2e_timeouts → test_timeouts in ~12 files
- **Success**:
  - All e2e tests use test_timeouts directly
  - e2e_timeouts fixture deleted
  - All e2e tests pass
- **Research References**:
  - [Research Lines 807-825](../research/20260104-consolidate-test-fixtures-research.md#L807-L825) - Phase 3 consolidation approach
- **Dependencies**:
  - Task 3.1 complete (analysis done)

### Task 3.3: Migrate 12 e2e test files to shared fixtures

Update all e2e test files to use factory fixtures from `tests/conftest.py`.

E2E test files (from research):
- Each has 3-5 custom fixtures for guild/channel/user/game creation
- Replace with factory fixtures
- Keep e2e-specific fixtures (auth, Discord helpers)

This is the largest migration task - may need to be broken into subtasks.

- **Files**:
  - All 12 e2e test files - Update to use shared fixtures
  - [tests/e2e/conftest.py](tests/e2e/conftest.py) - Remove migrated fixtures
- **Success**:
  - All e2e test files updated
  - Custom data creation fixtures deleted
  - All e2e tests pass
  - Duplicate fixtures eliminated
- **Research References**:
  - [Research Lines 807-825](../research/20260104-consolidate-test-fixtures-research.md#L807-L825) - Phase 3 goals
  - [Research Lines 76-79](../research/20260104-consolidate-test-fixtures-research.md#L76-L79) - E2E duplication problem
- **Dependencies**:
  - Task 3.1 (migration plan defined)

## Phase 4: Delete Redundant Fixtures

### Task 4.1: Delete deprecated fixtures from `tests/integration/conftest.py`

Aggressively delete fixtures superseded by `tests/conftest.py`.

DELETE immediately:
- `db_url`, `admin_db_url` (replaced by versions in tests/conftest.py)
- `async_engine`, `admin_async_engine` (replaced by session fixtures)
- `db`, `admin_db` (replaced by versions in tests/conftest.py)
- `redis_client` async version (replaced by sync version + async wrapper)
- `seed_user_guilds_cache()`, `seed_user_session()` helpers (replaced by seed_redis_cache)
- `guild_a_config`, `guild_b_config`, `channel_a`, `channel_b`, `template_a`, `template_b`, `user_a`, `user_b`, `game_a`, `game_b` (replaced by factories)
- `guild_a_id`, `guild_b_id` (not needed with factory pattern)

KEEP:
- `rabbitmq_url`, `rabbitmq_connection`, `rabbitmq_channel` (RabbitMQ specific)
- `cleanup_guild_context`, `cleanup_db_engine` (autouse cleanup)

- **Files**:
  - [tests/integration/conftest.py](tests/integration/conftest.py) - Delete deprecated fixtures
- **Success**:
  - All deprecated fixtures deleted
  - Only RabbitMQ and autouse fixtures remain
  - File reduced from ~300 lines to ~50 lines
- **Research References**:
  - [Research Lines 827-860](../research/20260104-consolidate-test-fixtures-research.md#L827-L860) - Deletion list
  - [Research Lines 805](../research/20260104-consolidate-test-fixtures-research.md#L805) - Aggressive deletion policy
- **Dependencies**:
  - Phase 1 and Phase 2 complete (all tests migrated)

### Task 4.2: Verify all tests still pass after cleanup

Run full test suite to verify fixture consolidation is complete and successful.

- **Files**:
  - N/A (verification step)
- **Success**:
  - All integration tests pass
  - All e2e tests pass
  - No fixture import errors
  - No deadlocks or cleanup conflicts
- **Research References**:
  - [Research Lines 957-975](../research/20260104-consolidate-test-fixtures-research.md#L957-L975) - Benefits summary
- **Dependencies**:
  - All other tasks complete

## Success Criteria

Overall task is complete when:
- 100+ duplicated fixtures consolidated to ~15 shared factory fixtures
- All integration and e2e tests migrated and passing
- No deadlocks or cleanup conflicts
- Redundant fixtures deleted
- Code is simpler and more maintainable
