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
- `shared/messaging/deferred_publisher.py`
  - Events queued within SQLAlchemy session; published after commit via event listener
  - Prevents race where consumer sees event before data is visible
- `shared/messaging/events.py`
  - `EventType` enum: `GAME_CREATED`, `GAME_UPDATED`, `GAME_CANCELLED`, `PLAYER_REMOVED`, `NOTIFICATION_DUE`, `GAME_STATUS_TRANSITION_DUE`, `PARTICIPANT_DROP_DUE`, `NOTIFICATION_SEND_DM`, plus others
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
- `services/api/services/sse_bridge.py`
  - Consumes `web_sse_events` RabbitMQ queue (`game.updated.#` binding)
  - Broadcasts to active SSE connections filtered by guild membership

### Code Search Results

- `EventPublisher` / `DeferredEventPublisher` usages in API
  - `services/api/routes/games.py`: creates `DeferredEventPublisher` per request; passes to `GameService`
  - `GameService._publish_game_created`, `_publish_game_updated`, `_publish_game_cancelled`, `_publish_player_removed`, `_notify_promoted_users` — all use `publish_deferred()`
- `NOTIFICATION_SEND_DM` publisher
  - `services/api/services/games.py` line 2212: published by API for waitlist promotions
  - Not self-published by bot — it is an API→bot flow like the others
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
4. `NOTIFICATION_SEND_DM` — API detects waitlist promotion, bot sends promotion DM

**Scheduler → bot (schedule-driven flows)**

5. `NOTIFICATION_DUE` — scheduler reads `notification_schedule`; publishes; bot sends reminder/join/clone DM
6. `GAME_STATUS_TRANSITION_DUE` — scheduler reads `game_status_schedule`; publishes; bot transitions game status
7. `PARTICIPANT_DROP_DUE` — scheduler reads `participant_action_schedule`; publishes; bot drops participant

**API → SSE bridge (fan-out)**

8. `GAME_UPDATED` — API publishes on every state change; SSE bridge broadcasts to connected frontend clients

**Already DB-native (no change needed)**

- `message_refresh_queue` → `NOTIFY message_refresh_queue_changed` → bot embed worker

### `GAME_UPDATED` Intermediate Hop

Currently: API → RabbitMQ `GAME_UPDATED` → bot handler → inserts into `message_refresh_queue`.
The RabbitMQ leg is redundant. API can write directly to `message_refresh_queue` within its transaction.
The NOTIFY trigger on `message_refresh_queue` already handles bot wake-up.

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
  2. Add bot LISTEN loop for `bot_action_queue_changed` (extend `MessageRefreshListener` or add sibling)
  3. Replace `GameService` `publish_deferred` calls with `BotActionQueue` inserts (flows 1–4)
  4. Replace `_publish_game_updated` with direct `message_refresh_queue` insert
  5. Replace `SchedulerDaemon` RabbitMQ publish with `BotActionQueue` insert (flows 5–7)
  6. Replace `SSEGameUpdateBridge` RabbitMQ consumer with asyncpg LISTEN (flow 8)
  7. Remove `services/retry/` service
  8. Remove `shared/messaging/` module
  9. Remove RabbitMQ from all compose files and config
  10. Remove `aio-pika`, `pika` dependencies; remove OTel aio-pika instrumentation
- **Dependencies**: Migration must be deployed before any code changes that write to the new table
- **Success Criteria**:
  - All existing integration and e2e tests pass without RabbitMQ container running
  - `rabbitmq` service absent from `compose.yaml`
  - `shared/messaging/` directory deleted
  - `services/retry/` directory deleted
