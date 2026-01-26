<!-- markdownlint-disable-file -->

# Task Details: Unit Test Fixture Consolidation

## Research Reference

**Source Research**: #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md

## Phase 1: Game Service Cluster Consolidation

### Task 1.1: Create tests/services/api/services/conftest.py with 8 shared fixtures

Create new conftest.py file in the game services directory with fixtures shared across all game service tests.

- **Files**:
  - tests/services/api/services/conftest.py - NEW FILE with complete fixture definitions
- **Success**:
  - File created with all 8 fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel, sample_user)
  - All imports resolve correctly
  - Fixtures properly decorated with @pytest.fixture
  - Documentation follows self-explanatory code standards
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 279-366) - Complete conftest.py implementation
  - #file:../research/20260107-unit-test-fixture-duplication-research.md (Lines 350-450) - Original fixture patterns
- **Dependencies**:
  - None (foundational task)
- **Implementation**:
  ```python
  """Shared fixtures for API game service tests."""

  import uuid
  from unittest.mock import AsyncMock, MagicMock

  import pytest
  from sqlalchemy.ext.asyncio import AsyncSession

  from services.api.services import games as games_service
  from services.api.services import participant_resolver as resolver_module
  from shared.discord import client as discord_client_module
  from shared.messaging import publisher as messaging_publisher
  from shared.models import channel as channel_model
  from shared.models import guild as guild_model
  from shared.models import template as template_model
  from shared.models import user as user_model


  @pytest.fixture
  def mock_db():
      """Mock database session for service tests."""
      return AsyncMock(spec=AsyncSession)


  @pytest.fixture
  def mock_event_publisher():
      """Mock event publisher for game events."""
      publisher = AsyncMock(spec=messaging_publisher.EventPublisher)
      publisher.publish = AsyncMock()
      return publisher


  @pytest.fixture
  def mock_discord_client():
      """Mock Discord API client."""
      return MagicMock(spec=discord_client_module.DiscordAPIClient)


  @pytest.fixture
  def mock_participant_resolver():
      """Mock participant resolver."""
      return AsyncMock(spec=resolver_module.ParticipantResolver)


  @pytest.fixture
  def game_service(mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver):
      """Game service instance with mocked dependencies."""
      return games_service.GameService(
          db=mock_db,
          event_publisher=mock_event_publisher,
          discord_client=mock_discord_client,
          participant_resolver=mock_participant_resolver,
      )


  @pytest.fixture
  def sample_guild():
      """Sample guild configuration for tests."""
      return guild_model.GuildConfiguration(
          id=str(uuid.uuid4()),
          guild_id="123456789",
      )


  @pytest.fixture
  def sample_channel(sample_guild):
      """Sample channel configuration for tests."""
      return channel_model.ChannelConfiguration(
          id=str(uuid.uuid4()),
          channel_id="987654321",
          guild_id=sample_guild.id,
      )


  @pytest.fixture
  def sample_user():
      """Sample user for tests."""
      return user_model.User(
          id=str(uuid.uuid4()),
          discord_id="111222333",
      )
  ```

### Task 1.2: Remove duplicate fixtures from test_games.py

Remove fixtures that are now in conftest.py, keeping only test-specific fixtures.

- **Files**:
  - tests/services/api/services/test_games.py - Remove lines 53-140 (fixture definitions)
- **Success**:
  - Lines 53-140 removed (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, mock_role_service, game_service, sample_guild, sample_channel, sample_template, sample_user)
  - Keep sample_game_data fixture (test-specific)
  - All tests still pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 171-186) - test_games.py fixture list
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Remove duplicate fixtures from test_games_promotion.py

Remove fixtures that are now in conftest.py.

- **Files**:
  - tests/services/api/services/test_games_promotion.py - Remove lines 39-102
- **Success**:
  - Lines 39-102 removed (all fixtures now in conftest.py)
  - Keep sample_host and sample_game (test-specific variants)
  - All tests still pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 188-198) - test_games_promotion.py fixture list
- **Dependencies**:
  - Task 1.1 completion

