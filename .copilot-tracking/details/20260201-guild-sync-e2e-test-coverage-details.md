<!-- markdownlint-disable-file -->

# Task Details: Guild Sync E2E Test Coverage

## Research Reference

**Source Research**: #file:../research/20260201-guild-sync-e2e-test-coverage-research.md

## Phase 1: Test Infrastructure Setup

### Task 1.1: Create test_guild_sync_e2e.py file structure

Create new test file tests/e2e/test_guild_sync_e2e.py with proper imports and structure following existing e2e test patterns.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - New test file for guild sync e2e tests
- **Success**:
  - File created with pytest imports and async test structure
  - Follows naming convention (test_XX_feature pattern)
  - Includes proper docstring header
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 63-82) - Existing test file patterns
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 152-158) - Test execution requirements
- **Dependencies**:
  - pytest-asyncio package
  - Existing e2e test infrastructure

### Task 1.2: Add database verification helper fixtures

Create helper fixtures in tests/e2e/test_guild_sync_e2e.py for querying guild, channel, and template records from database.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add helper fixtures
- **Success**:
  - get_guild_by_discord_id() fixture created
  - get_channels_for_guild() fixture created
  - get_templates_for_guild() fixture created
  - Each fixture uses admin_db and returns database records
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 97-109) - Database verification pattern
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 147-151) - Database tables involved
- **Dependencies**:
  - admin_db fixture from conftest.py
  - SQLAlchemy text() for raw SQL queries

## Phase 2: Basic Sync Tests

### Task 2.1: Implement complete guild creation verification test

Create test_complete_guild_creation() that verifies all aspects of guild sync: guild config, channel configs, and default template.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - Test calls /api/v1/guilds/sync endpoint
  - Verifies GuildConfiguration created with correct Discord snowflake
  - Verifies ChannelConfiguration records created for text channels
  - Verifies default GameTemplate created for first text channel
  - Verifies response counts match database records
  - Verifies user can access guild through /api/v1/guilds endpoint
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 36-52) - Current test gaps
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 54-89) - sync_user_guilds() implementation
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 111-130) - Guild sync service implementation
- **Dependencies**:
  - authenticated_admin_client fixture
  - admin_db fixture
  - Helper fixtures from Task 1.2

### Task 2.2: Implement idempotency test (multiple syncs)

Create test_sync_idempotency() that verifies calling sync twice doesn't create duplicates.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - First sync call creates records (new_guilds > 0)
  - Second sync call creates no records (new_guilds = 0, new_channels = 0)
  - Database has no duplicate guild/channel/template records
  - Guild remains accessible after second sync
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 41-45) - Idempotency gap identified
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 54-89) - sync_user_guilds() handles existing guilds
- **Dependencies**:
  - authenticated_admin_client fixture
  - admin_db fixture
  - Helper fixtures from Task 1.2

## Phase 3: Multi-Guild and Isolation Tests

### Task 3.1: Implement multi-guild sync test

Create test_multi_guild_sync() that verifies User A and User B each sync only their admin guilds.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - User A syncs and only Guild A is created
  - User B syncs and only Guild B is created
  - Cross-guild isolation verified (User A cannot see Guild B data)
  - Both guilds have proper channel and template configurations
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 91-95) - Available fixtures for Guild A and B
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 111-130) - Candidate guild computation
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 164-177) - E2E environment configuration
- **Dependencies**:
  - authenticated_admin_client and authenticated_client_b fixtures
  - discord_guild_id and discord_guild_b_id fixtures
  - admin_db fixture
  - Guild A and Guild B configured in env.e2e

### Task 3.2: Implement RLS enforcement verification test

Create test_rls_enforcement_after_sync() that verifies RLS properly isolates guild data after sync.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - User A syncs Guild A
  - User B syncs Guild B
  - User A can query Guild A games/templates
  - User A gets 404 for Guild B games/templates
  - User B can query Guild B games/templates
  - User B gets 404 for Guild A games/templates
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 152-158) - RLS context management
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 111-130) - RLS context expansion during sync
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 65-67) - Cross-guild isolation test pattern
- **Dependencies**:
  - authenticated_admin_client and authenticated_client_b fixtures
  - synced_guild and synced_guild_b fixtures
  - admin_db fixture
  - Game and template creation capabilities

