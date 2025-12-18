<!-- markdownlint-disable-file -->
# Task Research Notes: Game Card Host Avatar Display Enhancement

## Overview

This research covers displaying host avatars in **TWO** distinct game card contexts:

1. **Web Frontend GameCard** - React component showing games in the web UI
2. **Discord Bot Game Card** - Discord embed message showing game announcements

Both need to display the host's Discord avatar alongside their name.

## Research Executed

### File Analysis
- `frontend/src/components/GameCard.tsx`
  - Current structure: Host displayed at bottom as Chip component
  - Host information from `game.host.display_name`
  - No avatar data currently used
- `frontend/src/types/index.ts`
  - `Participant` interface has `discord_id` and `display_name`
  - No `avatar` or `avatar_hash` field in current schema
- `shared/schemas/participant.py`
  - Backend schema only includes `discord_id` and `display_name`
  - Missing avatar hash field
- `services/api/services/display_names.py`
  - Fetches guild member data from Discord API
  - Extracts `nick`, `global_name`, `username` for display names
  - Does NOT extract avatar information
- `services/api/auth/discord_client.py`
  - `get_guild_member()` fetches full member object from Discord
  - `get_guild_members_batch()` used for bulk display name resolution

### Code Search Results
- Display name resolution in `services/api/services/display_names.py`:
  - Uses Discord API `/guilds/{guild_id}/members/{user_id}` endpoint
  - Currently only extracts display name from member object
  - Member object contains avatar data but it's not being captured
- ParticipantResponse construction in `services/api/routes/games.py`:
  - Lines 350-430: Builds participant responses with display names
  - Creates host response without avatar data
  - Only passes `discord_id` and `display_name` to frontend

### External Research

- #fetch:"https://discord.com/developers/docs/resources/guild#guild-member-object"
  - Guild member object includes `avatar` field: member's guild-specific avatar hash (optional)
  - Guild member object includes nested `user` object with `avatar` field: user's global avatar hash
  - Both fields are nullable/optional
- #fetch:"https://discord.com/developers/docs/resources/user#avatar-data"
  - User object has `avatar` field: user's avatar hash (nullable string)
  - Avatar hashes can be animated (prefixed with `a_` for GIF format)
- #fetch:"https://discord.com/developers/docs/reference#image-formatting"
  - Discord CDN base URL: `https://cdn.discordapp.com/`
  - User Avatar: `avatars/{user_id}/{user_avatar}.png`
  - Guild Member Avatar: `guilds/{guild_id}/users/{user_id}/avatars/{member_avatar}.png`
  - Supported formats: PNG, JPEG, WebP, GIF
  - Size parameter: `?size={power_of_2}` (16-4096)
  - Default avatar fallback: `embed/avatars/{index}.png` where index = `(user_id >> 22) % 6`

## Key Discoveries

### 1. Web Frontend GameCard (React Component)

#### Current Implementation
- Host displayed at bottom as Chip component in `frontend/src/components/GameCard.tsx`
- Host information from `game.host.display_name`
- No avatar data currently used
- MUI Avatar component available for use

#### Implementation Gap
- No avatar fields in TypeScript `Participant` interface
- No avatar display in GameCard component
- Backend doesn't return avatar URLs in API responses

### 2. Discord Bot Game Card (Discord Embed)

#### Current Implementation
- Game embeds created in `services/bot/formatters/game_message.py`
- Host displayed as Discord mention using `format_discord_mention(host_id)`
- Discord automatically renders mentions with user avatar in chat
- Current embed structure:
  ```python
  embed.add_field(name="Host", value=format_discord_mention(host_id), inline=True)
  ```
- Discord mentions (`<@123456789>`) automatically show avatar when rendered

#### Discord Embed Author Field Option
Discord embeds support an `author` field with avatar:
```python
embed.set_author(
    name="Host: Display Name",
    icon_url="https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
)
```

**Author Field Structure**:
- `name`: Text displayed (e.g., "Host: PlayerName")
- `icon_url`: Avatar image URL (Discord CDN)
- `url`: Optional clickable link
- Displays as small circular icon next to name at top of embed

#### Current vs Enhanced Display

**Current (using mention field)**:
```
┌─────────────────────────────┐
│ 📅 D&D Campaign Session     │
│ When: <timestamp>           │
│ Players: 3/5   Host: <@123> │  ← Discord renders avatar inline
│ Participants: <@123> <@456> │
└─────────────────────────────┘
```

**Enhanced (using author field)**:
```
┌─────────────────────────────┐
│ 👤 Host: PlayerName         │  ← Avatar icon + name at top
│ 📅 D&D Campaign Session     │
│ When: <timestamp>           │
│ Players: 3/5                │
│ Participants: <@123> <@456> │
└─────────────────────────────┘
```

