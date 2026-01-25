<!-- markdownlint-disable-file -->

# Release Changes: Duplicate Code Elimination

**Related Plan**: 20260114-duplicate-code-elimination-plan.instructions.md
**Implementation Date**: 2026-01-17

## Summary

Reducing code duplication from 3.68% to under 2% by extracting common patterns into reusable functions and utilities across Python backend and TypeScript frontend.

**Phase 1 complete**: Extracted template response construction into reusable helper, eliminating 120+ lines of duplicated code across 4 endpoints.

**Phase 2 complete**: Refactored Discord API methods to use centralized error handling, eliminating 135+ lines of duplicated error handling code across 5 methods.

## Changes

### Added

- [services/api/routes/templates.py](services/api/routes/templates.py#L39-L62): New `build_template_response()` helper function to eliminate duplicated template response construction
- [tests/services/api/routes/test_templates.py](tests/services/api/routes/test_templates.py#L104-L192): Unit tests for `build_template_response()` helper covering all fields, null optionals, and channel name resolution
- [shared/discord/client.py](shared/discord/client.py#L145-L206): New `_make_api_request()` base method for generic Discord API request handling with error handling and caching
- [tests/shared/discord/test_client.py](tests/shared/discord/test_client.py#L207-L397): Unit tests for `_make_api_request()` covering successful requests, error responses, caching, and network errors

### Modified

- [services/api/routes/templates.py](services/api/routes/templates.py):
  - Added `get_discord_client` import for dependency injection
  - Updated `list_templates` endpoint to inject `DiscordAPIClient` and use it for channel name resolution
  - Refactored `get_template` endpoint to use `build_template_response()` helper
  - Refactored `create_template` endpoint to use `build_template_response()` helper
  - Refactored `update_template` endpoint to use `build_template_response()` helper
  - Refactored `set_default_template` endpoint to use `build_template_response()` helper
- [tests/services/api/routes/test_templates.py](tests/services/api/routes/test_templates.py): Updated tests to pass `discord_client` parameter to endpoint functions
- [shared/discord/client.py](shared/discord/client.py):
  - Refactored `exchange_code()` method from 24 to 12 lines (-50%) to use `_make_api_request()` base method
  - Refactored `refresh_token()` method from 24 to 12 lines (-50%) to use `_make_api_request()` base method
  - Refactored `fetch_guild()` method from 34 to 16 lines (-53%) to use `_make_api_request()` base method
  - Refactored `fetch_user()` method from 29 to 11 lines (-62%) to use `_make_api_request()` base method
  - Refactored `get_guild_member()` method from 24 to 10 lines (-58%) to use `_make_api_request()` base method
  - Updated `_make_api_request()` to handle both "message" and "error_description" error fields (OAuth vs REST API)
- [tests/shared/discord/test_client.py](tests/shared/discord/test_client.py):
  - Updated OAuth tests (`test_exchange_code_*`, `test_refresh_token_*`) to patch `_make_api_request` instead of mocking session directly
  - Updated resource fetch tests to mock `session.request` instead of `session.get/post` to match new base method
  - Added missing Redis mocks to `test_get_guild_member_success` and `test_get_guild_member_not_found`
  - Fixed async mocking by using `new_callable=AsyncMock` for `cache_client.get_redis_client()` patches
  - Replaced `MagicMock()` headers with actual dicts to prevent AsyncMock iteration issues

### Removed

## Phase 3 Progress

### Task 3.1 Complete

- [shared/discord/game_embeds.py](shared/discord/game_embeds.py): New module with `build_game_list_embed()` function to centralize game list embed formatting
- [tests/shared/discord/test_game_embeds.py](tests/shared/discord/test_game_embeds.py): Comprehensive unit tests for `build_game_list_embed()` with 11 test cases covering single/multiple games, descriptions, pagination, colors, and edge cases

### Task 3.2 Complete

- [services/bot/commands/list_games.py](services/bot/commands/list_games.py): Refactored to use shared `build_game_list_embed()`, removed 24-line duplicate `_create_games_list_embed()` function, added import from shared module
- [tests/services/bot/commands/test_list_games.py](tests/services/bot/commands/test_list_games.py): Updated to import and test shared `build_game_list_embed()` instead of removed local function

### Task 3.3 Complete

- [services/bot/commands/my_games.py](services/bot/commands/my_games.py): Refactored to use shared `build_game_list_embed()`, removed 27-line duplicate `_create_games_embed()` function, added import from shared module
- [tests/services/bot/commands/test_my_games.py](tests/services/bot/commands/test_my_games.py): Updated to import and test shared `build_game_list_embed()` instead of removed local function

## Phase 4 Progress

### Task 4.1 Complete

- [frontend/src/types/index.ts](frontend/src/types/index.ts): Refactored `TemplateUpdateRequest` from 16-line interface to single-line utility type using `Partial<Omit<GameTemplate, ...>>`, eliminating ~15 lines of duplicate type definitions

### Task 4.2 & 4.3 Complete (Combined)

Note: The plan file lists Tasks 4.2 (Create TemplateUpdate utility type) and 4.3 (Verify TypeScript compilation), but the details file only has 4.1 and 4.2. Task 4.1 covered both the refactoring and creation of the utility type. This task verified compilation.

- TypeScript type checking passed (`npm run type-check`) with no errors
- Full frontend build succeeded (`npm run build`) with no compilation errors
- All TypeScript files using Template types compile correctly

## Phase 5 Progress

### Task 5.1 Complete

- [services/bot/events/handlers.py](services/bot/events/handlers.py#L338-L374): New `_fetch_channel_and_message()` helper method to centralize channel and message fetching with validation
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py#L2170-L2262): Unit tests for `_fetch_channel_and_message()` with 6 test cases covering successful fetch, channel not cached, invalid channel, wrong channel type, message not found, and fetch errors

### Task 5.2 Complete

- [services/bot/events/handlers.py](services/bot/events/handlers.py#L844-L873): Refactored `_update_message_for_player_removal()` to use shared `_fetch_channel_and_message()`, reducing from 33 to 30 lines and eliminating 17 lines of duplicate channel/message fetching logic

### Task 5.3 Complete

- [services/bot/events/handlers.py](services/bot/events/handlers.py#L963-1009): Refactored `_handle_game_cancelled()` to use shared `_fetch_channel_and_message()`, eliminating separate `_fetch_and_validate_channel()` and `_update_cancelled_game_message()` methods
- [services/bot/events/handlers.py](services/bot/events/handlers.py): Removed 47-line `_fetch_and_validate_channel()` method (now redundant with new helper)
- [services/bot/events/handlers.py](services/bot/events/handlers.py): Removed 20-line `_update_cancelled_game_message()` method (logic inlined into handler)
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py): Updated cancellation tests to mock `_fetch_channel_and_message()` instead of removed methods, removed 7 obsolete helper method tests

## Phase 6 Progress

### Task 6.1 Complete: jscpd Verification

- **Result**: Code duplication reduced from **3.68% to 1.7%** (exceeding 2% target)
- **Metrics**:
  - Python: 1.7% line duplication, 2.19% token duplication
  - TypeScript: 1.65% line duplication, 3.11% token duplication
  - Overall: 1.7% line duplication, 2.24% token duplication
- **Clones found**: 22 (reduced from 31 initial clones)

### Task 6.2 Complete: Test Suite Verification

- **Python tests**: All 1342 tests passed (185 deselected)
- **TypeScript tests**: All 105 tests passed
- **Result**: No regressions detected from refactoring

### Task 6.3 Complete: Configuration Update

- [.jscpd.json](.jscpd.json): Updated threshold from 5% to 3% to maintain improved duplication standards

## Release Summary

**Total Files Affected**: 11

### Files Created (4)

- [shared/discord/game_embeds.py](shared/discord/game_embeds.py) - Centralized game list embed formatting function
- [tests/shared/discord/test_game_embeds.py](tests/shared/discord/test_game_embeds.py) - Comprehensive unit tests for game embed builder
- New helper methods added to existing files (build_template_response, _make_api_request, _fetch_channel_and_message)

### Files Modified (7)

- [services/api/routes/templates.py](services/api/routes/templates.py) - Added build_template_response helper, refactored 4 endpoints
- [tests/services/api/routes/test_templates.py](tests/services/api/routes/test_templates.py) - Added helper tests, updated endpoint tests
- [shared/discord/client.py](shared/discord/client.py) - Added _make_api_request base method, refactored 5 API methods
- [tests/shared/discord/test_client.py](tests/shared/discord/test_client.py) - Added base method tests, updated API method tests
- [services/bot/commands/list_games.py](services/bot/commands/list_games.py) - Removed duplicate embed function, use shared function
- [services/bot/commands/my_games.py](services/bot/commands/my_games.py) - Removed duplicate embed function, use shared function
- [services/bot/events/handlers.py](services/bot/events/handlers.py) - Added _fetch_channel_and_message helper, refactored 2 handlers, removed 67 lines of duplicate code
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py) - Added helper tests, updated handler tests
- [frontend/src/types/index.ts](frontend/src/types/index.ts) - Refactored TemplateUpdateRequest to use TypeScript utility types
- [.jscpd.json](.jscpd.json) - Updated duplication threshold from 5% to 3%

### Files Removed (0)

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: jscpd threshold lowered from 5% to 3%

### Deployment Notes

This is a refactoring change with no behavioral modifications. All existing tests pass and no API changes were made. The changes can be deployed without requiring data migrations or configuration updates.
