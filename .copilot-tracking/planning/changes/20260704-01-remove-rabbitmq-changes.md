<!-- markdownlint-disable-file -->

# Changes: Remove RabbitMQ

## Phase 1: Add `BotActionQueue` Model + Alembic Migration ✅

- Added `shared/models/bot_action_queue.py` with `BotActionQueue` SQLAlchemy model
- Exported from `shared/models/__init__.py`
- Created Alembic migration with table DDL, index, INSERT trigger, and `pg_notify('bot_action_queue_changed', '')`
- Unit tests: `tests/unit/shared/models/test_bot_action_queue.py`

## Phase 2: Add `cancel_game` Service ✅

- Added `shared/services/game_cancellation.py` with `cancel_game(db, game, enqueue_cancellation=True)`
- Updated `GameService._delete_game_internal` to delegate to `cancel_game`
- Updated `embed_deletion_consumer.py` to call `cancel_game(db, game, enqueue_cancellation=False)`
- Unit tests: `tests/unit/shared/services/test_game_cancellation.py`

## Phase 3: Migrate API to Bot Flows (Flows 1-4) + SSE NOTIFY ✅

- Removed `DeferredEventPublisher` / `EventPublisher` from `GameService.__init__`
- Replaced `_publish_game_created` with `BotActionQueue` INSERT (`action_type='game_created'`)
- Replaced `_publish_game_updated` with `MessageRefreshQueue` upsert + `pg_notify('game_updated_sse', ...)`
- Replaced `_publish_player_removed` with `BotActionQueue` INSERT (`action_type='player_removed'`)
- Replaced `_notify_demoted_users` / `_publish_promotion_notification` with `BotActionQueue` INSERTs (`action_type='send_dm'`)
- Replaced `host_added_dropout` publish in `leave_game` with `BotActionQueue` INSERT
- Removed dead `_publish_game_cancelled` method
- Updated `cancel_game` signature: replaced `event_publisher` param with `enqueue_cancellation: bool`
- Removed `DeferredEventPublisher` / `EventPublisher` creation from `routes/games.py`
- Updated all affected unit and integration tests

## Phase 4: Replace SSE Bridge Consumer (Flow 8) ✅

- Migrated `SSEGameUpdateBridge` from `EventConsumer` (RabbitMQ) to asyncpg `LISTEN game_updated_sse`
- `__init__` now takes `db_url: str`; `_on_notify` synchronous callback parses JSON and schedules `_broadcast_to_clients`
- `_broadcast_to_clients` signature changed from `Event` to `dict`
- `start_consuming` / `stop_consuming` manage asyncpg connection lifecycle
- `get_sse_bridge()` reads `db_url` from `get_api_config().database_url`
- Removed `shared/messaging/` imports (`EventConsumer`, `Event`, `EventType`) from `sse_bridge.py`
- Updated `tests/unit/services/api/services/test_sse_bridge_unit.py` to use asyncpg mocks and dict payloads
