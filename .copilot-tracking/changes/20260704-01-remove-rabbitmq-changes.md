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

## Phase 8: Remove Dead Messaging Infrastructure

### Removed

---

## Phase 9: Docker, Config, and Dependency Cleanup

### Modified

### Removed
