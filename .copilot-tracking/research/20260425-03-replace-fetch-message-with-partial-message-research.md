<!-- markdownlint-disable-file -->

# Task Research Notes: Replace fetch_message REST Calls with PartialMessage

## Research Executed

### File Analysis

- `services/bot/events/handlers.py`
  - Three methods use `channel.fetch_message()` as a precursor to `.edit()` or `.delete()`:
    - `_fetch_message_for_refresh()` → called by `_refresh_game_message()`
    - `_fetch_channel_and_message()` → called by `_update_message_for_player_removal()`, `_handle_game_cancelled()`, `_try_edit_game_message()`
    - `_archive_game_announcement()` → inline `channel.fetch_message()` before `.delete()`
  - One method uses `channel.fetch_message()` intentionally as a sentinel (sweep loop in `bot.py`) — must not be changed
- `services/bot/bot.py`
  - Sweep loop at line 618: `channel.fetch_message()` is the detection mechanism; catching `discord.NotFound` is the whole point. **Leave this alone.**
- `tests/unit/services/bot/events/test_handlers.py`
  - Tests for `_fetch_message_for_refresh` and `_fetch_channel_and_message` assert `.fetch_message` was called; these must be updated

### Code Search Results

- `get_partial_message` in entire workspace
  - Zero occurrences — pattern not yet used in this codebase
- `discord.PartialMessage` API (verified in discord.py 2.6.4)
  - `discord.TextChannel.get_partial_message(id: int) -> discord.PartialMessage`
  - `discord.PartialMessage` exposes: `.edit()`, `.delete()`, `.id`, `.channel`
  - No network call — constructed entirely from the given integer ID
- Bot intents: `guilds=True, guild_messages=True, members=True` — no `message_content`
  - Intents govern gateway event content, not REST calls; no additional intent is needed for `.edit()` or `.delete()`

### Project Conventions

- Bot already uses `bot.get_channel()` (in-memory cache) over `bot.fetch_channel()` (REST); same principle applies here
- Existing error handling catches `discord.NotFound` and `discord.HTTPException`; that pattern must be preserved

## Key Discoveries

### Why `fetch_message` Is Unnecessary for Edit/Delete

Discord's REST API enforces only two requirements for `PATCH /channels/{channel_id}/messages/{message_id}` and `DELETE /...`:

1. The bot is the message author, **or**
2. The bot has `MANAGE_MESSAGES` in that channel

All three affected call sites operate exclusively on messages the bot sent itself via `channel.send()`. The message ID is stored in the database at send time. The current full `Message` object returned by `fetch_message()` is never read — the next line immediately replaces its entire content or deletes it.

`channel.get_partial_message(int(message_id))` returns a `discord.PartialMessage` with `.edit()` and `.delete()` that issue exactly the same REST calls as on a full `Message` object, without a preceding GET.

### Affected Methods and Their Required Changes

**1. `_fetch_message_for_refresh(channel, message_id)` → delete the method**

Currently: fetches a `Message`, returns it (or `None` on `NotFound`).

After change: callers use `channel.get_partial_message(int(message_id))` directly. `PartialMessage.edit()` raises `discord.NotFound` the same way as a full message, so the `NotFound` guard moves to the caller. The method is eliminated entirely.

**2. `_fetch_channel_and_message(channel_id, message_id)` → change return to `(channel, partial_message)`**

Currently: returns `(channel, message)` after issuing `channel.fetch_message()`.

After change:

- Remove `channel.fetch_message()` call
- Replace with `channel.get_partial_message(int(message_id))`
- Return type changes from `tuple[TextChannel, Message] | None` to `tuple[TextChannel, PartialMessage] | None`
- The `discord.NotFound` / general `Exception` handling wrapping the old `fetch_message` is removed
- All callers (`_update_message_for_player_removal`, `_handle_game_cancelled`, `_try_edit_game_message`) receive a `PartialMessage` and call `.edit()` or `.delete()` on it — those callers already have their own `discord.NotFound` exception handlers, so behaviour is unchanged

**3. `_archive_game_announcement(game)` → inline swap**

Currently:

```python
message = await channel.fetch_message(int(game.message_id))
await message.delete()
```

