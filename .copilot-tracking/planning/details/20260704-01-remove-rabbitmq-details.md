<!-- markdownlint-disable-file -->

# Task Details: Remove RabbitMQ

## Research Reference

**Source Research**: #file:../research/20260408-02-remove-rabbitmq-research.md

---

## Phase 1: Add `BotActionQueue` Model + Alembic Migration

### Task 1.1: Write TDD tests for `BotActionQueue` model (RED)

Write xfail unit tests covering: model attribute access (`id`, `action_type`, `game_id`, `channel_id`, `message_id`, `user_id`, `discord_id`, `payload`, `enqueued_at`), table name `bot_action_queue`, and that the `action_type` column is not nullable.

- **Files**:
  - `tests/unit/shared/models/test_bot_action_queue.py` — new test file (stub model first)
  - `shared/models/bot_action_queue.py` — new model file (stub raising `NotImplementedError`)
- **Success**:
  - Tests collected and marked `xfail`
  - `uv run pytest tests/unit/shared/models/test_bot_action_queue.py` shows xfail
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 195-224) — table DDL + column spec
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 78-85) — project model conventions
- **Dependencies**:
  - None

### Task 1.2: Implement `BotActionQueue` model and Alembic migration (GREEN)

Implement the SQLAlchemy model with typed columns per the DDL spec. Add to `shared/models/__init__.py`. Create an Alembic migration that adds the `bot_action_queue` table, an index on `enqueued_at ASC`, and a trigger that fires `pg_notify('bot_action_queue_changed', '')` on INSERT. Remove xfail markers.

- **Files**:
  - `shared/models/bot_action_queue.py` — full SQLAlchemy model
  - `shared/models/__init__.py` — export `BotActionQueue`
  - `alembic/versions/` — new migration file
- **Success**:
  - `uv run pytest tests/unit/shared/models/test_bot_action_queue.py` passes (no xfail)
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 195-224) — complete DDL including trigger and NOTIFY
- **Dependencies**:
  - Task 1.1

---

## Phase 2: Add `shared/services/game_cancellation.py` + Update `GameService._delete_game_internal`

### Task 2.1: Write TDD tests for `cancel_game` (RED)

Write xfail unit tests covering: releases thumbnail image ref, releases banner image ref, deletes game row, publishes `GAME_CANCELLED` event when publisher provided, does NOT publish when publisher is `None`, captures `message_id` and `channel_id` from game before deletion.

- **Files**:
  - `tests/unit/shared/services/test_game_cancellation.py` — new test file
  - `shared/services/game_cancellation.py` — stub raising `NotImplementedError`
- **Success**:
  - Tests collected and marked `xfail`
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 155-166) — `cancel_game` signature and behaviour
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 275-279) — `GAME_CANCELLED` special case (capture before delete)
- **Dependencies**:
  - Phase 1 (BotActionQueue model available)

### Task 2.2: Implement `cancel_game` and update `GameService._delete_game_internal` (GREEN)

Implement `cancel_game(db, game, event_publisher=None)` in `shared/services/game_cancellation.py`. Update `GameService._delete_game_internal` to be a thin wrapper that calls `cancel_game(self.db, game, self.event_publisher)`. Update existing `_delete_game_internal` tests.

- **Files**:
  - `shared/services/game_cancellation.py` — full implementation
  - `services/api/services/games.py` — `_delete_game_internal` updated as thin wrapper
  - `tests/unit/api/services/test_games.py` — update `_delete_game_internal` tests
- **Success**:
  - All unit tests pass; no xfail markers remain in new tests
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 139-166) — EMBED_DELETED flow and `cancel_game` details
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 275-279) — `GAME_CANCELLED` special case
- **Dependencies**:
  - Task 2.1

---

## Phase 3: Migrate API to Bot Flows (Flows 1-4) + SSE NOTIFY

### Task 3.1: Write TDD tests for updated `GameService` API flows (RED)

