<!-- markdownlint-disable-file -->

# Task Details: Duplicate Code Elimination

## Research Reference

**Source Research**: #file:../research/20260114-duplicate-code-elimination-research.md

## Phase 1: High-Impact Template Response Duplication

### Task 1.1: Create build_template_response helper function with unit tests

Create helper function in services/api/routes/templates.py and corresponding unit tests.

- **Files**:
  - services/api/routes/templates.py - Add build_template_response() function
  - tests/services/api/routes/test_templates.py - Add unit tests for helper

- **Implementation**:
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

- **Unit Tests**:
  - Test with valid template object
  - Test channel name resolution
  - Test with null optional fields
  - Mock discord_client.fetch_channel_name_safe

- **Success**:
  - Helper function created and properly typed
  - All unit tests pass
  - Function handles all template fields correctly

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 95-130) - Template response builder implementation

- **Dependencies**: None

### Task 1.2: Refactor GET /templates/{template_id} endpoint

Replace duplicated response construction with build_template_response() helper.

- **Files**:
  - services/api/routes/templates.py (lines 202-231) - Replace with helper call

- **Success**:
  - Endpoint uses helper function
  - Existing tests pass
  - No behavioral changes

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 55-58) - GET endpoint duplication

- **Dependencies**: Task 1.1 completion

### Task 1.3: Refactor POST /templates endpoint

Replace duplicated response construction with build_template_response() helper.

- **Files**:
  - services/api/routes/templates.py (lines 137-166) - Replace with helper call

- **Success**:
  - Endpoint uses helper function
  - Existing tests pass
  - No behavioral changes

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 55-58) - POST endpoint duplication

- **Dependencies**: Task 1.1 completion

### Task 1.4: Refactor PUT /templates/{template_id} endpoint

Replace duplicated response construction with build_template_response() helper.

- **Files**:
  - services/api/routes/templates.py (lines 255-286) - Replace with helper call

- **Success**:
  - Endpoint uses helper function
  - Existing tests pass
  - No behavioral changes

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 54-56) - PUT endpoint duplication

- **Dependencies**: Task 1.1 completion

### Task 1.5: Refactor POST /templates/{template_id}/set-default endpoint

Replace duplicated response construction with build_template_response() helper.

- **Files**:
  - services/api/routes/templates.py (lines 337-368) - Replace with helper call

- **Success**:
  - Endpoint uses helper function
  - Existing tests pass
  - No behavioral changes

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 54-56) - Set default endpoint duplication

- **Dependencies**: Task 1.1 completion

## Phase 2: High-Impact Discord API Error Handling

### Task 2.1: Create _make_api_request base method with unit tests

Create generic HTTP request handler in DiscordClient class with comprehensive unit tests.

- **Files**:
  - shared/discord/client.py - Add _make_api_request() method
  - tests/shared/discord/test_client.py - Add unit tests

- **Implementation**:
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

- **Unit Tests**:
  - Test successful GET request with caching
  - Test successful POST request without caching
  - Test 404 error with cache invalidation
  - Test 400/500 errors with proper exception
  - Test network error handling
  - Mock aiohttp session and Redis client

- **Success**:
  - Base method created with proper error handling
  - All unit tests pass
  - Logging and caching work correctly

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 132-178) - Discord API request base method

- **Dependencies**: None

### Task 2.2: Refactor exchange_code method

Replace HTTP handling with _make_api_request() call.

- **Files**:
  - shared/discord/client.py (lines 167-183) - Refactor to use base method

- **Success**:
  - Method uses _make_api_request()
  - Existing tests pass
  - OAuth token exchange still works

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 61-63) - OAuth operations duplication

- **Dependencies**: Task 2.1 completion

### Task 2.3: Refactor refresh_token method

Replace HTTP handling with _make_api_request() call.

- **Files**:
  - shared/discord/client.py (lines 208-224) - Refactor to use base method

- **Success**:
  - Method uses _make_api_request()
  - Existing tests pass
  - Token refresh still works

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 61-63) - OAuth operations duplication

- **Dependencies**: Task 2.1 completion

### Task 2.4: Refactor fetch_guild method

Replace HTTP handling with _make_api_request() call.

- **Files**:
  - shared/discord/client.py (lines 472-490) - Refactor to use base method

- **Success**:
  - Method uses _make_api_request()
  - Existing tests pass
  - Guild fetching with caching still works

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 59-60) - fetch_guild duplication

- **Dependencies**: Task 2.1 completion

### Task 2.5: Refactor fetch_user method

Replace HTTP handling with _make_api_request() call.

- **Files**:
  - shared/discord/client.py (lines 572-589) - Refactor to use base method

- **Success**:
  - Method uses _make_api_request()
  - Existing tests pass
  - User fetching with caching still works

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 60-61) - fetch_user duplication

- **Dependencies**: Task 2.1 completion

### Task 2.6: Refactor get_guild_member method

Replace HTTP handling with _make_api_request() call.

- **Files**:
  - shared/discord/client.py (lines 613-628) - Refactor to use base method

- **Success**:
  - Method uses _make_api_request()
  - Existing tests pass
  - Guild member fetching still works

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 62-63) - get_guild_member duplication

- **Dependencies**: Task 2.1 completion

## Phase 3: Medium-Impact Game Embed Formatting

### Task 3.1: Create build_game_list_embed function with unit tests

Create shared Discord embed builder module and unit tests.

- **Files**:
  - shared/discord/game_embeds.py - New module with build_game_list_embed()
  - tests/shared/discord/test_game_embeds.py - New test file