After change:

```python
message = channel.get_partial_message(int(game.message_id))
await message.delete()
```

The surrounding `except discord.NotFound` block stays — it now catches the `NotFound` that `.delete()` raises if the message is already gone.

### `_update_message_for_player_removal` — error handling note

Currently the `NotFound` guard is inside `_fetch_channel_and_message`. After the change, `_fetch_channel_and_message` always returns successfully (no fetch). The `discord.NotFound` case will surface from the `.edit()` call inside `_update_message_for_player_removal`, which already has its own `except discord.NotFound` handler at line ~988. No new error handling is needed.

### Test Changes

**`test_fetch_message_for_refresh_success`** and **`test_fetch_message_for_refresh_not_found`** — delete both; the method they test is removed.

**`test_fetch_channel_and_message_success`** — remove the `mock_channel.fetch_message` setup and the `mock_channel.fetch_message.assert_called_once_with(...)` assertion. Add assertion that `mock_channel.get_partial_message` was called with `int(message_id)`.

**`test_fetch_channel_and_message_message_not_found`** and **`test_fetch_channel_and_message_fetch_error`** — delete both; `_fetch_channel_and_message` no longer makes a network call, so those error paths are gone. The `NotFound` scenario is now tested at the caller level.

**`test_update_message_for_player_removal_success`** — update to use `mock_channel.get_partial_message` instead of `mock_channel.fetch_message`.

**`test_update_message_for_player_removal_message_not_found`** — update to have `mock_message.edit.side_effect = discord.NotFound(...)` instead of `mock_channel.fetch_message.side_effect`.

**`test_archive_game_announcement_deletes_original`** and **`test_archive_game_announcement_posts_to_archive_channel`** — swap `mock_channel.fetch_message = AsyncMock(return_value=mock_message)` for `mock_channel.get_partial_message = MagicMock(return_value=mock_message)` (note: sync, not async — `get_partial_message` is not a coroutine). Remove assertions on `fetch_message`; assert `get_partial_message` was called.

**`test_channel_worker`** — update similarly.

### Complete Example

```python
# Before
async def _fetch_channel_and_message(
    self,
    channel_id: str,
    message_id: str,
) -> tuple[discord.TextChannel, discord.Message] | None:
    channel = self.bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        logger.error("Invalid or inaccessible channel: %s", channel_id)
        return None
    try:
        message = await channel.fetch_message(int(message_id))
        return (channel, message)
    except Exception as e:
        logger.error("Failed to fetch message %s: %s", message_id, e)
        return None

# After
def _get_channel_and_partial_message(
    self,
    channel_id: str,
    message_id: str,
) -> tuple[discord.TextChannel, discord.PartialMessage] | None:
    channel = self.bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.TextChannel):
        logger.error("Invalid or inaccessible channel: %s", channel_id)
        return None
    return (channel, channel.get_partial_message(int(message_id)))
```

Note: the method becomes synchronous (`def` not `async def`) — all callers must drop the `await`.

## Recommended Approach

Single commit touching `services/bot/events/handlers.py` and its tests:

1. Delete `_fetch_message_for_refresh()` — update `_refresh_game_message()` to inline `channel.get_partial_message()`
2. Rename `_fetch_channel_and_message()` to `_get_channel_and_partial_message()`, make it synchronous, remove `fetch_message`, return `PartialMessage`
3. Patch `_archive_game_announcement()` inline
4. Update all callers to drop `await` on the renamed method
5. Update tests as described above

## Implementation Guidance

- **Objectives**: Eliminate three `channel.fetch_message()` REST GET calls that exist solely to obtain an object for `.edit()` or `.delete()`
- **Key Tasks**:
  1. Replace `_fetch_message_for_refresh` with direct `get_partial_message` inline
  2. Refactor `_fetch_channel_and_message` → `_get_channel_and_partial_message` (sync)
  3. Update `_archive_game_announcement` inline
  4. Update affected unit tests
- **Dependencies**: discord.py 2.6.4 already available; no package changes
- **Success Criteria**: No `channel.fetch_message` calls outside of the sweep loop in `bot.py`; all unit tests pass
