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
