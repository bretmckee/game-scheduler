<!-- markdownlint-disable-file -->

# Release Changes: Discord Gateway Intent Redis Projection

**Related Plan**: 20260418-01-gateway-intent-redis-projection.plan.md
**Implementation Date**: 2026-04-18

## Summary

Eliminate Discord REST API calls from the per-request API path by enabling GUILD_MEMBERS privileged intent, creating a Redis projection from gateway member events in the Discord bot, and implementing an API-side reader with gen-rotation retry logic.

## Changes

### Added

- `shared/cache/keys.py` - Added four projection key factory functions: `proj_gen()`, `proj_member()`, `proj_user_guilds()`, `bot_last_seen()`
- `tests/unit/shared/cache/test_keys.py` - Added unit tests for all four new projection key functions
- `services/bot/guild_projection.py` - Created bot-side writer module with OTel instruments and projection repopulation logic
- `tests/unit/bot/test_guild_projection.py` - Created comprehensive unit tests for guild_projection (12 tests covering all functions with TDD xfail→green workflow)
- `services/api/services/member_projection.py` - Created API-side reader module with gen-rotation retry, OTel instruments, and reader functions: `get_user_guilds`, `get_member`, `get_user_roles`, `is_bot_fresh`
- `tests/unit/api/services/test_member_projection.py` - Created unit tests for member_projection reader (13 tests covering all functions and retry/miss edge cases with TDD xfail→green workflow)

### Modified

- `services/bot/bot.py` - Enabled `GUILD_MEMBERS` intent and set `chunk_guilds_at_startup=True` in bot initialization
- `services/bot/bot.py` - Added call to `repopulate_all` in `on_ready()` to populate projection on bot startup
- `services/bot/bot.py` - Added event handlers: `on_member_add()`, `on_member_update()`, `on_member_remove()` to update projection on member changes
- `services/bot/bot.py` - Added `_projection_heartbeat()` background task started in `setup_hook()` to write bot heartbeat to Redis every 30 seconds

### Removed

## Release Summary

_To be completed after all phases are implemented._
