<!-- markdownlint-disable-file -->
# Task Research Notes: Unit Test Fixture Consolidation - Current State Analysis (January 2026)

## Executive Summary

**Current State**: Unit test fixtures remain heavily duplicated across 91 test files with 157 total fixtures. Since the January 2026 research, lint fixes and other changes have updated line numbers and some patterns, but the core duplication problem persists.

**Key Findings**:
- **157 total fixtures** in unit tests (23 MORE than original 134 count - tests have grown)
- **14 `mock_db` duplicates** (up from 12 in original research)
- **5-file "game service cluster"** with identical fixture sets (was 4 files, now includes `test_update_game_fields_helpers.py`)
- **59 duplicate fixtures** identified across critical categories (38% of all fixtures)
- **No conftest.py files** exist in `tests/services/` subdirectories yet

**What Changed Since Original Research**:
- Test suite grew from ~50 files to 91 files
- `test_update_game_fields_helpers.py` added to game service cluster
- Fixture count increased 23 (+17%)
- Line numbers shifted throughout codebase from lint/refactoring work
- `tests/conftest.py` now has comprehensive factory fixtures for integration tests

**What Remains the Same**:
- Core duplication patterns unchanged
- Game service cluster still has identical fixtures
- No service-level conftest files created yet
- Same consolidation approach still valid

## Research Executed

### Current Codebase Scan (January 26, 2026)
```bash
# Comprehensive fixture analysis
Total Test Files: 91 (was ~50)
Total Fixtures: 157 (was 134)
Unit Test Directories: tests/services/, tests/shared/
```

### Automated Fixture Counting
```bash
mock_db: 14 occurrences (was 12)
mock_event_publisher: 5 occurrences (was 4)
mock_discord_client: 10 occurrences (was 7+2=9)
mock_participant_resolver: 5 occurrences (was 4)
game_service: 5 occurrences (was 4)

sample_guild: 4 occurrences (unchanged)
sample_channel: 4 occurrences (unchanged)
sample_template: 3 occurrences (was 4)
mock_current_user: 5 occurrences (was 4)
mock_role_service: 4 occurrences (unchanged)
```

### File Verification
Verified actual fixture implementations in:
- tests/services/api/services/test_games.py (11 fixtures)
- tests/services/api/services/test_games_promotion.py (9 fixtures)
- tests/services/api/services/test_games_edit_participants.py (8 fixtures)
- tests/services/api/services/test_games_image_upload.py (10 fixtures)
- tests/services/api/services/test_update_game_fields_helpers.py (5 fixtures) **NEW**
- tests/services/api/routes/test_guilds.py (mock_db, mock_current_user)
- tests/services/api/routes/test_templates.py (mock_db, mock_current_user)
- tests/services/api/services/test_calendar_export.py (mock_db, sample data)

### Fixture Discovery Status
```bash
find tests/services/**/conftest.py: 0 results
# No service-level conftest files exist yet - opportunity for immediate impact
```

## Current State: Duplication Analysis

### CRITICAL PRIORITY: Mock Database Sessions (14 duplicates)

**Files with `mock_db` fixture:**
1. tests/services/api/routes/test_templates.py
2. tests/services/api/routes/test_guilds.py
3. tests/services/api/routes/test_channels.py
4. tests/services/api/dependencies/test_permissions_migration.py
5. tests/services/api/services/test_update_game_fields_helpers.py
6. tests/services/api/services/test_games_image_upload.py
7. tests/services/api/services/test_games_edit_participants.py
8. tests/services/api/services/test_games.py
9. tests/services/api/services/test_calendar_export.py
10. tests/services/api/services/test_template_service.py
11. tests/services/api/services/test_participant_resolver.py
12. tests/services/api/services/test_games_promotion.py
13. tests/services/bot/auth/test_role_checker.py
14. tests/shared/data_access/test_guild_queries.py

**Implementation** (identical across all files):
```python
@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)
```

**Consolidation Strategy**: Move to `tests/conftest.py` as shared mock fixture.

**Impact**: 14 files → 1 shared fixture (93% reduction)

### CRITICAL PRIORITY: Game Service Cluster (5 files, 43 total fixtures)

**Files in cluster:**
1. tests/services/api/services/test_games.py (11 fixtures)
2. tests/services/api/services/test_games_promotion.py (9 fixtures)
3. tests/services/api/services/test_games_edit_participants.py (8 fixtures)
4. tests/services/api/services/test_games_image_upload.py (10 fixtures)
5. tests/services/api/services/test_update_game_fields_helpers.py (5 fixtures) **NEW**

**Shared fixtures across ALL 5 files:**
- `mock_db` - AsyncMock database session
- `mock_event_publisher` - EventPublisher mock
- `mock_discord_client` - Discord API client mock
- `mock_participant_resolver` - ParticipantResolver mock
- `game_service` - GameService instance with injected mocks

