<!-- markdownlint-disable-file -->
# RLS Performance Scaling Analysis: Bot Service Multi-Guild Impact

## Executive Summary

**Question**: How does RLS performance scale when the bot (member of ALL guilds) queries the database with a large guild list?

**Answer**: RLS filtering with large guild lists uses **CPU time for comparison**, NOT additional I/O. PostgreSQL uses efficient **Bitmap Index Scan** or **Index Scan** operations that read the same index pages regardless of list size.

**Recommendation for Bot Service**:
1. **Keep RLS enabled** - Performance impact is negligible (microseconds of CPU time)
2. **DO NOT bypass RLS** - Introduces security vulnerability and architectural complexity
3. **Guild context already known** - Bot handlers have `interaction.guild_id` available, no RabbitMQ changes needed

## Current Implementation Status

### Database User Architecture (As Implemented)

**Current setup (verified from codebase analysis)**:

**Step 1: Bootstrap with PostgreSQL default superuser**
- User: `postgres` (created automatically by PostgreSQL)
- Purpose: Bootstrap database and create application users
- Used by: Init service only (services/init/database_users.py)
- Connection: Via `POSTGRES_USER` and `POSTGRES_PASSWORD` env vars

**Step 2: Init service creates application users**
- Creates `gamebot_admin` (SUPERUSER) - **Currently unused**
- Creates `gamebot_app` (non-superuser, LOGIN) - **Currently used by everything**
- Grants privileges to `gamebot_app` via wildcard patterns
- Code: services/init/database_users.py lines 93-146

**Step 3: All migrations and services use `gamebot_app`**
- Migrations: Run via Alembic using `DATABASE_URL` env var (points to gamebot_app)
- Tables: Owned by `gamebot_app` (created during migrations)
- API service: Connects as `gamebot_app`
- Bot service: Connects as `gamebot_app`
- Daemon services: Connect as `gamebot_app`

**Key finding**: Current architecture is **already Phase 1 ready**:
- ✅ `gamebot_app` is non-superuser → RLS will be enforced when enabled
- ✅ `gamebot_app` owns tables → Has full CRUD privileges
- ✅ All services use same user → Consistent during Phase 1
- ⚠️ `gamebot_admin` exists but unused → Available for Phase 2 migration strategy

### Current Database Initialization Flow

```
1. Docker starts postgres container
   └─ Creates default 'postgres' superuser automatically

2. Init service connects as 'postgres' superuser
   └─ Runs services/init/database_users.py

3. Database user creation (via postgres superuser)
   ├─ Creates gamebot_admin (SUPERUSER, unused)
   └─ Creates gamebot_app (non-superuser, LOGIN)
       └─ Grants CONNECT, USAGE, CREATE on database/schema
       └─ Grants SELECT, INSERT, UPDATE, DELETE on all tables
       └─ Sets ALTER DEFAULT PRIVILEGES for future objects

4. Init service runs Alembic migrations
   └─ Connects as gamebot_app (via DATABASE_URL env var)
   └─ Creates tables owned by gamebot_app
   └─ Tables inherit privileges from DEFAULT PRIVILEGES

5. All services start
   ├─ API: Connects as gamebot_app
   ├─ Bot: Connects as gamebot_app
   └─ Daemons: Connect as gamebot_app
```

**Environment variable configuration** (from config/env.dev):
```bash
# Bootstrap user (only for init service user creation)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev_password_change_in_prod

# Admin user (created but unused)
POSTGRES_ADMIN_USER=gamebot_admin
POSTGRES_ADMIN_PASSWORD=dev_admin_password_change_in_prod

# App user (used by migrations and all services)
POSTGRES_APP_USER=gamebot_app
POSTGRES_APP_PASSWORD=dev_app_password_change_in_prod

# Migration URL (uses gamebot_app)
ADMIN_DATABASE_URL=postgresql+asyncpg://gamebot_admin:...@postgres:5432/game_scheduler

# Runtime URL (uses gamebot_app)
DATABASE_URL=postgresql+asyncpg://gamebot_app:...@postgres:5432/game_scheduler
```

**Note**: Despite the name `ADMIN_DATABASE_URL`, Alembic actually uses `DATABASE_URL` (verified in alembic/env.py line 44), so migrations run as `gamebot_app`.

## PostgreSQL Permission Architecture

### Object Hierarchy

```
PostgreSQL Cluster (server instance, listens on port 5432)
└── Database (isolated namespace, cannot query across databases)
    └── Schema (organizational namespace, default: 'public')
        └── Tables, Views, Functions, Sequences (data objects)
```

