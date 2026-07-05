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

## Phase 6: Migrate Scheduler Flows (Flows 5-7)

### Modified

- `services/scheduler/event_builders.py` — replaced `SyncEventPublisher.publish()` calls with `BotActionQueue(...)` construction; `build_notification_event` and `build_status_transition_event` now return `BotActionQueue` instances
- `services/scheduler/participant_action_event_builder.py` — replaced publisher call with `BotActionQueue(action_type="participant_drop_due", ...)` construction
- `services/scheduler/generic_scheduler_daemon.py` — removed `rabbitmq_url` constructor parameter and `SyncEventPublisher` import; `__init__` no longer stores `rabbitmq_url`; `connect()` no longer creates publisher; `_process_item` now calls `db.add(event)` instead of `publisher.publish(event)`; `_cleanup()` no longer calls `publisher.close()`
- `tests/unit/services/scheduler/test_event_builders.py` — updated assertions to verify `BotActionQueue` instances are returned with correct `action_type` and `payload` fields
- `tests/unit/services/test_participant_action_event_builder.py` — updated assertions to verify `BotActionQueue` instance is returned with correct `action_type` and `payload`
- `tests/unit/services/scheduler/test_generic_scheduler_daemon.py` — removed `rabbitmq_url` from all constructor calls; updated `_process_item` tests to assert `db.add(event)` instead of `publisher.publish(event)`; removed publisher cleanup tests
- `tests/integration/test_notification_daemon.py` — replaced `get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)` assertions with `bot_action_queue` DB queries; removed `rabbitmq_channel` fixture from impacted test methods; updated `clean_notification_schedule` fixture to remove RabbitMQ dependency
- `tests/integration/test_participant_action_daemon.py` — replaced RabbitMQ assertions with `bot_action_queue` DB queries checking `action_type='participant_drop_due'` and `payload.participant_id`; removed `rabbitmq_channel` fixture; removed `json`, `QUEUE_BOT_EVENTS`, `consume_one_message`, `get_queue_message_count` imports; updated `clean_bot_events_queue` fixture
- `tests/integration/test_status_transitions.py` — replaced `get_queue_message_count` assertions with `bot_action_queue` DB queries; removed `rabbitmq_channel` fixture; updated `purge_bot_events_queue` fixture to remove RabbitMQ dependency
- `tests/integration/test_clone_confirmation_notification.py` — replaced RabbitMQ assertions with `bot_action_queue` DB queries checking `payload.notification_type` and `payload.participant_id`; removed `rabbitmq_channel` fixture; removed `json`, `QUEUE_BOT_EVENTS`, `consume_one_message`, `get_queue_message_count` imports; updated `clean_notifications_queue` fixture

### Removed

---

## Phase 7: Migrate Bot Join/Leave/Drop Handlers (Flow 10)

### Added

- `tests/unit/bot/handlers/test_join_game_handler.py` — new unit tests for `handle_join_game` verifying `MessageRefreshQueue` upsert and `pg_notify` execute calls (no publisher)

### Modified

- `services/bot/handlers/join_game.py` — removed `publisher` parameter; added `selectinload(GameSession.channel)` to the session query; replaced `publisher.publish_game_updated(...)` with direct `db.execute(pg_insert(MessageRefreshQueue)...)` upsert and `db.execute(text("SELECT pg_notify(...)"))` call
- `services/bot/handlers/leave_game.py` — removed `publisher` parameter; replaced `publisher.publish_game_updated(...)` with direct `MessageRefreshQueue` upsert + `pg_notify` execute calls
- `services/bot/handlers/participant_drop.py` — removed `publisher` parameter; added `selectinload(GameSession.channel)` to the query; moved notify logic inside the existing `async with db.begin()` block as direct upsert + `pg_notify` execute calls
- `services/bot/events/publisher.py` — deleted `publish_game_updated` method (no longer called anywhere)
- `services/bot/handlers/button_handler.py` — removed `publisher` argument from `handle_join_game` and `handle_leave_game` call sites
- `services/bot/events/handlers.py` — removed `publisher` argument from `participant_drop` call in `_handle_participant_drop_due`
- `services/bot/views/clone_confirmation_view.py` — removed `publisher` argument from `participant_drop` call
- `tests/unit/bot/handlers/test_leave_game_handler.py` — removed `mock_publisher` fixture and parameter; updated `db.execute` side-effect lists to include MRQ upsert and `pg_notify` calls; replaced `publish_game_updated.assert_awaited_once_with` with execute-call string assertions
- `tests/unit/bot/handlers/test_participant_drop_handler.py` — removed `mock_publisher` fixture and parameter; updated `db.execute` side-effect lists; replaced publisher assertions with execute-call string assertions
- `tests/unit/bot/events/test_handlers_lifecycle_events.py` — removed `publisher` argument from `participant_drop` mock call in `_handle_participant_drop_due` test
- `tests/unit/services/bot/handlers/test_participant_drop.py` — removed `publisher` argument from `participant_drop` call
- `tests/unit/bot/views/test_clone_confirmation_view.py` — removed `publisher` argument from `participant_drop` call; removed `test_publish_game_updated` test assertion
- `tests/unit/services/bot/events/test_publisher.py` — removed `test_publish_game_updated` test (method deleted)
- `tests/integration/test_join_game.py` — replaced `publish_game_updated` RabbitMQ assertions with `message_refresh_queue` DB row checks
- `tests/integration/test_leave_game.py` — replaced `publish_game_updated` RabbitMQ assertions with `message_refresh_queue` DB row checks
- `tests/integration/test_participant_drop_event.py` — replaced RabbitMQ/publisher assertions with `message_refresh_queue` DB row checks; removed `rabbitmq_channel` fixture dependencies
- `tests/integration/test_button_handler.py` — replaced `mock_publisher.publish_game_updated.assert_awaited_once_with(...)` assertions with `message_refresh_queue` DB row checks; removed unused `mock_publisher` from test signatures

