<!-- markdownlint-disable-file -->

# Task Research Notes: Remove Channel Refresh from Guild Sync Button

## Research Executed

### File Analysis

- `services/bot/guild_sync.py`
  - `sync_all_bot_guilds` currently does two things: creates new guilds (with channels) AND refreshes channels for ALL existing guilds
  - The existing-guild refresh loop lives at lines 302–307, returns `updated_channels` count
  - `_refresh_guild_channels` (lines 173–230) handles types 0, 2, 5 (text, voice, announcement)
  - `_create_guild_with_channels_and_template` (lines 125–170) handles new-guild channel creation, also types 0, 2, 5

- `services/api/services/guild_service.py`
  - `refresh_guild_channels` (lines 80–158) is a separate implementation called by `GET /{guild_id}/channels?refresh=true`
  - Only handles **type 0** (text channels only) — inconsistent with `_refresh_guild_channels` in guild_sync.py

- `services/api/routes/guilds.py`
  - `sync_guilds` (lines 314–350): calls `sync_all_bot_guilds`, logs and returns `updated_channels`
  - `list_guild_channels` (lines 215–253): calls `guild_service.refresh_guild_channels` when `refresh=true`

- `shared/schemas/guild.py`
  - `GuildSyncResponse` has `new_guilds`, `new_channels`, `updated_channels` fields

- `frontend/src/api/guilds.ts`
  - `GuildSyncResponse` interface has `updated_channels: number`

- `frontend/src/pages/GuildListPage.tsx`
  - Sync button handler checks `result.updated_channels > 0` in the condition (line 59)
  - Builds "X updated channels" message part from `updated_channels` (lines 69–71)
  - "All servers and channels are already synced" message appears when all three counts are 0

### Code Search Results

- `updated_channels` references
  - `guild_sync.py` lines 303, 307, 312 — source of the value
  - `guilds.py` (route) lines 342, 348 — logs and returns it
  - `guild.py` (schema) lines 92–94 — schema field
  - `guilds.ts` (frontend) line 26 — interface field
  - `GuildListPage.tsx` lines 59, 69, 71 — conditional logic and message

- `sync_all_bot_guilds` callers
  - `services/api/routes/guilds.py` — sync button endpoint
  - `services/bot/bot.py` — bot startup (Discord gateway `on_ready` event)

### Test Files Impacted

- `tests/services/bot/test_guild_sync.py`
  - `test_sync_all_bot_guilds_skip_existing_guilds` (line 104–164): asserts `result["updated_channels"] == 1`, verifies `get_guild_channels.await_count == 2` (called for both new AND existing guild). Both assertions break.

- `tests/services/api/routes/test_guilds.py`
  - Multiple tests pass `"updated_channels"` in `mock_sync.return_value` dict
  - Two tests assert `result.updated_channels == 0`

- `frontend/src/pages/__tests__/GuildListPage.test.tsx`
  - Line 177: `{ new_guilds: 0, new_channels: 1, updated_channels: 3 }` — expects "Synced 1 new channel, 3 updated channels". Test needs removal.
  - Line 213: `{ new_guilds: 2, new_channels: 1, updated_channels: 1 }` — expects "Synced 2 new servers, 1 new channel, 1 updated channel". Test needs updating (remove updated channels part).
  - Lines 159, 195: use `updated_channels: 0` — field needs removing from mock data.

- `tests/e2e/test_guild_sync_e2e.py`
  - No tests assert on `updated_channels` directly — response JSON access is safe
  - Docstrings reference "refreshes channels for existing guilds" — need updating to reflect new behavior
  - `test_sync_creates_all_guilds` docstring says sync "refreshes channels for existing guilds"
  - `test_sync_idempotency` implicitly relies on the fact that second sync is a no-op; still passes since `new_channels == 0` remains true

