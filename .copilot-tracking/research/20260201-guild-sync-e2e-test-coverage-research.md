<!-- markdownlint-disable-file -->
# Task Research Notes: Guild Sync E2E Test Coverage

## Research Executed

### File Analysis
- tests/e2e/test_01_authentication.py
  - Contains minimal guild sync test (lines 55-60) that only verifies response format
  - Does not verify database state, idempotency, or error handling
  - Missing verification of guild, channel, and template creation
- tests/e2e/test_guild_routes_e2e.py
  - Comprehensive tests for guild route authorization (GET/UPDATE operations)
  - Uses guild_a_db_id and guild_b_db_id fixtures for cross-guild testing
  - Pattern: Tests both positive (own guild) and negative (other guild) cases
- tests/e2e/test_guild_isolation_e2e.py
  - Tests cross-guild isolation for games and templates
  - Uses synced_guild and synced_guild_b fixtures
  - Pattern: Creates resources in Guild A and B, verifies isolation
- tests/e2e/conftest.py (lines 236-280)
  - synced_guild fixture calls /api/v1/guilds/sync endpoint
  - Returns sync response with new_guilds and new_channels counts
  - Includes debug print statements for troubleshooting
  - synced_guild_b fixture for Guild B synchronization
- services/api/services/guild_service.py (lines 210-256)
  - sync_user_guilds() orchestrates full sync workflow
  - Creates guild config, channel configs, and default template
  - Uses RLS context management for multi-guild operations
  - Returns counts of created guilds and channels

### Code Search Results
- "wait_for_db_condition" and "wait_for_game_message_id"
  - Used extensively in e2e tests for polling database state
  - Pattern: Poll with predicate until condition met or timeout
  - Located in tests/shared/polling.py
- "async def test.*" in tests/e2e/
  - 16 test functions across test files
  - Common patterns: authenticated clients, fixtures for guild/channel/template IDs
  - Tests use admin_db fixture for direct database verification

### External Research
N/A - All information gathered from project codebase

### Project Conventions
- E2E tests use real Discord resources (guilds, channels, users) configured in env.e2e
- Tests follow pattern: API call → wait for async processing → verify database state
- Guild isolation testing requires Guild A and Guild B infrastructure
- Tests use authenticated_admin_client and authenticated_client_b fixtures
- Database verification uses admin_db fixture with SQL queries
- Polling pattern from tests/shared/polling.py for async operations
- Test file naming: test_00_environment.py runs first, others numbered by phase

## Key Discoveries

### Current Guild Sync Test Coverage - UPDATED 2026-02-02

**Status**: Comprehensive guild sync tests now exist in test_guild_sync_e2e.py (640 lines)

**Tests Implemented** (6 tests covering all requirements):
1. ✅ test_complete_guild_creation - Verifies guild, channel, template creation with database validation
2. ✅ test_sync_idempotency - Tests multiple syncs don't create duplicates
3. ✅ test_multi_guild_sync - Verifies User A and User B sync their respective guilds
4. ✅ test_rls_enforcement_after_sync - Validates cross-guild isolation via RLS
5. ✅ test_channel_filtering - Confirms only text channels (type=0) are synced
6. ✅ test_template_creation_with_channels - Verifies default template creation
7. ✅ test_sync_respects_user_permissions - Validates MANAGE_GUILD permission checking

**Migration Task**: Update tests to use hermetic fixture pattern (discord_ids instead of individual fixtures)

**Changes Needed**:
1. Replace `discord_guild_id` parameter with `discord_ids` fixture
2. Replace `discord_guild_b_id` parameter with `discord_ids` fixture
3. Replace `discord_channel_id` parameter with `discord_ids` fixture
4. Update all test bodies to use `discord_ids.guild_a_id`, `discord_ids.channel_a_id`, etc.
5. Update `fresh_guild_sync` fixture to use `discord_ids` instead of individual ID parameters

