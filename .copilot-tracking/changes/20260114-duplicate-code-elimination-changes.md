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
