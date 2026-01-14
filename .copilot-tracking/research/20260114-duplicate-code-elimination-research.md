<!-- markdownlint-disable-file -->
# Task Research Notes: Duplicate Code Elimination

## Research Executed

### Tool Analysis
- jscpd duplicate code detector
  - Configured with 6 line / 50 token threshold
  - Scanned services/, shared/, frontend/src/
  - Found 31 clones across 120 files
  - 3.68% overall duplication rate

### File Analysis
- services/api/routes/templates.py
  - Multiple instances of TemplateResponse construction (31+ lines each)
  - 4 separate instances of nearly identical response serialization
- shared/discord/client.py
  - 6 instances of HTTP request error handling patterns (15-18 lines each)
  - Common pattern: request → log → check status → handle errors → cache
- frontend/src/types/index.ts
  - Template interface fields duplicated between full and partial types
  - 14-line type definitions repeated with optional modifiers
- services/bot/commands/list_games.py + my_games.py
  - 20 lines of identical Discord embed formatting
- services/bot/events/handlers.py
  - 17 lines of channel/message fetching duplicated twice

### Code Search Results
- Template response construction pattern appears in 4+ endpoints
- Discord API error handling appears in 6+ methods
- Game embed formatting appears in 2 commands
- Permission verification pattern appears in 4+ dependency functions

## Key Discoveries

### Top 10 Duplicated Code Areas

| Rank | Files | Size | Description |
|------|-------|------|-------------|
| 1 | services/api/routes/templates.py (337-368, 255-286) | 31 lines, 210 tokens | Template Response Construction with channel resolution |
| 2 | services/api/routes/templates.py (202-231, 137-166) | 29 lines, 206 tokens | Template Response Creation (GET/POST variants) |
| 3 | shared/discord/client.py (472-490, 417-437) | 18 lines, 191 tokens | Discord API Error Handling (fetch_guild) |
| 4 | shared/discord/client.py (572-589, 417-437) | 17 lines, 189 tokens | Discord API Error Handling (fetch_user) |
| 5 | services/bot/events/handlers.py (737-754, 663-680) | 17 lines, 157 tokens | Discord Channel Message Fetching |
| 6 | list_games.py (168-188) vs my_games.py (183-203) | 20 lines, 146 tokens | Game List Embed Formatting |
| 7 | shared/discord/client.py (208-224, 167-183) | 16 lines, 133 tokens | OAuth Token Operations |
| 8 | shared/discord/client.py (613-628, 524-540) | 15 lines, 136 tokens | Discord API GET Requests |
| 9 | frontend/src/types/index.ts (171-185, 150-164) | 14 lines, 143 tokens | TypeScript Template Interface Fields |
| 10 | frontend/src/types/index.ts (211-222, 193-204) | 11 lines, 135 tokens | TypeScript Template Update Interface |

### Duplication Categories

**1. API Response Serialization (~90 lines total)**
- Location: services/api/routes/templates.py
- Pattern: Database model → API schema conversion with channel resolution
- Instances: 4 separate endpoint handlers
- Impact: HIGH - repeated in every template CRUD operation

**2. Discord HTTP Error Handling (~80 lines total)**
- Location: shared/discord/client.py
- Pattern: HTTP request → log → status check → error handling → caching
- Instances: 6+ API methods (fetch_guild, fetch_user, get_guild_member, etc.)
- Impact: HIGH - affects all Discord API interactions

**3. TypeScript Type Definitions (~25 lines total)**
- Location: frontend/src/types/index.ts
- Pattern: Full interface vs. partial interface for updates
- Instances: 2 (Template and TemplateUpdate)
- Impact: MEDIUM - maintenance burden for type changes

**4. Discord UI Formatting (~40 lines total)**
- Location: services/bot/commands/
- Pattern: Game list embed construction with timestamps and pagination
- Instances: 2 commands (list_games, my_games)
- Impact: MEDIUM - inconsistent if not kept in sync

**5. Channel Message Operations (~35 lines total)**
- Location: services/bot/events/handlers.py
- Pattern: Channel validation → fetch channel → fetch message → update
- Instances: 2 event handlers
- Impact: MEDIUM - error handling consistency risk

**6. Permission Verification (~45 lines total)**
- Location: services/api/dependencies/permissions.py
- Pattern: FastAPI dependency function structure for permission checks
- Instances: 3+ permission functions
- Impact: LOW - similar but with different permission types

## Recommended Approach

### Phase 1: High-Impact Quick Wins

**1.1 Extract Template Response Builder**

Create helper in services/api/routes/templates.py or services/api/services/template_service.py:

```python
async def build_template_response(
    template: Template,
    discord_client: discord_client_module.DiscordClient
) -> template_schemas.TemplateResponse:
    """Build TemplateResponse with channel name resolution."""
    channel_name = await discord_client.fetch_channel_name_safe(
        template.channel.channel_id
    )

    return template_schemas.TemplateResponse(
        id=template.id,
        guild_id=template.guild_id,
        name=template.name,
        description=template.description,
        order=template.order,
        is_default=template.is_default,
        channel_id=template.channel_id,
        channel_name=channel_name,
        notify_role_ids=template.notify_role_ids,
        allowed_player_role_ids=template.allowed_player_role_ids,
        allowed_host_role_ids=template.allowed_host_role_ids,
        max_players=template.max_players,
        expected_duration_minutes=template.expected_duration_minutes,
        reminder_minutes=template.reminder_minutes,
        where=template.where,
        signup_instructions=template.signup_instructions,
        allowed_signup_methods=template.allowed_signup_methods,
        default_signup_method=template.default_signup_method,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )
```

**Impact:** Eliminates ~90 lines of duplication across 4 endpoints

**1.2 Create Discord API Request Base Method**

Add to DiscordClient class in shared/discord/client.py:

```python
async def _make_api_request(
    self,
    method: str,
    url: str,
    operation_name: str,
    headers: dict[str, str],
    cache_key: str | None = None,
    cache_ttl: int | None = None,
    session: aiohttp.ClientSession | None = None,
    **request_kwargs
) -> dict[str, Any]:
    """
    Generic Discord API request handler with error handling and caching.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full request URL
        operation_name: Human-readable operation name for logging
        headers: Request headers
        cache_key: Optional cache key for GET requests
        cache_ttl: Optional cache TTL in seconds
        session: Optional existing session
        **request_kwargs: Additional arguments for aiohttp request

    Returns:
        Response JSON data

    Raises:
        DiscordAPIError: On non-200 status
    """
    redis = await cache.get_redis_client()
    self._log_request(method, url, operation_name)

    try:
        session_to_use = session or self.session
        async with session_to_use.request(
            method,
            url,
            headers=headers,
            **request_kwargs
        ) as response:
            response_data = await response.json()
            self._log_response(response)

            if response.status != status.HTTP_200_OK:
                error_msg = response_data.get("message", "Unknown error")
                if response.status == status.HTTP_404_NOT_FOUND and cache_key:
                    await redis.set(cache_key, json.dumps({"error": "not_found"}), ttl=60)
                raise DiscordAPIError(response.status, error_msg, dict(response.headers))

            # Cache successful result if requested
            if cache_key and cache_ttl:
                await redis.set(cache_key, json.dumps(response_data), ttl=cache_ttl)

            return response_data

    except aiohttp.ClientError as e:
        logger.error(f"Network error in {operation_name}: {e}")
        raise
```

**Impact:** Eliminates ~80 lines of duplication across 6+ methods

### Phase 2: Medium-Impact Refactoring

**2.1 Extract Game List Embed Builder**

Create shared/discord/game_embeds.py:

```python
def build_game_list_embed(
    games: list[Game],
    title: str,
    color: discord.Color = discord.Color.blue()
) -> discord.Embed:
    """
    Build Discord embed for game list display.

    Args:
        games: List of games to display
        title: Embed title
        color: Embed color

    Returns:
        Formatted Discord embed with game list
    """
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(UTC),
    )

    for game in games[:10]:
        unix_timestamp = int(game.scheduled_at.timestamp())
        value = f"🕒 <t:{unix_timestamp}:F> (<t:{unix_timestamp}:R>)\n"
        if game.description:
            value += f"{game.description[:100]}\n"
        value += f"ID: `{game.id}`"

        embed.add_field(
            name=game.title,
            value=value,
            inline=False,
        )

    if len(games) > DEFAULT_PAGE_SIZE:
        embed.set_footer(text=f"Showing {DEFAULT_PAGE_SIZE} of {len(games)} games")
    else:
        embed.set_footer(text=f"{len(games)} game(s) found")

    return embed
```

**Impact:** Eliminates ~40 lines of duplication, ensures consistent formatting

**2.2 TypeScript Utility Types**

Refactor frontend/src/types/index.ts:

```typescript
// Define base interface once
export interface Template {
  id: string;
  guild_id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  channel_id: string;
  channel_name: string;
  notify_role_ids: string[] | null;
  allowed_player_role_ids: string[] | null;
  allowed_host_role_ids: string[] | null;
  max_players: number | null;
  expected_duration_minutes: number | null;
  reminder_minutes: number[] | null;
  where: string | null;
  signup_instructions: string | null;
  allowed_signup_methods: string[] | null;
  default_signup_method: string | null;
}

// Create partial type for updates
export type TemplateUpdate = Partial<Omit<Template, 'id' | 'guild_id' | 'channel_name'>>;
```

