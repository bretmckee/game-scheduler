---
applyTo: '.copilot-tracking/changes/20260228-01-remove-channel-refresh-from-guild-sync-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove Channel Refresh from Guild Sync

## Overview

Remove the existing-guild channel refresh loop from `sync_all_bot_guilds` so the sync button only creates new guilds, and eliminate `updated_channels` throughout the full stack.

## Objectives

- `sync_all_bot_guilds` no longer calls `_refresh_guild_channels` for existing guilds
- `updated_channels` field removed from `GuildSyncResponse` schema, route handler, frontend interface, and frontend UI logic
- All affected unit, integration, and e2e tests updated to reflect the new behavior
- The per-guild `GET /{guild_id}/channels?refresh=true` endpoint remains unchanged as the sole channel-refresh mechanism

## Research Summary

### Project Files

- `services/bot/guild_sync.py` — contains `sync_all_bot_guilds` with the refresh loop to remove (lines 302–307)
- `services/api/routes/guilds.py` — route handler that logs and returns `updated_channels` (lines 342, 348)
- `shared/schemas/guild.py` — `GuildSyncResponse` schema with `updated_channels` field (lines 92–94)
- `frontend/src/api/guilds.ts` — `GuildSyncResponse` interface with `updated_channels: number` (line 26)
- `frontend/src/pages/GuildListPage.tsx` — UI logic referencing `updated_channels` (lines 59, 69–71)
- `tests/services/bot/test_guild_sync.py` — unit tests asserting on `updated_channels` and refresh call counts (lines 104–164)
- `tests/services/api/routes/test_guilds.py` — multiple tests passing/asserting `updated_channels`
- `frontend/src/pages/__tests__/GuildListPage.test.tsx` — frontend tests with `updated_channels` in mock data (lines 159, 177, 195, 213)
- `tests/e2e/test_channel_refresh_e2e.py` — e2e tests that use sync as channel-population step (both tests)

### External References

- #file:../research/20260228-01-remove-channel-refresh-from-guild-sync-research.md — full findings and code locations

## Implementation Checklist

### [ ] Phase 1: Remove channel refresh from backend

- [ ] Task 1.1: Remove the existing-guild refresh loop from `sync_all_bot_guilds` in `guild_sync.py`
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 14–36)

- [ ] Task 1.2: Remove `updated_channels` from `GuildSyncResponse` in `shared/schemas/guild.py`
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 38–52)

- [ ] Task 1.3: Remove `updated_channels` logging and return value from the sync route in `guilds.py`
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 54–68)

### [ ] Phase 2: Update backend unit tests

- [ ] Task 2.1: Update `tests/services/bot/test_guild_sync.py` — remove `updated_channels` assertions and fix `get_guild_channels` call-count expectations
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 71–92)

- [ ] Task 2.2: Update `tests/services/api/routes/test_guilds.py` — remove `updated_channels` from mock return values and assertions
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 94–109)

### [ ] Phase 3: Update frontend code and tests

- [ ] Task 3.1: Remove `updated_channels` from `GuildSyncResponse` interface in `frontend/src/api/guilds.ts`
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 112–124)

- [ ] Task 3.2: Remove `updated_channels` conditional and message from `frontend/src/pages/GuildListPage.tsx`
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 126–148)

- [ ] Task 3.3: Update `frontend/src/pages/__tests__/GuildListPage.test.tsx`
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 150–175)

### [ ] Phase 4: Update e2e tests

- [ ] Task 4.1: Update `tests/e2e/test_channel_refresh_e2e.py` — replace sync-button channel-population step with the per-guild `GET /{guild_id}/channels?refresh=true` endpoint
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 178–205)

- [ ] Task 4.2: Update docstrings in `tests/e2e/test_guild_sync_e2e.py` that reference channel refresh behaviour
  - Details: .copilot-tracking/details/20260228-01-remove-channel-refresh-from-guild-sync-details.md (Lines 207–218)

## Dependencies

- Python (pytest, pytest-asyncio)
- TypeScript / Vitest
- Running test suite: `uv run pytest` and `npm test` inside `frontend/`

## Success Criteria

- `sync_all_bot_guilds` never calls `_refresh_guild_channels`
- `GuildSyncResponse` has no `updated_channels` field in schema, route, or frontend interface
- All Python unit tests pass: `uv run pytest tests/services/bot/test_guild_sync.py tests/services/api/routes/test_guilds.py`
- All frontend unit tests pass: `npm run test` in `frontend/`
- No references to `updated_channels` remain anywhere in the codebase
