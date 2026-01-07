<!-- markdownlint-disable-file -->
# Task Research Notes: Unit Test Fixture Duplication Analysis

## Research Executed

### Automated Analysis Scripts
- Scanned all unit test files in `tests/services/**/*.py` and `tests/shared/**/*.py`
- Excluded integration and E2E tests (already addressed in previous consolidation)
- Analyzed 134 fixture definitions across ~50 unit test files

### Semantic Categorization
- Read fixture implementations to understand functionality
- Categorized by purpose: mocks, sample data models, service instances
- Identified both exact name matches AND functional duplicates with different names

### Code Pattern Analysis
- Examined fixture bodies in multiple files:
  - `tests/services/api/services/test_games.py`
  - `tests/services/api/services/test_games_promotion.py`
  - `tests/services/api/services/test_games_edit_participants.py`
  - `tests/services/api/services/test_games_image_upload.py`
  - `tests/services/bot/auth/test_role_checker.py`
  - `tests/services/api/routes/test_guilds.py`
  - `tests/services/api/dependencies/test_permissions.py`
  - `tests/shared/data_access/test_guild_queries.py`

## Key Discoveries

### High-Impact Duplication: Mock Database Sessions

**12 exact duplicates of `mock_db` fixture:**

```python
@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)
```

**Found in:**
- services/bot/auth/test_role_checker.py
- services/api/routes/test_templates.py
- services/api/routes/test_guilds.py
- services/api/dependencies/test_permissions_migration.py
- services/api/services/test_games_image_upload.py
- services/api/services/test_games_edit_participants.py
- services/api/services/test_games.py
- services/api/services/test_games_promotion.py
- services/api/services/test_calendar_export.py
- services/api/services/test_template_service.py
- services/api/services/test_participant_resolver.py
- shared/data_access/test_guild_queries.py

**Variants with different names but same purpose:**
- `mock_game` (2 occurrences) - Actually mocks database session, not a game
- `game_session` (1 occurrence) - Returns mock AsyncSession

**Total: 15 functionally identical database session mocks**

### High-Impact Duplication: Game Service Test Fixtures

**"Game service test cluster" - 4 files with nearly identical fixture sets:**

tests/services/api/services/:
- test_games.py (11 fixtures)
- test_games_promotion.py (9 fixtures)
- test_games_edit_participants.py (7 fixtures)
- test_games_image_upload.py (10 fixtures)

**Duplicated across all 4 files:**
- `mock_db` - AsyncMock database session
- `mock_event_publisher` - EventPublisher mock
- `mock_discord_client` - Discord API client mock
- `mock_participant_resolver` - ParticipantResolver mock
- `game_service` - GameService instance with injected mocks
- `sample_guild` - GuildConfiguration model
- `sample_channel` - ChannelConfiguration model

**Duplicated across 3 files:**
- `sample_user` - User model (in test_games, test_games_edit_participants, test_games_image_upload)
- `sample_template` - GameTemplate model (in test_games, test_games_image_upload, + test_template_service)

**Analysis:** These 4 test files test different aspects of the GameService but duplicate the entire fixture setup.

### Moderate Duplication: Mock Discord Clients

**Two different types of Discord client mocks:**

**Type 1: Discord API Client (shared.discord.client.DiscordAPIClient)**
- `mock_discord_client` - 7 occurrences in API service tests
- Used for REST API calls to Discord

**Type 2: Discord.py Bot Client (discord.Client)**
- `mock_bot` - 2 occurrences in bot service tests
- Used for gateway events and bot commands

**Issue:** These are mocking different classes but serving similar purpose (Discord interaction isolation)

### Mock Event Publishers

**4 exact duplicates of `mock_event_publisher`:**
- All in services/api/services/ test files (games, games_promotion, games_edit_participants, games_image_upload)
- Identical implementation: `AsyncMock(spec=messaging_publisher.EventPublisher)`

**4 duplicates of `game_service` fixture:**
- All inject the same 4 dependencies: db, event_publisher, discord_client, participant_resolver
- Identical construction pattern

**Related daemon publishers:**
- `daemon` - 2 occurrences (retry_daemon, scheduler_daemon)
- Different purpose but similar pattern

### Sample Data Model Duplication

