<!-- markdownlint-disable-file -->

# Task Details: Move Game Reminders from DMs to Location Channel/Thread Posts

## Research Reference

**Source Research**: .copilot-tracking/research/20260823-01-reminder-channel-post-research.md

## Overview

Hybrid reminder delivery. When a game's `where` field resolves to exactly one
channel/thread, post a single reminder message there (mentioning confirmed
participants + host) and DM only the first waitlisted participant. When the
location is empty/ambiguous, or the channel post fails (`discord.Forbidden` /
`discord.NotFound`), fall back to the existing full DM fan-out (confirmed +
first waitlisted + host) so no reminder is ever lost. No schema, queue, or API
changes are required.

Delivery model summary:

| `where` resolves to                                  | Channel post                    | Waitlist DM           | Confirmed/host DM  |
| ---------------------------------------------------- | ------------------------------- | --------------------- | ------------------ |
| Exactly one `<#id>`, channel accessible              | Yes (mentions confirmed + host) | First waitlisted only | No                 |
| Exactly one `<#id>`, post fails (Forbidden/NotFound) | No                              | First waitlisted      | Yes (full fan-out) |
| None / empty / zero or multiple `<#id>`              | No                              | First waitlisted      | Yes (full fan-out) |

## Phase 1: Location Channel Resolution Helper

### Task 1.1: Add unit tests for `extract_single_channel_id` (RED)

Add a pure helper `extract_single_channel_id(where: str | None) -> str | None`
to `shared/utils/discord.py` (next to the existing `format_channel_mention` and
`parse_mention` helpers). It returns the channel ID string only when `where`
contains exactly one `<#id>` token; otherwise it returns `None`.

Write the unit tests first (RED) in
`tests/unit/shared/utils/test_discord_utils.py`. Import the new function at the
top of the test module (the import will fail until Task 1.2 lands — this is the
expected RED state within this phase).

Test cases (assert on real return values, no coverage theater):

- `None` input → `None`
- Empty string `""` → `None`
- Plain text with no mention (`"Meet at the park"`) → `None`
- Exactly one mention (`"<#123456789>"`) → `"123456789"`
- One mention with surrounding prose
  (`"Meet in <#123456789> after work"`) → `"123456789"`
- Two mentions (`"<#111> and <#222>"`) → `None`
- A `#name` mention that was never resolved to a snowflake
  (`"Meet in #general"`) → `None` (only `<#id>` tokens count)

- **Files**:
  - `tests/unit/shared/utils/test_discord_utils.py` - add import + 7 test cases
- **Success**:
  - `uv run pytest tests/unit/shared/utils/test_discord_utils.py` fails with
    `ImportError` (RED confirmed) before Task 1.2
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 78-84) - Implementation Patterns: channel resolution from `where`
    via a single `<#(\d+)>` regex
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 160-175) - Implementation Guidance: Key Task 1
- **Dependencies**:
  - None (foundational phase)

### Task 1.2: Implement `extract_single_channel_id` (GREEN)

Implement the helper in `shared/utils/discord.py`. Use a module-level compiled
regex matching the same token format `ChannelResolver` writes
(`re.compile(r"<#(\d+)>")`). Return the first captured group only when exactly
one match exists; return `None` for zero or two-or-more matches, and for
`None`/empty input.

