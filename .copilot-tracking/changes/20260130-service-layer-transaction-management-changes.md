<!-- markdownlint-disable-file -->

# Release Changes: Service Layer Transaction Management and Atomicity

**Related Plan**: 20260130-service-layer-transaction-management-plan.instructions.md
**Implementation Date**: 2026-01-30

## Summary

Restore transaction atomicity by removing premature commits from service layer functions and enforcing route-level transaction boundaries.

## Changes

### Added

### Modified

- services/api/services/guild_service.py - Removed commits from create_guild_config() and update_guild_config(), replaced with flush for ID generation, added transaction docstring notes, removed unused db parameter from update_guild_config()
- services/api/services/channel_service.py - Removed commits from create_channel_config() and update_channel_config(), replaced with flush for ID generation, added transaction docstring notes, removed unused db parameter from update_channel_config()
- services/api/routes/guilds.py - Updated update_guild_config() call to remove db argument
- services/api/routes/channels.py - Updated update_channel_config() call to remove db argument
- services/bot/events/handlers.py - Refactored _handle_game_created() to reduce cognitive complexity from 18 to 14 by extracting validation helpers (_validate_game_created_event, _validate_discord_channel, _get_bot_channel)
- tests/services/api/services/test_guild_service.py - Updated tests to verify no commits in service layer, expect flush for ID generation, removed db parameter from update tests
- tests/services/api/services/test_channel_service.py - Updated tests to verify no commits in service layer, expect flush for ID generation, removed db parameter from update tests
- tests/services/api/routes/test_channels.py - Added test_update_channel_config_success to verify route-level transaction handling
- tests/services/bot/events/test_handlers.py - Added 8 tests for new validation helper methods with comprehensive coverage of success and error paths

### Removed