**Impact:** Eliminates ~25 lines, single source of truth for template fields

**2.3 Extract Channel Message Fetcher**

Add to EventHandlers class in services/bot/events/handlers.py:

```python
async def _fetch_channel_and_message(
    self,
    channel_id: str,
    message_id: str
) -> tuple[discord.TextChannel, discord.Message] | None:
    """
    Fetch Discord channel and message objects with validation.

    Args:
        channel_id: Discord channel ID
        message_id: Discord message ID

    Returns:
        Tuple of (channel, message) or None if not found/invalid
    """
    channel = self.bot.get_channel(int(channel_id))
    if not channel:
        try:
            channel = await self.bot.fetch_channel(int(channel_id))
        except Exception as e:
            logger.error(f"Invalid or inaccessible channel: {channel_id} - {e}")
            return None

    if not channel or not isinstance(channel, discord.TextChannel):
        logger.error(f"Invalid or inaccessible channel: {channel_id}")
        return None

    try:
        message = await channel.fetch_message(int(message_id))
        return (channel, message)
    except Exception as e:
        logger.error(f"Failed to fetch message {message_id}: {e}")
        return None
```

**Impact:** Eliminates ~35 lines, centralizes error handling

### Phase 3: Low-Impact Cleanup

**3.1 Permission Dependency Template**

Consider using a factory function in services/api/dependencies/permissions.py:

```python
def create_permission_dependency(permission_type: str):
    """Factory for creating permission check dependencies."""
    async def permission_checker(
        guild_id: str,
        current_user: auth_schemas.CurrentUser = Depends(auth.get_current_user),
        role_service: roles_module.RoleVerificationService = Depends(get_role_service),
        db: AsyncSession = Depends(database.get_db),
    ) -> auth_schemas.CurrentUser:
        # Common permission check logic
        await role_service.verify_permission(
            current_user.user_id,
            guild_id,
            permission_type,
            db
        )
        return current_user

    return permission_checker

# Usage
require_manage_channels = create_permission_dependency("MANAGE_CHANNELS")
require_manage_roles = create_permission_dependency("MANAGE_ROLES")
```

**Impact:** Eliminates ~45 lines, but may reduce code clarity

## Implementation Guidance

### Objectives
- Reduce code duplication from 3.68% to under 2%
- Improve maintainability through centralized patterns
- Ensure consistent error handling and formatting
- Maintain or improve code readability

### Key Tasks

**Phase 1 (High Priority):**
1. Create build_template_response() helper function
2. Replace 4 instances in templates.py endpoints
3. Create _make_api_request() base method in DiscordClient
4. Refactor 6+ Discord API methods to use base method
5. Add unit tests for new helper functions
6. Run jscpd to verify duplication reduction

**Phase 2 (Medium Priority):**
1. Create shared/discord/game_embeds.py module
2. Extract build_game_list_embed() function
3. Update list_games.py and my_games.py to use shared function
4. Refactor TypeScript types to use Partial utility type
5. Create _fetch_channel_and_message() helper in EventHandlers
6. Update event handler methods

**Phase 3 (Low Priority):**
1. Evaluate permission dependency pattern
2. Implement factory function if beneficial
3. Update all permission dependencies

### Dependencies
- No new external dependencies required
- Python 3.13 standard library
- TypeScript 5.x utility types
- Existing Discord.py and FastAPI frameworks

### Success Criteria
- Code duplication reduced below 2%
- All existing tests pass
- No behavioral changes to APIs or bot commands
- Code coverage maintained or improved
- jscpd threshold can be lowered to 3% or less

### Testing Strategy
1. Unit tests for each new helper function
2. Integration tests for template endpoints
3. Integration tests for Discord client methods
4. Bot command tests for embed formatting
5. Run full test suite to ensure no regressions
6. Manual testing of Discord bot commands
7. Verify jscpd shows reduced duplication

### Risk Assessment
- LOW RISK: Template response builder, game embed formatter
- MEDIUM RISK: Discord API base method (affects many methods)
- LOW RISK: TypeScript type refactoring (compile-time only)
- MEDIUM RISK: Event handler refactoring (affects message updates)

### Notes
- Phase 1 should be completed as a single PR
- Phase 2 can be split into multiple smaller PRs
- Phase 3 is optional and should be evaluated based on team preference
- Pre-commit hook with jscpd already implemented to monitor duplication
