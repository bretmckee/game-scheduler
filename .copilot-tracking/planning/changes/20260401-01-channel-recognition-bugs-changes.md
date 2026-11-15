# Changes: Channel Recognition Bug Fixes

## Status

All phases complete.

## Added

- `services/api/services/channel_resolver.py` — Added module-level `render_where_display(where, channels)` function that replaces `<#id>` tokens with `#name` using a pre-fetched channel list
- `services/api/services/channel_resolver.py` — Added private `_check_snowflake_tokens` helper method to `ChannelResolver` that validates `<#id>` tokens against the guild channel list
- `shared/discord/client.py` — Added module-level `get_guild_channels_safe(guild_id, client)` helper that fetches guild channels via the global client singleton with error handling (returns `[]` on failure), following the `fetch_channel_name_safe` pattern
- `tests/unit/services/api/routes/test_games_helpers.py` — Added `TestBuildGameResponse` class with test asserting `where_display` is populated by `render_where_display` when `game.where` contains a `<#id>` token

## Modified

- `services/api/services/channel_resolver.py` — Changed `_channel_mention_pattern` regex from `#([\w-]+)` to `(?<!<)#([^\s<>]+)` to accept emoji/Unicode channel names (Bug 1 fix)
- `services/api/services/channel_resolver.py` — Added `_snowflake_token_pattern` and snowflake detection to `resolve_channel_mentions`; valid `<#id>` tokens pass through silently, invalid ones produce a `not_found` error (Bug 2 fix)
- `shared/schemas/game.py` — Added `where_display: str | None` field to `GameResponse` with default `None`
- `services/api/routes/games.py` — Updated `_build_game_response` to call `get_guild_channels_safe` and `render_where_display`, populating `where_display` in `GameResponse`; also imported `get_guild_channels_safe`
- `services/api/services/games.py` — Added channel resolver call in `update_game` after `_update_game_fields`: resolves `game.where` through `channel_resolver.resolve_channel_mentions` when `update_data.where is not None`, raising `ValidationError` on invalid mentions (mirrors `create_game` pattern)
- `tests/unit/services/api/routes/test_channel_resolver.py` — Added 5 regression tests: emoji channel name resolution, valid `<#id>` token accepted, unknown `<#id>` token error, `render_where_display` with `None`, and `render_where_display` token substitution; all written as `xfail` first then made passing
- `tests/unit/services/api/routes/test_games_helpers.py` — Added `_build_game_response` and `ParticipantResponse` to imports
- `tests/unit/services/api/routes/test_games_participant_count.py` — Added `get_guild_channels_safe` patch to all 4 tests that call `_build_game_response`
- `tests/unit/services/api/routes/test_games_timezone.py` — Added `get_guild_channels_safe` patch to all 4 tests that call `_build_game_response`
- `tests/unit/services/api/services/test_games_service.py` — Added `test_update_game_resolves_channel_mention_in_where` regression test (written as `xfail`, made passing); updated `test_update_game_where_field` to mock `resolve_channel_mentions` return value after resolver was added to `update_game`
- `frontend/src/pages/EditGame.tsx` — Added `ChannelValidationError` interface, `channelValidationErrors` state, updated `handleSubmit` 422 handler to split `invalid_mentions` by `type` into participant vs. channel errors calling `setChannelValidationErrors`, added `handleChannelSuggestionClick` callback that clears `channelValidationErrors`, and passed `channelValidationErrors` and `onChannelValidationErrorClick` props to `<GameForm>` (mirrors `CreateGame.tsx` pattern)
- `frontend/src/pages/__tests__/EditGame.test.tsx` — Added `StatusCodes` import and two regression tests: channel 422 response renders `ChannelValidationErrors` UI, and clicking a suggestion chip clears the errors (written as `it.fails`, made passing)

## Removed

None.

## Divergences from Plan

None.

---

<!-- Merged from the former .copilot-tracking/changes/ copy of this log -->

# Changes: Channel Recognition Bug Fixes

## Summary

Fix three bugs in channel name recognition and display: emoji/Unicode in channel
names rejected by regex, `<#snowflake>` input not handled, clicking a suggestion
chip does not update the Location field; also add `where_display` so the web UI
renders human-readable channel names.

---

## Phase 1: Channel Resolver Unit Tests and Fixes (TDD)

### Added

- `tests/unit/test_channel_resolver.py` — xfail regression tests for emoji/Unicode
  in hashtag regex, `<#id>` token acceptance, and `render_where_display` function

### Modified

- `services/api/services/channel_resolver.py` — Fixed `HASHTAG_RE` to accept
  emoji and Unicode; added `<#snowflake>` branch that validates the ID via
  `fetch_channel_name_safe`; added `render_where_display` helper that converts
  stored `where` tokens to human-readable channel names

---

## Phase 2: Backend Schema and API Response (TDD)

### Added

- `tests/unit/test_build_game_response.py` — xfail test asserting `where_display`
  is populated in `_build_game_response`

### Modified

- `shared/schemas/game.py` — Added `where_display: str | None` field to `GameResponse`
- `services/api/routes/games.py` — Populated `where_display` in `_build_game_response`
  by calling `render_where_display` from the channel resolver

---

## Phase 3: Backend — Edit Path (TDD)

### Added

- `tests/unit/test_update_game_channel_resolution.py` — xfail test asserting
  `update_game` calls the channel resolver and accepts `<#id>` and `#🍻emoji`
  inputs

### Modified

- `services/api/services/games.py` — Added `resolve_channel` call in `update_game`
  matching the create path so all inputs are validated and normalized

---

## Phase 4: Frontend — Types and Display

### Modified

- `frontend/src/types/index.ts` — Added `where_display?: string | null` to `GameSession`
- `frontend/src/components/GameCard.tsx` — Render `game.where_display ?? game.where`
  so human-readable name is shown instead of raw `<#id>` token
- `frontend/src/pages/GameDetails.tsx` — Render `game.where_display ?? game.where`
  in the Where section with the same fallback
- `frontend/src/components/GameForm.tsx` — Pre-populate `where` with
  `initialData?.where_display ?? initialData?.where`; added internal
  `handleChannelSuggestionClick` that updates `formData.where` before calling the
  parent callback (Bug 3 fix)

### Added

- `frontend/src/components/__tests__/GameCard.where_display.test.tsx` — Tests that
  `GameCard` shows `where_display` when present and falls back to `where`
- `frontend/src/pages/__tests__/GameDetails.where_display.test.tsx` — Tests that
  `GameDetails` shows `where_display` when present and falls back to `where`
- `frontend/src/components/__tests__/GameForm.where_display.test.tsx` — Tests for
  pre-populate using `where_display` and suggestion-chip click updating the
  Location field