### Discord Member API Response Structure

The `get_guild_member()` API call returns:
```python
{
  "user": {
    "id": "80351110224678912",
    "username": "Nelly",
    "discriminator": "1337",
    "global_name": "Nelly Display Name",
    "avatar": "8342729096ea3675442027381ff50dfe"  # Global avatar
  },
  "nick": "Server Nickname",  # Guild-specific nickname
  "avatar": "a1b2c3d4e5f6"    # Guild-specific avatar (overrides user avatar)
}
```

### Avatar Priority Rules

1. **Guild Member Avatar** (if set): Takes highest priority
   - URL: `https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{avatar}.png`
2. **User Global Avatar** (if no guild avatar): Fallback
   - URL: `https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png`
3. **No Avatar**: Return `null` to display initials fallback in UI

### Current Implementation Gap

**Backend**:
- `DisplayNameResolver.resolve_display_names()` fetches member objects but discards avatar data
- Only extracts: `member.get("nick") or member["user"].get("global_name") or member["user"]["username"]`
- Member avatar: `member.get("avatar")`
- User avatar: `member["user"].get("avatar")`

**Frontend**:
- No avatar fields in TypeScript interfaces
- No avatar display in GameCard component
- MUI Avatar component available for use

### Complete Examples

**Backend Display Name Service Enhancement**:
```python
# services/api/services/display_names.py
async def resolve_display_names_and_avatars(
    self, guild_id: str, user_ids: list[str]
) -> dict[str, dict[str, str]]:
    """
    Resolve Discord user IDs to display names and avatar URLs.

    Returns:
        Dict mapping user IDs to {"display_name": str, "avatar_url": str}
    """
    result = {}
    # ... cache checking logic ...

    for member in members:
        user_id = member["user"]["id"]
        display_name = (
            member.get("nick")
            or member["user"].get("global_name")
            or member["user"]["username"]
        )

        # Determine avatar URL with priority: guild avatar > user avatar > null
        member_avatar = member.get("avatar")
        user_avatar = member["user"].get("avatar")

        if member_avatar:
            avatar_url = f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{member_avatar}.png?size=64"
        elif user_avatar:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png?size=64"
        else:
            avatar_url = None

        result[user_id] = {
            "display_name": display_name,
            "avatar_url": avatar_url
        }

    return result
```

**Frontend Interface Update**:
```typescript
// frontend/src/types/index.ts
export interface Participant {
  id: string;
  game_session_id: string;
  user_id: string | null;
  discord_id: string | null;
  display_name: string | null;
  avatar_url?: string | null;  // NEW: Discord avatar URL
  joined_at: string;
  pre_filled_position: number | null;
}
```

**Frontend GameCard Component**:
```tsx
// frontend/src/components/GameCard.tsx
import { Avatar, Box, Chip, Typography } from '@mui/material';

// Move host display to top with avatar
<CardContent>
  {game.host && game.host.display_name && (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
      <Avatar
        src={game.host.avatar_url || undefined}
        alt={game.host.display_name}
        sx={{ width: 32, height: 32 }}
      >
        {!game.host.avatar_url && game.host.display_name[0]}
      </Avatar>
      <Typography variant="subtitle2" color="text.secondary">
        Host: <strong>{game.host.display_name}</strong>
      </Typography>
    </Box>
  )}

  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
    <Typography variant="h6" component="div">
      {game.title}
    </Typography>
    <Chip label={game.status} color={getStatusColor(game.status)} size="small" />
  </Box>
  {/* ... rest of card content ... */}
</CardContent>
```

## Recommended Approach

### Phase 1: Backend Avatar Data Collection

**Objectives**: Modify backend to fetch and return avatar URLs for both web and Discord
- **Key Tasks**:
  1. Update `DisplayNameResolver` to extract avatar hashes from Discord API responses
  2. Add avatar URL construction logic with proper priority (guild > user > default)
  3. Update `ParticipantResponse` schema to include `avatar_url` field
  4. Modify game response builder to include avatar URLs for host and participants
- **Dependencies**: None
- **Success Criteria**:
  - Avatar URLs returned in API responses (null when no avatar)
  - URLs follow Discord CDN format correctly
  - Users without custom avatars get null avatar_url
  - Caching includes avatar data
- **Applies To**: Both web frontend and Discord bot

### Phase 2A: Web Frontend Implementation

