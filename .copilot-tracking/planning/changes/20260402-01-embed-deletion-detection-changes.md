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

## Phase 3: Bot Service Changes

### Added

<!-- populated as tasks complete -->

### Modified

<!-- populated as tasks complete -->

---

## Phase 4: Optional — DB Index

### Added

<!-- populated as tasks complete -->