## Phase 4: Edge Cases and Error Handling

### Task 4.1: Implement channel filtering test (text channels only)

Create test_channel_filtering() that verifies only text channels (type=0) are synced.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - Guild sync creates only text channel configs (type=0)
  - Voice channels (type=2) not created in database
  - Default template uses first text channel
  - Response new_channels count matches text channel count
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 132-148) - Channel creation logic with type filtering
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 160-162) - Discord API channel endpoint
- **Dependencies**:
  - authenticated_admin_client fixture
  - admin_db fixture
  - Discord guild with multiple channel types
  - Helper fixtures from Task 1.2

### Task 4.2: Implement template creation edge cases tests

Create test_template_creation_edge_cases() that verifies template creation in various scenarios.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - Guild with no channels: no template created
  - Guild with only voice channels: no template created
  - Guild with text channels: template created
  - Template has is_default=True
  - Template channel_id matches first text channel
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 132-148) - Template creation for first text channel
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 147-151) - game_templates table schema
- **Dependencies**:
  - authenticated_admin_client fixture
  - admin_db fixture
  - Discord guilds with different channel configurations
  - Helper fixtures from Task 1.2

### Task 4.3: Implement permission checking test

Create test_permission_checking() that verifies sync respects Discord permissions.

- **Files**:
  - tests/e2e/test_guild_sync_e2e.py - Add test function
- **Success**:
  - User without MANAGE_GUILD permission gets empty result
  - User in guilds where bot not installed gets empty result
  - Only guilds where user has MANAGE_GUILD AND bot is installed are synced
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 111-130) - Candidate guild computation (bot guilds ∩ user admin guilds)
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 160-162) - Discord API permission flags
- **Dependencies**:
  - Multiple Discord test users with different permission levels
  - authenticated clients for different users
  - admin_db fixture

## Phase 5: Cleanup and Integration

### Task 5.1: Update existing minimal test or remove if superseded

Review tests/e2e/test_01_authentication.py test_synced_guild_creates_configs() and either enhance or remove if superseded by new tests.

- **Files**:
  - tests/e2e/test_01_authentication.py - Update or remove minimal test
- **Success**:
  - Decision made on test_synced_guild_creates_configs() fate
  - If removed: New tests provide equivalent coverage
  - If kept: Test enhanced to add value beyond new test suite
  - No duplicate test coverage
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 36-41) - Existing minimal test
- **Dependencies**:
  - Task 2.1 completion (comprehensive test exists)

### Task 5.2: Verify all tests pass and clean up properly

Run full e2e test suite to verify new tests pass and don't interfere with existing tests.

- **Files**:
  - scripts/run-e2e-tests.sh - Run e2e test suite
  - tests/e2e/test_guild_sync_e2e.py - Verify cleanup
- **Success**:
  - All new guild sync tests pass
  - All existing e2e tests still pass
  - No test pollution (tests run independently)
  - Test execution time reasonable
  - Coverage report shows increased guild sync coverage
- **Research References**:
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 97-109) - Existing test patterns
  - #file:../research/20260201-guild-sync-e2e-test-coverage-research.md (Lines 164-177) - E2E environment configuration
- **Dependencies**:
  - All previous tasks completed
  - E2E environment properly configured
  - scripts/run-e2e-tests.sh script

## Dependencies

- pytest and pytest-asyncio for test execution
- Existing e2e test infrastructure (fixtures, clients, database)
- Real Discord environment (guilds, channels, users, bot)
- PostgreSQL RLS implementation
- Guild sync service implementation

## Success Criteria

- All 8 test scenarios implemented and passing
- Tests verify both API responses and database state
- Tests are idempotent and can run multiple times
- Tests verify cross-guild isolation and RLS enforcement
- Tests follow project conventions (naming, patterns, fixtures)
- No test pollution between runs
- Line coverage for guild sync functionality significantly increased
