<!-- markdownlint-disable-file -->

# Changes: Embed Deletion Detection and Auto-Cancellation

## Status

Complete — all phases implemented.

---

## Added

- [shared/messaging/events.py](../../../shared/messaging/events.py) — Added `EventType.EMBED_DELETED = "game.embed_deleted"` after `GAME_COMPLETED`
- [tests/unit/shared/messaging/test_events.py](../../../tests/unit/shared/messaging/test_events.py) — Added `test_embed_deleted_event_type` verifying member and string value
- [shared/cache/client.py](../../../shared/cache/client.py) — Added `_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA` constant (with parametric `per_channel_max` via ARGV[2]), `claim_global_and_channel_slot` async method, and `claim_global_slot` convenience method (sentinel key + unlimited channel budget)
- [tests/unit/shared/cache/test_claim_global_and_channel_slot.py](../../../tests/unit/shared/cache/test_claim_global_and_channel_slot.py) — New test file covering all four rate-limit paths and key naming
- [shared/discord/client.py](../../../shared/discord/client.py) — Added `channel_id` parameter to `_make_api_request`; calls `claim_global_and_channel_slot` or `claim_global_slot` in a sleep-retry loop before each HTTP call
- [tests/unit/shared/discord/test_discord_api_client.py](../../../tests/unit/shared/discord/test_discord_api_client.py) — Added `TestMakeAPIRequestRateLimit` class (3 tests) and updated `mock_redis` fixture to expose `claim_global_slot` / `claim_global_and_channel_slot` as `AsyncMock(return_value=0)`

- [alembic/versions/fd0d4f43e53a_add_message_id_index.py](../../../alembic/versions/fd0d4f43e53a_add_message_id_index.py) — New Alembic migration adding `ix_game_sessions_message_id` index on `game_sessions.message_id`; uses standard `op.create_index()` (no `CONCURRENTLY` needed — migrations run in the init container before any other service starts)

## Modified

## Removed
