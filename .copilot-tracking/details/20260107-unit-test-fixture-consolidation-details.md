<!-- markdownlint-disable-file -->

# Task Details: Unit Test Fixture Consolidation

## Research Reference

**Source Research**: #file:../research/20260107-unit-test-fixture-duplication-research.md

## Phase 1: Game Service Cluster Consolidation (Critical Impact)

### Task 1.1: Create tests/services/api/services/conftest.py with 7 shared fixtures

Create new conftest.py file to consolidate fixtures used by 4 game service test files.

- **Files**:
  - tests/services/api/services/conftest.py - NEW FILE to create
- **Success**:
  - File created with 7 fixture definitions
  - All fixtures properly documented
  - Fixtures use correct AsyncMock/MagicMock specs
  - No syntax errors, passes linting
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 350-425) - Complete conftest.py implementation example
  - #file:../../tests/conftest.py (Lines 1-50) - Existing conftest structure patterns
- **Implementation**:
  - Create fixtures: mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel, sample_user, sample_template
  - Follow existing patterns from root conftest.py
  - Use function scope (default) for all fixtures
  - Import required modules: pytest, AsyncMock, MagicMock, AsyncSession, games_service, resolver_module, discord_client_module, messaging_publisher, model modules
- **Dependencies**:
  - Directory tests/services/api/services/ exists (it does)

### Task 1.2: Remove 28 duplicate fixtures from 4 game service test files

Remove local fixture definitions that are now in conftest.py, keeping only file-specific fixtures.

- **Files**:
  - tests/services/api/services/test_games.py - Remove 7 fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel)
  - tests/services/api/services/test_games_promotion.py - Remove 7 fixtures (same list)
  - tests/services/api/services/test_games_edit_participants.py - Remove 7 fixtures (all its fixtures)
  - tests/services/api/services/test_games_image_upload.py - Remove 7 fixtures (same list)
- **Success**:
  - All 7 fixtures removed from each file
  - No import statements added (pytest auto-discovers fixtures)
  - Tests still reference fixtures by name
  - File-specific fixtures remain (e.g., sample_game_data in test_games.py)
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 85-110) - Duplication analysis showing exact matches
- **Dependencies**:
  - Task 1.1 completed

### Task 1.3: Verify game service tests pass with shared fixtures

Run game service tests to ensure consolidation didn't break anything.

- **Files**:
  - All tests/services/api/services/test_*.py files
- **Success**:
  - All game service tests pass (100% pass rate)
  - No fixture discovery errors
  - No import errors
  - Test execution time unchanged
- **Implementation**:
  - Run: `uv run pytest tests/services/api/services/ -v`
  - Check for fixture not found errors
  - Verify all assertions still work
- **Dependencies**:
  - Task 1.2 completed

## Phase 2: Mock Object Consolidation (High Impact)

### Task 2.1: Add mock_db fixture to tests/conftest.py

Add shared mock_db fixture to root conftest.py, overridden by service-level conftest when needed.

- **Files**:
  - tests/conftest.py - Add mock_db fixture
- **Success**:
  - Fixture added after existing fixtures (around line 800)
  - Documented as "for unit tests only, integration tests use admin_db_sync/app_db"
  - Returns AsyncMock(spec=AsyncSession)
  - Imports added: AsyncSession from sqlalchemy.ext.asyncio
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 427-445) - Root conftest extension example
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 45-75) - mock_db duplication analysis (12+ duplicates)
- **Implementation**:
  - Add after line 796 (end of existing fixtures)
  - Use function scope
  - Add clear docstring distinguishing from integration test DB fixtures
- **Dependencies**:
  - Phase 1 completed

### Task 2.2: Remove 12+ mock_db duplicates from unit test files

Remove all mock_db fixtures from unit test files that don't override behavior.

- **Files**:
  - tests/services/bot/auth/test_role_checker.py - Remove mock_db (line ~36)
  - tests/services/api/routes/test_templates.py - Remove mock_db
  - tests/services/api/routes/test_guilds.py - Remove mock_db
  - tests/services/api/dependencies/test_permissions_migration.py - Remove mock_db
  - tests/services/api/services/test_calendar_export.py - Remove mock_db
  - tests/services/api/services/test_template_service.py - Remove mock_db
  - tests/services/api/services/test_participant_resolver.py - Remove mock_db
  - tests/shared/data_access/test_guild_queries.py - Remove mock_db
  - Plus 4 game service test files (if not already removed in Phase 1)