**Original Test (test_01_authentication.py:55-60)** - Still exists but minimal:
```python
async def test_synced_guild_creates_configs(synced_guild, discord_guild_id):
    """Verify guild sync creates necessary configurations."""
    assert synced_guild is not None
    assert "new_guilds" in synced_guild
    assert "new_channels" in synced_guild
```

### Guild Sync Implementation Details

**What sync_user_guilds() Does**:
1. Fetches user's guilds from Discord (with MANAGE_GUILD permission)
2. Fetches bot's guilds from Discord
3. Computes intersection (guilds where user is admin AND bot is installed)
4. Expands RLS context to include candidate guilds
5. Queries existing guilds from database
6. For each new guild:
   - Creates GuildConfiguration record
   - Fetches channels from Discord API
   - Creates ChannelConfiguration for each text channel (type=0)
   - Creates default GameTemplate for first text channel
7. Returns counts of created guilds and channels

**Key Complexity Areas**:
- RLS context management across multiple guild operations
- Discord API calls (user guilds, bot guilds, guild channels)
- Multi-step database creation (guild → channels → template)
- Transaction atomicity (all-or-nothing for each guild)

### E2E Test Infrastructure

**Available Fixtures**:
- `authenticated_admin_client` - HTTP client for User A (Guild A admin)
- `authenticated_client_b` - HTTP client for User B (Guild B admin)
- `admin_db` - Async database session with admin access
- `discord_guild_id` - Guild A Discord snowflake ID
- `discord_guild_b_id` - Guild B Discord snowflake ID
- `discord_channel_id` - Guild A channel Discord snowflake ID
- `discord_channel_b_id` - Guild B channel Discord snowflake ID
- `synced_guild` - Calls /guilds/sync for Guild A
- `synced_guild_b` - Calls /guilds/sync for Guild B
- `wait_for_db_condition` - Polling utility for async database changes

**Test Environment** (config/env.e2e):
- Real Discord bot tokens (DISCORD_BOT_TOKEN, DISCORD_ADMIN_BOT_A_TOKEN)
- Real Discord guild IDs (DISCORD_GUILD_A_ID, DISCORD_GUILD_B_ID)
- Real Discord channel IDs
- Real Discord user IDs with known permissions
- Controlled, persistent Discord resources for deterministic testing

### Existing Test Patterns

**Pattern 1: Database Verification After API Call**
```python
# From test_guild_isolation_e2e.py:38-55
guild_result = await admin_db.execute(
    text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
    {"guild_id": discord_guild_id},
)
guild_row = guild_result.fetchone()
assert guild_row, f"Guild A {discord_guild_id} not found in database"
guild_a_db_id = guild_row[0]
```

**Pattern 2: Cross-Guild Isolation Testing**
```python
# From test_guild_routes_e2e.py:66-82
# User B can access their own guild
response_b = await authenticated_client_b.get(f"/api/v1/guilds/{guild_b_db_id}")
assert response_b.status_code == 200

# User A cannot access Guild B
response_a = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_b_db_id}")
assert response_a.status_code == 404
```

**Pattern 3: Polling for Async Operations**
```python
# From test_guild_isolation_e2e.py:98-110
await wait_for_db_condition_async(
    admin_db,
    "SELECT id FROM game_sessions WHERE id = :game_id",
    {"game_id": game_id},
    lambda result: result is not None,
    timeout=10,
    description=f"Guild A game {game_id} to exist in database",
)
```

### Complete Examples