**Objectives**: Update web frontend to display host avatar
- **Key Tasks**:
  1. Add `avatar_url?: string | null` to `Participant` interface in `frontend/src/types/index.ts`
  2. Update API client types to match new backend response
  3. Modify `GameCard.tsx` to move host to top with Avatar component
  4. Add fallback to display initials when no avatar URL
  5. Style avatar and layout for visual consistency
- **Dependencies**: Phase 1 completion
- **Success Criteria**:
  - TypeScript compiles without errors
  - Avatar URLs accessible in components
  - Host displayed at top of card with avatar
  - Avatar shows Discord profile picture when available
  - Initials display as fallback
  - Layout is visually balanced

### Phase 2B: Discord Bot Embed Implementation

**Objectives**: Add host avatar to Discord game embeds
- **Key Tasks**:
  1. Modify `services/bot/formatters/game_message.py`
  2. Add avatar URL parameter to `create_game_embed()` and `format_game_announcement()`
  3. Use `embed.set_author()` to display host with avatar at top of embed
  4. Fetch host avatar URL from display name resolver
  5. Keep host mention in fields for backup/reference
- **Dependencies**: Phase 1 completion
- **Success Criteria**:
  - Discord embed shows host avatar at top using author field
  - Avatar URL correctly formatted for Discord CDN
  - Fallback gracefully when avatar URL is None
  - Existing game embeds continue to work
  - Host information prominently displayed

### Discord Bot Implementation Options

**Option A: Use Embed Author Field (RECOMMENDED)**
- Displays host avatar prominently at top of embed
- Clean, Discord-native appearance
- Host name and avatar together
- Example:
  ```python
  if host_avatar_url:
      embed.set_author(
          name=f"Host: {host_display_name}",
          icon_url=host_avatar_url
      )
  ```

**Option B: Keep Mention Field with Avatar**
- Discord automatically renders avatars for mentions
- Less prominent but more consistent with participant display
- No API changes needed for avatar URLs (Discord handles it)
- Current implementation already works

**Recommendation**: Use Option A (author field) because:
- More visually prominent
- Better separation of host from other participants
- Consistent with web frontend enhancement
- Leverages existing avatar URL infrastructure from Phase 1

## Recommended Approach (Detailed)

### Backend Changes

**Files to Modify**:
1. `services/api/services/display_names.py` - Add avatar extraction logic
2. `shared/schemas/participant.py` - Add `avatar_url` field to response schema
3. `services/api/routes/games.py` - Pass avatar URLs in game responses
4. `shared/cache/keys.py` - Update cache keys to include avatars

**Avatar URL Construction Helper**:
```python
def build_avatar_url(
    user_id: str,
    guild_id: str,
    member_avatar: str | None,
    user_avatar: str | None,
    size: int = 64
) -> str | None:
    """Build Discord CDN avatar URL with fallback to None."""
    if member_avatar:
        return f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{member_avatar}.png?size={size}"
    elif user_avatar:
        return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.png?size={size}"
    else:
        return None
```

### Frontend Changes

**Files to Modify**:
1. `frontend/src/types/index.ts` - Add `avatar_url` to Participant interface
2. `frontend/src/components/GameCard.tsx` - Reorganize layout and add Avatar
3. `frontend/src/pages/GameDetails.tsx` - Add host avatar on details page (optional enhancement)

**MUI Components to Use**:
- `Avatar` - For circular avatar images
- `Box` - For layout and flexbox positioning
- `Typography` - For host label text

**GameCard Component Example**:
```tsx
// frontend/src/components/GameCard.tsx
<CardContent>
  {game.host && game.host.display_name && (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
      <Avatar
        src={game.host.avatar_url || undefined}
        alt={game.host.display_name}
        sx={{ width: 32, height: 32 }}
      >
        {!game.host.avatar_url && game.host.display_name[0]}
      </Avatar>
      <Typography variant="subtitle2" color="text.secondary">
        Host: <strong>{game.host.display_name}</strong>
      </Typography>
    </Box>
  )}
  {/* ... rest of card content ... */}
</CardContent>
```

### Discord Bot Changes

**Files to Modify**:
1. `services/bot/formatters/game_message.py` - Update `create_game_embed()` and `format_game_announcement()`
2. `services/bot/events/handlers.py` - Pass host avatar URL when creating announcements

**Embed Creation Example**:
```python
# services/bot/formatters/game_message.py
@staticmethod
def create_game_embed(
    game_title: str,
    host_id: str,
    host_display_name: str | None = None,  # NEW
    host_avatar_url: str | None = None,    # NEW
    # ... other parameters
) -> discord.Embed:
    # ... embed creation ...

    # Add host as author with avatar
    if host_display_name:
        author_name = f"Host: {host_display_name}"
        if host_avatar_url:
            embed.set_author(name=author_name, icon_url=host_avatar_url)
        else:
            embed.set_author(name=author_name)

    # ... rest of fields ...
    return embed
```