Write xfail tests covering: `_publish_game_created` inserts a `BotActionQueue` row with `action_type='game_created'`; `_publish_game_cancelled` inserts with `action_type='game_cancelled'` and correct `message_id`/`channel_id`; `_publish_player_removed` inserts with `action_type='player_removed'`; `_detect_and_notify_transitions` inserts `action_type='send_dm'` for promotions; `_notify_demoted_users` inserts `action_type='send_dm'` for demotions; `_publish_game_updated` inserts a `message_refresh_queue` row AND calls `pg_notify('game_updated_sse', ...)`.

- **Files**:
  - `tests/unit/api/services/test_games.py` — add xfail tests for each method
- **Success**:
  - Tests collected and marked `xfail`
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 103-138) — flow inventory (flows 1-4 and 8)
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 225-264) — flow-by-flow replacement patterns
- **Dependencies**:
  - Phase 1 (BotActionQueue model)
  - Phase 2 (cancel_game + `_delete_game_internal` wrapper)

### Task 3.2: Implement API GameService migration (GREEN)

Remove `DeferredEventPublisher` parameter from `GameService.__init__`. Replace all `publish_deferred()` calls in `_publish_game_created`, `_publish_game_cancelled`, `_publish_player_removed`, `_detect_and_notify_transitions`, and `_notify_demoted_users` with `BotActionQueue` inserts. Replace `_publish_game_updated` with a direct `message_refresh_queue` insert plus `pg_notify('game_updated_sse', ...)`. Update `services/api/routes/games.py` to remove `DeferredEventPublisher` creation. Remove xfail markers.

- **Files**:
  - `services/api/services/games.py` — remove publisher, add BotActionQueue inserts + pg_notify
  - `services/api/routes/games.py` — remove DeferredEventPublisher creation and passing
  - `tests/unit/api/services/test_games.py` — remove xfail markers; update tests
  - `tests/unit/api/routes/test_games.py` — update route tests (no publisher arg)
- **Success**:
  - All unit tests pass; `uv run mypy shared/ services/` passes
  - `GameService` no longer imports from `shared/messaging/`
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 225-250) — flow-by-flow replacement code examples
- **Dependencies**:
  - Task 3.1

---

## Phase 4: Replace SSE Bridge Consumer (Flow 8)

### Task 4.1: Migrate `SSEGameUpdateBridge` to asyncpg LISTEN (TDD)

Write xfail tests for `SSEGameUpdateBridge` receiving notifications via `LISTEN game_updated_sse`. Then implement: replace `EventConsumer` with an asyncpg LISTEN connection on channel `game_updated_sse`, mirroring `MessageRefreshListener` pattern. Parse JSON payload for `game_id` and `guild_id`. Remove `EventConsumer` import from `sse_bridge.py`. Remove xfail markers.

- **Files**:
  - `services/api/services/sse_bridge.py` — replace EventConsumer with asyncpg LISTEN
  - `tests/unit/api/services/test_sse_bridge.py` — xfail then GREEN tests
- **Success**:
  - `sse_bridge.py` no longer imports from `shared/messaging/`
  - All unit tests pass; `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 178-190) — SSE fan-out pattern and asyncpg LISTEN approach
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 247-264) — Flow 8 replacement code example
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 7-52) — existing `MessageRefreshListener` as reference pattern
- **Dependencies**:
  - Phase 3 (pg_notify emitted from `_publish_game_updated`)

---

## Phase 5: Bot Embed Deletion Handler + Bot Action Queue Consumer

### Task 5.1: Add bot action queue LISTEN consumer (TDD)

Write xfail tests for a new bot listener/worker that processes `bot_action_queue` rows: reads rows `FOR UPDATE SKIP LOCKED LIMIT 1`, dispatches on `action_type`, deletes the row in the same transaction. Implement as a sibling class to `MessageRefreshListener` using asyncpg `LISTEN bot_action_queue_changed`. Handles all action types from flows 1-7. Remove xfail markers.

- **Files**:
  - `services/bot/bot_action_listener.py` — new listener class
  - `services/bot/bot.py` — register new listener on startup
  - `tests/unit/bot/test_bot_action_listener.py` — new test file
- **Success**:
  - All unit tests pass; `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 185-194) — crash safety / transactional delete pattern
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 7-52) — `message_refresh_listener.py` as reference pattern
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 103-138) — all action types to handle
- **Dependencies**:
  - Phase 1 (BotActionQueue model)