**Guild Sync Service Implementation** (services/api/services/guild_service.py:210-256):
```python
async def sync_user_guilds(db: AsyncSession, access_token: str, user_id: str) -> dict[str, int]:
    """
    Sync user's Discord guilds with database.

    Fetches user's guilds with MANAGE_GUILD permission and bot's guilds,
    then creates GuildConfiguration and ChannelConfiguration for new guilds.
    Creates default template for each new guild.
    """
    discord_client = get_discord_client()

    # Compute candidate guilds: (bot guilds ∩ user admin guilds)
    candidate_guild_ids = await _compute_candidate_guild_ids(discord_client, access_token, user_id)

    # Set RLS context to include ALL candidate guilds for query and insert
    await _expand_rls_context_for_guilds(db, candidate_guild_ids)

    # Query for existing guilds with proper RLS context set
    existing_guild_ids = await _get_existing_guild_ids(db)

    new_guild_ids = candidate_guild_ids - existing_guild_ids

    if not new_guild_ids:
        return {"new_guilds": 0, "new_channels": 0}

    # Create guild and channel configs for new guilds
    new_guilds_count = 0
    new_channels_count = 0

    for guild_discord_id in new_guild_ids:
        guilds_created, channels_created = await _create_guild_with_channels_and_template(
            db, discord_client, guild_discord_id
        )
        new_guilds_count += guilds_created
        new_channels_count += channels_created

    return {"new_guilds": new_guilds_count, "new_channels": new_channels_count}
```

**Guild Creation Helper** (services/api/services/guild_service.py:150-208):
```python
async def _create_guild_with_channels_and_template(
    db: AsyncSession,
    client: DiscordAPIClient,
    guild_discord_id: str,
) -> tuple[int, int]:
    """Create guild configuration, channel configurations, and default template."""
    # Set RLS context to Discord snowflake ID for guild creation
    current_guild_ids = get_current_guild_ids() or []
    initial_guild_ids = list(set(current_guild_ids) | {guild_discord_id})
    initial_ids_csv = ",".join(initial_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{initial_ids_csv}'"))
    set_current_guild_ids(initial_guild_ids)

    # Create guild config
    guild_config = await create_guild_config(db, guild_discord_id)

    # Update RLS context to include the new guild UUID
    current_guild_ids = get_current_guild_ids() or []
    updated_guild_ids = list(set(current_guild_ids) | {str(guild_config.id)})
    updated_ids_csv = ",".join(updated_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{updated_ids_csv}'"))
    set_current_guild_ids(updated_guild_ids)

    # Fetch guild channels using bot token
    guild_channels = await client.get_guild_channels(guild_discord_id)

    # Create channel configs for text channels (type=0)
    text_channel = 0
    channels_created = 0
    for channel in guild_channels:
        if channel.get("type") == text_channel:
            await channel_service.create_channel_config(
                db, guild_config.id, channel["id"], is_active=True
            )
            channels_created += 1

    # Create default template for first text channel
    if guild_channels:
        first_channel = next((ch for ch in guild_channels if ch.get("type") == text_channel), None)
        if first_channel:
            channel_config = await queries.get_channel_by_discord_id(db, first_channel["id"])
            if channel_config:
                template_svc = template_service_module.TemplateService(db)
                await template_svc.create_default_template(guild_config.id, channel_config.id)

    return (1, channels_created)
```

**E2E Fixture Pattern** (tests/e2e/conftest.py:236-258):
```python
@pytest.fixture
async def synced_guild(authenticated_admin_client, discord_guild_id):
    """
    Sync guilds using the API endpoint and return sync results.

    Calls /api/v1/guilds/sync with the admin bot token.
    Returns the sync response containing new_guilds and new_channels counts.
    """
    response = await authenticated_admin_client.post("/api/v1/guilds/sync")

    assert response.status_code == 200, (
        f"Guild sync failed: {response.status_code} - {response.text}"
    )

    return response.json()
```

### API and Schema Documentation

**Guild Sync Endpoint** (services/api/routes/guilds.py:287-310):
```python
@router.post("/sync", response_model=guild_schemas.GuildSyncResponse)
async def sync_guilds(
    current_user: Annotated[auth_schemas.CurrentUser, Depends(dependencies.auth.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db)],
) -> guild_schemas.GuildSyncResponse:
    """
    Sync user's Discord guilds with database.

    Fetches user's guilds with MANAGE_GUILD permission and bot's guilds,
    creates GuildConfiguration and ChannelConfiguration for new guilds,
    and creates default template for each new guild.

    Returns count of new guilds and channels created.
    """
    access_token = current_user.access_token
    user_discord_id = current_user.user.discord_id

    result = await guild_service.sync_user_guilds(db, access_token, user_discord_id)

    return guild_schemas.GuildSyncResponse(
        new_guilds=result["new_guilds"],
        new_channels=result["new_channels"],
    )
```

