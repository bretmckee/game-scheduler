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

### Modified

- `services/bot/bot.py` - Enabled `GUILD_MEMBERS` intent and set `chunk_guilds_at_startup=True` in bot initialization

### Removed

## Release Summary

_To be completed after all phases are implemented._
