<!-- markdownlint-disable-file -->

# Task Research Notes: Remove RabbitMQ

## Research Executed

### File Analysis

- `shared/messaging/infrastructure.py`
  - 3 queues: `bot_events`, `notification_queue`, `web_sse_events`
  - 3 DLQs: one per primary queue
  - Topic exchange `game_scheduler` with wildcard bindings
  - 1-hour TTL on all primary queues
- `shared/messaging/publisher.py` / `sync_publisher.py`
  - Async (`aio_pika`) and sync (`pika`) publishers
  - `PERSISTENT` delivery mode; no publisher confirms
  - Fire-and-forget publish — no acknowledgement checked
- `shared/messaging/consumer.py`
  - Single consumer per queue; no competing consumers
  - `prefetch_count=10`
  - Dynamically creates and binds queues on `connect()` — `api_embed_deletion_events` is not declared in `infrastructure.py` but is created this way
- `shared/messaging/deferred_publisher.py`
  - Events queued within SQLAlchemy session; published after commit via event listener
  - Prevents race where consumer sees event before data is visible
- `shared/messaging/events.py`
  - `EventType` enum: `GAME_CREATED`, `GAME_UPDATED`, `GAME_CANCELLED`, `PLAYER_REMOVED`, `NOTIFICATION_DUE`, `GAME_STATUS_TRANSITION_DUE`, `PARTICIPANT_DROP_DUE`, `NOTIFICATION_SEND_DM`, `EMBED_DELETED`, plus others
- `services/retry/retry_daemon.py`
  - Dedicated daemon; polls `bot_events.dlq` and `notification_queue.dlq` every 15 minutes
  - Republishes dead-lettered messages to primary queues
- `services/scheduler/generic_scheduler_daemon.py`
  - Reads schedule tables via `SELECT ... ORDER BY time ASC`
  - Publishes to RabbitMQ via `SyncEventPublisher`; marks `executed=True`; commits — atomically
  - Uses `PostgresNotificationListener` (psycopg2 + `select()`) to wake early on NOTIFY
- `services/bot/message_refresh_listener.py`
  - asyncpg `LISTEN message_refresh_queue_changed`
  - Already live — proves the DB NOTIFY pattern works in the bot
- `services/bot/announcement_loop.py`
  - asyncpg `LISTEN game_announcement_changed` (already fully DB-native — no RabbitMQ)
  - Processes deferred game announcements when `post_at` arrives
- `services/api/services/sse_bridge.py`
  - Consumes `web_sse_events` RabbitMQ queue (`game.updated.#` binding)
  - Broadcasts to active SSE connections filtered by guild membership
- `services/api/services/embed_deletion_consumer.py` _(added after original research)_
  - **Reverse-direction flow**: bot → API via RabbitMQ
  - Subscribes to `api_embed_deletion_events` queue with `embed.deleted` routing key
  - Calls `GameService._delete_game_internal` to cancel game when Discord embed is deleted
  - This queue is not in `infrastructure.py` — created dynamically by `EventConsumer`
- `services/api/services/games.py`
  - `_delete_game_internal`: releases image refs, deletes DB row, publishes `GAME_CANCELLED`
  - `_detect_and_notify_transitions` (renamed from `_notify_promoted_users`): now handles both promotions and demotions
  - `_notify_demoted_users` _(new)_: publishes `NOTIFICATION_SEND_DM` for `HOST_SELECTED_WITH_WAITLIST` demotion

### Code Search Results

- `EventPublisher` / `DeferredEventPublisher` usages in API
  - `services/api/routes/games.py`: creates `DeferredEventPublisher` per request; passes to `GameService`
  - `GameService._publish_game_created`, `_publish_game_updated`, `_publish_game_cancelled`, `_publish_player_removed`, `_detect_and_notify_transitions` — all use `publish_deferred()`
- `NOTIFICATION_SEND_DM` publisher
  - Published by API for waitlist promotions (`_notify_promoted_users`) and demotions (`_notify_demoted_users`)
  - Not self-published by bot — it is an API→bot flow like the others
- `EMBED_DELETED` publisher
  - `services/bot/events/publisher.py`: `BotEventPublisher.publish_embed_deleted()` with routing key `embed.deleted`
  - Called from `services/bot/bot.py` on `on_raw_message_delete` events
- Bot-initiated `GAME_UPDATED` publisher
  - `services/bot/events/publisher.py`: `BotEventPublisher.publish_game_updated()` with routing key `game.updated.{guild_id}`
  - Called from `services/bot/handlers/join_game.py`, `leave_game.py`, `participant_drop.py` after Discord button interactions that modify participant lists
  - Consumed by: bot `_handle_game_updated` (→ `message_refresh_queue`) AND SSE bridge