**Response Schema** (shared/schemas/guild.py:84-88):
```python
class GuildSyncResponse(BaseModel):
    """Response from guild sync operation."""

    new_guilds: int = Field(..., description="Number of new guilds created")
    new_channels: int = Field(..., description="Number of new channels created")
```

### Configuration Examples

**E2E Environment Configuration** (config/env.e2e:1-50):
```bash
# Discord Bot Configuration
DISCORD_BOT_TOKEN=<token value>
DISCORD_BOT_CLIENT_ID=<client id>

# E2E Test Guild A
DISCORD_GUILD_A_ID=<guild_a_snowflake>
DISCORD_GUILD_A_CHANNEL_ID=<channel_a_snowflake>
DISCORD_USER_ID=<user_a_snowflake>
DISCORD_ADMIN_BOT_A_TOKEN=<admin_bot_a_token>

# E2E Test Guild B (cross-guild isolation)
DISCORD_GUILD_B_ID=<guild_b_snowflake>
DISCORD_GUILD_B_CHANNEL_ID=<channel_b_snowflake>
DISCORD_ADMIN_BOT_B_CLIENT_ID=<user_b_snowflake>
DISCORD_ADMIN_BOT_B_TOKEN=<admin_bot_b_token>

# Container Configuration
CONTAINER_PREFIX=gamebot-e2e
COMPOSE_FILE=compose.yaml:compose.e2e.yaml
```

### Technical Requirements

**Database Tables Involved**:
- `guild_configurations` - Guild config records (guild_id = Discord snowflake)
- `channel_configurations` - Channel config records (channel_id = Discord snowflake, guild_id = guild config UUID)
- `game_templates` - Template records (guild_id = guild config UUID, channel_id = channel config UUID)
- `users` - User records (discord_id = Discord snowflake)

**RLS Context Management**:
- Uses PostgreSQL session variables: `SET LOCAL app.current_guild_id = '<uuid>'`
- Supports multiple guild IDs: `SET LOCAL app.current_guild_ids = 'id1,id2,id3'`
- Context must include both Discord snowflake (for creation) and UUID (for template)

**Discord API Calls**:
- `GET /users/@me/guilds` (with user OAuth token) - Get user's guilds with permissions
- `GET /users/@me/guilds` (with bot token) - Get bot's guilds
- `GET /guilds/{guild_id}/channels` (with bot token) - Get guild channels
- Rate limit: 1 req/sec for user guilds endpoint (enforced with asyncio.sleep(1.1))

**Test Execution Requirements**:
- Real Discord bot with access to test guilds
- User accounts with MANAGE_GUILD permission in test guilds
- Bot installed in test guilds with channel view permissions
- At least 2 guilds for cross-guild isolation testing
- Database must be clean or idempotent test design required

## Recommended Approach

Create comprehensive e2e test suite for guild sync functionality that verifies:

### Test Suite: test_guild_sync_e2e.py

**Test 1: Verify Complete Guild Creation**
- Call /guilds/sync endpoint
- Verify GuildConfiguration created in database with correct Discord snowflake
- Verify ChannelConfiguration records created for all text channels
- Verify default GameTemplate created for first text channel
- Verify response counts match database records
- Verify user can access created guild through /guilds endpoint

**Test 2: Idempotency (Multiple Syncs)**
- Call /guilds/sync endpoint twice
- Verify first call creates records (new_guilds > 0)
- Verify second call creates no records (new_guilds = 0, new_channels = 0)
- Verify no duplicate guild/channel/template records in database
- Verify guild remains accessible after second sync

**Test 3: Multi-Guild Sync**
- Setup: Ensure bot is in both Guild A and Guild B
- User A syncs (admin in Guild A only)
- Verify only Guild A created
- User B syncs (admin in Guild B only)
- Verify only Guild B created
- Verify cross-guild isolation (User A cannot see Guild B data)

