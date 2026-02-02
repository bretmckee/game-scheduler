<!-- markdownlint-disable-file -->

# Task Details: E2E Test Hermetic Isolation

## Research Reference

**Source Research**: #file:../research/20260201-e2e-test-hermetic-isolation-research.md

## Phase 1: Environment Variable Management

### Task 1.1: Create DiscordTestEnvironment dataclass

Create dataclass to load and validate all Discord IDs from environment variables at session start.

- **Files**:
  - tests/e2e/conftest.py - Add DiscordTestEnvironment dataclass at top of file
- **Success**:
  - Dataclass has fields for guild_a_id, channel_a_id, user_a_id, guild_b_id, channel_b_id, user_b_id
  - from_environment() classmethod validates all required env vars exist
  - validate_snowflake() helper validates Discord ID format (17-19 digits)
  - Clear error messages for missing/invalid variables
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 341-370) - Complete dataclass implementation
- **Dependencies**:
  - None (first task)

### Task 1.2: Create discord_ids session-scoped fixture

Create session-scoped fixture that loads DiscordTestEnvironment once at test start.

- **Files**:
  - tests/e2e/conftest.py - Add discord_ids fixture after DiscordTestEnvironment class
- **Success**:
  - Fixture is session-scoped (loads once per test run)
  - Returns DiscordTestEnvironment instance
  - Provides fail-fast behavior with clear error messages
  - All tests can access discord_ids.guild_a_id, discord_ids.channel_a_id, etc.
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 372-387) - Fixture implementation
- **Dependencies**:
  - Task 1.1 completion (needs DiscordTestEnvironment class)

## Phase 2: Guild Creation Fixtures

### Task 2.1: Create GuildContext dataclass

Create dataclass to hold all IDs for a test guild (database + Discord IDs).

- **Files**:
  - tests/e2e/conftest.py - Add GuildContext dataclass before fresh_guild fixture
- **Success**:
  - Dataclass has fields: db_id, discord_id, channel_db_id, channel_discord_id, template_id
  - All fields are strings (UUIDs or Discord snowflakes)
  - Provides type hints for IDE autocomplete
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 389-407) - GuildContext definition
- **Dependencies**:
  - None

### Task 2.2: Create fresh_guild fixture with cleanup

Create function-scoped fixture that creates Guild A via /api/v1/guilds/sync and cleans up after test.

- **Files**:
  - tests/e2e/conftest.py - Add fresh_guild fixture after GuildContext class
- **Success**:
  - Fixture calls /api/v1/guilds/sync to create guild database records
  - Queries database for guild_id, channel_id, template_id
  - Returns GuildContext with all IDs populated
  - Finally block deletes guild_configurations (CASCADE removes all related records)
  - Uses discord_ids fixture to get Guild A environment variables
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 409-469) - Complete fixture implementation
- **Dependencies**:
  - Task 1.1 completion (needs discord_ids fixture)
  - Task 2.1 completion (needs GuildContext class)
  - Existing fixtures: admin_db, authenticated_admin_client

### Task 2.3: Create fresh_guild_b fixture with cleanup

Create function-scoped fixture that creates Guild B via /api/v1/guilds/sync for cross-guild isolation tests.

- **Files**:
  - tests/e2e/conftest.py - Add fresh_guild_b fixture after fresh_guild
- **Success**:
  - Fixture calls /api/v1/guilds/sync with User B's authenticated client
  - Queries database for Guild B guild_id, channel_id, template_id
  - Returns GuildContext with Guild B IDs
  - Finally block deletes guild_configurations (CASCADE cleanup)
  - Uses discord_ids fixture to get Guild B environment variables
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 471-525) - Complete fixture implementation
- **Dependencies**:
  - Task 1.1 completion (needs discord_ids fixture)
  - Task 2.1 completion (needs GuildContext class)
  - Existing fixtures: admin_db, authenticated_client_b

## Phase 3: Remove Init Service Seeding

### Task 3.1: Remove seed_e2e_data() call from init service

Remove E2E seeding from init service Phase 6 to eliminate shared state.

- **Files**:
  - services/init/main.py - Remove seed_e2e_data() call in Phase 6
- **Success**:
  - Phase 6 section no longer calls seed_e2e_data()
  - Keep Discord ID environment variables in compose.e2e.yaml (required for fixtures)
  - Tests will fail until fixtures are updated (expected)
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 263-279) - Phase 1 approach
- **Dependencies**:
  - Task 2.2 completion (fresh_guild fixture must exist first)
  - Task 2.3 completion (fresh_guild_b fixture must exist first)

### Task 3.2: Mark seed_e2e.py as deprecated

Add deprecation notice to seed_e2e.py file without deleting it (has unit tests).

- **Files**:
  - services/init/seed_e2e.py - Add module-level deprecation comment
- **Success**:
  - File has clear deprecation notice at top
  - Explains that E2E tests now use fresh_guild fixtures
  - Keep file and unit tests for historical reference
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 723-730) - Deprecated files section
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Update test_00_environment.py

### Task 4.1: Keep database/migration validation tests

