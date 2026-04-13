<!-- markdownlint-disable-file -->

# Changes: Discord Member Fetch Performance

## Summary

Eliminate ~27s cold-cache load on the game list by skipping participant Discord lookups in `list_games`, parallelizing remaining member fetches with `asyncio.gather`, and exposing a higher rate-limit budget for interactive requests.

## Added

- `tests/unit/shared/cache/test_rate_limit_constants.py` — tests asserting `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND=25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE=45` are importable from `shared.cache.ttl`

## Modified

- `shared/cache/ttl.py` — added `DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND = 25` and `DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE = 45` as module-level integer constants

## Removed
