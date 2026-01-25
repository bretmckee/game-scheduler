<!-- markdownlint-disable-file -->

# Task Details: Remaining Code Duplication Elimination

## Research Reference

**Source Research**: #file:../research/20260125-remaining-code-duplication-analysis-research.md

## Phase 1: Quick Wins - Participant Count Query

### Task 1.1: Extract participant count helper function and create unit tests

Create a reusable utility function in `services/bot/handlers/utils.py` to count non-placeholder participants for a game, with comprehensive unit tests.

- **Files**:
  - services/bot/handlers/utils.py - Add new `get_participant_count()` function
  - tests/unit/bot/handlers/test_utils.py - Add unit tests for `get_participant_count()`
- **Success**:
  - Function accepts database session and game_id
  - Returns integer count of participants where user_id is not None
  - Function includes proper type hints and docstring
  - Function is async and properly handles database queries
  - Unit tests cover: normal case with participants, empty game, game with placeholders, non-existent game
  - All tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 191-217) - Participant count query pattern
- **Implementation**:
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

### Task 1.2: Update join_game.py to use helper

Replace inline participant counting logic with utility function call.

- **Files**:
  - services/bot/handlers/join_game.py - Replace lines 156-164
- **Success**:
  - Import `get_participant_count` from utils
  - Replace duplicated query logic with function call
  - Maintain existing behavior and return values
  - Existing integration tests continue to pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 191-217)
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Update leave_game.py to use helper

Replace inline participant counting logic with utility function call.

- **Files**:
  - services/bot/handlers/leave_game.py - Replace lines 128-136
- **Success**:
  - Import `get_participant_count` from utils
  - Replace duplicated query logic with function call
  - Maintain existing behavior and return values
  - Existing integration tests continue to pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 191-217)
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Response Construction Patterns

### Task 2.1: Extract guild config response builder and create unit tests

Create helper function to construct GuildConfigResponse objects consistently, with unit tests.

- **Files**:
  - services/api/routes/guilds.py - Add `_build_guild_config_response()` helper function
  - tests/unit/api/routes/test_guilds.py - Add unit tests for response builder
- **Success**:
  - Function accepts GuildConfiguration, CurrentUser, and AsyncSession
  - Returns GuildConfigResponse with all required fields
  - Fetches guild_name using permissions.get_guild_name()
  - Formats timestamps using isoformat()
  - Includes proper type hints and docstring
  - Unit tests verify: correct field mapping, timestamp formatting, guild_name retrieval, handling of None values
  - All tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 102-129) - Guild response construction pattern
- **Implementation**:
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

### Task 2.2: Update guild routes to use response builder

Replace response construction in get_guild_config, create_guild_config, and update_guild_config.

- **Files**:
  - services/api/routes/guilds.py - Update response construction at lines 122-134, 162-174, 191-205
- **Success**:
  - All three route handlers use `_build_guild_config_response()`
  - Response structure remains identical
  - All existing API tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 102-129)
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Extract channel config response builder and create unit tests

Create helper function to construct ChannelConfigResponse objects consistently, with unit tests.

- **Files**:
  - services/api/routes/channels.py - Add `_build_channel_config_response()` helper function
  - tests/unit/api/routes/test_channels.py - Add unit tests for response builder
- **Success**:
  - Function accepts ChannelConfiguration object
  - Returns ChannelConfigResponse with all required fields
  - Fetches channel_name using discord_client_module.fetch_channel_name_safe()
  - Formats timestamps using isoformat()
  - Includes proper type hints and docstring
  - Unit tests verify: correct field mapping, timestamp formatting, channel_name retrieval, guild relationship handling
  - All tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 131-153) - Channel response construction pattern
- **Implementation**:
  ```python
  async def _build_channel_config_response(
      channel_config: ChannelConfiguration,
  ) -> channel_schemas.ChannelConfigResponse:
      """Build channel configuration response with channel name."""
      channel_name = await discord_client_module.fetch_channel_name_safe(
          channel_config.channel_id
      )
      return channel_schemas.ChannelConfigResponse(
          id=channel_config.id,
          guild_id=channel_config.guild_id,
          guild_discord_id=channel_config.guild.guild_id,
          channel_id=channel_config.channel_id,
          channel_name=channel_name,
          is_active=channel_config.is_active,
          created_at=channel_config.created_at.isoformat(),
          updated_at=channel_config.updated_at.isoformat(),
      )
  ```

### Task 2.4: Update channel routes to use response builder

Replace response construction in get_channel_config, create_channel_config, and update_channel_config.

- **Files**:
  - services/api/routes/channels.py - Update response construction at lines 61-77, 104-120, 140-153
- **Success**:
  - All three route handlers use `_build_channel_config_response()`
  - Response structure remains identical
  - All existing API tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 131-153)
- **Dependencies**:
  - Task 2.3 completion

### Task 2.5: Consolidate template permission checks

Extract common bot manager permission check pattern in template operations.

- **Files**:
  - services/api/routes/templates.py - Refactor update_template, delete_template, set_default_template
