<!-- markdownlint-disable-file -->
# Centralized Query Layer: Unified Database Access Architecture

## Executive Summary

**One Solution, Two Benefits**: Create a centralized guild-scoped query layer that simultaneously eliminates code duplication and enforces guild isolation security.

**Current State**: 37+ scattered database queries with inconsistent patterns create both maintenance burden (duplication) and security risk (accidental cross-guild data leakage).

**Proposed Solution**: Single migration to `guild_queries.py` wrapper functions that consolidate repeated patterns while requiring guild_id parameters for security.

**Timeline**: 8 weeks, incremental delivery, low risk

**ROI**: One migration effort delivers both deduplication benefits and security enforcement.

## Problem Statement

### Duplication Problem
- 15+ locations repeat `queries.get_guild_by_id(db, guild_id)`
- 5+ locations repeat `queries.get_channel_by_id(db, channel_id)`
- 37+ total database query locations with similar patterns
- Each query has slightly different error handling and context
- Maintenance burden: Changes require updates in multiple locations

### Security Problem
- **Threat Model**: Developer accidents (forgetting filters, copy-paste errors, refactoring bugs)
- **Risk**: Optional guild_id parameters make cross-guild data leakage easy
- **Example**: `list_games(guild_id: str | None = None)` allows querying all games
- 11 locations have explicit guild filtering, 26 locations inconsistent or missing
- No architectural enforcement preventing accidental cross-guild queries

### Root Cause: Same Issue
Both problems stem from **scattered, direct database access without centralized control**:
- Duplication happens because queries are written inline everywhere
- Security gaps happen because guild filtering is optional everywhere
- **One architectural fix solves both problems**

## Research Evidence

### Duplication Audit Found
From `.copilot-tracking/research/20251231-code-duplication-audit-research.md`:

**Guild Fetching Pattern** - 15+ locations:
- services/api/routes/templates.py (2 locations)
- services/api/routes/guilds.py (6 locations)
- services/api/dependencies/permissions.py (3 locations)
- Plus 4+ more across API routes

**Analysis from original research**: "This is NOT duplication - these are standard CRUD operations"
- Queries intentionally simple and reusable
- Created as part of game template system (commit 0e5f5a73)
- **But**: No centralized enforcement layer

### Security Audit Found
From `.copilot-tracking/research/20251231-database-access-centralization-guild-isolation-research.md`:

**Query Pattern Analysis** - 37+ locations:
- 8 tables accessed (GameSession, GameTemplate, GameParticipant, etc.)
- 11 locations explicitly filter by guild_id
- 26 locations have inconsistent or missing guild checks
- **High-risk pattern**: `services/api/services/games.py:487` - optional guild_id parameter

**Both audits identified the same code** - just different concerns:
- Duplication: "These queries are repeated"
- Security: "These queries lack enforcement"

## Unified Solution: Guild-Scoped Query Layer

### Architecture
```
Application Code (API, Bot, Scheduler)
    ↓
shared/data_access/guild_queries.py (~10-12 wrapper functions)
    ↓ Enforces: guild_id required + filtering + RLS context
Database (PostgreSQL with RLS policies)
```

### Why This Solves Both Problems

**Eliminates Duplication**:
- ✅ Single implementation of each query pattern
- ✅ Consistent error handling across all usage
- ✅ One place to optimize/update query logic
- ✅ Reduces 37+ inline queries to 10-12 reusable functions