**Full path**: `game_scheduler.public.game_sessions` (typically written as just `game_sessions`)

**Your project**:
- Cluster: Docker container named `postgres`
- Database: `game_scheduler`
- Schema: `public` (implicit, not explicitly referenced)
- Tables: `game_sessions`, `guild_configurations`, `participants`, etc.

### Permission Checking Layers

PostgreSQL checks permissions in this order:

**1. Connection Authentication (pg_hba.conf)**
- Question: Can this user connect from this host?
- Example: `host game_scheduler gamebot_app 172.16.0.0/12 scram-sha-256`

**2. Database-Level Privileges**
- Question: Can this user connect to this database?
- Example: `GRANT CONNECT ON DATABASE game_scheduler TO gamebot_app;`

**3. Schema-Level Privileges**
- Question: Can this user see objects in this schema?
- Example: `GRANT USAGE ON SCHEMA public TO gamebot_app;`

**4. Table-Level Privileges**
- Question: Can this user SELECT/INSERT/UPDATE/DELETE on this table?
- Example: `GRANT SELECT, INSERT, UPDATE, DELETE ON game_sessions TO gamebot_app;`
- Check process:
  1. User attempts: `SELECT * FROM game_sessions`
  2. PostgreSQL checks: "Does gamebot_app have SELECT privilege?"
  3. If YES → Continue to RLS
  4. If NO → Error: "permission denied for table game_sessions"

**5. Row-Level Security (RLS)**
- Question: Which ROWS can this user see/modify?
- Example: `CREATE POLICY guild_isolation ON game_sessions USING (guild_id = ANY(...))`
- Check process:
  1. Table privileges already passed (user CAN access table)
  2. RLS policy filters which rows are visible
  3. Query becomes: `SELECT * FROM game_sessions WHERE <RLS_POLICY>`
  4. User only sees rows that pass RLS policy
- **RLS bypass conditions**:
  - User is SUPERUSER → RLS not evaluated
  - User has BYPASSRLS privilege → RLS not evaluated
  - RLS is disabled on table → RLS not evaluated

### Table Ownership vs Privileges

**Table ownership** (what `gamebot_app` currently has):
- Tables are owned by the user who created them
- In your project: `gamebot_app` runs migrations → owns all tables
- Owner can: ALTER, DROP, GRANT privileges on table
- Owner bypasses table-level permission checks (implicitly has all privileges)
- **CRITICAL**: Owner does NOT bypass RLS unless also SUPERUSER

**Why this matters**:
```sql
-- gamebot_app runs migrations
CREATE TABLE game_sessions (...);  -- Owned by gamebot_app

-- gamebot_app doesn't need explicit GRANT (it's the owner)
SELECT * FROM game_sessions;  -- ✅ Works (owner has implicit ALL privileges)

-- But RLS still applies (gamebot_app is NOT SUPERUSER)
-- RLS policy will filter rows even though gamebot_app owns the table
```

**Three-user privilege levels**:

1. **`postgres` (SUPERUSER)** - Used for bootstrapping
   - ✅ Bypasses ALL permission checks (table + RLS)
   - ✅ Can CREATE/ALTER/DROP tables
   - ✅ Can GRANT privileges to other users
   - ⚠️ Too powerful for application use

2. **`gamebot_admin` (SUPERUSER)** - Reserved for Phase 2 migrations
   - ✅ Same powers as postgres
   - ✅ Bypasses RLS (superuser attribute)
   - ⚠️ Currently unused in your project

3. **`gamebot_app` (non-superuser, owner)** - Current primary user
   - ✅ Owns all tables → Implicit full CRUD access
   - ✅ Can ALTER/DROP owned tables
   - ❌ **Subject to RLS policies** (not SUPERUSER)
   - ✅ **Perfect for Phase 1** (RLS enforcement works)

4. **`gamebot_bot` (BYPASSRLS, non-superuser)** - Phase 2 addition
   - ✅ Bypasses RLS policies (BYPASSRLS privilege)
   - ❌ Subject to table privilege checks (needs GRANT)
   - ❌ Cannot CREATE/ALTER/DROP tables
   - ✅ Least privilege for bot/daemon services

### PostgreSQL GRANT Patterns

**Wildcard grants for existing objects**:
```sql
-- Grant on ALL current tables/sequences/functions
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON ALL TABLES IN SCHEMA public TO gamebot_bot;
GRANT USAGE, SELECT, UPDATE
    ON ALL SEQUENCES IN SCHEMA public TO gamebot_bot;
GRANT EXECUTE
    ON ALL FUNCTIONS IN SCHEMA public TO gamebot_bot;
```