- `tests/e2e/test_channel_refresh_e2e.py` — **Significant impact**
  - Both tests (`test_channel_refresh_reactivates_inactive_channels` and `test_channel_list_without_refresh_uses_cached_data`) call `POST /api/v1/guilds/sync` as **step 1** to populate channels
  - If the guild already exists in the e2e environment (set up by other fixtures), the sync will no longer refresh channels for it — the initial channel population step will silently do nothing
  - These tests need to use an alternative setup mechanism (e.g., the `GET /{guild_id}/channels?refresh=true` endpoint, or a direct DB fixture) instead of the full guild sync

- `tests/integration/api/routes/test_guilds.py`
  - `test_list_channels_accepts_refresh_parameter` — unaffected (tests the per-guild refresh endpoint, not sync)

## Key Discoveries

### The Duplication

The original intent:

- **Sync button** (`POST /api/v1/guilds/sync`): add new guilds to the DB
- **Channel list fetch** (`GET /{guild_id}/channels?refresh=true`): refresh channels for that one guild

The actual current behavior:

- **Sync button** does BOTH: adds new guilds AND refreshes channels for every existing guild
- **Channel list fetch** also refreshes a single guild's channels on demand

### Secondary Bug: Channel Type Filter Mismatch

`_refresh_guild_channels` in `guild_sync.py` (used by sync button) handles types 0, 2, 5.
`guild_service.refresh_guild_channels` (used by the channel list endpoint) only handles type 0.

This inconsistency is a pre-existing issue, separate from this task, but it's worth noting.

## Recommended Approach

Remove the existing-guild channel refresh loop from `sync_all_bot_guilds`. The function should only create new guilds. The `updated_channels` concept is eliminated throughout the stack.

## Implementation Guidance

- **Objectives**: Make the sync button add new guilds only; channel refresh remains in the per-guild `GET /channels?refresh=true` endpoint only

- **Key Tasks**:
  1. `services/bot/guild_sync.py` — remove lines 302–307 (existing guild refresh loop), remove `updated_channels_count` variable, remove `"updated_channels"` from return dict, update docstring
  2. `shared/schemas/guild.py` — remove `updated_channels` field from `GuildSyncResponse`
  3. `services/api/routes/guilds.py` — remove `updated_channels` from logger call and from `GuildSyncResponse(...)` constructor
  4. `frontend/src/api/guilds.ts` — remove `updated_channels: number` from `GuildSyncResponse` interface
  5. `frontend/src/pages/GuildListPage.tsx` — remove `updated_channels` from condition, remove message part, remove from "all synced" implied condition
  6. `tests/services/bot/test_guild_sync.py` — update `test_sync_all_bot_guilds_skip_existing_guilds`: remove `updated_channels` assertion, update `get_guild_channels.await_count` to 1 (only called for new guild), update docstring
  7. `tests/services/api/routes/test_guilds.py` — remove `"updated_channels"` from mock return dicts, remove `result.updated_channels == 0` assertions
  8. `frontend/src/pages/__tests__/GuildListPage.test.tsx` — remove the "displays success message with updated channels on sync" test; update "handles proper pluralization" test to remove updated_channels; remove `updated_channels` field from remaining mock data
  9. `tests/e2e/test_channel_refresh_e2e.py` — replace `POST /api/v1/guilds/sync` setup step with `GET /{guild_id}/channels?refresh=true` call (or a direct DB fixture), since sync no longer refreshes existing guild channels
  10. `tests/e2e/test_guild_sync_e2e.py` — update docstrings that mention "refreshes channels for existing guilds"

- **Dependencies**: None — changes are self-contained within this stack

- **Success Criteria**:
  - `POST /api/v1/guilds/sync` response has only `new_guilds` and `new_channels` fields
  - `GET /{guild_id}/channels?refresh=true` still refreshes channels for a single guild
  - All unit, integration, and e2e tests pass
  - `sync_all_bot_guilds` makes zero Discord API calls for existing guilds
