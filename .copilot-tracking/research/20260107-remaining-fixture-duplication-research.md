<!-- markdownlint-disable-file -->
# Task Research Notes: Remaining Test Fixture Duplication

## Research Executed

### File Analysis
- Analyzed all integration test files in `tests/integration/`
- Analyzed all e2e test files in `tests/e2e/`
- Examined `tests/conftest.py` for consolidated fixtures
- Examined `tests/integration/conftest.py` for remaining fixtures
- Examined `tests/e2e/conftest.py` for e2e-specific fixtures

### Code Search Results
- Search pattern: `@pytest\.fixture` across `tests/integration/**/*.py`
  - Found 15 fixture definitions across integration test files
- Search pattern: `@pytest\.fixture` across `tests/e2e/**/*.py`
  - Found 26 fixture definitions across e2e test files

### Integration Test Files Not Modified
Files that were NOT touched during consolidation effort:
1. `test_rabbitmq_infrastructure.py` - Custom RabbitMQ fixtures
2. `test_database_infrastructure.py` - Custom database fixtures for infrastructure testing
3. `test_database_users.py` - Custom postgres connection fixture
4. `test_rls_bot_bypass.py` - Custom `bot_db_session` fixture
5. `test_rls_api_enforcement.py` - Custom `app_db_session` fixture

### E2E Test Files Not Modified
All 12 e2e test files contain custom fixtures duplicating database access and ID fetching:
1. `test_join_notification.py` - `main_bot_helper` fixture (duplicated in 4+ files)
2. `test_game_reminder.py` - `main_bot_helper` fixture (duplicate)
3. `test_guild_routes_e2e.py` - `guild_a_db_id`, `guild_b_db_id` fixtures
4. `test_guild_isolation_e2e.py` - `guild_a_template_id`, `guild_b_template_id`, `guild_a_game_id`, `guild_b_game_id` fixtures
5. `test_player_removal.py` - `main_bot_helper` fixture (duplicate)
6. `test_waitlist_promotion.py` - `main_bot_helper` fixture (duplicate)
7. `test_game_authorization.py` - `template_id` fixture
8. Others with similar patterns

## Key Discoveries

### Shared Fixtures (tests/conftest.py)
**Comprehensive factory fixtures implemented:**
- `test_timeouts()` - Timeout configuration (session scope)
- `admin_db_url_sync`, `admin_db_url`, `app_db_url`, `bot_db_url` - Database URLs (session scope)
- `admin_db_sync`, `admin_db`, `app_db`, `bot_db` - Database sessions (function scope)
- `redis_client`, `redis_client_async` - Redis clients
- `seed_redis_cache` - Redis cache seeding factory
- `create_guild`, `create_channel`, `create_user`, `create_template`, `create_game` - Factory fixtures
- `test_environment`, `test_game_environment` - Composite fixtures
- `create_authenticated_client` - HTTP client factory

### Integration Test Duplicates Found

#### 1. Database Session Fixtures (DUPLICATED)
**Location:** `test_rls_bot_bypass.py` and `test_rls_api_enforcement.py`

```python
# test_rls_bot_bypass.py (lines 48-75)
@pytest.fixture
async def bot_db_session():
    """Create database session using gamebot_bot user (bot/daemon user with BYPASSRLS)."""
    raw_url = os.getenv("BOT_DATABASE_URL")
    if not raw_url:
        pytest.skip("BOT_DATABASE_URL not set")

    bot_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    bot_engine = create_async_engine(bot_url, echo=False)
    bot_session_factory = async_sessionmaker(
        bot_engine, class_=AsyncSession, expire_on_commit=False,
        autocommit=False, autoflush=False
    )

    async with bot_session_factory() as session:
        yield session
        await session.rollback()

    await bot_engine.dispose()

# test_rls_api_enforcement.py (lines 47-73)
@pytest.fixture
async def app_db_session():
    """Create database session using gamebot_app user (API user with RLS enforced)."""
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        pytest.skip("DATABASE_URL not set")

    app_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    app_engine = create_async_engine(app_url, echo=False)
    app_session_factory = async_sessionmaker(
        app_engine, class_=AsyncSession, expire_on_commit=False,
        autocommit=False, autoflush=False
    )

    async with app_session_factory() as session:
        yield session
        await session.rollback()

    await app_engine.dispose()
```

