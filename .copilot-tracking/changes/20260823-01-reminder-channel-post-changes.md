# Changes: Move Game Reminders from DMs to Location Channel/Thread Posts

## Phase 1: Location Channel Resolution Helper

### Task 1.1: Unit tests for `extract_single_channel_id` (RED)

- Added import of `extract_single_channel_id` plus 7 behavioral test cases to
  `tests/unit/shared/utils/test_discord_utils.py`:
  - `None` input → `None`
  - Empty string → `None`
  - Plain text with no mention → `None`
  - Exactly one `<#id>` token → ID returned
  - One mention with surrounding prose → ID returned
  - Two mentions → `None` (ambiguous)
  - Unresolved `#name` mention → `None` (only snowflake tokens count)

### Task 1.2: Implement `extract_single_channel_id` (GREEN)

- Added module-level compiled regex `_CHANNEL_SNOWFLAKE_TOKEN = re.compile(r"<#(\d+)>")`
  and the pure helper `extract_single_channel_id(where: str | None) -> str | None`
  to `shared/utils/discord.py`. Returns the captured channel ID only when exactly
  one `<#id>` token is present; otherwise `None`.
- Added `import re` to the module imports.

**Verification**: `uv run pytest tests/unit` — 2525 passed; `uv run mypy shared/ services/` — clean.

## Phase 2: Channel-Post Reminder Delivery

### Task 2.1: Extend `create_notification_embed` for optional host + jump link

- Changed signature to `create_notification_embed(game_title, scheduled_at, host_id: str | None, time_until, jump_url: str | None = None)` in `services/bot/formatters/game_message.py`. The Host field is now added only when `host_id` is truthy; a new `🔗 View Game` field is added only when `jump_url` is truthy.
- Added 4 real-embed field-level tests to `tests/unit/services/bot/formatters/test_game_message.py` (no host → no Host field; host present → `<@id>` value; jump URL → View Game field; default → no View Game field). Existing mocked tests pass unchanged.

### Task 2.2: Unit tests for `_post_reminder_to_channel` and the delivery branch (RED)

- Added `_post_reminder_to_channel` stub (`raise NotImplementedError`) to `services/bot/events/handlers.py` so tests could reference it (forward-import prohibition).
- Added 8 unit tests plus two small helpers (`_reminder_flow_patches`, `_make_participants`) to `tests/unit/services/bot/events/test_handlers_game_reminder.py`:
  - `_post_reminder_to_channel`: success (content mentions confirmed + host, embed title/fields/jump link, allowed_mentions users-only), Forbidden → False, NotFound → False, no-host omits host mention
  - `_handle_notification_due` branches: channel-post success (1 waitlist DM only), post-failed fallback (full fan-out of 4), no-channel fallback (full fan-out, no post), ambiguous location (full fan-out, no lookup/post)

### Task 2.3: Implement `_post_reminder_to_channel` and wire the delivery branch (GREEN)

- Implemented `_post_reminder_to_channel` in `services/bot/events/handlers.py`: builds the reminder embed via `GameMessageFormatter.create_notification_embed` (with jump URL), mentions confirmed participants + host as `<@id>` tokens, posts once with `allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)`; returns False on `discord.Forbidden` / `discord.NotFound`.
- Wired the hybrid branch into `_handle_game_reminder`: resolve a single channel ID from `game.where` via `extract_single_channel_id`, look it up with `_get_bot_channel`; on successful post DM only the first waitlisted participant and return; otherwise fall back to the existing full DM fan-out (confirmed + first waitlisted + host).
- Added imports: `GameMessageFormatter`, `format_discord_timestamp`, `extract_single_channel_id`.

### Task 2.4: Verify existing flow tests still pass via fallback path

- All six pre-existing `_handle_notification_due` flow tests pass unchanged (`where=None` → full DM fan-out fallback, identical counts/kwargs).

**Verification**: `uv run pytest tests/unit` — 2537 passed; `uv run mypy shared/ services/` — clean.

## Phase 3: E2E Test Rewrite

### Task 3.1: Add `wait_for_channel_message` helper

- Added `wait_for_channel_message(channel_id, predicate, timeout=150, interval=5.0, limit=15, description)` to `tests/e2e/helpers/discord.py`, polling channel history via the existing `get_recent_messages` + `wait_for_condition` utilities (mirrors `wait_for_dm_matching`).

### Task 3.2: Rewrite reminder e2e test for hybrid delivery

- Renamed `test_game_reminder_dm_delivery` → `test_game_reminder_hybrid_delivery` in `tests/e2e/test_game_reminder.py`. The game is now created with `where=<#discord_channel_id>` (single-channel mention), `max_players="1"`, and Player A + the test user as initial participants so Player A is confirmed and the test user is waitlisted (same pattern as `test_waitlist_promotion.py`).
- Assertions: a `🔔 Game Reminder` embed post appears in the location channel whose description contains the game title and whose content mentions `<@player_a_id>`; the waitlisted test user still receives a `DMType.REMINDER` DM.
- Updated module docstring and test docstring to describe hybrid delivery.