```python
_CHANNEL_SNOWFLAKE_TOKEN = re.compile(r"<#(\d+)>")


def extract_single_channel_id(where: str | None) -> str | None:
    """
    Extract a single Discord channel ID from a location string.

    Returns the channel ID only when `where` contains exactly one `<#id>`
    snowflake token (the format ChannelResolver writes). Returns None for
    None/empty input, plain text with no mention, or text with multiple
    mentions, so callers can fall back to DM delivery.

    Args:
        where: Free-text location field (GameSession.where)

    Returns:
        Channel ID string, or None if not exactly one channel is referenced
    """
    if not where:
        return None
    matches = _CHANNEL_SNOWFLAKE_TOKEN.findall(where)
    if len(matches) != 1:
        return None
    return matches[0]
```

Add `import re` to the module imports if not already present.

- **Files**:
  - `shared/utils/discord.py` - add `import re`, module regex, and the function
- **Success**:
  - `uv run pytest tests/unit/shared/utils/test_discord_utils.py` passes (GREEN)
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 78-84) - Implementation Patterns: regex `<#(\d+)>` matching the
    ChannelResolver token format
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 24-27) - File Analysis: ChannelResolver `_snowflake_token_pattern`
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Channel-Post Reminder Delivery

### Task 2.1: Extend `create_notification_embed` for optional host + jump link (RED→GREEN)

The existing `GameMessageFormatter.create_notification_embed`
(`services/bot/formatters/game_message.py`, line ~648) always adds a Host field
via `format_discord_mention(host_id)`, which produces a broken `<@>` mention
when `host_id` is empty. The channel-post path needs to support a missing host
and should include a jump link to the game announcement.

RED: Add unit tests in
`tests/unit/services/bot/formatters/test_game_message.py` (do NOT mock
`discord.Embed` for these — construct a real embed and inspect `.fields`):

- `host_id=None` → no `🎯 Host` field, `📅 Start Time` field still present
- `host_id="123"` → `🎯 Host` field present with value `<@123>`
- `jump_url="https://discord.com/channels/1/2/3"` → `🔗 View Game` field present
  with that URL
- `jump_url=None` (default) → no `🔗 View Game` field

GREEN: Change the signature to
`create_notification_embed(game_title: str, scheduled_at: datetime, host_id: str | None, time_until: str, jump_url: str | None = None) -> discord.Embed`.
Add the Host field only when `host_id` is truthy; add the `🔗 View Game` field
only when `jump_url` is truthy. The existing two tests (which mock `discord.Embed`
and pass a real `host_id`) must still pass unchanged.

- **Files**:
  - `services/bot/formatters/game_message.py` - update `create_notification_embed`
  - `tests/unit/services/bot/formatters/test_game_message.py` - add 4 field tests
- **Success**:
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py` passes
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 20-22) - File Analysis: `create_notification_embed` is dead in
    production, safe to adopt
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 160-175) - Implementation Guidance: Key Task 6 (optional jump-link
    field, promoted to required here for a useful channel post)
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Add unit tests for `_post_reminder_to_channel` and the `_handle_game_reminder` branch (RED)

Add tests to `tests/unit/services/bot/events/test_handlers_game_reminder.py`.
Create a `_post_reminder_to_channel` stub in `services/bot/events/handlers.py`
(`raise NotImplementedError`) in the same RED step so the tests can import/patch
it (forward-import prohibition: the stub must exist before tests reference it).

`_post_reminder_to_channel` tests (call the method directly with a mock channel):

- Success: mock `channel.send` as `AsyncMock`; assert it is awaited once with
  `content` containing `<@confirmed_id>` and `<@host_id>`, an `embed` whose
  title is `🔔 Game Reminder`, and
  `allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)`;
  method returns `True`
- `discord.Forbidden`: `channel.send` raises `discord.Forbidden`; method returns
  `False`
- `discord.NotFound`: `channel.send` raises `discord.NotFound`; method returns
  `False`
- No host: `game.host=None`; `content` contains only the confirmed mention, no
  host mention

`_handle_game_reminder` branch tests (drive via `_handle_notification_due`,
patching `_get_bot_channel` and `_post_reminder_to_channel`):

- Channel-post success: `sample_game.where="<#123456789>"`,
  `_get_bot_channel` → mock channel, `_post_reminder_to_channel` → `True`.
  Assert `_post_reminder_to_channel` awaited once; `_send_reminder_dm` awaited
  exactly once (the first waitlisted participant only, `is_waitlist=True`); no
  confirmed or host DMs
- Channel-post fallback (post failed): `where="<#123456789>"`,
  `_post_reminder_to_channel` → `False`. Assert full DM fan-out: confirmed +
  first waitlisted + host (same counts as the existing flow tests)
- No channel: `where="<#123456789>"`, `_get_bot_channel` → `None`. Assert full
  DM fan-out
- Ambiguous location: `where="<#111> and <#222>"`. Assert full DM fan-out and
  `_post_reminder_to_channel` never awaited

Use the existing `sample_game` / `sample_user` fixtures and the established
`get_db_session` / `utc_now` / `_get_game_with_participants` patching pattern
from the existing flow tests.

- **Files**:
  - `tests/unit/services/bot/events/test_handlers_game_reminder.py` - add 8 tests
  - `services/bot/events/handlers.py` - add `_post_reminder_to_channel` stub
- **Success**:
  - New tests fail (RED) because the branch + real method do not exist yet
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 85-126) - Complete Examples: proposed channel-post path sketch
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 78-84) - Implementation Patterns: posting + error handling
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Implement `_post_reminder_to_channel` and wire the branch (GREEN)

Replace the `_post_reminder_to_channel` stub with the real implementation and
add the delivery branch to `_handle_game_reminder`.

`_post_reminder_to_channel` (in `services/bot/events/handlers.py`):

```python
async def _post_reminder_to_channel(
    self,
    channel: discord.TextChannel,
    game: game_model.GameSession,
    confirmed: list[participant_model.GameParticipant],
    jump_url: str | None,
) -> bool:
    """Post a reminder to the location channel mentioning confirmed + host.

    Args:
        channel: Resolved location channel or thread
        game: Game session being reminded
        confirmed: Confirmed (non-waitlist) participants
        jump_url: Discord jump URL to the game posting, or None

    Returns:
        True if the post succeeded, False if it failed (caller falls back to DMs)
    """
    embed = GameMessageFormatter.create_notification_embed(
        game_title=game.title,
        scheduled_at=game.scheduled_at,
        host_id=game.host.discord_id if game.host else None,
        time_until=format_discord_timestamp(game.scheduled_at, "R"),
        jump_url=jump_url,
    )
    mention_ids = [p.user.discord_id for p in confirmed if p.user and p.user.discord_id]
    if game.host and game.host.discord_id:
        mention_ids.append(game.host.discord_id)
    content = " ".join(f"<@{mid}>" for mid in mention_ids)
    try:
        await channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
        )
        logger.info("Posted reminder to channel %s for game %s", channel.id, game.id)
        return True
    except (discord.Forbidden, discord.NotFound) as e:
        logger.warning(
            "Failed to post reminder to channel %s for game %s: %s",
            channel.id,
            game.id,
            e,
        )
        return False
```

Wire the branch into `_handle_game_reminder` (replace the unconditional DM
fan-out, after `game_time_unix` and `jump_url` are computed):

```python
location_channel_id = extract_single_channel_id(game.where)
channel = (
    await self._get_bot_channel(location_channel_id) if location_channel_id else None
)

if channel is not None:
    posted = await self._post_reminder_to_channel(
        channel=channel, game=game, confirmed=confirmed, jump_url=jump_url
    )
    if posted:
        # Channel post reached confirmed + host; DM only the first waitlisted
        await self._send_participant_reminders(
            overflow[:_WAITLIST_REMINDER_COUNT],
            game.title,
            game_time_unix,
            is_waitlist=True,
            jump_url=jump_url,
        )
        logger.info(
            "✓ Posted reminder to channel %s for game %s; waitlist DMs sent",
            channel.id,
            reminder_event.game_id,
        )
        return

# Fallback: full DM fan-out (no/ambiguous location, or channel post failed)
await self._send_participant_reminders(
    confirmed, game.title, game_time_unix, is_waitlist=False, jump_url=jump_url
)
await self._send_participant_reminders(
    overflow[:_WAITLIST_REMINDER_COUNT],
    game.title,
    game_time_unix,
    is_waitlist=True,
    jump_url=jump_url,
)
await self._send_host_reminder(game.host, game.title, game_time_unix, jump_url=jump_url)
```

Add imports to `services/bot/events/handlers.py`:

- `from services.bot.formatters.game_message import GameMessageFormatter, format_game_announcement`
  (extend the existing `format_game_announcement` import)
- `from services.bot.utils.discord_format import format_discord_timestamp, get_member_display_info`
  (extend the existing `get_member_display_info` import)
- `from shared.utils.discord import extract_single_channel_id`

Keep `_send_reminder_dm`, `_send_participant_reminders`, `_send_host_reminder`,
and the `DMFormats` reminder formats intact — they are used by the waitlist DMs
in the success path and by the full fallback.

- **Files**:
  - `services/bot/events/handlers.py` - implement method, wire branch, add imports
- **Success**:
  - `uv run pytest tests/unit/services/bot/events/test_handlers_game_reminder.py` passes
  - `uv run pytest tests/unit` passes
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 85-126) - Complete Examples: channel-post path + fallback
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 33-35) - File Analysis: `announcement_loop._announce` posting pattern
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Verify existing flow tests still pass (fallback path)

The six existing `_handle_notification_due` flow tests in
`tests/unit/services/bot/events/test_handlers_game_reminder.py` use the
`sample_game` fixture, which does not set `where` (so `game.where` is `None`).
With `where=None`, `extract_single_channel_id` returns `None`, the channel is
`None`, and the handler takes the full DM fan-out fallback — identical to the
current behavior. These tests (asserting DM counts of 3, 1, 1, 2, 4, 4 and
per-call kwargs) must pass unchanged.

Run the full file and confirm no regressions. If any test now fails, the
fallback path diverged from the original behavior — fix the implementation, not
the test.

- **Files**:
  - `tests/unit/services/bot/events/test_handlers_game_reminder.py` - no changes
    expected (verification only)
- **Success**:
  - All six existing flow tests pass unchanged
  - `uv run pytest tests/unit` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 36-38) - File Analysis: existing flow tests encode DM fan-out counts
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: E2E Test Rewrite

### Task 3.1: Add `wait_for_channel_message` helper to the e2e discord helper

Add a polling helper to `tests/e2e/helpers/discord.py` (near the existing
`wait_for_dm_matching` / `wait_for_recent_dm` methods) that scans recent channel
history for the first message matching a predicate. Reuse the existing
`get_recent_messages` and `wait_for_condition` utilities.

```python
async def wait_for_channel_message(
    self,
    channel_id: str,
    predicate: Callable[[discord.Message], bool],
    timeout: int = 150,
    interval: float = 5.0,
    limit: int = 15,
    description: str = "channel message",
) -> discord.Message:
    """
    Wait for a recent message in a channel matching a predicate.

    Args:
        channel_id: Discord channel snowflake
        predicate: Returns True for the matching message
        timeout: Maximum seconds to wait
        interval: Seconds between history scans
        limit: Number of recent messages to scan each poll
        description: Human-readable description for timeout errors

    Returns:
        Matching Discord Message object
    """

    async def check_messages():
        messages = await self.get_recent_messages(channel_id, limit)
        for msg in messages:
            if predicate(msg):
                return (True, msg)
        return (False, None)

    return await wait_for_condition(
        check_messages,
        timeout=timeout,
        interval=interval,
        description=description,
    )
```

Confirm `Callable` is imported (it already is, used by `wait_for_message_update`).

- **Files**:
  - `tests/e2e/helpers/discord.py` - add `wait_for_channel_message`
- **Success**:
  - `uv run mypy shared/ services/` passes (helper is type-correct)
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 40-43) - File Analysis: `wait_for_message` / history-scan helpers are
    the natural addition for "new message in channel matching title"
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Rewrite `test_game_reminder_dm_delivery` for hybrid delivery

Rewrite `tests/e2e/test_game_reminder.py::test_game_reminder_dm_delivery` to
verify the hybrid delivery model. The test must:

1. Create a game with `where=f"<#{discord_channel_id}>"` (a single channel
   mention — `ChannelResolver` validates and stores it as a `<#id>` token),
   `max_players="1"`, and
   `initial_participants=json.dumps([f"<@{discord_player_a_id}>", f"<@{discord_user_id}>"])`
   so Player A is confirmed and the real test user is waitlisted (the same
   pattern as `tests/e2e/test_waitlist_promotion.py`).
2. Keep the existing `reminder_minutes=[1]`, `wait_for_game_message_id`, and
   `notification_schedule` row waits.
3. Assert a reminder channel post appears in `discord_channel_id` using the new
   `wait_for_channel_message` helper with a predicate matching an embed titled
   `🔔 Game Reminder` whose description contains the game title. Assert the post
   content mentions the confirmed participant
   (`f"<@{discord_player_a_id}>" in post.content`).
4. Assert the waitlisted test user still receives a reminder DM via the existing
   `wait_for_recent_dm(user_id=discord_user_id, game_title=game_title,
dm_type=DMType.REMINDER)`.
5. Update the test docstring and module docstring to describe hybrid delivery
   (channel post + waitlist DM) instead of DM-only delivery.

Add `discord_player_a_id` to the test's fixture parameters.

- **Files**:
  - `tests/e2e/test_game_reminder.py` - rewrite the test
- **Success**:
  - `scripts/run-e2e-tests.sh tests/e2e/test_game_reminder.py |& tee output-e2e.txt`
    passes (follow `.github/instructions/test-execution.instructions.md`:
    `tee` capture, ≥900000ms timeout)
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 39-41) - File Analysis: e2e test encodes DM behavior and must be
    rewritten to assert a channel post
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Lines 136-143) - Technical Requirements: e2e test rewrite required
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Backend "Always send reminders as DMs" Flag

### Task 4.1: Migration + model column for `reminders_as_dms` (RED→GREEN)

Add a new alembic migration creating `alembic/versions/<new_rev>_add_reminders_as_dms.py`
with `down_revision = "bf79aeffb6b0"` (verified head via `uv run alembic heads`).
Follow the exact structure of `alembic/versions/20260321_add_rewards_fields.py`:
copyright header, docstring with revision IDs, `upgrade()` adds one column,
`downgrade()` drops it.

```python
def upgrade() -> None:
    """Add reminders_as_dms opt-out flag to game sessions."""
    op.add_column(
        "game_sessions",
        sa.Column(
            "reminders_as_dms",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove reminders_as_dms flag from game sessions."""
    op.drop_column("game_sessions", "reminders_as_dms")
