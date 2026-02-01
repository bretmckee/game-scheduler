<!-- markdownlint-disable-file -->
# Task Research Notes: Template Creation Test Coverage

## Research Executed

### File Analysis
- tests/integration/test_template_default_overrides.py
  - Integration test verifying template defaults don't override user choices during game creation
  - Uses `create_template` fixture to create test template
  - Tests API via httpx client to create games from templates
  - Does NOT test template creation itself
- tests/integration/conftest.py
  - RabbitMQ fixtures for integration tests
  - No Discord-specific fixtures (bot tokens, channels)
- tests/e2e/conftest.py
  - Discord fixtures: discord_token, discord_main_bot_token, discord_guild_id, discord_channel_id, discord_user_id
  - discord_helper fixture for message verification
- tests/conftest.py
  - create_template fixture creates templates directly in database via SQL
  - Bypasses API entirely

### Code Search Results
- `services/api/routes/templates.py` - POST /guilds/{guild_id}/templates endpoint
  - Requires bot manager role authorization
  - Validates request via TemplateCreateRequest schema
  - Uses TemplateService.create_template()
  - Does NOT interact with Discord (no message posting)
  - Returns TemplateResponse with channel_name resolved
- E2E tests search
  - All E2E tests query for default template but never create custom templates
  - E2E tests focus on game lifecycle (announcement, updates, reminders, waitlist)
  - Use discord_helper for Discord message verification

### External Research
- N/A - Internal codebase analysis sufficient

### Project Conventions
- Integration tests: Test infrastructure integration (database, RabbitMQ) without Discord
- E2E tests: Test full system including Discord bot interactions
- Standards referenced: .github/instructions/integration-tests.instructions.md
- Test fixtures: Shared factories in tests/conftest.py

## Key Discoveries

### Project Structure
Integration tests verify:
- Database infrastructure and RLS policies
- RabbitMQ message queuing
- Transaction atomicity
- Status transitions and daemon processing

E2E tests verify:
- Discord message posting and updates
- Game announcements and reminders
- Notification daemon Discord interactions
- Complete user workflows

### Implementation Patterns
Template creation endpoint characteristics:
```python
@router.post("/guilds/{guild_id}/templates", ...)
async def create_template(
    guild_id: str,
    request: TemplateCreateRequest,
    current_user: ...,
    db: AsyncSession = Depends(get_db_with_user_guilds()),
    discord_client: DiscordAPIClient = Depends(get_discord_client),
):
    # 1. Authorization check (bot manager role required)
    await queries.require_guild_by_id(db, guild_id, ...)
    await dependencies.permissions.require_bot_manager(...)

    # 2. Create template via service
    template_svc = TemplateService(db)
    template = await template_svc.create_template(
        guild_id=guild_id,
        channel_id=request.channel_id,
        name=request.name,
        # ... all template fields
    )

    # 3. Build response with channel name resolution
    return await build_template_response(template, discord_client)
```

Discord client usage:
- Used ONLY to resolve channel_id → channel_name for response
- Does NOT post messages or interact with Discord
- Fetch operation is read-only and non-critical

### Complete Examples
Existing integration test pattern (test_template_default_overrides.py):
```python
@pytest.mark.asyncio
async def test_cleared_reminder_minutes_not_reverted_to_template_default(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    # Setup environment
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create template using factory fixture (direct DB)
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="Test Template",
        max_players=10,
    )

    # Create session and seed cache
    session_token, _ = await create_test_session(...)
    await seed_redis_cache(...)

    # Test game creation via API
    async with httpx.AsyncClient(...) as client:
        response = await client.post("/api/v1/games", data={...})
        assert response.status_code == 201
```

### API and Schema Documentation
TemplateCreateRequest schema:
- Required: guild_id, name, channel_id
- Optional: description, order, is_default, role filtering, game defaults
- Validated by Pydantic with min/max constraints

Authorization requirements:
- User must be authenticated (session token)
- User must be bot manager for the guild
- Guild must exist and be accessible via RLS

### Configuration Examples
Integration test environment (config/env.int):
- PostgreSQL with test database
- RabbitMQ for message queuing
- Redis for session cache
- No Discord bot connection required

E2E test environment (config/env.e2e):
- All integration components PLUS
- Discord bot tokens (admin and main)
- Real Discord guild/channel IDs
- Discord API access