**Verification**: `uv run mypy shared/ services/` — clean; rewritten test collects cleanly (`pytest --collect-only`). Full e2e run pending per `.github/instructions/test-execution.instructions.md`.

## Phase 4: Backend "Always send reminders as DMs" Flag

### Task 4.1: Migration + model column for `reminders_as_dms`

- Created `alembic/versions/07db1045a251_add_reminders_as_dms.py` via
  `uv run alembic revision`, chained from head `bf79aeffb6b0`. `upgrade()` adds
  `game_sessions.reminders_as_dms BOOLEAN NOT NULL DEFAULT false`;
  `downgrade()` drops the column (mirrors `20260321_add_rewards_fields.py`).
- Added mapped column to `GameSession` in `shared/models/game.py` next to
  `remind_host_rewards`: `Mapped[bool] = mapped_column(Boolean, nullable=False,
default=False, server_default=text("false"))`.
- Verified single alembic head is now `07db1045a251`; offline DDL generation
  (`alembic upgrade bf79aeffb6b0:07db1045a251 --sql`) emits exactly
  `ALTER TABLE game_sessions ADD COLUMN reminders_as_dms BOOLEAN DEFAULT false
NOT NULL;`. Live-DB application happens with the integration environment.

### Task 4.2: Schemas — create/update/response fields

- `GameCreateRequest`: added `reminders_as_dms: bool | None` Field after
  `remind_host_rewards` (None → off; no template default exists).
- `GameUpdateRequest`: added `reminders_as_dms: bool | None = None` (absent =
  no change).
- `GameResponse`: added `reminders_as_dms: bool` with `default=False`.

### Task 4.3: API routes + service wiring with unit tests (RED→GREEN)

**RED** — 5 new unit tests written first and verified as failing/expected-failure:

- `tests/unit/services/api/services/test_games_service.py`:
  - `_build_game_session` sets `reminders_as_dms=True` from request (strict
    xfail RED — kwarg not yet accepted by the constructor call)
  - `_build_game_session` defaults to `False` when absent (strict xfail RED —
    unflushed instance reads `None`, proving explicit wiring is required rather
    than relying on the column-level SQLAlchemy default)
- `tests/unit/services/api/services/test_update_game_fields_helpers.py`:
  - `_update_remaining_fields` sets `game.reminders_as_dms = True` from update
    data (strict xfail RED)
  - `_update_remaining_fields` leaves the flag untouched when the field is
    None (regression guard, passes in both phases)
- `tests/unit/services/test_system_clone_for_recurrence.py`: recurrence clone
  carries `reminders_as_dms` from source game (strict xfail RED; fixture now
  sets `source_game.reminders_as_dms = True`)

**GREEN** — wired the flag through (xfail markers removed, assertions
unchanged):

- `services/api/routes/games.py`: create endpoint gained
  `reminders_as_dms: Annotated[bool | None, Form()] = None` passed into
  `GameCreateRequest`; update endpoint gained the same Form() param passed into
  `GameUpdateRequest`; `_build_game_response` returns
  `reminders_as_dms=bool(game.reminders_as_dms)`.
- `services/api/services/games.py`:
  - `_build_game_session`: `reminders_as_dms=bool(game_data.reminders_as_dms)`
    (no template default; None → False)
  - `_update_remaining_fields`: `if update_data.reminders_as_dms is not None:`
    assignment (docstring field list updated)
  - manual `clone_game` path: carries over
    `reminders_as_dms=source_game.reminders_as_dms`
- `shared/services/game_schedules.py`: `clone_game_for_recurrence` carries over
  `reminders_as_dms=source.reminders_as_dms`

**Integration coverage** (`tests/integration/test_rewards_fields.py`, written
after implementation per TDD integration-test rules — no xfail):

- `test_reminders_as_dms_defaults_false_and_round_trips_true`: fresh game via
  API has `reminders_as_dms=false` in response and DB row; explicit `"true"`
  round-trips through create + response + DB; PUT to `"false"` persists.
- `test_clone_game_copies_reminders_as_dms`: clone of a flagged game inherits
  `reminders_as_dms=true`.

**Verification**: `uv run pytest tests/unit` — 2542 passed (+5 new);
`uv run mypy shared/ services/` — clean; ruff check + format clean on all
changed files; both new integration tests pass against the live Docker stack
(`scripts/run-integration-tests.sh <node ids>` → `2 passed`, migration applied
cleanly at environment startup; output in `output-integration.txt`).