- **Success**:
  - All mock_db fixtures removed from listed files
  - Tests still pass (fixture discovered from conftest.py)
  - No duplicate fixture warnings
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 45-75) - Complete list of mock_db locations
- **Dependencies**:
  - Task 2.1 completed

### Task 2.3: Add mock_discord_api_client to tests/conftest.py

Add shared Discord REST API client mock to root conftest.py.

- **Files**:
  - tests/conftest.py - Add mock_discord_api_client fixture
- **Success**:
  - Fixture returns MagicMock(spec=discord_client_module.DiscordAPIClient)
  - Docstring clarifies this is for REST API client (not discord.py bot)
  - Import added: from shared.discord import client as discord_client_module
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 112-130) - Discord client duplication analysis (7 API + 2 Bot)
- **Dependencies**:
  - Task 2.1 completed

### Task 2.4: Add mock_discord_bot to tests/services/bot/conftest.py

Create bot-specific conftest.py with discord.py bot client mock.

- **Files**:
  - tests/services/bot/conftest.py - NEW FILE to create
- **Success**:
  - File created with mock_bot fixture
  - Returns MagicMock(spec=discord.Client)
  - Import added: import discord
  - Docstring clarifies this is for discord.py gateway/commands
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 112-130) - Discord client types analysis
- **Dependencies**:
  - Task 2.3 completed

### Task 2.5: Verify all unit tests pass after mock consolidation

Run full unit test suite to ensure Phase 2 changes work correctly.

- **Files**:
  - All tests/services/**/*.py and tests/shared/**/*.py
- **Success**:
  - All unit tests pass (100% pass rate)
  - No fixture discovery issues
  - No import errors
  - Mock behavior unchanged
- **Implementation**:
  - Run: `uv run pytest tests/services/ tests/shared/ -v --ignore=tests/integration --ignore=tests/e2e`
  - Check for any failures or warnings
- **Dependencies**:
  - Tasks 2.1-2.4 completed

## Phase 3: Sample Data Model Consolidation (Medium Impact)

### Task 3.1: Create model factory fixtures in tests/conftest.py

Add lightweight factory fixtures for creating model objects without database.

- **Files**:
  - tests/conftest.py - Add create_sample_user, create_sample_guild, create_sample_channel factories
- **Success**:
  - 3 factory fixtures added (create_sample_user, create_sample_guild, create_sample_channel)
  - Each returns function that creates model with optional parameters
  - Factories use uuid.uuid4() for IDs by default
  - Allow discord_id/guild_id/channel_id override via parameters
  - Docstrings explain factory pattern usage
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 427-455) - Factory fixture examples
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 160-200) - Sample data duplication analysis (23 fixtures)
  - #file:../../tests/conftest.py (Lines 318-513) - Existing factory patterns (create_guild, create_user, etc.)
- **Implementation**:
  - create_sample_user: Returns function(discord_id=None) -> User
  - create_sample_guild: Returns function(guild_id=None) -> GuildConfiguration
  - create_sample_channel: Returns function(guild, channel_id=None) -> ChannelConfiguration
  - Follow existing factory pattern from lines 318+
- **Dependencies**:
  - Phase 2 completed

### Task 3.2: Migrate tests to use factory fixtures instead of local sample_* fixtures

Update tests to call factory functions instead of using sample_* fixtures directly.

- **Files**:
  - All files with sample_guild, sample_channel, sample_user fixtures (excluding conftest files)
  - Focus on: test_guilds.py, test_templates.py, test_calendar_export.py, bot command tests
- **Success**:
  - Tests call create_sample_user() to get user instance
  - Tests call create_sample_guild() to get guild instance
  - Tests can customize IDs: create_sample_guild(guild_id="custom123")
  - Tests still pass with same behavior
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 160-200) - Lists all sample_* fixture locations
- **Implementation**:
  - Replace `sample_user` fixture usage with `user = create_sample_user()`
  - Replace `sample_guild` fixture usage with `guild = create_sample_guild()`
  - Replace `sample_channel(sample_guild)` with `channel = create_sample_channel(guild)`