### Task 5.2: Migrate bot embed deletion handler; delete `EmbedDeletionConsumer` (TDD)

Write xfail tests for `on_raw_message_delete` calling `cancel_game(db, game)` directly (no publisher argument). Implement: update `services/bot/bot.py` `on_raw_message_delete` to call `cancel_game(db, game)`. Delete `services/api/services/embed_deletion_consumer.py`. Remove the `EmbedDeletionConsumer` startup from API startup code. Delete `BotEventPublisher.publish_embed_deleted` (now dead). Remove xfail markers.

- **Files**:
  - `services/bot/bot.py` — update `on_raw_message_delete`
  - `services/bot/events/publisher.py` — remove `publish_embed_deleted`
  - `services/api/services/embed_deletion_consumer.py` — delete file
  - `services/api/main.py` (or equivalent) — remove `EmbedDeletionConsumer` startup
  - `tests/unit/bot/test_bot.py` — update embed deletion tests
  - `tests/unit/api/services/test_embed_deletion_consumer.py` — delete test file
- **Success**:
  - `embed_deletion_consumer.py` deleted
  - `BotEventPublisher.publish_embed_deleted` removed
  - All unit tests pass; `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 139-166) — EMBED_DELETED flow simplification rationale and steps
- **Dependencies**:
  - Task 5.1
  - Phase 2 (`cancel_game` implemented)

---

## Phase 6: Migrate Scheduler Flows (Flows 5-7)

### Task 6.1: Replace scheduler `SyncEventPublisher` with `BotActionQueue` inserts (TDD)

Write xfail tests for `SchedulerDaemon._process_item` inserting `BotActionQueue` rows for `NOTIFICATION_DUE`, `GAME_STATUS_TRANSITION_DUE`, and `PARTICIPANT_DROP_DUE`. Implement: replace `self.publisher.publish(event)` with `db.execute(insert(BotActionQueue).values(...))` within the existing atomic commit. Remove `SyncEventPublisher` from scheduler. Remove `rabbitmq_url` from scheduler config. Remove xfail markers.

- **Files**:
  - `services/scheduler/generic_scheduler_daemon.py` — replace publisher with BotActionQueue insert
  - `services/scheduler/` config files — remove `rabbitmq_url`
  - `tests/unit/scheduler/test_generic_scheduler_daemon.py` — update tests
- **Success**:
  - `services/scheduler/` no longer imports from `shared/messaging/`
  - All unit tests pass; `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 7-52) — scheduler daemon current implementation
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 235-244) — flows 5-7 replacement code example
- **Dependencies**:
  - Phase 1 (BotActionQueue model)

---

## Phase 7: Migrate Bot Join/Leave/Drop Handlers (Flow 10)

### Task 7.1: Replace `BotEventPublisher.publish_game_updated()` in bot handlers (TDD)

Write xfail tests for `join_game.py`, `leave_game.py`, and `participant_drop.py` handlers inserting into `message_refresh_queue` and calling `pg_notify('game_updated_sse', ...)` directly. Implement: replace `publisher.publish_game_updated()` with direct `message_refresh_queue` insert + `pg_notify` in all three handlers. Remove `BotEventPublisher.publish_game_updated`. Remove xfail markers.

- **Files**:
  - `services/bot/handlers/join_game.py` — replace publisher call
  - `services/bot/handlers/leave_game.py` — replace publisher call
  - `services/bot/handlers/participant_drop.py` — replace publisher call
  - `services/bot/events/publisher.py` — remove `publish_game_updated`; delete if now empty
  - `tests/unit/bot/handlers/test_join_game.py` — update tests
  - `tests/unit/bot/handlers/test_leave_game.py` — update tests
  - `tests/unit/bot/handlers/test_participant_drop.py` — update tests
