# Changes: Discord Embed Rate Limit Redesign

## Phase 1: Database Foundation

### Task 1.1: Alembic migration

- Created `alembic/versions/b1d2e3f4a5c6_add_message_refresh_queue.py`
- Added `message_refresh_queue` table with `id`, `game_id` (FK → `game_sessions`, CASCADE),
  `channel_id`, `enqueued_at` columns
- Added composite index on `(channel_id, enqueued_at)`
- Added `notify_message_refresh_queue_changed()` PGFunction trigger that calls
  `pg_notify('message_refresh_queue_changed', NEW.channel_id::text)` on INSERT

### Task 1.2: ORM model

- Created `shared/models/message_refresh_queue.py` — `MessageRefreshQueue` SQLAlchemy model
- Created `tests/unit/shared/models/test_message_refresh_queue.py` — unit tests

## Phase 2: Redis Rate Limit Tracking

### Task 2.1–2.3: `claim_channel_rate_limit_slot`

- Added `claim_channel_rate_limit_slot(channel_id, window_ms, max_slots)` to
  `shared/cache/client.py` using inline Lua script
- Implements atomic ZADD/ZREMRANGEBYSCORE/ZCARD/PEXPIRE pattern
- Returns `(allowed: bool, retry_after_ms: int)` tuple
- Added unit tests in `tests/unit/shared/cache/test_redis_client.py`

### Task 2.4: Cleanup

- Removed `MESSAGE_UPDATE_THROTTLE` from `shared/cache/ttl.py`
- Removed `message_update_throttle` from `shared/cache/keys.py`
- Added edge-case tests for `claim_channel_rate_limit_slot`

## Phase 3: asyncpg LISTEN Listener

### Task 3.1–3.3: `MessageRefreshListener`

- Created `services/bot/message_refresh_listener.py` — `MessageRefreshListener` class
- Opens dedicated asyncpg connection, calls `add_listener("message_refresh_queue_changed", ...)`
- `_on_notify` spawns per-channel worker via `spawn_worker_cb(channel_id)`, deduplicates
  running workers by channel
- Added unit tests in `tests/unit/services/bot/test_message_refresh_listener.py`

### Task 3.4: Refactor + edge cases

- Added edge-case unit tests: empty payload, duplicate notify while worker running,
  exception in spawn_cb

## Phase 4: Per-Channel Worker

### Task 4.1–4.3: `_channel_worker`

- Added `_channel_worker(channel_id)` to `services/bot/events/handlers.py`
- Worker loop: claim rate-limit slot → fetch oldest pending row → update Discord embed →
  delete row; stops when no rows remain or worker cancelled
- Uses `claim_channel_rate_limit_slot` (5 slots / 5000 ms window)
- Added unit tests in `tests/unit/services/bot/events/test_handlers.py`

### Task 4.4: Refactor + multi-game edge cases

- Added edge-case tests: multiple games in same channel serialized, rate-limit backoff applied

## Phase 5: Event Handler Replacement and Final Cleanup

### Task 5.1–5.2: `_handle_game_updated` replacement

- Replaced throttle logic in `_handle_game_updated` with DB INSERT into
  `message_refresh_queue`
- Added `_recover_pending_workers` to `services/bot/bot.py`, called from `on_ready`
  and `on_resumed`

### Task 5.3: Obsolete method deletion

- Removed `_delayed_refresh`, `_set_message_refresh_throttle` from
  `services/bot/events/handlers.py`
- Removed all references to old throttle keys and TTL constants

## Phase 6: Integration Tests

### Task 6.1: Queue trigger integration test

- Added `TestMessageRefreshQueueTrigger` in
  `tests/integration/test_message_refresh_queue.py`
- Asserts INSERT on `message_refresh_queue` fires `pg_notify` with correct `channel_id`

### Task 6.2: Listener integration test

- Added `TestMessageRefreshListenerIntegration` in
  `tests/integration/test_message_refresh_queue.py`
- Verifies `MessageRefreshListener` receives correct `channel_id` via asyncpg

### Task 6.3: Recovery query integration test

- Added `TestMessageRefreshQueueRecovery` in
  `tests/integration/test_message_refresh_queue.py`
- Verifies `SELECT DISTINCT channel_id FROM message_refresh_queue` returns all
  pending channels (guards the `on_ready` recovery query)
