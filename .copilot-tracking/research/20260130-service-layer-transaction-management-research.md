<!-- markdownlint-disable-file -->
# Task Research Notes: Service Layer Transaction Management and Atomicity

## Research Executed

### File Analysis
- [services/api/services/guild_service.py](../../services/api/services/guild_service.py)
  - `create_guild_config()` commits immediately at line 54
  - `update_guild_config()` commits immediately at line 78
  - `sync_user_guilds()` calls `_create_guild_with_channels_and_template()` which orchestrates multi-step operation
  - No transaction boundary management - relies on nested commits

- [services/api/services/channel_service.py](../../services/api/services/channel_service.py)
  - `create_channel_config()` commits immediately at line 52
  - `update_channel_config()` commits immediately at line 77
  - Same premature commit pattern

- [services/api/services/template_service.py](../../services/api/services/template_service.py)
  - All CRUD operations (`create_template()`, `update_template()`, `delete_template()`, etc.) commit immediately
  - 6 separate commit calls found in the service

- [services/api/services/games.py](../../services/api/services/games.py)
  - `create_game()` commits at line 633
  - `update_game()` commits at line 1373
  - `add_participant()` commits at line 1445
  - `remove_participant()` commits at lines 1533, 1547, 1620
  - Multiple flush operations (lines 188, 288, 607, 888, 989, 1054) for ID generation
  - Total: 6 commits, 6 flushes in one service file

- [shared/database.py](../../shared/database.py)
  - `get_db()` FastAPI dependency handles commit/rollback at route boundary (lines 90-96)
  - Proper transaction lifecycle: yield session → commit on success → rollback on exception
  - `get_db_with_user_guilds()` follows same pattern (lines 137-143)
  - Architecture designed for route-level transaction management

- [services/api/routes/guilds.py](../../services/api/routes/guilds.py)
  - `sync_guilds()` endpoint at line 287
  - Receives `db` from `Depends(database.get_db)`
  - Calls `guild_service.sync_user_guilds(db, ...)`
  - Expects `get_db()` to commit at end of route handler
  - **Problem**: Service functions commit before route handler can establish transaction boundary

### Code Search Results
- `await db.commit()` pattern found in:
  - guild_service.py: 2 occurrences
  - channel_service.py: 2 occurrences
  - auth.py routes: 1 occurrence

- `await self.db.commit()` pattern found in:
  - template_service.py: 6 occurrences
  - games.py: 6 occurrences

- `await db.flush()` pattern found in:
  - games.py: 6 occurrences (used to generate IDs before commit)
  - notification_schedule.py: 1 occurrence
  - participant_resolver.py: 1 occurrence

- Test files verify commit behavior:
  - All service tests mock `db.commit` and assert it's called
  - Tests validate current (incorrect) behavior of immediate commits
  - 50+ test assertions checking `mock_db.commit.assert_awaited_once()`

### Incident Analysis
**Production Issue Discovered**: Guild sync operation on 2026-01-30 06:19:19

Database logs showed:
```
2026-01-30 06:19:19,251 - services.api.middleware.error_handler - ERROR - Database error:
Could not refresh instance '<GuildConfiguration at 0x71ede51d5fd0>'
```

Database state after failed sync:
- Guild configuration: **CREATED** (committed before failure)
- Channel configurations: **NOT CREATED** (operation failed)
- Game templates: **NOT CREATED** (depends on channels)

**Root Cause**: `create_guild_config()` committed immediately. When subsequent channel creation failed, guild couldn't be rolled back, leaving orphaned guild record.

### Project Conventions
- SQLAlchemy AsyncSession with async/await patterns
- FastAPI dependency injection for database sessions
- Service layer for business logic, route layer for HTTP concerns
- No explicit transaction management in service functions
- Relies on FastAPI route-level transaction handling

### Non-FastAPI Context Analysis
**Discord Bot Usage:**
- Bot uses `get_db_session()` which returns raw `AsyncSessionLocal()`
- Bot manages its own transactions: `async with get_db_session() as db: ... await db.commit()`
- Bot does NOT call API service layer functions with commits
- Bot implements participant operations directly (join/leave handlers)
- Pattern: `db.add(participant); await db.commit()` - bot controls transaction

