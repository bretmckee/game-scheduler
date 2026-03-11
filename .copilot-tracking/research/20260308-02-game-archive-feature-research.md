<!-- markdownlint-disable-file -->

# Task Research Notes: Game Announcement Archive Feature

## Research Executed

### File Analysis

- `shared/models/template.py`
  - `GameTemplate` has distinct **locked fields** (manager-only: `channel_id`, `notify_role_ids`, `allowed_player_role_ids`, `allowed_host_role_ids`) and **pre-populated fields** (host-editable: `max_players`, `reminder_minutes`, etc.)
  - Archive config belongs in locked fields — it is a guild admin concern, not per-game

- `shared/models/game.py`
  - `GameSession` copies locked fields from template at creation time (`channel_id`, `notify_role_ids`, `allowed_player_role_ids`)
  - New archive fields must also be copied at game creation

- `services/api/services/games.py` — `_build_game_session`
  - Explicitly copies `channel_id = template.channel_id` and `notify_role_ids = template.notify_role_ids`
  - Archive fields follow the same copy pattern

- `services/api/services/games.py` — `_create_game_status_schedules`
  - Creates `GameStatusSchedule` rows for `IN_PROGRESS` and `COMPLETED` at game creation
  - ARCHIVED schedule is **not** created here — it cannot be scheduled until the game actually completes (the actual completion time may differ from the scheduled time if e.g. duration was wrong)

- `services/bot/events/handlers.py` — `_handle_status_transition_due`
  - Handles all status transitions uniformly
  - After transitioning to COMPLETED, if `archive_delay_seconds` is set, this handler creates the ARCHIVED `GameStatusSchedule` row
  - This is the correct trigger point — the handler already has the game loaded, knows the actual transition time, can calculate `now + archive_delay_seconds`

- `services/bot/events/handlers.py` — `_handle_game_cancelled`
  - No archive action for cancelled games (per spec)
  - Will be extended separately to delete the announcement

- `shared/models/game_status_schedule.py`
  - Has a `UniqueConstraint("game_id", "target_status")` — one schedule row per game per target status
  - ARCHIVED transition fits cleanly; row is created after COMPLETED fires

- `shared/schemas/template.py`
  - `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, `TemplateListItem` all need two new fields
  - `TemplateResponse` and `TemplateListItem` include `channel_name` (resolved via Discord API) — `archive_channel_name` follows the same pattern

- `services/api/routes/templates.py` — `build_template_response`
  - Calls `discord_client_module.fetch_channel_name_safe(template.channel_id, ...)` for the announcement channel
  - Must also call it for `template.archive_channel_id` when present

- `services/api/routes/templates.py` — `create_template`
  - Passes explicit kwargs to `template_svc.create_template()`
  - Must add `archive_delay_seconds` and `archive_channel_id`

- `alembic/versions/` — most recent migration is `f3a2c1d8e9b7`
  - New migration must follow this as `down_revision`

### Code Search Results

- `_resolve_template_fields`
  - Archive fields are **not** host-editable — they are not resolved from game request data
  - They are copied directly in `_build_game_session` alongside `channel_id`

- `GameStatus` (consolidation follow-up required)
  - The consolidation work did **not** add the archive-related enum value or transitions
  - This feature must add `ARCHIVED = "ARCHIVED"` to the canonical `GameStatus` in
    `shared/utils/status_transitions.py`
  - Also add/move `display_name` into the canonical enum and include `"ARCHIVED": "Archived"`
  - Update `is_valid_transition`: `COMPLETED → ARCHIVED` is valid; `CANCELLED → ARCHIVED` is not

### External Research

- Discord Message API
  - No native "move message" endpoint exists
  - Archive flow: POST new message to archive channel → DELETE original message
  - `discord.py`: `channel.send(content, embed, view)` then `message.delete()` on original
  - Buttons must be disabled/absent on archive post — already handled since ARCHIVED status renders without interactive view

### Project Conventions

- Duration fields: use `_seconds` suffix (matches user's direction; store as `Integer` seconds, `NULL` = never)
- Channel FK fields: `ForeignKey("channel_configurations.id")`, nullable, `String(36)`
- Locked template fields flow: template → `_build_game_session` → `GameSession` column
- RLS migrations: existing pattern adds policies for each table; no new RLS needed (new columns inherit table-level RLS)

## Key Discoveries

### Data Model Changes

**`GameTemplate` — new locked fields:**

```python
archive_delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
archive_channel_id: Mapped[str | None] = mapped_column(
    ForeignKey("channel_configurations.id"), nullable=True
)
# Relationship (optional, for eager loading):
archive_channel: Mapped["ChannelConfiguration | None"] = relationship(
    "ChannelConfiguration", foreign_keys=[archive_channel_id]
)
```

`GameTemplate.channel` already uses a plain `relationship("ChannelConfiguration")` without `foreign_keys` specified — since there will now be two FKs to `channel_configurations`, **both** relationships need explicit `foreign_keys` to avoid SQLAlchemy ambiguity.

**`GameSession` — same two fields copied from template:**

```python
archive_delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
archive_channel_id: Mapped[str | None] = mapped_column(
    ForeignKey("channel_configurations.id"), nullable=True
)
```

`GameSession` also has two FKs to `channel_configurations` (`channel_id` and `archive_channel_id`) — same `foreign_keys` fix needed on both relationships.

### State Machine (after adding ARCHIVED to canonical GameStatus)

```
SCHEDULED → IN_PROGRESS → COMPLETED ──→ ARCHIVED
          ↘              ↘
           CANCELLED      CANCELLED