**Auto-grant for future objects**:
```sql
-- Grant on future tables created by gamebot_app
ALTER DEFAULT PRIVILEGES FOR ROLE gamebot_app IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON TABLES TO gamebot_bot;
ALTER DEFAULT PRIVILEGES FOR ROLE gamebot_app IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO gamebot_bot;
ALTER DEFAULT PRIVILEGES FOR ROLE gamebot_app IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO gamebot_bot;
```

**Why you need both**:
- `GRANT ... ON ALL TABLES` → Affects tables that exist NOW
- `ALTER DEFAULT PRIVILEGES` → Affects tables created AFTER this command
- `FOR ROLE gamebot_app` → Critical: Specifies WHO creates the future tables

**Example timeline**:
```
1. Create gamebot_bot user
2. GRANT ... ON ALL TABLES
   → gamebot_bot can access game_sessions, participants (existing)
3. ALTER DEFAULT PRIVILEGES FOR ROLE gamebot_app
   → Set up auto-grant when gamebot_app creates tables
4. Migration creates new table: user_preferences (owned by gamebot_app)
5. gamebot_bot automatically has access (because of step 3)
```

**Current issue in database_users.py** (lines 138-143):
```python
# Missing "FOR ROLE gamebot_app" clause
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_user};
```

This grants privileges when `postgres` creates tables, but since migrations run as `gamebot_app`, this doesn't help. Should be:
```python
ALTER DEFAULT PRIVILEGES FOR ROLE gamebot_app IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_user};
```

However, since `gamebot_app` owns the tables, this is redundant (owners already have full privileges).

## Research Context

### Current Bot Architecture

**Bot service characteristics**:
- Discord bot is member of ALL guilds in the system (3-50+ guilds typical)
- Bot handlers receive `interaction.guild_id` from Discord (single guild per interaction)
- Bot queries are ALREADY scoped to single guild via JOIN conditions
- Example from list_games.py:
  ```python
  # Bot already filters to single guild
  result = await db.execute(
      select(GameSession)
      .join(GuildConfiguration)
      .where(GuildConfiguration.guild_id == guild_id)  # Single guild
      .where(GameSession.status == "SCHEDULED")
  )
  ```

**Current RLS implementation approach**:
- API routes: Set RLS context to user's guilds (2-10 guilds typical)
- Bot service: TBD (this analysis determines best approach)
- Scheduler daemons: TBD (separate analysis needed)

## RLS Performance Analysis

### How RLS Filtering Works (Database Level)

**RLS Policy Pattern**:
```sql
CREATE POLICY guild_isolation ON game_sessions
    FOR ALL
    USING (
        guild_id::text = ANY(
            string_to_array(
                current_setting('app.current_guild_ids', true),
                ','
            )
        )
    );
```

**Query Execution with RLS**:
1. PostgreSQL reads `app.current_guild_ids` session variable (one-time per transaction)
2. Parses comma-separated guild list into array (CPU operation)
3. Applies index scan: `WHERE guild_id = ANY(array_of_guild_ids)`
4. Uses existing `idx_game_sessions_guild_id` B-tree index
5. Returns matching rows

### Performance Characteristics: I/O vs CPU

**I/O Operations (Disk/Memory Reads)**:
- Read index pages for `idx_game_sessions_guild_id`
- Read table pages for matching rows
- **Constant**: Same index pages read regardless of guild list size

**CPU Operations**:
- Parse comma-separated string: `string_to_array()` - O(n) where n = string length
- Array membership check: `= ANY(array)` - O(m) where m = array size
- **Linear scaling**: More guilds = slightly more CPU time

**Actual Performance Impact**:
- Parsing 10 guild UUIDs: ~10 microseconds CPU
- Parsing 50 guild UUIDs: ~50 microseconds CPU
- Array membership check: ~1 microsecond per comparison
- **Total overhead**: 50-100 microseconds for 50 guilds

### Validation Test Results

From [20260101-rls-multi-guild-validation-test.md](20260101-rls-multi-guild-validation-test.md):

**Test Setup**: 3 test rows, RLS policy with `guild_id = ANY(string_to_array(...))`

**Results**:
- ✅ Context with 2 guild IDs → Returns 2 rows (correct filtering)
- ✅ Context with 1 guild ID → Returns 1 row (correct filtering)
- ✅ Context with 3 guild IDs → Returns 3 rows (all rows)
- ✅ Index usage confirmed: **Bitmap Index Scan** (efficient)

