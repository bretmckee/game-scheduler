<!-- markdownlint-disable-file -->

# Task Research Notes: Host Notification When HOST_ADDED Player Drops Out

## Research Executed

### File Analysis

- `shared/models/participant.py`
  - `ParticipantType` enum: `HOST_ADDED = 8000`, `ROLE_MATCHED = 16000`, `SELF_ADDED = 24000`
  - `GameParticipant.position_type` (SmallInteger, not null) — tracks which tier a participant belongs to
  - `GameParticipant.display_name` (String(100), nullable) — set for placeholders; null for real users
  - `GameParticipant.user_id` (nullable FK to users.id) — null for placeholder participants

- `shared/models/game.py`
  - `GameSession.host_id` — FK to `users.id`
  - `GameSession.host` — ORM relationship to `User`; eager-loaded by `get_game()` in the API service

- `shared/models/user.py`
  - Only stores `discord_id` (String(20)); no cached username/display_name
  - Display names are always fetched at render time (per model comment)

- `shared/message_formats.py`
  - `DMFormats`: static methods for all DM types (`removal`, `reminder_host`, `rewards_reminder`, etc.)
  - `DMPredicates`: matching predicates for each DM type, used in e2e and unit tests
  - New `DMFormats.host_added_dropout` + `DMPredicates.host_added_dropout` must be added here

- `services/bot/handlers/leave_game.py`
  - `handle_leave_game()` — Discord button leave path; has direct `bot` client access
  - `_validate_leave_game()` — loads `GameSession` with `selectinload(GameSession.guild)` only; does NOT load `GameSession.host`
  - Returns `participant` in result dict; `participant.position_type` is accessible
  - After deletion, sends success message to the leaving user; does NOT notify the host

- `services/api/services/games.py`
  - `leave_game()` (line 2347) — web UI leave path; deletes participant, publishes `GAME_UPDATED`
  - `get_game()` (line 834) — already eager-loads `GameSession.host` via `selectinload`
  - Has `participant.position_type` and `game.host.discord_id` available before deletion
  - API service has no direct Discord access; uses RabbitMQ events to communicate with bot

- `services/bot/events/handlers.py`
  - `_handle_send_notification()` (line 921) — handles `NOTIFICATION_SEND_DM` event by sending a pre-formatted DM message to a user via `_send_dm()`; already exists and is the correct mechanism for API-side host DMs
  - `_publish_player_removed()` — only called from `update_game` (host-forced removal); NOT from `leave_game`

- `shared/messaging/events.py`
  - `EventType.NOTIFICATION_SEND_DM = "notification.send_dm"` — existing event type for API-triggered DMs
  - `NotificationSendDMEvent` — fields: `user_id`, `game_id`, `game_title`, `game_time_unix`, `notification_type`, `message`

### Code Search Results

- `selectinload.*host` in `services/bot/**/*.py`
  - Only in `announcement_loop.py` (line 142) and `handlers.py` (line 1398); NOT in `leave_game.py`
- `position_type.*HOST_ADDED` in bot handlers
  - Only in `participant_sorting.py` and test files; no existing leave handler checks it
- `_publish_player_removed` call sites
  - Line 1358 in `games.py` — only called from `update_game` (host-forced removal via edit form)
  - Confirmed: `leave_game()` never calls `_publish_player_removed`

### Project Conventions

- Standards referenced: `python.instructions.md`, `unit-tests.instructions.md`, `test-driven-development.instructions.md`, `fastapi-transaction-patterns.instructions.md`
- DM format: all DM message strings live in `shared/message_formats.py`; never inline
- Predicates paired with every format: `DMPredicates` must be extended alongside `DMFormats`
- `<@{discord_id}>` in Discord DMs resolves to the user's current display name — no username caching needed
- Jump URL pattern: `f"https://discord.com/channels/{guild.guild_id}/{channel.channel_id}/{message_id}"`
- Timestamp pattern: `<t:{unix}:R>` for relative, `<t:{unix}:F>` for full; existing DMs use both

## Key Discoveries

### Project Structure

Two distinct self-leave paths exist; both must be handled:

1. **Button leave** (`services/bot/handlers/leave_game.py`) — triggered by Discord button click; bot process handles it directly with DB access and `discord.Client`
2. **API leave** (`services/api/services/games.py` → `POST /api/v1/games/{id}/leave`) — triggered by web UI; API process handles it; communicates with bot only via RabbitMQ

Host-forced removal (`update_game` with `removed_participant_ids`) is intentionally excluded — the host initiated the action and does not need to be notified.

