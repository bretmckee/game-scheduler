<!-- markdownlint-disable-file -->
# Task Research Notes: Host Field Visibility in Game Creation Form

## Research Executed

### File Analysis
- [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx)
  - Current form has: title, location, scheduled time, duration, reminders, channel, description, signup instructions, max players, participants
  - No host field present - host is implicitly the current user
  - EditableParticipantList component used for pre-populated participants
- [services/api/routes/games.py](services/api/routes/games.py#L70-L88)
  - Host is set from `current_user.user.id` automatically
  - No host field in GameCreateRequest schema
- [services/api/services/games.py](services/api/services/games.py#L130-L210)
  - Host user fetched from database based on `host_user_id` parameter
  - Permission check verifies user can host games with template
  - Host cannot be changed by user input
- [shared/schemas/game.py](shared/schemas/game.py#L30-L68)
  - GameCreateRequest has no host field
  - Host derived from authenticated user only

### Code Search Results
- `host_id` references (20+ matches)
  - Host stored in GameSession.host_id as ForeignKey to users table
  - Host displayed in GameDetails page as Chip with display_name
  - Host permissions checked throughout codebase
- Pre-populated participants system
  - EditableParticipantList allows adding users with @mentions or placeholders
  - Supports both Discord users (@username) and placeholder strings
  - ParticipantInput interface: id, mention, preFillPosition, isReadOnly, validationStatus

### Project Conventions
- Authorization pattern: Bot managers can edit any game, regular users only their own games
- Permission system: check_bot_manager_permission and check_game_host_permission
- Form patterns: TextField for text, Select for dropdowns, read-only via disabled prop
- Validation: Submit-time validation with 422 errors and disambiguation suggestions

## Key Discoveries

### Current Host Field Behavior
The host field is **completely implicit** in the current implementation:
1. Host is **never shown** on the create game form
2. Host is **automatically set** to `current_user.user.id` on the backend
3. Host is displayed on the GameDetails page as a colored Chip after creation
4. No user input involved - authentication determines the host

### Pre-Populated Participants System
The existing system already supports adding users to games:
- **EditableParticipantList component** allows adding participants with flexible input
- Supports **@mentions** (Discord users) and **placeholder strings** (text-only)
- Each participant has:
  - mention: free-form text input
  - isReadOnly: joined participants can't edit mention, only reorder/remove
  - validationStatus: validated against Discord API on submit
- Submit-time validation with disambiguation for ambiguous mentions
- Form preserves state on validation errors for corrections

### Permission System
Two relevant permission levels exist:
1. **Bot Managers**: Have `bot_manager_role_ids` or MANAGE_GUILD permission
   - Can edit/delete ANY game in the guild
   - Can manage templates and guild settings
2. **Regular Users**: Authenticated Discord users
   - Can only edit/delete their own games (games they host)
   - Can join games (via Discord or pre-population)

## Implementation Patterns

### TextField Read-Only Pattern
```tsx
<TextField
  value={formData.where}
  disabled={loading}
  helperText="Game location (optional)"
/>
```

### Conditional Editability Pattern (from EditableParticipantList)
```tsx
<TextField
  value={p.mention}
  onChange={(e) => handleMentionChange(p.id, e.target.value)}
  disabled={p.isReadOnly}  // Joined players are read-only
  helperText={p.isReadOnly ? 'Joined player (can reorder or remove)' : undefined}
/>
```

### User Display Pattern (from ParticipantList)
```tsx
const formatParticipantDisplay = (displayName: string | null, discordId: string | null) => {
  if (!displayName) return discordId || 'Unknown';
  return displayName.startsWith('@') ? displayName : `@${displayName}`;
};
```

### Bot Manager Permission Check Pattern
```python
# From services/api/auth/roles.py
async def check_bot_manager_permission(
    self, user_id: str, guild_id: str, db: AsyncSession, access_token: str | None = None
) -> bool:
    user_role_ids = await self.get_user_role_ids(user_id, guild_id)
    guild_config = await db.execute(
        select(guild_model.GuildConfiguration).where(
            guild_model.GuildConfiguration.guild_id == guild_id
        )
    )
    if not guild_config or not guild_config.bot_manager_role_ids:
        return await self.has_permissions(user_id, guild_id, access_token, DiscordPermissions.MANAGE_GUILD)
    return any(role_id in guild_config.bot_manager_role_ids for role_id in user_role_ids)
```

## Recommended Approach

### High-Level Solution: Bot Manager-Only Host Field with Backend Validation

**User Requirement**:
- **Bot Managers**: Show editable host field (can specify any user)
- **Regular Users**: NO host field visible - UI remains exactly as it is now
- **Backend**: Accept optional host field, validate permissions, default to current user if empty

### Implementation Details:
- **Frontend logic**:
  - Check if current user is bot manager (via existing `user.roles` or guild config)
  - If bot manager → show editable host field
  - If regular user → hide field entirely (no changes to current form)
  - Host field never sent in request for regular users (remains undefined/empty)
- **Backend logic**:
  - If `host` is empty/None → use `current_user.user.id` (existing behavior, backward compatible)
  - If `host` provided → resolve mention and validate requester is bot manager
  - Validate resolved host has permissions for the template
  - Return validation errors with disambiguation if needed

### Implementation Complexity: **MODERATE**

**Estimated Effort**: 3-4 hours for full implementation with tests

**Complexity increased slightly due to**:
- Need frontend bot manager detection (but existing patterns available)
- Conditional field rendering based on permissions

### Why Moderate Complexity?

**Aspects that keep it manageable**:
1. **Existing permission detection** - frontend already has user role/permission data
2. **All validation in one place** - backend service layer
3. **Reuse existing patterns** - ParticipantResolver, ValidationError handling
4. **No new error types** - uses existing 422 validation error structure
5. **Clean separation** - bot managers get new feature, regular users unchanged

**Slightly increased complexity from**:
- Frontend needs conditional rendering based on bot manager status
- Need to fetch/check user permissions on form load

## Implementation Guidance

### Objectives
- Add host field to game creation form for bot managers only
- Make host editable field for bot managers (can specify any user)
- Regular users see NO host field - form remains unchanged for them
- Maintain backward compatibility (empty/missing host defaults to current user)

### Key Tasks

#### Frontend Changes (1.5-2 hours)

1. **Add Bot Manager Detection**
   - Fetch current user's guild configuration or check user permissions
   - Determine if user has bot manager role or MANAGE_GUILD permission
   - Pattern: Check `currentUser.permissions` or compare roles with guild config
   - Store in component state: `isBotManager: boolean`

2. **Add Host Field to GameForm Component (Conditional)**
   - Add `host` to GameFormData interface (optional string, undefined for regular users)
   - **Only if `isBotManager === true`**: Render TextField after Game Title field
   - Field is editable for bot managers
   - Helper text: "Game host (@mention or username). Leave empty to host yourself."
   - Placeholder: Current user's display name
   - **Regular users**: Field not rendered at all - form identical to current state

3. **Update CreateGame and EditGame Pages**
   - Include `host` in form submission ONLY if user is bot manager and field has value
   - For regular users: `host` field remains undefined/not sent (backend defaults to current user)
   - Handle validation errors for host field (422 responses) - only applies to bot managers
   - Display disambiguation suggestions if host mention ambiguous

#### Backend Changes (2 hours)

1. **Update Schemas**
   - Add `host: str | None` to GameCreateRequest (optional, defaults to None)
   - Add to GameUpdateRequest for consistency (optional)

2. **Modify GameService.create_game** - Core validation logic
   ```python
   # Pseudocode for validation logic:
   if game_data.host and game_data.host.strip():
       # Resolve the mention
       resolved_host = await resolve_mention(game_data.host)

       # Check authorization: requester MUST be bot manager
       is_bot_manager = await check_bot_manager(current_user, guild_id)

       if not is_bot_manager:
           raise ValueError("Only bot managers can specify the game host")

       # Validate resolved host can host with this template
       if not await check_host_permission(resolved_host, template):
           raise ValueError("Specified user cannot host games with this template")

       actual_host = resolved_host
   else:
       # Empty or None - use current user (existing behavior, backward compatible)
       actual_host = current_user
   ```

3. **Update create_game Route**
   - No changes needed - existing ValidationError handling works
   - `host` automatically extracted from GameCreateRequest
   - All validation happens in service layer

#### Testing (1 hour)
- ✅ Empty host → defaults to current user (backward compatible)
- ✅ Bot m/missing host → defaults to current user (backward compatible)
- ✅ Bot manager specifies different user → creates game with that host
- ✅ Bot manager specifies themselves → works (resolves to them, redundant but valid)
- ✅ Bot manager leaves empty → defaults to them (existing behavior)
- ✅ Regular user creates game (no host field sent) → defaults to them (existing behavior)
- ✅ Regular user attempts to send host via API → error "Only bot managers can specify the game host"
- ✅ Invalid host mention (bot manager) → validation error with suggestions
- ✅ Host lacks template permissions → error "User cannot host with this template"
- ✅ Frontend: Regular users do not see host field at all
- ✅ Frontend: Bot managers see editable host field
### Dependencies
- Existing ParticipantResolver can be reused for host mention resolution
- **No new dependencies** - everything needed already exists
missing host defaults to current user (backward compatible)
- ✅ Bot managers can specify any valid user as host via editable field
- ✅ Bot managers see host field in game creation form
- ✅ Regular users see NO host field - form identical to current state
- ✅ Regular users blocked from specifying host (both UI and API level)
- ✅ Host validation works with disambiguation for bot managers
- ✅ Invalid host mentions display clear error messages
- ✅ Host permission validation enforced (allowed_host_role_ids)
- ✅ All existing tests pass
- ✅ New integration tests cover bot manager host override scenarios

### Why This Approach Meets Requirements

**Advantages**:
1. **Clean user experience** - Regular users see zero changes to existing UI
2. **Progressive enhancement** - Bot managers get additional capability without affecting others
3. **Secure by default** - Backend enforces all authorization, frontend just hides UI
4. **Backward compatible** - Empty/missing host continues to work as it always has
5. **Clear separation of concerns** - Permission-based feature visibility

**Security Model**:
- Frontend hides field from non-managers (UX convenience)
- Backend blocks unauthorized requests (actual security enforcement)
- Defense in depth: both layers validate appropriately
- API consumers must be bot managers to use host field (enforced server-side)ion, not frontend hiding
- All existing tests pass
- New integration tests cover bot manager host override scenarios
