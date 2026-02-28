<!-- markdownlint-disable-file -->

# Task Details: Remove Channel Refresh from Guild Sync

## Research Reference

**Source Research**: #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md

## Phase 1: Remove channel refresh from backend

### Task 1.1: Remove the existing-guild refresh loop from `sync_all_bot_guilds`

Delete the block in `sync_all_bot_guilds` (approximately lines 302–307) that iterates over existing guilds and calls `_refresh_guild_channels`, and remove `updated_channels` from the function's return value / accumulator variables. The function should return only `new_guilds` and `new_channels`.

- **Files**:
  - `services/bot/guild_sync.py` — remove refresh loop and `updated_channels` accumulator
- **Success**:
  - `sync_all_bot_guilds` returns a dict without `updated_channels`
  - `_refresh_guild_channels` is no longer called anywhere from this function
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 7–18) — guild_sync.py analysis
- **Dependencies**:
  - None

### Task 1.2: Remove `updated_channels` from `GuildSyncResponse` schema

Delete the `updated_channels` field from `GuildSyncResponse` in `shared/schemas/guild.py` (around lines 92–94).

- **Files**:
  - `shared/schemas/guild.py` — remove `updated_channels` field from `GuildSyncResponse`
- **Success**:
  - `GuildSyncResponse` has only `new_guilds` and `new_channels` fields
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 25–27) — schema field locations
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Remove `updated_channels` from the sync route handler

In `services/api/routes/guilds.py`, remove the log statement and return value reference to `updated_channels` inside `sync_guilds` (around lines 342, 348).

- **Files**:
  - `services/api/routes/guilds.py` — remove `updated_channels` from logging and return construction
- **Success**:
  - `sync_guilds` builds and returns a `GuildSyncResponse` with no `updated_channels`
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 21–23) — route handler analysis
- **Dependencies**:
  - Task 1.1, Task 1.2

## Phase 2: Update backend unit tests

### Task 2.1: Update `tests/services/bot/test_guild_sync.py`

In `test_sync_all_bot_guilds_skip_existing_guilds` (lines 104–164):

- Remove the assertion `result["updated_channels"] == 1`
- Fix the `get_guild_channels.await_count` assertion: the mock should only be called once (for the new guild), not twice
- Remove any mock setup for `_refresh_guild_channels` that is no longer meaningful

- **Files**:
  - `tests/services/bot/test_guild_sync.py` — update assertions and mock setup
- **Success**:
  - Tests pass without asserting on `updated_channels` or `_refresh_guild_channels` calls for existing guilds
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 43–47) — test file impact analysis
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update `tests/services/api/routes/test_guilds.py`

Remove `updated_channels` from every `mock_sync.return_value` dict and from every assertion that checks `result.updated_channels`. Verify no `updated_channels` key is injected anywhere.

- **Files**:
  - `tests/services/api/routes/test_guilds.py` — remove `updated_channels` from mocks and assertions
- **Success**:
  - All route tests pass; no reference to `updated_channels` remains
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 48–51) — route test impact
- **Dependencies**:
  - Phase 1 completion

## Phase 3: Update frontend code and tests

### Task 3.1: Remove `updated_channels` from the frontend API interface

Delete the `updated_channels: number` field from the `GuildSyncResponse` interface in `frontend/src/api/guilds.ts` (line 26).

- **Files**:
  - `frontend/src/api/guilds.ts` — remove `updated_channels` field
- **Success**:
  - Interface compiles without `updated_channels`
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 29–31) — frontend interface analysis
- **Dependencies**:
  - None (can run in parallel with Phase 1)

### Task 3.2: Remove `updated_channels` UI logic from `GuildListPage.tsx`

In `frontend/src/pages/GuildListPage.tsx`:

- Remove the `result.updated_channels > 0` branch from the sync-result conditional (line 59)
- Remove the "X updated channel(s)" message part from the result string builder (lines 69–71)
- The "All servers and channels are already synced" message should now fire when `new_guilds == 0 && new_channels == 0`

- **Files**:
  - `frontend/src/pages/GuildListPage.tsx` — remove `updated_channels` conditional and message fragment
- **Success**:
  - Component compiles; sync button shows messages based on `new_guilds` and `new_channels` only
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 33–38) — GuildListPage analysis
- **Dependencies**:
  - Task 3.1

### Task 3.3: Update `GuildListPage.test.tsx`

- Line 177 test (`{ new_guilds: 0, new_channels: 1, updated_channels: 3 }`): remove `updated_channels` from mock data; update expected message to no longer include "3 updated channels"
- Line 213 test (`{ new_guilds: 2, new_channels: 1, updated_channels: 1 }`): remove `updated_channels`; update expected message to "Synced 2 new servers, 1 new channel"
- Lines 159, 195: remove `updated_channels: 0` from mock data objects

- **Files**:
  - `frontend/src/pages/__tests__/GuildListPage.test.tsx` — update mock data and expected messages
- **Success**:
  - All frontend unit tests pass; no `updated_channels` in mock data or assertions
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 53–60) — frontend test impact
- **Dependencies**:
  - Task 3.2

## Phase 4: Update e2e tests

### Task 4.1: Update `tests/e2e/test_channel_refresh_e2e.py`

Both e2e tests (`test_channel_refresh_reactivates_inactive_channels` and `test_channel_list_without_refresh_uses_cached_data`) currently call `POST /api/v1/guilds/sync` as step 1 to populate channels for an existing guild. After this change, sync will not refresh channels for existing guilds.

Replace the sync-button call in each test's setup with a direct call to `GET /api/v1/guilds/{guild_id}/channels?refresh=true`, which is the per-guild refresh endpoint that remains unchanged.

- **Files**:
  - `tests/e2e/test_channel_refresh_e2e.py` — replace sync with per-guild channel refresh in setup steps
- **Success**:
  - Both e2e tests pass with new setup mechanism
  - Tests no longer depend on sync button for channel population
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 62–70) — e2e test impact analysis
- **Dependencies**:
  - Phase 1 completion

### Task 4.2: Update docstrings in `tests/e2e/test_guild_sync_e2e.py`

Update docstrings in `test_sync_creates_all_guilds` and `test_sync_idempotency` that describe the sync button as also refreshing channels for existing guilds. Docstrings should reflect that sync only creates new guilds.

- **Files**:
  - `tests/e2e/test_guild_sync_e2e.py` — update docstrings
- **Success**:
  - Docstrings accurately describe the new sync behavior
- **Research References**:
  - #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md (Lines 71–75) — e2e guild sync test notes
- **Dependencies**:
  - None

## Dependencies

- Python ≥ 3.11, pytest, pytest-asyncio
- Node.js, Vitest (frontend)
- `uv` for Python dependency management

## Success Criteria

- `uv run pytest tests/services/bot/test_guild_sync.py tests/services/api/routes/test_guilds.py` passes
- `npm run test` passes inside `frontend/`
- `grep -r updated_channels services/ shared/ frontend/src tests/` returns no results