**Scheduler Daemons:**
- Use synchronous `SyncSessionLocal()` from `shared.database`
- Operate independently of API service layer
- No calls to guild/channel/template/game service functions found

**Scripts:**
- `data_migration_create_default_templates.py` uses `get_db_session()`
- Manages own transaction lifecycle
- Does not call API service layer functions

**Conclusion**: Service layer functions with commits are **ONLY** called from FastAPI routes. Bot and daemons manage their own transactions and don't use these service functions.

## Key Discoveries

### Architectural Pattern Violation

**Current (Incorrect) Pattern:**
```python
# Service layer - commits immediately
async def create_guild_config(db: AsyncSession, guild_discord_id: str) -> GuildConfiguration:
    guild_config = GuildConfiguration(guild_id=guild_discord_id)
    db.add(guild_config)
    await db.commit()  # ⚠️ PREMATURE COMMIT
    await db.refresh(guild_config)
    return guild_config

# Orchestrator calls multiple services
async def sync_user_guilds(db: AsyncSession, ...):
    for guild_id in new_guild_ids:
        guild = await create_guild_config(db, guild_id)  # Commits here
        for channel in channels:
            await create_channel_config(db, guild.id, channel["id"])  # Commits here
            # If this fails, guild is already committed and can't be rolled back
```

**Expected (Correct) Pattern:**
```python
# Service layer - NO commits
async def create_guild_config(db: AsyncSession, guild_discord_id: str) -> GuildConfiguration:
    guild_config = GuildConfiguration(guild_id=guild_discord_id)
    db.add(guild_config)
    await db.flush()  # Only if need ID immediately
    return guild_config

# Route handler manages transaction
@router.post("/sync")
async def sync_guilds(db: AsyncSession = Depends(get_db)):
    # All service calls within one transaction
    result = await guild_service.sync_user_guilds(db, ...)
    # get_db() commits here on success, or rolls back on exception
    return result
```

### Impact Analysis

**Affected Operations** (from grep analysis):
1. **Guild Operations** (2 commits)
   - Creating new guild configuration
   - Updating guild settings

2. **Channel Operations** (2 commits)
   - Creating channel configuration
   - Updating channel settings

3. **Template Operations** (6 commits)
   - Creating templates
   - Updating templates
   - Deleting templates
   - Reordering templates
   - Setting default template

4. **Game Operations** (6 commits + 6 flushes)
   - Creating games
   - Updating games
   - Adding participants
   - Removing participants
   - Participant promotions

5. **Auth Operations** (1 commit)
   - User creation in auth flow

**Data Integrity Risks:**
- Orphaned guild records without channels or templates
- Games with inconsistent participant state
- Failed participant removals leaving schedules/notifications
- Template operations failing mid-update
- Multi-step game state changes partially applied

### SQLAlchemy Best Practices Research

**Session Lifecycle Management:**
From SQLAlchemy 2.0 async documentation:
- Session should be created at highest scope possible (request boundary)
- Commit/rollback at same scope where session was created
- Service/business logic should manipulate session but not commit
- Use `flush()` when need generated IDs before commit
- Avoid nested transactions unless explicitly using savepoints

**FastAPI + SQLAlchemy Pattern:**
```python
# Dependency provides session with transaction boundary
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit at route boundary
        except Exception:
            await session.rollback()  # Rollback on any error
            raise
        finally:
            await session.close()

# Route uses dependency
@app.post("/items")
async def create_item(db: AsyncSession = Depends(get_db)):
    item = await item_service.create(db, ...)  # No commit in service
    # Commit happens here when route returns successfully
    return item
```

### Flush vs Commit

**Current Usage:**
- `flush()` used 9 times across codebase
- Correctly used to generate IDs before needing them
- Example: Creating game, then immediately creating participants with game_id FK

**Purpose:**
- `flush()`: Sends pending changes to database, generates IDs, **maintains transaction**
- `commit()`: Finalizes transaction, **releases locks, makes changes permanent**

Service functions should use `flush()` when need IDs, never `commit()`.