Preserve tests that validate database connectivity and migrations.

- **Files**:
  - tests/e2e/test_00_environment.py - Review and keep database/migration tests
- **Success**:
  - Tests for database connectivity remain unchanged
  - Tests for migration health remain unchanged
  - Tests for Discord API connectivity remain unchanged
  - No changes to test logic
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 306-330) - Phase 5 approach
- **Dependencies**:
  - None

### Task 4.2: Remove seeded data validation tests

Remove tests that validate init service seeded Guild A and Guild B data.

- **Files**:
  - tests/e2e/test_00_environment.py - Remove seeded data validation tests
- **Success**:
  - Remove tests that query for pre-existing guild_configurations
  - Remove tests that validate Guild A template exists
  - Remove tests that validate Guild B channel exists
  - Remove "E2E data seeded by init service" references
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 306-330) - Environment validation refactor
- **Dependencies**:
  - Task 3.1 completion (init service no longer seeds data)

### Task 4.3: Add discord_ids fixture validation test

Add test to verify discord_ids fixture loads environment variables correctly.

- **Files**:
  - tests/e2e/test_00_environment.py - Add test_discord_ids_fixture
- **Success**:
  - Test receives discord_ids fixture
  - Validates all six Discord IDs are non-empty strings
  - Validates Discord IDs have correct format (17-19 digits)
  - Test provides early validation before any guild operations
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 372-387) - discord_ids fixture usage
- **Dependencies**:
  - Task 1.2 completion (needs discord_ids fixture)

## Phase 5: Update Guild-Dependent Fixtures

### Task 5.1: Remove individual ID fixtures

Remove session-scoped fixtures that provide individual Discord IDs (replaced by discord_ids).

- **Files**:
  - tests/e2e/conftest.py - Remove individual ID fixtures
- **Success**:
  - Remove discord_guild_id fixture (use discord_ids.guild_a_id)
  - Remove discord_channel_id fixture (use discord_ids.channel_a_id)
  - Remove discord_user_id fixture (use discord_ids.user_a_id)
  - Remove discord_guild_b_id fixture (use discord_ids.guild_b_id)
  - Remove discord_channel_b_id fixture (use discord_ids.channel_b_id)
  - Remove discord_user_b_id fixture (use discord_ids.user_b_id)
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 341-387) - discord_ids fixture replaces individual fixtures
- **Dependencies**:
  - Task 1.2 completion (discord_ids fixture must exist)
  - Phase 6 completion (all tests updated to use discord_ids)

### Task 5.2: Replace guild_a_db_id and guild_b_db_id fixtures

Replace fixtures that query database for guild database IDs with simple passthroughs to fresh_guild.

- **Files**:
  - tests/e2e/conftest.py - Update guild_a_db_id and guild_b_db_id fixtures
- **Success**:
  - guild_a_db_id fixture depends on fresh_guild and returns fresh_guild.db_id
  - guild_b_db_id fixture depends on fresh_guild_b and returns fresh_guild_b.db_id
  - Remove database queries from fixtures
  - Fixtures now just provide convenient access to fresh_guild attributes
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 647-674) - Downstream fixture updates
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild)
  - Task 2.3 completion (needs fresh_guild_b)

### Task 5.3: Replace guild_a_template_id and guild_b_template_id fixtures

Replace fixtures that query database for template IDs with simple passthroughs to fresh_guild.

- **Files**:
  - tests/e2e/conftest.py - Update guild_a_template_id and guild_b_template_id fixtures
- **Success**:
  - guild_a_template_id fixture depends on fresh_guild and returns fresh_guild.template_id
  - guild_b_template_id fixture depends on fresh_guild_b and returns fresh_guild_b.template_id
  - Remove database queries and guild sync logic from fixtures
  - Fixtures provide convenient access to fresh_guild attributes
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 676-695) - Template fixture updates
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild)
  - Task 2.3 completion (needs fresh_guild_b)

### Task 5.4: Update synced_guild and synced_guild_b fixtures

Replace synced_guild fixtures to use fresh_guild implementation with cleanup.

- **Files**:
  - tests/e2e/conftest.py - Update synced_guild and synced_guild_b fixtures
- **Success**:
  - synced_guild fixture uses same implementation as fresh_guild (with cleanup)
  - synced_guild_b fixture uses same implementation as fresh_guild_b (with cleanup)
  - Both fixtures return GuildContext instead of sync_results dict
  - Tests using sync_results dict need updates (test_01_authentication.py)
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 598-645) - synced_guild replacement
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild implementation pattern)
  - Task 2.3 completion (needs fresh_guild_b implementation pattern)

## Phase 6: Migrate Test Files

### Task 6.1: Update test_01_authentication.py

Migrate authentication test to use fresh_guild fixture and GuildContext.

- **Files**:
  - tests/e2e/test_01_authentication.py - Update fixture dependencies
- **Success**:
  - Replace synced_guild with fresh_guild in test signatures
  - Update test assertions to use GuildContext attributes (not sync_results dict)
  - Remove discord_guild_id fixture dependency (use discord_ids if needed)
  - Test logic unchanged - only fixture access patterns updated
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 620-633) - Authentication test changes
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild fixture)
  - Task 5.4 completion (synced_guild uses GuildContext)