- `BotEventPublisher.publish_game_created` — defined in `services/bot/events/publisher.py` but never called from any handler; dead code deleted during migration
- `services/scheduler/services/notification_service.py` `NotificationService` — publishes `NOTIFICATION_DUE` but is never imported by any production code; dead code deleted during migration
- Existing DB NOTIFY usage
  - `notification_schedule_changed` — scheduler wake (psycopg2 sync)
  - `game_status_schedule_changed` — scheduler wake (psycopg2 sync)
  - `participant_action_schedule_changed` — scheduler wake (psycopg2 sync)
  - `message_refresh_queue_changed` — bot embed worker wake (asyncpg async)
- `GAME_CANCELLED` subtlety
  - `GameService.delete_game` deletes the game row; `message_id` and `channel_id` captured into event payload before deletion; needed by bot to delete the Discord announcement

### Project Conventions

- Typed DB table per concern (not a generic JSONB outbox) — matches `notification_schedule`, `participant_action_schedule`, `game_status_schedule`, `message_refresh_queue`
- Transactional inserts — work and queue-row insertion share one commit
- Producer writes row; consumer deletes row as part of processing transaction — crash safety by Postgres atomicity
- asyncpg `LISTEN` for async consumers (bot); psycopg2 sync `LISTEN` for sync consumers (scheduler)
- DB triggers fire `pg_notify` on INSERT — no application-level notify call needed in producers

## Key Discoveries

### RabbitMQ Features Actually Used

| Feature                           | Used | Notes                                                                                         |
| --------------------------------- | ---- | --------------------------------------------------------------------------------------------- |
| Durable persistent messages       | Yes  | Replaced by DB rows                                                                           |
| Per-queue TTL (1 hr)              | Yes  | Replaced: rows persist until processed                                                        |
| Per-message TTL                   | Yes  | Notification expiry guard — redundant; `_validate_game_for_reminder` already checks staleness |
| Dead letter queues + retry daemon | Yes  | Eliminated: unprocessed DB rows survive bot restart naturally                                 |
| Topic exchange / wildcard routing | Yes  | Replaced by separate typed tables                                                             |
| Competing consumers               | No   | Single bot instance                                                                           |
| Message priorities                | No   |                                                                                               |
| Delayed message plugin            | No   | Scheduler handles timing                                                                      |
| Publisher confirms                | No   |                                                                                               |
| Cross-technology consumers        | No   | All Python+Postgres                                                                           |

### Flow Inventory

**API → bot (action queue flows)**

1. `GAME_CREATED` — API creates game, bot posts Discord announcement
2. `GAME_CANCELLED` — API deletes game, bot deletes Discord message (captures `message_id`+`channel_id` before deletion)
3. `PLAYER_REMOVED` — API removes participant during game update, bot sends removal DM + refreshes embed
4. `NOTIFICATION_SEND_DM` — API detects waitlist promotion or demotion (`HOST_SELECTED_WITH_WAITLIST`), bot sends DM

**Scheduler → bot (schedule-driven flows)**

5. `NOTIFICATION_DUE` — scheduler reads `notification_schedule`; publishes; bot sends reminder/join/clone DM
6. `GAME_STATUS_TRANSITION_DUE` — scheduler reads `game_status_schedule`; publishes; bot transitions game status
7. `PARTICIPANT_DROP_DUE` — scheduler reads `participant_action_schedule`; publishes; bot drops participant

**API → SSE bridge (fan-out)**

8. `GAME_UPDATED` — API publishes on every state change; SSE bridge broadcasts to connected frontend clients

**Bot → bot + SSE (Discord interaction-driven updates)**

10. `GAME_UPDATED` (bot-initiated) — bot join/leave/drop handlers publish after modifying participants; bot's `_handle_game_updated` consumes to refresh embed; SSE bridge also consumes for frontend
    - Sources: `join_game.py`, `leave_game.py`, `participant_drop.py`
    - After migration: replace `publisher.publish_game_updated()` with direct `message_refresh_queue` insert + `pg_notify('game_updated_sse', ...)`

**Bot → API (reverse-direction flow — added after original research)**

9. `EMBED_DELETED` — bot detects Discord embed deletion, currently publishes to RabbitMQ, API `EmbedDeletionConsumer` cancels the game
   - Only reverse-direction flow in the system
   - After migration: bot calls shared `cancel_game()` directly; `EmbedDeletionConsumer` deleted entirely
   - The Discord message is already gone when this triggers, so no `bot_action_queue` row is needed

**Already DB-native (no change needed)**

