<!-- markdownlint-disable-file -->
# Task Research Notes: Consolidate Test Fixtures

## Executive Summary

**Problem**: Test fixtures are a mess - duplicated across `tests/integration/conftest.py`, `tests/e2e/conftest.py`, and individual test files. No design, just organic growth leading to:
- 100+ fixtures scattered across 30+ files
- Same patterns repeated 15+ times (guild+channel+user creation)
- **Redis cache seeding duplicated inline in every test** (5 cache keys × 3 test files)
- Mix of sync/async, ORM/raw SQL, no consistency
- Untested fixtures that caused deadlocks and cleanup conflicts
- Integration and e2e tests can't share fixtures

**Solution**: Consolidate into `tests/conftest.py` with:
- Factory-based fixtures (functions that create data, not data itself)
- **Single `seed_redis_cache` fixture to replace inline duplication**
- Sync-first implementation (daemon tests need sync)
- Async wrappers using `asyncio.run()` to avoid duplication
- Comprehensive fixture tests to prevent deadlocks
- Migration plan to move shared fixtures from subdirectories

**Key Insight from Debugging**: `admin_db_sync` automatic cleanup caused test failures because tests had their own cleanup fixtures that conflicted. Solution: Hermetic tests that create everything they need and rely on automatic cleanup.

## Current Fixture Landscape

### tests/integration/conftest.py (24 fixtures)
**Infrastructure fixtures**:
- `rabbitmq_url`, `rabbitmq_connection`, `rabbitmq_channel` - RabbitMQ access
- `cleanup_guild_context`, `cleanup_db_engine` - Autouse cleanup
- `db_url`, `admin_db_url` - URL generators (session scope)
- `async_engine`, `admin_async_engine` - Async engines
- `async_session_factory`, `admin_async_session_factory` - Session factories
- `db`, `admin_db` - Async database sessions
- `redis_client` - Async Redis client
- `seed_user_guilds_cache()` - Helper function to seed user guilds cache
- `seed_user_session()` - Helper function to seed session cache

**Data creation fixtures** (async ORM):
- `guild_a_id`, `guild_b_id` - UUID generators
- `guild_a_config`, `guild_b_config` - Guild objects
- `channel_a`, `channel_b` - Channel objects
- `template_a`, `template_b` - Template objects
- `user_a`, `user_b` - User objects
- `game_a`, `game_b` - Game objects

**Limitations**:
- All async (daemon tests need sync)
- All ORM (many tests use raw SQL)
- Fixed A/B naming (not flexible)
- Only available to integration tests
- Redis cache seeding is helper functions, not fixtures (inconsistent pattern)
- Each test duplicates Redis seeding code inline (5 cache keys each)

### tests/e2e/conftest.py (20+ fixtures)
**Infrastructure fixtures**:
- `discord_token`, `discord_main_bot_token` - Bot tokens
- `discord_guild_id`, `discord_channel_id`, `discord_user_id` - Test IDs
- `discord_guild_b_id`, `discord_channel_b_id`, `discord_user_b_id`, `discord_user_b_token` - Guild B
- `database_url`, `db_engine`, `db_session` - Database access
- `api_base_url`, `http_client` - HTTP clients
- `discord_helper`, `bot_discord_id` - Discord helpers
- `e2e_timeouts` - Timeout values

**Data creation fixtures**:
- `authenticated_admin_client` - Auth'd HTTP client
- `authenticated_client_b` - User B auth'd client
- `synced_guild` - Guild sync results
- `guild_b_db_id`, `guild_b_template_id` - Guild B data

**Individual e2e test files** (12 files): Each has 3-5 custom fixtures creating guilds/channels/users/games

**Problems**:
- Massive duplication across test files
- Can't use integration test fixtures
- No shared factory pattern

### Individual Test Files (50+ custom fixtures)
**Patterns found**:
1. **test_notification_daemon.py**: `test_game_session` - Creates full hierarchy
2. **test_status_transitions.py**: `test_game_session` - Identical to above
3. **test_game_signup_methods.py**: `test_user`, `test_template`, `authenticated_client` - Complex setup
4. **test_template_default_overrides.py**: `clean_test_data` - Conflicts with automatic cleanup
5. **12 e2e test files**: Each duplicates guild/channel/user/game creation

