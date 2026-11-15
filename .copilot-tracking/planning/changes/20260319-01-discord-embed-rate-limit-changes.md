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

---

<!-- Merged from the former .copilot-tracking/changes/ copy of this log -->

# Changes: Discord Embed Rate Limit Redesign

## Added

- `alembic/versions/b1d2e3f4a5c6_add_message_refresh_queue.py` — Alembic migration creating the `message_refresh_queue` table, `(channel_id, enqueued_at)` index, `notify_message_refresh_queue_changed` PGFunction, and AFTER INSERT trigger that fires `pg_notify('message_refresh_queue_changed', channel_id)`.
- `shared/models/message_refresh_queue.py` — `MessageRefreshQueue` SQLAlchemy ORM model mapping the new table with `id` (UUID PK), `game_id` (FK → `game_sessions.id` CASCADE), `channel_id` (String 20), and `enqueued_at` (DateTime with timezone).
- `tests/unit/shared/models/test_message_refresh_queue.py` — Unit tests verifying model instantiation, column types, FK target and CASCADE behaviour, and table name (7 tests, all passing).

## Modified

- `shared/models/__init__.py` — Added `MessageRefreshQueue` import and export.

- `shared/cache/client.py` — Added `_CHANNEL_RATE_LIMIT_LUA` module-level Lua script constant and full `claim_channel_rate_limit_slot(channel_id)` implementation: atomic sliding-window sorted-set check using Redis `EVAL`; returns wait_ms (0 = proceed); ZADD + PEXPIRE(5001) happen inside the Lua script when the slot is claimed.
- `tests/unit/shared/cache/test_claim_channel_rate_limit_slot.py` — 10 unit tests covering: empty window returns 0, spacing n=1..4 (1000/1000/1500/1500 ms), full window returns window_wait, key scoped to channel ID, Lua script contains PEXPIRE 5001, independent channels use separate keys, return value is always int.

## Modified (continued)

- `services/bot/events/handlers.py` — Replaced `CacheKeys.message_update_throttle()` and `CacheTTL.MESSAGE_UPDATE_THROTTLE` references with inline literals (`f"message_update:{game_id}"` and `2`) to break the dependency on the now-deleted symbols. Removed unused `CacheKeys` and `CacheTTL` imports. Throttle logic itself unchanged; Phase 5 will replace it with DB insert.

## Removed

- `shared/cache/ttl.py` `CacheTTL.MESSAGE_UPDATE_THROTTLE` — obsolete 2-second throttle TTL constant.
- `shared/cache/keys.py` `CacheKeys.message_update_throttle()` — obsolete game-keyed throttle cache key function.
- `tests/unit/shared/cache/test_ttl.py` `test_message_update_throttle_ttl` — test for removed constant.
- `tests/unit/shared/cache/test_keys.py` `test_message_update_throttle_key` — test for removed key function.

---

## Phase 4: Per-Channel Worker — `_channel_worker` (TDD)

### Added

- `tests/unit/services/bot/events/test_channel_worker.py` — 11 unit tests covering: `_channel_workers` dict initialised to `{}`; worker exits and deregisters when queue empty; `claim_channel_rate_limit_slot` called with correct channel_id; worker sleeps `wait_ms/1000` seconds; delete executed after successful edit; 429 causes inner-loop retry with correct sleep and second edit attempt; non-429 error is logged without terminating worker; two games in same channel are edited sequentially with two rate-limit slot claims; burst of 4 queue entries produces sleeps `[1.0, 1.0, 1.5]` matching graduated spacing.

### Modified

- `services/bot/events/handlers.py` — Added `_channel_workers: dict[str, asyncio.Task[Any]] = {}` to `EventHandlers.__init__`; added `delete` to the top-level `sqlalchemy` import; implemented `_channel_worker(discord_channel_id)` with the corrected outer/inner loop: outer loop fetches one `game_id` via `select(MessageRefreshQueue.game_id).limit(1)`, claims a rate-limit slot, then inner loop sleeps `wait_ms/1000`, snapshots `T_cut`, fetches game state, edits the Discord message, handles 429 by setting `wait_ms = retry_after_ms` and continuing, deletes rows for `(channel_id, game_id, enqueued_at <= T_cut)` on success, and breaks; worker deregisters itself from `_channel_workers` in the `finally` block.

**Note (deviation from plan details):** The delete statement is scoped to `(channel_id, game_id, enqueued_at <= T_cut)` rather than `(channel_id, enqueued_at <= T_cut)` as written in the original research pseudocode. This corrects a design bug — channel-wide deletion would silently drop pending refreshes for other games sharing the same channel. The fix was agreed with the user during implementation.

### Added

- `services/bot/message_refresh_listener.py` — New `MessageRefreshListener` class: `__init__` stores `bot_db_url` and `spawn_worker_cb`; `start()` opens a dedicated asyncpg connection (stripping the `+asyncpg` SQLAlchemy prefix), registers `_on_notify` on the `message_refresh_queue_changed` channel, and blocks until cancelled or an error occurs (logs exception and closes connection cleanly); `_on_notify` prunes completed tasks from `_channel_workers` then calls `spawn_worker_cb(discord_channel_id)` at most once per active channel.
- `tests/unit/services/bot/test_message_refresh_listener.py` — 9 unit tests covering: `start()` calls `asyncpg.connect` with a plain `postgresql://` URL; `start()` registers the listener with the correct channel name and callback; `_on_notify` spawns a worker for a new channel; repeated notify for the same running channel does not spawn again; task stored in `_channel_workers`; connection error on `start()` is logged and returns cleanly; empty payload is ignored without raising; completed worker is removed and a new one spawned; `_channel_workers` dict is pruned and does not grow unbounded.

