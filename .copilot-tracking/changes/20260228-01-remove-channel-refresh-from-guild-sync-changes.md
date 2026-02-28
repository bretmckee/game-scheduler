<!-- markdownlint-disable-file -->

# Changes: Remove Channel Refresh from Guild Sync

## Overview

Remove the existing-guild channel refresh loop from `sync_all_bot_guilds` and eliminate `updated_channels` throughout the full stack.

## Modified

### Phase 1: Remove channel refresh from backend

- `services/bot/guild_sync.py` — Removed the existing-guild refresh loop (the `updated_channels_count` accumulator, the `existing_guilds_in_bot` set construction, and the `_refresh_guild_channels` call), and removed `updated_channels` from the returned dict.
- `shared/schemas/guild.py` — Removed `updated_channels` field from `GuildSyncResponse`.
- `services/api/routes/guilds.py` — Removed `updated_channels` from the `logger.info` call and from the `GuildSyncResponse` constructor in `sync_guilds`.

### Phase 2: Update backend unit tests

- `tests/services/bot/test_guild_sync.py` — Rewrote `test_sync_all_bot_guilds_skip_existing_guilds` to assert existing guilds are skipped (not refreshed): updated docstring, reduced `get_guild_channels` side_effect to one entry, removed `updated_channels` assertion, and changed call-count expectation from 2 to 1.
- `tests/services/api/routes/test_guilds.py` — Removed `"updated_channels": 0` from all three `mock_sync.return_value` dicts and removed all `assert result.updated_channels == 0` assertions.

### Phase 3: Update frontend code and tests

- `frontend/src/api/guilds.ts` — Removed `updated_channels: number` field from the `GuildSyncResponse` interface.
- `frontend/src/pages/GuildListPage.tsx` — Removed the `result.updated_channels > 0` branch from the sync-result conditional and the "X updated channel(s)" message fragment from the string builder.
- `frontend/src/pages/__tests__/GuildListPage.test.tsx` — Removed `updated_channels` from all four mock data objects and updated expected messages: "displays success message with updated channels on sync" now asserts "Synced 1 new channel"; "handles proper pluralization in sync messages" now asserts "Synced 2 new servers, 1 new channel".

### Phase 4: Update e2e tests

- `tests/e2e/test_channel_refresh_e2e.py` — Both tests (`test_channel_refresh_reactivates_inactive_channels` and `test_channel_list_without_refresh_uses_cached_data`) now call `GET /{guild_id}/channels?refresh=true` after sync to populate channels (sync no longer refreshes channels for existing guilds). Docstrings updated to reflect two-step setup.
- `tests/e2e/test_guild_sync_e2e.py` — Updated `test_sync_creates_all_guilds` docstring: removed "refreshes ALL bot guilds globally" wording; now says "creates ALL bot guilds globally" and "New guilds are created; existing guilds are not modified by sync".
- `services/bot/guild_sync.py` — Removed stale `"updated_channels"` key from the `sync_all_bot_guilds` return-value docstring.
- `services/api/services/guild_service.py` — Renamed local variable `updated_channels_result`/`updated_channels` to `all_channels_result`/`all_channels` to eliminate any remaining `updated_channels` term from the codebase.
- `tests/unit/api/services/test_guild_service_channel_refresh.py` — Renamed `updated_channels_result`, `updated_channels`, and `updated_scalars_mock` to `all_channels_result`, `all_channels`, and `all_channels_scalars_mock` across all six test functions.