- `message_refresh_queue` → `NOTIFY message_refresh_queue_changed` → bot embed worker

### `EMBED_DELETED` Flow Simplification

Currently: bot detects embed deletion → publishes `embed.deleted` to RabbitMQ → `EmbedDeletionConsumer` (API) calls `_delete_game_internal` → publishes `GAME_CANCELLED` → bot tries to delete Discord message (already gone).

The round-trip is unnecessary. The bot already has the game info when it detects the deletion. After migration the bot calls `cancel_game(db, game)` directly (no event publisher — no announcement row needed because the message is already gone). `EmbedDeletionConsumer` is deleted.

The shared `cancel_game` function lives in `shared/services/game_cancellation.py`:

```python
async def cancel_game(
    db: AsyncSession,
    game: GameSession,
    event_publisher: DeferredEventPublisher | None = None,
) -> None:
    """Release images, delete the game row, and optionally enqueue cancellation."""
    await release_image(db, game.thumbnail_id)
    await release_image(db, game.banner_image_id)
    await db.delete(game)
    if event_publisher is not None:
        # Writes a game_cancelled row to bot_action_queue
        event_publisher.publish_deferred(
            Event(event_type=EventType.GAME_CANCELLED, data={...})
        )
```

`GameService._delete_game_internal` becomes a thin wrapper: `cancel_game(self.db, game, self.event_publisher)`.
Bot embed deletion handler calls `cancel_game(db, game)` — no publisher argument.

### `GAME_UPDATED` Intermediate Hop

Currently two separate paths both publish `GAME_UPDATED`:

**API-initiated path**: API → RabbitMQ `GAME_UPDATED` → bot `_handle_game_updated` → inserts into `message_refresh_queue`; also → SSE bridge.
The RabbitMQ leg is redundant. API can write directly to `message_refresh_queue` within its transaction. For SSE: `GameService._publish_game_updated` sends `pg_notify('game_updated_sse', ...)`.

**Bot-initiated path**: join/leave/drop handlers → `BotEventPublisher.publish_game_updated()` → RabbitMQ → same two consumers.
Replacement: handlers insert directly into `message_refresh_queue` and send `pg_notify('game_updated_sse', ...)`.
After migration `BotEventPublisher.publish_game_updated` is deleted.

### SSE Fan-out Pattern

With PG NOTIFY, all `LISTEN` connections on a channel receive the notification.
Multiple API replicas each broadcast to their own connected SSE clients — correct fan-out behaviour.
Clients that lose SSE connection during a replica crash must reconnect (standard SSE client behaviour)
and re-fetch current state via REST — no data loss.

### Crash Safety

Transactional delete pattern (worker deletes row within same transaction as processing work)
means an unprocessed row simply reappears on bot restart. No separate reaper or `claimed_at` needed.
This is identical to the existing scheduler daemon pattern.

## Recommended Approach

Replace all RabbitMQ flows with DB tables + PostgreSQL LISTEN/NOTIFY.

### New table: `bot_action_queue`

Typed columns per action type — no JSONB payload. One row per pending bot action.

```sql
CREATE TABLE bot_action_queue (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type TEXT NOT NULL,   -- 'game_created', 'game_cancelled', 'player_removed',
                                 -- 'send_dm', 'notification_due', 'status_transition_due',
                                 -- 'participant_drop_due'
    game_id     TEXT,
    channel_id  TEXT,
    message_id  TEXT,
    user_id     TEXT,
    discord_id  TEXT,
    payload     JSONB,           -- small typed-per-action overflow only
    enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_bot_action_queue_enqueued ON bot_action_queue (enqueued_at ASC);
```

A DB trigger fires `pg_notify('bot_action_queue_changed', '')` on INSERT.

The bot adds `LISTEN bot_action_queue_changed` alongside its existing
`message_refresh_queue_changed` listener in `MessageRefreshListener` (or a parallel listener).

Processing loop: `SELECT ... ORDER BY enqueued_at ASC FOR UPDATE SKIP LOCKED LIMIT 1`,
process, DELETE — all within one transaction.

### Flow-by-flow replacement

**Flows 1–4 (API → bot)**

`GameService` methods replace `publish_deferred()` calls with:

```python
await db.execute(
    insert(BotActionQueue).values(action_type="game_created", game_id=game.id, channel_id=...)
)
# No separate commit needed — already within the API transaction
```

The `DeferredEventPublisher` and `EventPublisher` are removed from `GameService`.
The `GAME_UPDATED` → `message_refresh_queue` write moves directly into `GameService._publish_game_updated`.

**Flows 5–7 (scheduler → bot)**

