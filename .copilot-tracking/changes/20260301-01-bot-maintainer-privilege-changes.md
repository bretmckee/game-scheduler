---
applyTo: '.copilot-tracking/plans/20260301-01-bot-maintainer-privilege.plan.md'
---

<!-- markdownlint-disable-file -->

# Change Record: Bot Maintainer Privilege Level

## Summary

Adds a dual-flag (`can_be_maintainer` / `is_maintainer`) privilege system for Discord application owners and team members, allowing them to view all bot-present guilds and bypass per-guild permission checks.

---

## Added

- `tests/unit/shared/discord/test_client.py` — Unit tests for `DiscordAPIClient.get_application_info()` covering correct URL, cache key, TTL, and return value.
- `tests/unit/services/api/auth/test_oauth2.py` — Unit tests for `is_app_maintainer()` covering owner match, team member match, non-member rejection, and team-absent fallback to owner check.
- `tests/unit/services/api/auth/test_tokens.py` — Unit tests for `get_guild_token()` (bot token for maintainer, OAuth token for regular/missing flag), and for updated `store_user_tokens()` / `get_user_tokens()` with maintainer flags.
- `services/api/routes/maintainers.py` — New router with `POST /api/v1/maintainers/toggle` (requires `can_be_maintainer`, re-validates via `is_app_maintainer()`, sets `is_maintainer=True` in session) and `POST /api/v1/maintainers/refresh` (requires `is_maintainer`, scans Redis to delete other elevated sessions, flushes `app_info` cache).
- `tests/integration/test_maintainers.py` — Integration tests for toggle (enables maintainer mode, 403 without `can_be_maintainer`, 403 if not in Discord team) and refresh (403 for non-maintainer, deletes other elevated sessions, flushes `app_info` cache).

## Modified

- `shared/cache/ttl.py` — Added `APP_INFO = 3600` constant to `CacheTTL` for 1-hour caching of Discord application info.
- `shared/cache/keys.py` — Added `app_info()` static method to `CacheKeys` returning `"discord:app_info"`.
- `shared/discord/client.py` — Added `get_application_info()` method to `DiscordAPIClient` that fetches `/oauth2/applications/@me` with bot token auth and 1-hour Redis caching. **Outside plan**: Added Redis cache-read check at the start of `get_application_info()` to honour the 1-hour TTL (without this, the method always called Discord). This was necessary to allow integration tests to seed the cache.
- `services/api/auth/oauth2.py` — Added `is_app_maintainer(discord_id)` async function that checks if a user is a Discord application owner or team member using the cached application info.
- `services/api/auth/tokens.py` — Added `get_guild_token(session_data)` sync function returning bot token for maintainers or decrypted OAuth token otherwise; updated `store_user_tokens()` to accept and persist `can_be_maintainer` flag with `is_maintainer: False` default; updated `get_user_tokens()` to return both flags.
- `services/api/routes/auth.py` — Updated OAuth callback to call `is_app_maintainer()` after user identity fetch and pass `can_be_maintainer` to `store_user_tokens()`.
- `services/api/app.py` — Added import of `maintainers` router and registered it with `app.include_router(maintainers.router)`.
- `tests/shared/auth_helpers.py` — Added `can_be_maintainer` and `is_maintainer` optional parameters to `create_test_session()` so integration tests can create sessions with maintainer flags.
- `tests/unit/shared/discord/test_client.py` — Added `mock_redis_cache_miss` autouse fixture to patch the Redis cache check added to `get_application_info()`; without this, unit tests would require a live Redis connection.

**Outside plan**: Fixed misplaced `# noqa: ANN401` comment in `shared/discord/client.py` `_get_error_message()` (moved from the return type line to the `Any` parameter line where the lint error actually occurs); this was a pre-existing bug discovered while linting Phase 4 changes.

## Removed

<!-- List of files removed -->