```

Then add the mapped column to `GameSession` in `shared/models/game.py`, next to
`remind_host_rewards` (line ~71):

```python
reminders_as_dms: Mapped[bool] = mapped_column(
    Boolean, nullable=False, default=False, server_default=text("false")
)
```

- **Files**:
  - `alembic/versions/<new_rev>_add_reminders_as_dms.py` - new migration
  - `shared/models/game.py` - new column on `GameSession`
- **Success**:
  - `uv run alembic upgrade head` applies cleanly against a scratch DB (or the
    integration test environment); `uv run mypy shared/ services/` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Extension section) - Migration mechanics + verified precedent table
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Schemas — create/update/response fields (RED→GREEN)

Add the field to all three schemas in `shared/schemas/game.py`, mirroring
`remind_host_rewards`:

- `GameCreateRequest` (after `remind_host_rewards`, line ~98):
  ```python
  reminders_as_dms: bool | None = Field(
      None,
      description="Always deliver game reminders as DMs instead of posting to the location channel",
  )
  ```
- `GameUpdateRequest` (next to `remind_host_rewards`, line ~160):
  ```python
  reminders_as_dms: bool | None = None
  ```
- `GameResponse` (next to `remind_host_rewards`, lines 245–249):
  ```python
  reminders_as_dms: bool = Field(
      default=False,
      description="When True, reminders are always delivered as DMs",
  )
  ```

Write RED unit tests first where schema behavior is observable through service
tests (Task 4.3); no standalone schema test file exists for these models.

- **Files**:
  - `shared/schemas/game.py` - three new fields
- **Success**:
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Extension section) - Verified precedent table, schema rows
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: API routes + service wiring with unit tests (RED→GREEN)

**RED** — add unit tests mirroring the rewards-feature patterns:

- `tests/unit/services/api/services/test_games_service.py`:
  - `_build_game_session` uses `game_data.reminders_as_dms=True` when set;
    defaults to `False` when absent (mirror
    `test_build_game_session_remind_host_rewards_request_overrides_template`,
    line ~1141). Assert on the constructed `GameSession.reminders_as_dms`.
- `tests/unit/services/api/services/test_update_game_fields_helpers.py`:
  - `_update_remaining_fields` sets `game.reminders_as_dms = True` from update
    data and leaves it untouched when the field is None (mirror
    `test_update_remaining_fields_updates_remind_host_rewards`, line ~459).
- `tests/unit/services/test_system_clone_for_recurrence.py`:
  - recurrence clone carries `reminders_as_dms` from source game (extend an
    existing clone test or add one alongside the `remind_host_rewards`
    assertions at line ~75).

**GREEN** — wire the flag through:

- `services/api/routes/games.py`:
  - create endpoint (~line 390): add
    `reminders_as_dms: Annotated[bool | None, Form()] = None` and pass it into
    the service call next to `remind_host_rewards=remind_host_rewards`
  - update endpoint (~line 671): same Form() parameter; it flows through
    `GameUpdateRequest` automatically once the schema has the field
- `services/api/services/games.py`:
  - `_build_game_session` (~line 545): since there is no template default,
    `reminders_as_dms=bool(game_data.reminders_as_dms)` (None → False)
  - `_update_remaining_fields` (~line 1280):
    ```python
    if update_data.reminders_as_dms is not None:
        game.reminders_as_dms = update_data.reminders_as_dms
    ```
  - manual clone path (~line 937): carry over
    `reminders_as_dms=source_game.reminders_as_dms`
- `shared/services/game_schedules.py` (`clone_game_for_recurrence`, ~line 231):
  carry over `reminders_as_dms=source.reminders_as_dms`

**Integration test**: add a case to `tests/integration/test_rewards_fields.py`
(or a new focused file) asserting a freshly created game via the API has
`reminders_as_dms = false` by default and that an explicit `true` round-trips
through create + response.

- **Files**:
  - `services/api/routes/games.py` - form params on create/update
  - `services/api/services/games.py` - build/update/clone wiring
  - `shared/services/game_schedules.py` - recurrence clone carry-over
  - `tests/unit/services/api/services/test_games_service.py` - RED tests
  - `tests/unit/services/api/services/test_update_game_fields_helpers.py` - RED tests
  - `tests/unit/services/test_system_clone_for_recurrence.py` - RED tests
  - `tests/integration/test_rewards_fields.py` (or new file) - integration coverage
- **Success**:
  - New unit tests pass; `uv run pytest tests/unit` passes; mypy clean
  - Integration test passes when run in the integration environment
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Extension section) - Verified precedent table, route/service rows
- **Dependencies**:
  - Task 4.2 completion

## Phase 5: Bot Short-Circuit for DM-Only Reminders

### Task 5.1: Unit tests for the flag short-circuit (RED)

Add tests to `tests/unit/services/bot/events/test_handlers_game_reminder.py`
using the existing `_reminder_flow_patches` helper and fixtures:

- `test_handle_game_reminder_dms_only_flag_skips_channel_post`:
  `sample_game.where = "<#123456789>"`, `sample_game.reminders_as_dms = True`,
  3 participants / `max_players=2` + host. Assert `_get_bot_channel` never
  awaited, `_post_reminder_to_channel` never awaited, and full DM fan-out of 4
  (2 confirmed + 1 waitlist + 1 host) with correct kwargs — identical shape to
  the fallback-path assertions already in this file.
- `test_handle_game_reminder_dms_only_flag_false_still_posts`: control test —
  same setup but `reminders_as_dms = False`; assert `_post_reminder_to_channel`
  awaited once and only the waitlist DM is sent (channel-post success path).

No stub needed: `_deliver_game_reminders` already exists; the RED state is that
the guard clause does not yet exist (flag ignored → channel post attempted).

- **Files**:
  - `tests/unit/services/bot/events/test_handlers_game_reminder.py` - 2 new tests
- **Success**:
  - Flag-skip test fails (RED); control test passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Extension section) - Bot-side change surface
- **Dependencies**:
  - Phase 4 completion (model column must exist for mypy/tests)

### Task 5.2: Implement the short-circuit in `_deliver_game_reminders` (GREEN)

At the top of `_deliver_game_reminders` in `services/bot/events/handlers.py`,
before `extract_single_channel_id(game.where)`:

```python
if game.reminders_as_dms:
    logger.info(
        "Game %s has reminders_as_dms enabled; skipping channel post",
        game.id,
    )
    # fall through to full DM fan-out below