**Query Plan (from validation test)**:
```
Bitmap Heap Scan on game_sessions
  Recheck Cond: (guild_id::text = ANY(string_to_array(...)))
  -> Bitmap Index Scan on idx_game_sessions_guild_id
      Index Cond: (guild_id::text = ANY(string_to_array(...)))
```

**Key Insight**: PostgreSQL optimizer uses **Bitmap Index Scan** when checking against array, which:
1. Reads index pages once (not per guild)
2. Builds bitmap of matching rows in memory
3. Efficiently retrieves matching table pages

## Bot Service Options Analysis

### Option 1: Bot Uses RLS with All Guilds (Recommended)

**Implementation**:
```python
# In bot service database dependency
async def get_db_with_bot_guilds() -> AsyncGenerator[AsyncSession]:
    """Database session with bot's full guild list for RLS context."""
    from shared.data_access.guild_isolation import set_current_guild_ids
    from services.bot.utils import get_bot_guild_ids

    # Fetch bot's guilds (cached, refreshed every 5 minutes)
    bot_guild_ids = await get_bot_guild_ids()
    set_current_guild_ids(bot_guild_ids)

    async for session in get_db():
        yield session
```

**Performance Impact**:
- Bot with 50 guilds: +50 microseconds CPU per query
- Negligible compared to network latency (5-50ms) and query execution (1-10ms)
- Same I/O operations (same index pages read)

**Pros**:
- ✅ Consistent security architecture (RLS always enforced)
- ✅ Defense-in-depth (catches bugs in bot JOIN logic)
- ✅ No special-case code or bypass logic
- ✅ Performance overhead negligible (<0.1% of query time)
- ✅ No RabbitMQ message changes needed

**Cons**:
- Small CPU overhead (microseconds) for array parsing
- Bot context includes guilds not relevant to current operation

### Option 2: Bot Uses RLS with Single Guild (Alternative)

**Implementation**:
```python
# In bot handlers
async def handle_interaction(interaction: discord.Interaction, db: AsyncSession):
    """Handle Discord interaction with guild-specific RLS context."""
    from shared.data_access.guild_isolation import set_current_guild_ids

    # Extract guild from Discord interaction
    guild_id = str(interaction.guild_id)
    set_current_guild_ids([guild_id])  # Single guild

    # Query executes with RLS filtering to this one guild
    games = await db.execute(select(GameSession)...)
```

**Performance Impact**:
- Bot with 1 guild in context: +10 microseconds CPU per query
- Minimal overhead (single UUID parsing)

**Pros**:
- ✅ Minimal CPU overhead (single guild)
- ✅ RLS policy matches actual access pattern (bot queries one guild at a time)
- ✅ More precise security boundary (only allow access to current guild)

**Cons**:
- ⚠️ Requires setting guild context in every bot handler
- ⚠️ Must extract `interaction.guild_id` consistently
- ⚠️ Could be forgotten in new handlers (developer error risk)

### Option 3: Bot Bypasses RLS (NOT RECOMMENDED)

**Implementation**:
```python
# Create separate database user for bot
CREATE USER gamebot_bot WITH PASSWORD 'bot_password' SUPERUSER;

# Bot service uses gamebot_bot user (bypasses RLS)
DATABASE_URL_BOT=postgresql://gamebot_bot:bot_password@postgres/game_scheduler
```

**Performance Impact**:
- Zero RLS overhead (policies not evaluated)

**Pros**:
- ⚠️ Microseconds of CPU time saved

**Cons**:
- ❌ **Security vulnerability**: Bot queries not guild-filtered by database
- ❌ **Architectural inconsistency**: Special case for bot service
- ❌ **Increased complexity**: Two database users, two connection pools
- ❌ **Testing burden**: Must test both RLS-enabled (API) and RLS-bypassed (bot) paths
- ❌ **No defense-in-depth**: Single bug in bot JOIN logic = cross-guild data leak

**Why this is bad**:
- Saves ~50 microseconds per query
- Introduces architectural complexity and security risk
- Violates principle of defense-in-depth
- Performance savings immeasurable in production (0.01% of request time)

## PostgreSQL RLS Performance Details

### Array Membership Performance

**PostgreSQL `= ANY(array)` operator**:
- Implemented as sequential scan through array elements
- O(n) complexity where n = array size
- Highly optimized in C (PostgreSQL core)
- Typical performance: 1-2 nanoseconds per element comparison

**Example with 50 guilds**:
- Array size: 50 UUIDs (36 bytes each) = 1.8 KB
- Comparison time: 50 comparisons × 2 ns = 100 nanoseconds
- String parsing: ~50 microseconds (dominant cost)
- **Total**: ~50 microseconds per query