### Task 1.4: Remove duplicate fixtures from test_games_edit_participants.py

Remove fixtures that are now in conftest.py.

- **Files**:
  - tests/services/api/services/test_games_edit_participants.py - Remove lines 41-97
- **Success**:
  - Lines 41-97 removed (all common fixtures)
  - Keep sample_game if test-specific, otherwise remove
  - All tests still pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 200-208) - test_games_edit_participants.py fixture list
- **Dependencies**:
  - Task 1.1 completion

### Task 1.5: Remove duplicate fixtures from test_games_image_upload.py

Remove fixtures that are now in conftest.py.

- **Files**:
  - tests/services/api/services/test_games_image_upload.py - Remove lines 40-117
- **Success**:
  - Lines 40-117 removed (all common fixtures including mock_role_service)
  - Keep sample_template and sample_game if test-specific
  - All tests still pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 210-222) - test_games_image_upload.py fixture list
- **Dependencies**:
  - Task 1.1 completion

### Task 1.6: Remove duplicate fixtures from test_update_game_fields_helpers.py

Remove fixtures that are now in conftest.py.

- **Files**:
  - tests/services/api/services/test_update_game_fields_helpers.py - Remove lines 38-72
- **Success**:
  - Lines 38-72 removed (all fixtures)
  - No test-specific fixtures needed
  - All tests still pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 224-229) - test_update_game_fields_helpers.py fixture list
- **Dependencies**:
  - Task 1.1 completion

### Task 1.7: Run game service tests to verify consolidation

Verify all game service tests pass after fixture consolidation.

- **Files**:
  - N/A (verification task)
- **Success**:
  - Command `docker compose run unit-tests tests/services/api/services/` completes successfully
  - All tests pass (no failures or errors)
  - Fixture discovery works correctly
  - No warnings about missing fixtures
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 377-378) - Test command
- **Dependencies**:
  - Tasks 1.1-1.6 completion

## Phase 2: Root-Level Mock Consolidation

### Task 2.1: Add unit test mock fixtures to tests/conftest.py

Add four unit test mock fixtures to root conftest.py for cross-service usage.

- **Files**:
  - tests/conftest.py - Add fixtures at end of file (after line 840)
- **Success**:
  - Four fixtures added: mock_db_unit, mock_discord_api_client, mock_current_user_unit, mock_role_service
  - Clear section header comment added
  - Documentation explains difference from integration fixtures
  - No conflicts with existing fixtures
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 392-467) - Complete fixture implementations
  - #file:../research/20260104-consolidate-test-fixtures-research.md - Integration fixture patterns
- **Dependencies**:
  - Phase 1 completion (validates approach)
- **Implementation**:
  ```python
  # ============================================================================
  # Unit Test Mock Fixtures
  # ============================================================================

  @pytest.fixture
  def mock_db_unit():
      """
      Mock AsyncSession database for unit tests.

      Differs from admin_db_sync/admin_db which are real database connections
      for integration tests. This is a pure mock for isolated unit tests.

      Returns AsyncMock with AsyncSession spec.
      """
      from unittest.mock import AsyncMock
      from sqlalchemy.ext.asyncio import AsyncSession

      return AsyncMock(spec=AsyncSession)


  @pytest.fixture
  def mock_discord_api_client():
      """
      Mock Discord REST API client (shared.discord.client.DiscordAPIClient).

      For bot commands/events using discord.py Bot, use a different mock.
      This mocks the HTTP REST API client used by services.
      """
      from unittest.mock import MagicMock
      from shared.discord import client as discord_client_module

      return MagicMock(spec=discord_client_module.DiscordAPIClient)


  @pytest.fixture
  def mock_current_user_unit():
      """
      Mock authenticated user for unit tests.

      Returns CurrentUser schema with mock user object for testing
      authenticated endpoints without real auth flow.
      """
      from unittest.mock import MagicMock
      from shared.schemas import auth as auth_schemas

      mock_user = MagicMock()
      mock_user.discord_id = "123456789"
      return auth_schemas.CurrentUser(
          user=mock_user,
          access_token="test_access_token",
          session_token="test-session-token",
      )


  @pytest.fixture
  def mock_role_service():
      """
      Mock role checking service for unit tests.

      Default behavior: All permission checks return True.
      Override in specific tests as needed.
      """
      from unittest.mock import AsyncMock

      role_service = AsyncMock()
      role_service.check_game_host_permission = AsyncMock(return_value=True)
      role_service.check_bot_manager_permission = AsyncMock(return_value=True)
      return role_service
  ```

