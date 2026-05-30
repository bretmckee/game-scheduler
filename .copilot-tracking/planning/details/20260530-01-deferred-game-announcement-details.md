<!-- markdownlint-disable-file -->

# Task Details: Deferred Game Announcement

## Research Reference

**Source Research**: #file:../research/20260530-01-deferred-game-announcement-research.md

---

## Phase 1: Database foundation — migration, model, schema

### Task 1.1: Add `post_at TIMESTAMPTZ NULL` to `game_sessions` via Alembic migration with NOTIFY trigger

Create a new Alembic revision that adds the column and installs a PostgreSQL NOTIFY trigger so the `AnnouncementLoop` bot task wakes immediately when a game's `post_at` changes.

- **TDD step**: Write an xfail test that imports `GameSession` and checks `hasattr(GameSession, "post_at")`. Mark xfail; confirm it fails. Then implement and confirm green.
- **Files**:
  - `alembic/versions/20260530_add_post_at_game_sessions.py` — new Alembic revision
  - `shared/models/game.py` — (modified in Task 1.2)
- **Migration contents**:
  - `op.add_column("game_sessions", sa.Column("post_at", sa.TIMESTAMP(timezone=True), nullable=True))`
  - Create PL/pgSQL function `notify_game_announcement_changed()` that calls `pg_notify('game_announcement_changed', NEW.id)` when `NEW.post_at IS NOT NULL` and the row is INSERTed or `OLD.post_at IS DISTINCT FROM NEW.post_at`
  - Attach trigger `game_sessions_announcement_notify` AFTER INSERT OR UPDATE ON `game_sessions` FOR EACH ROW
  - Downgrade: drop trigger, drop function, drop column
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 147–164) — PostgreSQL trigger SQL pattern
- **Success**:
  - `alembic upgrade head` applies cleanly
  - `alembic downgrade -1` reverts cleanly
  - Column `post_at` exists in `game_sessions`; NOTIFY trigger is registered

### Task 1.2: Add `post_at: Mapped[datetime | None]` to `GameSession` model

- **Files**:
  - `shared/models/game.py` — insert after `message_id` field (line 74)
- **Change**: add `post_at: Mapped[datetime | None] = mapped_column(nullable=True)` with `__tablename__ = "game_sessions"` context
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 213–220) — `GameSession.post_at` attribute spec
- **Success**:
  - `GameSession().post_at` is `None` by default
  - SQLAlchemy maps to the `post_at` column added in Task 1.1

### Task 1.3: Add `post_at` field to `GameCreateRequest`, `GameUpdateRequest`, and `GameResponse` schemas

- **TDD step**: Write xfail tests in `tests/unit/shared/schemas/test_game_schema.py` verifying each of the three schemas accepts/returns `post_at`. Mark xfail; confirm failures. Implement; confirm green.
- **Files**:
  - `shared/schemas/game.py` — add `post_at` to three classes (lines 41–246)
- **`GameCreateRequest` addition** (after `scheduled_at` at line 46):
  ```python
  post_at: datetime | None = Field(
      None,
      description="When to post the Discord announcement. None or past = post immediately.",
  )
  ```
- **`GameUpdateRequest` addition** (after `scheduled_at` at line 124):
  ```python
  post_at: datetime | None = Field(
      None,
      description="Update scheduled announcement time. None means do not change.",
  )
  clear_post_at: bool = Field(
      False,
      description="If True, clear post_at and announce immediately if not yet announced.",
  )
  ```
  Note: a separate `clear_post_at` bool is used (matching the `remove_thumbnail`/`remove_image` sentinel pattern) to distinguish "not provided" from "explicitly cleared."
- **`GameResponse` addition** (after `scheduled_at` at line 187):
  ```python
  post_at: str | None = Field(None, description="Scheduled announcement time (ISO 8601 UTC) or None")
  ```
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 211–247) — schema field specifications
- **Success**:
  - `GameCreateRequest(post_at=None, ...)` validates without error
  - `GameUpdateRequest(clear_post_at=True)` validates
  - `GameResponse(post_at="2026-06-01T18:00:00Z", ...)` serializes correctly

