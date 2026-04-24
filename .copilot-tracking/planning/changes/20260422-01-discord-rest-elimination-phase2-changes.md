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
