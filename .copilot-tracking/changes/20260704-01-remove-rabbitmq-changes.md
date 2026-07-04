# Changes: Remove RabbitMQ

## Summary

Replace all RabbitMQ message flows with PostgreSQL LISTEN/NOTIFY + a new `bot_action_queue` table.

## Phase 1: Add `BotActionQueue` Model + Alembic Migration

### Added

- `shared/models/bot_action_queue.py` — new `BotActionQueue` SQLAlchemy model with `id`, `action_type` (NOT NULL), `game_id`, `channel_id`, `message_id`, `user_id`, `discord_id`, `payload` (JSONB), `enqueued_at` columns
- `alembic/versions/20260704_add_bot_action_queue.py` — migration creating `bot_action_queue` table, `ix_bot_action_queue_enqueued` index, `notify_bot_action_queue_changed` trigger function, and INSERT trigger
- `tests/unit/shared/models/test_bot_action_queue.py` — unit tests for `BotActionQueue` model attributes and constraints

### Modified

- `shared/models/__init__.py` — added `BotActionQueue` import and `__all__` export

### Removed

---

## Phase 2: Add `cancel_game` Service + Update `GameService._delete_game_internal`

### Added

- `shared/services/game_cancellation.py` — `cancel_game(db, game, event_publisher=None)` releases image refs, deletes game row, optionally enqueues GAME_CANCELLED event
- `tests/unit/shared/services/test_game_cancellation.py` — 6 unit tests for `cancel_game`

### Modified

- `services/api/services/games.py` — `_delete_game_internal` delegates to `cancel_game` as thin wrapper

### Removed

## Phase 3: Migrate API to Bot Flows (Flows 1-4) + SSE NOTIFY

### Added

- `tests/unit/api/services/test_games.py` — new `TestPublishGameCreated`, `TestPublishGameUpdated`, `TestPublishPlayerRemoved`, `TestNotifyDemotedUsers` test classes verifying BotActionQueue inserts and pg_notify behavior

### Modified

- `shared/services/game_cancellation.py` — replaced `event_publisher: DeferredEventPublisher | None` parameter with `enqueue_cancellation: bool = True`; now inserts `BotActionQueue(action_type='game_cancelled', ...)` directly instead of calling `publish_deferred`
- `tests/unit/shared/services/test_game_cancellation.py` — updated tests to use new `enqueue_cancellation` parameter and check `db.add` for `BotActionQueue` rows
- `services/api/services/games.py` — removed `event_publisher` from `GameService.__init__`; added `json`, `pg_insert`, `BotActionQueue`, `MessageRefreshQueue` imports; replaced `_publish_game_created` with BotActionQueue insert; replaced `_publish_game_updated` with MessageRefreshQueue upsert + pg_notify; replaced `_publish_player_removed` with BotActionQueue insert; replaced `_notify_demoted_users` with BotActionQueue inserts; replaced `_publish_promotion_notification` with BotActionQueue insert; replaced inline `host_added_dropout` publish in `leave_game` with BotActionQueue insert; removed dead `_publish_game_cancelled` method; updated `_delete_game_internal` to call `cancel_game_service(db, game)` without publisher
- `services/api/routes/games.py` — removed `DeferredEventPublisher` and `EventPublisher` imports and instantiation from `_get_game_service`; removed `event_publisher` from `GameService(...)` constructor call
- `services/api/services/embed_deletion_consumer.py` — removed dead `DeferredEventPublisher`/`EventPublisher` usage from `GameService` instantiation (file itself remains; deleted in Phase 5)
- `tests/unit/services/api/services/conftest.py` — removed `mock_event_publisher` fixture and its import; removed `event_publisher` from `game_service` fixture
- `tests/unit/services/api/services/test_games_service.py` — replaced `publish_deferred` assertion with BotActionQueue `db.add` assertion; removed `EventType` import; added `BotActionQueue` import; updated `test_join_game_success` and `test_leave_game_success` to add pg_notify/upsert execute mocks; removed all `mock_event_publisher` fixture parameters
- `tests/unit/services/api/services/test_games_promotion.py` — replaced all `mock_event_publisher.publish_deferred.call_args_list` assertions with `mock_db.add.call_args_list` BotActionQueue checks; replaced `mock_event_publisher.reset_mock()` with `mock_db.add.reset_mock()`; removed `EventType` import; removed `mock_event_publisher` from all test signatures
- `tests/unit/api/services/test_games.py` — updated `game_service` fixture to remove `event_publisher`; updated leave_game tests to check BotActionQueue rows; updated execute side_effect lists to include pg_notify/upsert calls
- `tests/unit/services/test_game_service_persist_and_publish.py` — removed `event_publisher` from `game_service` fixture
- `tests/unit/services/test_clone_game.py` — removed `event_publisher` from `game_service` fixture
- `tests/unit/services/test_system_clone_for_recurrence.py` — removed `event_publisher` from `game_service` fixture