---

## Phase 2: API create path — parse and gate on `post_at`

### Task 2.1: Add `post_at` form parameter to the `create_game` route and pass it through to the service

- **TDD step**: Write xfail test that the `create_game` route (unit-tested via mock) passes `post_at` through to `GameCreateRequest`. Confirm xfail; implement; confirm green.
- **Files**:
  - `services/api/routes/games.py` — `create_game` function (line 311)
- **Changes**:
  - Add `post_at: Annotated[str | None, Form()] = None` to `create_game` signature (after `remind_host_rewards`)
  - Parse: `post_at_datetime = datetime.fromisoformat(post_at.replace("Z", "+00:00")) if post_at else None`
  - Include `post_at=post_at_datetime` in the `GameCreateRequest(...)` constructor call
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 85–97) — `_persist_and_publish` branching overview
- **Success**:
  - Route accepts `post_at` form field; absent field defaults to `None`
  - Value is passed to the service unchanged

### Task 2.2: Validate `post_at < scheduled_at` in `create_game` service and gate `_persist_and_publish` schedule/publish calls

- **TDD step**:
  1. Write xfail test `test_create_game_rejects_post_at_after_scheduled_at` — pass `post_at > scheduled_at`; expect `ValueError`. Mark xfail; confirm failure; implement; confirm green.
  2. Write xfail test `test_persist_and_publish_skips_schedules_when_post_at_future` — mock a game with future `post_at`; assert `_setup_game_schedules` and `_publish_game_created` are NOT called. Mark xfail; confirm failure; implement; confirm green.
  3. Verify existing `_persist_and_publish` tests (in `tests/unit/services/test_game_service_persist_and_publish.py`) still pass — they use games without `post_at`, so the immediate path is unchanged.
- **Files**:
  - `services/api/services/games.py` — `create_game` (near top of method), `_persist_and_publish` (lines 765–815)
- **Changes to `create_game`** (validate after `GameSession` is built):
  ```python
  if game_data.post_at and game_data.post_at <= game_data.scheduled_at:
      raise ValueError("post_at must be before scheduled_at")
  ```
  Actually the semantics should be: `post_at` is when the announcement posts, `scheduled_at` is when the game starts. `post_at` should be before `scheduled_at`. So validate `post_at >= scheduled_at` → raise error.
- **Changes to `_persist_and_publish`**: wrap the schedule and publish calls:
  ```python
  if game.post_at and game.post_at > utc_now():
      # Deferred: AnnouncementLoop will fire at post_at and then call _setup_game_schedules
      pass
  else:
      await self._setup_game_schedules(
          game,
          resolved_fields["reminder_minutes"],
          resolved_fields["expected_duration_minutes"],
      )
      game = await self.get_game(game.id)
      ...
      await self._publish_game_created(game, channel_config)
  ```
  Preserve the `get_game` reload between schedules and publish for the immediate path.
- **`clone_game` (line 844)**: `clone_game` calls `_persist_and_publish` directly; because `clone_game` constructs a new `GameSession` without copying `post_at` from the source (clones should announce immediately), no change needed — `game.post_at` will be `None` on the cloned game.
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 87–97) — `_persist_and_publish` conditional branching pattern
- **Success**:
  - Creating a game with future `post_at` persists the row but does NOT call `_setup_game_schedules` or publish `GAME_CREATED`
  - Creating a game with `post_at=None` (or past) behaves identically to today
  - Creating a game with `post_at >= scheduled_at` raises `ValueError`

---

## Phase 3: API update path, join guard, and list visibility

### Task 3.1: Extend `update_game` route and `_parse_update_form_data` with `post_at` / `clear_post_at` form fields

- **TDD step**: Write xfail test that the `update_game` route accepts `post_at` and `clear_post_at` form fields and passes them to `GameUpdateRequest`. Mark xfail; implement; confirm green.
- **Files**:
  - `services/api/routes/games.py` — `_parse_update_form_data` (line 143), `update_game` route (line 547)