**Duplicates:** `bot_db` and `app_db` fixtures in `tests/conftest.py`
**Action Required:** Remove local fixtures, use shared fixtures from `tests/conftest.py`

#### 2. Daemon-Specific Queue Cleanup Fixtures
**Location:** `test_notification_daemon.py` and `test_status_transitions.py`

```python
# test_notification_daemon.py (lines 40-50)
@pytest.fixture
def clean_notification_schedule(rabbitmq_channel):
    """Clean RabbitMQ queue before and after test, with daemon processing time."""
    time.sleep(0.5)  # Let daemon process any remaining notifications
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)
    yield
    time.sleep(0.5)  # Let daemon process cleanup
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

# test_status_transitions.py (lines 40-47)
@pytest.fixture
def purge_bot_events_queue(rabbitmq_channel):
    """Purge bot_events queue before and after test to prevent cross-test pollution."""
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)
    yield
    time.sleep(0.5)  # Let daemon process any remaining messages
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)
```

**Status:** TEST-SPECIFIC - Not duplicated, appropriate for test-specific cleanup needs
**Action Required:** Keep as-is (test-specific behavior)

#### 3. Infrastructure Test Fixtures
**Location:** `test_rabbitmq_infrastructure.py`, `test_database_infrastructure.py`, `test_database_users.py`

```python
# test_rabbitmq_infrastructure.py (lines 38-74)
@pytest.fixture(scope="module")
def rabbitmq_connection():
    """Create RabbitMQ connection for testing."""
    # Custom implementation for infrastructure testing
    pass

@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create RabbitMQ channel for testing."""
    # Custom implementation with queue purging
    pass

# test_database_infrastructure.py (lines 38-64)
@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment, converting asyncpg to psycopg2 for sync tests."""
    # Custom implementation using ADMIN_DATABASE_URL
    pass

@pytest.fixture(scope="module")
def db_engine(db_url):
    """Create database engine for testing."""
    pass

@pytest.fixture
def db_session(db_engine):
    """Create database session for testing."""
    pass

# test_database_users.py (lines 34-44)
@pytest.fixture
def postgres_connection():
    """Create connection to PostgreSQL as superuser for verification."""
    # Direct psycopg2 connection for verifying user privileges
    pass
```

**Status:** INFRASTRUCTURE-SPECIFIC - Different purpose than shared fixtures
**Analysis:**
- These fixtures test the infrastructure itself (RabbitMQ setup, database schema, user privileges)
- They intentionally create connections with different configurations than production fixtures
- They use module scope for performance in infrastructure verification tests
**Action Required:** Keep as-is (infrastructure testing fixtures, not duplicates)

### E2E Test Duplicates Found

#### 4. Main Bot Helper Fixture (HEAVILY DUPLICATED)
**Location:** Duplicated in **at least 4 files**
- `test_join_notification.py` (lines 56-62)
- `test_game_reminder.py` (lines 58-64)
- `test_player_removal.py` (lines 56-62)
- `test_waitlist_promotion.py` (lines 34-40)

```python
@pytest.fixture
async def main_bot_helper(discord_main_bot_token):
    """Create Discord helper for main bot (sends notifications)."""
    helper = DiscordTestHelper(discord_main_bot_token)
    await helper.connect()
    yield helper
    await helper.disconnect()
```

**Duplication Count:** 4+ instances (exact same implementation)
**Action Required:** Move to `tests/e2e/conftest.py` or `tests/conftest.py`
**Impact:** High - Used in multiple e2e tests, straightforward consolidation

