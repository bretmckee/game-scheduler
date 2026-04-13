<!-- markdownlint-disable-file -->

# Changes: Discord Member Fetch Performance

## Summary

Eliminate ~27s cold-cache load on the game list by skipping participant Discord lookups in `list_games`, parallelizing remaining member fetches with `asyncio.gather`, and exposing a higher rate-limit budget for interactive requests.

## Added

- `tests/unit/shared/cache/test_rate_limit_constants.py` — tests asserting `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND=25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE=45` are importable from `shared.cache.ttl`
- `tests/unit/shared/cache/test_claim_global_and_channel_slot.py` — added tests for `global_max` parameter being passed as ARGV[3] in both `TestClaimGlobalAndChannelSlot` and `TestClaimGlobalSlot`
- `tests/unit/shared/discord/test_discord_api_client.py` — added tests verifying `_make_api_request` forwards `global_max`; added tests for `get_guild_member` accepting `global_max`, `get_guild_members_batch` forwarding `global_max`, and concurrent dispatch via `asyncio.gather`

## Modified

- `shared/cache/ttl.py` — added `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND = 25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE = 45` as module-level integer constants
- `shared/cache/client.py` — changed Lua `global_max = 25` to `tonumber(ARGV[3] or '25')`, added `global_max: int = 25` parameter to `claim_global_and_channel_slot` and `claim_global_slot`, passing `str(global_max)` as ARGV[3]
- `shared/discord/client.py` — added `global_max: int = 25` parameter to `_make_api_request` forwarding to claim calls; added `global_max` to `get_guild_member`; replaced serial loop in `get_guild_members_batch` with `asyncio.gather` and added `global_max` parameter

## Removed