- **Changes to `_parse_update_form_data`**:
  - Add `post_at: str | None` and `clear_post_at: bool` parameters (and return them in the tuple)
  - Parse `post_at` → `datetime | None` the same way `scheduled_at` is parsed
- **Changes to `update_game` signature** (before the `*` keyword-only separator):
  - `post_at: Annotated[str | None, Form()] = None`
  - `clear_post_at: Annotated[bool, Form()] = False`
- **Changes to `GameUpdateRequest` construction** in the route: include `post_at=post_at_datetime, clear_post_at=clear_post_at`
- **Success**:
  - Route accepts both new form fields; absent fields default to `None`/`False`

### Task 3.2: Handle `post_at` in `update_game` service — clear-to-announce-immediately, change-time, and `_publish_game_updated` guard

- **TDD steps**:
  1. `test_update_game_clear_post_at_announces_immediately` — game has future `post_at` and no `message_id`; `update_data.clear_post_at=True` → expect `_setup_game_schedules` and `_publish_game_created` called; `game.post_at` is `None` after. Mark xfail; implement; confirm green.
  2. `test_update_game_change_post_at_updates_value` — game has future `post_at`; `update_data.post_at` set to a later time → game.post_at updated; no publish. Mark xfail; implement; confirm green.
  3. `test_update_game_skips_publish_updated_when_not_yet_announced` — game has future `post_at` and no `message_id`; standard update with no `clear_post_at` → `_publish_game_updated` NOT called. Mark xfail; implement; confirm green.
  4. `test_update_game_publishes_updated_when_already_announced` — game has `message_id` set → `_publish_game_updated` IS called (existing behavior). Confirm this test already passes or write it to document the behavior.
- **Files**:
  - `services/api/services/games.py` — `_update_game_fields` (line 1274), `update_game` (line 1919)
- **Changes to `_update_game_fields`**: add handling for `update_data.post_at` — if non-None and `clear_post_at` is False, set `game.post_at = update_data.post_at`. (The clear path is async and handled in `update_game` directly.)
- **Changes to `update_game`** (after `_update_game_fields` call, before `_publish_game_updated`):

  ```python
  # Handle post_at update paths
  if update_data.clear_post_at and game.post_at is not None and game.message_id is None:
      game.post_at = None
      await self._setup_game_schedules(game, ...)
      await self._publish_game_created(game, channel_config)
      return game  # No need to also fire _publish_game_updated

  # Guard: only update Discord embed if announcement has already posted
  if game.message_id is not None:
      await self._publish_game_updated(game)
  ```

- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 165–195) — `update_game` guard and clear-post_at patterns
- **Success**:
  - `clear_post_at=True` on a pre-announced game sets `game.post_at = None`, calls schedules and publish-created
  - Updating `post_at` to a new future time only changes the field; bot loop auto-detects via NOTIFY
  - `_publish_game_updated` is suppressed when `game.message_id` is `None`

### Task 3.3: Guard `join_game` route — return 404 for pre-announced games

- **TDD step**: Write xfail test `test_join_game_returns_404_for_pre_announced_game` — mock game has future `post_at` and no `message_id`; route should raise `HTTPException(status_code=404)`. Mark xfail; implement; confirm green.
- **Files**:
  - `services/api/routes/games.py` — `join_game` route (line 707), after `game = await game_service.get_game(game_id)` check
- **Change** (insert after the existing 404-if-not-found check):

  ```python
  from datetime import UTC, datetime  # already imported

  if (
      game.post_at is not None
      and game.post_at > datetime.now(UTC)
      and game.message_id is None
  ):
      raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Game not found")
  ```

- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 204–210) — `join_game` guard pattern
- **Success**:
  - Attempting to join a game with future `post_at` and no `message_id` returns 404
  - Joining a game whose `post_at` has passed (or is None) succeeds as before

### Task 3.4: Filter pending-announcement games in `list_games` route for non-managers

- **TDD step**: Write xfail test `test_list_games_hides_pending_announcement_from_non_manager` — game has future `post_at`; non-manager user → game excluded from response. Also `test_list_games_shows_pending_announcement_to_manager`. Mark xfail; implement; confirm green.
- **Files**:
  - `services/api/routes/games.py` — `list_games` route authorization loop (lines 449–475)
