---
applyTo: '.copilot-tracking/changes/20260704-01-remove-rabbitmq-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove RabbitMQ

## Overview

Replace all RabbitMQ message flows with PostgreSQL LISTEN/NOTIFY + a new `bot_action_queue` table, then remove all AMQP infrastructure, the retry service, and AMQP dependencies.

## Objectives

- Eliminate the `rabbitmq` container and all `aio-pika`/`pika` Python dependencies
- Replace every RabbitMQ flow with a DB-native equivalent (new `bot_action_queue` table + `pg_notify`)
- Preserve identical bot behaviour and all integration/e2e test outcomes
- Remove `services/retry/`, `shared/messaging/`, and `services/api/services/embed_deletion_consumer.py`
- Introduce `shared/services/game_cancellation.py` used by both API and bot

## Research Summary

### Project Files

- `shared/messaging/` — AMQP publisher/consumer/config infrastructure being removed
- `shared/models/` — SQLAlchemy model conventions; new `bot_action_queue.py` added here
- `services/api/services/games.py` — `GameService` publisher calls migrated to BotActionQueue inserts
- `services/api/services/sse_bridge.py` — RabbitMQ consumer replaced with asyncpg LISTEN
- `services/api/services/embed_deletion_consumer.py` — deleted; bot handles directly
- `services/bot/message_refresh_listener.py` — reference pattern for asyncpg LISTEN consumers
- `services/bot/bot.py` — `on_raw_message_delete` migrated; new listener registered
- `services/scheduler/generic_scheduler_daemon.py` — publisher replaced with BotActionQueue inserts
- `compose.yaml` et al. — `rabbitmq` and `retry` services removed in Phase 9

### External References

- #file:../research/20260408-02-remove-rabbitmq-research.md — complete flow inventory, DDL spec, implementation guidance

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python coding conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD RED/GREEN/REFACTOR workflow
- #file:../../.github/instructions/unit-tests.instructions.md — unit test quality standards
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md — transaction patterns
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md — Docker cleanup

## Implementation Checklist

### [x] Phase 1: Add `BotActionQueue` Model + Alembic Migration

- [x] Task 1.1: Write xfail TDD tests for `BotActionQueue` model attributes and constraints (RED)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 13-28)

- [x] Task 1.2: Implement SQLAlchemy model, export from `shared/models/__init__.py`, create Alembic migration with table + index + INSERT trigger + NOTIFY (GREEN)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 29-46)

### [x] Phase 2: Add `cancel_game` Service + Update `GameService._delete_game_internal`

- [x] Task 2.1: Write xfail TDD tests for `cancel_game(db, game, event_publisher=None)` in `shared/services/game_cancellation.py` (RED)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 49-63)

- [x] Task 2.2: Implement `cancel_game`; update `GameService._delete_game_internal` as thin wrapper; update tests (GREEN)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 64-82)

### [x] Phase 3: Migrate API to Bot Flows (Flows 1-4) + SSE NOTIFY

- [x] Task 3.1: Write xfail TDD tests for all updated `GameService` publish methods using `BotActionQueue` inserts and `pg_notify` (RED)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 85-99)

- [x] Task 3.2: Remove `DeferredEventPublisher` from `GameService`; replace all `publish_deferred()` calls; update API route; update all tests (GREEN)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 100-118)

### [x] Phase 4: Replace SSE Bridge Consumer (Flow 8)

- [x] Task 4.1: Write xfail tests then migrate `SSEGameUpdateBridge` from `EventConsumer` to asyncpg `LISTEN game_updated_sse`; remove `shared/messaging/` imports (TDD)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 121-138)

### [ ] Phase 5: Bot Embed Deletion Handler + Bot Action Queue Consumer

- [ ] Task 5.1: Write xfail tests then implement `BotActionListener` with asyncpg `LISTEN bot_action_queue_changed` and transactional row dispatch; register on bot startup (TDD)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 142-158)

- [ ] Task 5.2: Write xfail tests then migrate `on_raw_message_delete` to call `cancel_game` directly; delete `EmbedDeletionConsumer`; remove `publish_embed_deleted` (TDD)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 159-181)

### [ ] Phase 6: Migrate Scheduler Flows (Flows 5-7)

- [ ] Task 6.1: Write xfail tests then replace `SyncEventPublisher` in scheduler with `BotActionQueue` inserts; remove `rabbitmq_url` from scheduler config (TDD)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 184-202)

### [ ] Phase 7: Migrate Bot Join/Leave/Drop Handlers (Flow 10)

- [ ] Task 7.1: Write xfail tests then replace `BotEventPublisher.publish_game_updated()` in `join_game.py`, `leave_game.py`, `participant_drop.py` with direct inserts + `pg_notify`; delete `publish_game_updated` (TDD)
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 205-228)

### [ ] Phase 8: Remove Dead Messaging Infrastructure

- [ ] Task 8.1: Verify all callers migrated; delete `shared/messaging/`, `services/retry/`, dead `BotEventPublisher` file; delete corresponding tests
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 231-252)

### [ ] Phase 9: Docker, Config, and Dependency Cleanup

- [ ] Task 9.1: Remove `rabbitmq` + `retry` from all compose files; remove RabbitMQ env vars; remove `aio-pika`, `pika`, OTel aio-pika from `pyproject.toml`; run `uv sync`; clean entrypoints and Dockerfiles
  - Details: .copilot-tracking/planning/details/20260704-01-remove-rabbitmq-details.md (Lines 255-277)

## Dependencies

- PostgreSQL with `pg_notify` (already in production use)
- asyncpg (already in use by `MessageRefreshListener`)
- SQLAlchemy async session (already in use by API and bot)
- `uv` for dependency and lockfile management

## Success Criteria

- All integration and e2e tests pass without `rabbitmq` container running
- `rabbitmq` service absent from `compose.yaml`
- `shared/messaging/` directory deleted
- `services/retry/` directory deleted
- `services/api/services/embed_deletion_consumer.py` deleted
- `shared/services/game_cancellation.py` exists and is used by both API and bot
- `grep -r "aio_pika|pika" services/ shared/` returns nothing
- `uv run pytest tests/unit` passes
- `uv run mypy shared/ services/` passes