#### 5. Guild/Template/Game ID Fetching Fixtures (DUPLICATED PATTERN)
**Location:** Multiple e2e test files

```python
# test_guild_routes_e2e.py (lines 37-60)
@pytest.fixture
async def guild_a_db_id(admin_db, discord_guild_id):
    """Get Guild A database UUID (User A's guild)."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Guild A {discord_guild_id} not found in database"
    return row[0]

@pytest.fixture
async def guild_b_db_id(admin_db, discord_guild_b_id):
    """Get Guild B database UUID (User B's guild)."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_b_id},
    )
    row = result.fetchone()
    assert row, f"Guild B {discord_guild_b_id} not found in database"
    return row[0]

# test_guild_isolation_e2e.py (lines 38-85)
@pytest.fixture
async def guild_a_template_id(admin_db, discord_guild_id, discord_channel_id, synced_guild):
    """Get default template ID for Guild A."""
    # Get Guild A database ID
    guild_result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    # ... fetch template
    pass

@pytest.fixture
async def guild_b_template_id(admin_db, discord_guild_b_id, synced_guild_b):
    """Get default template ID for Guild B."""
    # Get Guild B database ID (DUPLICATE PATTERN)
    guild_result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_b_id},
    )
    # ... fetch template
    pass

@pytest.fixture
async def guild_a_game_id(admin_db, authenticated_admin_client, guild_a_template_id):
    """Create a game in Guild A for isolation testing."""
    # Create game via API
    # Wait for game to exist in database
    pass

@pytest.fixture
async def guild_b_game_id(admin_db, authenticated_client_b, guild_b_template_id):
    """Create a game in Guild B for isolation testing."""
    # Create game via API
    # Wait for game to exist in database
    pass

# test_game_authorization.py (lines 36-70)
@pytest.fixture
async def template_id(admin_db, discord_guild_id, discord_channel_id, synced_guild):
    """Create test template for E2E guild with no role restrictions."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    # ... create template via ORM
    pass
```

**Pattern:** Fetch database UUIDs by Discord IDs, repeated across multiple test files
**Duplication Count:** 6+ fixtures following same pattern
**Action Required:** Not applicable - E2E tests intentionally use real Discord IDs and fetch database IDs inline
**Rationale from Research Document:**
- E2E tests verify real Discord/database integration
- Inline ID fetching ensures tests verify data was actually synced from Discord
- Factory fixtures would bypass the sync verification that e2e tests are designed to validate

### Fixtures in tests/integration/conftest.py (Remaining)

```python
# tests/integration/conftest.py - 106 lines
@pytest.fixture(scope="module")
def rabbitmq_url():
    """Get RabbitMQ URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

@pytest.fixture
def rabbitmq_connection(rabbitmq_url):
    """Create RabbitMQ connection for test setup/assertions."""
    pass

@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create RabbitMQ channel for test operations."""
    pass

# Helper functions (not fixtures)
def get_queue_message_count(channel, queue_name): pass
def consume_one_message(channel, queue_name, timeout=5): pass
def purge_queue(channel, queue_name): pass

@pytest.fixture(autouse=True, scope="function")
async def cleanup_guild_context():
    """Ensure guild context is cleared before and after each test."""
    pass

@pytest.fixture(autouse=True, scope="function")
async def cleanup_db_engine():
    """Dispose database engine after each test to prevent event loop issues."""
    pass
```

**Status:** INTEGRATION-SPECIFIC - RabbitMQ and cleanup utilities
**Action Required:** Keep as-is (integration test infrastructure)

### Fixtures in tests/e2e/conftest.py (E2E-Specific)