**Shared fixtures across 4 files** (all except test_update_game_fields_helpers.py):
- `sample_guild` - GuildConfiguration model
- `sample_channel` - ChannelConfiguration model
- `sample_template` - GameTemplate model (in 3 files)
- `sample_user` - User model (in 3 files)

**Current fixture implementations verified** (line numbers as of Jan 26, 2026):

tests/services/api/services/test_games.py (lines 53-140):
- mock_db (line 54)
- mock_event_publisher (line 60)
- mock_discord_client (line 68)
- mock_participant_resolver (line 74)
- mock_role_service (line 80)
- game_service (line 88)
- sample_guild (line 99)
- sample_channel (line 108)
- sample_template (line 118)
- sample_user (line 135)
- sample_game_data (line 141)

tests/services/api/services/test_games_promotion.py (lines 39-102):
- mock_db (line 40)
- mock_event_publisher (line 46)
- mock_discord_client (line 54)
- mock_participant_resolver (line 60)
- game_service (line 66)
- sample_guild (line 77)
- sample_channel (line 86)
- sample_host (line 97)
- sample_game (line 103)

tests/services/api/services/test_games_edit_participants.py (lines 41-97):
- mock_db (line 42)
- mock_event_publisher (line 48)
- mock_discord_client (line 56)
- mock_participant_resolver (line 62)
- game_service (line 68)
- sample_guild (line 79)
- sample_channel (line 88)
- sample_game (line 98)

tests/services/api/services/test_games_image_upload.py (lines 40-117):
- mock_db (line 41)
- mock_event_publisher (line 47)
- mock_discord_client (line 55)
- mock_participant_resolver (line 61)
- mock_role_service (line 67)
- game_service (line 75)
- sample_guild (line 86)
- sample_channel (line 95)
- sample_template (line 105)
- sample_game (line 118)

tests/services/api/services/test_update_game_fields_helpers.py (lines 38-72):
- mock_db (line 39)
- mock_event_publisher (line 45)
- mock_discord_client (line 53)
- mock_participant_resolver (line 59)
- game_service (line 66)

**Consolidation Strategy**: Create `tests/services/api/services/conftest.py` with 8 shared fixtures.

**Impact**: 43 fixtures → 8 shared fixtures (81% reduction in this cluster)

### HIGH PRIORITY: Mock Services (14 duplicates)

**mock_discord_client: 10 occurrences**
Files: test_games.py, test_games_promotion.py, test_games_edit_participants.py, test_games_image_upload.py, test_update_game_fields_helpers.py, test_participant_resolver.py, test_avatar_resolver.py, test_roles.py, test_games_participant_count.py, test_bot.py

**mock_participant_resolver: 5 occurrences**
Files: test_games.py, test_games_promotion.py, test_games_edit_participants.py, test_games_image_upload.py, test_update_game_fields_helpers.py

**mock_role_service: 4 occurrences**
Files: test_games.py, test_games_image_upload.py, test_permissions_migration.py, test_permissions.py

**Consolidation Strategy**:
- `mock_discord_client` → `tests/conftest.py` (used across services)
- `mock_participant_resolver` → `tests/services/api/services/conftest.py` (service-specific)
- `mock_role_service` → `tests/conftest.py` (used in dependencies + services)

### MEDIUM PRIORITY: Sample Data Models (15 duplicates)

**sample_guild: 4 occurrences**
All in game service cluster - consolidate to services/api/services/conftest.py

**sample_channel: 4 occurrences**
All in game service cluster - consolidate to services/api/services/conftest.py

**sample_template: 3 occurrences**
In test_games.py, test_games_image_upload.py, test_template_service.py

**mock_current_user: 5 occurrences**
Files: test_guilds.py, test_templates.py, test_permissions_migration.py, test_permissions.py, test_games_image_upload.py

**Consolidation Strategy**:
- sample_guild/channel → services/api/services/conftest.py
- sample_template → services/api/services/conftest.py
- mock_current_user → tests/conftest.py (used in routes + services)

## What Already Exists in tests/conftest.py

**Current fixtures in tests/conftest.py** (verified Jan 26, 2026):
- Database fixtures: `admin_db_sync`, `admin_db`, `app_db`, `bot_db`
- Database URL fixtures: `admin_db_url_sync`, `admin_db_url`, `app_db_url`, `bot_db_url`
- Redis fixtures: `redis_client`, `redis_client_async`, `seed_redis_cache`
- Factory fixtures: `create_guild`, `create_channel`, `create_user`, `create_template`, `create_game`
- Composite fixtures: `test_environment`, `test_game_environment`
- HTTP client fixtures: `create_authenticated_client`
- Test configuration: `test_timeouts`

**These fixtures are FOR INTEGRATION TESTS** - they use real database sessions and create actual data. Unit tests need MOCK versions.

