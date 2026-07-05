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

## Phase 10: Docker, Config, and Dependency Cleanup ✅

- Removed `rabbitmq` service block from [compose.yaml](compose.yaml)
- Removed `retry-daemon` service block from [compose.yaml](compose.yaml)
- Removed `RABBITMQ_URL` env var from `init`, `bot`, `api`, `scheduler` services in [compose.yaml](compose.yaml)
- Removed `rabbitmq` from `init` `depends_on` in [compose.yaml](compose.yaml)
- Removed `rabbitmq_data` volume from [compose.yaml](compose.yaml)
- Removed `rabbitmq` override section from [compose.override.yaml](compose.override.yaml)
- Removed `rabbitmq` override section from [compose.test.yaml](compose.test.yaml)
- Removed `rabbitmq` override section and `retry-daemon` stub from [compose.int.yaml](compose.int.yaml)
- Removed `rabbitmq` from `system-ready` depends_on in [compose.int.yaml](compose.int.yaml)
- Removed `RABBITMQ_*` env vars from `integration-tests` in [compose.int.yaml](compose.int.yaml)
- Removed `rabbitmq_data` volume from [compose.int.yaml](compose.int.yaml)
- Removed `rabbitmq` override section and `retry-daemon` stub from [compose.e2e.yaml](compose.e2e.yaml)
- Removed `rabbitmq` from `system-ready` depends_on in [compose.e2e.yaml](compose.e2e.yaml)
- Removed `RABBITMQ_URL` from `e2e-tests` environment in [compose.e2e.yaml](compose.e2e.yaml)
- Removed `rabbitmq_data` volume from [compose.e2e.yaml](compose.e2e.yaml)
- Removed `retry-daemon` from `frontend` depends_on in [compose.prod.yaml](compose.prod.yaml)
- Removed `rabbitmq` override section from [compose.staging.yaml](compose.staging.yaml)
- Removed RabbitMQ configuration section from [config.template/env.template](config.template/env.template)
- Removed retry daemon config vars from [config.template/env.template](config.template/env.template)
- Removed RabbitMQ port vars from [config.template/env.template](config.template/env.template)
- Deleted `config.template/rabbitmq/` directory (RabbitMQ config files)
- Removed `aio-pika`, `pika`, `opentelemetry-instrumentation-aio-pika` from [pyproject.toml](pyproject.toml)
- Removed `pika.data` DeprecationWarning filter from [pyproject.toml](pyproject.toml)
- Updated integration marker description in [pyproject.toml](pyproject.toml)
- Removed `AioPikaInstrumentor` import and usage from [shared/telemetry.py](shared/telemetry.py)
- Updated telemetry docstring and log message in [shared/telemetry.py](shared/telemetry.py)
- Removed `AioPikaInstrumentor` mocks from [tests/unit/shared/test_telemetry.py](tests/unit/shared/test_telemetry.py)
- Deleted [docker/retry.Dockerfile](docker/retry.Dockerfile)
- Ran `uv sync` — uninstalled aio-pika, aiormq, pamqp, pika, opentelemetry-instrumentation-aio-pika
- All 2420 unit tests pass; mypy clean; all 6 Docker images build; 318 integration tests pass; 98 e2e tests pass

## Phase 4: Replace SSE Bridge Consumer (Flow 8) ✅

- Migrated `SSEGameUpdateBridge` from `EventConsumer` (RabbitMQ) to asyncpg `LISTEN game_updated_sse`
- `__init__` now takes `db_url: str`; `_on_notify` synchronous callback parses JSON and schedules `_broadcast_to_clients`
- `_broadcast_to_clients` signature changed from `Event` to `dict`
- `start_consuming` / `stop_consuming` manage asyncpg connection lifecycle
- `get_sse_bridge()` reads `db_url` from `get_api_config().database_url`
- Removed `shared/messaging/` imports (`EventConsumer`, `Event`, `EventType`) from `sse_bridge.py`
- Updated `tests/unit/services/api/services/test_sse_bridge_unit.py` to use asyncpg mocks and dict payloads
