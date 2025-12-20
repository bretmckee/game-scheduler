<!-- markdownlint-disable-file -->
# Task Research Notes: Discord API Client Consolidation

## Research Executed

### File Analysis
- services/api/auth/discord_client.py
  - 740-line file implementing DiscordAPIClient with comprehensive Redis caching
  - Uses aiohttp for REST API calls with bot token authentication
  - Caches: user_guilds (300s), channels (300s), guilds (600s), guild_roles (300s), users (300s)
  - Implements double-checked locking pattern for concurrent requests
  - Singleton pattern via get_discord_client() function
  - Has methods: exchange_code, refresh_token, get_user_info, get_user_guilds, get_bot_guilds, get_guild_channels, fetch_channel, fetch_guild, fetch_guild_roles, fetch_user, get_guild_member, get_guild_members_batch
  - Includes convenience wrappers: fetch_channel_name_safe, fetch_user_display_name_safe, fetch_guild_name_safe

- services/bot/utils/discord_format.py
  - get_member_display_info() uses discord.py Client directly (no caching)
  - Calls bot.get_guild(), bot.fetch_guild(), guild.get_member(), guild.fetch_member()
  - Returns display_name and avatar_url from discord.py Member object
  - No Redis integration at all

- services/bot/auth/cache.py
  - RoleCache class for caching user roles only (not guild member data)
  - Uses shared.cache.client.RedisClient
  - Caches user_roles with keys.CacheKeys.user_roles(user_id, guild_id)
  - Does NOT cache member display names or avatars

- services/api/services/display_names.py
  - DisplayNameResolver uses DiscordAPIClient from services.api.auth
  - Caches display names and avatars with key display_avatar:<guild_id>:<user_id>
  - TTL: 300 seconds (5 minutes)
  - Uses get_guild_members_batch() to fetch member data

### Code Search Results
- `from services.api.auth import discord_client`
  - Found in 19 API service files (routes, services, auth modules)
  - All within services/api/ directory - NO imports in services/bot/

- discord.Client usage in bot - **13 uncached REST API call locations identified**:

  **services/bot/events/handlers.py:**
  - Line 167: `bot.fetch_channel()` in game.created event handler
  - Line 275: `bot.fetch_channel()` in game.deleted event handler
  - Line 454: `bot.fetch_user()` for sending DMs to users
  - Line 564: `bot.fetch_channel()` in cleanup message handler

  **services/bot/auth/role_checker.py:**
  - Line 78: `bot.fetch_guild()` in get_user_role_ids()
  - Line 84: `guild.fetch_member()` in get_user_role_ids()
  - Line 115: `bot.fetch_guild()` in get_guild_roles()
  - Line 139: `bot.fetch_guild()` in user_can_manage_guild()
  - Line 144: `guild.fetch_member()` in user_can_manage_guild()
  - Line 166: `bot.fetch_guild()` in user_can_manage_channels()
  - Line 171: `guild.fetch_member()` in user_can_manage_channels()
  - Line 193: `bot.fetch_guild()` in is_administrator()
  - Line 198: `guild.fetch_member()` in is_administrator()

  **services/bot/utils/discord_format.py:**
  - Line 49: `bot.fetch_guild()` in get_member_display_info()
  - Line 57: `guild.fetch_member()` in get_member_display_info()

  All these are direct Discord API calls with NO Redis caching

### External Research
None required - this is internal architecture analysis.

### Project Conventions
- Shared code lives in shared/ directory
- shared/cache/ contains Redis client and key patterns
- shared/cache/ttl.py defines CacheTTL constants
- shared/cache/keys.py defines CacheKeys patterns
- Services use shared modules via: from shared.cache import client, keys, ttl

## Key Discoveries

### Current Architecture

**API Service:**
```
services/api/auth/discord_client.py (DiscordAPIClient)
  ↓
aiohttp REST client + Redis caching
  ↓
Discord REST API (bot token)
```

**Bot Service:**
```
services/bot/utils/discord_format.py (get_member_display_info)
  ↓
discord.py Client methods (no caching)
  ↓
Discord REST API (bot token) + Gateway WebSocket
```

### Duplicate API Calls Identified

Both services make these Discord API calls without shared caching:

1. **Fetch Guild** - API caches (600s TTL), bot makes 8 uncached calls
   - role_checker.py: Lines 78, 115, 139, 166, 193 (permission checks)
   - discord_format.py: Line 49 (get member info)

2. **Fetch Channel** - API caches (300s TTL), bot makes 3 uncached calls
   - handlers.py: Lines 167, 275, 564 (event handling, message cleanup)

3. **Fetch User** - API caches (300s TTL), bot makes 1 uncached call
   - handlers.py: Line 454 (send DM to user)

