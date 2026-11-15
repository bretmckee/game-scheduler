<!-- markdownlint-disable-file -->

# Changes: Embed Deletion Detection and Auto-Cancellation

**Plan**: .copilot-tracking/planning/plans/20260402-01-embed-deletion-detection.plan.md
**Details**: .copilot-tracking/planning/details/20260402-01-embed-deletion-detection-details.md

---

## Phase 1: Foundation (Shared Library Changes) — COMPLETE

### Added

- `shared/messaging/events.py` — Added `EventType.EMBED_DELETED = "game.embed_deleted"` constant after `GAME_CANCELLED`
- `shared/cache/client.py` — Added `_GLOBAL_AND_CHANNEL_RATE_LIMIT_LUA` Lua script and `claim_global_and_channel_slot(channel_id)` async method for atomic combined rate limiting
- `shared/cache/client.py` — Added `claim_global_slot()` convenience wrapper that bypasses per-channel limiting
- `tests/unit/shared/cache/test_cache_client_unit.py` — Unit tests for `claim_global_and_channel_slot` (zero-wait, global-full, channel-full, both-full)

### Modified

- `shared/discord/client.py` — Modified `_make_api_request` to call `claim_global_and_channel_slot` before every HTTP dispatch
- `tests/unit/shared/discord/test_discord_client_unit.py` — Added test verifying rate limit claim precedes HTTP call in `_make_api_request`

---

## Phase 2: API Service Changes — COMPLETE

### Added

- `services/api/services/embed_deletion_consumer.py` — New `EmbedDeletionConsumer` class and `get_embed_deletion_consumer()` singleton factory; subscribes to `game.embed_deleted` RabbitMQ events and cancels games via `_delete_game_internal`
- `tests/unit/services/api/services/test_embed_deletion_consumer.py` — Unit tests for `_handle_embed_deleted`: known game triggers cancel+commit, unknown game_id silently dropped

### Modified

- `services/api/services/games.py` — Extracted `_delete_game_internal(game)` from `delete_game`; the existing public method now delegates to it after the auth check
- `services/api/app.py` — Registered `EmbedDeletionConsumer` in the lifespan context alongside the SSE bridge (start on startup, cancel+stop on shutdown)
- `tests/unit/services/api/services/test_games_service.py` — Added `test_delete_game_internal_releases_images_and_publishes` to verify the extracted method works in isolation

---

## Phase 3: Bot Service Changes — COMPLETE

### Added

- `services/bot/events/publisher.py` — Added `publish_embed_deleted(game_id, channel_id, message_id)` method to `BotEventPublisher`; publishes `EventType.EMBED_DELETED` with routing key `game.embed_deleted`
- `tests/unit/services/bot/events/test_publisher.py` — Added `test_publish_embed_deleted` covering the new method
- `tests/unit/services/bot/test_bot.py` — Added `test_on_raw_message_delete_game_found_publishes`, `test_on_raw_message_delete_no_game_no_publish`, `test_sweep_deleted_embeds_publishes_for_missing_messages`, `test_sweep_deleted_embeds_skips_existing_messages`, `test_sweep_deleted_embeds_no_games`, `test_sweep_deleted_embeds_no_publisher_skips`

### Modified

- `services/bot/bot.py` — Added `guild_messages=True` to `discord.Intents(...)`; added `on_raw_message_delete` handler (DB lookup → publish `EMBED_DELETED` if game found); added `_sweep_deleted_embeds()` coroutine (PriorityQueue of games, ~60 workers, `claim_global_and_channel_slot` + `fetch_message`, publishes on `NotFound`); updated `on_ready` and `on_resumed` to call `_sweep_deleted_embeds` after `_recover_pending_workers`; added imports for `get_bypass_db_session`, `GameSession`, `get_redis_client`
- `tests/unit/services/bot/test_bot.py` — Updated `test_bot_intents_configuration` to assert `guild_messages is True`

---

## Phase 4: Optional — DB Index

### Added

<!-- populated as tasks complete -->

---

<!-- Merged from the former .copilot-tracking/changes/ copy of this log -->

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
