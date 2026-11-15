---
applyTo: '.copilot-tracking/changes/20260422-01-discord-rest-elimination-phase2-changes.md'
---

<!-- markdownlint-disable-file -->

# Changes: Discord REST Elimination — Phase 2

## Summary

Replace all remaining `oauth2.get_user_guilds()` REST calls, the last `bot.fetch_user()` call,
and the `discord_api.get_guild_member()` call with Redis projection reads, then remove the
now-redundant `/sync` endpoint, frontend Sync button, and dead guild sync functions.

---

## Phase 1: Fix sse_bridge.py guild membership check

### Task 1.1 & 1.2

- **`services/api/services/sse_bridge.py`**: Replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read in the SSE broadcast loop; added `cache_client` parameter threading from `get_sse_manager()`.
- **`tests/unit/services/api/test_sse_bridge.py`**: Added projection-based guild lookup tests; removed obsolete OAuth guild tests.

---

## Phase 2: Fix queries.py RLS setup

### Task 2.1 & 2.2

- **`services/api/database/queries.py`**: Replaced `oauth2.get_user_guilds()` with `member_projection.get_user_guilds()` for RLS context setup; added `cache_client` to `get_guild_ids_for_user()`.
- **`tests/unit/services/api/test_queries.py`**: Updated tests to mock projection path; confirmed REST path no longer exercised.

---

## Phase 3: Fix guilds.py list_guilds route

### Task 3.1 & 3.2

- **`services/api/routes/guilds.py`**: Replaced `oauth2.get_user_guilds()` with `member_projection.get_user_guilds()` in `list_guilds` route handler.
- **`tests/unit/services/api/test_guilds.py`**: Added projection-based guild list tests.

---

## Phase 4: Remove guilds field from auth response

### Task 4.1 & 4.2

- **`services/api/routes/auth.py`**: Removed `guilds` field population from `/auth/user` response.
- **`shared/schemas/auth.py`**: Removed `guilds` field from `UserInfoResponse`.
- **`frontend/src/types/index.ts`**: Removed `guilds?: DiscordGuild[]` from `CurrentUser` interface.
- **`tests/unit/services/api/test_auth.py`**: Added test confirming `guilds` absent from response.

---

## Phase 5: Fix discord_format.py member lookup

### Task 5.1 & 5.2

- **`services/bot/utils/discord_format.py`**: Replaced `discord_api.get_guild_member()` REST call with `member_projection.get_member()` projection read; removed `DiscordAPIClient` usage from format function.
- **`tests/unit/services/bot/test_discord_format.py`**: Added projection-based member display info tests.

---

## Phase 6: Fix participant_drop.py user fetch

### Task 6.1 & 6.2

- **`services/bot/handlers/participant_drop.py`**: Replaced `bot.fetch_user()` async REST call with `bot.get_user()` synchronous cache lookup.
- **`tests/unit/services/bot/test_participant_drop.py`**: Added sync user fetch test; confirmed no `fetch_user` calls.

---

## Phase 7: Remove /sync endpoint and frontend Sync button

### Task 7.1, 7.2 & 7.3

- **`services/api/routes/guilds.py`**: Removed `POST /api/v1/guilds/sync` route handler.
- **`frontend/src/pages/GuildListPage.tsx`**: Removed Sync button, `handleSync` handler, and `syncMutation`.
- **`frontend/src/pages/__tests__/GuildListPage.test.tsx`**: Removed Sync button tests; updated remaining tests.
- **`tests/unit/services/api/test_guilds.py`**: Added test confirming `/sync` returns 404.

---

## Phase 8: Fix shared/database.py missed call site

### Task 8.1 & 8.2

- **`shared/database.py`**: Replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read in `get_db_with_user_guilds()`; removed `guild_token` extraction.
- **`tests/unit/shared/test_database_dependencies.py`**: Updated mocks to projection path; added projection-not-oauth test; removed unused `mock_user_guilds` fixture.
- **`tests/unit/services/api/test_export.py`**: Updated mocks to projection path; fixed pre-existing DTZ001 violations.

---

## Phase 9: Remove dead REST functions from guild_sync.py

### Task 9.1

