<!-- markdownlint-disable-file -->
# Task Research Notes: E2E Test Hermetic Isolation

## Executive Summary

**Problem**: E2E tests depend on shared state seeded by init service at container startup. This prevents writing tests for guild creation and causes test interdependencies.

**Solution**: Replace init service seeding with function-scoped fixtures that create guilds via /api/v1/guilds/sync and clean up after each test.

**Scope**: 21 test files requiring fixture dependency updates (test logic unchanged)

**Key Changes**:
1. Remove seed_e2e_data() call from init service
2. Create fresh_guild and fresh_guild_b fixtures with automatic cleanup
3. Update all test fixtures to use fresh guilds instead of pre-seeded data
4. Keep test_00_environment.py for database/migration validation only
5. Single PR migration (OK to break intermediate state)

## Research Executed

### File Analysis
- services/init/seed_e2e.py
  - Seeds Guild A + Guild B with channels, users, templates at init time
  - Creates shared state that all E2E tests depend on
  - Makes it impossible to write tests that create guilds from scratch
- tests/e2e/conftest.py
  - Session-scoped fixtures for Discord IDs (guild_id, channel_id, user_id)
  - `synced_guild` fixture calls /api/v1/guilds/sync
  - `synced_guild_b` fixture for cross-guild testing
- tests/e2e/test_00_environment.py
  - Validates init service seeded data exists
  - Tests verify Guild A, Guild B, channels, users, templates in database
- tests/e2e/test_01_authentication.py
  - Single test: `test_synced_guild_creates_configs` depends on synced_guild fixture
- tests/e2e/test_guild_routes_e2e.py
  - Uses `synced_guild` fixture implicitly via guild_a_db_id/guild_b_db_id fixtures
- tests/e2e/test_guild_isolation_e2e.py
  - Uses `synced_guild` and `synced_guild_b` fixtures for template creation

### Code Search Results
- 18 test files reference "E2E data seeded by init service" in docstrings
- Tests expect guild_configurations, channel_configurations, game_templates to pre-exist
- `synced_guild` fixture only called by one test explicitly
- Most tests depend on session-scoped fixtures (discord_guild_id, discord_channel_id, discord_user_id)

### Project Conventions
- E2E tests marked with `pytestmark = pytest.mark.e2e`
- Tests use async fixtures and httpx.AsyncClient for API calls
- Database access via admin_db fixture (AsyncSession)
- Discord integration via DiscordTestHelper for message validation

## Key Discoveries

### Current Initialization Flow

1. **Init Service Startup** (services/init/main.py):
   - Phase 6: Calls `seed_e2e_data()` if TEST_ENVIRONMENT=true
   - Seeds Guild A + Guild B at container startup
   - Creates persistent shared state

2. **Data Created by Init Service** (services/init/seed_e2e.py):
   - Guild A: guild_configuration, channel_configuration, user (DISCORD_USER_ID), bot user, default template
   - Guild B: guild_configuration, channel_configuration, user (DISCORD_ADMIN_BOT_B_CLIENT_ID), default template
   - All records have fixed Discord IDs from environment variables

3. **Test Dependencies**:
   - Environment validation tests verify seeded data exists
   - Session-scoped fixtures provide Discord IDs from environment
   - Most tests query database expecting pre-existing records
   - `synced_guild` fixture only used by authentication test

### Hermetic Test Barriers

**Problem 1: Pre-seeded Database Records**
- Init service creates guild_configurations/channel_configurations at startup
- Database records exist before any test runs
- Impossible to test guild creation from scratch
- Cannot test `/api/v1/guilds/sync` with empty database state

**Problem 2: Shared Database State**
- All tests use same database records (guild_configurations, channel_configurations)
- Tests that modify guilds affect other tests
- No cleanup between tests
- Database state persists across entire test run

**Problem 3: Session-Scoped Fixtures**
- Fixtures query database expecting pre-seeded records
- Cannot create fresh database records for each test
- Fixtures don't clean up after themselves