---

## Phase 5: Event Handler Replacement and Final Cleanup

### Modified

- `tests/unit/services/bot/events/test_handlers.py` — Removed `test_handle_game_updated_success`, `test_handle_game_updated_message_not_found`, `test_handle_game_updated_debouncing` (all test old throttle behavior); added `test_handle_game_updated_inserts_queue_row` asserting a `MessageRefreshQueue` row is inserted with correct `game_id` and `channel_id`; removed `test_set_message_refresh_throttle` from `TestRefreshGameMessageHelpers`; removed `test_stop_consuming_cancels_background_tasks`; removed `_background_tasks` teardown from `event_handlers` fixture; removed `_set_message_refresh_throttle` patches from `test_refresh_game_message_success` and `test_refresh_game_message_message_not_found`.
- `services/bot/events/handlers.py` — Replaced `_handle_game_updated` body: removed Redis TTL check and `asyncio.create_task(_delayed_refresh(...))` path; replaced with `get_db_session` context that fetches the game, inserts a `MessageRefreshQueue` row, and commits. Deleted `_delayed_refresh`, `_set_message_refresh_throttle`, `_pending_refreshes`, and `_background_tasks` from the class. Simplified `stop_consuming` to remove `_pending_refreshes.clear()` and `_background_tasks` cancellation loop. Removed `_set_message_refresh_throttle` call from `_refresh_game_message`.
- `services/bot/bot.py` — Added `import asyncio`, `from sqlalchemy import distinct, select`, and `from shared.models.message_refresh_queue import MessageRefreshQueue`; added `_recover_pending_workers()` helper that queries `SELECT DISTINCT channel_id FROM message_refresh_queue` and spawns a `_channel_worker` task for each channel with no active worker; wired `_recover_pending_workers()` into `on_ready` and `on_resumed`.
- `tests/unit/bot/events/test_handlers_game_events.py` — Updated module docstring to remove `_delayed_refresh` reference; replaced `test_handle_game_updated_redis_failure_fails_open` (tested removed Redis fail-open path) with `test_handle_game_updated_db_failure_logs_exception` (tests that a DB exception is caught and logged without re-raising); removed `test_delayed_refresh_refreshes_and_clears_pending` (tested deleted method).

---

## Phase 6: Integration Tests

### Added

- `tests/integration/test_message_refresh_queue.py` — Three integration tests: `TestMessageRefreshQueueTrigger.test_insert_notifies_correct_channel_id` (inserts via raw SQL and asserts the asyncpg LISTEN connection receives the correct `channel_id` payload); `TestMessageRefreshListenerIntegration.test_listener_receives_channel_id` (instantiates `MessageRefreshListener` against `BOT_DATABASE_URL` and asserts `spawn_cb` fires with the correct `channel_id` after an INSERT); `TestMessageRefreshQueueRecovery.test_recovery_query_returns_pending_channels` (inserts two distinct `channel_id` rows and asserts `SELECT DISTINCT channel_id` returns both).

---

## Phase 7: UPSERT Redesign for `message_refresh_queue`

### Added

- `alembic/versions/c3d4e5f6a7b8_upsert_message_refresh_queue.py` — Migration that drops the `id` UUID primary key column, adds a composite `PRIMARY KEY (channel_id, game_id)`, and recreates the trigger as `AFTER INSERT OR UPDATE` so the upsert write path always fires `pg_notify`; downgrade re-adds `id` as a generated nullable column (populated with `gen_random_uuid()`), restores the single-column PK, and restores the `AFTER INSERT`-only trigger.

### Modified

- `shared/models/message_refresh_queue.py` — Removed `id` column and `generate_uuid` import; set `primary_key=True` on both `game_id` and `channel_id` to define the composite PK; updated docstring to describe the upsert deduplication model.
- `tests/unit/shared/models/test_message_refresh_queue.py` — Removed `test_id_is_settable` and `id` from `test_instantiate_with_required_fields` and `test_column_types`; added `test_primary_key_is_composite` asserting `PRIMARY KEY (channel_id, game_id)` with no surrogate `id`.
- `tests/unit/services/bot/events/test_handlers.py` — Updated `test_handle_game_updated_inserts_queue_row` to assert `db.execute` is awaited once and no `MessageRefreshQueue` is added via `db.add` (upsert path, not bare INSERT).
- `services/bot/events/handlers.py` — Added `func` to the `sqlalchemy` import and `from sqlalchemy.dialects.postgresql import insert as pg_insert`; replaced `db.add(MessageRefreshQueue(...))` with an `pg_insert(MessageRefreshQueue).values(...).on_conflict_do_update(index_elements=["channel_id", "game_id"], set_={"enqueued_at": func.now()})` upsert executed via `db.execute(stmt)`.
- `tests/integration/test_message_refresh_queue.py` — Updated all three integration tests to use the upsert SQL form (`INSERT ... ON CONFLICT (channel_id, game_id) DO UPDATE SET enqueued_at = NOW()`) instead of bare `INSERT`; updated class and module docstrings to reference the upsert.