### Task 6.2: Update test_guild_routes_e2e.py

Migrate guild routes tests to use fresh_guild fixtures.

- **Files**:
  - tests/e2e/test_guild_routes_e2e.py - Update fixture dependencies
- **Success**:
  - Replace guild_a_db_id fixture with fresh_guild (use fresh_guild.db_id)
  - Replace guild_b_db_id fixture with fresh_guild_b (use fresh_guild_b.db_id)
  - Remove inline database queries for guild IDs
  - Test logic unchanged - only fixture access patterns updated
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 647-660) - Guild routes fixture updates
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild)
  - Task 2.3 completion (needs fresh_guild_b)

### Task 6.3: Update test_guild_isolation_e2e.py

Migrate guild isolation tests to use fresh_guild fixtures.

- **Files**:
  - tests/e2e/test_guild_isolation_e2e.py - Update fixture dependencies
- **Success**:
  - Replace guild_a_template_id with fresh_guild (use fresh_guild.template_id)
  - Replace guild_b_template_id with fresh_guild_b (use fresh_guild_b.template_id)
  - Remove inline database queries for template IDs
  - Test logic unchanged - only fixture access patterns updated
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 676-695) - Isolation test updates
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild)
  - Task 2.3 completion (needs fresh_guild_b)

### Task 6.4: Migrate 16 game-related test files

Migrate all remaining test files that depend on pre-seeded data.

- **Files**:
  - tests/e2e/test_game_announcement.py
  - tests/e2e/test_game_authorization.py
  - tests/e2e/test_game_cancellation.py
  - tests/e2e/test_game_reminder.py
  - tests/e2e/test_game_status_transitions.py
  - tests/e2e/test_game_update.py
  - tests/e2e/test_join_notification.py
  - tests/e2e/test_player_removal.py
  - tests/e2e/test_signup_methods.py
  - tests/e2e/test_user_join.py
  - tests/e2e/test_waitlist_promotion.py
  - Plus 5 more game-related test files
- **Success**:
  - Add fresh_guild to test function signatures
  - Replace inline database queries for guild_db_id with fresh_guild.db_id
  - Replace inline database queries for template_id with fresh_guild.template_id
  - Replace inline database queries for channel_db_id with fresh_guild.channel_db_id
  - Replace individual ID fixtures with discord_ids where needed
  - Test logic completely unchanged - only fixture dependencies modified
  - Remove "E2E data seeded by init service" from docstrings
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 527-596) - Migration patterns
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 697-721) - Complete test file inventory
- **Dependencies**:
  - Task 2.2 completion (needs fresh_guild)
  - Task 1.2 completion (needs discord_ids)

## Phase 7: Update Documentation

### Task 7.1: Update TESTING.md with new fixture patterns

Document new fixture patterns and hermetic test approach.

- **Files**:
  - docs/developer/TESTING.md - Add section on E2E fixtures
- **Success**:
  - Document fresh_guild and fresh_guild_b fixtures
  - Document GuildContext dataclass attributes
  - Document automatic cleanup behavior
  - Provide examples of test migration patterns
  - Explain why environment variables are still required (real Discord entities)
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 389-525) - Complete fixture implementation
- **Dependencies**:
  - Phase 2 completion (fixtures implemented)

### Task 7.2: Document environment variable validation

Document discord_ids fixture and environment variable requirements.

- **Files**:
  - docs/developer/TESTING.md - Add section on environment variable setup
- **Success**:
  - List all six required environment variables
  - Explain Discord snowflake ID format requirements
  - Document validation error messages and how to fix them
  - Explain that Discord guilds must be set up manually before testing
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 341-387) - Environment variable management
- **Dependencies**:
  - Task 1.1 completion (DiscordTestEnvironment implementation)
  - Task 1.2 completion (discord_ids fixture)

### Task 7.3: Add troubleshooting section

Add troubleshooting guide for common fixture and cleanup issues.

- **Files**:
  - docs/developer/TESTING.md - Add troubleshooting section
- **Success**:
  - Document cleanup failure scenarios
  - Explain database cascade behavior
  - Provide guidance on orphaned records
  - Document concurrent test execution patterns
  - Add examples of fixture dependency errors
- **Research References**:
  - #file:../research/20260201-e2e-test-hermetic-isolation-research.md (Lines 734-761) - Edge cases and considerations
- **Dependencies**:
  - Phase 6 completion (all tests migrated, real issues identified)

## Dependencies

- Pytest fixtures framework
- AsyncSession for database operations
- httpx.AsyncClient for API calls
- Discord bot with guild membership
- Database CASCADE constraints for cleanup

## Success Criteria

- All E2E tests pass with no shared state
- Each test creates and cleans up own guilds
- Can write tests that create guilds from scratch
- test_00_environment.py validates database/migrations only
- No orphaned database records after test suite
- Test logic unchanged - only fixture dependencies modified
- Guild creation/sync tests work without pre-seeded data
