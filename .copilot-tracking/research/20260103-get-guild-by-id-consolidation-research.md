<!-- markdownlint-disable-file -->
# get_guild_by_id Duplication Pattern Analysis

## Executive Summary

**Goal**: Consolidate 11 duplicated `get_guild_by_id()` + error handling patterns into single helper function.

**Critical Discovery**: All 11 locations are API routes with `current_user.access_token` available, enabling helper function to set RLS context automatically.

**Recommended Approach**:
- Helper function sets RLS context when missing (idempotent)
- Works with both `get_db` and `get_db_with_user_guilds()`
- Manual authorization check for defense in depth
- No route migration required

**Benefits**:
- ✅ Reduces 44-55 lines to 11 lines (~75% reduction)
- ✅ Adds authorization enforcement (closes security gap)
- ✅ Sets RLS context automatically (enables future RLS on guild_configurations)
- ✅ Single maintenance point
- ✅ Works immediately without breaking changes

**Timeline**: 10 hours over 5 days (1 extra hour for context-setting logic)

---

## Research Executed

### Code Search Results
- `get_guild_by_id` usage pattern search
  - Found 11 actual usage locations (down from original estimate of 15+)
  - Pattern highly consistent across all locations
  - Clear duplication of error handling logic

### File Analysis
- **services/api/database/queries.py** - Base function definition
- **services/api/routes/templates.py** (2 locations) - Template operations
- **services/api/routes/guilds.py** (6 locations) - Guild configuration operations
- **services/api/dependencies/permissions.py** (3 locations) - Permission checks

## Key Discoveries

### Current Implementation Pattern

All 11 locations follow this exact pattern:

```python
guild_config = await queries.get_guild_by_id(db, guild_id)
if not guild_config:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Guild configuration not found"  # or similar message
    )
# Then use guild_config.guild_id (Discord snowflake ID)
```

### Two Usage Patterns Identified

**Pattern 1: Fetch by route parameter** (9 locations)
```python
# guild_id comes from route parameter
guild_config = await queries.get_guild_by_id(db, guild_id)
if not guild_config:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guild configuration not found")
```

**Pattern 2: Fetch by entity's guild_id** (2 locations in permissions.py)
```python
# guild_id comes from another entity (game.guild_id, template.guild_id)
guild_config = await queries.get_guild_by_id(db, template.guild_id)
if not guild_config:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
```

### What Happens After Fetching

In **all 11 locations**, the code:
1. Fetches guild_config
2. Checks if None
3. Raises HTTPException(404) if not found
4. Uses `guild_config.guild_id` (Discord snowflake) for subsequent operations

The guild_config object is used for:
- `guild_config.guild_id` - Discord guild ID (primary usage)
- `guild_config.bot_manager_role_ids` - Role configuration
- `guild_config.require_host_role` - Permission settings
- Other configuration fields

## Duplication Analysis

### Duplicated Code
- **Error handling block**: Repeated 11 times identically
- **Exception raising**: Same pattern 11 times
- **Error message**: Varies slightly ("Guild configuration not found", "Template not found", "Game not found")

### Lines of Code Impact
- Current: ~4-5 lines per location × 11 = 44-55 lines
- Proposed: 1 line per location × 11 = 11 lines
- **Savings**: ~33-44 lines of duplicated error handling

### Maintenance Burden
- **Current**: 11 update sites if error handling logic changes
- **Proposed**: 1 update site (single helper function)

## RLS Context Considerations

### CRITICAL DISCOVERY: RLS Context Strategy Varies by Caller Type

**VERIFIED: All 11 locations have access to authentication credentials**

Investigation confirmed access token availability:

| Location | File | Function | Auth Available | How |
|----------|------|----------|----------------|-----|
| 1 | templates.py:55 | list_templates | ✅ | `current_user` param via Depends |
| 2 | templates.py:181 | create_template | ✅ | `current_user` param via Depends |
| 3 | permissions.py:135 | verify_template_access | ✅ | `access_token` parameter |
| 4 | permissions.py:181 | verify_game_access | ✅ | `access_token` parameter |
| 5 | permissions.py:242 | _resolve_guild_id | ✅ | Called from require_manage_guild which has `current_user` |
| 6 | guilds.py:89 | get_guild | ✅ | `current_user` param via Depends |
| 7 | guilds.py:121 | get_guild_config | ✅ | `current_user` param via Depends |
| 8 | guilds.py:192 | update_guild_config | ✅ | `current_user` param via Depends |
| 9 | guilds.py:228 | list_guild_channels | ✅ | `current_user` param via Depends |
| 10 | guilds.py:272 | get_guild_roles | ✅ | `current_user` param via Depends |
| 11 | guilds.py:344 | validate_mention | ✅ | `current_user` param via Depends |

**Conclusion: All 11 locations can access user authentication → Helper can set RLS context**

### RLS Context Availability Details

**RLS Context Already Set** (2 locations):
- ✅ templates.py (2 locations) - Uses `Depends(database.get_db_with_user_guilds())`