### Removed

---

## Phase 8: Remove Dead Messaging Infrastructure

### Modified

- `shared/schemas/events.py` — added `NotificationDueEvent` and `NotificationSendDMEvent` types (moved from deleted `shared/messaging/events.py`)
- `services/bot/events/handlers.py` — removed `EventConsumer`, `Event`, `EventType`, `get_bot_publisher` imports; removed `start_consuming`, `stop_consuming`, `_process_event` dead methods; removed `self.consumer` and `self._handlers` fields; updated `_handle_clone_confirmation` to call `CloneConfirmationView` without `publisher`; updated import to use `shared.schemas.events` for `NotificationDueEvent`, `NotificationSendDMEvent`
- `services/bot/views/clone_confirmation_view.py` — removed `BotEventPublisher` import and `publisher` parameter from `__init__`
- `services/bot/handlers/button_handler.py` — removed `BotEventPublisher` import and `publisher` parameter from `__init__`
- `services/bot/bot.py` — removed `BotEventPublisher` import and `self.event_publisher` field; removed publisher creation/connect in `setup_hook`; removed `start_consuming` call from `on_ready`; removed `stop_consuming`/`disconnect` from `close()`; `ButtonHandler()` called without publisher
- `services/bot/events/__init__.py` — removed `BotEventPublisher` import and export
- `shared/database.py` — removed `publish_deferred_events_after_commit` and `clear_deferred_events_after_rollback` SQLAlchemy event listeners; removed unused `asyncio` and `event` imports
- `services/init/main.py` — removed `initialize_rabbitmq` import and call; updated phase count from 5 to 4
- `tests/unit/services/bot/events/test_handlers_clone.py` — removed `get_bot_publisher` patches; updated `CloneConfirmationView` assertion to remove `publisher=ANY`; updated import to `shared.schemas.events`
- `tests/unit/services/bot/events/test_handlers_join_notification.py` — updated `NotificationDueEvent` import to `shared.schemas.events`
- `tests/unit/services/bot/events/test_handlers_lifecycle_events.py` — updated `NotificationDueEvent` import to `shared.schemas.events`
- `tests/unit/bot/events/test_handlers_misc.py` — removed `get_bot_publisher` patches from clone confirmation tests; updated `NotificationDueEvent` import
- `tests/unit/bot/views/test_clone_confirmation_view.py` — removed `BotEventPublisher` import and `mock_publisher` fixture; removed `publisher` from test signatures
- `tests/unit/bot/events/test_handlers_game_events.py` — removed `Event, EventType` import; removed `_process_event` tests (method deleted)
- `tests/unit/bot/handlers/test_participant_drop_handler.py` — removed `EventType` import; removed `test_participant_drop_due_is_registered_in_event_handlers` test
- `tests/unit/services/bot/test_bot.py` — removed `BotEventPublisher` patches from setup_hook tests; deleted `test_setup_hook_publisher_initialization_failure`; updated `test_on_raw_message_delete_no_game_no_publish` to assert `cancel_game` not called
- `tests/unit/bot/test_bot_events.py`, `test_bot_reconnect_repopulation.py`, `test_guild_projection_incremental.py`, `test_sweep_orphaned_embeds.py`, `test_test_server.py`, `test_trigger_sweep.py`, `test_bot_ready.py`, `test_sweep_metrics.py` — removed `instance.event_publisher` assignments from bot fixture functions
- `tests/unit/services/init/test_main_roles_only.py` — removed `initialize_rabbitmq` patches from all 4 tests