**Note on Environment Variables**:
Environment variables for Discord IDs (DISCORD_GUILD_A_ID, DISCORD_CHANNEL_A_ID, etc.) are **required and correct**. E2E tests need real Discord entities set up manually before test execution. The problem is DATABASE seeding, not environment configuration. Fixtures should use environment variables to know WHICH Discord guilds to sync, but create database records on demand via /api/v1/guilds/sync instead of expecting pre-seeded records.

### Tests Using synced_guild Fixture

**Direct Usage**:
1. `test_01_authentication.py::test_synced_guild_creates_configs`
   - Verifies /api/v1/guilds/sync creates database records
   - Depends on pre-existing guild membership in Discord

**Indirect Usage** (via guild fixtures):
1. `test_guild_routes_e2e.py`:
   - `guild_a_db_id` fixture depends on synced_guild
   - `guild_b_db_id` fixture depends on synced_guild_b
2. `test_guild_isolation_e2e.py`:
   - `guild_a_template_id` depends on synced_guild
   - `guild_b_template_id` depends on synced_guild_b

**Tests Depending on Pre-seeded Data**:
All 18 test files with "E2E data seeded by init service" docstrings:
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
- test_game_authorization.py

### Test Database Access Patterns

**Common Pattern**:
```python
# Get guild database ID from pre-seeded data
result = await admin_db.execute(
    text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
    {"guild_id": discord_guild_id},  # From environment variable
)
row = result.fetchone()
assert row, f"Test guild {discord_guild_id} not found"  # Fails if init didn't seed
guild_db_id = row[0]

# Get template from pre-seeded data
result = await admin_db.execute(
    text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
    {"guild_id": guild_db_id},
)
template_id = result.fetchone()[0]  # Used to create games
```

## Recommended Approach

### Phase 1: Remove Init Service Seeding

**Goal**: Eliminate shared state by removing E2E seeding from init service

**Changes**:
1. Remove `seed_e2e_data()` call from services/init/main.py
2. Mark seed_e2e.py as deprecated
3. Run full E2E suite to identify broken tests

**Expected Failures**:
- test_00_environment.py: All database validation tests will fail
- All 18 tests expecting pre-seeded data will fail when querying guild_configurations
- test_01_authentication.py: synced_guild tests will pass (creates guilds dynamically)
- test_guild_routes_e2e.py: Will fail (depends on synced guilds existing)

### Phase 2: Create Guild Creation Fixtures

**Goal**: Provide hermetic fixtures that create and cleanup guilds

**Fixture Design**:
```python
@pytest.fixture
async def fresh_guild(
    admin_db: AsyncSession,
    authenticated_admin_client: httpx.AsyncClient,
    discord_token: str,
) -> AsyncGenerator[GuildContext, None]:
    """
    Create a fresh guild for test isolation.

    Uses /api/v1/guilds/sync to create guild from Discord bot membership.
    Cleans up guild and all related records after test.
    """
    # Call /api/v1/guilds/sync to create guild
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")
    assert response.status_code == 200

    # Get guild database ID
    result = await admin_db.execute(
        text("SELECT id, guild_id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": os.environ["DISCORD_GUILD_A_ID"]},
    )
    row = result.fetchone()

    guild_context = GuildContext(
        db_id=row[0],
        discord_id=row[1],
        channel_id=...,  # From sync results
        template_id=...,  # From default template
    )

    yield guild_context

    # Cleanup: Delete guild and cascade
    await admin_db.execute(
        text("DELETE FROM guild_configurations WHERE id = :id"),
        {"id": guild_context.db_id},
    )
    await admin_db.commit()
```

**Additional Fixtures**:
- `fresh_guild_b`: For cross-guild isolation tests
- `guild_with_template`: Creates guild + custom template
- `guild_with_channel`: Creates guild + channel configuration
- `guild_with_user`: Creates guild + user membership

### Phase 3: Migrate Tests to Hermetic Fixtures

**Migration Strategy**:
1. Start with test_01_authentication.py (already partially hermetic)
2. Migrate test_guild_routes_e2e.py (uses synced_guild)
3. Migrate test_guild_isolation_e2e.py (uses synced_guild_b)
4. Migrate remaining 18 tests one at a time

