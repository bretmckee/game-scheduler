<!-- markdownlint-disable-file -->
# Remaining Code Duplication Analysis

## Research Summary

After commit af772528557a017bb2dd8c992692935fb1916c90 reduced code clones from 31 to 22, this analysis examines the remaining duplications to determine which warrant consolidation.

## Detection Configuration

From `.jscpd.json`:
- **Threshold**: 2% duplication
- **Min Lines**: 6 lines
- **Min Tokens**: 50 tokens
- **Mode**: mild
- **Languages**: Python, TypeScript, JavaScript

## Clone Count Explanation

**jscpd detected 22 distinct code clone pairs**, which are organized below into **14 logical categories** for easier analysis:

| Category | Clone Pairs | Files Affected |
|----------|-------------|----------------|
| 1. Authorization patterns | 4 | permissions.py (internal) |
| 2. Guild response construction | 2 | guilds.py (internal) |
| 3. Channel response construction | 2 | channels.py (internal) |
| 4. Template operations | 3 | templates.py (internal) |
| 5. Display name fetching | 1 | display_names.py (internal) |
| 6. Participant count query | 1 | join_game.py ↔ leave_game.py |
| 7. Game error handling | 1 | games.py (internal) |
| 8. Discord API error handling | 2 | client.py (internal) |
| 9. Publisher methods | 1 | publisher.py ↔ sync_publisher.py |
| 10. Permission decorators | 1 | decorators.py (internal) |
| 11. TypeScript types | 1 | types/index.ts (internal) |
| 12. Model timestamps | 1 | guild.py ↔ template.py |
| 13. Daemon initialization | 1 | notification_daemon_wrapper.py ↔ status_transition_daemon_wrapper.py |
| 14. Database config | 1 | verify_schema.py ↔ wait_postgres.py |
| **Total** | **22** | **14 categories** |

## Remaining Clones Analysis (22 pairs in 14 categories)

### Category 1: Worth Eliminating (High Priority)

#### 1. Authorization Pattern Duplication (4 clone pairs)
**Location**: `services/api/dependencies/permissions.py`

**Clone Pairs**:
1. Lines 251-272 vs 304-325 (21 lines, 79 tokens)
2. Lines 273-288 vs 326-341 (15 lines, 116 tokens)
3. Lines 251-272 vs 391-416 (25 lines, 79 tokens)
4. Lines 273-284 vs 417-428 (11 lines, 94 tokens)

**Pattern**: Three nearly identical permission check functions:
- `require_manage_guild()`
- `require_manage_channels()`
- `require_bot_manager()`

**Impact**: Critical authorization code with repeated logic for:
- Token validation
- Guild ID resolution
- Permission checking
- Error handling

**Recommendation**: **HIGH PRIORITY - Should eliminate**. Create a generic `_require_permission()` helper that takes a permission check function as a parameter. This is security-sensitive code where consistency is critical.

```python
# Consolidation approach:
async def _require_permission(
    guild_id: str,
    permission_checker: Callable,
    error_message: str,
    current_user: auth_schemas.CurrentUser,
    role_service: RoleVerificationService,
    db: AsyncSession,
) -> auth_schemas.CurrentUser:
    """Generic permission requirement helper."""
    # Common validation, resolution, and error handling
    pass
```

---

#### 2. Response Schema Construction (2 clone pairs)
**Location**: `services/api/routes/guilds.py`

**Clone Pairs**:
1. Lines 122-134 vs 162-174 (12 lines, 80 tokens)
2. Lines 120-134 vs 191-205 (14 lines, 95 tokens)

**Pattern**: Creating `GuildConfigResponse` objects with identical fields after different operations (get, create, update).

**Impact**: Repetitive response construction with potential for inconsistency.

**Recommendation**: **MEDIUM PRIORITY - Should eliminate**. Extract a helper function:

```python
async def _build_guild_config_response(
    guild_config: GuildConfiguration,
    current_user: auth_schemas.CurrentUser,
    db: AsyncSession,
) -> guild_schemas.GuildConfigResponse:
    """Build guild configuration response with guild name."""
    guild_name = await permissions.get_guild_name(
        guild_config.guild_id, current_user, db
    )
    return guild_schemas.GuildConfigResponse(
        id=guild_config.id,
        guild_name=guild_name,
        bot_manager_role_ids=guild_config.bot_manager_role_ids,
        require_host_role=guild_config.require_host_role,
        created_at=guild_config.created_at.isoformat(),
        updated_at=guild_config.updated_at.isoformat(),
    )
```

---

#### 3. Channel Response Construction (2 clone pairs)
**Location**: `services/api/routes/channels.py`

**Clone Pairs**:
1. Lines 61-77 vs 104-120 (16 lines, 107 tokens)
2. Lines 61-74 vs 140-153 (13 lines, 101 tokens)

**Pattern**: Building `ChannelConfigResponse` objects after get/create/update operations.

**Impact**: Repetitive response construction.

**Recommendation**: **MEDIUM PRIORITY - Should eliminate**. Same pattern as guilds—extract helper function.

---

#### 4. Template Response Construction (3 clone pairs)
**Location**: `services/api/routes/templates.py`

**Clone Pairs**:
1. Lines 138-152 vs 57-71 (14 lines, 105 tokens)
2. Lines 259-271 vs 231-243 (12 lines, 95 tokens)
3. Lines 292-304 vs 231-243 (12 lines, 95 tokens)

**Pattern**: Bot manager permission check followed by template operations.

**Impact**: Repetitive authorization and response construction for update/delete/set_default operations.

**Recommendation**: **MEDIUM PRIORITY - Should eliminate**. Already has `build_template_response()` helper, but permission check pattern is duplicated. Extract permission check into a decorator or helper.

---

#### 5. Display Name Fetching (1 clone pair)
**Location**: `services/api/services/display_names.py`

**Clone Pair**:
- Lines 103-113 vs 233-244 (11 lines, 94 tokens)

**Pattern**: Fetching Discord member info and extracting display name with same fallback logic:
```python
display_name = (
    member.get("nick")
    or member["user"].get("global_name")
    or member["user"]["username"]
)
```

**Impact**: One method fetches only display_name (for caching), the other also fetches avatar_url.

**Recommendation**: **LOW PRIORITY - Consider eliminating**. Could extract the display name resolution logic into a helper method, though the duplication is relatively small.

---

#### 6. Participant Count Query (1 clone pair)
**Location**: `services/bot/handlers/`

**Clone Pair**:
- `join_game.py` [156-164] vs `leave_game.py` [128-136] (8 lines, 75 tokens)

**Pattern**: Counting current participants with same query:
```python
result = await db.execute(
    select(GameParticipant)
    .where(GameParticipant.game_session_id == str(game_id))
    .where(GameParticipant.user_id.isnot(None))
)
participant_count = len(result.scalars().all())
```

**Impact**: Business logic duplication that could lead to inconsistency.

**Recommendation**: **MEDIUM PRIORITY - Should eliminate**. Extract into a shared utility function in `services/bot/handlers/utils.py`:

```python
async def get_participant_count(db: AsyncSession, game_id: str) -> int:
    """Get count of non-placeholder participants."""
    result = await db.execute(
        select(GameParticipant)
        .where(GameParticipant.game_session_id == str(game_id))
        .where(GameParticipant.user_id.isnot(None))
    )
    return len(result.scalars().all())
```

---

### Category 2: Consider Eliminating (Medium Priority)

#### 7. Game Error Handling (1 clone pair)
**Location**: `services/api/routes/games.py`

**Clone Pair**:
- Lines 289-306 vs 467-484 (17 lines, 108 tokens)

**Pattern**: Identical error handling for ValidationError and ValueError in create vs update operations.