**RLS Context CAN BE SET** (9 locations):
- ⚠️ guilds.py (6 locations) - Has `current_user`, can fetch guilds & set context
- ⚠️ permissions.py (3 locations) - Has `access_token` or `current_user`, can set context

## Recommended Approach

### Option A: Helper Sets RLS Context (RECOMMENDED)

**Best of both worlds**: Helper function sets RLS context when needed, works everywhere.

Add to `services/api/database/queries.py`:

```python
from fastapi import HTTPException
from starlette import status
from shared.data_access.guild_isolation import get_current_guild_ids, set_current_guild_ids

async def require_guild_by_id(
    db: AsyncSession,
    guild_id: str,
    access_token: str,
    user_discord_id: str,
    not_found_detail: str = "Guild configuration not found"
) -> GuildConfiguration:
    """
    Fetch guild configuration by UUID with automatic RLS context setup.

    Sets RLS context if not already set (idempotent). Returns 404 for both
    "not found" and "unauthorized" to prevent information disclosure.

    Args:
        db: Database session
        guild_id: Database UUID (GuildConfiguration.id)
        access_token: User's OAuth2 access token
        user_discord_id: User's Discord ID
        not_found_detail: Custom error message for 404 response

    Returns:
        Guild configuration (verified user has access)

    Raises:
        HTTPException(404): If guild not found OR user not authorized
    """
    from services.api.auth import oauth2

    # Ensure RLS context is set (idempotent - only fetches if not already set)
    if get_current_guild_ids() is None:
        user_guilds = await oauth2.get_user_guilds(access_token, user_discord_id)
        guild_ids = [g["id"] for g in user_guilds]
        set_current_guild_ids(guild_ids)

    guild_config = await get_guild_by_id(db, guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail
        )

    # Defense in depth: Manual authorization check
    # (RLS will also enforce at database level once enabled)
    authorized_guild_ids = get_current_guild_ids()
    if authorized_guild_ids is None or guild_config.guild_id not in authorized_guild_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail
        )

    return guild_config
```

### Migration Pattern

**BEFORE** (current pattern, 4-5 lines):
```python
guild_config = await queries.get_guild_by_id(db, guild_id)
if not guild_config:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Guild configuration not found",
    )
```

**AFTER** (consolidated, 1 line):
```python
guild_config = await queries.require_guild_by_id(
    db, guild_id, current_user.access_token, current_user.user.discord_id
)
```

### Benefits of Option A

✅ **Works everywhere**: Sets context when missing, uses existing context when present
✅ **No route migration needed**: Works with both `get_db` and `get_db_with_user_guilds()`
✅ **Defense in depth**: Manual check + RLS (once enabled)
✅ **Idempotent**: Safe to call multiple times (checks before fetching guilds)
✅ **Performance**: oauth2.get_user_guilds() has 5-min cache
✅ **Future-proof**: When routes migrate to get_db_with_user_guilds(), still works (just uses existing context)

### Option B: Migrate Routes First (Future Work)

For cleaner architecture long-term:
1. Migrate 9 routes to `get_db_with_user_guilds()`
2. Add RLS to guild_configurations
3. Simplify helper to not set context (just rely on RLS)

**Additional effort**: +4 hours

### Migration Pattern

**BEFORE** (current pattern, 4-5 lines):
```python
guild_config = await queries.get_guild_by_id(db, guild_id)
if not guild_config:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Guild configuration not found",
    )
```

**AFTER** (consolidated, 1 line):
```python
guild_config = await queries.require_guild_by_id(db, guild_id)
```

**For custom error messages** (Pattern 2):
```python
# Instead of: "Template not found" or "Game not found"
guild_config = await queries.require_guild_by_id(db, template.guild_id, "Template not found")
```

## Implementation Plan

### Phase 1: Create Helper Function with Auto-Context-Setting
- Add `require_guild_by_id()` to `services/api/database/queries.py`
- Import HTTPException, get/set_current_guild_ids, oauth2
- Implement idempotent RLS context setup
- Implement manual authorization check
- Write unit tests including:
  - RLS context already set + authorized → uses existing context
  - RLS context NOT set → fetches guilds, sets context, succeeds
  - Guild not found → HTTPException(404)
  - Guild found + user NOT authorized → HTTPException(404)
  - Verify oauth2.get_user_guilds called only when context missing
- **Duration**: 4 hours (includes context-setting logic)

### Phase 2: Migrate Usage Locations (11 total)

**Priority Order** (by file, for easier review):

1. **services/api/routes/guilds.py** (6 locations)
   - Line 89: `get_guild_basic_info`
   - Line 121: `get_guild_config`
   - Line 192: `update_guild_config`
   - Line 228: `list_guild_channels`
   - Line 272: `get_guild_roles`
   - Line 344: `validate_mention`

2. **services/api/routes/templates.py** (2 locations)
   - Line 55: `list_templates`
   - Line 181: `create_template`

3. **services/api/dependencies/permissions.py** (3 locations)
   - Line 135: `verify_template_access` - custom message "Template not found"
   - Line 181: `verify_game_access` - custom message "Game not found"
   - Line 242: `resolve_guild_discord_id` - standard message