## Lessons Learned from Debugging Session

### Lesson 1: Automatic Cleanup Conflicts
**Problem**: Tests with custom `clean_test_data` fixtures that delete before/after test execution conflict with `admin_db_sync` automatic cleanup.

**Example failure**:
```python
@pytest.fixture
def clean_test_data(admin_db_sync):
    # Delete before test
    admin_db_sync.execute(text("DELETE FROM game_templates WHERE name LIKE 'TEST%'"))
    yield
    # Delete after test
    admin_db_sync.execute(text("DELETE FROM game_templates WHERE name LIKE 'TEST%'"))

# Then admin_db_sync ALSO deletes everything!
# Result: Tests fail with "No channels found" because cleanup ran before test setup
```

**Solution**: Hermetic tests - create everything you need, rely on automatic cleanup, don't maintain shared test data.

### Lesson 2: Deadlock Prevention
**Problem**: TRUNCATE commands blocked by daemon connections holding "idle in transaction" locks.

**Solution**:
1. Explicit `session.rollback()` before `session.close()`
2. Use DELETE instead of TRUNCATE (row-level locks vs table-level)
3. Create separate cleanup session AFTER test session fully closed

**Critical code pattern**:
```python
yield session  # Test runs

session.rollback()  # Release locks!
session.close()
engine.dispose()

# NOW create cleanup session
cleanup_engine = create_engine(url)
cleanup_session = sessionmaker(bind=cleanup_engine)()
# Use DELETE not TRUNCATE
cleanup_session.execute(text("DELETE FROM game_sessions"))
```

### Lesson 3: Factory Pattern Needed
**Problem**: Fixed fixtures like `guild_a_config` don't work when tests need multiple guilds or specific Discord IDs.

**Solution**: Factory fixtures that return functions:
```python
@pytest.fixture
def create_guild_sync(admin_db_sync):
    def _create(discord_guild_id=None, bot_manager_roles=None):
        # Create and return guild dict
        return {"id": guild_id, "guild_id": discord_guild_id, ...}
    return _create

# Usage in test
def test_multi_guild(create_guild_sync):
    guild1 = create_guild_sync(discord_guild_id="111")
    guild2 = create_guild_sync(discord_guild_id="222")
```

### Lesson 4: Sync First, Async Wrapper
**Problem**: Duplicating sync and async versions of every fixture.

**Solution**: Implement sync version, wrap with `asyncio.run()` for async:
```python
# Sync version (primary implementation)
@pytest.fixture
def create_guild_sync(admin_db_sync):
    def _create(discord_guild_id=None):
        # Implementation with raw SQL
        pass
    return _create

# Async wrapper (no duplication)
@pytest.fixture
async def create_guild_async(create_guild_sync):
    def _create_async(discord_guild_id=None):
        return asyncio.run(create_guild_sync(discord_guild_id))
    return _create_async
```

**Note**: This works because fixture creation is sync, only the returned function needs to be called differently.

## Proposed Consolidated Fixture Design

### Architecture Principles

1. **Location**: All shared fixtures in `tests/conftest.py` (discovered by pytest for all tests)
2. **Factory Pattern**: Fixtures return functions, not data
3. **Sync First**: Implement sync version, wrap for async
4. **Hermetic Tests**: Create what you need, automatic cleanup handles deletion
5. **RLS Safe**: Always use admin user for fixture creation
6. **Tested**: Comprehensive tests for all fixtures to prevent deadlocks

### Core Database Fixtures (in tests/conftest.py)