- **Success**:
  - `BotEventPublisher.publish_game_updated` removed
  - Bot handler files no longer import from `shared/messaging/`
  - All unit tests pass; `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 128-138) — flow 10 description (bot-initiated GAME_UPDATED)
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 167-177) — GAME_UPDATED intermediate hop analysis
- **Dependencies**:
  - Phase 4 (SSE LISTEN consumer running before pg_notify producers)

---

## Phase 8: Remove Dead Messaging Infrastructure

### Task 8.1: Delete `shared/messaging/`, `services/retry/`, and remaining dead code

Verify no remaining imports of `shared/messaging/` anywhere in `services/` or `shared/`. Delete the `shared/messaging/` package. Delete the `services/retry/` directory. Delete `services/bot/events/publisher.py` if fully empty. Delete corresponding unit tests. Update `shared/__init__.py` if it re-exported from `shared/messaging/`.

- **Files**:
  - `shared/messaging/` — delete entire directory
  - `services/retry/` — delete entire directory
  - `services/bot/events/publisher.py` — delete if now empty/dead
  - `services/bot/events/__init__.py` — delete if package is now empty
  - `tests/unit/shared/messaging/` — delete test directory
  - `tests/unit/retry/` — delete test directory (if exists)
- **Success**:
  - `grep -r "shared.messaging\|from shared.messaging\|import messaging" services/ shared/` returns nothing
  - `grep -r "BotEventPublisher" services/ shared/` returns nothing
  - All unit tests pass; `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 265-274) — complete list of files/modules to remove
- **Dependencies**:
  - Phases 3-7 all complete (all callers migrated before removal)

---

## Phase 9: Add Missing Integration and E2E Tests

### Task 9.1: Add integration tests for Flows 2, 3, 4, and 9

Add new integration tests covering the four flows that currently lack real-DB integration coverage.

- **Flow 2 (`GAME_CANCELLED`)**: Call `DELETE /api/v1/games/{id}` via `create_authenticated_client`; assert a `bot_action_queue` row exists with `action_type='game_cancelled'` and correct `game_id`. Pattern identical to the GAME_CREATED test in `test_game_signup_methods.py`.

- **Flow 3 (`PLAYER_REMOVED`)**: Create a game, insert a participant directly via `admin_db_sync`, call `PUT /api/v1/games/{id}` with `removed_participant_ids`; assert a `bot_action_queue` row with `action_type='player_removed'`.

- **Flow 4 (`NOTIFICATION_SEND_DM`)**: Create a game with `max_players=1`, add one confirmed participant and one waitlist participant, remove the confirmed participant via `PUT /api/v1/games/{id}` with `removed_participant_ids` to trigger `_detect_and_notify_transitions`; assert a `bot_action_queue` row with `action_type='send_dm'`.

- **Flow 9 (`EMBED_DELETED`)**: Call `cancel_game(db, game)` (no `event_publisher` argument) directly against a real async DB session; assert the game row is deleted and no `bot_action_queue` row is created. Pattern matches `test_participant_drop_event.py` direct-handler style.

These tests cover already-implemented code — no TDD RED phase required; write passing tests directly.

- **Files**:
  - `tests/integration/test_game_cancellation_queue.py` — new: Flow 2 bot_action_queue assertion
  - `tests/integration/test_player_removed_queue.py` — new: Flows 3 and 4 bot_action_queue assertions
  - `tests/integration/test_embed_deletion_integration.py` — new: Flow 9 real-DB cancel_game test
- **Success**:
  - All new integration tests pass
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows new tests PASSED
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 313-327) — coverage matrix identifying gaps
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 328-374) — missing test descriptions and patterns per flow
- **Dependencies**:
  - Phase 8 (migration complete; cancel_game and bot_action_queue inserts are live)

### Task 9.2: Add integration and e2e tests for Flow 10 SSE delivery