`SchedulerDaemon._process_item` replaces `self.publisher.publish(event)` with:

```python
db.execute(insert(BotActionQueue).values(action_type=..., game_id=..., ...))
db.commit()  # atomic: marks item processed + enqueues bot action
```

`SyncEventPublisher` removed from scheduler. `rabbitmq_url` config removed.

**Flow 8 (SSE fan-out)**

`GameService._publish_game_updated` adds:

```python
await db.execute(text(
    "SELECT pg_notify('game_updated_sse', :payload)"
).bindparams(payload=json.dumps({"game_id": game.id, "guild_id": game.guild_id})))
```

`SSEGameUpdateBridge` replaces its `EventConsumer` with an asyncpg `LISTEN game_updated_sse` connection,
mirroring `MessageRefreshListener`.

### Services removed

- `services/retry/` — entire service; Docker container removed
- `services/api/services/embed_deletion_consumer.py` — deleted; bot handles cancellation directly
- `shared/messaging/publisher.py`, `sync_publisher.py`, `consumer.py`, `deferred_publisher.py`, `config.py`, `infrastructure.py` — all removed after migration
- `rabbitmq` container from all compose files
- `opentelemetry-instrumentation-aio-pika` dependency removed
- `aio-pika`, `pika` dependencies removed
- `RABBITMQ_URL`, `RABBITMQ_HOST`, `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` env vars removed

### `GAME_CANCELLED` special case

Insert into `bot_action_queue` with `message_id` and `channel_id` captured **before** `db.delete(game)`,
within the same transaction. Bot reads these from the queue row — game row is already gone.

## Implementation Guidance

- **Objectives**: Remove RabbitMQ container and all AMQP dependencies; preserve identical bot behaviour
- **Key Tasks**:
  1. Add `BotActionQueue` model + Alembic migration (table + trigger + NOTIFY)
  2. Add `shared/services/game_cancellation.py` with `cancel_game(db, game, event_publisher=None)`
  3. Replace `GameService._delete_game_internal` with thin wrapper calling `cancel_game`
  4. Update bot embed deletion handler (`services/bot/bot.py`) to call `cancel_game(db, game)` directly; delete `EmbedDeletionConsumer`
  5. Add bot LISTEN loop for `bot_action_queue_changed` (extend `MessageRefreshListener` or add sibling)
  6. Replace `GameService` `publish_deferred` calls with `BotActionQueue` inserts (flows 1–4)
  7. Replace `_publish_game_updated` with direct `message_refresh_queue` insert
  8. Replace bot join/leave/drop handlers: replace `publisher.publish_game_updated()` with direct `message_refresh_queue` insert + `pg_notify('game_updated_sse', ...)`
  9. Replace `SSEGameUpdateBridge` RabbitMQ consumer with asyncpg LISTEN (flow 8)
  10. Remove `services/retry/` service
  11. Remove `shared/messaging/` module (includes dead `NotificationService` and `BotEventPublisher.publish_game_created`)
  12. Remove RabbitMQ from all compose files and config
  13. Remove `aio-pika`, `pika` dependencies; remove OTel aio-pika instrumentation
- **Dependencies**: Migration must be deployed before any code changes that write to the new table
- **Success Criteria**:
  - All existing integration and e2e tests pass without RabbitMQ container running
  - `rabbitmq` service absent from `compose.yaml`
  - `shared/messaging/` directory deleted
  - `services/retry/` directory deleted
  - `services/api/services/embed_deletion_consumer.py` deleted
  - `shared/services/game_cancellation.py` exists and is used by both API and bot

---

## Addendum: Test Coverage Analysis (2026-07-05)

Post-migration analysis of which flows have integration and e2e test coverage,
and which tests remain to be added.

### Coverage by Flow