**Test 4: Channel Filtering (Text Channels Only)**
- Setup: Mock or use guild with voice channels
- Call /guilds/sync
- Verify only text channels (type=0) created in database
- Verify voice channels (type=2) not created
- Verify default template uses first text channel

**Test 5: Template Creation Edge Cases**
- Test guild with no channels (verify template not created)
- Test guild with only voice channels (verify template not created)
- Test guild with text channels (verify template created)
- Verify template is_default=True
- Verify template channel_id matches first text channel

**Test 6: RLS Enforcement After Sync**
- User A syncs Guild A
- User B syncs Guild B
- Verify User A can query Guild A games/templates
- Verify User A gets 404 for Guild B games/templates
- Verify User B can query Guild B games/templates
- Verify User B gets 404 for Guild A games/templates

**Test 7: Permission Checking**
- Test user without MANAGE_GUILD permission
- Verify /guilds/sync returns empty result (no new guilds)
- Test bot not installed in user's admin guilds
- Verify /guilds/sync returns empty result

**Test 8: Discord API Error Handling**
- Test with invalid Discord token (mock or separate test)
- Test with Discord API timeout/error (mock or separate test)
- Verify appropriate error response
- Verify partial failure doesn't create orphaned records

## Implementation Guidance - COMPLETED 2026-02-02

**Migration Status**: ✅ COMPLETE

**Changes Applied**:
1. ✅ Updated `fresh_guild_sync` fixture to use `discord_ids` parameter
2. ✅ Updated all 7 test functions to use `discord_ids` instead of individual fixtures:
   - test_complete_guild_creation
   - test_sync_idempotency
   - test_multi_guild_sync
   - test_rls_enforcement_after_sync
   - test_channel_filtering
   - test_template_creation_with_channels
   - test_sync_respects_user_permissions
3. ✅ Updated all test bodies to use `discord_ids.guild_a_id`, `discord_ids.channel_a_id`, `discord_ids.guild_b_id`
4. ✅ Maintained helper fixtures (get_guild_by_discord_id, get_channels_for_guild, get_templates_for_guild)
5. ✅ Preserved fresh_guild_sync cleanup pattern (appropriate for testing /guilds/sync endpoint)

**Key Differences from Other E2E Tests**:
- Guild sync tests do NOT use `fresh_guild_a`/`fresh_guild_b` fixtures
- Reason: Testing the /guilds/sync endpoint itself, which creates guilds
- Uses custom `fresh_guild_sync` fixture that starts with empty database
- All other E2E tests should use `fresh_guild_a`/`fresh_guild_b` for pre-created guilds

**Next Steps**:
- Run tests: `docker compose --env-file config/env.e2e run --rm e2e-tests tests/e2e/test_guild_sync_e2e.py -v`
- Verify all 7 tests pass with hermetic fixtures
- Update remaining E2E tests to use hermetic pattern per 20260201-e2e-test-hermetic-isolation-plan.instructions.md

**Original Implementation Guidance**:

- **Objectives**: Establish comprehensive e2e test coverage for guild sync functionality including database verification, idempotency, cross-guild isolation, and error scenarios
- **Key Tasks**:
  1. Create test_guild_sync_e2e.py with 8 test scenarios
  2. Add helper fixtures for database verification (get_guild_by_discord_id, get_channels_for_guild, get_templates_for_guild)
  3. Add cleanup fixtures to ensure test isolation
  4. Use existing polling utilities for async operations
  5. Follow existing e2e test patterns (authenticated clients, admin_db verification)
- **Dependencies**:
  - Existing e2e test infrastructure (authenticated clients, admin_db)
  - Real Discord environment configured in env.e2e
  - Guild A and Guild B test infrastructure
  - tests/shared/polling.py utilities
- **Success Criteria**:
  - All 8 test scenarios passing
  - Tests verify both API responses and database state
  - Tests are idempotent (can run multiple times)
  - Tests verify cross-guild isolation
  - Tests follow project conventions and patterns
  - No test pollution (proper cleanup between tests)
