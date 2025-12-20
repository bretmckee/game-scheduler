<!-- markdownlint-disable-file -->

# Task Details: Discord API Client Consolidation

## Research Reference

**Source Research**: #file:../research/20251220-discord-client-consolidation-research.md

## Phase 1: Create Shared Discord Module

### Task 1.1: Create shared/discord directory structure and move DiscordAPIClient

Move services/api/auth/discord_client.py to shared/discord/client.py to make it accessible to both API and bot services.

- **Files**:
  - Create: shared/discord/__init__.py
  - Move: services/api/auth/discord_client.py → shared/discord/client.py
- **Success**:
  - shared/discord/__init__.py exists and exports DiscordAPIClient
  - shared/discord/client.py contains complete DiscordAPIClient implementation
  - Original services/api/auth/discord_client.py can be deleted after Phase 2 completion
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 6-14) - DiscordAPIClient current implementation details
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 188-194) - Move to shared architecture design
- **Dependencies**:
  - None

### Task 1.2: Update DiscordAPIClient to accept credentials as constructor parameters

Remove dependency on services.api.config by accepting credentials as constructor parameters.

- **Files**:
  - Modify: shared/discord/client.py - Update __init__ method
- **Success**:
  - DiscordAPIClient.__init__() accepts client_id, client_secret, bot_token as parameters
  - No imports from services.api.config remain in client.py
  - Credentials are stored as instance variables
  - All methods use instance credentials instead of config module
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 167-170) - Credentials configuration concern
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 196-199) - Phase 1 implementation steps
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 305-307) - Critical implementation detail about bot token
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Update DiscordAPIClient imports to use shared.cache

Ensure DiscordAPIClient uses shared.cache modules correctly after move.

- **Files**:
  - Modify: shared/discord/client.py - Import statements
- **Success**:
  - Imports use: from shared.cache import client, keys, ttl
  - All Redis operations use shared.cache.client.RedisClient
  - No broken imports or missing modules
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 70-73) - Current shared cache usage
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 265-269) - Task 1 details about import updates
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Update API Service Imports

### Task 2.1: Find all files importing services.api.auth.discord_client

Identify all API service files that import the old location.

- **Files**:
  - Search: services/api/**/*.py for "from services.api.auth import discord_client"
- **Success**:
  - Complete list of 19 files documented
  - All import patterns identified (get_discord_client, DiscordAPIClient, etc.)
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 35-37) - 19 API files import discord_client
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 271-275) - Task 2 find and update imports
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update imports to shared.discord.client across all 19 API files

Replace all imports from services.api.auth.discord_client with shared.discord.client.

- **Files**:
  - Modify: All 19 API service files identified in Task 2.1
- **Success**:
  - All imports changed from "services.api.auth.discord_client" to "shared.discord.client"
  - No remaining imports from old location
  - All functionality preserved (same function/class names)
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 173-175) - Breaking existing API concern
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 199) - Update all API imports step
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 271-275) - Task 2 details
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update get_discord_client() singleton in API service

Update API's singleton pattern to instantiate DiscordAPIClient with credentials from API config.

- **Files**:
  - Modify: services/api/dependencies/discord.py (or wherever get_discord_client is defined)
- **Success**:
  - get_discord_client() imports from shared.discord.client
  - Passes credentials from services.api.config to DiscordAPIClient constructor
  - Singleton pattern preserved
  - All API routes continue to work
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 12) - Singleton pattern via get_discord_client()
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 196-199) - Phase 1 implementation steps
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Verify API unit tests pass

Run API service tests to ensure no functionality broken by the move.

- **Files**:
  - Run: uv run pytest tests/services/api/ -v
- **Success**:
  - All API unit tests pass
  - No new errors or failures introduced
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 275) - Verify all tests pass
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: Integrate DiscordAPIClient in Bot Service

### Task 3.1: Create bot service singleton for DiscordAPIClient

Create a singleton instance of DiscordAPIClient in bot service with bot config credentials.

- **Files**:
  - Create: services/bot/dependencies/discord_client.py
- **Success**:
  - New module exports get_discord_client() function
  - Singleton pattern matches API implementation
  - Uses credentials from services.bot.config
  - Imports from shared.discord.client
  - Returns DiscordAPIClient instance with bot token
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 201-206) - Phase 2 bot integration steps
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 277-282) - Task 3 create bot singleton
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 305-307) - Bot token requirement
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Update get_member_display_info() to use cached client

Replace direct discord.py calls with DiscordAPIClient.get_guild_member() for caching.

- **Files**:
  - Modify: services/bot/utils/discord_format.py
- **Success**:
  - get_member_display_info() imports and uses bot's get_discord_client()
  - Calls DiscordAPIClient.get_guild_member(guild_id, user_id) instead of bot.fetch_guild/guild.fetch_member
  - Extracts display_name and avatar_url from response
  - Maintains same return format as before
  - Function behavior unchanged from caller perspective
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 16-21) - Current get_member_display_info implementation
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 47-58) - Bot direct fetch calls (Lines 49, 57)
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 202) - Update get_member_display_info to use DiscordAPIClient
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 282) - Add caching to member display name and avatar lookups
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 331-335) - Member data structure differences
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Replace uncached fetch calls in role_checker.py

Replace bot.fetch_guild() and guild.fetch_member() calls with cached equivalents.

- **Files**:
  - Modify: services/bot/auth/role_checker.py
