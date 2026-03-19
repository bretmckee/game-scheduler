<!-- markdownlint-disable-file -->

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