### Task 2.2: Update routes tests to use shared mock_current_user fixture

Remove mock_current_user from route test files, use mock_current_user_unit from conftest.py.

- **Files**:
  - tests/services/api/routes/test_guilds.py - Remove mock_current_user fixture
  - tests/services/api/routes/test_templates.py - Remove mock_current_user fixture
- **Success**:
  - mock_current_user fixtures removed from both files
  - Tests updated to use mock_current_user_unit
  - All route tests pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 258-268) - mock_current_user duplication
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update dependencies tests to use shared mock_role_service fixture

Remove mock_role_service from dependency test files, use shared version from conftest.py.

- **Files**:
  - tests/services/api/dependencies/test_permissions_migration.py - Remove mock_role_service
  - tests/services/api/dependencies/test_permissions.py - Remove mock_role_service
- **Success**:
  - mock_role_service fixtures removed from both files
  - Tests use shared mock_role_service
  - All dependency tests pass
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 243-245) - mock_role_service duplication
- **Dependencies**:
  - Task 2.1 completion

### Task 2.4: Run full unit test suite to verify consolidation

Verify all unit tests pass after root-level consolidation.

- **Files**:
  - N/A (verification task)
- **Success**:
  - Command `docker compose run unit-tests tests/services/` completes successfully
  - All tests pass (no failures or errors)
  - Fixture discovery works correctly across all directories
  - No fixture name conflicts
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 479-480) - Test command
- **Dependencies**:
  - Tasks 2.1-2.3 completion

## Phase 3: Verification and Cleanup

### Task 3.1: Verify fixture discovery with pytest --collect-only

Ensure pytest can discover all fixtures and tests correctly.

- **Files**:
  - N/A (verification task)
- **Success**:
  - Command `docker compose run unit-tests pytest --collect-only tests/services/` succeeds
  - All tests collected successfully
  - No warnings about fixture discovery
  - Fixture scope is correct (function scope for mocks)
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 534-537) - Fixture discovery verification
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Run coverage report to verify no test regressions

Ensure coverage remains at or above current levels after consolidation.

- **Files**:
  - N/A (verification task)
- **Success**:
  - Command `scripts/coverage-report.sh` completes successfully
  - Coverage percentage unchanged or improved
  - No new uncovered lines introduced
  - All test modules still included in coverage
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 510-513) - Quality metrics
- **Dependencies**:
  - Phase 2 completion

### Task 3.3: Document fixture locations and usage patterns

Add documentation for where fixtures are located and when to use each.

- **Files**:
  - tests/services/api/services/conftest.py - Update module docstring with usage guidance
  - tests/conftest.py - Update unit test fixtures section with usage examples
- **Success**:
  - Clear guidance on which fixtures to use for unit vs integration tests
  - Examples of when to create local fixtures vs use shared ones
  - Directory structure documented (where to find fixtures)
  - Naming conventions documented (_unit suffix for unit test versions)
- **Research References**:
  - #file:../research/20260126-unit-test-fixture-consolidation-current-state-research.md (Lines 324-333) - Gap analysis showing unit vs integration fixtures
  - #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Documentation standards
- **Dependencies**:
  - Phase 2 completion

## Dependencies

- Python 3.13+ with pytest
- Docker compose for test execution
- Current test suite baseline (all passing)

## Success Criteria

- 58 fixtures consolidated (35 in Phase 1, 23 in Phase 2)
- All 91 unit test files pass
- Fixture discovery works correctly
- Coverage unchanged or improved
- Clear documentation for fixture usage
