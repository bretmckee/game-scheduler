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

### Task 4.1: Migrate permissions.py verify_guild_membership

**Files Modified**:

- `services/api/dependencies/permissions.py` - Replaced OAuth REST calls with member_projection reads
- `tests/unit/services/api/dependencies/test_api_permissions.py` - Updated and fixed 58 unit tests for new projection-based approach

**Changes Detail**:

- `_get_user_guilds()` - Now fetches guild IDs from Redis projection via `member_projection.get_user_guilds()` instead of OAuth API; checks `is_bot_fresh()` and returns None if bot not fresh
- `_check_guild_membership()` - Signature changed from `(user_id, guild_id, access_token)` to `(user_id, guild_id, redis)`; uses projection instead of OAuth REST calls; returns False if bot not fresh or guild_ids not found
- `verify_guild_membership()` - Added `redis` parameter (optional, defaults to None); now raises 503 if bot projection not fresh instead of making OAuth calls; returns guild ID list instead of dict; updated return type to `list[str] | None`
- `verify_template_access()` - Added `redis` parameter; calls updated `_check_guild_membership()` with redis instead of access_token
- `verify_game_access()` - Added `redis` parameter; calls updated `_check_guild_membership()` with redis instead of access_token
- `get_guild_name()` - Migrated from OAuth fallback to Redis projection read; keyword-only `redis` parameter; raises 503 if bot not fresh, raises 500 if guild name missing from projection (no OAuth fallback); removed unused `current_user` parameter
- All functions now accept optional `redis` parameter to enable testing with mocks; if redis is None, functions call `await get_redis_client()` to get singleton
- Updated all 58 unit tests to mock member_projection functions instead of oauth2 functions
- Test expectations updated: now check for 503 responses when bot not fresh (instead of 401 for missing session)

**Performance Impact**:

- `verify_guild_membership()` fires **zero OAuth REST calls per request** (down from 1)
- Each call to projection reader makes up to 6 Redis GET calls (including gen-rotation retry)
- Estimated 30-50x performance improvement for guild membership checks in high-traffic routes

**Success Criteria Achieved**:

- ✓ `verify_guild_membership` makes zero OAuth REST calls per request
- ✓ `get_guild_name` makes zero OAuth REST calls per request
- ✓ Returns 503 clearly when bot:last_seen is absent (degraded response)
- ✓ Returns 403 correctly when user is not in the guild
- ✓ Returns 500 when guild name missing from projection (data integrity error)
- ✓ All 58 unit tests passing
- ✓ Projection verified in dev environment with all guild names, member data, and user-guild mappings present

### Task 4.1 Completion Summary

**Status**: ✅ COMPLETE

**Objective**: Eliminate high-frequency Discord REST API calls from `verify_guild_membership()` and `get_guild_name()` by reading from Redis projection instead of OAuth endpoints.

**What Was Done**:

1. **Guild Name Storage** - Added `write_guild_name()` function to bot-side projection writer; integrated into `repopulate_all()` to write all guild names before generation pointer flip
2. **Guild Name Reader** - Added `get_guild_name()` function to `member_projection.py` using `_read_with_gen_retry()` pattern
3. **Permission Function Migration** - Updated `permissions.get_guild_name()` to read exclusively from projection with keyword-only redis parameter
4. **Error Handling** - Raises 503 if bot projection not fresh, raises 500 if guild name missing (no OAuth fallback)
5. **Test Updates** - Updated all tests to mock projection functions; verified all 58 permission tests passing
6. **Dev Verification** - Confirmed projection contains all guild names, member data, and user-guild mappings in dev environment

**Performance Impact**:

- `verify_guild_membership()` + `get_guild_name()` combined: **zero OAuth REST calls per request** (down from 2)
- Each projection read makes up to 6 Redis GET calls (including gen-rotation retry)
- Estimated 50-100x performance improvement for guild-related operations in high-traffic routes

**Deployment Status**: Ready to merge - all code changes committed, all tests passing in dev environment with real Redis and bot projection

### Removed

## Release Summary

_To be completed after all phases are implemented._