- **Dependencies**:
  - Task 3.1 completed

### Task 3.3: Remove 23 duplicate sample model fixtures

Remove all local sample_guild, sample_channel, sample_user fixtures that have been replaced with factories.

- **Files**:
  - All files identified in Task 3.2 (excluding service conftest files that keep their fixtures)
- **Success**:
  - All sample_* fixtures removed from non-conftest files
  - Tests still pass using factory functions
  - No fixture not found errors
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 160-200) - Complete list of sample data fixtures
- **Dependencies**:
  - Task 3.2 completed

## Phase 4: Specialized Fixture Consolidation (Lower Priority)

### Task 4.1: Consolidate auth fixtures (mock_current_user, mock_tokens)

Create shared auth fixtures for API authentication testing.

- **Files**:
  - tests/services/api/conftest.py - NEW FILE or add to existing
  - Remove from: test_guilds.py, test_templates.py, test_permissions.py, test_negative_authorization.py
- **Success**:
  - mock_current_user fixture in API conftest
  - mock_tokens fixture in API conftest
  - 4+ duplicate fixtures removed
  - All API route/dependency tests pass
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 220-245) - Auth fixture duplication (4+ instances)
- **Implementation**:
  - Create tests/services/api/conftest.py if doesn't exist
  - Add fixtures returning auth_schemas.CurrentUser and token dicts
- **Dependencies**:
  - Phase 3 completed

### Task 4.2: Consolidate middleware fixtures (mock_app, mock_request)

Create shared FastAPI middleware test fixtures.

- **Files**:
  - tests/services/api/middleware/conftest.py - NEW FILE to create
  - Remove from: test_error_handler.py, test_cors.py, test_authorization.py
- **Success**:
  - mock_app and mock_request fixtures in middleware conftest
  - 2+ duplicate fixtures removed per type
  - All middleware tests pass
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 247-260) - Middleware fixture analysis
- **Dependencies**:
  - Task 4.1 completed

### Task 4.3: Consolidate bot command fixtures

Create shared discord.py command test fixtures.

- **Files**:
  - tests/services/bot/commands/conftest.py - NEW FILE to create
  - Remove from: test_my_games.py, test_list_games.py, test_decorators.py
- **Success**:
  - mock_interaction, mock_guild, mock_channel fixtures in commands conftest
  - 3 duplicate mock_interaction fixtures removed
  - All bot command tests pass
- **Research References**:
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 262-280) - Bot command fixture duplication
- **Implementation**:
  - Create discord.py mock objects for Interaction, Guild, Channel
  - Follow discord.py API specifications
- **Dependencies**:
  - Task 4.2 completed

### Task 4.4: Final verification and cleanup

Run full test suite and verify consolidation goals achieved.

- **Files**:
  - All test files
- **Success**:
  - All unit tests pass (134 tests)
  - Fixture count reduced from 134 to ~40 (70% reduction)
  - No exact duplicate fixtures remain
  - No more than 3 local fixtures per test file (on average)
  - All conftest.py files have documentation
  - Changes file updated with complete list of modifications
- **Implementation**:
  - Run: `uv run pytest tests/ -v --ignore=tests/integration --ignore=tests/e2e`
  - Count fixtures: grep -r "@pytest.fixture" tests/services tests/shared | wc -l
  - Verify no duplicates: Look for fixtures with same name in multiple files
  - Update changes markdown with summary
- **Dependencies**:
  - All previous tasks completed

## Dependencies

- pytest fixture discovery system
- unittest.mock (AsyncMock, MagicMock)
- SQLAlchemy AsyncSession
- Discord.py library
- FastAPI for middleware fixtures
- All existing tests passing before consolidation

## Success Criteria

- Fixture count: 134 → ~40 (70% reduction achieved)
- Duplicate fixtures: 96 → 0 (100% elimination)
- Test pass rate: 100% maintained through all phases
- Code quality: All conftest.py files properly documented
- Maintainability: Adding new tests doesn't require fixture duplication
- Clear organization: Root → service → feature-specific fixture hierarchy
