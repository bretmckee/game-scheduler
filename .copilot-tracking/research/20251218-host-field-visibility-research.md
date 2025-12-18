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

### High-Level Solution: Backend-Validated Host Field with Frontend Convenience

**Simpler approach**: Add `host` to API, validate entirely on backend:
- **Backend logic**:
  - If `host` is empty/None → use `current_user.user.id` (existing behavior)
  - If `host` provided → resolve it and check if requester is bot manager OR if it resolves to requester themselves
  - This allows normal users to optionally specify themselves explicitly (harmless)
- **Frontend options**:
  - **Bot Managers**: Show editable field (can specify anyone)
  - **Regular Users**: Either hide field entirely OR show read-only field with their name
  - No frontend permission checks needed - backend handles all validation

### Implementation Complexity: **LOW-TO-MODERATE**

**Estimated Effort**: 3-4 hours for full implementation with tests

### Why Low-to-Moderate Complexity?

**Simplified aspects**:
1. **No frontend permission logic needed** - just show/hide based on user preference
2. **All validation in one place** - backend service layer
3. **Reuse existing patterns** - ParticipantResolver, ValidationError handling
4. **No new error types** - uses existing 422 validation error structure

**Key simplifications**:
- Frontend doesn't need to check bot manager permission (optional for UX only)
- Backend already has all necessary permission checks
- Normal users specifying themselves is valid (just redundant)
- Single validation flow handles all cases

## Implementation Guidance

### Objectives
- Add host field visibility to game creation form
- Make host editable for bot managers only
- Show current user as read-only host for regular users
- Maintain backward compatibility (empty host defaults to current user)

### Key Tasks

#### Frontend Changes (1-2 hours)

**Simple approach - No permission checking on frontend:**

1. **Add Host Field to GameForm Component**
   - Add `host` to GameFormData interface (optional string)
   - Add TextField after Game Title field
   - Always editable (or optionally hide for non-managers for cleaner UX)
   - Pre-fill with current user's display name as placeholder
   - Helper text: "Game host (@mention or username). Leave empty to host yourself."

2. **Update CreateGame and EditGame Pages**
   - Include `host` in form submission payload (send as-is to API)
   - Handle validation errors for host field (422 responses)
   - Display disambiguation suggestions if host mention ambiguous
   - No frontend permission checks needed!

3. **Optional UX Enhancement**
   - For bot managers: Show field as always editable
   - For regular users: Could hide field entirely, or show disabled with their name
   - This is purely cosmetic - backend enforces all rules

#### Backend Changes (2 hours)

1. **Update Schemas**
   - Add `host: str | None` to GameCreateRequest (optional, defaults to None)
   - Add to GameUpdateRequest for consistency (optional)

2. **Modify GameService.create_game** - Core validation logic
   ```python
   # Pseudocode for simplified logic:
   if game_data.host and game_data.host.strip():
       # Resolve the mention
       resolved_host = await resolve_mention(game_data.host)

       # Check authorization: requester is bot manager OR resolved host is requester
       is_bot_manager = await check_bot_manager(current_user)
       is_self_reference = (resolved_host.id == current_user.id)

       if not (is_bot_manager or is_self_reference):
           raise ValueError("Only bot managers can specify a different host")

       # Validate host can host with this template
       if not await check_host_permission(resolved_host, template):
           raise ValueError("Specified user cannot host games with this template")

       actual_host = resolved_host
   else:
       # Empty or None - use current user (existing behavior)
       actual_host = current_user
   ```

3. **Update create_game Route**
   - No changes needed - existing ValidationError handling works
   - `host` automatically extracted from GameCreateRequest
   - All validation happens in service layer

#### Testing (1 hour)
- ✅ Empty host → defaults to current user (backward compatible)
- ✅ Bot manager specifies different user → creates game with that host
- ✅ Bot manager specifies themselves → works (redundant but valid)
- ✅ Regular user leaves empty → defaults to them (existing behavior)
- ✅ Regular user specifies themselves → works (resolves to them)
- ✅ Regular user specifies someone else → error "Only bot managers can..."
- ✅ Invalid host mention → validation error with suggestions
- ✅ Host lacks template permissions → error "User cannot host with this template"

### Dependencies
- Existing ParticipantResolver can be reused for host mention resolution
- **No new dependencies** - everything needed already exists

### Success Criteria
- ✅ Empty/None host defaults to current user (backward compatible)
- ✅ Bot managers can specify any valid user as host
- ✅ Regular users can specify themselves (optional redundancy)
- ✅ Regular users blocked from specifying others
- ✅ Host validation works with disambiguation
- ✅ Invalid host mentions display clear error messages
- ✅ Host permission validation enforced (allowed_host_role_ids)
- ✅ All existing tests pass
- ✅ New integration tests cover host override scenarios

### Why This Approach is Better

**Advantages**:
1. **Simpler frontend** - No permission checks needed on client side
2. **Single source of truth** - All authorization logic in backend
3. **More flexible** - Normal users CAN specify themselves if they want
4. **Less code** - No conditional rendering logic needed
5. **Easier testing** - Authorization tests only in backend
6. **Better separation** - Frontend is presentation, backend is business logic

**Trade-off**:
- Normal users could technically send a `host_mention` in the API request (if they bypass the UI)
- But backend will reject it unless it's themselves, so no security issue
- This is actually normal REST API design - trust backend validation, not frontend hiding
- All existing tests pass
- New integration tests cover bot manager host override scenarios