**Test Pattern Changes**:
```python
# Before: Depends on pre-seeded data
async def test_game_creation(discord_guild_id, discord_channel_id, admin_db):
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    guild_db_id = result.fetchone()[0]

# After: Uses hermetic fixture
async def test_game_creation(fresh_guild):
    guild_db_id = fresh_guild.db_id
```

### Phase 4: Environment Variables (NO CHANGES NEEDED)

**Clarification**: Environment variables are NOT a problem and should NOT be removed.

**What Environment Variables Provide** (Required for E2E tests):
- Real Discord guild IDs that bot is member of
- Real Discord channel IDs for message validation
- Real Discord user IDs for authentication testing
- Connection to actual Discord API for true end-to-end validation

**Why They Must Remain**:
- E2E tests require real Discord infrastructure (not mocks)
- Discord guilds/channels/users must be set up manually before test execution
- Fixtures need to know WHICH Discord entities to interact with
- Tests validate real Discord message delivery and webhook behavior

**What Actually Changes**:
- BEFORE: Init service reads env vars and SEEDS database with guild_configurations
- AFTER: Fixtures read same env vars and call /api/v1/guilds/sync on demand
- Database records are temporary (created per test, cleaned up after)
- Discord entities remain permanent (manual setup, documented in TESTING.md)

**No Dynamic Guild Generation**:
- Creating Discord guilds via API requires server creation permissions
- Cleanup is complex (must delete entire Discord servers)
- Manual setup is simpler and more reliable for E2E testing
- Environment variables provide the contract between manual setup and automated tests

### Phase 5: Environment Validation Refactor

**Goal**: Update test_00_environment.py to validate fixtures, not pre-seeded data

**Changes**:
```python
# Before: Validates init service seeded data
async def test_database_seeded(admin_db, discord_guild_id):
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    assert result.fetchone() is not None

# After: Validates fixture can create guild
async def test_fresh_guild_fixture(fresh_guild):
    assert fresh_guild.db_id is not None
    assert fresh_guild.discord_id is not None
    assert fresh_guild.template_id is not None
```

## Complete Fixture Implementation

### Environment Variable Management

**Pattern**: Load and validate all Discord IDs once at session start, provide via fixture

```python
from dataclasses import dataclass
import os
import pytest

@dataclass
class DiscordTestEnvironment:
    """
    Discord IDs from environment variables for E2E testing.

    These point to real Discord entities that must be set up manually
    before running E2E tests (see TESTING.md for setup instructions).
    """
    # Guild A (primary test guild)
    guild_a_id: str
    channel_a_id: str
    user_a_id: str

    # Guild B (for cross-guild isolation tests)
    guild_b_id: str
    channel_b_id: str
    user_b_id: str

    @classmethod
    def from_environment(cls) -> "DiscordTestEnvironment":
        """
        Load Discord IDs from environment variables with validation.

        Raises:
            ValueError: If required environment variables are missing
            ValueError: If Discord IDs have invalid format (not snowflakes)
        """
        required_vars = {
            "DISCORD_GUILD_A_ID": "Guild A ID",
            "DISCORD_CHANNEL_A_ID": "Guild A channel ID",
            "DISCORD_USER_A_ID": "Guild A user ID",
            "DISCORD_GUILD_B_ID": "Guild B ID",
            "DISCORD_CHANNEL_B_ID": "Guild B channel ID",
            "DISCORD_USER_B_ID": "Guild B user ID",
        }

        missing_vars = [
            f"{var} ({desc})"
            for var, desc in required_vars.items()
            if not os.getenv(var)
        ]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables for E2E tests:\n"
                f"  {', '.join(missing_vars)}\n\n"
                f"See docs/developer/TESTING.md for setup instructions."
            )

        def validate_snowflake(value: str, name: str) -> str:
            """Validate Discord snowflake ID format (17-19 digit number)."""
            if not value.isdigit() or len(value) < 17 or len(value) > 19:
                raise ValueError(
                    f"{name} has invalid Discord ID format: {value}\n"
                    f"Expected 17-19 digit snowflake ID"
                )
            return value

        return cls(
            guild_a_id=validate_snowflake(os.getenv("DISCORD_GUILD_A_ID"), "DISCORD_GUILD_A_ID"),
            channel_a_id=validate_snowflake(os.getenv("DISCORD_CHANNEL_A_ID"), "DISCORD_CHANNEL_A_ID"),
            user_a_id=validate_snowflake(os.getenv("DISCORD_USER_A_ID"), "DISCORD_USER_A_ID"),
            guild_b_id=validate_snowflake(os.getenv("DISCORD_GUILD_B_ID"), "DISCORD_GUILD_B_ID"),
            channel_b_id=validate_snowflake(os.getenv("DISCORD_CHANNEL_B_ID"), "DISCORD_CHANNEL_B_ID"),
            user_b_id=validate_snowflake(os.getenv("DISCORD_USER_B_ID"), "DISCORD_USER_B_ID"),
        )


@pytest.fixture(scope="session")
def discord_ids() -> DiscordTestEnvironment:
    """
    Load and validate Discord IDs from environment variables.

    Session-scoped: Validates once at test session start.
    Provides fail-fast behavior with clear error messages.
    """
    return DiscordTestEnvironment.from_environment()
```

