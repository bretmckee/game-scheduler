<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Embed Rate Limit Redesign

## Research Executed

### File Analysis

- `services/bot/events/handlers.py`
  - `_handle_game_updated`: checks Redis key `message_update:{game_id}`, fires immediately or schedules `_delayed_refresh` sleeping flat 2s
  - `_delayed_refresh`: `asyncio.create_task` + `asyncio.sleep(delay)` — independent coroutine, does not block event loop
  - `_set_message_refresh_throttle`: sets Redis key with 2s TTL after each successful edit
  - `_pending_refreshes`: in-memory set, lost on crash
  - `_background_tasks`: in-memory set of asyncio Tasks, lost on crash
- `shared/cache/ttl.py`
  - `MESSAGE_UPDATE_THROTTLE = 2` — flat 2s throttle window
- `shared/cache/keys.py`
  - `message_update_throttle(game_id)` → `message_update:{game_id}` — keyed per game, not per channel
- `shared/models/game.py`
  - `GameSession` has `updated_at`, `channel_id` (FK to `channel_configurations.id`), `message_id`
  - No `message_synced_at` field
- `shared/models/participant.py`
  - `GameParticipant` has `joined_at` but no deletion timestamp — leaves are row deletes
- `shared/models/channel.py`
  - `ChannelConfiguration.games` is a list — multiple games can share a channel
  - `channel_id` is the Discord snowflake (String(20))
- `shared/models/notification_schedule.py`
  - Established pattern: DB-backed queue, `sent` boolean, `notification_time`, processed by scheduler daemon
- `shared/database.py`
  - `BOT_DATABASE_URL` exists — dedicated asyncpg connection URL for the bot
  - `asyncpg~=0.30.0` in `pyproject.toml`
- `alembic/versions/c2135ff3d5cd_initial_schema.py`
  - Established pattern: `PGFunction` + `pg_notify` + `CREATE TRIGGER` for event-driven wake-up
  - `notification_schedule_trigger` and `game_status_schedule_trigger` demonstrate the pattern
- `services/bot/bot.py`
  - `on_ready`: starts RabbitMQ consumer task via `self.loop.create_task`
  - `on_resumed`: reconnect handler exists but does nothing beyond logging
  - No startup scan for pending work

### Code Search Results

- `publish_game_updated`
  - Called from `join_game.py`, `leave_game.py`, `participant_drop.py`, `services/api/services/games.py`
  - One event per user action — no batching at publish time
- `asyncpg LISTEN`
  - No existing async LISTEN usage in codebase — scheduler uses `psycopg2 + select()` synchronously
  - `asyncpg` native: `await conn.add_listener('channel', callback)` — callback runs on event loop

### External Research