4. **Fetch Guild Member** - API has get_guild_member() method, bot makes 6 uncached calls
   - role_checker.py: Lines 84, 144, 171, 198 (permission checks)
   - discord_format.py: Line 57 (get member info)

5. **Fetch Guild Roles** - API caches (300s TTL), bot has separate RoleCache but still fetches guild/member

**Impact:** Bot makes ~18+ uncached Discord API calls across these functions, many of which are called repeatedly for permission checks and event handling. This contributes significantly to Discord API rate limit consumption.

### Cache TTL Configuration

From shared/cache/ttl.py:
```python
class CacheTTL:
    DISPLAY_NAME = 300  # 5 minutes
    USER_ROLES = 300  # 5 minutes
    USER_GUILDS = 300  # 5 minutes
    DISCORD_CHANNEL = 300  # 5 minutes
    DISCORD_GUILD = 600  # 10 minutes
    DISCORD_USER = 300  # 5 minutes
    GUILD_CONFIG = 600  # 10 minutes
```

### Cache Key Patterns

From shared/cache/keys.py:
```python
display_name(guild_id, user_id) -> f"display:{guild_id}:{user_id}"
display_name_avatar(user_id, guild_id) -> f"display_avatar:{guild_id}:{user_id}"
user_roles(user_id, guild_id) -> f"user_roles:{user_id}:{guild_id}"
guild_config(guild_id) -> f"guild_config:{guild_id}"
```

DiscordAPIClient uses its own key patterns:
```python
f"user_guilds:{user_id}"
f"discord:channel:{channel_id}"
f"discord:guild:{guild_id}"
f"discord:guild_roles:{guild_id}"
f"discord:user:{user_id}"
```

### Discord.py vs aiohttp Difference

**discord.py (Bot):**
- Provides Gateway WebSocket connection (required for events, interactions)
- Has REST API client built-in for fetch operations
- Maintains internal cache of guilds, channels, members (in memory, not Redis)
- Member objects have display_name, avatar properties pre-computed
- Cannot be shared - tied to bot instance lifecycle

**aiohttp (API):**
- REST-only client (no WebSocket)
- No built-in caching - we implement Redis caching
- Used for stateless REST operations
- Can be shared across requests and services

### Dependencies

**DiscordAPIClient dependencies:**
- aiohttp (HTTP client)
- services.api.config (for credentials)
- shared.cache.client (Redis)
- shared.cache.ttl (TTL constants)

**Bot dependencies:**
- discord.py (Gateway + REST)
- services.bot.config (for credentials)
- shared.cache.client (for RoleCache only)

## Recommended Approach

**Move DiscordAPIClient to shared layer and use it in both services for REST operations with caching.**

### Architecture Design

```
shared/discord/client.py (DiscordAPIClient - moved from API)
  ↓
  ├─> services/api/ (for all Discord REST calls)
  └─> services/bot/ (for cached REST calls)
        └─> discord.py (WebSocket only, no REST caching)
```

### Implementation Strategy

**Phase 1: Move to Shared**
1. Move services/api/auth/discord_client.py → shared/discord/client.py
2. Update DiscordAPIClient.__init__ to not depend on services.api.config
3. Accept credentials as constructor parameters
4. Update all API imports from `services.api.auth.discord_client` → `shared.discord.client`

**Phase 2: Bot Integration**
1. Create shared DiscordAPIClient instance in bot service
2. Update get_member_display_info() to use DiscordAPIClient.get_guild_member() with caching
3. Replace bot.fetch_channel() calls with DiscordAPIClient.fetch_channel() (cached)
4. Replace bot.fetch_guild() calls with DiscordAPIClient.fetch_guild() (cached)
5. Keep discord.py Client for WebSocket and in-memory cache

**Phase 3: Consolidate Caching**
1. Merge display_name_avatar cache with DiscordAPIClient member caching
2. Consider removing DisplayNameResolver in favor of DiscordAPIClient methods
3. Consolidate cache key patterns

### Benefits

1. **Reduced API Calls**: Single cache shared across services
2. **Rate Limit Protection**: Discord has 5000 req/hour limit - shared cache reduces risk
3. **Consistency**: Both services see same cached data with same TTL
4. **Performance**: Cache hits are 100x faster than API calls
5. **Code Reuse**: Eliminate duplicate logic between API and bot

### Risks and Mitigation

**Risk 1: Import Cycles**
- Current: API can't import from bot, bot can't import from API
- Mitigation: Shared layer breaks the cycle - both can import from shared

**Risk 2: Configuration Differences**
- API uses services.api.config, bot uses services.bot.config
- Mitigation: Pass credentials as constructor params, let each service configure