### Implementation Patterns

**Button path — send DM directly:**

```python
# In handle_leave_game(), after participant is deleted:
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

**API path — publish NOTIFICATION_SEND_DM:**

```python
# In leave_game(), before deleting participant:
position_type = participant.position_type
host_discord_id = game.host.discord_id if game.host else None

# After deletion and game reload:
if position_type == ParticipantType.HOST_ADDED and host_discord_id:
    scheduled_unix = int(game.scheduled_at.timestamp())
    jump_url = (
        f"https://discord.com/channels/{game.guild.guild_id}/"
        f"{game.channel.channel_id}/{game.message_id}"
        if game.message_id else None
    )
    event = messaging_events.Event(
        event_type=messaging_events.EventType.NOTIFICATION_SEND_DM,
        data=NotificationSendDMEvent(
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

### Complete Examples

**New DM format (`shared/message_formats.py`):**

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

**Matching predicate (`shared/message_formats.py`):**

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

### API and Schema Documentation

`_validate_leave_game` must also load `GameSession.channel` to build the jump URL (currently only loads `GameSession.guild`). Channel discord ID is at `game.channel.channel_id`. Guild discord ID is at `game.guild.guild_id`.

`game.scheduled_at` is a `datetime` object (not ISO string) in both paths — use `int(game.scheduled_at.timestamp())`.

### Configuration Examples

`_validate_leave_game` query change (adds host and channel eager loads):

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

### Technical Requirements

- `position_type` and `player_discord_id` must be captured BEFORE the `await db.delete(participant)` call in both paths — they become unavailable after deletion and session expiry
- The button path uses `interaction.client.get_user()` (from Discord cache); failure to find the user in cache is a soft failure (log and continue)
- The API path uses the already-existing `NOTIFICATION_SEND_DM` event — no new event type needed
- `game.message_id` may be `None` (pre-announcement games); jump URL must be `None` in that case

## Recommended Approach

Extend both leave paths to detect `position_type == HOST_ADDED` and send a DM to the host using the existing `DMFormats` / `NOTIFICATION_SEND_DM` patterns.

- **Button path**: add `selectinload(GameSession.host)` and `selectinload(GameSession.channel)` to `_validate_leave_game`; send DM directly after deletion using `interaction.client.get_user()`
- **API path**: capture `participant.position_type` and `user.discord_id` before deletion; publish `NOTIFICATION_SEND_DM` event after deletion using pre-built message from `DMFormats.host_added_dropout`
- **No new event type** required — `NOTIFICATION_SEND_DM` already handles arbitrary host DMs
- **No opt-in toggle** — always fires for HOST_ADDED self-leave; mirrors the existing `rewards_reminder` host DM pattern

## Implementation Guidance

- **Objectives**: Notify the host via DM whenever a HOST_ADDED participant voluntarily leaves a game
- **Key Tasks**:
  1. Add `DMFormats.host_added_dropout` + `DMPredicates.host_added_dropout` to `shared/message_formats.py`
  2. Update `_validate_leave_game` in `services/bot/handlers/leave_game.py` to eager-load `GameSession.host` and `GameSession.channel`
  3. After deletion in `handle_leave_game`, check `position_type` and send host DM
  4. In `services/api/services/games.py` `leave_game()`, capture position_type + discord_id before delete, publish `NOTIFICATION_SEND_DM` if HOST_ADDED
  5. Unit tests for new DM format, button leave host notification, API leave host notification
  6. Integration test in `tests/integration/test_leave_game.py` for HOST_ADDED leave
  7. E2E test extension: admin creates game with `host=<@DISCORD_USER_ID>` + Player A as HOST_ADDED participant; Player A calls `/api/v1/games/{id}/leave`; `main_bot_helper` verifies `DISCORD_USER_ID` receives the DM
  8. Add `HOST_ADDED_DROPOUT` to `DMType` enum in `tests/e2e/helpers/discord.py`
- **Dependencies**: No schema migrations, no new event types, no new environment variables
- **Success Criteria**:
  - HOST_ADDED player leaves via Discord button → host receives DM within seconds
  - HOST_ADDED player leaves via web UI → host receives DM via RabbitMQ/`NOTIFICATION_SEND_DM`
  - SELF_ADDED or ROLE_MATCHED player leaves → no host DM sent
  - Host-forced removal → no host DM sent
  - `position_type` and discord_id captured before delete in both paths
  - All 9 affected files updated with tests passing