else:
    location_channel_id = extract_single_channel_id(game.where)
    channel = (
        await self._get_bot_channel(location_channel_id) if location_channel_id else None
    )
    ...existing channel-post branch...
```

Prefer an early structure that keeps cognitive complexity low — e.g. compute
`channel = None` when the flag is set and let the existing
`if channel is not None:` branch handle everything unchanged:

```python
location_channel_id = extract_single_channel_id(game.where) if not game.reminders_as_dms else None
channel = (
    await self._get_bot_channel(location_channel_id) if location_channel_id else None
)
```

This single-line guard reuses the entire existing fallback path with zero
duplication. Update the method docstring to document the opt-out.

- **Files**:
  - `services/bot/events/handlers.py` - guard clause + docstring note
- **Success**:
  - Both new tests pass; all pre-existing reminder flow tests pass unchanged
  - `uv run pytest tests/unit` passes; mypy clean; complexipy clean
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Extension section) - Short-circuit semantics decision
- **Dependencies**:
  - Task 5.1 completion

## Phase 6: Frontend Checkbox

### Task 6.1: Type, form state, checkbox, payloads (RED→GREEN)

**RED** — add vitest coverage mirroring the rewards-feature tests:

- `frontend/src/components/__tests__/GameForm.rewards.test.tsx` pattern → new
  describe block (same file or a sibling `GameForm.remindersAsDms.test.tsx`):
  checkbox reflects `initialData.reminders_as_dms === true`; defaults unchecked
  when absent.
- `frontend/src/pages/__tests__/CreateGame.test.tsx` (pattern at lines 537–600):
  payload sends `'true'` when checked and `'false'` when unchecked.

**GREEN** — wire the field through the frontend:

- `frontend/src/types/index.ts`: add `reminders_as_dms?: boolean;` to the
  `GameSession` interface next to `remind_host_rewards` (~line 124).
- `frontend/src/components/GameForm.tsx`:
  - form-state interface (~line 113): `remindersAsDms: boolean;`
  - both initializers (lines ~310 and ~343):
    `remindersAsDms: initialData?.reminders_as_dms ?? false,`
  - new MUI `FormControlLabel` + `Checkbox` next to the rewards checkbox
    (lines ~963–975), label "Always send reminders as DMs", same
    `setFormData((prev) => ({ ...prev, remindersAsDms: e.target.checked }))`
    onChange and `disabled={loading}` pattern
- `frontend/src/pages/CreateGame.tsx` (~line 234) and
  `frontend/src/pages/EditGame.tsx` (both append sites, lines ~233 and ~368):

  ```typescript
  payload.append('reminders_as_dms', formData.remindersAsDms ? 'true' : 'false');
  ```

- **Files**:
  - `frontend/src/types/index.ts` - type field
  - `frontend/src/components/GameForm.tsx` - state + checkbox
  - `frontend/src/pages/CreateGame.tsx`, `frontend/src/pages/EditGame.tsx` - payloads
  - `frontend/src/components/__tests__/...`, `frontend/src/pages/__tests__/CreateGame.test.tsx` - tests
- **Success**:
  - New vitest cases pass; `cd frontend && npm run build` passes;
    `cd frontend && npm run test` passes
- **Research References**:
  - .copilot-tracking/research/20260823-01-reminder-channel-post-research.md
    (Extension section) - Verified precedent table, frontend rows
- **Dependencies**:
  - Phase 5 completion (API must accept the form field first)

## Dependencies

- Python 3.x with `uv` (dependency + test runner)
- `discord.py` (existing) — `discord.TextChannel`, `discord.Forbidden`,
  `discord.NotFound`, `discord.AllowedMentions`
- `pytest` + `pytest-asyncio` (existing)
- E2E: full stack via `compose.e2e.yaml`, Discord test guild, notification
  daemon (existing e2e prerequisites)

## Success Criteria

- When `where` contains exactly one valid `<#id>` and the bot can access that
  channel/thread, exactly one reminder message is posted there mentioning
  confirmed participants + host, and the first `_WAITLIST_REMINDER_COUNT`
  waitlisted participant receives a reminder DM.
- When `where` is empty/ambiguous or the channel is inaccessible, the existing
  full DM fan-out still occurs (confirmed + first waitlisted + host) — no
  regression.
- `uv run pytest tests/unit` passes; `uv run mypy shared/ services/` passes.
- The rewritten e2e reminder test passes with `tee`-captured output.
- Extension: when `reminders_as_dms` is true on a game, every reminder takes
  the full DM fan-out path unconditionally — no channel lookup or post is
  attempted regardless of `where`; default-off changes nothing for existing
  games; recurring clones carry the flag over.