**Sample Guild - 4 exact duplicates + 3 variants:**
```python
@pytest.fixture
def sample_guild():
    return guild_model.GuildConfiguration(
        id=str(uuid.uuid4()),
        guild_id="123456789",  # Hardcoded across all
    )
```
- All use same hardcoded guild_id "123456789"
- Could be consolidated with optional parameter

**Sample Channel - 4 exact duplicates:**
```python
@pytest.fixture
def sample_channel(sample_guild):
    return channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="987654321",  # Hardcoded across all
        guild_id=sample_guild.id,
    )
```

**Sample User - 4 exact duplicates + 3 variants:**
- `sample_user` - 4 occurrences with discord_id "111222333"
- `mock_user` - 3 occurrences (different discord_ids)
- `sample_host` - 1 occurrence
- `mock_current_user` - 4 occurrences (auth wrapper around user)

**Sample Game - 4 exact duplicates + variants:**
- `sample_game` - 4 occurrences (GameSession models)
- `sample_games` - 2 occurrences (lists of games)

**Sample Template - 4 exact duplicates:**
- All in API service tests
- Identical structure with same default values

### Mock Role Services

**4 exact duplicates of `mock_role_service`:**
```python
@pytest.fixture
def mock_role_service():
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    return role_service
```

**Found in:**
- services/api/dependencies/test_permissions_migration.py
- services/api/dependencies/test_permissions.py
- services/api/services/test_games_image_upload.py
- services/api/services/test_games.py

### Mock Participant Resolvers

**4 exact duplicates:**
- All return `AsyncMock(spec=resolver_module.ParticipantResolver)`
- All in game service tests

### Other Significant Duplications

**Mock Current User (auth) - 4 duplicates:**
```python
@pytest.fixture
def mock_current_user():
    mock_user = MagicMock()
    mock_user.discord_id = "123456789"
    return auth_schemas.CurrentUser(
        user=mock_user,
        access_token="test_access_token",
        session_token="test-session-token",
    )
```

**Mock Discord Interactions - 3 duplicates:**
- All in bot command tests
- Mock discord.py Interaction objects for slash commands

**Mock FastAPI Objects:**
- `mock_app` - 2 duplicates (middleware tests)
- `mock_request` - 2 duplicates (middleware tests)

## Duplication Summary Table

| Category | Exact Name Duplicates | Similar Variants | Total Fixtures | Consolidation Impact |
|----------|----------------------|------------------|----------------|---------------------|
| Mock Database Session | 12 (`mock_db`) | 3 variants | 15 | **CRITICAL** |
| Game Service Cluster | 28 (7 fixtures × 4 files) | 0 | 28 | **CRITICAL** |
| Mock Discord Clients | 7 (API) + 2 (Bot) | 0 | 9 | **HIGH** |
| Sample Guild Model | 4 | 3 variants | 7 | **HIGH** |
| Sample User/Host Model | 4 (`sample_user`) | 7 variants | 11 | **HIGH** |
| Mock Event Publisher | 4 | 0 | 4 | **MEDIUM** |
| Sample Channel Model | 4 | 1 variant | 5 | **MEDIUM** |
| Sample Template Model | 4 | 1 variant | 5 | **MEDIUM** |
| Sample Game Model | 4 (`sample_game`) | 2 variants | 6 | **MEDIUM** |
| Mock Role Service | 4 | 1 variant | 5 | **MEDIUM** |
| Mock Participant Resolver | 4 | 1 variant | 5 | **MEDIUM** |
| Mock Current User (Auth) | 4 | 0 | 4 | **MEDIUM** |
| Mock Discord Interaction | 3 | 0 | 3 | **LOW** |
| Mock Discord Guild Object | 3 | 0 | 3 | **LOW** |
| Mock Discord Channel Object | 3 | 0 | 3 | **LOW** |
| Mock Redis/Cache | 2 | 3 variants | 5 | **LOW** |
| Mock FastAPI Request | 2 | 0 | 2 | **LOW** |
| Mock FastAPI App | 2 | 0 | 2 | **LOW** |

**Total fixtures analyzed:** 134
**Fixtures with exact name duplication:** 74 (55%)
**Functionally duplicate fixtures (different names):** 22 (16%)
**Combined duplication:** 96 fixtures (72% of all unit test fixtures)

## Root Cause Analysis

### Why So Much Duplication?

1. **Test Organization Pattern:**
   - Tests grouped by feature (games, games_promotion, games_edit_participants, games_image_upload)
   - Each test file is self-contained with all needed fixtures
   - No shared test fixture modules for unit tests (unlike integration/e2e)