- **Change** (inside the `for game in games:` loop, after `verify_game_access` succeeds):
  ```python
  # Hide pre-announced games from non-managers
  if (
      game.post_at is not None
      and game.post_at > datetime.now(UTC)
      and game.message_id is None
  ):
      is_manager = await permissions_deps.can_manage_game(
          game_host_id=game.host.discord_id,
          guild_id=game.guild.guild_id,
          current_user=current_user,
          role_service=role_service,
          db=game_service.db,
      )
      if not is_manager:
          continue
  authorized_games.append(game)
  ```
  Move the `authorized_games.append(game)` inside this block (currently it follows `continue` on exception).
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 186–203) — visibility filter pattern
- **Success**:
  - Non-manager cannot see pending-announcement games in list
  - Host/bot-manager can see pending-announcement games
  - Games with `post_at=None` or already announced (`message_id` set) are unaffected

### Task 3.5: Integration tests for join guard and list visibility

Write integration tests against the real database (no bot) to confirm the API-level guards added in Tasks 3.3 and 3.4 behave correctly end-to-end through the HTTP layer.

- **Files**:
  - `tests/integration/test_deferred_game_announcement.py` — new file
- **Tests**:
  1. `test_join_game_returns_404_for_pending_announcement` — create a game row in the DB with `post_at = now + 1 hour` and `message_id = NULL`; call the join endpoint as a non-host user; assert HTTP 404.
  2. `test_join_game_succeeds_after_announcement_posted` — same game but with `message_id` set (simulating the bot having announced it); assert join succeeds (HTTP 200/201).
  3. `test_list_games_hides_pending_from_non_manager` — create a pending-announcement game; list games as a regular user; assert the game is absent from the response.
  4. `test_list_games_shows_pending_to_host` — same game; list as the game host; assert the game appears in the response.
- **Test setup note**: Insert the game row directly via the admin DB session (bypassing service logic) so this test is not coupled to the create path; set `post_at` and leave `message_id` NULL.
- **Dependencies**: Phase 3 Tasks 3.3 and 3.4 complete
- **Success**:
  - All four tests pass against the real DB in the integration environment

---

## Phase 4: AnnouncementLoop bot task

### Task 4.1: Create `services/bot/announcement_loop.py` with asyncpg LISTEN + `SKIP_LOCKED` query loop

- **TDD steps**:
  1. Write xfail test `test_announcement_loop_process_due_announces_due_games` — mock DB with a due game (past `post_at`, no `message_id`); assert `_announce` is called. Mark xfail; implement; confirm green.
  2. Write xfail test `test_announcement_loop_skips_already_announced_games` — game has `message_id` set; assert `_announce` is NOT called. Mark xfail; implement; confirm green.
  3. Write xfail test `test_announcement_loop_announce_posts_to_discord_and_sets_message_id` — mock Discord channel `send`; assert `game.message_id` set and `_setup_game_schedules` called. Mark xfail; implement; confirm green.
- **Files**:
  - `services/bot/announcement_loop.py` — new file