### Technical Requirements
Template creation does NOT require Discord interaction because:
1. Template is pure database entity
2. Templates don't post Discord messages
3. Channel name resolution happens AFTER template creation for response building
4. Channel name resolution failure doesn't fail the operation (safe fallback)

Missing test coverage identified:
- No test verifies template creation via API endpoint
- No test verifies authorization enforcement
- No test verifies validation of required fields
- No test verifies database persistence after API call
- Factory fixture bypasses all API validation and authorization

## Recommended Approach

**Template creation test should be an INTEGRATION test** because:

### Why Integration Test (NOT E2E)
1. **No Discord bot interaction required**
   - Template creation doesn't post messages
   - Channel name resolution is optional (response-only)
   - Endpoint works without Discord connection

2. **Core functionality is database + API validation**
   - Database persistence
   - Authorization enforcement (bot manager role)
   - Request validation (schema, constraints)
   - Transaction handling

3. **Faster test execution**
   - Integration tests ~10-20 seconds
   - E2E tests ~60-120 seconds
   - No Discord rate limits or network latency

4. **More reliable**
   - No dependency on Discord API availability
   - No Discord rate limiting
   - No flaky message timing issues

### Test Implementation Pattern
```python
# tests/integration/test_template_creation.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_template_via_api(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template creation through POST /guilds/{guild_id}/templates."""
    # Setup test environment
    guild = create_guild(bot_manager_roles=["123456789"])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create authenticated session
    session_token, _ = await create_test_session(...)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=["123456789"],  # Include bot manager role
    )

    # Create template via API
    async with httpx.AsyncClient(
        base_url=api_base_url,
        cookies={"session_token": session_token},
    ) as client:
        response = await client.post(
            f"/api/v1/guilds/{guild['id']}/templates",
            json={
                "guild_id": guild["id"],
                "channel_id": channel["id"],
                "name": "D&D Campaign",
                "description": "Weekly D&D session",
                "max_players": 5,
                "expected_duration_minutes": 180,
                "reminder_minutes": [60, 15],
                "where": "Discord Voice",
                "signup_instructions": "Be on time",
                "order": 1,
                "is_default": False,
            }
        )

    # Verify response
    assert response.status_code == 201
    template_data = response.json()
    assert template_data["name"] == "D&D Campaign"
    assert template_data["guild_id"] == guild["id"]
    assert template_data["channel_id"] == channel["id"]
    assert template_data["max_players"] == 5
    template_id = template_data["id"]

    # Verify database persistence
    result = admin_db_sync.execute(
        text("""
            SELECT name, description, max_players, guild_id, channel_id
            FROM game_templates
            WHERE id = :id
        """),
        {"id": template_id}
    )
    row = result.fetchone()
    assert row is not None
    assert row.name == "D&D Campaign"
    assert row.description == "Weekly D&D session"
    assert row.max_players == 5
    assert row.guild_id == guild["id"]
    assert row.channel_id == channel["id"]
```

### Additional Test Cases Needed
1. **Authorization tests**
   - Test without bot manager role → 403 Forbidden
   - Test without authentication → 401 Unauthorized

2. **Validation tests**
   - Test missing required fields → 422 Unprocessable Entity
   - Test invalid channel_id → 404 Not Found
   - Test invalid guild_id → 404 Not Found

3. **Edge cases**
   - Test creating default template (is_default=True)
   - Test order field handling
   - Test null/empty optional fields

## Implementation Guidance
- **Objectives**: Prevent regression in template creation API endpoint
- **Key Tasks**:
  1. Create tests/integration/test_template_creation.py
  2. Implement happy path test (template creation succeeds)
  3. Implement authorization tests (403/401 cases)
  4. Implement validation tests (422/404 cases)
  5. Add docstrings explaining what regression each test prevents
- **Dependencies**:
  - Existing fixtures: create_guild, create_channel, create_user, seed_redis_cache
  - Existing helpers: create_test_session, cleanup_test_session
  - Integration test infrastructure: admin_db_sync, api_base_url
- **Success Criteria**:
  - All template creation paths tested via API
  - Authorization properly enforced
  - Database persistence verified
  - Test runs in integration test suite without Discord dependency