### Removed

---

- `tests/integration/test_games_route_guild_isolation.py` — removed `EventPublisher` import and `event_publisher=EventPublisher()` from all `GameService` constructor calls
- `tests/integration/services/api/services/test_game_image_integration.py` — removed `mock_event_publisher` from all test function signatures and `event_publisher=mock_event_publisher` from all `GameService` constructor calls
- `tests/integration/test_embed_deletion_consumer.py` — updated to check `bot_action_queue` table (zero rows, since the Discord message is already gone) instead of RabbitMQ queue; removed `rabbitmq_channel` fixture dependency
- `tests/integration/test_game_signup_methods.py` — updated three tests to check `bot_action_queue` DB rows instead of RabbitMQ queues
- `tests/integration/test_clone_game_endpoint.py` — updated `test_clone_game_endpoint_publishes_game_created_event` to check `bot_action_queue` DB row
- `tests/integration/test_recurrence_clone.py` — updated `test_clear_post_at_announces_recurrence_clone` to check `bot_action_queue` DB row
- `tests/unit/services/api/services/test_embed_deletion_consumer.py` — updated `test_handle_embed_deleted_cancels_game` to check that `cancel_game` is called with `enqueue_cancellation=False`

### Removed

---

## Known State After Phase 3

E2E tests are failing because:

- The API now sends `game_created`/`game_cancelled`/etc. actions to `bot_action_queue` (DB)
- The bot still only listens to RabbitMQ for these events (not yet updated)
- Phase 5 implements the bot's `BotActionListener` that processes `bot_action_queue` rows
- E2E tests will pass again once Phases 5-8 are complete

---

## Phase 5: Bot Embed Deletion Handler + Bot Action Queue Consumer

### Added

- `services/bot/bot_action_listener.py` — `BotActionListener` class with asyncpg `LISTEN bot_action_queue_changed`; drains `bot_action_queue` rows on NOTIFY; dispatches each row to the appropriate `EventHandlers` handler method; deletes row within the same transaction (crash safety)
- `tests/unit/bot/test_bot_action_listener.py` — unit tests for `BotActionListener` covering all action-type dispatches, drain/spawn logic, and start() lifecycle

### Modified

- `services/bot/bot.py` — added `BotActionListener` import; registered `BotActionListener` task in `on_ready`; updated `on_raw_message_delete` to call `cancel_game(db, game, enqueue_cancellation=False)` directly (no RabbitMQ); updated `_sweep_deleted_embeds` to remove publisher guard; updated `_run_sweep_worker` to remove `publisher` param and call new `_cancel_missing_embed`; added `_cancel_missing_embed` method; added `cancel_game` import
- `shared/services/game_cancellation.py` — moved `game.channel` access inside the `if enqueue_cancellation:` block to avoid lazy-loading errors when called from the bot (where channel is not eagerly loaded)
- `services/bot/events/publisher.py` — deleted `publish_embed_deleted` method (now dead)
- `services/api/app.py` — removed `EmbedDeletionConsumer` import and startup/shutdown lifecycle
- `tests/unit/services/bot/test_bot.py` — updated embed deletion tests to verify `cancel_game` called directly; updated sweep tests to verify `cancel_game` called; removed `publisher` param from `_run_sweep_worker` call sites; removed `test_sweep_deleted_embeds_no_publisher_skips` (guard removed)
- `tests/unit/bot/test_sweep_metrics.py` — removed `mock_publisher` from `_run_sweep_worker` calls; added `_cancel_missing_embed` patch
- `tests/unit/services/bot/events/test_publisher.py` — deleted `test_publish_embed_deleted` (method deleted)

### Removed

- `services/api/services/embed_deletion_consumer.py` — deleted; bot handles embed deletion directly
- `tests/unit/services/api/services/test_embed_deletion_consumer.py` — deleted (unit tests for deleted module)
- `tests/integration/test_embed_deletion_consumer.py` — deleted (integration tests for deleted module)

---

## Phase 8: Remove Dead Messaging Infrastructure

### Modified

### Removed
