<!-- markdownlint-disable-file -->

# Task Research Notes: Cancelled Game Cleanup (Discord deletion + DB deletion)

## Research Executed

### File Analysis

- `services/api/services/games.py`
  - `delete_game()` (line 1712): auth check → `release_image()` × 2 → manual delete of `GameStatusSchedule` rows → `game.status = CANCELLED` → reload game → `_publish_game_cancelled()`
  - `_publish_game_cancelled()` (line 2019): publishes `GAME_CANCELLED` event with `{game_id, message_id, channel_id}` as a deferred event (fires after DB commit)
  - Does NOT currently delete the game row — only marks status CANCELLED
- `services/api/routes/games.py`
  - `DELETE /api/v1/games/{game_id}` (line 547): calls `delete_game()`, returns 204, no explicit commit — commit is handled by `get_db_with_user_guilds()` session lifecycle
- `services/bot/events/handlers.py`
  - `_handle_game_cancelled()` (line 1119): fetches game from DB, fetches channel+message, calls `message.edit()` to update embed footer to show "Cancelled"
  - Does NOT delete the message or the game row
- `shared/models/game_image.py`
  - `GameImage` has `reference_count` column — pure application-managed integer, no DB trigger
  - FK direction: `game_sessions.thumbnail_id → game_images.id ON DELETE SET NULL`
  - `ON DELETE SET NULL` means: if an image row is deleted, the FK column on the game is nulled — protects games from dangling references to deleted images. Has **no effect** on game deletion.
- `shared/services/image_storage.py`
  - `release_image()`: decrements `reference_count`; deletes image row when count reaches zero
  - Must be called explicitly before game deletion — no trigger or cascade handles it
- `shared/models/game_status_schedule.py` / `notification_schedule.py` / `participant.py` / `participant_action_schedule.py`
  - All have `ForeignKey("game_sessions.id", ondelete="CASCADE")` — deleting the game row cascades to all these tables automatically
- `shared/models/participant.py`
  - `ForeignKey("game_sessions.id", ondelete="CASCADE")` — participants deleted by DB cascade
- `shared/messaging/deferred_publisher.py`
  - Events queued on `db.info["_deferred_events"]`, published after the session `commit()` via SQLAlchemy `after_commit` event listener
  - Event payload is captured before commit, so game row being gone at publish time is fine
- `services/bot/handlers/participant_drop.py`
  - Uses `get_bypass_db_session()` — the bot already has precedent for writing to the DB with bypass RLS
- `tests/e2e/test_game_cancellation.py`
  - Asserts `game.status == "CANCELLED"` in DB after DELETE request
  - Asserts Discord message embed footer contains "cancelled"
  - Both assertions will need updating under new behaviour

### Code Search Results

- `game_sessions.thumbnail_id` FK: `ondelete="SET NULL"` (in `dc81dd7fe299` migration and `20260311_add_archive_fields` migration)
- `game_participants.game_session_id` FK: `ondelete="CASCADE"` (initial schema migration)
- `game_status_schedule.game_id` FK: `ondelete="CASCADE"` (model confirmed)
- `notification_schedule.game_id` FK: `ondelete="CASCADE"` (model confirmed)
- `participant_action_schedule.game_id` FK: `ondelete="CASCADE"` (model confirmed)
- Manual `GameStatusSchedule` deletion in `delete_game()` is redundant — CASCADE handles it

### Project Conventions

- Standards referenced: deferred event publishing pattern (`DeferredEventPublisher`), bypass DB session for bot writes, TDD applies (Python)
- Instructions followed: surgical minimal changes, no extra features

## Key Discoveries

### Image Reference Counting

The `game_images` table uses an application-managed `reference_count` integer. There is no DB trigger, no `ON DELETE CASCADE` from game to image. The FK runs in the **opposite direction** — game points at image with `ON DELETE SET NULL`. This means:

- Deleting a game row has **no effect** on image `reference_count`
- `release_image()` is the only mechanism to decrement and eventually delete image rows
- It must be called while the game object (and its `thumbnail_id`/`banner_image_id` values) is still in memory, before `db.delete(game)`

### DB Cascade Chain on Game Deletion

When `db.delete(game)` is committed, Postgres automatically deletes:

- `game_participants` rows (CASCADE)
- `game_status_schedule` rows (CASCADE)
- `notification_schedule` rows (CASCADE)
- `participant_action_schedule` rows (CASCADE)

The manual loop deleting `GameStatusSchedule` rows in the current `delete_game()` is therefore redundant.

### Event Payload Completeness

`_publish_game_cancelled()` already includes `game_id`, `message_id`, and `channel_id` — everything the bot needs to delete the Discord message. The game row being gone from the DB by the time the bot processes the event is fine.

### Bot DB Access Precedent

`services/bot/handlers/participant_drop.py` already uses `get_bypass_db_session()` to delete a participant row directly. The same pattern applies if we ever want the bot to write to the DB, but for this task the bot only needs to delete the Discord message — no DB write required in the bot.

## Recommended Approach

**API does all DB work; bot only deletes the Discord message.**

### API changes (`services/api/services/games.py` — `delete_game`)

1. Capture `message_id = game.message_id` and `channel_id = game.channel.channel_id` before any mutations
2. Call `release_image(self.db, game.thumbnail_id)` and `release_image(self.db, game.banner_image_id)` — unchanged, must remain before deletion
3. Remove the manual `GameStatusSchedule` deletion loop — CASCADE handles it
4. Replace `game.status = CANCELLED` + reload with `await self.db.delete(game)`
5. Publish `GAME_CANCELLED` event with the captured `message_id` and `channel_id` using `publish_deferred` — unchanged payload shape, fires after commit

### Bot changes (`services/bot/events/handlers.py` — `_handle_game_cancelled`)

1. Remove the DB fetch of the game (row no longer exists)
2. Call `message.delete()` instead of `message.edit()`
3. Handle `discord.NotFound` gracefully (message already gone)

### Test changes

- `tests/e2e/test_game_cancellation.py`: assert game row is **absent** from DB (not status=CANCELLED), and assert Discord message is **deleted** (not footer contains "cancelled")
- `tests/integration/services/api/services/test_game_image_integration.py` (`test_delete_game_releases_images`): already commits and checks image deletion — will continue to pass unchanged once logic switches to `db.delete(game)`

## Implementation Guidance

- **Objectives**: Delete game from DB on cancel; delete Discord announcement message
- **Key Tasks**:
  1. Update `GameService.delete_game()` — remove status-set and schedule loop, add `db.delete(game)`, capture Discord IDs beforehand
  2. Update `EventHandlers._handle_game_cancelled()` — remove DB fetch, call `message.delete()`
  3. Update `test_game_cancellation.py` E2E assertions
- **Dependencies**: `release_image()` must precede `db.delete(game)`; event payload shape unchanged
- **Success Criteria**:
  - `DELETE /api/v1/games/{id}` returns 204 and game row is absent from DB
  - Discord announcement message is deleted (not edited)
  - Image reference counts are correctly decremented; orphaned images deleted
  - All existing integration tests pass without modification (except E2E cancellation test assertions)
  - TDD: unit/integration tests for new bot handler behaviour and updated service behaviour written first