### Row-Level Security (RLS) and Transaction Boundaries

**Critical PostgreSQL RLS Issue Discovered**: 2026-01-30 debugging session revealed RLS-specific failure mode not previously documented.

**How RLS Context Works:**
- RLS context set using `SET LOCAL app.current_guild_ids = '...'` at transaction start
- Middleware sets context based on user's guild membership
- All queries within transaction respect RLS policies
- `SET LOCAL` is **transaction-scoped** - automatically reset when transaction ends

**The RLS-Commit Problem:**
```python
# Step 1: Middleware sets RLS context
await db.execute(text("SET LOCAL app.current_guild_ids = '123,456'"))

# Step 2: Service creates guild
guild_config = GuildConfiguration(guild_id='789')
db.add(guild_config)
await db.commit()  # ⚠️ TRANSACTION ENDS - RLS CONTEXT LOST

# Step 3: Refresh needs server-generated defaults
await db.refresh(guild_config)  # ❌ FAILS: "Could not refresh instance"
# New transaction has NO RLS context, SELECT blocked by policy
```

**Why Server-Generated Values Matter:**
Models have `server_default` values that must be fetched after insert:
- `created_at`: `server_default=func.now()`
- `updated_at`: `server_default=func.now()`
- `require_host_role`: `server_default=text("false")`

Without `refresh()`, these fields remain `None` in the Python object despite being set in database.

**Cascade of RLS Failures:**
1. **Guild Insert**: Needs RLS context with Discord snowflake ID (guild_id field)
2. **Guild Commit**: Transaction ends, RLS context lost
3. **Guild Refresh**: SELECT query fails - no RLS context for newly created row
4. **Channel Insert**: Needs RLS context with guild's database UUID
5. **Template Insert**: Fails because parent guild UUID not in RLS context

**Attempted Workarounds (All Problematic):**
```python
# Workaround 1: Re-set context after each commit
await db.commit()
await db.execute(text(f"SET LOCAL app.current_guild_ids = '{guild_id}'"))
await db.refresh(guild_config)  # Works but hacky

# Problem: Must re-set context after EVERY commit in call chain
# - create_guild_config() commits → re-set
# - create_channel_config() commits → re-set (needs guild UUID now!)
# - create_default_template() commits → re-set (needs both IDs!)
```

**Why Flush() Solves RLS Issues:**
```python
# Single transaction start to finish
await db.execute(text("SET LOCAL app.current_guild_ids = '123,456,789'"))

guild_config = GuildConfiguration(guild_id='789')
db.add(guild_config)
await db.flush()  # ✓ Sends INSERT, generates ID, KEEPS TRANSACTION OPEN
# RLS context still active

channel_config = ChannelConfiguration(guild_id=guild_config.id)
db.add(channel_config)
await db.flush()  # ✓ Still in same transaction
# RLS context still active

template = GameTemplate(guild_id=guild_config.id, channel_id=channel_config.id)
db.add(template)
await db.flush()  # ✓ Still in same transaction

# All objects in session, all server defaults available
# Only ONE RLS context setup needed
# Route-level get_db() commits everything atomically
```

**RLS Policy Verification:**
```sql
-- guild_configurations policy checks BOTH id and guild_id
CREATE POLICY guild_isolation_configurations ON guild_configurations
FOR ALL USING (
    id::text = ANY(string_to_array(current_setting('app.current_guild_ids', true), ','))
    OR
    guild_id::text = ANY(string_to_array(current_setting('app.current_guild_ids', true), ','))
);

-- game_templates policy checks guild_id (database UUID FK)
CREATE POLICY guild_isolation_templates ON game_templates
FOR ALL USING (
    guild_id::text = ANY(string_to_array(current_setting('app.current_guild_ids', true), ','))
);
```

**Key Insight**: RLS policies check different ID types (Discord snowflakes vs database UUIDs). Premature commits lose context before operations complete. Single transaction with flush() maintains context for entire operation chain.

**Production Impact**: Without fixing commits, every guild sync on fresh database fails. RLS prevents orphaned data but blocks legitimate operations when transaction boundaries are incorrect.

### Test Suite Implications