- **Implementation**:
  ```python
  from datetime import datetime, UTC
  import discord

  DEFAULT_PAGE_SIZE = 10

  def build_game_list_embed(
      games: list,
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

      for game in games[:DEFAULT_PAGE_SIZE]:
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

- **Unit Tests**:
  - Test with 0 games (empty list)
  - Test with < 10 games
  - Test with exactly 10 games
  - Test with > 10 games (pagination)
  - Test with games having null descriptions
  - Test with custom title and color

- **Success**:
  - New module created
  - All unit tests pass
  - Embed formatting matches existing behavior

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 180-229) - Game embed builder

- **Dependencies**: None

### Task 3.2: Refactor list_games command to use shared embed builder

Replace inline embed construction with shared builder.

- **Files**:
  - services/bot/commands/list_games.py (lines 168-188) - Replace with helper call

- **Success**:
  - Command uses shared embed builder
  - Existing tests pass
  - No visual changes to Discord output

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 64-65) - list_games duplication

- **Dependencies**: Task 3.1 completion

### Task 3.3: Refactor my_games command to use shared embed builder

Replace inline embed construction with shared builder.

- **Files**:
  - services/bot/commands/my_games.py (lines 183-203) - Replace with helper call

- **Success**:
  - Command uses shared embed builder
  - Existing tests pass
  - No visual changes to Discord output

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 64-65) - my_games duplication

- **Dependencies**: Task 3.1 completion

## Phase 4: Medium-Impact TypeScript Type Definitions

### Task 4.1: Refactor Template interface to be single source of truth

Consolidate duplicate Template type definitions using TypeScript utility types.

- **Files**:
  - frontend/src/types/index.ts (lines 150-185) - Keep base Template interface
  - frontend/src/types/index.ts (lines 193-222) - Replace TemplateUpdate with utility type

- **Implementation**:
  ```typescript
  // Keep this as-is (base Template interface)
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

  // Replace duplicate with utility type
  export type TemplateUpdate = Partial<Omit<Template, 'id' | 'guild_id' | 'channel_name'>>;
  ```

- **Success**:
  - Template interface unchanged
  - TemplateUpdate becomes derived type
  - TypeScript compilation successful

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 231-247) - TypeScript utility types

- **Dependencies**: None

### Task 4.2: Verify TypeScript compilation and type checking

Ensure no type errors after refactoring.

- **Files**: All TypeScript files using Template types

- **Success**:
  - npm run type-check passes
  - npm run build succeeds
  - No new TypeScript errors

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 66-68) - Type definition duplication

- **Dependencies**: Task 4.1 completion

## Phase 5: Medium-Impact Channel Message Fetching

### Task 5.1: Create _fetch_channel_and_message helper with unit tests

Create helper method in EventHandlers class with unit tests.

- **Files**:
  - services/bot/events/handlers.py - Add _fetch_channel_and_message() method
  - tests/services/bot/events/test_handlers.py - Add unit tests

- **Implementation**:
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

- **Unit Tests**:
  - Test with valid channel and message IDs
  - Test with invalid channel ID
  - Test with non-TextChannel type
  - Test with invalid message ID
  - Mock bot.get_channel and bot.fetch_channel

- **Success**:
  - Helper method created
  - All unit tests pass
  - Error handling works correctly

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 249-290) - Channel message fetcher

- **Dependencies**: None

### Task 5.2: Refactor first event handler to use helper

Replace inline channel/message fetching with helper call.

- **Files**:
  - services/bot/events/handlers.py (lines 663-680) - Replace with helper call

- **Success**:
  - Event handler uses helper method
  - Existing tests pass
  - Message updates still work

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 63-64) - Event handler duplication

- **Dependencies**: Task 5.1 completion

### Task 5.3: Refactor second event handler to use helper

Replace inline channel/message fetching with helper call.

- **Files**:
  - services/bot/events/handlers.py (lines 737-754) - Replace with helper call

- **Success**:
  - Event handler uses helper method
  - Existing tests pass
  - Message updates still work

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 63-64) - Event handler duplication

- **Dependencies**: Task 5.1 completion

## Phase 6: Verification and Documentation

### Task 6.1: Run jscpd to verify duplication reduction

Verify code duplication has been reduced below 2% target.

- **Command**: `npx jscpd services shared frontend/src --config .jscpd.json`

- **Success**:
  - Duplication percentage < 2%
  - Significant reduction from initial 3.68%
  - Clone count significantly reduced

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 1-14) - Initial jscpd analysis

- **Dependencies**: All previous phases complete

### Task 6.2: Run full test suite to ensure no regressions

Verify all tests pass after refactoring.

- **Commands**:
  - `uv run pytest tests/ --tb=short`
  - `cd frontend && npm run test`

- **Success**:
  - All Python unit tests pass
  - All Python integration tests pass
  - All TypeScript tests pass
  - No behavioral changes detected

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 372-385) - Testing strategy

- **Dependencies**: All previous phases complete

### Task 6.3: Update jscpd threshold configuration

Lower jscpd threshold now that duplication is reduced.

- **Files**:
  - .jscpd.json - Update threshold from 5 to 3

- **Success**:
  - Threshold updated
  - Pre-commit hook passes
  - Documentation updated if needed

- **Research References**:
  - #file:../research/20260114-duplicate-code-elimination-research.md (Lines 353-365) - Success criteria

- **Dependencies**: Tasks 6.1 and 6.2 completion

## Dependencies

- No new external dependencies required
- Python 3.13 standard library
- TypeScript 5.x utility types
- Existing Discord.py and FastAPI frameworks

## Success Criteria

- Code duplication reduced from 3.68% to under 2%
- All existing unit tests pass
- All integration tests pass
- No behavioral changes to APIs or bot commands
- Code coverage maintained or improved
- jscpd threshold lowered to 3% or less
- TypeScript compilation successful
