<!-- markdownlint-disable-file -->

# Task Details: Game Card Host Avatar Display Enhancement

## Research Reference

**Source Research**: #file:../research/20251218-game-card-host-avatar-display-research.md

## Phase 1: Backend Avatar Data Collection

### Task 1.1: Update DisplayNameResolver to extract avatar hashes

Modify `DisplayNameResolver.resolve_display_names()` to extract both guild member avatar and user avatar hashes from Discord API responses, then construct Discord CDN URLs with proper priority.

- **Files**:
  - `services/api/services/display_names.py` - DisplayNameResolver class
- **Success**:
  - Extract `member.get("avatar")` for guild-specific avatar
  - Extract `member["user"].get("avatar")` for user global avatar
  - Build CDN URLs: guild avatar > user avatar > null
  - Format: `https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/{hash}.png?size=64`
  - Return dict with both display_name and avatar_url
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 171-208) - Backend display name service enhancement example
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 149-160) - Avatar priority rules
- **Dependencies**:
  - None

### Task 1.2: Add avatar_url to ParticipantResponse schema

Update Pydantic schemas to include optional avatar_url field in participant responses.

- **Files**:
  - `shared/schemas/participant.py` - ParticipantResponse schema
- **Success**:
  - Add `avatar_url: str | None = None` field to ParticipantResponse
  - Field accepts null/None values gracefully
  - Schema validation passes with and without avatar_url
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 455-462) - API response changes
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Update game routes to return avatar URLs

Modify game API routes to include avatar URLs in host and participant responses.

- **Files**:
  - `services/api/routes/games.py` - Game route handlers
- **Success**:
  - Call DisplayNameResolver with avatar extraction enabled
  - Pass avatar URLs to ParticipantResponse objects
  - Host object includes avatar_url in API responses
  - All participant objects include avatar_url in responses
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 455-467) - API response structure
- **Dependencies**:
  - Task 1.1 and 1.2 completion

### Task 1.4: Update caching to include avatar data

Modify cache storage to include avatar URLs alongside display names with same TTL.

- **Files**:
  - `shared/cache/keys.py` - Cache key definitions
  - `services/api/services/display_names.py` - Cache read/write logic
- **Success**:
  - Cache stores JSON: `{"display_name": "...", "avatar_url": "..."}`
  - Cache key format: `display_name_avatar:{user_id}:{guild_id}`
  - TTL remains 5 minutes (same as display names)
  - Cache invalidation works correctly
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 531-535) - Caching strategy
- **Dependencies**:
  - Task 1.1 completion

## Phase 2A: Web Frontend Implementation

### Task 2A.1: Add avatar_url to Participant TypeScript interface

Update TypeScript type definitions to include optional avatar_url field.

- **Files**:
  - `frontend/src/types/index.ts` - Type definitions
- **Success**:
  - Participant interface has `avatar_url?: string | null` field
  - TypeScript compilation passes without errors
  - Type checking validates avatar_url as optional string or null
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 210-223) - Frontend interface update
- **Dependencies**:
  - Phase 1 completion

### Task 2A.2: Update GameCard component to display host avatar

Reorganize GameCard layout to display host with avatar at top, replacing bottom Chip component.

- **Files**:
  - `frontend/src/components/GameCard.tsx` - Game card component
- **Success**:
  - Host displayed at top of card in Box with flexbox layout
  - MUI Avatar component shows profile picture when avatar_url present
  - Avatar falls back to first initial when avatar_url is null
  - Avatar size is 32x32 pixels
  - Typography shows "Host: {name}" with proper styling
  - Old Chip component removed from bottom
  - Layout is visually balanced and responsive
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 225-250) - GameCard component example
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 393-410) - GameCard component implementation
- **Dependencies**:
  - Task 2A.1 completion

### Task 2A.3: Add frontend tests for avatar display

Create tests for GameCard avatar display with various avatar URL states.

- **Files**:
  - `frontend/src/components/GameCard.test.tsx` - Component tests
- **Success**:
  - Test avatar displays with valid URL
  - Test fallback to initials when avatar_url is null
  - Test layout with and without avatars
  - Test accessibility (alt text present)
  - All tests pass
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 431-436) - Web frontend test requirements
- **Dependencies**:
  - Task 2A.2 completion

## Phase 2B: Discord Bot Embed Implementation

### Task 2B.1: Update create_game_embed to accept avatar parameters

Add optional host_display_name and host_avatar_url parameters to embed creation function.

- **Files**:
  - `services/bot/formatters/game_message.py` - GameMessageFormatter.create_game_embed()
- **Success**:
  - Function signature includes host_display_name: str | None = None
  - Function signature includes host_avatar_url: str | None = None
  - Parameters properly typed and documented
  - Backward compatibility maintained for existing calls
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 412-429) - Embed creation example
- **Dependencies**:
  - Phase 1 completion

### Task 2B.2: Use embed.set_author() for host display