### Phase 3: Verification
- Run integration tests to ensure no behavioral changes
- Verify all 11 locations migrated
- Check error messages still appropriate in all contexts

## Benefits

### Immediate Benefits
✅ **Reduces duplication**: 44-55 lines → 11 lines (~75% reduction)
✅ **Single source of truth**: Error handling logic in one place
✅ **Easier maintenance**: Changes apply to all 11 locations automatically
✅ **More readable**: Intent clearer with "require" in name
✅ **Security enforcement**: Authorization check consolidated (closes security gap)
✅ **No information disclosure**: Returns 404 for both "not found" and "unauthorized"
✅ **RLS context setup**: Automatically sets context for future RLS enablement
✅ **No breaking changes**: Works with both get_db and get_db_with_user_guilds()
✅ **Performance**: oauth2.get_user_guilds() has 5-min cache, only called when needed

### Future Benefits
✅ **Extension point**: Can add logging, telemetry, or caching in one place
✅ **Consistent behavior**: All routes handle missing guilds identically
✅ **Type safety**: Return type guarantees non-None result

## Risk Analysis

### Very Low Risk
- ✅ Pure refactoring - no logic changes
- ✅ Each migration can be tested independently
- ✅ Easy rollback - just revert individual changes
- ✅ No external API changes
- ✅ No database schema changes

### Security Enhancement
- ✅ **Adds authorization enforcement**: Current code relies on route-level checks
- ✅ **Defense in depth**: Helper verifies RLS context authorization
- ✅ **Prevents info disclosure**: Returns 404 (not 403) for unauthorized access
- ✅ **Catches missing context**: Fails safely if RLS context not set

### Critical Security Note

**Current Pattern Has Authorization Gap**:
```python
# CURRENT CODE (SECURITY GAP)
guild_config = await queries.get_guild_by_id(db, guild_id)
if not guild_config:
    raise HTTPException(status_code=404, detail="Guild not found")
# Uses guild_config.guild_id with NO verification user has access to this guild!
```

**Why This Is Risky**:
- GuildConfiguration has NO RLS policy currently
- UUID guild_id can be guessed/enumerated (not secret)
- User could access any guild's configuration
- Route dependencies verify membership AFTER fetching (gap in security)

**New Pattern Fixes This**:
```python
# NEW CODE (SECURE) - with RLS enabled
guild_config = await queries.require_guild_by_id(db, guild_id)
# RLS at database level blocks unauthorized access
# Returns 404 if user not authorized - no information disclosure
```

**With RLS Enabled**: Database enforces authorization automatically:
- ✅ Cannot fetch guild_config unless user in that guild
- ✅ Authorization at data access layer (defense in depth)
- ✅ Protection even if code bypasses helper function
- ✅ Consistent with other tables (games, templates, participants)

This consolidation **closes a security gap** by adding RLS to guild_configurations table.

### Testing Strategy
- **Unit test new `require_guild_by_id()` function**:
  - Guild exists + RLS context set + authorized → success
  - Guild missing → 404
  - Guild exists + RLS context set + unauthorized → 404
  - Guild exists + NO RLS context (None) → 404 (safe failure)
- **Run existing integration tests** (should all pass - manual check provides same protection)
- **Manual verification** of error responses in dev environment
- **Security validation**:
  - Attempt to access unauthorized guild → verify 404
  - Test with and without RLS context set

## Scope Clarification

This consolidation focuses **only** on the `get_guild_by_id` + error handling pattern.

**In Scope:**
- Creating `require_guild_by_id()` helper
- Migrating 11 identified locations
- Maintaining identical error behavior

**Out of Scope (separate efforts):**
- Guild isolation security enforcement
- RLS policy implementation
- Other query pattern consolidations
- Centralized query layer architecture

This is a **targeted deduplication** - minimal scope, clear benefit, low risk.

## Timeline Estimate

- **Day 1**: Create helper function + comprehensive unit tests with auto-context logic (4 hours)
- **Day 2**: Migrate guilds.py (6 locations) + test (2 hours)
- **Day 3**: Migrate templates.py (2 locations) + test (1 hour)
- **Day 4**: Migrate permissions.py (3 locations) + test (1 hour)
- **Day 5**: Final verification + integration tests + security validation (2 hours)

**Total: 1.5 weeks (10 hours actual work)**

### Future Work: Full RLS Enablement (Separate Task)
Once all routes use this helper (which sets RLS context):
1. Add RLS policy to guild_configurations (1 hour)
2. Test and verify (2 hours)
3. Optional: Simplify helper to remove manual check (1 hour)

**Additional effort**: 4 hours

## Next Steps

1. **Approve approach** - Confirm helper with auto-context-setting is acceptable
2. **Create helper** - Add require_guild_by_id() with context setup + tests
3. **Migrate incrementally** - One file at a time, adding access_token/user_discord_id params
4. **Verify completion** - All 11 locations migrated + security validated + RLS context working
5. **Optional future** - Add RLS to guild_configurations (now safe since context is set)

## Research Sources

- Code search: `get_guild_by_id` usage across codebase
- File analysis: services/api/routes/*, services/api/dependencies/permissions.py
- Pattern analysis: Common error handling structures