**Current Tests Verify Incorrect Behavior:**
```python
# From test_guild_service.py
mock_db.commit = AsyncMock()
result = await create_guild_config(mock_db, guild_id)
mock_db.commit.assert_awaited_once()  # Test verifies the bug
```

**Impact of Fix:**
- 50+ unit tests will need updates
- Tests should verify NO commits in service layer
- Integration tests should verify transaction atomicity
- Need new tests for rollback scenarios
- Add RLS context verification in tests

## Recommended Approach

### Phase 1: Service Layer Refactoring

**Priority 1 - High Risk Operations:**
1. Guild sync operations (create_guild_config, create_channel_config, create_default_template)
2. Game creation with participants (atomic game + participants + schedules)
3. Participant operations with promotions (remove + promote + notify)

**Changes Required:**
1. Remove all `await db.commit()` from service functions
2. Remove all `await self.db.commit()` from service classes
3. Keep `await db.flush()` where needed for ID generation
4. Add transaction documentation to service function docstrings

**Example Refactor:**
```python
# BEFORE
async def create_guild_config(db: AsyncSession, guild_discord_id: str) -> GuildConfiguration:
    guild_config = GuildConfiguration(guild_id=guild_discord_id)
    db.add(guild_config)
    await db.commit()
    await db.refresh(guild_config)
    return guild_config

# AFTER
async def create_guild_config(db: AsyncSession, guild_discord_id: str) -> GuildConfiguration:
    """
    Create new guild configuration.

    Note: Does not commit. Caller must commit transaction.
    """
    guild_config = GuildConfiguration(guild_id=guild_discord_id)
    db.add(guild_config)
    await db.flush()  # Generate ID for immediate use
    return guild_config
```

### Phase 2: Route Handler Verification

**Verify Transaction Boundaries:**
1. All routes use `Depends(get_db)` or `Depends(get_db_with_user_guilds())`
2. These dependencies handle commit/rollback correctly
3. No routes manually call commit/rollback

**Current Status:**
- Routes properly use dependency injection ✓
- Transaction boundaries at route level ✓
- Problem is service layer breaking boundaries ✗

### Phase 3: Test Suite Updates

**Update Unit Tests:**
1. Remove `mock_db.commit.assert_awaited_once()` assertions
2. Add `mock_db.commit.assert_not_awaited()` where appropriate
3. Update test fixtures to not expect commits

**Add Integration Tests:**
1. Test transaction rollback on errors
2. Verify atomicity of multi-step operations
3. Test partial failure scenarios (e.g., guild sync with channel error)

### Phase 4: Documentation

**Add Guidelines:**
1. Document transaction management pattern in project conventions
2. Add examples to service layer template/skeleton
3. Update contribution guidelines with commit/flush rules
4. Add pre-commit hook or linter rule to detect service layer commits

## Implementation Guidance

### Objectives
- Restore transaction atomicity across all service operations
- Prevent data integrity issues from partial operation failures
- Maintain clean separation of concerns (service logic vs transaction management)
- Update tests to validate correct transaction behavior

### Key Tasks
1. **Service Layer Cleanup**
   - Remove 17 commit calls from service functions
   - Verify flush usage is appropriate (9 locations)
   - Add docstring notes about transaction expectations

2. **Orchestrator Review**
   - Verify `sync_user_guilds()` and similar orchestrators work without nested commits
   - Test error handling and rollback behavior
   - Add logging for transaction boundaries

3. **Test Updates**
   - Update ~50 test assertions about commits
   - Add new rollback/atomicity tests
   - Create integration test scenarios for partial failures

4. **Route Handler Audit**
   - Verify all mutation endpoints use `get_db()` dependency
   - Check for any manual commit/rollback calls
   - Validate error handling preserves transaction boundaries

### Dependencies
- No external dependencies required
- No database migration needed
- No API contract changes
- Backward compatible at API level

### Success Criteria
- All service functions commit-free
- Guild sync creates guild+channels+template atomically or rolls back completely
- Game creation with participants is atomic
- Participant operations maintain consistency
- Test suite validates transaction atomicity
- No orphaned records from partial operation failures

## Technical Requirements