**Benefits**:
- **Fail Fast**: Validation happens before any tests run
- **Clear Errors**: Specific messages about which vars are missing/invalid
- **Type Safety**: IDE autocomplete for `discord_ids.guild_a_id`
- **Single Source**: All env var access goes through one fixture
- **Easy Mocking**: Can override `discord_ids` fixture for unit tests

### GuildContext Dataclass

```python
@dataclass
class GuildContext:
    """Context for a test guild with all related IDs."""
    db_id: str  # Database UUID
    discord_id: str  # Discord snowflake ID
    channel_db_id: str  # Database UUID for channel
    channel_discord_id: str  # Discord channel snowflake
    template_id: str  # Database UUID for default template


@pytest.fixture
async def fresh_guild(
    admin_db: AsyncSession,
    authenticated_admin_client: httpx.AsyncClient,
    discord_ids: DiscordTestEnvironment,
) -> AsyncGenerator[GuildContext, None]:
    """
    Create a fresh guild for test isolation using /api/v1/guilds/sync.

    Automatically cleans up guild and all related records after test.
    Uses Guild A from discord_ids fixture.
    """
    guild_db_id = None

    try:
        # Call /api/v1/guilds/sync to create guild from Discord bot membership
        response = await authenticated_admin_client.post("/api/v1/guilds/sync")
        assert response.status_code == 200, f"Guild sync failed: {response.text}"

        # Get guild database ID
        result = await admin_db.execute(
            text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_ids.guild_a_id},
        )
        row = result.fetchone()
        assert row, f"Guild {discord_ids.guild_a_id} not found after sync"
        guild_db_id = row[0]

        # Get channel database ID
        result = await admin_db.execute(
            text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
            {"channel_id": discord_ids.channel_a_id},
        )
        row = result.fetchone()
        assert row, f"Channel {discord_ids.channel_a_id} not found after sync"
        channel_db_id = row[0]

        # Get default template ID
        result = await admin_db.execute(
            text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
            {"guild_id": guild_db_id},
        )
        row = result.fetchone()
        assert row, f"Default template not found for guild {guild_db_id}"
        template_id = row[0]

        guild_context = GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_a_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.channel_a_id,
            template_id=template_id,
        )

        yield guild_context

    finally:
        # Cleanup: Delete guild and cascade to all related records
        if guild_db_id:
            await admin_db.execute(
                text("DELETE FROM guild_configurations WHERE id = :id"),
                {"id": guild_db_id},
            )
            await admin_db.commit()


@pytest.fixture
async def fresh_guild_b(
    admin_db: AsyncSession,
    authenticated_client_b: httpx.AsyncClient,
    discord_guild_b_id: str,
    discord_ids: DiscordTestEnvironment,
) -> AsyncGenerator[GuildContext, None]:
    """
    Create Guild B for cross-guild isolation testing.

    Uses User B's authenticated client and Guild B from discord_ids fixture.
    Automatically cleans up after test.
    """
    guild_db_id = None

    try:
        # Call /api/v1/guilds/sync to create Guild B
        response = await authenticated_client_b.post("/api/v1/guilds/sync")
        assert response.status_code == 200, f"Guild B sync failed: {response.text}"

        # Get guild database ID
        result = await admin_db.execute(
            text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
            {"guild_id": discord_ids.guild_b_id},
        )
        row = result.fetchone()
        assert row, f"Guild B {discord_ids.guild_b_id} not found after sync"
        guild_db_id = row[0]

        # Get channel database ID
        result = await admin_db.execute(
            text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
            {"channel_id": discord_ids.channel_b_id},
        )
        row = result.fetchone()
        assert row, f"Channel B {discord_ids.channel_b_id} not found after sync"
        channel_db_id = row[0]

        # Get default template ID
        result = await admin_db.execute(
            text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
            {"guild_id": guild_db_id},
        )
        row = result.fetchone()
        assert row, f"Default template not found for Guild B {guild_db_id}"
        template_id = row[0]

        guild_context = GuildContext(
            db_id=guild_db_id,
            discord_id=discord_ids.guild_b_id,
            channel_db_id=channel_db_id,
            channel_discord_id=discord_ids.
        )

        yield guild_context

    finally:
        # Cleanup: Delete Guild B and cascade
        if guild_db_id:
            await admin_db.execute(
                text("DELETE FROM guild_configurations WHERE id = :id"),
                {"id": guild_db_id},
            )
            await admin_db.commit()
```