```

`is_valid_transition` update (part of this feature):

```python
valid_transitions = {
    GameStatus.SCHEDULED: [GameStatus.IN_PROGRESS, GameStatus.CANCELLED],
    GameStatus.IN_PROGRESS: [GameStatus.COMPLETED, GameStatus.CANCELLED],
    GameStatus.COMPLETED: [GameStatus.ARCHIVED],
    GameStatus.CANCELLED: [],
    GameStatus.ARCHIVED: [],
}
```

### Archive Schedule Creation

In `_handle_status_transition_due`, after the COMPLETED transition commits:

```python
if (
    transition_event.target_status == GameStatus.COMPLETED
    and game.archive_delay_seconds is not None
):
    archive_time = utc_now() + datetime.timedelta(seconds=game.archive_delay_seconds)
    async with get_db_session() as db2:
        archive_schedule = GameStatusSchedule(
            id=str(uuid.uuid4()),
            game_id=game.id,
            target_status=GameStatus.ARCHIVED.value,
            transition_time=archive_time,
            executed=False,
        )
        db2.add(archive_schedule)
        await db2.commit()
```

Note: `archive_delay_seconds=0` is a valid value meaning "archive immediately after completion."

### New Bot Handler: `_handle_archive`

Registered in `EventHandlers.__init__` as `EventType.GAME_STATUS_TRANSITION_DUE` already handles all transitions via `_handle_status_transition_due`. No new event type is needed — the ARCHIVED status transition fires through the existing machinery. The `_refresh_game_message` call at the end of `_handle_status_transition_due` will need to be augmented: after refreshing, if the new status is ARCHIVED, call `_archive_game_announcement`.

```python
async def _archive_game_announcement(self, game: GameSession) -> None:
    """Delete announcement from active channel; repost to archive channel if configured."""
    if not game.message_id or not game.channel:
        return

    channel = await self._get_bot_channel(game.channel.channel_id)
    if not channel:
        return

    # Post to archive channel first (before deleting source)
    if game.archive_channel_id:
        archive_channel_config = game.archive_channel
        if archive_channel_config:
            archive_channel = await self._get_bot_channel(archive_channel_config.channel_id)
            if archive_channel:
                content, embed, _ = await self._create_game_announcement(game)
                # No view — archived announcements have no interactive buttons
                await archive_channel.send(content=content, embed=embed)

    # Delete original announcement
    try:
        message = await channel.fetch_message(int(game.message_id))
        await message.delete()
    except discord.NotFound:
        logger.warning("Original announcement not found for archive deletion: %s", game.message_id)