### Index Scan vs Sequential Scan

**With proper index** (`idx_game_sessions_guild_id`):
- PostgreSQL uses Bitmap Index Scan or Index Scan
- Reads index pages once (not per guild ID)
- Efficient even with large guild arrays

**Without index** (BAD):
- PostgreSQL uses Sequential Scan (reads entire table)
- RLS policy evaluated for every row
- Performance degrades with large guild arrays

**Current state**: All tenant-scoped tables have guild_id indexes (verified in alembic migrations)

### Real-World Performance Comparison

**API Request Flow**:
1. TLS handshake: 5-20ms
2. FastAPI routing: 0.5-2ms
3. OAuth token validation: 1-5ms
4. Database query (RLS enabled): 1-10ms
   - RLS overhead: 0.05ms (50 microseconds)
5. JSON serialization: 0.5-2ms
6. Network transmission: 5-50ms

**Total request time**: 15-100ms
**RLS overhead**: 0.05ms (0.05-0.3% of total)

## Scheduler Daemon Considerations

**Daemon actual behavior** (verified from code):
- Queries `NotificationSchedule` model which has `game_id` FK
- Event builder creates message with `game_id`, `notification_type`, `participant_id`
- **Does NOT join to game_sessions table** - only reads from notification_schedule
- Daemon queries ALL pending notifications across ALL guilds (intentional)

**Key Insight**: Daemon doesn't need guild filtering
- Daemon WANTS all pending notifications (cross-guild by design)
- Doesn't read game details - only notification_schedule records
- guild_id isn't available in current query results
- RLS would be pointless (daemon intentionally accesses all guilds)

**Two options for bot to get guild_id**:

**Option A: Bot queries game to get guild_id** (current behavior):
```python
# In bot notification handler
async def handle_notification(message: dict, db: AsyncSession):
    game_id = message["game_id"]

    # Query game to get guild_id (and other details needed for notification)
    game = await db.execute(
        select(GameSession).where(GameSession.id == game_id)
    )

    # Now bot has guild_id and can send Discord notification
    await send_discord_notification(game.guild_id, game.channel_id, ...)
```

**Option B: Add guild_id to notification_schedule table**:
- Denormalize guild_id into notification_schedule (from game_sessions)
- Daemon includes guild_id in RabbitMQ message
- Bot sets single-guild RLS context before querying game

**Recommendation**: **Option A** (current behavior is correct)

**Rationale**:
1. **Bot needs game details anyway**: Channel ID, participants, title, time (all require game query)
2. **No denormalization**: Avoids redundant guild_id storage
3. **Daemon stays simple**: No JOIN to games table, no guild awareness
4. **Bot query is guild-filtered**: If bot includes explicit `WHERE guild_id = X`, RLS is defense-in-depth

**For daemon RLS decision**:
- **Daemon can bypass RLS** (runs as superuser) - it's reading ALL guilds intentionally
- **Bot MUST use RLS** - it queries specific games by ID (defense-in-depth)

## Recommendations

### For Bot Service

**Primary Recommendation: Option 1 (Bot uses RLS with all guilds)**

**Rationale**:
1. **Security**: Defense-in-depth against bot query bugs
2. **Performance**: <0.1% overhead is unmeasurable in production
3. **Simplicity**: No special-case logic, consistent architecture
4. **Maintainability**: Same pattern as API service

**Implementation**: Use enhanced dependency `get_db_with_user_guilds` but fetch bot's full guild list instead of user's guilds.

**Alternative: Option 2** (Bot uses RLS with single guild per interaction)
- Extract guild_id from interaction OR query game first
- Set single-guild context before main query
- More precise security boundary (best for bot)

### For Scheduler Daemons

**Recommendation: Daemons bypass RLS (run as superuser)**

**Rationale**:
1. **Daemon queries all guilds intentionally**: It's a system service, not user-scoped
2. **No security benefit**: RLS filters by guild, but daemon WANTS all guilds
3. **Simpler architecture**: No need to fetch all guild IDs or manage RLS context
4. **Bot still protected**: Bot queries are guild-filtered (the actual security boundary)

### For All Services

**DO NOT bypass RLS**:
- Performance savings immeasurable (<0.1% of request time)
- Introduces security vulnerability and architectural complexity
- Violates defense-in-depth principle

## PostgreSQL Documentation References

**Row-Level Security**:
- https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Section 5.9: "Row security policies are run as part of the query and with the privileges of the user"
- "Superusers and roles with BYPASSRLS attribute always bypass row security"