2. **Copy-Paste Development:**
   - New test files created by copying existing ones
   - Fixtures copied wholesale even if only subset needed
   - No refactoring back to shared location

3. **Lack of Unit Test conftest.py:**
   - Root `tests/conftest.py` has factories but for integration-style fixtures
   - No `tests/services/conftest.py` for service-level shared fixtures
   - No `tests/shared/conftest.py` for shared module tests

4. **Inconsistent Mock Patterns:**
   - Some tests use `MagicMock`, others `AsyncMock`
   - Different spec declarations for same objects
   - No established mocking conventions

## Recommended Approach

### Strategy: Layered Consolidation

Based on pytest fixture discovery order and test organization:

**Phase 1: Service-Level Consolidation (Highest Impact)**
- Create `tests/services/api/services/conftest.py`
- Consolidate the "game service cluster" fixtures (28 duplicate fixtures → 7 shared)
- Create `tests/services/bot/conftest.py` for bot-specific fixtures

**Phase 2: Mock Object Consolidation (High Impact)**
- Create shared mock factories in `tests/conftest.py` or service-level conftest
- Consolidate database session mocks (15 → 1)
- Consolidate Discord client mocks (9 → 2, keeping API vs Bot distinction)
- Consolidate event publisher mocks (4 → 1)

**Phase 3: Sample Data Consolidation (Medium Impact)**
- Extend existing factories in `tests/conftest.py` to support unit test patterns
- Current factories use admin_db_sync (for integration tests)
- Create lightweight factory variants that return model objects without DB

**Phase 4: Specialized Fixture Consolidation (Lower Priority)**
- Auth fixtures (mock_current_user, mock_tokens)
- Middleware fixtures (mock_app, mock_request)
- Bot command fixtures (mock_interaction, mock_guild, mock_channel)

### Implementation Guidelines

**Use Existing Patterns from Integration Test Consolidation:**
- Scope fixtures appropriately (function vs module)
- Document fixture purpose and usage
- Use factory pattern for configurable fixtures
- Keep fixture dependencies explicit

**Maintain Test Independence:**
- Fixtures should return fresh mocks for each test
- Avoid shared state between tests
- Use function scope by default, module scope only when safe

**Parameterization Over Variants:**
- Instead of `sample_user` and `mock_user` and `sample_host`
- Create `create_user(discord_id=None)` factory fixture
- Tests can customize as needed

## Consolidation Priority Ranking

### Critical Priority (Complete removal of duplication)

1. **Mock Database Session** (15 fixtures → 1)
   - Impact: Affects 12+ test files
   - Effort: Low (trivial fixture)
   - Location: `tests/conftest.py` or `tests/services/conftest.py`

2. **Game Service Test Cluster** (28 fixtures → 7)
   - Impact: Consolidates 4 test files
   - Effort: Medium (create services/api/services/conftest.py)
   - Benefits: Reduces 21 fixtures, simplifies maintenance

### High Priority (Major duplication removal)

3. **Mock Discord Clients** (9 fixtures → 2)
   - Keep distinction between DiscordAPIClient and discord.py bot
   - Create clear naming convention

4. **Sample Guild/Channel/User Models** (23 fixtures → 3-4)
   - Factory pattern with sensible defaults
   - Allow customization via parameters

### Medium Priority (Moderate duplication)

5. **Mock Services** (Mock Event Publisher, Role Service, Participant Resolver)
   - 13 fixtures → 3-4
   - Service-specific conftest files

6. **Sample Game/Template Data** (11 fixtures → 2-3)
   - Extend existing factory fixtures
   - Add lightweight model-only variants

### Low Priority (Minor duplications)

7. **Auth Fixtures** (mock_current_user, mock_tokens)
8. **Middleware Fixtures** (mock_app, mock_request)
9. **Bot Command Fixtures** (mock_interaction, mock_guild)
10. **Redis/Cache Mocks**

## Implementation Guidance

### Phase 1: Game Service Cluster Consolidation

**Create `tests/services/api/services/conftest.py`:**

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


@pytest.fixture
def sample_template(sample_guild, sample_channel):
    """Sample game template for tests."""
    return template_model.GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        name="Test Template",
        order=0,
        is_default=True,
        max_players=10,
        reminder_minutes=[60, 15],
    )