```python
# ============================================================================
# Database URL Fixtures (Session Scope)
# ============================================================================

@pytest.fixture(scope="session")
def admin_db_url_sync():
    """Synchronous admin database URL (psycopg2)."""
    raw_url = os.getenv("ADMIN_DATABASE_URL", "postgresql://gamebot_admin:...")
    return raw_url  # No asyncpg conversion

@pytest.fixture(scope="session")
def admin_db_url():
    """Async admin database URL (asyncpg)."""
    raw_url = os.getenv("ADMIN_DATABASE_URL", "postgresql://gamebot_admin:...")
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")

@pytest.fixture(scope="session")
def app_db_url():
    """Async app user database URL (asyncpg, RLS enforced)."""
    raw_url = os.getenv("DATABASE_URL", "postgresql://gamebot_app:...")
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")

@pytest.fixture(scope="session")
def bot_db_url():
    """Async bot user database URL (asyncpg, BYPASSRLS)."""
    raw_url = os.getenv("BOT_DATABASE_URL", "postgresql://gamebot_bot:...")
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")

# ============================================================================
# Database Session Fixtures (Function Scope)
# ============================================================================

@pytest.fixture
def admin_db_sync(admin_db_url_sync):
    """
    Synchronous admin session with automatic cleanup.

    Use for: Daemon tests, raw SQL operations, fixture creation
    Cleanup: Automatic DELETE of all test data after test completes
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(admin_db_url_sync)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    yield session

    # Critical: rollback before close to release locks
    session.rollback()
    session.close()
    engine.dispose()

    # Separate cleanup session after test session closed
    cleanup_engine = create_engine(admin_db_url_sync)
    cleanup_session = sessionmaker(bind=cleanup_engine)()

    try:
        # Use DELETE not TRUNCATE (avoids daemon lock conflicts)
        cleanup_session.execute(text("DELETE FROM game_sessions"))
        cleanup_session.execute(text("DELETE FROM game_templates"))
        cleanup_session.execute(text("DELETE FROM channel_configurations"))
        cleanup_session.execute(text("DELETE FROM users"))
        cleanup_session.execute(text("DELETE FROM guild_configurations"))
        cleanup_session.commit()
    finally:
        cleanup_session.close()
        cleanup_engine.dispose()

@pytest.fixture
async def admin_db(admin_db_url):
    """Async admin session (no automatic cleanup - test controls commit/rollback)."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(admin_db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()

@pytest.fixture
async def app_db(app_db_url):
    """Async app user session (RLS enforced)."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(app_db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()

@pytest.fixture
async def bot_db(bot_db_url):
    """Async bot user session (BYPASSRLS)."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(bot_db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()

# ============================================================================
# Redis Client Fixture
# ============================================================================

@pytest.fixture
def redis_client(redis_client_sync):
    """
    Sync Redis client for cache operations.

    Primary implementation - most tests are sync and need Redis seeding.
    Uses asyncio.run() internally to manage async connect/disconnect.

    Used for:
    - Seeding user permissions (bot_manager_role_ids)
    - Caching Discord guild/channel/user metadata
    - Storing session tokens for authentication
    - Bypassing Discord API calls in tests

    Automatically connects and disconnects.

    Note: This is the sync version. For async tests, use redis_client_async.
    """
    from shared.cache.client import RedisClient
    import asyncio

    client = RedisClient()

    # Connect using asyncio.run()
    asyncio.run(client.connect())

    yield client

    # Disconnect using asyncio.run()
    asyncio.run(client.disconnect())


@pytest.fixture
async def redis_client_async():
    """
    Async Redis client for async integration tests.

    For tests that are already async and can await operations.
    Most tests should use redis_client (sync version) instead.
    """
    from shared.cache.client import RedisClient

    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


# ============================================================================
# Redis Cache Seeding Fixture
# ============================================================================

@pytest.fixture
def seed_redis_cache(redis_client):
    """
    Factory fixture to seed Redis cache with Discord metadata.

    Returns async function that seeds multiple cache keys at once.
    Designed to bypass Discord API calls in tests.

    Uses redis_client (sync fixture), so works in both sync and async tests.

    Current State Analysis:
    - tests/integration/conftest.py has seed_user_guilds_cache() and seed_user_session() helpers
    - test_game_signup_methods.py has inline cache seeding (5 cache keys)
    - test_template_default_overrides.py has inline cache seeding (3 cache keys)
    - This fixture consolidates all patterns into single factory

    Cache Keys Seeded:
    1. CacheKeys.user_guilds(user_discord_id) - RLS context
    2. CacheKeys.user_roles(user_discord_id, guild_id) - Permissions
    3. CacheKeys.discord_channel(channel_id) - Channel metadata
    4. CacheKeys.discord_guild(guild_id) - Guild metadata
    5. CacheKeys.session(session_token) - Authentication (optional)

    Usage (sync tests with asyncio.run):
        asyncio.run(seed_redis_cache(
            user_discord_id="123",
            guild_discord_id="456",
            channel_discord_id="789",
            bot_manager_roles=["999888777666555444"]
        ))

    Usage (async tests with await):
        await seed_redis_cache(
            user_discord_id=user["discord_id"],
            guild_discord_id=guild["guild_id"],
            channel_discord_id=channel["channel_id"]
        )
    """
    async def _seed(
        user_discord_id: str,
        guild_discord_id: str,
        channel_discord_id: str | None = None,
        user_roles: list[str] | None = None,
        bot_manager_roles: list[str] | None = None,
        session_token: str | None = None,
        session_user_id: str | None = None,
        session_access_token: str | None = None,
    ):
        """
        Seed Redis cache with Discord metadata to bypass API calls.

        Args:
            user_discord_id: Discord user ID (18-digit string)
            guild_discord_id: Discord guild ID (18-digit string)
            channel_discord_id: Discord channel ID (optional)
            user_roles: User's role IDs (defaults to [guild_discord_id] for membership)
            bot_manager_roles: Bot manager role IDs (appended to user_roles)
            session_token: Session token for auth (optional)
            session_user_id: User database UUID for session (optional)
            session_access_token: Discord access token for session (optional)
        """
        from shared.cache.keys import CacheKeys

        # User guilds (RLS context) - Required for guild isolation
        user_guilds_key = CacheKeys.user_guilds(user_discord_id)
        guilds_data = [{
            "id": guild_discord_id,
            "name": f"Test Guild {guild_discord_id[:8]}",
            "permissions": "2147483647",  # Administrator permissions
        }]
        await redis_client.set_json(user_guilds_key, guilds_data, ttl=300)

        # User roles (permissions) - Default to guild membership
        if user_roles is None:
            user_roles = [guild_discord_id]  # Discord convention: guild membership = guild_id role
        if bot_manager_roles:
            user_roles = user_roles + bot_manager_roles

        user_roles_key = CacheKeys.user_roles(user_discord_id, guild_discord_id)
        await redis_client.set_json(user_roles_key, user_roles, ttl=3600)

        # Channel metadata (if channel interactions needed)
        if channel_discord_id:
            channel_key = CacheKeys.discord_channel(channel_discord_id)
            await redis_client.set_json(channel_key, {
                "id": channel_discord_id,
                "name": "test-channel",
                "type": 0,  # GUILD_TEXT
                "guild_id": guild_discord_id,
            }, ttl=3600)

        # Guild metadata (always seed for guild name/icon)
        guild_key = CacheKeys.discord_guild(guild_discord_id)
        await redis_client.set_json(guild_key, {
            "id": guild_discord_id,
            "name": "Test Guild",
            "icon": None,
        }, ttl=3600)

        # Session (if authentication needed)
        if session_token and session_user_id and session_access_token:
            from shared.utils.token_encryption import encrypt_token
            from datetime import datetime, timedelta, UTC

            session_key = CacheKeys.session(session_token)
            session_data = {
                "user_id": session_user_id,
                "access_token": encrypt_token(session_access_token),
                "refresh_token": encrypt_token("mock_refresh_token"),
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
            await redis_client.set_json(session_key, session_data, ttl=3600)

    return _seed
```

