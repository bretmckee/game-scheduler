<!-- markdownlint-disable-file -->

# Task Research Notes: Deferred Game Announcement

## Research Executed

### File Analysis

- `shared/models/game.py`
  - `GameSession` has no `post_at` field today; `message_id` is nullable String(20)
  - `status` uses `GameStatus` enum: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, ARCHIVED
  - `created_at`, `updated_at`, `scheduled_at` are the only datetime fields
- `shared/schemas/game.py`
  - `GameCreateRequest`: no `post_at` field; `scheduled_at` is the only datetime
  - `GameUpdateRequest`: no `post_at`; all fields optional
  - `GameResponse`: includes `message_id`, `status`, timestamps — needs `post_at` added
- `services/api/services/games.py`
  - `create_game()` → `_persist_and_publish()` → `_setup_game_schedules()` + `_publish_game_created()`
  - `_setup_game_schedules()` creates `NotificationSchedule` reminder rows and `GameStatusSchedule` transition rows immediately at game creation
  - `_publish_game_created()` fires deferred `GAME_CREATED` RabbitMQ event
  - `update_game()` unconditionally calls `_publish_game_updated()` at the end
  - `_publish_game_updated()` publishes `GAME_UPDATED`; passes `message_id: game.message_id or ""`
  - `list_games()` takes no auth context for visibility; route applies `verify_game_access` post-query
- `services/api/routes/games.py`
  - `list_games` route has `current_user`, `role_service` in scope; post-filters with `verify_game_access`
  - `join_game` route has no check for announcement state; would allow joining pre-announced games
- `services/api/dependencies/permissions.py`
  - `can_manage_game()`: returns True if host, is_maintainer token, or has bot_manager permission
  - This is the correct check for "can see pending-announcement games"
- `services/bot/events/handlers.py`
  - `_handle_game_created()`: validates channel, loads game from DB, calls `channel.send()`, sets `game.message_id`, commits
  - `_handle_game_updated()`: inserts into `message_refresh_queue` — does NOT check `message_id IS NULL` before queuing
- `services/bot/message_refresh_listener.py`
  - asyncpg LISTEN pattern: `connect → add_listener → create_future` to block
  - `_on_notify` spawns per-channel worker task; deduplicates by channel ID
  - This is the exact pattern `AnnouncementLoop` will mirror
- `services/bot/bot.py`
  - `setup_hook` / `on_ready`: wires `MessageRefreshListener` as `asyncio.create_task`; same hook point for `AnnouncementLoop`
- `services/scheduler/generic_scheduler_daemon.py`
  - Sync pattern: `MIN(time_field) WHERE NOT status_field`; sleep until due; LISTEN for early wake
  - Three instances: notification, status, participant-action
  - Research doc `20260408-03` proposes absorbing these as async tasks in the bot
- `shared/models/notification_schedule.py` / `shared/models/game_status_schedule.py`
  - Both use `executed: bool` as the "processed" flag
  - `game_sessions.message_id IS NULL` serves the equivalent role for announcement state

### Code Search Results

- `_setup_game_schedules` call sites
  - Called in `_persist_and_publish` (line 804) and `clone_game` (line 956)
- `_publish_game_created` call sites
  - Only called from `_persist_and_publish`
- `can_manage_game` signature
  - Takes `game_host_id`, `guild_id`, `current_user`, `role_service`, `db`
- `join_game` route (line 707)
  - Calls `verify_game_access` but no announcement-state guard

### External Research

- #githubRepo:"discord/discord-api-docs asyncpg LISTEN NOTIFY pattern"
  - asyncpg `add_listener` + `create_future` is the idiomatic async LISTEN approach
- Prior research `20260408-03-remove-scheduler-research.md` (from git commit 3ac4a299)
  - Proposes `SchedulerLoop` class as async replacement for `SchedulerDaemon`
  - Design: asyncpg LISTEN + `asyncio.wait_for` sleep + MIN() next-due query
  - Deferred announcement is explicitly a clean "first piece" of this migration

### Project Conventions

- Standards referenced: `python.instructions.md`, `fastapi-transaction-patterns.instructions.md`
- Alembic migrations use `alembic_utils.pg_function.PGFunction` for triggers
- Schedule tables use `executed: bool` flag (not delete-on-process)
- Bot asyncpg tasks started in `on_ready` under `if not hasattr(self, "_X_started")` guard