```

**Then remove fixtures from:**
- tests/services/api/services/test_games.py
- tests/services/api/services/test_games_promotion.py
- tests/services/api/services/test_games_edit_participants.py
- tests/services/api/services/test_games_image_upload.py

**Impact:** Removes 21 duplicate fixtures immediately

### Phase 2: Root-Level Mock Consolidation

**Extend `tests/conftest.py` with common mocks:**

```python
# Add to existing tests/conftest.py

@pytest.fixture
def mock_db():
    """Mock AsyncSession database for unit tests.

    For integration tests with real database, use admin_db_sync or app_db.
    """
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_discord_api_client():
    """Mock Discord REST API client (shared.discord.client.DiscordAPIClient).

    For bot commands/events using discord.py, use mock_discord_bot instead.
    """
    return MagicMock(spec=discord_client_module.DiscordAPIClient)


@pytest.fixture
def create_sample_user():
    """Factory to create sample User models with custom discord_id.

    Returns function that creates User with optional discord_id parameter.
    """
    def _create(discord_id: str | None = None):
        return user_model.User(
            id=str(uuid.uuid4()),
            discord_id=discord_id or str(uuid.uuid4())[:18],
        )
    return _create
```

**Impact:** Removes 15+ database mock duplicates, 7+ Discord client duplicates

### Success Criteria

**Metrics:**
- Reduce unique fixture definitions by 60-70% (96 → ~30)
- Each fixture appears in only ONE location (no exact duplicates)
- Test files have <3 local fixtures on average (down from 7+)

**Quality:**
- All tests pass after consolidation
- No shared mutable state between tests
- Clear fixture documentation and purpose
- Consistent naming conventions

**Maintainability:**
- Adding new service tests doesn't require duplicating fixtures
- Fixture changes propagate automatically to all users
- Clear layering: root → service → feature-specific

## Alternative Approach: Fixture Plugins

**Not Recommended for This Project:**
- pytest-fixtures plugin would add dependency
- Current patterns (conftest hierarchy) are standard pytest
- Team already familiar with conftest pattern from integration tests
- Consolidation via conftest.py is more straightforward

## Migration Risk Assessment

**Low Risk:**
- Mock fixtures (mock_db, mock_event_publisher, etc.)
- These are isolated, no complex dependencies
- Can be moved with simple search/replace

**Medium Risk:**
- Sample data fixtures with dependencies (sample_channel depends on sample_guild)
- Need to ensure pytest discovers fixtures in correct order
- May need to adjust import statements

**High Risk:**
- None identified - all fixtures are test-scoped without complex interactions

**Mitigation:**
- Run full test suite after each consolidation phase
- Use git branches for each phase
- Keep commits focused (one fixture type per commit)
- If test fails, easy to revert single commit

## Implementation Tasks

### Phase 1 Tasks
- [ ] Create `tests/services/api/services/conftest.py`
- [ ] Move 7 fixtures from test_games.py to conftest.py
- [ ] Remove fixtures from test_games.py, test_games_promotion.py, test_games_edit_participants.py, test_games_image_upload.py
- [ ] Run game service tests to verify
- [ ] Create `tests/services/bot/conftest.py` for bot fixtures

### Phase 2 Tasks
- [ ] Add mock_db to tests/conftest.py
- [ ] Remove all mock_db fixtures from unit tests
- [ ] Add mock_discord_api_client to tests/conftest.py
- [ ] Add mock_event_publisher to tests/conftest.py
- [ ] Run full unit test suite

### Phase 3 Tasks
- [ ] Add create_sample_user factory to tests/conftest.py
- [ ] Add create_sample_guild factory to tests/conftest.py
- [ ] Add create_sample_channel factory to tests/conftest.py
- [ ] Migrate tests to use factories instead of local fixtures

### Phase 4 Tasks
- [ ] Consolidate auth fixtures (mock_current_user, mock_tokens)
- [ ] Consolidate middleware fixtures
- [ ] Consolidate bot command fixtures
- [ ] Final cleanup pass

## References

**Similar Patterns in Project:**
- `tests/conftest.py` - Root fixtures with factories (lines 215-796)
- `tests/integration/conftest.py` - Integration test fixtures
- `tests/e2e/conftest.py` - E2E test fixtures

**Recent Work:**
- Task: 20260104-consolidate-test-fixtures-plan.instructions.md
- Successfully consolidated integration/e2e fixtures
- Same patterns can apply to unit tests