### Factory Fixtures for Data Creation

```python
# ============================================================================
# Factory Fixtures (Synchronous - Primary Implementation)
# ============================================================================

@pytest.fixture
def create_guild(admin_db_sync):
    """
    Factory to create guild configurations.

    Returns function that creates guild and returns dict:
    - id: str (database UUID)
    - guild_id: str (Discord guild ID, 18 digits)
    - bot_manager_role_ids: list[str]

    Example:
        guild = create_guild(
            discord_guild_id="123456789012345678",
            bot_manager_roles=["999888777666555444"]
        )
        template = create_template(guild_id=guild["id"], ...)
    """
    def _create(
        discord_guild_id: str | None = None,
        bot_manager_roles: list[str] | None = None
    ) -> dict:
        from sqlalchemy import text
        from datetime import UTC, datetime
        import json
        import uuid

        guild_db_id = str(uuid.uuid4())
        guild_discord_id = discord_guild_id or str(uuid.uuid4())[:18]

        admin_db_sync.execute(text(
            "INSERT INTO guild_configurations "
            "(id, guild_id, bot_manager_role_ids, created_at, updated_at) "
            "VALUES (:id, :guild_id, :bot_manager_role_ids, :created_at, :updated_at)"
        ), {
            "id": guild_db_id,
            "guild_id": guild_discord_id,
            "bot_manager_role_ids": json.dumps(bot_manager_roles or []),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })
        admin_db_sync.commit()

        return {
            "id": guild_db_id,
            "guild_id": guild_discord_id,
            "bot_manager_role_ids": bot_manager_roles or []
        }

    return _create

@pytest.fixture
def create_channel(admin_db_sync):
    """Factory to create channel configurations."""
    def _create(
        guild_id: str,  # Database UUID
        discord_channel_id: str | None = None
    ) -> dict:
        from sqlalchemy import text
        from datetime import UTC, datetime
        import uuid

        channel_db_id = str(uuid.uuid4())
        channel_discord_id = discord_channel_id or str(uuid.uuid4())[:18]

        admin_db_sync.execute(text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
        ), {
            "id": channel_db_id,
            "channel_id": channel_discord_id,
            "guild_id": guild_id,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })
        admin_db_sync.commit()

        return {
            "id": channel_db_id,
            "channel_id": channel_discord_id,
            "guild_id": guild_id
        }

    return _create

@pytest.fixture
def create_user(admin_db_sync):
    """Factory to create users."""
    def _create(discord_user_id: str | None = None) -> dict:
        from sqlalchemy import text
        from datetime import UTC, datetime
        import uuid

        user_db_id = str(uuid.uuid4())
        user_discord_id = discord_user_id or str(uuid.uuid4())[:18]

        admin_db_sync.execute(text(
            "INSERT INTO users (id, discord_id, created_at, updated_at) "
            "VALUES (:id, :discord_id, :created_at, :updated_at)"
        ), {
            "id": user_db_id,
            "discord_id": user_discord_id,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })
        admin_db_sync.commit()

        return {
            "id": user_db_id,
            "discord_id": user_discord_id
        }

    return _create

@pytest.fixture
def create_template(admin_db_sync):
    """Factory to create game templates."""
    def _create(
        guild_id: str,
        channel_id: str,
        name: str = "Test Template",
        description: str | None = None,
        max_players: int = 4,
        allowed_signup_methods: list[str] | None = None,
        default_signup_method: str = "SELF_SIGNUP",
        **kwargs
    ) -> dict:
        from sqlalchemy import text
        from datetime import UTC, datetime
        import json
        import uuid

        template_db_id = str(uuid.uuid4())

        admin_db_sync.execute(text(
            "INSERT INTO game_templates "
            "(id, guild_id, channel_id, name, description, max_players, "
            "allowed_signup_methods, default_signup_method, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :name, :description, :max_players, "
            ":allowed_signup_methods, :default_signup_method, :created_at, :updated_at)"
        ), {
            "id": template_db_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "name": name,
            "description": description or f"Test template: {name}",
            "max_players": max_players,
            "allowed_signup_methods": json.dumps(allowed_signup_methods or ["SELF_SIGNUP"]),
            "default_signup_method": default_signup_method,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })
        admin_db_sync.commit()

        return {
            "id": template_db_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "name": name,
            "max_players": max_players
        }

    return _create

@pytest.fixture
def create_game(admin_db_sync):
    """Factory to create game sessions."""
    def _create(
        guild_id: str,
        channel_id: str,
        host_id: str,
        template_id: str | None = None,
        title: str = "Test Game",
        description: str | None = None,
        scheduled_at: datetime | None = None,
        max_players: int = 4,
        status: str = "scheduled",
        **kwargs
    ) -> dict:
        from sqlalchemy import text
        from datetime import UTC, datetime, timedelta
        import uuid

        game_db_id = str(uuid.uuid4())

        admin_db_sync.execute(text(
            "INSERT INTO game_sessions "
            "(id, guild_id, channel_id, host_id, template_id, title, description, "
            "scheduled_at, max_players, status, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :host_id, :template_id, :title, "
            ":description, :scheduled_at, :max_players, :status, :created_at, :updated_at)"
        ), {
            "id": game_db_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": host_id,
            "template_id": template_id,
            "title": title,
            "description": description or f"Test game: {title}",
            "scheduled_at": scheduled_at or datetime.now(UTC) + timedelta(hours=2),
            "max_players": max_players,
            "status": status,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })
        admin_db_sync.commit()

        return {
            "id": game_db_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": host_id,
            "title": title,
            "status": status
        }

    return _create
```