### Removed

- `shared/messaging/` — deleted entire directory (AMQP publisher/consumer infrastructure)
- `services/retry/` — deleted entire directory (AMQP retry daemon)
- `services/bot/events/publisher.py` — deleted `BotEventPublisher` class (all callers migrated)
- `services/init/rabbitmq.py` — deleted RabbitMQ queue initialization script
- `services/scheduler/services/notification_service.py` — deleted dead code (replaced by Phase 6 `event_builders.py`)
- `tests/unit/shared/messaging/` — deleted test directory for deleted module
- `tests/unit/services/retry/` — deleted test directory for deleted retry service
- `tests/unit/services/bot/events/test_handlers_init.py` — deleted tests for removed `start_consuming`/`stop_consuming` methods
- `tests/unit/services/bot/events/test_publisher.py` — deleted tests for deleted `BotEventPublisher`
- `tests/unit/services/scheduler/test_notification_service.py` — deleted tests for deleted module
- `tests/unit/shared/test_database_deferred_publishing.py` — deleted tests for removed deferred publishing listeners

### Additional cleanup for integration/e2e test collection

- `compose.int.yaml` — overrode `retry-daemon` with alpine stub; removed `retry-daemon` from `system-ready.depends_on`
- `compose.e2e.yaml` — added `retry-daemon` alpine stub; removed `retry-daemon` from `system-ready.depends_on`
- `tests/integration/conftest.py` — removed `pika` import, `close_rabbitmq_connection` import, `rabbitmq_connection`/`rabbitmq_channel` fixtures, `get_queue_message_count`/`consume_one_message`/`purge_queue` helpers, and `reset_rabbitmq_connection` autouse fixture
- `tests/integration/test_button_handler.py` — removed `BotEventPublisher` import and `mock_publisher` fixture; updated `ButtonHandler()` call to remove publisher

---

## Phase 9: Add Missing Integration and E2E Tests

### Added

- `tests/integration/test_game_cancellation_queue.py` — Flow 2: `DELETE /api/v1/games/{id}` asserts `bot_action_queue` row with `action_type='game_cancelled'`
- `tests/integration/test_player_removed_queue.py` — Flow 3: PUT with `removed_participant_ids` asserts `bot_action_queue` row with `action_type='player_removed'`; Flow 4: removing the confirmed player from a HOST_SELECTED_WITH_WAITLIST game asserts `send_dm` promotion row
- `tests/integration/test_embed_deletion_integration.py` — Flow 9: `cancel_game(db, game, enqueue_cancellation=False)` against a real DB session asserts game deleted and no `bot_action_queue` row
- `tests/integration/test_game_updated_sse_bot.py` — Flow 10 integration: `handle_join_game` fires `pg_notify('game_updated_sse', ...)`, verified via asyncpg LISTEN
- `tests/e2e/test_game_updated_sse_e2e.py` — Flow 10 e2e: `POST /api/v1/games/{id}/join` delivers `game_updated` SSE event to a connected client

### Notes

- Fixed `httpx.Timeout` constructor usage: `httpx.Timeout(timeout=30.0, connect=10.0)` is required; `httpx.Timeout(connect=10.0, read=30.0)` raises `ValueError`
- Integration suite: 318 passed (5 new); E2E suite: 98 passed (1 new)
- `tests/integration/test_clone_game_endpoint.py` — removed `QUEUE_BOT_EVENTS` import and `rabbitmq_channel.queue_purge()` calls
- `tests/integration/test_game_signup_methods.py` — removed `QUEUE_BOT_EVENTS` import, `rabbitmq_channel` fixture params, and `queue_purge` calls
- `services/init/main.py` — removed `initialize_rabbitmq` import and call; reduced phase count from 5 to 4
- `tests/unit/services/init/test_main_roles_only.py` — removed `initialize_rabbitmq` patches from all 4 tests
- `services/init/rabbitmq.py` — deleted RabbitMQ queue initialization script

### Deleted (integration test cleanup)

- `tests/integration/test_retry_daemon_integration.py` — deleted integration tests for deleted retry daemon
- `tests/integration/test_rabbitmq_infrastructure.py` — deleted tests for removed RabbitMQ queue infrastructure