- **Class structure** (mirrors `MessageRefreshListener`):

  ```python
  class AnnouncementLoop:
      MAX_TIMEOUT = 3600  # seconds; cap sleep when no games due

      def __init__(self, db_url: str, bot: "GameSchedulerBot") -> None:
          self._db_url = db_url
          self._bot = bot
          self._wake_event = asyncio.Event()

      async def start(self) -> None:
          conn = await asyncpg.connect(self._db_url)
          await conn.add_listener("game_announcement_changed", self._on_notify)
          while True:
              await self._process_due()
              next_due = await self._next_due_time()
              if next_due:
                  wait = max(0, (next_due - utc_now()).total_seconds())
              else:
                  wait = self.MAX_TIMEOUT
              try:
                  await asyncio.wait_for(self._wake_event.wait(), timeout=wait)
              except asyncio.TimeoutError:
                  pass
              self._wake_event.clear()

      def _on_notify(self, conn, pid, channel, payload) -> None:
          self._wake_event.set()

      async def _next_due_time(self) -> datetime | None:
          async with get_db_session() as db:
              result = await db.execute(
                  select(func.min(GameSession.post_at)).where(
                      GameSession.post_at.isnot(None),
                      GameSession.post_at > utc_now(),
                      GameSession.message_id.is_(None),
                      GameSession.status == GameStatus.SCHEDULED.value,
                  )
              )
              return result.scalar_one_or_none()

      async def _process_due(self) -> None:
          async with get_db_session() as db:
              result = await db.execute(
                  select(GameSession)
                  .where(
                      GameSession.post_at.isnot(None),
                      GameSession.post_at <= utc_now(),
                      GameSession.message_id.is_(None),
                      GameSession.status == GameStatus.SCHEDULED.value,
                  )
                  .with_for_update(skip_locked=True)
                  .options(selectinload(...))  # load relationships needed for announce
              )
              for game in result.scalars():
                  await self._announce(db, game)

      async def _announce(self, db: AsyncSession, game: GameSession) -> None:
          if game.message_id is not None:
              return  # double-check inside row lock
          # Re-use the bot's existing handler logic for creating the Discord message
          handlers = self._bot.event_handlers
          channel = await self._bot._get_bot_channel(game.channel.channel_id)
          content, embed, view = await handlers._create_game_announcement(game)
          message = await channel.send(content=content, embed=embed, view=view)
          game.message_id = str(message.id)
          await db.commit()
          # Set up reminders/status schedules now that the announcement is live
          game_service = GameService(db, ...)
          await game_service._setup_game_schedules(
              game,
              game.reminder_minutes or [],
              game.expected_duration_minutes,
          )
  ```

- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 98–146) — `AnnouncementLoop` class pattern
- **Dependencies**:
  - Phase 1 (model has `post_at`), Phase 2 (`_persist_and_publish` skips schedules when deferred)

### Task 4.2: Wire `AnnouncementLoop` into `bot.on_ready` under `_announcement_loop_started` hasattr guard

- **TDD step**: Write xfail test `test_on_ready_starts_announcement_loop` in `tests/unit/bot/test_bot_ready.py` — mirrors existing `test_on_ready_starts_message_refresh_listener` (line 226). Mark xfail; implement; confirm green. Also write `test_on_ready_does_not_restart_announcement_loop` (mirrors line 239).
- **Files**:
  - `services/bot/bot.py` — `on_ready` (line 174); imports section (line 44)
- **Import addition** (near line 44):
  ```python
  from services.bot.announcement_loop import AnnouncementLoop
  ```
- **`on_ready` addition** (after the `_refresh_listener_started` block, around line 220):
  ```python
  if not hasattr(self, "_announcement_loop_started"):
      self._announcement_loop_started = True
      self._announcement_loop_task = asyncio.create_task(
          AnnouncementLoop(self.config.database_url, self).start()
      )
      logger.info("Started announcement loop task")
  ```
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 248–257) — startup guard pattern
- **Success**:
  - Bot starts `AnnouncementLoop` task exactly once on connect
  - Reconnects do not spawn a second loop

### Task 4.3: E2e tests for deferred announcement flow

Write e2e tests that exercise the full stack (API + bot + real Discord). Use `post_at = now + 30 seconds` to give the stack enough time to start up without making the test excessively slow, while being far enough in the future to avoid flakiness from slow test setup.

- **Files**:
  - `tests/e2e/test_deferred_game_announcement.py` — new file
- **Tests**:
  1. `test_deferred_game_not_visible_before_announcement` — create a game with `post_at = now + 30s`; immediately list games as a non-host; assert game is absent.
  2. `test_deferred_game_announces_at_post_at_time` — same game; wait using `wait_for_game_message_id` with a timeout long enough to cover the 30s delay plus bot processing (use `TimeoutType.LONG` or equivalent ~90s timeout); assert `message_id` is set and the Discord message exists in the channel.
  3. `test_deferred_game_visible_after_announcement` — after `message_id` is confirmed set, list games as a non-host; assert the game now appears.
  4. `test_clear_post_at_triggers_immediate_announcement` — create a game with `post_at = now + 30s`; immediately PATCH the game with `clear_post_at=true`; wait for `message_id` to be set (should arrive within normal announcement timeout, not 30s); assert the Discord message is posted.