**Impact**: Duplicated error transformation logic.

**Recommendation**: **MEDIUM PRIORITY - Consider eliminating**. Extract into a decorator or context manager for consistent error handling across game operations.

---

#### 8. Discord API Error Handling (2 clone pairs)
**Location**: `shared/discord/client.py`

**Clone Pairs**:
1. Lines 282-291 vs 546-555 (9 lines, 85 tokens)
2. Lines 372-384 vs 411-423 (12 lines, 99 tokens)

**Pattern**: Repeated error handling for Discord API responses:
```python
if response.status != status.HTTP_200_OK:
    error_msg = (
        response_data.get("message", "Unknown error")
        if isinstance(response_data, dict)
        else "Unknown error"
    )
    raise DiscordAPIError(response.status, error_msg, dict(response.headers))
```

**Impact**: Error handling consistency across API methods.

**Recommendation**: **LOW-MEDIUM PRIORITY - Consider eliminating**. Could extract into a helper method that validates response and raises appropriate errors, but the pattern is simple enough that duplication may be acceptable for clarity.

---

#### 9. Message Publisher Convenience Methods (1 clone pair)
**Location**: `shared/messaging/`

**Clone Pair**:
- `publisher.py` [118-140] vs `sync_publisher.py` [142-164] (22 lines, 90 tokens)

**Pattern**: Identical `publish_dict()` convenience method in both async and sync publishers.

**Impact**: Minor—these are parallel implementations (async vs sync).

**Recommendation**: **LOW PRIORITY - Probably keep**. These are intentionally parallel implementations. Consolidation would require complex abstraction or code generation for minimal benefit.

---

### Category 3: Acceptable Duplication (Low Priority or Keep)

#### 10. Permission Decorators (1 clone pair)
**Location**: `services/bot/commands/decorators.py`

**Clone Pair**:
- Lines 59-70 vs 92-103 (11 lines, 98 tokens)

**Pattern**: Two decorator functions with identical structure:
- `require_manage_guild()`
- `require_manage_channels()`

**Impact**: Discord bot command decorators with similar permission checks.

**Recommendation**: **LOW PRIORITY - Consider keeping**. These decorators are intentionally separate for clarity in command definitions. The duplication makes the permission requirements explicit. Consolidation would add complexity for marginal benefit.

---

#### 11. Template Type Definitions (1 clone pair)
**Location**: `frontend/src/types/index.ts`

**Clone Pair**:
- Lines 150-164 vs 171-185 (14 lines, 143 tokens)

**Pattern**: `GameTemplate` vs `TemplateListItem` TypeScript interfaces with overlapping fields.

**Impact**: Frontend type definitions.

**Recommendation**: **LOW PRIORITY - Keep**. These represent different API responses:
- `GameTemplate`: Full template with metadata (guild_id, order, created_at, updated_at)
- `TemplateListItem`: Simplified template for list views

Could use TypeScript utility types (`Omit`, `Pick`) but current approach is clearer and more explicit.

---

#### 12. Database Model Timestamps (1 clone pair)
**Location**: `shared/models/`

**Clone Pair**:
- `guild.py` [47-55] vs `template.py` [63-69] (8 lines, 96 tokens)

**Pattern**: Standard timestamp column definitions:
```python
created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
updated_at: Mapped[datetime] = mapped_column(
    default=utc_now, onupdate=utc_now, server_default=func.now()
)
```

**Impact**: Standard SQLAlchemy column definitions across models.

**Recommendation**: **LOW PRIORITY - Keep**. This is standard SQLAlchemy pattern. While you could use mixins, explicit definitions are clearer and more maintainable. The duplication is intentional and conventional.

---

#### 13. Daemon Initialization (1 clone pair)
**Location**: `services/scheduler/`

**Clone Pair**:
- `notification_daemon_wrapper.py` [35-51] vs `status_transition_daemon_wrapper.py` [35-51] (16 lines, 90 tokens)