- **Success**:
  - All 8 bot.fetch_guild() calls replaced with DiscordAPIClient.fetch_guild()
  - All 5 guild.fetch_member() calls replaced with DiscordAPIClient.get_guild_member()
  - Permission checking logic preserved
  - Error handling maintained
  - Functions: get_user_role_ids(), get_guild_roles(), user_can_manage_guild(), user_can_manage_channels(), is_administrator()
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 50-58) - Role checker uncached calls (Lines 78, 84, 115, 139, 144, 166, 171, 193, 198)
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 100-112) - Duplicate API calls impact
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 204) - Replace bot.fetch_guild() calls
- **Dependencies**:
  - Task 3.1 completion

### Task 3.4: Replace uncached fetch calls in handlers.py

Replace bot.fetch_channel() and bot.fetch_user() calls with cached equivalents.

- **Files**:
  - Modify: services/bot/events/handlers.py
- **Success**:
  - 3 bot.fetch_channel() calls replaced (Lines 167, 275, 564)
  - 1 bot.fetch_user() call replaced (Line 454)
  - Event handling logic preserved
  - Error handling maintained
  - Message sending and cleanup functions work correctly
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 42-48) - Handler uncached calls
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 103-107) - Fetch channel and user duplicate calls
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 203-204) - Replace bot.fetch_channel() calls
- **Dependencies**:
  - Task 3.1 completion

### Task 3.5: Verify bot unit tests pass

Run bot service tests to ensure no functionality broken by integration.

- **Files**:
  - Run: uv run pytest tests/services/bot/ -v
- **Success**:
  - All bot unit tests pass
  - No new errors or failures introduced
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 295-297) - Test success criteria
- **Dependencies**:
  - Tasks 3.2, 3.3, 3.4 completion

## Phase 4: Consolidate Cache Keys

### Task 4.1: Audit and document all cache key patterns

Document current cache key patterns across all services and identify inconsistencies.

- **Files**:
  - Read: shared/cache/keys.py
  - Read: shared/discord/client.py (cache key usage)
  - Read: services/api/services/display_names.py
- **Success**:
  - All cache key patterns documented
  - Inconsistencies identified (display_avatar: vs discord: prefixes)
  - Recommendation created for standardization
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 126-147) - Cache key patterns
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 179-183) - Cache key conflicts risk
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 311-316) - Cache key consolidation notes
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Update DiscordAPIClient to use CacheKeys constants

Replace inline cache key strings with shared.cache.keys.CacheKeys patterns.

- **Files**:
  - Modify: shared/discord/client.py
  - Potentially modify: shared/cache/keys.py (add missing patterns)
- **Success**:
  - All cache key strings replaced with CacheKeys.method_name() calls
  - No f"discord:..." or other inline strings remain
  - Cache behavior unchanged
  - TTL constants from shared.cache.ttl used consistently
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 287-292) - Task 4 consolidate cache keys
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 311-316) - Cache key standardization
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Update DisplayNameResolver cache keys for consistency

Align DisplayNameResolver cache keys with CacheKeys patterns.

- **Files**:
  - Modify: services/api/services/display_names.py
  - Modify: shared/cache/keys.py (if new patterns needed)
- **Success**:
  - DisplayNameResolver uses CacheKeys.display_name_avatar() or equivalent
  - Backward compatibility maintained (cache warming may be needed)
  - Consistent with DiscordAPIClient patterns
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 29-33) - DisplayNameResolver current implementation
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 208-210) - Phase 3 merge display_name_avatar cache
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 311-316) - Cache key inconsistencies
- **Dependencies**:
  - Task 4.2 completion

## Phase 5: Testing and Validation

### Task 5.1: Run full test suite

Execute all unit tests for API and bot services.

- **Files**:
  - Run: uv run pytest tests/services/ -v
- **Success**:
  - All API tests pass
  - All bot tests pass
  - No regressions introduced
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 293-297) - Task 5 testing requirements
- **Dependencies**:
  - Phase 4 completion

### Task 5.2: Verify integration tests pass

Run integration tests that involve both API and bot services.

- **Files**:
  - Run: uv run pytest tests/integration/ -v
- **Success**:
  - All integration tests pass
  - Cross-service functionality works correctly
  - Cache sharing between services verified
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 298) - Integration tests verification
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Manual testing of avatar display and member info

Perform manual testing to verify avatar display and member info work correctly.

- **Files**:
  - Test in: Frontend UI (game cards, user profiles)
  - Test in: Discord (bot message embeds)
- **Success**:
  - User avatars display correctly in frontend
  - Display names show correctly in frontend
  - Bot embeds show correct user info
  - No broken images or missing data
  - Cache hit rate logs show >80% hits for member info
- **Research References**:
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 299) - Manual testing of avatar display
  - #file:../research/20251220-discord-client-consolidation-research.md (Lines 302-304) - Success criteria for avatar display
- **Dependencies**:
  - Task 5.2 completion

## Dependencies

- aiohttp (already in API dependencies)
- discord.py (already in bot dependencies)
- shared.cache.client.RedisClient (already in both services)
- shared.cache.keys.CacheKeys (already in both services)
- shared.cache.ttl.CacheTTL (already in both services)

## Success Criteria

- All 19 API files successfully import from shared.discord.client
- Bot service uses DiscordAPIClient for get_member_display_info() with caching
- 18+ uncached Discord API calls in bot replaced with cached versions
- Cache hit rate > 80% for member info in bot service
- All unit tests pass (API and bot)
- All integration tests pass
- Avatar display works correctly in frontend and Discord embeds
- No increase in Discord API rate limit errors
- Cache key patterns are consistent across services