Add tests verifying that `pg_notify('game_updated_sse', ...)` fires from bot handler paths and that the SSE endpoint delivers the event to a connected client.

- **Integration**: Add a test that calls `handle_join_game` (or similar bot handler) then opens an asyncpg `LISTEN game_updated_sse` connection and asserts the notification fires. Reuse producer/consumer machinery from `test_sse_bridge_integration.py`.

- **E2E**: Add a test that opens `authenticated_admin_client.stream("GET", "/api/v1/sse/game-updates")` in a background task, calls `POST /api/v1/games/{id}/join`, and asserts a `game_updated` SSE event is received. Use `asyncio.create_task` + `asyncio.wait` pattern from `test_sse_bridge_integration.py`. Override the stream timeout: `timeout=httpx.Timeout(connect=10.0, read=30.0)`.

These tests cover already-implemented code — no TDD RED phase required.

- **Files**:
  - `tests/integration/test_game_updated_sse_bot.py` — new: pg_notify fires after bot join handler
  - `tests/e2e/test_game_updated_sse_e2e.py` — new: SSE event delivered after API join action
- **Success**:
  - Integration test passes: asyncpg listener receives `game_updated_sse` notification
  - E2E test passes: SSE client receives `game_updated` event after `POST /api/v1/games/{id}/join`
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows new tests PASSED
  - `scripts/run-e2e-tests.sh |& tee output-e2e.txt` shows new test PASSED
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 360-374) — Flow 10 SSE integration and e2e patterns
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 375-383) — notes on coverage gaps
- **Dependencies**:
  - Task 9.1

---

## Phase 10: Docker, Config, and Dependency Cleanup

### Task 10.1: Remove RabbitMQ from compose files, config templates, and Python dependencies

Remove the `rabbitmq` service block from all compose files. Remove the `retry` service blocks from all compose files. Remove `RABBITMQ_URL`, `RABBITMQ_HOST`, `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS` from all env template files. Remove `aio-pika`, `pika`, and `opentelemetry-instrumentation-aio-pika` from `pyproject.toml`. Remove RabbitMQ instrumentation setup from `shared/telemetry.py`. Run `uv sync` to update the lockfile. Delete `docker/retry.Dockerfile`. Remove RabbitMQ readiness-wait logic from bot/api entrypoints if present.

- **Files**:
  - `compose.yaml`, `compose.override.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.prod.yaml`, `compose.staging.yaml`, `compose.test.yaml` — remove `rabbitmq` and `retry` services
  - `config.template/env.template` — remove RabbitMQ env vars
  - `pyproject.toml` — remove `aio-pika`, `pika`, `opentelemetry-instrumentation-aio-pika`
  - `shared/telemetry.py` — remove aio-pika instrumentation
  - `docker/retry.Dockerfile` — delete
  - `docker/bot-entrypoint.sh`, `docker/api-entrypoint.sh` — remove RabbitMQ readiness wait if present
- **Success**:
  - `grep -r "rabbitmq" compose*.yaml config.template/` returns nothing
  - `grep "aio.pika\|pika" pyproject.toml` returns nothing
  - `uv run pytest tests/unit` passes
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260408-02-remove-rabbitmq-research.md (Lines 265-274) — services and env vars to remove
- **Dependencies**:
  - Phase 8 (all code removed before infrastructure cleanup)

---

## Dependencies

- PostgreSQL with `pg_notify` support (already in use)
- asyncpg (already in use — `MessageRefreshListener` uses it)
- SQLAlchemy async session (already in use)
- `uv` for dependency management

## Success Criteria

- All existing integration and e2e tests pass without `rabbitmq` container running
- `rabbitmq` service absent from `compose.yaml`
- `shared/messaging/` directory deleted
- `services/retry/` directory deleted
- `services/api/services/embed_deletion_consumer.py` deleted
- `shared/services/game_cancellation.py` exists and is used by both API and bot
- `grep -r "aio_pika\|pika" services/ shared/` returns nothing
- `uv run pytest tests/unit` passes
- `uv run mypy shared/ services/` passes
