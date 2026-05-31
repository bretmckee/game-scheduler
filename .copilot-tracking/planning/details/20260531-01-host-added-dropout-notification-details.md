<!-- markdownlint-disable-file -->

# Task Details: Host Notification When HOST_ADDED Player Drops Out

## Research Reference

**Source Research**: #file:../research/20260531-01-host-added-dropout-notification-research.md

---

## Phase 1: DM format stubs + RED unit tests

### Task 1.1: Add `DMFormats.host_added_dropout` and `DMPredicates.host_added_dropout` stubs

Add `NotImplementedError` stubs to both classes so Phase 1 tests can import the names without
`AttributeError`. Place each stub after the last existing method in its respective class.

- **Files**:
  - `shared/message_formats.py` — add stub after `rewards_reminder` (currently ends ~line 244);
    add predicate stub after the last method in `DMPredicates` (currently ~line 380)
- **Success**:
  - `python -c "from shared.message_formats import DMFormats, DMPredicates"` imports without error
  - Both stubs raise `NotImplementedError` when called
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 135-168) — complete format/predicate examples
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 7-47) — `DMFormats` / `DMPredicates` class locations in `shared/message_formats.py`
- **Dependencies**:
  - None

### Task 1.2: Add xfail unit tests for format and predicate

Add failing tests to `tests/unit/shared/test_message_formats.py` (append after line 293).
Each test must be marked `@pytest.mark.xfail(strict=True, reason=...)`.

Tests to add:

- `test_host_added_dropout_contains_player_mention` — format includes player `<@id>`
- `test_host_added_dropout_contains_game_title` — format includes game title
- `test_host_added_dropout_contains_relative_timestamp` — format includes `<t:{unix}:R>`
- `test_host_added_dropout_with_jump_url_includes_link` — format appends jump URL on separate line
- `test_host_added_dropout_without_jump_url_omits_link` — format omits URL when `None`
- `test_host_added_dropout_predicate_matches` — predicate returns `True` for matching DM
- `test_host_added_dropout_predicate_rejects_wrong_title` — predicate returns `False` for wrong title
- `test_host_added_dropout_predicate_rejects_none_content` — predicate returns `False` when `dm.content is None`

- **Files**:
  - `tests/unit/shared/test_message_formats.py` — append tests after line 293
- **Success**:
  - `uv run pytest tests/unit/shared/test_message_formats.py -v` — all new tests show as `xfailed`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 135-168) — exact format and predicate signatures to test against
- **Dependencies**:
  - Task 1.1 complete (stubs must exist so tests can import the names)

---

## Phase 2: DM format implementation (GREEN)

### Task 2.1: Implement `DMFormats.host_added_dropout`

Replace the stub with the real implementation in `shared/message_formats.py`.
Signature and body per research complete examples.

```python
@staticmethod
def host_added_dropout(
    player_mention: str,
    game_title: str,
    game_time_unix: int,
    jump_url: str | None = None,
) -> str:
    base = (
        f"⚠️ {player_mention} (who you added) dropped out of **{game_title}**"
        f" which starts <t:{game_time_unix}:R>"
    )
    if jump_url:
        return f"{base}\n{jump_url}"
    return base
```

- **Files**:
  - `shared/message_formats.py` — replace `host_added_dropout` stub in `DMFormats`
- **Success**:
  - Calling `DMFormats.host_added_dropout("<@123>", "Epic Quest", 1700000000)` returns a string
    containing `"<@123>"`, `"Epic Quest"`, and `"<t:1700000000:R>"`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 135-153) — exact `DMFormats.host_added_dropout` implementation
- **Dependencies**:
  - Task 1.1 complete

### Task 2.2: Implement `DMPredicates.host_added_dropout`

Replace the stub with the real predicate in `shared/message_formats.py`.

```python
@staticmethod
def host_added_dropout(game_title: str) -> Callable[[DiscordMessage], bool]:
    def predicate(dm: DiscordMessage) -> bool:
        return bool(
            dm.content
            and game_title in dm.content
            and "dropped out" in dm.content
            and "who you added" in dm.content
        )
    return predicate
```

- **Files**:
  - `shared/message_formats.py` — replace `host_added_dropout` stub in `DMPredicates`
- **Success**:
  - Predicate returns `True` for a DM containing the game title, "dropped out", "who you added"
  - Predicate returns `False` when `dm.content` is `None`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 154-168) — exact `DMPredicates.host_added_dropout` implementation
- **Dependencies**:
  - Task 1.1 complete