### Migration Pattern for Tests

**Before** (depends on pre-seeded data):
```python and individual env fixtures):
```python
async def test_game_creation(
    authenticated_admin_client,
    discord_guild_id,  # Individual fixture per ID
    discord_channel_id,
    admin_db,
):
    # Query database for pre-seeded guild
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    guild_db_id = result.fetchone()[0]

    # Get template
    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_db_id},
    )
    template_id = result.fetchone()[0]

    # Test logic...
    response = await authenticated_admin_client.post("/api/v1/games", data={
        "template_id": template_id,
        "title": "Test Game",
        ...
    })
```

**After** (uses hermetic fixture with discord_ids):
```python
async def test_game_creation(
    authenticated_admin_client,
    fresh_guild,  # ← Provides all guild context
    discord_ids,  # ← Optional: if test needs Discord IDs directly
):
    # Use guild context directly (no database queries needed)
    template_id = fresh_guild.template_id

    # Test logic unchanged...
    response = await authenticated_admin_client.post("/api/v1/games", data={
        "template_id": template_id,
        "title": "Test Game",
        ...
    })

    # Can also access Discord IDs if needed for assertions
    assert fresh_guild.discord_id == discord_ids.guild_a_id

### Relationship to Existing synced_guild Fixtures

**Current State**:
- `synced_guild` fixture calls /api/v1/guilds/sync but expects pre-seeded guild
- Returns sync_results dict, not GuildContext
- No cleanup after test

**New fresh_guild Fixtures**:
- Also call /api/v1/guilds/sync but with empty database
- Return GuildContext with all IDs
- Automatic cleanup in finally block

**Replacement Strategy**:
1. Replace `synced_guild` fixture with `fresh_guild` implementation (same name)
2. Replace `synced_guild_b` fixture with `fresh_guild_b` implementation (same name)
3. Tests using sync_results dict need update (only test_01_authentication.py)
4. Downstream fixtures (guild_a_db_id, guild_a_template_id) need update

**Example: test_01_authentication.py Changes**:
```python
# Before: Uses sync_results dict
async def test_synced_guild_creates_configs(synced_guild, discord_guild_id):
    sync_results = synced_guild  # Dict with new_guilds, new_channels
    assert sync_results["new_guilds"] >= 0

# After: Uses GuildContext
async def test_synced_guild_creates_configs(fresh_guild):
    assert fresh_guild.db_id is not None
    assert fresh_guild.template_id is not None
```

### Downstream Fixture Updates