**Risk 3: Breaking Existing API**
- 19 files import discord_client from services.api.auth
- Mitigation: Update all imports in single commit, test thoroughly

**Risk 4: discord.py Integration**
- Bot still needs discord.py for WebSocket
- Mitigation: Use DiscordAPIClient for REST, keep discord.py for Gateway

**Risk 5: Cache Key Conflicts**
- Different key patterns in use (display_avatar: vs discord:)
- Mitigation: Consolidate to single pattern in shared.cache.keys

### Alternative Approaches Considered

**Alternative 1: Add Caching to Bot Only**
- Duplicate DiscordAPIClient logic in bot service
- ❌ Rejected: Creates code duplication and cache fragmentation

**Alternative 2: API Calls Bot via HTTP**
- Bot exposes HTTP endpoint for cached Discord data
- ❌ Rejected: Adds latency, complexity, and failure points

**Alternative 3: Shared Redis Cache Only**
- Keep separate clients, only share Redis keys
- ❌ Rejected: Still duplicates API call logic and error handling

**Alternative 4: Use discord.py in API**
- Replace aiohttp with discord.py Client in API
- ❌ Rejected: API doesn't need Gateway WebSocket, heavy dependency

## Implementation Guidance

### Objectives
1. Move DiscordAPIClient to shared layer accessible to both services
2. Maintain existing caching behavior and TTLs
3. Update all imports across API service (19 files)
4. Integrate DiscordAPIClient into bot service for REST operations
5. Preserve discord.py for WebSocket/Gateway operations in bot
6. Consolidate cache key patterns and TTLs

### Key Tasks

**Task 1: Create Shared Discord Module**
- Create shared/discord/__init__.py
- Move discord_client.py to shared/discord/client.py
- Update DiscordAPIClient to accept credentials as constructor params
- Remove dependency on services.api.config
- Update imports within moved file (shared.cache remains same)

**Task 2: Update API Service**
- Find all 19 files importing from services.api.auth.discord_client
- Update imports to shared.discord.client
- Update get_discord_client() singleton to use shared module
- Verify all tests pass

**Task 3: Integrate in Bot Service**
- Create bot service singleton for DiscordAPIClient
- Update get_member_display_info() to use DiscordAPIClient.get_guild_member()
- Add caching to member display name and avatar lookups
- Replace other bot.fetch_* calls with DiscordAPIClient equivalents where beneficial
- Maintain discord.py Client for WebSocket operations

**Task 4: Consolidate Cache Keys**
- Audit all cache key usage
- Standardize on shared.cache.keys.CacheKeys patterns
- Update DiscordAPIClient to use CacheKeys instead of inline strings
- Document cache key patterns in shared/cache/keys.py

**Task 5: Testing**
- Run all existing unit tests for API
- Run all existing unit tests for bot
- Run integration tests
- Manual testing of avatar display (Task 3.4)
- Verify cache hit rates improve in bot service

### Dependencies
- aiohttp (already in API dependencies)
- discord.py (already in bot dependencies)
- shared.cache.client (already in both)
- No new external dependencies required

### Success Criteria
- All 19 API files successfully import from shared.discord.client
- Bot service uses DiscordAPIClient for get_member_display_info()
- Cache hit rate > 80% for member info in bot service
- All existing tests pass
- No increase in Discord API rate limit errors
- Avatar display works in both frontend and Discord embeds

## Notes

**Critical Implementation Detail:**
The DiscordAPIClient needs bot token for all operations. Both API and bot services already have bot tokens in their configs. When moving to shared, the client must accept credentials as constructor parameters rather than reading from a service-specific config module.

**Cache Key Consolidation:**
Current inconsistency:
- DisplayNameResolver: `display_avatar:<guild_id>:<user_id>`
- DiscordAPIClient: `discord:channel:<id>`, `discord:guild:<id>`
- RoleCache: `user_roles:<user_id>:<guild_id>`

Should standardize to CacheKeys class patterns for consistency.

**Discord.py Internal Cache:**
discord.py maintains its own in-memory cache of guilds, channels, and members. This is separate from Redis and only available within the bot process. We can leverage this for get_guild()/get_member() (no API call) vs fetch_guild()/fetch_member() (makes API call). The shared DiscordAPIClient complements this with Redis caching across both services.

**Member Data Structure:**
- discord.py Member object: Has display_name (computed), avatar (Asset), roles, etc.
- DiscordAPIClient response: Raw JSON from API with user nested inside member
- Need adapter to normalize between these formats

**Rate Limiting:**
Discord API rate limits are per-token, not per-client instance. Sharing cache reduces total API calls across both services using the same bot token. Current rate limit: 5000 requests/hour for authenticated requests.