- **`tests/unit/services/bot/test_guild_sync.py`**: Deleted 11 `test_sync_all_bot_guilds_*` top-level test functions, 3 `test_create_guild_with_channels_and_template_*` methods from `TestGuildSyncHelpers`, and 4 `test_refresh_guild_channels_*` top-level test functions. Updated `test_sync_guilds_from_gateway_does_not_call_rest` and `test_sync_single_guild_from_gateway_does_not_call_rest` to remove now-invalid `DiscordAPIClient` patches.

### Task 9.2

- **`services/bot/guild_sync.py`**: Deleted dead `sync_all_bot_guilds()`, `_create_guild_with_channels_and_template()`, and `_refresh_guild_channels()` functions. Removed `DiscordAPIClient` import (only used by the deleted functions).

---

<!-- Merged from the former .copilot-tracking/changes/ copy of this log -->

# Change Record: Discord REST Elimination — Phase 2

## Overview

Tracking file for implementation of plan `20260422-01-discord-rest-elimination-phase2.plan.md`.

## Changes

### Added

- `tests/unit/services/api/services/test_sse_bridge_unit.py` — added `test_broadcast_uses_projection_not_oauth_for_guild_check` verifying the broadcast loop uses `member_projection.get_user_guilds` (written as xfail, then promoted to passing after implementation)

### Modified

- `services/api/services/sse_bridge.py` — replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read; removed `oauth2` import; added `cache_client` and `member_projection` imports
- `services/api/database/queries.py` — replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read in `require_guild_by_id`; renamed `access_token` → `_access_token` (unused, kept for API compatibility); added `cache_client` and `member_projection` imports
- `services/api/routes/guilds.py` — replaced `oauth2.get_user_guilds()` REST call in `list_guilds` with `member_projection.get_user_guilds()` and `member_projection.get_guild_name()` projection reads; removed `oauth2` and `tokens` imports; added `cache_client` and `member_projection` imports
- `tests/unit/services/api/database/test_queries.py` — added `test_require_guild_by_id_uses_projection_not_oauth_for_guild_list`; updated three existing tests to mock projection path instead of `oauth2.get_user_guilds`
- `tests/unit/services/api/routes/test_guilds_routes.py` — added `test_list_guilds_uses_projection_not_oauth`; updated `test_list_guilds_success` and `test_list_guilds_no_configs` to mock projection path instead of `oauth2.get_user_guilds`

- `services/api/routes/auth.py` — removed `oauth2.get_user_guilds()` call and `guild_token` local from `get_user_info`; removed `guilds=guilds` kwarg from `UserInfoResponse` constructor
- `shared/schemas/auth.py` — removed `guilds: list[dict]` field from `UserInfoResponse`
- `frontend/src/types/index.ts` — removed `guilds?: DiscordGuild[]` optional field from `CurrentUser` interface
- `tests/unit/services/api/routes/test_auth_routes.py` — added `test_get_user_info_no_guilds_field` verifying `oauth2.get_user_guilds` is not called and result has no `guilds` attribute
- `services/bot/utils/discord_format.py` — replaced `discord_api.get_guild_member()` call with `member_projection.get_member()` projection read; removed `get_discord_client` and `discord_client` imports; added `cache_client` and `member_projection` imports; updated display name key paths from nested `user` dict to flat projection dict; replaced `_build_avatar_url()` call with direct `member_data.get("avatar_url")`; removed `DiscordAPIError` except clause
- `tests/unit/services/bot/utils/test_discord_format.py` — rewrote all `TestGetMemberDisplayInfo` tests to patch `cache_client.get_redis_client` and `member_projection.get_member` instead of `get_discord_client`; renamed `test_returns_none_on_api_error` → `test_returns_none_on_redis_error` (now tests generic exception); added `test_get_member_display_info_uses_projection_not_discord_api`; removed `DiscordAPIError` import
- `services/bot/handlers/participant_drop.py` — replaced `await bot.fetch_user()` REST call with `bot.get_user()` cache lookup; added `None` guard with `logger.warning` and early return
- `tests/unit/services/bot/handlers/test_participant_drop.py` — new file; added `test_uses_get_user_not_fetch_user` verifying `bot.fetch_user` is not awaited and `bot.get_user` is called
- `services/api/routes/guilds.py` — removed `sync_guilds` handler and `POST /api/v1/guilds/sync` route; removed `os`, `slowapi.Limiter`, `slowapi.util.get_remote_address`, `services.api.config.get_api_config`, `fastapi.Request`, and `services.bot.guild_sync.sync_all_bot_guilds` imports; removed `limiter` and `SYNC_RATE_LIMIT` module-level constants
- `tests/unit/services/api/routes/test_guilds_routes.py` — removed `TestSyncGuilds` class (5 tests); removed `from starlette.requests import Request` import; added `TestSyncEndpointRemoved::test_sync_guilds_handler_not_registered` confirming `sync_guilds` is no longer registered (written as xfail, promoted to passing after implementation)
- `frontend/src/pages/GuildListPage.tsx` — removed `handleSyncGuilds`, `syncing` and `syncMessage` useState entries, `syncUserGuilds` and `GuildSyncResponse` API import, `RefreshIcon` MUI import, Sync button JSX in empty-state and main-view, `syncMessage` Alert JSX in empty-state and main-view
- `frontend/src/api/guilds.ts` — `syncUserGuilds` function and `GuildSyncResponse` interface remain (deletion deferred; API file cleanup out of scope for this task)
- `frontend/src/pages/__tests__/GuildListPage.test.tsx` — removed 4 sync-interaction tests; removed stale `guilds: [...]` from `mockUser`; removed `guilds: []` from `userWithNoGuilds`; added `no Sync Guilds button rendered` test (written as `it.fails`, promoted to `it` after implementation)