### Testing Considerations

**Backend Tests**:
- Test avatar URL construction for all three cases (guild, user, null)
- Verify caching includes avatar data
- Test with missing/null avatar fields returns null
- Verify animated avatars (a_ prefix) handled correctly

**Web Frontend Tests**:
- Test avatar display with valid URLs
- Test fallback to initials when no avatar
- Test layout with and without avatars
- Verify accessibility (alt text, ARIA labels)

**Discord Bot Tests**:
- Test embed author field with avatar URL
- Test embed without avatar (graceful fallback)
- Verify Discord CDN URL format
- Test with animated avatars
- Ensure existing embeds still work

## Technical Requirements

### API Response Changes (Backend)

**Before**:
```json
{
  "host": {
    "discord_id": "123456789",
    "display_name": "PlayerOne"
  }
}
```

**After**:
```json
{
  "host": {
    "discord_id": "123456789",
    "display_name": "PlayerOne",
    "avatar_url": "https://cdn.discordapp.com/avatars/123456789/abc123.png?size=64"
  }
}
```

### Avatar Size Recommendations

**Web Frontend**:
- **GameCard**: 32x32 pixels (size=64 for retina displays)
- **GameDetails**: 48x48 pixels (size=128 for retina displays)
- **ParticipantList**: 32x32 pixels (size=64 for retina displays)

**Discord Bot**:
- **Embed Author Icon**: 64x64 pixels (Discord recommends size=128)
- Discord automatically scales and caches images

### Discord Embed Structure Comparison

**Current Embed (using field)**:
```python
embed = discord.Embed(title="D&D Session", ...)
embed.add_field(name="Host", value="<@123456789>", inline=True)
# Discord mention shows avatar inline in field value
```

**Enhanced Embed (using author)**:
```python
embed = discord.Embed(title="D&D Session", ...)
embed.set_author(
    name="Host: PlayerOne",
    icon_url="https://cdn.discordapp.com/avatars/123456789/abc123.png?size=128"
)
# Avatar and name prominently displayed at top of embed
```

**Visual Comparison**:

Current:
```
┌────────────────────────────────┐
│ 📅 D&D Campaign Session        │
│                                │
│ When: Saturday at 7:00 PM      │
│ Where: Roll20                  │
│ Players: 3/5  Host: @PlayerOne │ ← mention with inline avatar
│                                │
│ Participants:                  │
│ @PlayerOne @Player2 @Player3   │
└────────────────────────────────┘
```

Enhanced:
```
┌────────────────────────────────┐
│ 👤 Host: PlayerOne             │ ← Avatar icon + name at top
├────────────────────────────────┤
│ 📅 D&D Campaign Session        │
│                                │
│ When: Saturday at 7:00 PM      │
│ Where: Roll20                  │
│ Players: 3/5                   │
│                                │
│ Participants:                  │
│ @PlayerOne @Player2 @Player3   │
└────────────────────────────────┘
```

### Caching Strategy

- Cache avatar URLs along with display names
- TTL: Same as display names (5 minutes)
- Cache key format: `display_name_avatar:{user_id}:{guild_id}`
- Store as JSON: `{"display_name": "...", "avatar_url": "..."}`

## Summary

### What Needs to Change

**Backend (Phase 1)**:
1. Extract avatar hashes from Discord API Guild Member objects
2. Build Discord CDN URLs with proper priority (guild > user > null)
3. Add `avatar_url` field to `ParticipantResponse` schema
4. Update caching to store avatar URLs alongside display names
5. Return avatar URLs in all game API responses

**Web Frontend (Phase 2A)**:
1. Add `avatar_url?: string | null` to `Participant` TypeScript interface
2. Update `GameCard.tsx` to display host at top with MUI Avatar component
3. Show Discord profile picture when available, fallback to initials
4. Remove old host Chip component from bottom of card

**Discord Bot (Phase 2B)**:
1. Add `host_display_name` and `host_avatar_url` parameters to embed creation functions
2. Use `embed.set_author()` to display host with avatar at top of Discord embed
3. Update event handlers to pass host information to embed formatters
4. Gracefully handle None/null avatar URLs

### Key Benefits

- **Consistent UX**: Both web and Discord show host avatar prominently
- **Shared Infrastructure**: Avatar URL logic reused across web API and Discord bot
- **Graceful Degradation**: Works without avatars (initials fallback on web, text-only in Discord)
- **Discord Native**: Uses Discord's built-in embed author field for clean appearance
- **Performance**: Avatar URLs cached with display names (5-minute TTL)
