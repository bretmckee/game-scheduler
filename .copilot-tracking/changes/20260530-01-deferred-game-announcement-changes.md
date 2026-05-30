# Changes: Deferred Game Announcement

## Plan Reference

[Plan](../plans/20260530-01-deferred-game-announcement.plan.md)

---

## Phase 1: Database foundation — migration, model, schema

### Added

- `alembic/versions/20260530_add_post_at_game_sessions.py` — Alembic migration adding `post_at TIMESTAMPTZ NULL` to `game_sessions` with PL/pgSQL NOTIFY trigger `game_sessions_announcement_notify`

### Modified

- `shared/models/game.py` — Added `post_at: Mapped[datetime | None]` column after `message_id`
- `shared/schemas/game.py` — Added `post_at` field to `GameCreateRequest`, `GameUpdateRequest` (with `clear_post_at` sentinel), and `GameResponse`
- `tests/unit/shared/models/test_game_session.py` — Added test verifying `post_at` column exists and is nullable
- `tests/unit/shared/schemas/test_game_schema.py` — Added tests verifying `post_at` field in all three schema classes

---

## Phase 2: API create path — parse and gate on `post_at`

### Modified

- `services/api/routes/games.py` — Added `post_at: Annotated[str | None, Form()] = None` parameter to `create_game` route; parse ISO string to datetime and pass through to `GameCreateRequest`
- `services/api/services/games.py` — Added early `ValueError` if `post_at >= scheduled_at` in `create_game`; added deferred gate in `_persist_and_publish` skipping `_setup_game_schedules` and `_publish_game_created` when `game.post_at` is in the future
- `tests/unit/services/api/routes/test_games_routes.py` — Added `TestCreateGameRoutePostAt` verifying route parses and passes `post_at` to service
- `tests/unit/services/api/services/test_games_service.py` — Added `test_create_game_rejects_post_at_after_scheduled_at` verifying validation error
- `tests/unit/services/test_game_service_persist_and_publish.py` — Added `test_persist_and_publish_skips_schedules_when_post_at_future`; fixed `mock_game` fixture to set `post_at = None` explicitly