### Composite Fixtures for Common Patterns

```python
@pytest.fixture
def test_environment(create_guild, create_channel, create_user):
    """
    Create complete test environment (guild + channel + user).

    Returns dict with all three objects for convenience.

    Example:
        env = test_environment()
        game = create_game(
            guild_id=env["guild"]["id"],
            channel_id=env["channel"]["id"],
            host_id=env["user"]["id"]
        )
    """
    def _create(
        discord_guild_id: str | None = None,
        discord_channel_id: str | None = None,
        discord_user_id: str | None = None,
        bot_manager_roles: list[str] | None = None
    ) -> dict:
        guild = create_guild(
            discord_guild_id=discord_guild_id,
            bot_manager_roles=bot_manager_roles
        )
        channel = create_channel(
            guild_id=guild["id"],
            discord_channel_id=discord_channel_id
        )
        user = create_user(discord_user_id=discord_user_id)

        return {
            "guild": guild,
            "channel": channel,
            "user": user
        }

    return _create
```

## Implementation Plan

### Phase 0: Create and Test Shared Fixtures
**Goal**: Add all fixtures to `tests/conftest.py` and verify they work without deadlocks

**Tasks**:
1. Create `tests/conftest.py` with all fixtures above
2. Create `tests/integration/test_shared_fixtures.py` with comprehensive tests:
   - Test each factory fixture independently
   - Test composite fixtures
   - Test Redis cache seeding
   - Test automatic cleanup works
   - **CRITICAL**: Test for deadlocks with long-running daemon connections