## Key Discoveries

### Project Structure

The announcement path today is a straight line: API → RabbitMQ → Bot → Discord. There is no
concept of "post this later." `post_at` is a new field on `game_sessions` that gates when the
API fires `_publish_game_created` and when the bot actually posts the Discord message.

The bot already has an async LISTEN loop (`MessageRefreshListener`); the new `AnnouncementLoop`
follows the same pattern and is the first concrete step of the `20260408-03` scheduler migration.

### Implementation Patterns

**`_persist_and_publish` conditional branching:**

```python
if game.post_at and game.post_at > utc_now():
    # Deferred: skip schedules and publish; bot loop will fire at post_at
    pass
else:
    await self._setup_game_schedules(game, ...)
    await self._publish_game_created(game, channel_config)
```

**`AnnouncementLoop` — async bot task (mirrors `MessageRefreshListener`):**

```python
class AnnouncementLoop:
    def __init__(self, db_url: str, bot: GameSchedulerBot) -> None: ...

    async def start(self) -> None:
        conn = await asyncpg.connect(db_url)
        await conn.add_listener("game_announcement_changed", self._on_notify)
        while True:
            await self._process_due()
            next_due = await self._next_due_time()
            wait = (next_due - utc_now()).total_seconds() if next_due else MAX_TIMEOUT
            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=max(0, wait))
            except asyncio.TimeoutError:
                pass
            self._wake_event.clear()

    async def _process_due(self) -> None:
        async with get_db_session() as db:
            result = await db.execute(
                select(GameSession)
                .where(
                    GameSession.post_at.isnot(None),
                    GameSession.post_at <= utc_now(),
                    GameSession.message_id.is_(None),
                    GameSession.status == GameStatus.SCHEDULED,
                )
                .with_for_update(skip_locked=True)
            )
            for game in result.scalars():
                await self._announce(db, game)

    async def _announce(self, db, game: GameSession) -> None:
        # Re-check message_id inside the row lock
        if game.message_id is not None:
            return
        # Post to Discord (same logic as _handle_game_created)
        content, embed, view = await self.bot.event_handlers._create_game_announcement(game)
        channel = await self.bot._get_bot_channel(game.channel.channel_id)
        message = await channel.send(content=content, embed=embed, view=view, ...)
        game.message_id = str(message.id)
        await db.commit()
        # Now set up schedules (deferred until announcement fires)
        game_service = GameService(db, ...)
        await game_service._setup_game_schedules(game, game.reminder_minutes or [], ...)
```

**PostgreSQL trigger for wakeup:**

```sql
CREATE OR REPLACE FUNCTION notify_game_announcement_changed()
RETURNS trigger AS $$
BEGIN
  IF NEW.post_at IS NOT NULL AND (TG_OP = 'INSERT' OR OLD.post_at IS DISTINCT FROM NEW.post_at) THEN
    PERFORM pg_notify('game_announcement_changed', NEW.id);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER game_sessions_announcement_notify
AFTER INSERT OR UPDATE ON game_sessions
FOR EACH ROW EXECUTE FUNCTION notify_game_announcement_changed();
```

**`update_game` guard for pre-announcement edits:**

```python
# At end of update_game, before _publish_game_updated:
if game.message_id is not None:
    await self._publish_game_updated(game)
# else: game not yet announced; no Discord message to refresh
```

**`update_game` clear-post_at path:**

```python
if update_data.post_at is None and game.post_at is not None and game.message_id is None:
    # Host cleared the deferred post — announce immediately
    game.post_at = None
    await self._setup_game_schedules(game, ...)
    await self._publish_game_created(game, channel_config)
elif update_data.post_at is not None:
    game.post_at = update_data.post_at  # scheduler loop picks up the new time automatically
```

**Visibility filter in list route:**

```python
for game in games:
    # If pending announcement, only host/manager can see it
    if game.post_at and game.post_at > utc_now() and game.message_id is None:
        is_manager = await permissions_deps.can_manage_game(
            game_host_id=game.host.discord_id,
            guild_id=game.guild.guild_id,
            current_user=current_user,
            role_service=role_service,
            db=game_service.db,
        )
        if not is_manager:
            continue
    # existing verify_game_access check...
```

**`join_game` guard:**

