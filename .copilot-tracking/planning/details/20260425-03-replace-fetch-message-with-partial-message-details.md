<!-- markdownlint-disable-file -->

# Task Details: Replace fetch_message REST Calls with PartialMessage

## Research Reference

**Source Research**: #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md

## Phase 1: RED — Add xfail tests for `_get_channel_and_partial_message`

### Task 1.1: Write xfail tests for the new synchronous `_get_channel_and_partial_message` method

Add three new unit tests to the existing test class in `test_handlers.py` (the class containing `test_fetch_channel_and_message_*`). The method does not yet exist, so mark each test `@pytest.mark.xfail(strict=True)`.

Test cases to add after `test_fetch_channel_and_message_fetch_error` (line 2381):

1. `test_get_channel_and_partial_message_success` — `bot.get_channel` returns a `TextChannel`; call is `event_handlers._get_channel_and_partial_message(channel_id, message_id)` (no `await`); assert result is `(mock_channel, mock_partial_message)`; assert `mock_channel.get_partial_message.assert_called_once_with(int(message_id))`; assert `mock_bot.fetch_channel` was not called; note that `get_partial_message` must be a `MagicMock` (not `AsyncMock`) because it is synchronous
2. `test_get_channel_and_partial_message_channel_not_in_cache` — `bot.get_channel` returns `None`; result is `None`
3. `test_get_channel_and_partial_message_wrong_channel_type` — `bot.get_channel` returns a `discord.VoiceChannel` mock; result is `None`

- **Files**:
  - `tests/unit/services/bot/events/test_handlers.py` — add three tests after line 2393
- **Success**:
  - `uv run pytest tests/unit/services/bot/events/test_handlers.py -k "get_channel_and_partial_message" -v` shows all three as `xfailed`
  - No existing tests are broken
- **Research References**:
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 97–109) — test update specifications
- **Dependencies**:
  - None (production changes come in Phase 2)

## Phase 2: GREEN — Implement refactoring and update all tests

### Task 2.1: Refactor `_fetch_channel_and_message` → `_get_channel_and_partial_message`

Replace the body of `_fetch_channel_and_message` (lines 356–400 in `handlers.py`):

- Rename to `_get_channel_and_partial_message`
- Change `async def` → `def` (synchronous)
- Remove `channel.fetch_message()` call and its surrounding `try/except`
- Replace with `channel.get_partial_message(int(message_id))`
- Update return type annotation to `tuple[discord.TextChannel, discord.PartialMessage] | None`
- Remove the redundant double `if not channel` check (keep only one guard)

Full after-state shown in research lines 140–165.

- **Files**:
  - `services/bot/events/handlers.py` (lines 356–400) — replace method
- **Success**:
  - `_get_channel_and_partial_message` is `def` (not `async def`)
  - No `channel.fetch_message` call inside the method
- **Research References**:
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 60–75) — change specification
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 140–165) — complete before/after example
- **Dependencies**:
  - Task 1.1 complete (xfail tests exist)

### Task 2.2: Delete `_fetch_message_for_refresh` and inline in `_refresh_game_message`

Delete `_fetch_message_for_refresh` entirely (lines 337–355 in `handlers.py`).

In `_refresh_game_message` (line 418), replace:

```python
message = await self._fetch_message_for_refresh(channel, game.message_id)
if not message:
    return
```

with:

```python
message = channel.get_partial_message(int(game.message_id))
```

No `NotFound` guard needed at this stage — if the message is gone, `_update_game_message_content` will call `.edit()` which raises `discord.NotFound`, caught by the outer `except Exception` block.

- **Files**:
  - `services/bot/events/handlers.py` (lines 337–355) — delete `_fetch_message_for_refresh`
  - `services/bot/events/handlers.py` (lines 418–420) — replace caller
- **Success**:
  - `grep "_fetch_message_for_refresh" services/bot/events/handlers.py` returns no results
  - `_refresh_game_message` calls `channel.get_partial_message` directly
- **Research References**:
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 46–58) — method 1 change specification
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Update `_archive_game_announcement` to use `get_partial_message` inline

In `_archive_game_announcement` (around line 1294 of `handlers.py`), replace:

```python
message = await channel.fetch_message(int(game.message_id))
await message.delete()
```

with:

```python
message = channel.get_partial_message(int(game.message_id))
await message.delete()
```

The surrounding `except discord.NotFound` block is unchanged — it now catches the `NotFound` that `.delete()` raises if the message is already gone.

- **Files**:
  - `services/bot/events/handlers.py` (~line 1294) — swap `fetch_message` for `get_partial_message`
- **Success**:
  - No `await` before `channel.get_partial_message`
  - `except discord.NotFound` block unchanged
- **Research References**:
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 76–88) — archive announcement change specification
- **Dependencies**:
  - Independent change within the method; no ordering requirement relative to 2.1/2.2