**Critical Principles:**
1. **Single Responsibility**: Service functions manipulate data, routes manage transactions
2. **Atomicity**: Multi-step operations succeed completely or roll back completely
3. **Consistency**: Database state always valid, no orphaned records
4. **Error Recovery**: Failed operations leave no side effects

**SQLAlchemy Patterns:**
- Use `flush()` to generate IDs mid-transaction
- Never `commit()` in service layer
- Let FastAPI dependency handle commit/rollback
- Use `refresh()` after flush if need to reload relationships

**Testing Strategy:**
- Unit tests: Verify NO commits in service layer
- Integration tests: Verify atomicity of multi-step operations
- E2E tests: Verify error scenarios don't corrupt data
- Add explicit rollback testing

## Alternative Approaches Considered

### Alternative 1: Explicit Transaction Managers
**Description**: Create transaction manager classes that wrap service operations

```python
class TransactionManager:
    async def execute(self, func, *args):
        async with self.session:
            result = await func(*args)
            await self.session.commit()
            return result
```

**Pros**:
- Explicit transaction boundaries
- Reusable across services
- Clear separation

**Cons**:
- Adds complexity layer
- Duplicates FastAPI dependency behavior
- More code to maintain
- Not idiomatic FastAPI pattern

**Verdict**: ❌ FastAPI's dependency injection already provides this functionality

### Alternative 2: Keep Service Commits, Add Savepoints
**Description**: Keep current pattern but use savepoints for nested transactions

```python
async def sync_user_guilds(db: AsyncSession, ...):
    async with db.begin_nested():  # Savepoint
        guild = await create_guild_config(db, ...)  # Commits to savepoint
        channels = await create_channels(db, ...)   # Commits to savepoint
    await db.commit()  # Commit all savepoints
```

**Pros**:
- Minimal code changes
- Keeps service layer "simple"

**Cons**:
- Still breaks FastAPI transaction pattern
- Savepoints add overhead
- Harder to reason about transaction state
- Doesn't fix root architectural issue
- Test complexity increases

**Verdict**: ❌ Treats symptom, not cause

### Alternative 3: Two-Phase Service Pattern
**Description**: Services return pending changes, route commits them

```python
class PendingChange:
    def apply(self, db): ...

async def create_guild_config(...) -> PendingChange:
    return PendingChange(lambda db: db.add(GuildConfiguration(...)))

@router.post("/sync")
async def sync_guilds(db: AsyncSession = Depends(get_db)):
    changes = await guild_service.sync_user_guilds(...)
    for change in changes:
        change.apply(db)
    # get_db commits here
```

**Pros**:
- Explicit about what gets committed
- Could enable transaction preview/dry-run

**Cons**:
- Massive refactoring required
- Unnatural pattern for SQLAlchemy
- Loses ORM benefits (change tracking, relationships)
- Overly complex for problem at hand

**Verdict**: ❌ Over-engineered solution

## Summary

**Critical Issue Identified**: Service layer functions commit immediately, breaking transaction atomicity and causing data integrity issues. Discovered via production incident where guild sync created orphaned guild record without channels or templates.

**Root Cause**: Service functions call `commit()` instead of letting FastAPI's `get_db()` dependency manage transaction lifecycle. This violates SQLAlchemy best practices and FastAPI architectural patterns.

**Scope**: 17 service function commits across 5 files, affecting guild operations, channel management, templates, games, and participants. 50+ tests verify incorrect behavior.

**Critical Finding - Isolated to FastAPI**: Service functions with commits are **ONLY** called from FastAPI route handlers. Discord bot and scheduler daemons use `get_db_session()` and manage their own transactions independently. They do NOT call these API service functions. This means removing commits from service layer will NOT break bot or daemon functionality.

**Recommended Solution**: Remove all commits from service layer, rely on FastAPI dependency injection for transaction management. Use `flush()` only where IDs needed mid-transaction. This restores proper transaction boundaries and prevents partial operation failures.

**Implementation Priority**: High risk operations first (guild sync, game creation, participant management), then remaining services. Update tests to validate atomicity. Zero external dependencies, backward compatible at API level. **No impact on bot or daemon services.**
