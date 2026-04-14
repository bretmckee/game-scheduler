<!-- markdownlint-disable-file -->

# Changes: Discord Member Fetch Performance

## Summary

Eliminate ~27s cold-cache load on the game list by skipping participant Discord lookups in `list_games`, parallelizing remaining member fetches with `asyncio.gather`, and exposing a higher rate-limit budget for interactive requests.

## Added

- `tests/unit/shared/cache/test_rate_limit_constants.py` — tests asserting `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND=25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE=45` are importable from `shared.cache.ttl`
- `tests/unit/shared/cache/test_claim_global_and_channel_slot.py` — added tests for `global_max` parameter being passed as ARGV[3] in both `TestClaimGlobalAndChannelSlot` and `TestClaimGlobalSlot`
- `tests/unit/shared/discord/test_discord_api_client.py` — added tests verifying `_make_api_request` forwards `global_max`; added tests for `get_guild_member` accepting `global_max`, `get_guild_members_batch` forwarding `global_max`, and concurrent dispatch via `asyncio.gather`
- `tests/unit/services/api/routes/test_games_helpers.py` — added `TestResolveParcticipantsFlag` for `resolve_participants=False` behaviour; added `TestPrefetchedDisplayData` for `prefetched_display_data` parameter: skips `_resolve_display_data` when provided, passes the map through, and default still calls `_resolve_display_data`
- `tests/unit/services/api/routes/test_games_routes.py` — added `TestListGamesResolvesParticipants` and `TestGetGameInteractiveBudget` for Phase 4; added `TestListGamesPrefetchedDisplayData` for Phase 5: verifies prefetched map is passed to `_build_game_response`, host fetched once across multiple games, and one resolver call per guild
- `tests/unit/services/api/services/test_display_names.py` — added test verifying `resolve_display_names_and_avatars` accepts and threads `global_max`

## Modified

- `shared/cache/ttl.py` — added `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND = 25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE = 45` as module-level integer constants
- `shared/cache/client.py` — changed Lua `global_max = 25` to `tonumber(ARGV[3] or '25')`, added `global_max: int = 25` parameter to `claim_global_and_channel_slot` and `claim_global_slot`, passing `str(global_max)` as ARGV[3]
- `shared/discord/client.py` — added `global_max: int = 25` parameter to `_make_api_request` forwarding to claim calls; added `global_max` to `get_guild_member`; replaced serial loop in `get_guild_members_batch` with `asyncio.gather` and added `global_max` parameter
- `services/api/routes/games.py` — added `import asyncio` and `from collections import defaultdict`; added `prefetched_display_data` parameter to `_build_game_response` (skips `_resolve_display_data` when provided); rewrote `list_games` to batch-collect unique host Discord IDs per guild, issue one `asyncio.gather` over `resolve_display_names_and_avatars` per guild, merge results into a single prefetched map, then gather all `_build_game_response` calls concurrently; also added `resolve_participants=False` to `list_games` call and `global_max=DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE` to `get_game` call (Phase 4)
- `services/api/services/display_names.py` — added `global_max` parameter to `resolve_display_names_and_avatars` and `_fetch_and_cache_display_names`, threaded through to `get_guild_members_batch`

## Removed