- `tests/unit/services/api/test_database_dependencies.py` — added `test_get_db_with_user_guilds_uses_projection_not_oauth` (written as xfail, promoted after implementation); updated three existing tests to patch `shared.cache.client.get_redis_client` and `shared.cache.projection.get_user_guilds` instead of `oauth2.get_user_guilds`; removed `mock_user_guilds` fixture (no longer needed)
- `shared/database.py` — replaced `oauth2.get_user_guilds()` REST call with `member_projection.get_user_guilds()` projection read in `get_db_with_user_guilds`; removed `guild_token` extraction and `oauth2` import; added `from shared.cache import client as cache_client` and `from shared.cache import projection as member_projection` imports inside inner function

- `services/bot/guild_projection.py` — added `_queue_member_to_pipe`, `_queue_user_guilds_to_pipe`, `_queue_guild_name_to_pipe` synchronous pipeline-queue helpers; refactored `_write_all_members` to open a single `redis._client.pipeline(transaction=False)` context manager and queue all member, user-guilds, and guild-name writes before a single `await pipe.execute()`; generation pointer flip and `write_bot_last_seen` remain outside the pipeline; `write_member`, `write_user_guilds`, `write_guild_name` unchanged
- `tests/unit/bot/test_guild_projection.py` — added `TestQueueMemberToPipe` (3 tests), `TestQueueUserGuildsToPipe` (2 tests), `TestQueueGuildNameToPipe` (1 test), `TestRepopulateAllUsesPipeline` (3 tests); updated all `TestRepopulateAll` tests to use a `MagicMock`-based pipeline context manager via new `_make_mock_client` helper; updated `test_repopulate_all_basic` assertion from `redis.set_json.call_count >= 2` to `pipe.set.call_count >= 2`
- `tests/unit/services/bot/test_bot.py` — updated `test_on_ready_event` to replace `AsyncMock()` for `mock_redis._client` with a `MagicMock` that properly sets up the pipeline async context manager and `scan`/`delete` mocks

---

## Phase Progress

- [x] Phase 1: Fix sse_bridge.py guild membership check (Group 2a)
- [x] Phase 2: Fix queries.py RLS setup (Group 2b)
- [x] Phase 3: Fix guilds.py list_guilds route (Group 2c)
- [x] Phase 4: Remove guilds field from auth response (Group 2d)
- [x] Phase 5: Fix discord_format.py member lookup (Group 3)
- [x] Phase 6: Fix participant_drop.py user fetch (Group 4)
- [x] Phase 7: Remove /sync endpoint and frontend Sync button (Group 6)
- [x] Phase 8: Fix shared/database.py missed call site (Finding 1 addendum)
- [x] Phase 9: Remove dead REST functions from guild_sync.py (Finding 3 addendum)
- [x] Phase 10: Pipeline Redis writes in `repopulate_all` (Addendum 2)