**Pattern**: Identical initialization code in daemon wrapper scripts (signal handlers, logging setup, telemetry init).

**Impact**: Boilerplate daemon startup code.

**Recommendation**: **LOW-MEDIUM PRIORITY - Consider eliminating**. Could extract into a `daemon_common.py` module with a `setup_daemon(name: str)` function, but the duplication is minimal and these are entry point scripts where explicit code aids clarity.

---

#### 14. Database Connection Retrieval (1 clone pair)
**Location**: `services/init/`

**Clone Pair**:
- `verify_schema.py` [49-57] vs `wait_postgres.py` [43-51] (8 lines, 93 tokens)

**Pattern**: Reading database connection parameters from environment variables:
```python
db_host = os.getenv("POSTGRES_HOST", "localhost")
db_port = os.getenv("POSTGRES_PORT", "5432")
db_user = os.getenv("POSTGRES_USER", "gamebot")
db_password = os.getenv("POSTGRES_PASSWORD", "")
db_name = os.getenv("POSTGRES_DB", "game_scheduler")
```

**Impact**: Configuration retrieval in initialization scripts.

**Recommendation**: **LOW PRIORITY - Consider eliminating**. These are standalone initialization scripts. Could create a `get_db_config()` helper function, but the duplication is minor and explicit environment variable reading is clear.

---

## Prioritized Elimination Recommendations

### High Priority (Should Eliminate)
1. **Authorization permission checks** (permissions.py) - Security-critical code
   - Estimated effort: 2-3 hours
   - Risk: Medium (requires careful testing of authorization)

### Medium Priority (Should Consider)
2. **Response construction patterns** (guilds.py, channels.py, templates.py)
   - Estimated effort: 1-2 hours per file
   - Risk: Low (straightforward refactoring)

3. **Participant count query** (join_game.py, leave_game.py)
   - Estimated effort: 30 minutes
   - Risk: Low (simple utility extraction)

4. **Game error handling** (games.py)
   - Estimated effort: 1 hour
   - Risk: Low-Medium (error handling refactoring)

5. **Display name fetching** (display_names.py)
   - Estimated effort: 30 minutes
   - Risk: Low

### Low Priority (Optional)
6. **Discord API error handling** (client.py) - Pattern is simple, duplication acceptable
7. **Daemon initialization** (scheduler daemons) - Entry point clarity valuable
8. **Database config retrieval** (init scripts) - Explicit code aids clarity

### Keep As-Is (Acceptable Duplication)
9. **Permission decorators** (decorators.py) - Intentional separation for clarity
10. **TypeScript type definitions** (frontend types) - Different API contracts
11. **Database model timestamps** (model classes) - SQLAlchemy convention
12. **Message publisher methods** (async/sync) - Parallel implementations

## Implementation Strategy

If proceeding with eliminations, recommend this order:
1. Start with **participant count query** (quick win, low risk)
2. Tackle **response construction patterns** (clear benefit, low risk)
3. Address **authorization checks** (highest impact, requires careful testing)
4. Consider **error handling consolidation** if time permits

## Estimated Total Effort
- High priority: 2-3 hours
- Medium priority: 3-4 hours
- Total for significant improvements: **5-7 hours**

---

## Research Executed

### Detection Tool
- Used `jscpd` (Copy/Paste Detector) with JSON output
- Configuration: `.jscpd.json`
- Report: `.jscpd-report/jscpd-report.json`

### Analysis Method
1. Ran jscpd to generate current duplication report
2. Read each identified clone location
3. Analyzed context and purpose of duplicated code
4. Categorized by elimination priority
5. Estimated effort and risk for consolidation

### Files Analyzed
- 21 Python files across API, bot, scheduler, and shared modules
- 1 TypeScript file (frontend types)
- Total: 22 distinct code clones across the codebase