**Enforces Security**:
- ✅ Function signature requires guild_id (can't forget)
- ✅ All queries automatically filter by guild_id
- ✅ RLS provides database-level safety net
- ✅ Linting prevents bypassing wrapper layer

**Single Migration Effort**:
- One pass through 37+ locations
- Migrate to `guild_queries.*` functions
- Get both benefits simultaneously
- 50% less work than separate efforts

## Implementation: 8-Week Plan

### Week 1: Create Wrapper Functions

**Deliverable**: `shared/data_access/guild_queries.py` with ~10-12 functions

```python
# Game Operations (5 functions) - Consolidates game query duplication + adds security
async def get_game_by_id(db, guild_id: str, game_id: str) -> GameSession | None:
    """Get game by ID - REQUIRES guild_id, filters by guild_id.

    Consolidates: 8+ inline select(GameSession).where(...) queries
    Enforces: guild_id parameter required, RLS context set
    """
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == game_id)
        .where(GameSession.guild_id == guild_id)  # Security: explicit filter
    )
    return result.scalar_one_or_none()

async def list_games(db, guild_id: str, channel_id: str = None) -> list[GameSession]:
    """List games for guild - REQUIRES guild_id, filters by guild_id.

    Replaces: list_games(guild_id: str | None = None) - HIGH RISK optional parameter
    Consolidates: 5+ variations of game listing queries
    """
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    query = select(GameSession).where(GameSession.guild_id == guild_id)
    if channel_id:
        query = query.where(GameSession.channel_id == channel_id)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_game(db, guild_id: str, game_data: dict) -> GameSession:
    """Create game - REQUIRES guild_id, sets guild_id on entity."""
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    game = GameSession(**game_data, guild_id=guild_id)  # Security: force guild_id
    db.add(game)
    await db.flush()
    return game

async def update_game(db, guild_id: str, game_id: str, updates: dict) -> GameSession:
    """Update game - REQUIRES guild_id, validates ownership."""
    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        raise ValueError(f"Game {game_id} not found in guild {guild_id}")
    for key, value in updates.items():
        setattr(game, key, value)
    await db.flush()
    return game

async def delete_game(db, guild_id: str, game_id: str) -> None:
    """Delete game - REQUIRES guild_id, validates ownership."""
    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        raise ValueError(f"Game {game_id} not found in guild {guild_id}")
    await db.delete(game)
    await db.flush()

# Participant Operations (3 functions) - Consolidates participant query duplication
async def add_participant(db, guild_id: str, game_id: str, user_id: str, data: dict) -> GameParticipant:
    """Add participant - validates game belongs to guild."""
    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        raise ValueError(f"Game {game_id} not found in guild {guild_id}")
    participant = GameParticipant(game_id=game_id, user_id=user_id, **data)
    db.add(participant)
    await db.flush()
    return participant

async def remove_participant(db, guild_id: str, game_id: str, user_id: str) -> None:
    """Remove participant - validates game belongs to guild."""
    game = await get_game_by_id(db, guild_id, game_id)
    if not game:
        raise ValueError(f"Game {game_id} not found in guild {guild_id}")
    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_id == game_id)
        .where(GameParticipant.user_id == user_id)
    )
    participant = result.scalar_one_or_none()
    if participant:
        await db.delete(participant)
        await db.flush()

async def list_user_games(db, guild_id: str, user_id: str) -> list[GameSession]:
    """List user's games in guild."""
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    result = await db.execute(
        select(GameSession)
        .join(GameParticipant)
        .where(GameSession.guild_id == guild_id)
        .where(GameParticipant.user_id == user_id)
    )
    return list(result.scalars().all())

# Template Operations (4 functions) - Consolidates template query patterns
async def get_template_by_id(db, guild_id: str, template_id: str) -> GameTemplate | None:
    """Get template - REQUIRES guild_id."""
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    result = await db.execute(
        select(GameTemplate)
        .where(GameTemplate.id == template_id)
        .where(GameTemplate.guild_id == guild_id)
    )
    return result.scalar_one_or_none()

async def list_templates(db, guild_id: str) -> list[GameTemplate]:
    """List templates for guild.

    Consolidates: 15+ inline queries.get_guild_by_id() + template queries
    """
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    result = await db.execute(
        select(GameTemplate)
        .where(GameTemplate.guild_id == guild_id)
    )
    return list(result.scalars().all())

async def create_template(db, guild_id: str, data: dict) -> GameTemplate:
    """Create template - REQUIRES guild_id."""
    await db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    template = GameTemplate(**data, guild_id=guild_id)
    db.add(template)
    await db.flush()
    return template

async def update_template(db, guild_id: str, template_id: str, updates: dict) -> GameTemplate:
    """Update template - validates ownership."""
    template = await get_template_by_id(db, guild_id, template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found in guild {guild_id}")
    for key, value in updates.items():
        setattr(template, key, value)
    await db.flush()
    return template
```

**Dual Benefits Achieved**:
- ✅ **Deduplication**: 37+ inline queries → 10-12 reusable functions
- ✅ **Security**: Every function requires guild_id, can't be forgotten
- ✅ **Maintainability**: Change query logic in one place
- ✅ **Auditability**: All database access through known entry points

### Week 2-3: Migrate API Routes

**Priority Order**: Highest duplication + highest risk first

```python
# BEFORE: Scattered, duplicated, optional filtering
@router.get("/games/{game_id}")
async def get_game(game_id: str, guild_id: str = Depends(...), db = Depends(...)):
    result = await db.execute(
        select(GameSession)
        .where(GameSession.id == game_id)
        .where(GameSession.guild_id == guild_id)  # Easy to forget
    )
    return result.scalar_one_or_none()

# AFTER: Centralized, required parameter, consistent error handling
@router.get("/games/{game_id}")
async def get_game(game_id: str, guild_id: str = Depends(...), db = Depends(...)):
    return await guild_queries.get_game_by_id(db, guild_id, game_id)
```

**Migration Targets** (from duplication audit):
1. **services/api/routes/games.py** - 8+ game queries → use guild_queries game functions
2. **services/api/routes/templates.py** - 6+ template queries → use guild_queries template functions
3. **services/api/routes/guilds.py** - 6+ guild/config queries → use guild_queries functions
4. **services/api/routes/channels.py** - 5+ channel queries → use guild_queries functions
5. **services/api/dependencies/permissions.py** - 10+ permission check queries → use guild_queries

**Benefits Realized**:
- ✅ **Removes duplication**: All routes use same implementation
- ✅ **Enforces security**: Can't call without guild_id
- ✅ **Easier testing**: Mock 10-12 functions instead of 37+ queries

### Week 4: Migrate Bot Handlers

```python
# BEFORE: Implicit guild context from Discord
async def handle_join_game(interaction: discord.Interaction, game_id: str):
    result = await db.execute(select(GameSession).where(GameSession.id == game_id))
    game = result.scalar_one_or_none()

# AFTER: Explicit guild from interaction
async def handle_join_game(interaction: discord.Interaction, game_id: str):
    game = await guild_queries.get_game_by_id(db, str(interaction.guild_id), game_id)
```

**Benefits**:
- ✅ Explicit guild_id in code (better than implicit Discord context)
- ✅ Same query implementation as API (consistency)
- ✅ Security enforced even in bot context

### Week 5: Migrate Scheduler Daemons

Create sync versions for scheduler's sync Session:

```python
# shared/data_access/guild_queries_sync.py
def get_next_scheduled_event_sync(db: Session, guild_id: str) -> GameStatusSchedule | None:
    db.execute(text("SET LOCAL app.current_guild_id = :guild_id"), {"guild_id": guild_id})
    return db.execute(
        select(GameStatusSchedule)
        .where(GameStatusSchedule.guild_id == guild_id)
        .where(GameStatusSchedule.scheduled_at <= datetime.utcnow())
    ).scalar_one_or_none()
```

**Benefits**:
- ✅ Consistent pattern across async and sync code
- ✅ Scheduler queries also centralized and secured

### Week 6: Verify 100% Migration

**Verification Checklist**:
- [ ] No imports of `GameSession` outside `guild_queries.py`, `models/`, `alembic/`
- [ ] No imports of `GameTemplate` outside allowed locations
- [ ] No imports of `GameParticipant` outside allowed locations
- [ ] All 37+ query locations now use `guild_queries.*` functions
- [ ] Run integration tests - all pass
- [ ] Manual audit of services/ directory for direct model usage

**Why Import Check Is Stronger**:
- Can't query what you can't import
- Catches all patterns: select(), insert(), update(), delete()
- Self-enforcing architecture

### Week 7: Enable RLS Safety Net

**NOW it's safe** - wrappers already pass guild_id correctly:

```sql
-- Won't break anything - code already filters correctly
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY guild_isolation_games ON game_sessions
    FOR ALL
    USING (guild_id = current_setting('app.current_guild_id', true)::uuid);

ALTER TABLE game_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY guild_isolation_templates ON game_templates
    FOR ALL
    USING (guild_id = current_setting('app.current_guild_id', true)::uuid);

ALTER TABLE game_participants ENABLE ROW LEVEL SECURITY;
CREATE POLICY guild_isolation_participants ON game_participants
    FOR ALL
    USING (game_id IN (
        SELECT id FROM game_sessions
        WHERE guild_id = current_setting('app.current_guild_id', true)::uuid
    ));

ALTER TABLE notification_schedule ENABLE ROW LEVEL SECURITY;
CREATE POLICY guild_isolation_notifications ON notification_schedule
    FOR ALL
    USING (game_session_id IN (
        SELECT id FROM game_sessions
        WHERE guild_id = current_setting('app.current_guild_id', true)::uuid
    ));
```

**Why This Is Low Risk**:
- Wrappers set RLS context: `SET LOCAL app.current_guild_id = :guild_id`
- Wrappers filter by guild_id in query
- RLS just adds defense-in-depth
- If wrapper has bug, RLS catches it

**Benefits**:
- ✅ **Double protection**: Application filter + database policy
- ✅ **Catches wrapper bugs**: If logic error in wrapper, RLS blocks it
- ✅ **Audit trail**: PostgreSQL logs RLS violations

### Week 8: Add Linting - Prevent Regressions

**Enforce architectural boundaries** - block model imports outside wrappers:

```python
# scripts/lint_guild_queries.py
"""Enforce that models can only be imported in wrapper files.

This prevents both:
1. Code duplication (inline queries instead of wrappers)
2. Security bypasses (queries without guild_id enforcement)
"""
import ast
import sys

ALLOWED_MODEL_IMPORT_FILES = [
    "shared/data_access/guild_queries.py",      # Async wrappers
    "shared/data_access/guild_queries_sync.py", # Sync wrappers
    "shared/models/",                            # Model definitions
    "alembic/",                                  # Migrations
]

PROTECTED_MODELS = [
    "GameSession", "GameTemplate", "GameParticipant",
    "NotificationSchedule", "GameStatusSchedule"
]

def check_file(filepath: str) -> list[str]:
    if any(allowed in filepath for allowed in ALLOWED_MODEL_IMPORT_FILES):
        return []

    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and 'shared.models' in node.module:
                for alias in node.names:
                    if alias.name in PROTECTED_MODELS:
                        violations.append(
                            f"{filepath}:{node.lineno}: Import of {alias.name} not allowed. "
                            f"Use guild_queries.* wrapper functions instead."
                        )

    return violations
```

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: enforce-query-layer
      name: Enforce centralized query layer (prevents duplication + security bypasses)
      entry: python scripts/lint_guild_queries.py
      language: python
      files: ^(services|tests)/.*\.py$
      exclude: ^shared/(models|data_access)/
```

**Dual Benefits**:
- ✅ **Prevents duplication**: Can't write inline query without import
- ✅ **Prevents security bypasses**: Can't skip guild_id without import
- ✅ **Self-documenting**: Violation message explains architecture

## Success Metrics

### Deduplication Metrics
- ✅ Query implementations: 37+ scattered → 10-12 centralized
- ✅ Lines of code: Reduced by ~500 lines (estimated)
- ✅ Maintenance burden: 37 update sites → 10-12 update sites
- ✅ Test complexity: Mock 10-12 functions vs 37+ queries

### Security Metrics
- ✅ Cross-guild query risk: ELIMINATED (required parameter + RLS)
- ✅ Optional filtering: ELIMINATED (all wrappers require guild_id)
- ✅ Error clarity: Missing guild_id = TypeError at call site
- ✅ Production incidents: Target ZERO cross-guild leaks

### Combined Benefits
- ✅ **One migration, two problems solved**
- ✅ **Architectural enforcement**: Linting prevents regressions on both fronts
- ✅ **Clear patterns**: All database access follows same approach
- ✅ **Self-documenting**: Function signatures show security requirements

## Comparison: Separate vs Combined Approach

### If Done Separately

**Phase 1: Deduplication**
- Week 1-2: Create `queries.py` functions
- Week 3-4: Migrate 37+ locations to `queries.*`
- Week 5: Testing

**Phase 2: Security**
- Week 6-7: Create `guild_queries.py` wrappers
- Week 8-9: Migrate same 37+ locations AGAIN
- Week 10: Enable RLS
- Week 11: Add linting

**Total**: 11 weeks, 74+ migrations (37 + 37)

### Combined Approach (This Plan)

**Single Phase**:
- Week 1: Create `guild_queries.py` (deduplication + security)
- Week 2-5: Migrate 37+ locations ONCE
- Week 6: Verify
- Week 7: RLS
- Week 8: Linting

**Total**: 8 weeks, 37 migrations

**Savings**: 3 weeks, 50% less migration work

## Risk Analysis

### Low Risk Migration
- ✅ Each wrapper function independent (incremental rollout)
- ✅ Can test each migration immediately
- ✅ No breaking changes to external APIs
- ✅ Rollback = revert individual files

### Medium Risk: RLS Enablement (Week 7)
- ⚠️ Database-level change affects all queries
- ✅ Mitigation: Wrappers already correct (6 weeks of testing)
- ✅ Rollback: `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`

### Validation Strategy
- Run integration tests after each week
- Manual verification of query patterns
- Code review focus on guild_id parameter usage
- Linting catches regressions automatically

## Comprehensive Testing Strategy

### Testing Gaps Identified

**Original plan** emphasized unit tests but lacked comprehensive integration and e2e coverage for a security-critical architectural change affecting 37+ locations.

### Three-Layer Testing Approach

#### Layer 1: Unit Tests (Existing in Plan)
**Coverage**: Wrapper functions in `shared/data_access/guild_queries.py`
**Purpose**: Verify individual function behavior with mocked database
**Key validations**:
- guild_id parameter required (TypeError if missing)
- RLS context set correctly
- Query filters by guild_id
- Error handling for edge cases

#### Layer 2: Integration Tests (ADDED)
**Why critical**: Unit tests cannot verify that migrations correctly pass guild_id through real call chains.

**Task 2.6: API Guild Isolation Integration Tests**
- **File**: `tests/integration/test_guild_isolation_api.py`
- **Coverage**: All migrated API routes (games, templates, guilds, channels)
- **Key scenarios**:
  - Attempt to access Guild B's game using Guild A's authentication → 404/403
  - List games with Guild A context → only returns Guild A games
  - Create game with Guild A context → guild_id correctly set
  - Update Guild B's game with Guild A token → fails
  - Delete Guild B's game with Guild A token → fails
  - Performance: wrapper overhead < 5ms per query
- **Why necessary**: Verifies wrappers integrate correctly with FastAPI dependency injection and authentication

**Task 3.4: Bot Guild Isolation Integration Tests**
- **File**: `tests/integration/test_bot_guild_isolation.py`
- **Coverage**: Bot handlers migrated to guild_queries
- **Key scenarios**:
  - Bot command in Guild A → only accesses Guild A data
  - Simulate interaction.guild_id extraction → verify correct guild_id passed to wrappers
  - Cross-guild access attempts fail gracefully
- **Why necessary**: Validates guild_id correctly extracted from Discord context (implicit → explicit conversion risk)

**Task 3.5: Scheduler Guild Isolation Integration Tests**
- **Files**: Update existing `tests/integration/test_notification_daemon.py`, `test_status_transitions.py`
- **Coverage**: Scheduler daemons using sync wrappers
- **Key scenarios**:
  - Daemon processes Guild A event → doesn't affect Guild B
  - Multiple guilds with pending events → processed correctly in isolation
  - Sync wrappers set RLS context correctly
- **Why necessary**: Ensures sync wrappers maintain same security guarantees as async

**Task 4.3: RLS Enforcement Integration Tests** (Already in plan, now expanded)
- **File**: `tests/integration/test_rls_enforcement.py`
- **Coverage**: Database-level RLS policies
- **Key scenarios**:
  - RLS context set correctly by wrappers
  - Cross-guild queries blocked even if application filter missing
  - PostgreSQL logs RLS violations (audit trail verification)

#### Layer 3: End-to-End Tests (ADDED)
**Why critical**: Security validation requires testing complete workflows across all components.

**Task 4.4: Complete Workflow Guild Isolation E2E Tests**
- **File**: `tests/e2e/test_guild_isolation_e2e.py`
- **Coverage**: Multi-component workflows (API → Bot → Scheduler)
- **Key scenarios**:
  - **Scenario 1**: Create game via API (Guild A) → Verify bot sees it in Guild A only, not Guild B
  - **Scenario 2**: Schedule notification (Guild A) → Daemon processes for Guild A only
  - **Scenario 3**: User joins game (Guild A) → Participant changes not visible in Guild B
  - **Scenario 4**: Multiple guilds operating simultaneously → No cross-contamination
  - **Scenario 5**: Scheduler processes events for both guilds → Correct isolation maintained
- **Why necessary**:
  - Catches issues that span component boundaries (e.g., guild_id lost in message passing)
  - Validates realistic production scenarios with multiple guilds
  - Provides confidence that accidental cross-guild queries are impossible

### Why Integration/E2E Tests Are Essential Here

**Threat model**: Developer accidents (forgetting filters, copy-paste errors, refactoring bugs)

**What unit tests miss**:
- Incorrect guild_id extraction from Discord `interaction.guild_id`
- Missing guild_id parameters in function calls (type hints help, but runtime verification needed)
- RLS context not propagating through transaction lifecycle
- Performance degradation from wrapper overhead (37+ locations affected)
- Message passing between components (API → RabbitMQ → Scheduler) losing guild context

**Historical evidence**: Project found 26 locations with inconsistent/missing guild checks - indicates developer accidents are real risk.

**Cost/benefit**: Adding 4 integration/e2e test tasks (2.6, 3.4, 3.5, 4.4) to 8-week plan adds ~1 week but prevents production guild data leakage incidents.

### Testing Timeline Integration

- **Week 1**: Unit tests for wrapper functions (Task 1.5)
- **Weeks 2-3**: API migration + integration tests (Tasks 2.1-2.6)
- **Week 4**: Bot migration + integration tests (Tasks 3.1, 3.4)
- **Week 5**: Scheduler migration + integration tests (Tasks 3.2-3.3, 3.5)
- **Week 6**: Verification + audit (Task 4.1)
- **Week 7**: RLS enablement + integration tests (Tasks 4.2-4.3)
- **Week 8**: E2E validation + linting + documentation (Tasks 4.4, 5.1-5.3)

Total: 8 weeks (unchanged from original, testing integrated into each phase)

## Next Steps

1. **Review and approve** this unified approach
2. **Week 1**: Create `shared/data_access/guild_queries.py`
3. **Week 2**: Begin API route migration (highest risk/duplication first)
4. **Weekly check-ins**: Verify progress, address issues

## Research Sources

This plan synthesizes findings from two complementary audits:
- `.copilot-tracking/research/20251231-code-duplication-audit-research.md` - Identified 37+ scattered queries
- `.copilot-tracking/research/20251231-database-access-centralization-guild-isolation-research.md` - Security analysis

Both identified the same code patterns from different perspectives. This unified plan addresses both concerns in a single architectural improvement.