- **Success**:
  - Permission check logic consolidated (lines 231-243 pattern)
  - Either extract to helper function or use existing build_template_response more consistently
  - All three operations use consistent permission checking
  - All existing API tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 155-176) - Template operations pattern
- **Dependencies**:
  - None

## Phase 3: Authorization Pattern Consolidation

### Task 3.1: Create generic permission requirement helper and create unit tests

Create `_require_permission()` helper in permissions.py to consolidate authorization logic, with comprehensive unit tests.

- **Files**:
  - services/api/dependencies/permissions.py - Add `_require_permission()` internal helper
  - tests/unit/api/dependencies/test_permissions.py - Add unit tests for permission helper
- **Success**:
  - Function accepts guild_id, permission_checker callable, error_message, current_user, role_service, db
  - Performs token validation
  - Resolves Discord guild_id from database UUID
  - Calls permission_checker with appropriate parameters
  - Raises HTTPException with custom error message on failure
  - Returns CurrentUser on success
  - Includes proper type hints and docstring
  - Unit tests cover: successful permission check, failed permission check, expired token, invalid guild_id, permission_checker exceptions
  - All tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 44-95) - Authorization pattern analysis
- **Implementation**:
  ```python
  async def _require_permission(
      guild_id: str,
      permission_checker: Callable[[str, str, str], Awaitable[bool]],
      error_message: str,
      current_user: auth_schemas.CurrentUser,
      role_service: roles_module.RoleVerificationService,
      db: AsyncSession,
  ) -> auth_schemas.CurrentUser:
      """Generic permission requirement helper for FastAPI dependencies."""
      token_data = await tokens.get_user_tokens(current_user.session_token)
      if not token_data:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

      access_token = token_data["access_token"]
      discord_guild_id = await _resolve_guild_id(
          guild_id, db, access_token, current_user.user.discord_id
      )

      has_permission = await permission_checker(
          current_user.user.discord_id,
          discord_guild_id,
          access_token,
      )

      if not has_permission:
          logger.warning(
              f"User {current_user.user.discord_id} lacks permission in guild {discord_guild_id}"
          )
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)

      return current_user
  ```

### Task 3.2: Refactor require_manage_guild to use helper

Simplify require_manage_guild() using _require_permission() helper.

- **Files**:
  - services/api/dependencies/permissions.py - Refactor require_manage_guild() at lines 251-298
- **Success**:
  - Function uses _require_permission() helper
  - Passes DiscordPermissions.MANAGE_GUILD check
  - Maintains same function signature for FastAPI dependency injection
  - All existing authorization tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 44-95)
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Refactor require_manage_channels to use helper

Simplify require_manage_channels() using _require_permission() helper.

- **Files**:
  - services/api/dependencies/permissions.py - Refactor require_manage_channels() at lines 304-354
- **Success**:
  - Function uses _require_permission() helper
  - Passes DiscordPermissions.MANAGE_CHANNELS check
  - Maintains same function signature for FastAPI dependency injection
  - All existing authorization tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 44-95)
- **Dependencies**:
  - Task 3.1 completion

### Task 3.4: Refactor require_bot_manager to use helper

Simplify require_bot_manager() using _require_permission() helper.

- **Files**:
  - services/api/dependencies/permissions.py - Refactor require_bot_manager() at lines 391-433
- **Success**:
  - Function uses _require_permission() helper
  - Passes role_service.check_bot_manager_permission check
  - Maintains same function signature for FastAPI dependency injection
  - All existing authorization tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 44-95)
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Optional Improvements

### Task 4.1: Extract display name resolution helper and create unit tests (optional)

Create helper method in display_names.py to resolve display name from member data, with unit tests.

- **Files**:
  - services/api/services/display_names.py - Add `_resolve_display_name()` helper method
  - tests/unit/api/services/test_display_names.py - Add unit tests for display name resolution
- **Success**:
  - Method accepts member dictionary
  - Returns display name using fallback logic (nick -> global_name -> username)
  - Used in both _fetch_display_names_from_discord() and _fetch_user_data_from_discord()
  - Unit tests cover: nickname present, global_name fallback, username fallback, missing fields handling
  - All tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 178-189)
- **Dependencies**:
  - None

### Task 4.2: Consolidate game error handling (optional)

Extract error handling decorator or context manager for game operations.

- **Files**:
  - services/api/routes/games.py - Create error handling helper, update create_game and update_game
- **Success**:
  - Common error handling for ValidationError and ValueError
  - Consistent error response format
  - Applied to both create_game and update_game routes
  - All existing API tests pass
- **Research References**:
  - #file:../research/20260125-remaining-code-duplication-analysis-research.md (Lines 219-234)
- **Dependencies**:
  - None

## Success Criteria

- Code duplication reduced from 22 to target of 11 or fewer clone pairs
- All new helper functions have unit tests with good coverage
- All existing tests pass
- Authorization behavior remains consistent
- Response formats unchanged
- No regressions in API functionality