**test_guild_routes_e2e.py fixtures**:
```python
# Before: Depends on synced_guild and queries database
@pytest.fixture
async def guild_a_db_id(admin_db, discord_guild_id):
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    return result.fetchone()[0]

# After: Uses fresh_guild directly
@pytest.fixture
async def guild_a_db_id(fresh_guild):
    return fresh_guild.db_id

# Better: Remove fixture entirely and use fresh_guild.db_id in tests
```

**test_guild_isolation_e2e.py fixtures**:
```python
# Before: Complex fixture with guild sync + template query
@pytest.fixture
async def guild_a_template_id(admin_db, discord_guild_id, discord_channel_id, synced_guild):
    guild_result = await admin_db.execute(...)
    guild_a_db_id = guild_result.fetchone()[0]
    result = await admin_db.execute(...)
    return result.fetchone()[0]

# After: Simple passthrough to fresh_guild
@pytest.fixture
async def guild_a_template_id(fresh_guild):
    return fresh_guild.template_id

# Better: Remove fixture entirely and use fresh_guild.template_id in tests
```

**Recommendation**: Remove intermediate fixtures (guild_a_db_id, guild_a_template_id) and use fresh_guild attributes directly in tests.

## Implementation Guidance

### User Decisions (2026-02-01)

**Cleanup Strategy**: Function-scoped fixtures with cleanup after each test
**Guild B Strategy**: Create separate `fresh_guild_b` fixture
**Migration Approach**: Single PR, OK to break intermediate state
**test_00_environment**: Keep for database/migration validation, remove seeded data checks
**Test Logic**: Keep test code unchanged, only replace fixture dependencies

### Objectives
1. Remove shared state from E2E tests
2. Make every test hermetic (create own data, clean up after)
3. Enable guild creation tests
4. Keep test logiEnvironment Variable Management**
- Create DiscordTestEnvironment dataclass with all Discord IDs
- Create session-scoped `discord_ids` fixture with validation
- Validate snowflake ID format (17-19 digits)
- Provide clear error messages for missing/invalid vars

**Task 2: Create Guild Creation Fixtures**
- Create `fresh_guild` fixture with automatic cleanup
- Create `fresh_guild_b` fixture for isolation tests
- Add GuildContext dataclass for test data
- Both 3: Remove Init Service Seeding**
- Remove seed_e2e_data() call from services/init/main.py
- Keep Discord ID environment variables in compose.e2e.yaml (required)
- Create `fresh_guild_b` fixture for isolation tests
- Add GuildContext dataclass for test data
- Both fixtures use /api/v1/guilds/sync + cleanup in finally block

**Task 2: Remove Init Service Seeding**
- Remove seed_e2e_data() call from services/init/main.py
- Remove E2E seed environment variables from compose.e2e.yaml
- Mark seed_e2e.py as deprecated

**Task 4: Update test_00_environment.py**
- Keep database/migration validation tests
- Remove "database seeded" validation tests
- Keep Discord connectivity tests
- Remove Guild B template/config validation
- Add test to validate discord_ids fixture loads correctly

**Task 5: Update Guild-Dependent Fixtures**
- Remove individual ID fixtures (discord_guild_id, discord_channel_id, etc.)
- Replace guild_a_db_id fixture to use fresh_guild
- Replace guild_b_db_id fixture to use fresh_guild_b
- Replace guild_a_template_id fixture to use fresh_guild
- Replace guild_b_template_id fixture to use fresh_guild_b
- Update synced_guild/synced_guild_b to use fresh fixtures

**Task 6: Migrate All Test Files** (21 test files)
- Update fixture dependencies only
- Keep test logic unchanged
- Add fresh_guild/fresh_guild_b to function signatures
- Remove inline database queries for guild_db_id
- Replace individual ID fixtures with discord_ids where needed

**Task 7: Update Documentation**
- Update TESTING.md with new fixture patterns
- Document discord_ids fixture and environment variable requirements
- Document guild cleanup behavior
- Add troubleshooting section for cleanup failures
- Add section on environment variable validation errors

### Complete Test File Inventory

**Files Requiring Migration** (21 total):