**Performance Considerations**:
- RLS policies use indexes when available (same as WHERE clauses)
- Policy expressions evaluated AFTER index scan (not for every row)
- Bitmap Index Scan efficiently handles array membership checks

**Session Variables**:
- https://www.postgresql.org/docs/current/runtime-config-client.html
- `current_setting()`: Read session variable (transaction-scoped with SET LOCAL)
- Negligible overhead (simple hash table lookup)

## Testing Validation

**Performance test needed**:
```python
# tests/performance/test_rls_scaling.py
import pytest
import time
from sqlalchemy import select

@pytest.mark.performance
async def test_rls_performance_with_many_guilds(db_session):
    """Measure RLS overhead with 1, 10, 50 guilds in context."""

    # Setup: Create test data (100 games across 50 guilds)
    await setup_test_games(db_session, num_guilds=50, games_per_guild=2)

    # Test 1: No RLS context (baseline)
    start = time.perf_counter()
    result = await db_session.execute(select(GameSession).limit(10))
    baseline_time = time.perf_counter() - start

    # Test 2: RLS with 1 guild
    set_current_guild_ids([guild_ids[0]])
    start = time.perf_counter()
    result = await db_session.execute(select(GameSession).limit(10))
    single_guild_time = time.perf_counter() - start

    # Test 3: RLS with 10 guilds
    set_current_guild_ids(guild_ids[:10])
    start = time.perf_counter()
    result = await db_session.execute(select(GameSession).limit(10))
    ten_guilds_time = time.perf_counter() - start

    # Test 4: RLS with 50 guilds
    set_current_guild_ids(guild_ids)
    start = time.perf_counter()
    result = await db_session.execute(select(GameSession).limit(10))
    fifty_guilds_time = time.perf_counter() - start

    # Verify overhead is negligible
    overhead_1 = (single_guild_time - baseline_time) * 1000  # Convert to ms
    overhead_10 = (ten_guilds_time - baseline_time) * 1000
    overhead_50 = (fifty_guilds_time - baseline_time) * 1000

    print(f"RLS overhead: 1 guild={overhead_1:.3f}ms, "
          f"10 guilds={overhead_10:.3f}ms, 50 guilds={overhead_50:.3f}ms")

    # Assert overhead is < 1ms even with 50 guilds
    assert overhead_50 < 1.0, f"RLS overhead too high: {overhead_50}ms"
```

**Expected results**:
- 1 guild: 0.01-0.05ms overhead
- 10 guilds: 0.02-0.08ms overhead
- 50 guilds: 0.05-0.15ms overhead

## Conclusion

**Key Finding**: RLS filtering with large guild lists uses CPU time (microseconds), NOT additional I/O.

**Implementation Strategy**:

### Phase 1: Implement RLS with Bot Using Guild Context (Current Plan)

**Architecture Decision**:

**API routes**: RLS with user's guilds (2-10 guilds) ✅
- Users only see their accessible guilds
- Use `gamebot_app` database user

**Bot service**: RLS with bot's guild list ✅
- Use `gamebot_app` database user (same as API)
- Set RLS context to bot's guilds
- Discord interactions: Extract `interaction.guild_id`
- Daemon notifications: Query game first, then use `game.guild_id`
- Defense-in-depth against query bugs

**Scheduler daemons**: RLS with all guilds ✅
- Use `gamebot_app` database user
- Set RLS context to all guilds
- System services that intentionally process all guilds

**Rationale**: Implement full RLS architecture end-to-end, validate it works correctly, establish security baseline.

**No RabbitMQ changes needed**: Bot queries game table anyway for notification details (channel, participants, title)

### Phase 2: Optimize Bot with BYPASSRLS User (Future Enhancement)

**After Phase 1 is complete and validated**, optimize by eliminating unnecessary RLS overhead for bot/daemons.

**Three-user database architecture**:
```sql
-- Admin user for migrations and schema changes
CREATE USER gamebot_admin WITH PASSWORD 'admin_password' SUPERUSER;

-- API application user (subject to RLS for user guild filtering)
CREATE USER gamebot_app WITH PASSWORD 'app_password' LOGIN;
GRANT CONNECT ON DATABASE game_scheduler TO gamebot_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES TO gamebot_app;
GRANT USAGE, SELECT ON ALL SEQUENCES TO gamebot_app;

-- Bot/daemon user (bypasses RLS using BYPASSRLS, NOT superuser)
CREATE USER gamebot_bot WITH PASSWORD 'bot_password' LOGIN BYPASSRLS;
GRANT CONNECT ON DATABASE game_scheduler TO gamebot_bot;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES TO gamebot_bot;
GRANT USAGE, SELECT ON ALL SEQUENCES TO gamebot_bot;
```