```python
if game.post_at and game.post_at > utc_now() and game.message_id is None:
    raise HTTPException(status_code=404, detail="Game not found")
```

### API and Schema Documentation

**New field: `GameSession.post_at`**

| Attribute   | Value                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| Column      | `post_at TIMESTAMPTZ NULL`                                                  |
| Python type | `datetime \| None`                                                          |
| Semantics   | If NULL or past: post immediately on create. If future: defer announcement. |
| Migration   | Single `op.add_column` in new Alembic revision                              |

**`GameCreateRequest` addition:**

```python
post_at: datetime | None = Field(
    None,
    description="When to post the Discord announcement. None or past = post immediately.",
)
```

**`GameUpdateRequest` addition:**

```python
post_at: datetime | None = Field(
    None,
    description=(
        "Update scheduled announcement time. Set to None to post immediately if not yet announced."
    ),
)
```

**`GameResponse` addition:**

```python
post_at: str | None = Field(None, description="Scheduled announcement time (ISO 8601 UTC) or None")
```

### Technical Requirements

- `SKIP_LOCKED` on the announcement query prevents two concurrent `AnnouncementLoop` iterations
  (if bot restarts mid-process) from double-posting
- `AnnouncementLoop` started in `on_ready` under a `_announcement_loop_started` hasattr guard,
  consistent with `MessageRefreshListener` startup pattern
- `_setup_game_schedules` must be called AFTER announcement fires (not at creation time) when
  `post_at` is in the future, to prevent reminder DMs arriving before the Discord announcement
- `clone_game` also calls `_persist_and_publish` — it must inherit the same `post_at` conditional

## Recommended Approach

Add `post_at: datetime | None` to `GameSession`. On creation with a future `post_at`, skip
`_setup_game_schedules` and `_publish_game_created`. The bot runs an `AnnouncementLoop` asyncio
task that wakes via asyncpg LISTEN and posts due games directly, then sets up schedules. This is
the first concrete step of the scheduler-removal migration documented in `20260408-03`.

## Implementation Guidance

- **Objectives**:
  - Allow game creators to specify when the Discord announcement posts
  - Pending-announcement games visible only to host/bot-manager
  - First concrete step toward absorbing scheduler daemons into the bot
- **Key Tasks**:
  1. **Migration** — Add `post_at TIMESTAMPTZ NULL` to `game_sessions`; add NOTIFY trigger
  2. **Model** — Add `post_at: Mapped[datetime | None]` to `GameSession`
  3. **Schemas** — Add `post_at` to `GameCreateRequest`, `GameUpdateRequest`, `GameResponse`
  4. **API route** — Parse `post_at` form field in `create_game` route; pass through to service
  5. **`create_game` service** — Validate `post_at < scheduled_at` if set; store on game
  6. **`_persist_and_publish`** — Gate `_setup_game_schedules` + `_publish_game_created` on `post_at`
  7. **`update_game`** — Handle clear-`post_at` (announce immediately) and change-`post_at` paths; guard `_publish_game_updated` on `message_id IS NOT NULL`
  8. **`join_game` route** — Return 404 if game has future `post_at` and no `message_id`
  9. **List visibility** — Add pending-announcement filter in `list_games` route loop
  10. **`AnnouncementLoop` class** — New `services/bot/announcement_loop.py`; asyncpg LISTEN + `SKIP_LOCKED` query + direct announce + schedule setup
  11. **Bot wiring** — Start `AnnouncementLoop` task in `on_ready` under hasattr guard
  12. **Frontend** — Optional "Schedule announcement" DateTimePicker in `CreateGame`/`EditGame`; "Pending announcement at [timestamp]" badge in `MyGames`/`GameDetails` when `message_id IS NULL` and `post_at` set
- **Dependencies**: None — does not require RabbitMQ or scheduler removal to proceed
- **Success Criteria**:
  - Game created with future `post_at` does not appear in Discord until that time
  - Pending-announcement game visible in "My Games" to host; hidden from other users' lists
  - Editing `post_at` to a new future time delays announcement to new time
  - Clearing `post_at` on edit causes immediate announcement
  - Reminder DMs do not fire before the Discord announcement appears
  - Joining a pre-announcement game via API returns 404
  - All existing game creation / announcement e2e tests continue to pass (no `post_at` = immediate, unchanged behavior)
