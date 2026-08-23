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
