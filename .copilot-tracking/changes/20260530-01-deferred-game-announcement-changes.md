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

---

## Phase 3: API update path, join guard, and list visibility

### Modified

- `services/api/routes/games.py` — Added `post_at`/`clear_post_at` form params to `update_game` route; extended `_parse_update_form_data` to 7-tuple; added pre-announced guard in `join_game` returning 404 when `post_at` is future and `message_id` is NULL; added visibility filter in `list_games` authorization loop hiding pending-announcement games from non-managers
- `services/api/services/games.py` — Updated `_update_game_fields` to set `game.post_at` when explicitly provided; added clear-to-announce-immediately path in `update_game` that clears `post_at`, calls `_setup_game_schedules`, and publishes `_publish_game_created`; added guard so `_publish_game_updated` is only called for games where `message_id is not None`
- `tests/unit/services/api/routes/test_games_endpoint_errors.py` — Added `test_join_game_returns_404_for_pre_announced_game`; fixed `mock_game` fixture to set `post_at = None` and `message_id = None`
- `tests/unit/services/api/routes/test_games_routes.py` — Added `TestListGamesPendingAnnouncementFilter` with two tests (hides from non-manager, shows to manager); fixed `_make_game` helpers and direct `MagicMock()` instances to set `post_at = None` and `message_id = None`
- `tests/unit/services/api/services/test_games_service.py` — Added four tests: `test_update_game_clear_post_at_announces_immediately`, `test_update_game_change_post_at_updates_value`, `test_update_game_skips_publish_updated_when_not_yet_announced`, `test_update_game_publishes_updated_when_already_announced`

### Added

- `tests/integration/test_deferred_game_announcement.py` — Four integration tests verifying join guard (404 for pending, 200 after announcement posted) and list visibility (hidden from non-manager, visible to host)

---

## Phase 5: Frontend — `post_at` field and pending-announcement badge

### Modified

- `frontend/src/types/index.ts` — Added `post_at?: string | null` to the `GameSession` interface (optional field, backward-compatible with all existing mocks)

- `frontend/src/components/GameForm.tsx` — Added `postAt: Date | null` and `clearPostAt: boolean` to `GameFormData`; initialized both in `useState` and the `useEffect` sync; added `handlePostAtChange` and `handleClearPostAtChange` handlers; added `DateTimePicker` with label "Schedule announcement (optional)" and helper text "Leave empty to post immediately", `maxDateTime` capped at `scheduledAt`; added "Post immediately (announce now)" `Checkbox` in edit mode when `initialData.post_at` is set and `message_id` is null

- `frontend/src/pages/CreateGame.tsx` — Appends `post_at` ISO string to `FormData` when `formData.postAt` is non-null

- `frontend/src/pages/EditGame.tsx` — Appends `clear_post_at=true` (or `post_at` ISO string) to `FormData` in both `handleSubmit` and `handleSaveAndArchive`

- `frontend/src/components/GameCard.tsx` — Added warning `Chip` showing "Pending announcement: [timestamp]" when `game.post_at` is set and `game.message_id` is null

- `frontend/src/pages/GameDetails.tsx` — Added info `Alert` showing "Announcement scheduled for [timestamp]" when `game.post_at` is set and `game.message_id` is null

### Added

- `frontend/src/types/__tests__/index.test.ts` — Two tests verifying `GameSession.post_at` accepts `null` and ISO strings

- `frontend/src/pages/__tests__/CreateGame.test.tsx` — Added `describe('CreateGame - post_at scheduling field')` with test verifying the "Schedule announcement (optional)" helper text is rendered

- `frontend/src/pages/__tests__/EditGame.test.tsx` — Added `describe('EditGame - post_at scheduling field')` with test verifying the picker renders and shows helper text when editing a game with `post_at` set

- `frontend/src/pages/__tests__/MyGames.test.tsx` — Added `describe('MyGames - pending announcement badge')` with test verifying "Pending announcement:" chip appears for a hosted game with `post_at` and no `message_id`

- `frontend/src/pages/__tests__/GameDetails.test.tsx` — Added `describe('GameDetails - pending announcement badge')` with two tests: shows "Announcement scheduled for" alert when `post_at` is set and `message_id` is null; does not show the alert when `message_id` is set