```python
# tests/e2e/conftest.py - 302 lines
# Helper functions (not fixtures)
async def wait_for_db_condition(...): pass
async def wait_for_game_message_id(...): pass

# Discord credential fixtures (session scope)
@pytest.fixture(scope="session")
def discord_token(): pass

@pytest.fixture(scope="session")
def discord_main_bot_token(): pass

@pytest.fixture(scope="session")
def discord_guild_id(): pass

@pytest.fixture(scope="session")
def discord_channel_id(): pass

@pytest.fixture(scope="session")
def discord_user_id(): pass

@pytest.fixture(scope="session")
def discord_guild_b_id(): pass

@pytest.fixture(scope="session")
def discord_channel_b_id(): pass

@pytest.fixture(scope="session")
def discord_user_b_id(): pass

@pytest.fixture(scope="session")
def discord_user_b_token(): pass

# E2E helper fixtures
@pytest.fixture
async def discord_helper(discord_token): pass

@pytest.fixture(scope="session")
def bot_discord_id(discord_token): pass

@pytest.fixture(scope="function")
async def authenticated_admin_client(...): pass

@pytest.fixture(scope="function")
async def synced_guild(...): pass

@pytest.fixture(scope="function")
async def synced_guild_b(...): pass

@pytest.fixture(scope="function")
async def authenticated_client_b(...): pass
```

**Status:** E2E-SPECIFIC - Discord credentials and test environment setup
**Action Required:** Keep as-is (e2e test infrastructure)

## Remaining Duplication Summary

### CONFIRMED DUPLICATES (Action Required)

#### Integration Tests
1. **`bot_db_session` fixture** in `test_rls_bot_bypass.py`
   - **Action:** Remove, use `bot_db` from `tests/conftest.py`
   - **Impact:** 1 file, ~30 lines removed
   - **Risk:** Low - exact duplicate of shared fixture

2. **`app_db_session` fixture** in `test_rls_api_enforcement.py`
   - **Action:** Remove, use `app_db` from `tests/conftest.py`
   - **Impact:** 1 file, ~30 lines removed
   - **Risk:** Low - exact duplicate of shared fixture

#### E2E Tests
3. **`main_bot_helper` fixture** duplicated in 4+ files
   - **Action:** Move to `tests/e2e/conftest.py`
   - **Files:** `test_join_notification.py`, `test_game_reminder.py`, `test_player_removal.py`, `test_waitlist_promotion.py`
   - **Impact:** 4 files, ~30 lines removed (net ~20 line reduction)
   - **Risk:** Low - trivial fixture, exact duplicates

### NOT DUPLICATES (Keep As-Is)

#### Infrastructure Test Fixtures
- `test_rabbitmq_infrastructure.py`: `rabbitmq_connection`, `rabbitmq_channel` - Test infrastructure itself
- `test_database_infrastructure.py`: `db_url`, `db_engine`, `db_session` - Test database schema/tables
- `test_database_users.py`: `postgres_connection` - Test user privileges directly

**Rationale:** These fixtures test the infrastructure components themselves, not application logic

#### Test-Specific Fixtures
- `test_notification_daemon.py`: `clean_notification_schedule` - Daemon-specific cleanup timing
- `test_status_transitions.py`: `purge_bot_events_queue` - Daemon-specific cleanup timing

**Rationale:** Timing and cleanup behavior specific to daemon testing

#### E2E ID Fetching Fixtures
- `test_guild_routes_e2e.py`: `guild_a_db_id`, `guild_b_db_id`
- `test_guild_isolation_e2e.py`: `guild_a_template_id`, `guild_b_template_id`, `guild_a_game_id`, `guild_b_game_id`
- `test_game_authorization.py`: `template_id`

**Rationale:** E2E tests verify real Discord/database integration; inline ID fetching ensures sync validation

## Recommended Approach

### Phase 1: Clean Up Integration Test Duplicates (PRIORITY)

