<!-- markdownlint-disable-file -->

# Release Changes: Remove channel_name from Database

**Related Plan**: 20251201-remove-channel-name-from-database-plan.instructions.md
**Implementation Date**: 2025-12-01

## Summary

Removed `channel_name` column from `channel_configurations` table and implemented dynamic fetching from Discord API with Redis caching. This eliminates staleness issues when Discord channel names change while maintaining backward compatibility in API responses.

## Changes

### Added

- alembic/versions/017_remove_channel_name.py - Database migration to drop channel_name column from channel_configurations table

### Modified

- shared/models/channel.py (Lines 1-63) - Removed channel_name field from ChannelConfiguration model
- shared/schemas/channel.py (Lines 1-75) - Removed channel_name from create and update request schemas, kept in response schema for API backward compatibility
- services/api/routes/channels.py (Lines 1-213) - Updated all endpoints to fetch channel names dynamically from Discord API with error handling
- services/api/auth/discord_client.py (Lines 583-603) - Added fetch_channel_name_safe() helper function to centralize channel name fetching logic with error handling
- services/api/routes/channels.py (Lines 1-180) - Refactored to use common fetch_channel_name_safe() function in all three endpoints
- services/api/routes/guilds.py (Lines 1-310) - Refactored list_guild_channels to use common fetch_channel_name_safe() function
- services/api/routes/games.py (Lines 1-325) - Refactored \_build_game_response to use common fetch_channel_name_safe() function
- tests/services/api/routes/test_guilds.py (Lines 367-408) - Updated test to mock the new common function
- services/api/services/config.py (Lines 1-300) - Removed channel_name parameter from create_channel_config method
- services/bot/commands/config_channel.py (Lines 1-312) - Removed channel_name logic from /config-channel command
- tests/services/api/services/test_config.py (Lines 58-75, 212-224, 265-275) - Removed channel_name from test fixtures and updated test parameters
- tests/services/bot/commands/test_config_channel.py (Lines 86-99) - Removed channel_name from test fixtures
- tests/services/api/routes/test_guilds.py (Lines 367-413) - Updated list_guild_channels test to mock discord_client.fetch_channel
- tests/services/bot/auth/test_role_checker.py (Lines 218-235) - Removed channel_name from ChannelConfiguration test fixture

### Removed

### Notes

- All unit tests pass (420/420 tests)
- All integration tests pass (10/10 tests) after container rebuild
- Docker containers build successfully (api, bot, integration-tests, init, frontend)
- Integration test containers needed rebuild to apply latest database migrations
- Code verification completed (2025-12-02):
  - All coding conventions followed (Python, ReactJS, self-explanatory code)
  - All copyright notices present
  - Import and commenting conventions followed
  - All linting issues fixed (ruff check passes)
  - Unit test coverage: services/api/services/games.py: 84%, services/api/routes/games.py: 54%
  - 8 new test functions added for participant count and timezone handling
  - Frontend TypeScript type-check passes
  - All affected Docker containers build successfully
  - All integration tests pass (10/10)
- Task 7.1 (Database migration): Migration 017_remove_channel_name.py applied successfully
- Task 7.2 (All tests passing): Unit tests (420/420), integration tests (10/10), frontend type-check all pass
- Task 7.3 (Manual testing): Channel names display correctly in frontend, fetched dynamically from Discord API with caching
- Bug fixes (2025-12-02):
  - Fixed services/api/routes/guilds.py list_guild_channels endpoint (missed during initial implementation)
  - Fixed tests/services/api/services/test_config.py test_update_channel_config (removed channel_name parameter)
  - Fixed tests/services/api/routes/test_guilds.py test_list_channels_success (added discord_client mock)
  - Fixed tests/services/bot/auth/test_role_checker.py test_check_game_host_permission_with_channel_roles (removed channel_name from fixture)
  - Fixed services/api/routes/guilds.py line 296: Changed `discord_channel.name` to `discord_channel.get("name", "Unknown Channel")` to properly handle dict return type
  - Fixed tests/services/api/routes/test_guilds.py: Changed mock from MagicMock with .name attribute to dict with "name" key