3. Run fixture tests: `docker compose run integration-tests tests/integration/test_shared_fixtures.py`
4. Verify no hanging, all pass

**Success Criteria**:
- All fixture tests pass
- No deadlocks
- Automatic cleanup works
- Existing tests still pass (no breaking changes)

### Phase 1: Migrate Sync-Based Integration Tests
**Goal**: Migrate daemon tests to use shared fixtures

**Tests to migrate**:
1. `test_notification_daemon.py` - Replace `test_game_session` fixture
2. `test_status_transitions.py` - Replace `test_game_session` fixture
3. `test_retry_daemon.py` - Simplify with shared fixtures
4. `test_template_default_overrides.py` - Remove `clean_test_data`, use factories
5. `test_game_signup_methods.py` - Remove custom fixtures, use factories

**Pattern**:
```python
# OLD: Custom fixture creating everything
@pytest.fixture
def test_game_session(db_session):
    # 50 lines of INSERT statements
    pass

def test_something(test_game_session):
    game_id = test_game_session
    # Test logic

# NEW: Use factory fixtures
def test_something(admin_db_sync, create_guild, create_channel, create_user, create_game):
    guild = create_guild()
    channel = create_channel(guild["id"])
    user = create_user()
    game = create_game(guild["id"], channel["id"], user["id"])
    # Test logic - automatic cleanup handles deletion
```