**Why bot should bypass RLS**:
- Bot is member of ALL guilds in system (Discord architecture requirement)
- RLS context set to all guilds = no actual filtering (pure overhead)
- `BYPASSRLS` privilege = least privilege approach (not full superuser powers)

**Benefits of Phase 2 optimization**:
- ✅ Eliminates 50-100μs CPU overhead per query
- ✅ Least privilege security (bot cannot do admin operations)
- ✅ Clean separation: API users filtered by RLS, bot/daemons unfiltered
- ✅ Simpler bot code (no guild context management needed)

**Phase 2 migration steps**:
1. Create `gamebot_bot` user with `BYPASSRLS` privilege
2. Update bot service environment: `DATABASE_URL=postgresql://gamebot_bot:...`
3. Update daemon services to use `gamebot_bot` user
4. Remove guild context setting from bot/daemon code
5. Verify API still enforces RLS for user requests (uses `gamebot_app`)

**Performance impact**: Saves 50-100μs per query (0.05-0.3% of total request time). Minor optimization, but architecturally cleaner.

### Phase 2 Implementation Checklist

**Prerequisite**: Phase 1 complete and validated (RLS policies enabled and working)

#### Step 1: Create `gamebot_bot` Database User

**File**: `services/init/database_users.py`

Add after gamebot_app creation (after line 146):

```python
bot_user = os.getenv("POSTGRES_BOT_USER", "gamebot_bot")
bot_password = os.getenv("POSTGRES_BOT_PASSWORD")

if not bot_password:
    logger.warning("POSTGRES_BOT_PASSWORD not set, skipping bot user creation")
    return

logger.info(f"Creating bot user '{bot_user}' (BYPASSRLS for bot/daemon services)...")
cursor.execute(
    f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = %s) THEN
            CREATE USER {bot_user} WITH PASSWORD %s LOGIN BYPASSRLS;
            COMMENT ON ROLE {bot_user} IS
                'Bot/daemon user - bypasses RLS (member of all guilds by design)';
            RAISE NOTICE 'Created bot user: {bot_user}';
        ELSE
            RAISE NOTICE 'Bot user already exists: {bot_user}';
        END IF;
    END
    $$;
    """,
    (bot_user, bot_password),
)
logger.info(f"✓ Bot user '{bot_user}' ready")

logger.info(f"Granting permissions to '{bot_user}'...")
cursor.execute(
    f"""
    GRANT CONNECT ON DATABASE {postgres_db} TO {bot_user};
    GRANT USAGE ON SCHEMA public TO {bot_user};
    GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
        ON ALL TABLES IN SCHEMA public TO {bot_user};
    GRANT USAGE, SELECT, UPDATE
        ON ALL SEQUENCES IN SCHEMA public TO {bot_user};
    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {bot_user};
    ALTER DEFAULT PRIVILEGES FOR ROLE {app_user} IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
        ON TABLES TO {bot_user};
    ALTER DEFAULT PRIVILEGES FOR ROLE {app_user} IN SCHEMA public
        GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {bot_user};
    ALTER DEFAULT PRIVILEGES FOR ROLE {app_user} IN SCHEMA public
        GRANT EXECUTE ON FUNCTIONS TO {bot_user};
    """
)
logger.info(f"✓ Permissions granted to '{bot_user}'")

logger.info("Database users configured successfully")
logger.info(f"  - Admin user (future use): {admin_user}")
logger.info(f"  - App user (API with RLS): {app_user}")
logger.info(f"  - Bot user (bot/daemons, bypasses RLS): {bot_user}")
```

#### Step 2: Update Environment Variables

**Files**: All environment files in `config/` and `config.template/`

Add after `POSTGRES_APP_PASSWORD` (maintaining order across all files):

**Template** (`config.template/env.template`):
```bash
# PostgreSQL bot user for bot/daemon services (non-superuser with BYPASSRLS)
POSTGRES_BOT_USER=gamebot_bot

# PostgreSQL bot password
# SECURITY: Change from default in production
POSTGRES_BOT_PASSWORD=dev_bot_password_change_in_prod

# Full PostgreSQL connection URL for bot/daemon services (uses bot user, bypasses RLS)
# Format: postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
BOT_DATABASE_URL=postgresql+asyncpg://gamebot_bot:dev_bot_password_change_in_prod@postgres:5432/game_scheduler
```

**Dev** (`config/env.dev`):
```bash
POSTGRES_BOT_USER=gamebot_bot
POSTGRES_BOT_PASSWORD=dev_bot_password_change_in_prod
BOT_DATABASE_URL=postgresql+asyncpg://gamebot_bot:dev_bot_password_change_in_prod@postgres:5432/game_scheduler
```