Implement embed author field to display host with avatar at top of Discord embed.

- **Files**:
  - `services/bot/formatters/game_message.py` - GameMessageFormatter.create_game_embed()
- **Success**:
  - Call embed.set_author() with host display name and avatar URL
  - Author name format: "Host: {display_name}"
  - Only set author when host_display_name is not None
  - Icon URL only included when host_avatar_url is not None
  - Gracefully handles None values
  - Remove or keep old Host field as backup (implementation decision)
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 412-429) - Embed creation example
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 95-104) - Discord embed author field structure
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 316-324) - Recommended Option A implementation
- **Dependencies**:
  - Task 2B.1 completion

### Task 2B.3: Update event handlers to pass avatar data

Modify bot event handlers to extract and pass host avatar URLs to embed formatters.

- **Files**:
  - `services/bot/events/handlers.py` - EventHandlers._create_game_announcement()
- **Success**:
  - Extract host_display_name from game.host.display_name
  - Extract host_avatar_url from game.host.avatar_url
  - Pass both values to format_game_announcement()
  - Handle None/null values gracefully
  - Existing game announcements continue to work
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 412-429) - Handler changes section
- **Dependencies**:
  - Task 2B.2 completion

### Task 2B.4: Add Discord bot tests for embed author field

Create tests for Discord embed creation with host avatar author field.

- **Files**:
  - `tests/services/bot/formatters/test_game_message.py` - Formatter tests
- **Success**:
  - Test embed.set_author() called with avatar URL
  - Test embed.set_author() called without avatar URL (name only)
  - Test graceful handling when host_display_name is None
  - Test Discord CDN URL format is correct
  - Test with animated avatars (a_ prefix)
  - All tests pass
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 438-444) - Discord bot test requirements
- **Dependencies**:
  - Task 2B.3 completion

## Dependencies

- Discord API access via services/api/auth/discord_client.py
- MUI Avatar component (already installed)
- discord.py library (already installed)

## Success Criteria

- Backend extracts and returns avatar URLs for all participants
- Avatar URLs follow Discord CDN format with proper priority
- Web frontend displays host avatar at top of GameCard
- Discord embeds show host avatar using author field
- Caching includes avatar data with 5-minute TTL
- All backend, frontend, and bot tests pass
- Graceful fallback when avatars are null/unavailable

## Phase 3: Integration and End-to-End Testing

### Task 3.1: Add integration tests for avatar data flow

Test complete flow from Discord API through backend to frontend/bot display.

- **Files**:
  - `tests/integration/test_avatar_integration.py` - Integration test suite
- **Success**:
  - Test Discord API call returns avatar data
  - Test DisplayNameResolver extracts and constructs URLs correctly
  - Test API response includes avatar URLs
  - Test cache stores and retrieves avatar data
  - Test avatar URL priority (guild > user > null) works end-to-end
  - All integration tests pass
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 149-160) - Avatar priority rules
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 531-535) - Caching strategy
- **Dependencies**:
  - Phase 1, 2A, and 2B completion

### Task 3.2: Test web frontend with real Discord avatars

Verify GameCard displays correctly with actual Discord avatar URLs in browser.

- **Files**:
  - Manual testing documentation or E2E tests
- **Success**:
  - GameCard displays actual Discord avatars when URLs present
  - Initials display correctly when avatar URL is null
  - Avatar images load without CORS errors
  - Retina displays show crisp avatars (2x resolution)
  - Layout remains balanced with various name lengths
  - Accessibility verified (screen reader announces host with avatar)
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 469-473) - Avatar size recommendations
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Test Discord bot embeds in live environment

Verify Discord embeds display host avatar correctly in actual Discord client.

- **Files**:
  - Manual testing in Discord or integration tests
- **Success**:
  - Embed author field displays at top with avatar icon
  - Avatar images render correctly in Discord client
  - Layout matches expected visual design
  - Works with both guild-specific and user avatars
  - Gracefully handles animated avatars (GIF)
  - Works when avatar URL is None (text-only display)
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 475-522) - Discord embed structure comparison
- **Dependencies**:
  - Task 3.1 completion

### Task 3.4: Verify avatar caching and performance

Test cache performance and ensure avatar URLs cached efficiently.

- **Files**:
  - Performance test suite or monitoring
- **Success**:
  - Cache hit rate > 80% for repeat avatar lookups
  - Cache TTL of 5 minutes enforced
  - Avatar URLs cached alongside display names
  - No performance degradation with avatar URL construction
  - Cache invalidation works correctly
  - Memory usage remains acceptable
- **Research References**:
  - #file:../research/20251218-game-card-host-avatar-display-research.md (Lines 531-535) - Caching strategy
- **Dependencies**:
  - Task 3.1 completion

## Final Verification

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Web frontend displays avatars correctly
- [ ] Discord bot embeds display avatars correctly
- [ ] Caching performance meets requirements
- [ ] No regressions in existing functionality
- [ ] Documentation updated if needed