**Success Criteria**:
- 5 tests migrated and passing
- Custom fixtures removed
- Tests simpler and more readable

### Phase 2: Migrate Async ORM Integration Tests
**Goal**: Update async tests to use shared fixtures consistently

**Tests to migrate**:
1. `test_guild_queries.py` - Remove local fixtures, use shared
2. `test_games_route_guild_isolation.py` - Remove local fixtures, use shared

**Deletion Policy**: As soon as a test is migrated to shared fixtures, immediately delete its custom fixtures from the test file. Once all tests using a deprecated fixture are migrated, immediately delete that fixture from `tests/integration/conftest.py`.

**Success Criteria**:
- Async tests using shared fixtures from `tests/conftest.py`
- No duplicate fixture definitions
- Custom fixtures deleted as tests are migrated

### Phase 3: Consolidate E2E Test Fixtures
**Goal**: E2E tests use shared fixtures from `tests/conftest.py`

**Approach**:
1. Keep e2e-specific fixtures in `tests/e2e/conftest.py`:
   - `discord_token`, `discord_guild_id`, etc. (test environment)
   - `authenticated_admin_client`, `authenticated_client_b` (auth)
   - `e2e_timeouts`, `discord_helper` (e2e utilities)

2. Migrate to shared fixtures:
   - Guild/channel/user/game creation → use factories from `tests/conftest.py`
   - Database session access → use `admin_db_sync`, `admin_db` from `tests/conftest.py`

3. Update 12 e2e test files to remove duplicate fixtures

**Success Criteria**:
- E2E tests simplified
- Duplicate fixtures removed
- Tests still pass

### Phase 4: Delete Redundant Fixtures
**Goal**: Clean up `tests/integration/conftest.py` to remove duplicates

**Actions**:
1. Delete fixtures from `tests/integration/conftest.py` as soon as they're no longer used by any test
2. No deprecation period - aggressive deletion once tests are migrated
3. Track migration progress to know when fixtures can be deleted

**Keep in tests/integration/conftest.py** (integration-specific utilities):
- `rabbitmq_url`, `rabbitmq_connection`, `rabbitmq_channel` (RabbitMQ specific)
- `cleanup_guild_context`, `cleanup_db_engine` (autouse cleanup)

**Delete immediately after migration** (superseded by `tests/conftest.py`):
- `db_url`, `admin_db_url` → replaced by versions in `tests/conftest.py`
- `async_engine`, `admin_async_engine` → replaced by session fixtures in `tests/conftest.py`
- `db`, `admin_db` → replaced by versions in `tests/conftest.py`
- `redis_client` (async version) → replaced by `redis_client` (sync) and `redis_client_async` in `tests/conftest.py`
- `seed_user_guilds_cache()` helper function → replaced by `seed_redis_cache` factory fixture
- `seed_user_session()` helper function → subsumed into `seed_redis_cache` factory fixture
- `guild_a_config`, `guild_b_config`, `channel_a`, `channel_b`, `template_a`, `template_b`, `user_a`, `user_b`, `game_a`, `game_b` → replaced by factory fixtures
- `guild_a_id`, `guild_b_id` → no longer needed with factory pattern

## Testing Strategy

### Fixture Validation Tests (tests/integration/test_shared_fixtures.py)