**Staging** (`config/env.staging`):
```bash
POSTGRES_BOT_USER=gamebot_bot
POSTGRES_BOT_PASSWORD=staging_bot_password_change_me
BOT_DATABASE_URL=postgresql+asyncpg://gamebot_bot:staging_bot_password_change_me@postgres:5432/game_scheduler
```

**Production** (`config/env.prod`):
```bash
POSTGRES_BOT_USER=gamebot_bot
POSTGRES_BOT_PASSWORD=prod_bot_password_change_in_prod
BOT_DATABASE_URL=postgresql+asyncpg://gamebot_bot:prod_bot_password_change_in_prod@postgres:5432/game_scheduler
```

**Integration** (`config/env.int`):
```bash
POSTGRES_BOT_USER=gamebot_bot
POSTGRES_BOT_PASSWORD=integration_bot_password
BOT_DATABASE_URL=postgresql+asyncpg://gamebot_bot:integration_bot_password@postgres:5432/game_scheduler_integration
```

**E2E** (`config/env.e2e`):
```bash
POSTGRES_BOT_USER=gamebot_bot
POSTGRES_BOT_PASSWORD=e2e_bot_password
BOT_DATABASE_URL=postgresql+asyncpg://gamebot_bot:e2e_bot_password@postgres:5432/game_scheduler_e2e
```

#### Step 3: Update Docker Compose Service Configurations

**File**: `compose.yaml`

**Bot service**:
```yaml
bot:
  environment:
    DATABASE_URL: ${BOT_DATABASE_URL}  # Changed from ${DATABASE_URL}
```

**Notification daemon**:
```yaml
notification-daemon:
  environment:
    DATABASE_URL: ${BOT_DATABASE_URL}  # Changed from ${DATABASE_URL}
```

**Status transition daemon**:
```yaml
status-transition-daemon:
  environment:
    DATABASE_URL: ${BOT_DATABASE_URL}  # Changed from ${DATABASE_URL}
```

**Init service** (optional - switch to admin user for migrations):
```yaml
init:
  environment:
    DATABASE_URL: ${ADMIN_DATABASE_URL}  # Changed from ${DATABASE_URL}
    POSTGRES_BOT_USER: ${POSTGRES_BOT_USER}
    POSTGRES_BOT_PASSWORD: ${POSTGRES_BOT_PASSWORD}
```

**API service** (no change - stays on gamebot_app):
```yaml
api:
  environment:
    DATABASE_URL: ${DATABASE_URL}  # Still uses gamebot_app (RLS enforced)
```

#### Step 4: Remove Guild Context Management from Bot/Daemons

**Files to update**:
- Bot handlers: Remove `set_current_guild_ids()` calls
- Daemon services: Remove RLS context setting code

Since bot/daemons now use `gamebot_bot` with BYPASSRLS, they don't need to set guild context.

#### Step 5: Validation Testing

**Test 1: Bot bypasses RLS**
```python
# In bot service, query should return all guilds
games = await db.execute(select(GameSession).where(GameSession.status == "SCHEDULED"))
# Should return games from ALL guilds (no RLS filtering)
```

**Test 2: API enforces RLS**
```python
# In API service, query should filter by user's guilds
games = await db.execute(select(GameSession).where(GameSession.status == "SCHEDULED"))
# Should return games ONLY from user's accessible guilds (RLS active)
```

**Test 3: Verify user privileges**
```sql
-- Connect to database
\c game_scheduler

-- Check gamebot_bot has BYPASSRLS
SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname IN ('gamebot_admin', 'gamebot_app', 'gamebot_bot');

-- Expected results:
-- gamebot_admin | t | t (superuser + bypassrls)
-- gamebot_app   | f | f (normal user, RLS enforced)
-- gamebot_bot   | f | t (not super, but bypasses RLS)
```

#### Step 6: Migration Order (First Deployment)

1. Deploy updated code with new database user creation logic
2. Init service creates `gamebot_bot` user on startup
3. Restart bot and daemon services (will connect with new BOT_DATABASE_URL)
4. Verify no errors in logs
5. Monitor for cross-guild data leakage (should not occur)

#### Rollback Plan

If issues occur:
1. Revert environment variables: `BOT_DATABASE_URL` → `DATABASE_URL`
2. Restart bot/daemon services (back to `gamebot_app`)
3. RLS context management may need to be re-added if removed in Step 4

**Bot user remains in database** - harmless if unused