```

### Alembic Migration

New migration file: `YYYYMMDD_add_archive_fields.py` with `down_revision = "f3a2c1d8e9b7"`.

```python
def upgrade() -> None:
    op.add_column("game_templates",
        sa.Column("archive_delay_seconds", sa.Integer(), nullable=True))
    op.add_column("game_templates",
        sa.Column("archive_channel_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_game_templates_archive_channel_id",
        "game_templates", "channel_configurations",
        ["archive_channel_id"], ["id"], ondelete="SET NULL"
    )
    op.add_column("game_sessions",
        sa.Column("archive_delay_seconds", sa.Integer(), nullable=True))
    op.add_column("game_sessions",
        sa.Column("archive_channel_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_game_sessions_archive_channel_id",
        "game_sessions", "channel_configurations",
        ["archive_channel_id"], ["id"], ondelete="SET NULL"
    )
```

`ondelete="SET NULL"` — if the archive channel is removed from the system, games/templates gracefully fall back to delete-only behavior.

### Schema Changes

**`TemplateCreateRequest` / `TemplateUpdateRequest`** — add to locked fields section:

```python
archive_delay_seconds: int | None = Field(
    None, ge=0, description="Seconds after completion to archive announcement (None = never)"
)
archive_channel_id: str | None = Field(
    None, description="Channel UUID to post archived announcement (None = delete only)"
)
```

**`TemplateResponse` / `TemplateListItem`** — add:

```python
archive_delay_seconds: int | None = Field(None, description="Archive delay in seconds")
archive_channel_id: str | None = Field(None, description="Archive channel UUID")
archive_channel_name: str | None = Field(None, description="Archive channel name (resolved)")
```

**Frontend UX note**: The API stores and accepts raw seconds. The frontend should present a compound "days / hours / minutes" selector and convert to/from seconds. Example: 2 days = 172800 seconds. The API never sees days/hours/minutes — that is purely a presentation concern.

### `build_template_response` in routes/templates.py

```python
archive_channel_name = None
if template.archive_channel_id:
    archive_channel_name = await discord_client_module.fetch_channel_name_safe(
        template.archive_channel_id, discord_client
    )
```

### `_build_game_session` in services/games.py

Add to the copy-from-template block (alongside `channel_id = template.channel_id`):

```python
archive_delay_seconds = template.archive_delay_seconds
archive_channel_id = template.archive_channel_id
```

And pass to `GameSession(...)` constructor.

### `create_template` route

Add `archive_delay_seconds=request.archive_delay_seconds` and `archive_channel_id=request.archive_channel_id` to the `create_template(...)` call.

## Testing

### Unit Tests

**`tests/services/bot/events/test_handlers.py`** — existing file, extend with:

- `test_handle_status_transition_creates_archived_schedule_when_delay_set` — mock a COMPLETED transition on a game with `archive_delay_seconds=3600`; assert a `GameStatusSchedule` row for `ARCHIVED` is inserted at approximately `now + 3600s`
- `test_handle_status_transition_no_archived_schedule_when_delay_none` — same but `archive_delay_seconds=None`; assert no ARCHIVED schedule row created
- `test_archive_game_announcement_deletes_original` — mock `channel.fetch_message` and `message.delete`; assert delete called; no archive channel configured
- `test_archive_game_announcement_posts_to_archive_channel` — configure `archive_channel_id`; assert `archive_channel.send` called with embed, no interactive view; assert original message deleted
- `test_archive_game_announcement_no_message_id_is_noop` — game with `message_id=None`; assert no Discord calls made

**`tests/services/api/services/test_games.py`** — existing file, extend with:

- `test_build_game_session_copies_archive_fields_from_template` — template with `archive_delay_seconds=7200`, `archive_channel_id="some-uuid"`; assert game session has matching values
- `test_build_game_session_archive_fields_null_when_template_unset` — template without archive fields; assert game session fields are `None`

**`tests/shared/models/test_game_status_schedule.py`** — verify ARCHIVED is accepted as a valid `target_status` value (no constraint change required, column is plain `String(20)`)

### Integration Tests

**`tests/services/api/routes/test_templates.py`** or new `tests/integration/test_template_archive_fields.py`:

- `test_create_template_with_archive_fields` — POST `/guilds/{id}/templates` with `archive_delay_seconds=3600` and a valid `archive_channel_id`; assert 201, response contains both fields
- `test_update_template_archive_fields` — PUT `/templates/{id}` to set then clear `archive_delay_seconds`; assert round-trips correctly
- `test_create_template_archive_delay_zero` — `archive_delay_seconds=0` is valid (immediate archive)
- `test_create_template_archive_channel_null_delay_not_null` — `archive_channel_id=None`, `archive_delay_seconds=3600`; valid (delete-only mode)

**`tests/integration/test_games_archive_fields.py`** (new):

- `test_game_creation_copies_archive_fields_from_template` — create game from template with archive fields set; assert game row in DB has matching `archive_delay_seconds` and `archive_channel_id`
- `test_game_creation_null_archive_fields_when_template_unset` — template without archive fields; game row fields are `NULL`

### E2E Tests

**`tests/e2e/test_game_archive.py`** (new file):

The E2E test environment needs a second channel in the same guild for archive testing. Add `DISCORD_ARCHIVE_CHANNEL_ID` to the e2e environment (equivalent of `DISCORD_GUILD_A_CHANNEL_ID`), registered in `channel_configurations` by the init service, and exposed through a `discord_archive_channel_id` fixture in `conftest.py`.

Pattern mirrors `tests/e2e/test_game_status_transitions.py`:

```python
@pytest.mark.timeout(360)
@pytest.mark.asyncio
async def test_game_archived_after_completion_deletes_announcement(
    authenticated_admin_client, admin_db, discord_helper,
    discord_channel_id, discord_archive_channel_id,
    discord_guild_id, discord_user_id, synced_guild, test_timeouts,
):
    """
    E2E: After COMPLETED transition, ARCHIVED transition deletes announcement.

    Verifies:
    - Game created with archive_delay_seconds=0 on template
    - COMPLETED transition fires normally
    - ARCHIVED schedule row created immediately after COMPLETED
    - ARCHIVED transition fires; original message deleted from active channel
    - If archive_channel configured: button-free copy appears in archive channel
    """
```

Test steps:

1. Update default test template to set `archive_delay_seconds=0` and `archive_channel_id` pointing to archive channel
2. Create game scheduled 1 minute in future with 1 minute duration
3. Wait for COMPLETED status in DB (same as existing status transition test)
4. Assert ARCHIVED row created in `game_status_schedule`
5. Wait for ARCHIVED status in DB using `wait_for_db_condition`
6. Assert original message deleted from active channel — use `discord_helper.wait_for_message_deleted` (or fetch and assert `None`)
7. Assert archive message posted to archive channel — use `discord_helper.wait_for_message` with a check that the embed footer contains `"Archived"` and there are no interactive components

**`tests/e2e/helpers/discord.py`** — likely needs a `wait_for_message_deleted` helper that polls `fetch_message` until `discord.NotFound` is raised, with timeout.

**Separate test for delete-only mode** (no archive channel):

```python
@pytest.mark.timeout(360)
@pytest.mark.asyncio
async def test_game_archived_delete_only_no_repost(
    ...
):
    """E2E: archive_delay_seconds set, archive_channel_id=None — message deleted, no repost."""
```

### Test Infrastructure Notes

- The archive e2e test is long-running (~4-5 min) same as the existing status transition test; use `@pytest.mark.timeout(360)` to allow margin
- `archive_delay_seconds=0` is the right value for e2e tests — no artificial wait beyond what the existing COMPLETED transition already requires
- The template archive fields need to be set **before** game creation in the test; update the default template via API at test start, then restore at teardown (or use a dedicated test template)
- `DISCORD_ARCHIVE_CHANNEL_ID` env var must be documented in `docs/developer/TESTING.md` alongside the existing Discord env var setup instructions

## Implementation Guidance

- **Objectives**: Let guild admins configure per-template archive behavior; automatically move completed game announcements to an archive channel (or delete them) after a configurable delay
- **Key Tasks** (in order):
  1. Alembic migration — add 4 new nullable columns
  2. `shared/models/template.py` — add two fields + fix `foreign_keys` on channel relationships
  3. `shared/models/game.py` — add two fields + fix `foreign_keys` on channel relationship
  4. `shared/utils/status_transitions.py` — add `COMPLETED → ARCHIVED` to valid transitions (consolidation phase already added `ARCHIVED` to enum)
  5. `shared/schemas/template.py` — extend all four schema classes
  6. `services/api/routes/templates.py` — `build_template_response`, `create_template` route
  7. `services/api/services/games.py` — `_build_game_session` (copy archive fields from template)
  8. `services/bot/events/handlers.py` — schedule archive after COMPLETED; implement `_archive_game_announcement`; call it after status transition to ARCHIVED
  9. Unit tests for new bot handler logic and archive field copying
  10. Integration tests for template/game CRUD with archive fields
  11. E2E test `tests/e2e/test_game_archive.py` with `DISCORD_ARCHIVE_CHANNEL_ID` env var
  12. Update `docs/developer/TESTING.md` with new env var
- **Dependencies**:
  - Consolidation phase (doc 01) must be complete first
  - `archive_channel_id` must reference a channel already registered in `channel_configurations` — guild admins must add the archive channel to the system before assigning it to a template (same requirement as the announcement channel)
  - E2E tests require a second Discord channel in the test guild configured as `DISCORD_ARCHIVE_CHANNEL_ID`
- **Success Criteria**:
  - Templates can be created/updated with `archive_delay_seconds` and `archive_channel_id`
  - New games copy those fields from their template
  - After a COMPLETED transition, a `GameStatusSchedule` ARCHIVED row is created iff `archive_delay_seconds IS NOT NULL`
  - When ARCHIVED fires: original announcement is deleted; if `archive_channel_id` is set, a button-free copy is posted there
  - `archive_delay_seconds=0` archives immediately after completion
  - `archive_delay_seconds=NULL` leaves the announcement in place indefinitely (today's behavior)
  - `archive_channel_id=NULL` with a non-null delay: delete only, no repost
  - All unit, integration, and e2e tests pass