- **Timing note**: The 30-second `post_at` offset is the minimum recommended value. Do not use shorter offsets — the bot needs time to start its LISTEN connection and the test runner needs time to reach the assertion before `post_at` passes.
- **Dependencies**: Phase 4 Tasks 4.1 and 4.2 complete (bot runs `AnnouncementLoop`)
- **Success**:
  - All four tests pass in the full e2e environment
  - Existing `test_game_announcement.py` tests continue to pass (no `post_at` = immediate path unchanged)

---

## Phase 5: Frontend — `post_at` field and pending-announcement badge

### Task 5.1: Add `post_at` to `GameSession` TypeScript interface and API call helpers

- **TDD step**: Write xfail vitest test that `GameSession.post_at` is `string | null`. Mark xfail; implement; confirm green.
- **Files**:
  - `frontend/src/types/index.ts` — `GameSession` interface (line 86)
- **Change**: add `post_at: string | null;` after `scheduled_at`
- **API helpers**: if any helper serializes `GameSession` to form data, add `post_at` serialization
- **Success**:
  - TypeScript compiles with no errors
  - `post_at` is available on `GameSession` objects returned from the API

### Task 5.2: Add `post_at` DateTimePicker to `CreateGame` and `EditGame` forms

- **TDD steps**:
  1. Write xfail test in `CreateGame.test.tsx` that the form renders a "Schedule announcement" datetime field. Mark xfail; implement; confirm green.
  2. Write xfail test in `EditGame.test.tsx` that the form renders the field prepopulated when `game.post_at` is set. Mark xfail; implement; confirm green.
- **Files**:
  - `frontend/src/pages/CreateGame.tsx` — add optional `post_at` datetime-local input
  - `frontend/src/pages/EditGame.tsx` — add optional `post_at` datetime-local input; pre-populate from game data; add "Clear (announce now)" checkbox/button that sends `clear_post_at=true`
- **UX**:
  - Field label: "Schedule announcement (optional)"
  - Placeholder/helper: "Leave empty to post immediately"
  - Constraint: `max` attribute set to `scheduled_at` value so the browser prevents selecting after game start
  - Clear path: a "Post immediately" checkbox or button that sends `clear_post_at=true` when checked and the game hasn't been announced yet
- **Success**:
  - Submitting `CreateGame` without `post_at` behaves as today
  - Submitting with a future `post_at` sends the field in the form POST

### Task 5.3: Add pending-announcement badge to `MyGames` and `GameDetails`

- **TDD steps**:
  1. Write xfail test in `MyGames.test.tsx` that a game with `post_at` set and `message_id=null` renders a "Pending announcement" badge. Mark xfail; implement; confirm green.
  2. Write xfail test in `GameDetails.test.tsx` that the badge is shown with the timestamp. Mark xfail; implement; confirm green.
- **Files**:
  - `frontend/src/pages/MyGames.tsx` — add badge render when `game.post_at && !game.message_id`
  - `frontend/src/pages/GameDetails.tsx` — same condition; show "Announcement scheduled for [formatted timestamp]"
- **Badge content**: "Scheduled announcement: [human-readable timestamp]"
- **Research reference**: #file:../research/20260530-01-deferred-game-announcement-research.md (Lines 265–303) — success criteria for visibility
- **Success**:
  - Badge appears only when `post_at` is set and `message_id` is null
  - Badge shows the correctly formatted timestamp

---

## Dependencies

- asyncpg (already present in bot service)
- Alembic (existing tooling)
- Phase ordering is strict: 1 → 2 → 3 → 4 → 5; each phase is independently committable

## Success Criteria

- All existing unit tests pass after each phase
- Creating with `post_at=None` is identical to today's behavior (no regression)
- Creating with future `post_at` defers Discord announcement and schedule setup
- `AnnouncementLoop` fires deferred announcements and then calls `_setup_game_schedules`
- Non-managers cannot see or join pre-announced games via the API
