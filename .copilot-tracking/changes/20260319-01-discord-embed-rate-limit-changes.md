<!-- markdownlint-disable-file -->

# Changes: Discord Embed Rate Limit Redesign

## Added

- `alembic/versions/b1d2e3f4a5c6_add_message_refresh_queue.py` — Alembic migration creating the `message_refresh_queue` table, `(channel_id, enqueued_at)` index, `notify_message_refresh_queue_changed` PGFunction, and AFTER INSERT trigger that fires `pg_notify('message_refresh_queue_changed', channel_id)`.
- `shared/models/message_refresh_queue.py` — `MessageRefreshQueue` SQLAlchemy ORM model mapping the new table with `id` (UUID PK), `game_id` (FK → `game_sessions.id` CASCADE), `channel_id` (String 20), and `enqueued_at` (DateTime with timezone).
- `tests/unit/shared/models/test_message_refresh_queue.py` — Unit tests verifying model instantiation, column types, FK target and CASCADE behaviour, and table name (7 tests, all passing).

## Modified

- `shared/models/__init__.py` — Added `MessageRefreshQueue` import and export.

## Removed