| Flow                                              | Integration                                                                                                                                   | E2E                                                                                                  |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 1 `GAME_CREATED`                                  | ✅ `test_game_signup_methods` — asserts `bot_action_queue` row `game_created`; `test_clone_game_endpoint`, `test_recurrence_clone` also cover | ✅ `test_game_announcement`; precondition in most other tests                                        |
| 2 `GAME_CANCELLED`                                | ❌                                                                                                                                            | ✅ `test_game_cancellation`                                                                          |
| 3 `PLAYER_REMOVED`                                | ❌                                                                                                                                            | ✅ `test_player_removal`                                                                             |
| 4 `NOTIFICATION_SEND_DM`                          | ❌                                                                                                                                            | ✅ `test_waitlist_promotion` (promotion); `test_host_added_dropout_notification` (demotion)          |
| 5 `NOTIFICATION_DUE`                              | ✅ `test_notification_daemon` — `bot_action_queue` row `notification_due`; `test_clone_confirmation_notification`                             | ✅ `test_game_reminder`; `test_join_notification`                                                    |
| 6 `GAME_STATUS_TRANSITION_DUE`                    | ✅ `test_status_transitions` — `bot_action_queue` row `status_transition_due`                                                                 | ✅ `test_game_status_transitions`                                                                    |
| 7 `PARTICIPANT_DROP_DUE`                          | ✅ `test_participant_action_daemon` — `bot_action_queue` row `participant_drop_due`; `test_participant_drop_event`                            | ✅ `test_clone_game_e2e`                                                                             |
| 8 `GAME_UPDATED` (API→SSE)                        | ✅ `test_sse_bridge_integration` — mock producer sends `pg_notify('game_updated_sse', ...)`; verifies SSE delivery and guild filtering        | ⚠️ Side-effect only in `test_game_update`, `test_user_join` (Discord embed verified, not SSE stream) |
| 9 `EMBED_DELETED`                                 | ❌ (unit tests exist: `test_bot.py` mocks `cancel_game`; `test_game_cancellation.py` mocks DB — but no real-DB integration test)              | ✅ `test_embed_deletion` — real-time `on_message_delete` and sweep paths                             |
| 10 `GAME_UPDATED` (bot-initiated join/leave/drop) | ⚠️ `test_join_game`, `test_leave_game` verify `message_refresh_queue` insert but not `pg_notify('game_updated_sse', ...)`                     | ❌ No dedicated test for SSE delivery from bot handler path                                          |

### Missing Tests and Effort Estimates

All missing integration tests follow the same pattern established in
`test_game_signup_methods.py` and `test_participant_drop_event.py`.
All missing e2e SSE work reuses patterns from `test_sse_bridge_integration.py`
and the `authenticated_admin_client` fixture (already `httpx.AsyncClient`).

**Flow 2 (`GAME_CANCELLED`) — integration — Easy**

`DELETE /api/v1/games/{id}` via `create_authenticated_client` → assert
`bot_action_queue` has row with `action_type = 'game_cancelled'` and correct `game_id`.
Identical structure to the GAME_CREATED test, different HTTP verb.

**Flow 3 (`PLAYER_REMOVED`) — integration — Easy–Moderate**

`POST /api/v1/games`, insert participant directly via `admin_db_sync`,
`PUT /api/v1/games/{id}` with `removed_participant_ids` → assert
`bot_action_queue` row with `action_type = 'player_removed'`.

**Flow 4 (`NOTIFICATION_SEND_DM`) — integration — Moderate**

Requires a full-game + waitlist game state to trigger `_detect_and_notify_transitions`:
create game at `max_players=1`, add one confirmed participant plus one waitlist participant,
then remove the confirmed participant to trigger promotion. Same `bot_action_queue` assertion.

**Flow 9 (`EMBED_DELETED`) — integration — Easy**

Call `cancel_game(db, game, enqueue_cancellation=False)` directly against a real DB session
(same direct-handler pattern as `test_participant_drop_event.py`) → assert game row deleted.
No `bot_action_queue` row expected (`enqueue_cancellation=False`).

**Flow 10 SSE delivery — integration or e2e — Moderate**

Two complementary approaches:

- _Integration_: extend `test_join_game.py` or add a sibling test that calls `handle_join_game`
  then opens a `pg_notify` listener (asyncpg) and verifies the notify fires. Reuses
  `test_sse_bridge_integration.py` producer/consumer machinery.

- _E2E_: open `authenticated_admin_client.stream("GET", "/api/v1/sse/game-updates")` in a
  background task, POST `/api/v1/games/{id}/join`, assert `game_updated` event received.
  API join and Discord-button join both call the same underlying `pg_notify` — testing via
  API is sufficient. Main complexity is the async orchestration (`asyncio.create_task` +
  `asyncio.wait`) already demonstrated in `test_sse_bridge_integration.py`.
  The `timeout=10.0` on `authenticated_admin_client` must be overridden for the stream call
  (pass `timeout=httpx.Timeout(connect=10.0, read=30.0)` to `stream()`).

### Notes

- Flows 2, 3, 4 lack integration tests because they were API-triggered flows with no scheduler
  daemon to test in isolation; the bot processing side was only verifiable e2e.
  With `bot_action_queue` the producer side is now trivially checkable in integration.
- Flow 9 has adequate unit coverage but no real-DB integration coverage.
- Flow 8 SSE is tested integration-only with a mock producer; no e2e test verifies that a real
  API action actually delivers an SSE event to a connected client.
- Flow 10 SSE is the only flow where both integration and e2e gaps exist simultaneously.