**Task 1.1:** Consolidate `bot_db_session` in `test_rls_bot_bypass.py`
```python
# REMOVE local fixture (lines 48-75)
@pytest.fixture
async def bot_db_session(): ...

# UPDATE test to use shared fixture
async def test_bot_queries_bypass_rls_see_all_guilds(
    admin_db, bot_db, create_guild, create_channel, create_user, create_game
):  # Change bot_db_session → bot_db
    # Test body unchanged
    pass
```

**Task 1.2:** Consolidate `app_db_session` in `test_rls_api_enforcement.py`
```python
# REMOVE local fixture (lines 47-73)
@pytest.fixture
async def app_db_session(): ...

# UPDATE test to use shared fixture
async def test_api_queries_filtered_by_rls_with_guild_context(
    admin_db, app_db, create_guild, create_channel, create_user, create_game
):  # Change app_db_session → app_db
    # Test body unchanged
    pass
```

### Phase 2: Clean Up E2E Test Duplicates (LOWER PRIORITY)

**Task 2.1:** Move `main_bot_helper` to `tests/e2e/conftest.py`
```python
# ADD to tests/e2e/conftest.py
@pytest.fixture
async def main_bot_helper(discord_main_bot_token):
    """Create Discord helper for main bot (sends notifications)."""
    helper = DiscordTestHelper(discord_main_bot_token)
    await helper.connect()
    yield helper
    await helper.disconnect()

# REMOVE from:
# - test_join_notification.py (lines 56-62)
# - test_game_reminder.py (lines 58-64)
# - test_player_removal.py (lines 56-62)
# - test_waitlist_promotion.py (lines 34-40)
```

## Implementation Guidance

### Objectives
1. Remove 2 duplicate database session fixtures from integration tests
2. Consolidate `main_bot_helper` fixture in e2e tests
3. Verify all tests still pass after consolidation

### Key Tasks
1. **Integration Tests:** Replace `bot_db_session` and `app_db_session` with shared fixtures
2. **E2E Tests:** Move `main_bot_helper` to `tests/e2e/conftest.py`
3. **Validation:** Run full test suite to verify no regressions

### Dependencies
- Shared fixtures in `tests/conftest.py` already implemented
- No new fixtures need to be created
- Only removal and import changes required

### Success Criteria
- All integration tests pass with shared `bot_db` and `app_db` fixtures
- All e2e tests pass with shared `main_bot_helper` fixture
- Net reduction of ~80-100 lines of duplicate fixture code
- No new fixture implementations required

## Complete Fixture Inventory

### tests/conftest.py (SHARED - 861 lines)
✅ Comprehensive factory fixtures
✅ Database session fixtures for all user types
✅ Redis client and cache seeding
✅ Composite fixtures for common patterns
✅ HTTP client factories

### tests/integration/conftest.py (INTEGRATION-SPECIFIC - 106 lines)
✅ RabbitMQ connection fixtures
✅ Cleanup autouse fixtures
✅ Helper functions (not fixtures)

### tests/e2e/conftest.py (E2E-SPECIFIC - 302 lines)
✅ Discord credential fixtures (session scope)
✅ E2E helper fixtures (discord_helper, bot_discord_id)
✅ Authenticated client fixtures
✅ Guild sync fixtures
✅ Helper functions (wait_for_db_condition, wait_for_game_message_id)
⚠️ **MISSING:** `main_bot_helper` (needs to be added)

### Individual Test Files
✅ Most consolidated to use shared fixtures
⚠️ **2 integration test files** have duplicate database session fixtures
⚠️ **4 e2e test files** have duplicate `main_bot_helper` fixture

## Conclusion

The consolidation effort was **largely successful** but missed:
1. **2 duplicate database session fixtures** in RLS tests (integration)
2. **1 duplicate helper fixture** across 4 e2e test files

These are **straightforward to fix** - simple removal and import changes.

**Estimated effort:** 15-30 minutes total
**Risk level:** Low (exact duplicates of shared fixtures)
**Test impact:** None (tests use identical functionality)