**Gap Analysis**:
- ❌ No `mock_db` (unit test version of AsyncSession)
- ❌ No `mock_discord_client` (mock DiscordAPIClient)
- ❌ No `mock_event_publisher` (mock EventPublisher)
- ❌ No `mock_role_service` (mock role checking)
- ❌ No `mock_current_user` (mock auth user)
- ✅ Has factory fixtures for real data (integration tests)

## Recommended Implementation Plan

### Phase 1: Service-Level Consolidation (Immediate Impact - 81% reduction in cluster)

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
```

**Then remove fixtures from:**
1. tests/services/api/services/test_games.py (remove lines 53-140)
2. tests/services/api/services/test_games_promotion.py (remove lines 39-102)
3. tests/services/api/services/test_games_edit_participants.py (remove lines 41-97)
4. tests/services/api/services/test_games_image_upload.py (remove lines 40-117)
5. tests/services/api/services/test_update_game_fields_helpers.py (remove lines 38-72)

**Impact**: 43 fixtures → 8 shared (35 removed, 81% reduction)

**Test Command**: `docker compose run unit-tests tests/services/api/services/`

### Phase 2: Root-Level Mock Consolidation (Affects 14+ files)

**Add to `tests/conftest.py`** (after existing fixtures):

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
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_discord_api_client():
    """
    Mock Discord REST API client (shared.discord.client.DiscordAPIClient).

    For bot commands/events using discord.py Bot, use a different mock.
    This mocks the HTTP REST API client used by services.
    """
    return MagicMock(spec=discord_client_module.DiscordAPIClient)


@pytest.fixture
def mock_current_user_unit():
    """
    Mock authenticated user for unit tests.

    Returns CurrentUser schema with mock user object for testing
    authenticated endpoints without real auth flow.
    """
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
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    role_service.check_bot_manager_permission = AsyncMock(return_value=True)
    return role_service
```

**Then remove from:**
- All 14 files with `mock_db` → use `mock_db_unit` (or configure `mock_db` to use local vs root)
- All 5 files with `mock_current_user` → use `mock_current_user_unit`
- All 4 files with `mock_role_service` → use shared version

**Note on Naming**: `mock_db_unit` and `mock_current_user_unit` avoid conflicts with future integration test fixtures.

**Impact**: 23 additional fixtures removed (14 mock_db + 5 mock_current_user + 4 mock_role_service)

**Test Command**: `docker compose run unit-tests tests/services/`

### Phase 3: Specialized Fixtures (Routes, Dependencies)

**Create `tests/services/api/routes/conftest.py`** for route-specific fixtures:
- `mock_guild_config`, `mock_channel_config`, `mock_template` (used in test_guilds, test_templates, test_channels)

**Create `tests/services/api/dependencies/conftest.py`** for dependency test fixtures:
- Permission checking mocks specific to dependency tests

**Impact**: Additional 10-15 fixtures consolidated

### Phase 4: Bot Service Fixtures

**Create `tests/services/bot/conftest.py`** for bot-specific fixtures:
- Mock discord.py bot objects
- Mock discord.py interactions
- Mock discord.py guild/channel/user objects

**Impact**: 5-10 bot fixtures consolidated

## Success Metrics

**Target Reduction**:
- Current: 157 fixtures across 91 files (avg 1.7 fixtures/file)
- Target: ~40 shared fixtures, ~50 test-specific (avg 0.5 fixtures/file)
- Reduction: 67 fixtures eliminated (43% reduction)

**Phase Breakdown**:
- Phase 1: Remove 35 fixtures (22% reduction)
- Phase 2: Remove 23 fixtures (15% reduction)
- Phase 3: Remove 10-15 fixtures (6-10% reduction)
- Phase 4: Remove 5-10 fixtures (3-6% reduction)

**Quality Metrics**:
- 100% test pass rate after each phase
- No shared mutable state between tests
- Clear fixture documentation
- Pytest fixture discovery working correctly

## Risk Assessment

**LOW RISK** (Phases 1-2):
- Mock fixtures have no complex dependencies
- Tests are isolated and independent
- Easy to verify with test suite runs
- Can revert individual commits if issues arise

**MEDIUM RISK** (Phase 3):
- Route-specific fixtures may have interdependencies
- Need to verify fixture discovery order
- May require adjustment of imports

**MITIGATION**:
- Run tests after each fixture consolidation
- Use git commits for each fixture type moved
- Keep test output logs for debugging
- Verify with `pytest --collect-only` to check fixture discovery

## References

- Original research: `.copilot-tracking/research/20260107-unit-test-fixture-duplication-research.md`
- Integration fixture consolidation: `.copilot-tracking/research/20260104-consolidate-test-fixtures-research.md`
- Current shared fixtures: `tests/conftest.py` (lines 1-840)
- Python testing instructions: `.github/instructions/python.instructions.md`