### Task 2.3: Remove xfail markers from Phase 1 unit tests

Remove `@pytest.mark.xfail` decorators from all 8 tests added in Task 1.2.

- **Files**:
  - `tests/unit/shared/test_message_formats.py`
- **Success**:
  - `uv run pytest tests/unit/shared/test_message_formats.py -v` — all new tests `PASSED`
- **Dependencies**:
  - Tasks 2.1 and 2.2 complete

---

## Phase 3: Bot handler RED unit tests

### Task 3.1: Add xfail unit tests for HOST_ADDED leave host DM

Append new tests to `tests/unit/bot/handlers/test_leave_game_handler.py` (after line 205).
Each test must be marked `@pytest.mark.xfail(strict=True, reason=...)`.

Tests to add:

- `test_host_added_leave_sends_dm_to_host` — when participant `position_type == HOST_ADDED`
  and `game.host` is set and `interaction.client.get_user()` returns a mock user,
  assert `mock_host_user.send` was called with the expected message matching
  `DMPredicates.host_added_dropout(game_title)`
- `test_non_host_added_leave_does_not_send_host_dm` — when `position_type == SELF_ADDED`,
  assert `interaction.client.get_user` was never called for host notification
- `test_host_added_leave_no_dm_when_host_not_in_cache` — when `get_user()` returns `None`,
  no exception is raised and leave completes normally

Mocking notes:

- Mock the game with `game.host` set, `game.host.discord_id = "999888777"`
- Mock `game.channel` with `channel.channel_id = "111222333"`, `game.guild.guild_id = "444555666"`
- Mock `game.message_id = "777888999"` for jump URL construction
- Mock `interaction.client.get_user(999888777)` to return a mock user (async `.send`)

- **Files**:
  - `tests/unit/bot/handlers/test_leave_game_handler.py` — append after line 205
- **Success**:
  - `uv run pytest tests/unit/bot/handlers/test_leave_game_handler.py -v` — new tests show as `xfailed`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 78-134) — button path implementation pattern
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 190-196) — technical requirements (cache miss is soft failure)
- **Dependencies**:
  - Phase 2 complete (tests use `DMFormats.host_added_dropout` for assertion)

---

## Phase 4: Bot handler implementation (GREEN)

### Task 4.1: Add eager-loads for `GameSession.host` and `GameSession.channel` in `_validate_leave_game`

In `services/bot/handlers/leave_game.py`, update `_validate_leave_game` (line 112).
The query currently only loads `selectinload(GameSession.guild)` (line 129).
Add two more `selectinload` options:

```python
result = await db.execute(
    select(GameSession)
    .options(
        selectinload(GameSession.guild),
        selectinload(GameSession.host),
        selectinload(GameSession.channel),
    )
    .where(GameSession.id == str(game_id))
)
```

- **Files**:
  - `services/bot/handlers/leave_game.py` — update query in `_validate_leave_game` (~line 126-131)
- **Success**:
  - `game.host` and `game.channel` are accessible after `_validate_leave_game` returns
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 175-189) — configuration example for updated query
- **Dependencies**:
  - None (independent of Phase 3 tests)

### Task 4.2: Add host DM sending logic in `handle_leave_game` after participant deletion

In `services/bot/handlers/leave_game.py`, after the `await db.delete(participant)` call
(currently inside `handle_leave_game`, ~lines 48-110), add:

```python
if participant.position_type == ParticipantType.HOST_ADDED and game.host and game.host.discord_id:
    host_user = interaction.client.get_user(int(game.host.discord_id))
    if host_user:
        scheduled_unix = int(game.scheduled_at.timestamp())
        jump_url = (
            f"https://discord.com/channels/{game.guild.guild_id}/"
            f"{game.channel.channel_id}/{game.message_id}"
            if game.message_id else None
        )
        await host_user.send(
            DMFormats.host_added_dropout(
                player_mention=f"<@{interaction.user.id}>",
                game_title=game.title,
                game_time_unix=scheduled_unix,
                jump_url=jump_url,
            )
        )
```

Capture `participant.position_type` before any `await` that could expire the session.
Also add `from shared.models.participant import ParticipantType` if not already imported,
and `from shared.message_formats import DMFormats` if not already imported.

- **Files**:
  - `services/bot/handlers/leave_game.py` — add host DM block after participant deletion
- **Success**:
  - Unit test `test_host_added_leave_sends_dm_to_host` passes (with xfail removed)
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 78-112) — button path implementation pattern with exact code
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 190-196) — technical requirements
- **Dependencies**:
  - Task 4.1 complete (host and channel must be loaded before DM can be sent)