```python
import pytest
from datetime import UTC, datetime

def test_admin_db_sync_fixture_only(admin_db_sync):
    """Verify admin_db_sync fixture works without deadlock."""
    assert admin_db_sync is not None
    # Cleanup should run without hanging

def test_create_guild_factory(admin_db_sync, create_guild):
    """Test guild creation with factory fixture."""
    guild = create_guild(discord_guild_id="123456789012345678")

    assert guild["id"] is not None
    assert guild["guild_id"] == "123456789012345678"
    assert guild["bot_manager_role_ids"] == []

    # Verify in database
    from sqlalchemy import text
    result = admin_db_sync.execute(
        text("SELECT guild_id FROM guild_configurations WHERE id = :id"),
        {"id": guild["id"]}
    )
    assert result.scalar() == "123456789012345678"

def test_create_multiple_guilds(create_guild):
    """Test creating multiple guilds in same test."""
    guild1 = create_guild(discord_guild_id="111")
    guild2 = create_guild(discord_guild_id="222")

    assert guild1["id"] != guild2["id"]
    assert guild1["guild_id"] != guild2["guild_id"]

def test_test_environment_composite(test_environment):
    """Test composite fixture creates all objects."""
    env = test_environment(
        discord_guild_id="111",
        discord_channel_id="222",
        discord_user_id="333"
    )

    assert "guild" in env
    assert "channel" in env
    assert "user" in env
    assert env["channel"]["guild_id"] == env["guild"]["id"]

@pytest.mark.asyncio
async def test_seed_redis_cache(redis_client, seed_redis_cache):
    """Test Redis cache seeding."""
    await seed_redis_cache(
        redis_client=redis_client,
        user_discord_id="111",
        guild_discord_id="222",
        channel_discord_id="333",
        user_roles=["role1", "222"]
    )

    from shared.cache.keys import CacheKeys

    # Verify user guilds cached
    guilds = await redis_client.get_json(CacheKeys.user_guilds("111"))
    assert len(guilds) == 1
    assert guilds[0]["id"] == "222"
```

## Migration Examples

### Before: test_notification_daemon.py

```python
@pytest.fixture
def test_game_session(db_session):
    guild_id = str(uuid4())
    channel_id = str(uuid4())
    user_id = str(uuid4())
    game_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    # 40 lines of INSERT statements
    db_session.execute(text("INSERT INTO guild_configurations ..."))
    db_session.execute(text("INSERT INTO channel_configurations ..."))
    db_session.execute(text("INSERT INTO users ..."))
    db_session.execute(text("INSERT INTO game_sessions ..."))
    db_session.commit()

    yield game_id

    # 20 lines of cleanup DELETE statements
    db_session.execute(text("DELETE FROM ..."))

def test_notification_schedule_created(rabbitmq_channel, test_game_session):
    game_id = test_game_session
    # Test logic...
```

### After: test_notification_daemon.py

```python
def test_notification_schedule_created(
    admin_db_sync,
    rabbitmq_channel,
    create_guild,
    create_channel,
    create_user,
    create_game
):
    # Create test data - simple and readable
    guild = create_guild()
    channel = create_channel(guild["id"])
    user = create_user()
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=user["id"],
        scheduled_at=datetime.now(UTC) + timedelta(hours=2)
    )

    # Test logic...
    # Automatic cleanup handles deletion
```

## Benefits of Consolidated Approach

1. **Reduced Duplication**: 100+ fixtures → ~15 shared factories
2. **Better Testing**: Comprehensive fixture tests prevent deadlocks
3. **Flexibility**: Factory pattern allows tests to create exactly what they need
4. **Maintainability**: One place to update when schema changes
5. **Consistency**: All tests use same patterns
6. **Hermetic**: Tests don't interfere with each other
7. **Shareability**: Integration and e2e tests use same fixtures
8. **RLS Safe**: Always use admin user for setup, test with appropriate user

## Design Decisions

1. **All tests are hermetic**: No session-scoped fixtures for sharing data between tests. Each test creates what it needs and relies on automatic cleanup. Tests may currently share data because it was easy, but that's an anti-pattern we're fixing.

2. **Async wrapper implementation**: TBD - Need to determine if `asyncio.run()` works with pytest-asyncio event loops or if we need different approach.

3. **Aggressive migration and deprecation**: Remove deprecated fixtures as soon as they're unused. Once shared fixtures exist, migrate tests aggressively and delete old fixtures immediately.

4. **Redis client at top level**: `redis_client` fixture belongs in `tests/conftest.py` because it's used for permissions seeding and auth token caching, which both integration and e2e tests need.