1. **Environment Tests**:
   - test_00_environment.py - Remove seeded data validation, keep DB/migration checks

2. **Authentication Tests**:
   - test_01_authentication.py - Update synced_guild fixture usage

3. **Guild Tests** (2 files):
   - test_guild_routes_e2e.py - Replace guild_a_db_id/guild_b_db_id fixtures
   - test_guild_isolation_e2e.py - Replace guild_a_template_id/guild_b_template_id fixtures

4. **Game Tests** (16 files with "E2E data seeded by init service"):
   - test_game_announcement.py
   - test_game_authorization.py
   - test_game_cancellation.py
   - test_game_reminder.py
   - test_game_status_transitions.py
   - test_game_update.py
   - test_join_notification.py
   - test_player_removal.py
   - test_signup_methods.py
   - test_user_join.py
   - test_waitlist_promotion.py
   - Plus 5 more game-related tests

### Common Patterns to Replace

**Pattern 1: Guild DB ID Query**
```python
# Remove this pattern:
result = await admin_db.execute(
    text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
    {"guild_id": discord_guild_id},
)
guild_db_id = result.fetchone()[0]

# Replace with:
guild_db_id = fresh_guild.db_id
```

**Pattern 2: Template ID Query**
```python
# Remove this pattern:
result = await admin_db.execute(
    text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
    {"guild_id": guild_db_id},
)
template_id = result.fetchone()[0]

# Replace with:
template_id = fresh_guild.template_id
```

**Pattern 3: Channel ID Query**
```python
# Remove this pattern:
result = await admin_db.execute(
    text("SELECT id FROM channel_configurations WHERE channel_id = :channel_id"),
    {"channel_id": discord_channel_id},
)
channel_db_id = result.fetchone()[0]

# Replace with:
channel_db_id = fresh_guild.channel_db_id
```

### Database Cascade Behavior

When cleaning up guilds, foreign key constraints ensure cascade deletion:
- guild_configurations → channel_configurations (CASCADE)
- guild_configurations → game_templates (CASCADE)
- guild_configurations → game_sessions (CASCADE)
- game_sessions → participants (CASCADE)
- game_sessions → notifications (CASCADE)

Single DELETE on guild_configurations removes all related records.

### Edge Cases and Considerations

**Concurrent Test Execution**:
- Each test gets its own guild via /api/v1/guilds/sync
- Cleanup happens in finally block (guaranteed execution)
- Tests can't interfere with each other's guilds

**Fixture Dependency Order**:
- fresh_guild depends on: admin_db, authenticated_admin_client, discord_guild_id, discord_channel_id
- fresh_guild_b depends on: admin_db, authenticated_client_b, discord_guild_b_id, discord_channel_b_id
- Tests can depend on both fresh_guild and fresh_guild_b simultaneously

**Discord API Limitations**:
- /api/v1/guilds/sync requires bot membership in Discord guild
- Real Discord guilds still need manual setup (documented in TESTING.md)
- Sync creates database records from Discord guild state

**Cleanup Failures**:
- Finally block ensures cleanup even if test fails
- If cleanup fails, test framework will report it
- No orphaned records should persist between test runs

### Removed Files/Code

**Deprecated but Not Deleted** (for reference):
- services/init/seed_e2e.py - Mark as deprecated, don't delete (has unit tests)
- tests/services/init/test_seed_e2e.py - Keep unit tests for historical reference

**Removed From Execution**:
- services/init/main.py - Remove seed_e2e_data() call (Phase 6)
- compose.e2e.yaml - Remove TEST_ENVIRONMENT and seed-related env vars

### Dependencies
- Pytest fixtures framework
- AsyncSession for database operations
- httpx.AsyncClient for API calls
- Discord bot with guild membership
- Database CASCADE constraints for cleanup

### Success Criteria
- All E2E tests pass with no shared state
- Each test creates and cleans up own guilds
- Can write tests that create guilds from scratch
- test_00_environment.py validates database/migrations only (no seeded data checks)
- No orphaned database records after test suite
- Test logic remains unchanged - only fixture dependencies modified
- Guild creation/sync tests work without pre-seeded data