### Task 4.3: Remove xfail markers from Phase 3 unit tests

Remove `@pytest.mark.xfail` decorators from all 3 tests added in Task 3.1.

- **Files**:
  - `tests/unit/bot/handlers/test_leave_game_handler.py`
- **Success**:
  - `uv run pytest tests/unit/bot/handlers/test_leave_game_handler.py -v` — all tests `PASSED`
- **Dependencies**:
  - Tasks 4.1 and 4.2 complete

---

## Phase 5: API service RED unit + integration tests

### Task 5.1: Add xfail unit test for HOST_ADDED leave publishes `NOTIFICATION_SEND_DM`

Add to `TestLeaveGame` class in `tests/unit/api/services/test_games.py` (after line 303).
Mark with `@pytest.mark.xfail(strict=True, reason=...)`.

Test: `test_host_added_leave_publishes_notification_send_dm`

- Set up a game with `game.host.discord_id = "999888777"` in the reloaded game
- Set participant `position_type = ParticipantType.HOST_ADDED`
- Call `await game_service.leave_game(game.id, "user-discord-id")`
- Assert `mock_publisher.publish_deferred` was called with an event whose
  `event_type == EventType.NOTIFICATION_SEND_DM`
- Assert the event `data["notification_type"] == "host_added_dropout"`
- Assert the event `data["user_id"] == "999888777"` (host's discord_id)

Also add `test_non_host_added_leave_does_not_publish_notification`:

- Set participant `position_type = ParticipantType.SELF_ADDED`
- Assert no `NOTIFICATION_SEND_DM` event is published (only `GAME_UPDATED`)

- **Files**:
  - `tests/unit/api/services/test_games.py` — add to `TestLeaveGame` class after line 303
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py::TestLeaveGame -v` — new tests `xfailed`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 113-134) — API path implementation pattern
- **Dependencies**:
  - Phase 2 complete

### Task 5.2: Add xfail integration test for HOST_ADDED leave

Add a new test function to `tests/integration/test_leave_game.py` (after line 247).
Mark with `@pytest.mark.xfail(strict=True, reason=...)`.

Test: `test_host_added_leave_publishes_notification_send_dm`

- Create a game with a host user (insert host into DB, set `game.host_id`)
- Insert a participant with `position_type = ParticipantType.HOST_ADDED`
- Call `handle_leave_game` (or call the service directly)
- Assert the mock publisher received a `NOTIFICATION_SEND_DM` event
- Assert `data["notification_type"] == "host_added_dropout"`

Refer to the existing `test_successful_leave_deletes_participant_and_publishes_event` (line 218)
for the DB setup / fixture pattern. The HOST_ADDED test needs a `host_id` on the game and
a host user record in the DB.

- **Files**:
  - `tests/integration/test_leave_game.py` — append after line 247
- **Success**:
  - `uv run pytest tests/integration/test_leave_game.py -v` (in integration container) — new test `xfailed`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 58-66) — project conventions for integration tests
- **Dependencies**:
  - Phase 2 complete

---

## Phase 6: API service implementation (GREEN)

### Task 6.1: Capture `position_type` and `host_discord_id` before deletion in `leave_game()`

In `services/api/services/games.py`, inside `leave_game()` (line 2347), before
`await self.db.delete(participant)` (~line 2409), add:

```python
position_type = participant.position_type
host_discord_id = game.host.discord_id if game.host else None
```

`game` is already loaded with `game.host` via `get_game()` which uses `selectinload(GameSession.host)`.
`user.discord_id` is also available here for use as the player mention.

- **Files**:
  - `services/api/services/games.py` — add two capture lines before `db.delete` (~line 2409)
- **Success**:
  - `position_type` and `host_discord_id` are available after `await self.db.delete(participant)`
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 113-134) — API path pattern showing capture-before-delete
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 190-196) — technical requirement: must capture before delete
- **Dependencies**:
  - None

### Task 6.2: Publish `NOTIFICATION_SEND_DM` after reload when participant was `HOST_ADDED`

In `services/api/services/games.py` inside `leave_game()`, after the game reload (currently
`await self._publish_game_updated(game)` at ~line 2421), add:

```python
if position_type == ParticipantType.HOST_ADDED and host_discord_id:
    scheduled_unix = int(game.scheduled_at.timestamp())
    jump_url = (
        f"https://discord.com/channels/{game.guild.guild_id}/"
        f"{game.channel.channel_id}/{game.message_id}"
        if game.message_id else None
    )
    event = messaging_events.Event(
        event_type=messaging_events.EventType.NOTIFICATION_SEND_DM,
        data=messaging_events.NotificationSendDMEvent(
            user_id=host_discord_id,
            game_id=uuid.UUID(game.id),
            game_title=game.title,
            game_time_unix=scheduled_unix,
            notification_type="host_added_dropout",
            message=DMFormats.host_added_dropout(
                player_mention=f"<@{user.discord_id}>",
                game_title=game.title,
                game_time_unix=scheduled_unix,
                jump_url=jump_url,
            ),
        ).model_dump(),
    )
    self.event_publisher.publish_deferred(event=event)
```

Add `from shared.message_formats import DMFormats` to imports if not already present.
Add `from shared.models.participant import ParticipantType` if not already imported.

- **Files**:
  - `services/api/services/games.py` — add notification block after `_publish_game_updated` call
- **Success**:
  - `NOTIFICATION_SEND_DM` event published when HOST_ADDED participant leaves
  - No event published when SELF_ADDED or ROLE_MATCHED participant leaves
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 113-134) — complete API path code example
- **Dependencies**:
  - Task 6.1 complete

### Task 6.3: Remove xfail markers from Phase 5 tests

Remove `@pytest.mark.xfail` decorators from all tests added in Phase 5.

- **Files**:
  - `tests/unit/api/services/test_games.py`
  - `tests/integration/test_leave_game.py`
- **Success**:
  - `uv run pytest tests/unit/api/services/test_games.py::TestLeaveGame -v` — all tests `PASSED`
  - Integration tests pass when run in container
- **Dependencies**:
  - Tasks 6.1 and 6.2 complete

---

## Phase 7: E2E test + DMType enum

### Task 7.1: Add `HOST_ADDED_DROPOUT` to `DMType` enum

In `tests/e2e/helpers/discord.py`, add `HOST_ADDED_DROPOUT = "host_added_dropout"` to the
`DMType(StrEnum)` class (currently ends at line 41, after `REWARDS_REMINDER`).

- **Files**:
  - `tests/e2e/helpers/discord.py` — add enum member after `REWARDS_REMINDER` (line 41)
- **Success**:
  - `from tests.e2e.helpers.discord import DMType; DMType.HOST_ADDED_DROPOUT` resolves without error
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 206-225) — implementation guidance lists this as task 8
- **Dependencies**:
  - Phase 6 complete

### Task 7.2: Add e2e test for HOST_ADDED dropout notification via API path

Create or extend an e2e test to verify the full stack: when a HOST_ADDED participant leaves
via the API, the host receives a `HOST_ADDED_DROPOUT` DM.

Test placement: add to an existing e2e test file or create
`tests/e2e/test_host_added_dropout_notification.py`.

Test outline:

1. Create a game where `DISCORD_USER_ID` (the test user) is the host
2. Add a second player as a `HOST_ADDED` participant via the API
3. That second player calls `POST /api/v1/games/{id}/leave`
4. Use `main_bot_helper` to verify `DISCORD_USER_ID` receives a DM matching
   `DMPredicates.host_added_dropout(game_title)` (i.e., `DMType.HOST_ADDED_DROPOUT`)

Refer to `tests/e2e/test_join_notification.py` for the DM assertion pattern using
`main_bot_helper` and `DMType`.

No `xfail` needed — implementation is complete by this phase. This is retrofitting
e2e coverage for already-correct code.

- **Files**:
  - `tests/e2e/test_host_added_dropout_notification.py` (new) OR existing e2e file
  - `tests/e2e/helpers/discord.py` (already updated in Task 7.1)
- **Success**:
  - E2E test passes in `scripts/run-e2e-tests.sh` environment
  - DM predicate correctly identifies the host dropout notification
- **Research References**:
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 206-225) — e2e test outline
  - #file:../research/20260531-01-host-added-dropout-notification-research.md (Lines 58-66) — project conventions
- **Dependencies**:
  - Phase 6 complete; Task 7.1 complete

---

## Dependencies

- No schema migrations required
- No new RabbitMQ event types required
- No new environment variables required

## Success Criteria

- HOST_ADDED player leaves via Discord button → host receives DM
- HOST_ADDED player leaves via web UI → host receives `NOTIFICATION_SEND_DM`-dispatched DM
- SELF_ADDED or ROLE_MATCHED player leaves → no host DM
- Host-forced removal (`update_game`) → no host DM
- All unit, integration, and e2e tests pass