- #fetch:https://docs.discord.com/developers/topics/rate-limits
  - Rate limit bucket is keyed on **`channel_id`** (top-level resource in path)
  - `PATCH /channels/{channel_id}/messages/{message_id}` shares bucket with all edits in that channel
  - Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset-After`, `X-RateLimit-Bucket`
  - Per-route limit for message edits: **5 requests per 5 seconds per channel**
  - `X-RateLimit-Scope: shared` — 429s with this scope do NOT count against Cloudflare invalid-request limit

## Key Discoveries

### Current Design Problems

1. **Wrong throttle scope**: keyed per-game (`message_update:{game_id}`), but Discord's bucket is per-channel. Multiple games in the same channel each believe they have a free quota when they share one bucket.
2. **Wrong sleep duration in trailing refresh**: `_delayed_refresh` sleeps a full `MESSAGE_UPDATE_THROTTLE` (2s) even when the key may be about to expire, producing up to ~4s total delay.
3. **Starvation**: second concurrent game for the same channel is permanently dropped if a task is already pending (`game_id in self._pending_refreshes` → skip).
4. **Crash recovery**: `_pending_refreshes` and `_background_tasks` are in-memory only. Any update pending during a crash is lost.
5. **No idle-then-first-join delay from throttle code**: the initial delay felt by users is pipeline latency (Discord → bot → RabbitMQ → bot → DB → Discord API), not the throttle logic.

### Project Conventions

- DB-backed queues with `pg_notify` triggers are the established pattern for durable, event-driven scheduling
- `PGFunction` + `op.create_entity` + `op.execute(CREATE TRIGGER)` is the migration pattern
- `asyncpg` is available and already the bot's DB driver; `BOT_DATABASE_URL` is its dedicated connection URL
- `asyncio.create_task` is used freely for background work in the bot

### Rate Limit Sorted Set Pattern

Redis sorted set with `ZADD` (score = ms timestamp) + `ZREMRANGEBYSCORE` + `ZCARD` enables atomic sliding-window rate limit tracking. The set key is `channel_rate_limit:{discord_channel_id}`, TTL = 5001ms (auto-expires after 5s inactivity). A Lua script executes the check atomically.

### Graduated Spacing Schedule

Spacing `[0, 1, 1, 1.5, 1.5]` seconds between consecutive edits (indexed by count of recent edits in the 5s window):

| Edit # (in 5s window) | Min wait since previous edit                         |
| --------------------- | ---------------------------------------------------- |
| 1st (n=0)             | 0s (immediate)                                       |
| 2nd (n=1)             | 1s                                                   |
| 3rd (n=2)             | 1s                                                   |
| 4th (n=3)             | 1.5s                                                 |
| 5th+ (n≥4)            | 1.5s (sustained rate: 0.67 edits/s < 1 edit/s limit) |

Cumulative spacing: 0, 1, 2, 3.5, 5s.

The spacing table is a user-experience optimization, not a correctness requirement. If a 429 is received (e.g. at the 5s boundary due to scheduling jitter), the per-channel worker sleeps `retry_after` seconds from the Discord response and retries — no state is lost, no other context is blocked. The 429 is a self-healing signal, not an error.

**Maximum user wait after joining into an active burst: 1.5 seconds.**
After idle: 0s (immediate).

## Recommended Approach

### Architecture: DB Queue + Per-Channel asyncio Workers + Redis Rate Limit Tracking

#### New DB Table: `message_refresh_queue`

```sql
CREATE TABLE message_refresh_queue (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id     VARCHAR(36) NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    channel_id  VARCHAR(20) NOT NULL,   -- Discord channel snowflake (denormalized)
    enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ON message_refresh_queue (channel_id, enqueued_at);
```

No uniqueness constraint on `game_id` — all inserts succeed. Deduplication happens implicitly: the worker deletes all rows for a channel up to `T_cut`, collapsing any burst into one Discord call.

#### Postgres Trigger

`AFTER INSERT ON message_refresh_queue FOR EACH ROW` → `pg_notify('message_refresh_queue_changed', NEW.channel_id)`.

The NOTIFY payload carries `channel_id` so the listener knows which channel to wake — no channel fan-out needed.

#### Insert Path (replaces `_handle_game_updated` throttle logic)

`game.updated` event arrives → insert one row into `message_refresh_queue` → return. The trigger fires the NOTIFY. No Redis check, no sleep, no in-memory state.

#### asyncpg LISTEN Listener (new component in bot)

Dedicated `asyncpg` connection (not from SQLAlchemy pool), using `BOT_DATABASE_URL`. On connect: `await conn.add_listener('message_refresh_queue_changed', _on_notify)`.

`_on_notify(conn, pid, channel, payload)`:

- `discord_channel_id = payload`
- If `discord_channel_id` not in `_channel_workers` → spawn `asyncio.create_task(_channel_worker(discord_channel_id))`
- If already in `_channel_workers` → no-op (worker will find the new row on its next loop)

#### Per-Channel Worker (`_channel_worker(discord_channel_id)`)

```
register self in _channel_workers
loop:
    check Redis sorted set for discord_channel_id
    compute wait = max(spacing_wait, window_wait, 0)
        spacing_wait = last_edit_ts + SPACING[min(n, 4)] - now_ms
        window_wait  = oldest_edit_ts + 5000 - now_ms  (only when n >= 5)
    if wait > 0:
        await asyncio.sleep(wait / 1000)

    T_cut = now()
    query DB: fetch one row for this channel (just to confirm work exists)
    if no rows: break → exit

    fetch current game state from DB (reflects ALL joins since last edit)
    result = do Discord message.edit(...)
    if result is 429:
        sleep retry_after seconds (from response body or X-RateLimit-Reset-After header)
        continue loop (row still in DB, will retry)
    record timestamp in Redis sorted set (ZADD channel_rate_limit:{id} ts ts)
    PEXPIRE key 5000ms

    DELETE FROM message_refresh_queue
      WHERE channel_id = discord_channel_id AND enqueued_at <= T_cut

deregister self from _channel_workers
```

No transaction held during Discord call or sleep. Crash at any point → rows survive in DB → on restart, startup scan (see below) re-triggers workers.

#### Startup Recovery

In `on_ready` (and `on_resumed`): query `SELECT DISTINCT channel_id FROM message_refresh_queue` → for each result, if no worker exists, spawn one. This replaces lost in-memory state after a crash.

#### Redis Key

`channel_rate_limit:{discord_channel_id}` — sorted set, score = member = Unix timestamp in ms. TTL = 5001ms, refreshed on each ZADD. Disappears automatically after 5s of inactivity.

### What Is Removed

- `MESSAGE_UPDATE_THROTTLE` TTL constant
- `message_update_throttle(game_id)` cache key
- `_set_message_refresh_throttle` method
- `_pending_refreshes` set
- `_delayed_refresh` method
- Binary exists-check Redis logic in `_handle_game_updated`

## Implementation Guidance

- **Objectives**: Replace fragile in-memory throttle with durable DB queue + per-channel workers with correct per-channel rate limit accounting and graduated spacing
- **Key Tasks**:
  1. Alembic migration: create `message_refresh_queue` table + `pg_notify` trigger function
  2. Add `claim_channel_rate_limit_slot(channel_id)` Lua script method to `RedisClient` — returns `wait_ms` (0 = proceed, >0 = sleep this long)
  3. Add `message_refresh_queue` SQLAlchemy model
  4. Add asyncpg LISTEN listener to bot startup (new `MessageRefreshListener` class in `services/bot/`)
  5. Add `_channel_worker` coroutine and `_channel_workers` dict to `EventHandlers`
  6. Replace `_handle_game_updated` throttle logic with DB insert
  7. Add startup recovery query in `on_ready` / `on_resumed`
  8. Update/replace unit tests for `_handle_game_updated`, `_set_message_refresh_throttle`, `_delayed_refresh`
  9. Update `shared/cache/keys.py` and `shared/cache/ttl.py` to remove obsolete constants
- **Dependencies**:
  - `asyncpg~=0.30.0` (already in `pyproject.toml`)
  - `BOT_DATABASE_URL` env var (already exists)
  - Redis sorted set support (already in redis-py/aioredis via `_client.zadd`, `_client.zremrangebyscore`, `_client.zcard`)
  - `alembic-utils` `PGFunction` (already used in initial schema migration)
- **Success Criteria**:
  - First join after idle: Discord message updates with no artificial delay (only pipeline latency)
  - Burst of N joins on same game: updates fire at 0, 1, 2, 3.5, 5s intervals (max 1.5s per user)
  - Multiple games in same channel: correctly share the per-channel bucket
  - Bot crash mid-burst: all pending updates survive and are processed after restart
  - System idle: no background tasks, no Redis keys, no DB rows
  - No 429 responses from Discord under normal operation

---

## Addendum: Integration Tests

### Context

The bot container is excluded from the integration environment (it requires a real Discord token), so
integration tests call handlers and components directly against a real DB + RabbitMQ. See
`tests/integration/test_participant_drop_event.py` and `test_notification_daemon.py` for the
established patterns.

### Three Integration Tests Worth Adding

#### 1. Queue trigger fires the correct `pg_notify` payload

Model: `tests/integration/test_notification_daemon.py` — `PostgresNotificationListener` + real DB,
no Discord.

- Insert a row into `message_refresh_queue` with a known `channel_id`
- Assert the asyncpg/psycopg2 LISTEN connection receives
  `pg_notify('message_refresh_queue_changed', '<channel_id>')`
- Guards correctness of the Alembic migration trigger function

#### 2. asyncpg LISTEN receives the `channel_id` payload

Model: `test_listener_subscribes_to_channel` in `test_notification_daemon.py`.

- Instantiate `MessageRefreshListener` against `BOT_DATABASE_URL`
- Insert a row via admin connection
- Assert the listener's callback receives the correct `channel_id` as payload
- Guards the listener's `add_listener` wiring and callback parsing

#### 3. Startup recovery query returns pending channels

Simplest test — pure SQL, no async listener needed.

- Insert rows for two distinct `channel_id`s into `message_refresh_queue`
- Run `SELECT DISTINCT channel_id FROM message_refresh_queue`
- Assert both channel IDs are returned
- Guards the on_ready recovery query that prevents work loss after crash

### What to Skip

- Rate limit boundary behavior at integration level — Redis sorted set behavior is covered by unit
  tests and does not need a full Docker environment
- A second end-to-end "single join → message updated" test — already covered by `test_game_update.py`