### Task 2.4: Update all callers to use `_get_channel_and_partial_message` without `await`

Three call sites in `handlers.py` must be updated:

1. `_update_message_for_player_removal` (line 974): `result = await self._fetch_channel_and_message(...)` → `result = self._get_channel_and_partial_message(...)`
2. `_handle_game_cancelled` (line 1104): same pattern
3. `_try_edit_game_message` (line 1470): same pattern

- **Files**:
  - `services/bot/events/handlers.py` (lines 974, 1104, 1470) — three call-site updates
- **Success**:
  - `grep "_fetch_channel_and_message" services/bot/events/handlers.py` returns no results
  - `grep "await self._get_channel_and_partial_message" services/bot/events/handlers.py` returns no results
- **Research References**:
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 60–75) — caller update guidance
- **Dependencies**:
  - Task 2.1 (new method name must exist)

### Task 2.5: Remove xfail markers and update/delete all obsolete tests

**Remove xfail markers** from the three `test_get_channel_and_partial_message_*` tests added in Task 1.1.

**Delete these tests** (testing code that has been removed):

- `test_fetch_message_for_refresh_success` (line 2284)
- `test_fetch_message_for_refresh_not_found` (line 2297)
- `test_fetch_channel_and_message_message_not_found` (line 2366)
- `test_fetch_channel_and_message_fetch_error` (line 2381)

**Update these tests** (method renamed, now synchronous — note `_get_channel_and_partial_message` is called without `await`):

- `test_fetch_channel_and_message_success` (line 2308): remove `mock_channel.fetch_message` setup and assertion; add `mock_channel.get_partial_message = MagicMock(return_value=mock_partial_message)`; assert `mock_channel.get_partial_message.assert_called_once_with(int(message_id))`; rename test to `test_get_channel_and_partial_message_success` if Phase 1 tests are deleted to avoid duplication, otherwise keep distinct
- `test_fetch_channel_and_message_channel_not_in_cache` (line 2327): update method name in call
- `test_fetch_channel_and_message_invalid_channel` (line 2340): update method name in call
- `test_fetch_channel_and_message_wrong_channel_type` (line 2353): update method name in call

**Update these tests** (callers changed to use `get_partial_message`):

- `test_update_message_for_player_removal_success` (line 1572): replace `mock_channel.fetch_message = AsyncMock(return_value=mock_message)` with `mock_channel.get_partial_message = MagicMock(return_value=mock_message)`; update assertion from `mock_channel.fetch_message.assert_awaited_once_with(int(message_id))` to `mock_channel.get_partial_message.assert_called_once_with(int(message_id))`
- `test_update_message_for_player_removal_message_not_found` (line 1624): change `mock_channel.fetch_message = AsyncMock(side_effect=discord.NotFound(...))` to `mock_channel.get_partial_message = MagicMock(return_value=mock_message)` plus `mock_message.edit.side_effect = discord.NotFound(MagicMock(), MagicMock())`; update the log message assertion from "Failed to fetch message" to "Game message not found"
- `test_archive_game_announcement_deletes_original` (line 633): replace `mock_channel.fetch_message = AsyncMock(return_value=mock_message)` with `mock_channel.get_partial_message = MagicMock(return_value=mock_message)`; update assertion from `mock_channel.fetch_message.assert_awaited_once_with(...)` to `mock_channel.get_partial_message.assert_called_once_with(int(sample_game.message_id))`
- `test_archive_game_announcement_posts_to_archive_channel` (line 668): same `fetch_message` → `get_partial_message` swap
- `test_refresh_game_message_success` (line 2419): this test patches `_fetch_message_for_refresh`; update to no longer patch that method; instead set `mock_channel.get_partial_message = MagicMock(return_value=mock_message)` and assert `mock_channel.get_partial_message.assert_called_once_with(int(sample_game.message_id))`

- **Files**:
  - `tests/unit/services/bot/events/test_handlers.py` — multiple test updates and deletions
- **Success**:
  - `uv run pytest tests/unit/services/bot/events/test_handlers.py -v` — all pass, no xfail, no failures
  - `grep "fetch_message" tests/unit/services/bot/events/test_handlers.py` returns no results
- **Research References**:
  - #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md (Lines 97–130) — complete test change specifications
- **Dependencies**:
  - Tasks 2.1–2.4 all complete

## Dependencies

- discord.py 2.6.4 (`TextChannel.get_partial_message` is available; no package changes needed)

## Success Criteria

- Zero `channel.fetch_message` calls in `services/bot/events/handlers.py`
- All unit tests pass with no failures or unexpected xfails
- `_get_channel_and_partial_message` is `def` (synchronous), returns `tuple[discord.TextChannel, discord.PartialMessage] | None`
