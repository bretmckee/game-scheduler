<!-- markdownlint-disable-file -->

# Task Research Notes: Channel Recognition Bug Fixes

## Research Executed

### File Analysis

- `services/api/services/channel_resolver.py`
  - Core resolver; two input patterns: `https://discord.com/channels/guild/channel` URLs and `#([\w-]+)` hashtag mentions
  - Hashtag regex `[\w-]` is ASCII-only — rejects emoji and Unicode, which Discord includes in channel names (e.g. `🍻tavern-generalchat`)
  - No handling for `<#snowflake>` — the `#` inside it is partially matched by the hashtag regex, extracting the numeric ID as a "channel name", which then fails lookup with no useful suggestions
  - Resolved text stores `<#channel_id>` format; this is only done at create time

- `services/api/services/games.py`
  - `create_game`: calls `resolve_channel_mentions`, stores resolved `<#id>` text in DB
  - `update_game` → `_update_game_fields` → `_update_simple_text_fields`: assigns `game.where = update_data.where` directly — resolver is **never called on edit**

- `services/api/routes/games.py`
  - `_build_game_response`: calls `_fetch_discord_names` for channel/guild display names, then returns `where=game.where` (the raw stored string) with no display transformation
  - Uses `fetch_channel_name_safe` / `fetch_guild_name_safe` via the global `DiscordAPIClient` singleton — no injected dependency needed for response helpers

- `shared/discord/client.py`
  - `DiscordAPIClient.get_guild_channels`: fetches all guild channels with Redis caching; returns full objects including `id`, `name`, `type`
  - `fetch_channel_name_safe`: module-level helper using the global client singleton; safe to call from `_build_game_response`
  - Channel `name` field from Discord API includes emoji (e.g. `🍻tavern-generalchat`)

- `shared/schemas/game.py`
  - `GameResponse`: has `where: str | None` — no display variant field

- `frontend/src/types/index.ts`
  - `GameSession.where: string | null` — matches stored form; no display variant

- `frontend/src/components/GameCard.tsx`
  - Renders `{game.where}` as raw JSX text — no channel list available at this level
  - No guild channel fetch; only has `channel_id`/`channel_name` from the game object itself

- `frontend/src/pages/GameDetails.tsx`
  - Same pattern: `{game.where}` as raw text, no channel list fetch

- `frontend/src/components/GameForm.tsx`
  - `formData.where` pre-populated from `initialData?.where` — receives raw stored string in edit mode
  - `handleChannelSuggestionClick` in `GameForm` only exists for participants (updates `formData.participants`); the channel equivalent is missing — clicking a channel suggestion only clears errors via the parent page callback, it does NOT update `formData.where`

- `frontend/src/pages/CreateGame.tsx`
  - Parses `invalid_mentions` from 422 response; splits by presence of `type` field into participant vs channel errors
  - `handleChannelSuggestionClick`: clears `channelValidationErrors` and `error` only — ignores both callback parameters
  - Passes `onChannelValidationErrorClick={handleChannelSuggestionClick}` to `GameForm`

- `frontend/src/pages/EditGame.tsx`
  - Has NO `channelValidationErrors` state
  - 422 handler only checks for `invalid_mentions` with participant errors; channel errors from the response are silently discarded
  - Passes no `channelValidationErrors` or `onChannelValidationErrorClick` props to `GameForm`
  - Note: currently moot because `update_game` never calls the resolver — but must be fixed when resolver is added to the edit path

- `services/bot/formatters/game_message.py`
  - `embed.add_field(name="Where", value=where, inline=True)` — passes raw stored string directly to Discord embed
  - Discord natively renders `<#id>` as a clickable channel link in embeds — this is correct and intentional

### Code Search Results

- `resolve_channel_mentions` call sites
  - Called only once: `games.py::create_game` — not called from `update_game`

- `_build_game_response` call sites
  - Called from: `create_game`, `get_game`, `list_games`, `update_game` route handlers — every GET/POST/PUT response goes through it

- `where` render in frontend
  - `GameCard.tsx:186`: `{game.where}` — raw text
  - `GameDetails.tsx:313`: `{game.where}` — raw text
  - `GameForm.tsx:651`: `value={formData.where}` — raw stored value in edit input

## Key Discoveries

### Three Distinct Bugs

**Bug 1 — Emoji/Unicode in channel names**
Discord channel names can contain emoji (e.g. `🍻tavern-generalchat`). The regex `#([\w-]+)` uses `[\w-]` which in Python matches only ASCII word characters (`[A-Za-z0-9_]`) plus hyphen. A user who copies a Discord channel name containing an emoji prefix and types `#🍻tavern-generalchat` gets a "not found" error.

Fix: change pattern to `(?<!<)#([^\s<>]+)`. The negative lookbehind `(?<!<)` is critical — without it, the `#` inside a stored `<#406497579061215235>` would be matched, extracting the numeric ID as a "channel name".

**Bug 2 — `<#snowflake>` input not recognized**
Users who copy a Discord channel link from the client UI get `<#406497579061215235>` format. The current code has no handler for this. The hashtag regex partially matches it (extracting `406497579061215235` as a channel "name"), fails the lookup, and returns a confusing "not found" error with substring-match suggestions.

Fix: add explicit handling for `<#(\d+)>` — if the ID is valid in the guild, leave text unchanged (success); if invalid, return a clear error. The lookbehind in the regex fix (Bug 1) also prevents double-processing.

**Bug 3 — Suggestion chip click clears error but doesn't update the field**
In `CreateGame.tsx`, `handleChannelSuggestionClick` ignores both its parameters and only calls `setChannelValidationErrors(null)`. The `where` field in the form is never updated. The participant suggestion handler in `GameForm.tsx` correctly updates `formData.participants` — the channel equivalent needs the same treatment.

Fix: add `handleChannelSuggestionClick` inside `GameForm.tsx` that replaces `originalInput` in `formData.where` with `newChannelName`, then calls the parent `onChannelValidationErrorClick` to clear state.

### `where` Storage and Display Gap

- **Stored format**: `<#406497579061215235>` (after create-time resolution)
- **Discord embed**: renders `<#id>` natively as `#🍻tavern-generalchat` — correct
- **Web UI** (`GameCard`, `GameDetails`): renders raw string — displays literal `<#406497579061215235>` — broken
- **Edit form** (`GameForm`): pre-populates with raw stored value — user sees cryptic snowflake ID

**Selected approach: Option A — `where_display` field in API response**

`_build_game_response` already calls `get_guild_channels` (indirectly via `fetch_channel_name_safe`); the global Discord client singleton is available there. Add a `render_where_display` function to `channel_resolver.py` that substitutes `<#id>` tokens in a stored string with `#channel-name` by looking up each ID in the already-fetched channel list. Return this as `where_display: str | None` alongside `where` in `GameResponse`.

- Frontend uses `where_display` for all read-only rendering and pre-populating the edit form
- Frontend submits `where` (the original stored value) unchanged on edit — no change to the submit path needed when the user hasn't touched the Location field
- When user clicks a suggestion chip, the field is updated with `#channel-name` (the human-readable form), which the backend then resolves to `<#id>` on submit — correct round-trip

### Edit Path Gap

`update_game` never calls `resolve_channel_mentions`. A user editing the Location field and typing `#channel-name` saves it as the literal string, not as `<#id>`. The Discord embed would then render `#channel-name` as plain text, not a link.

Fix: add the same resolver call to `update_game` that `create_game` has, and add `channelValidationErrors` state + 422 parsing to `EditGame.tsx`.

## Recommended Approach

### Backend changes

1. **`channel_resolver.py`**: Change hashtag regex to `(?<!<)#([^\s<>]+)` — allows emoji/Unicode, ignores `<#id>` tokens
2. **`channel_resolver.py`**: Add `<#(\d+)>` handling loop: valid ID → no-op; invalid ID → `not_found` error
3. **`channel_resolver.py`**: Add module-level `render_where_display(where: str | None, channels: list[dict]) -> str | None` — replaces `<#id>` tokens with `#name` using a pre-fetched channel list; returns `None` if input is `None`
4. **`shared/schemas/game.py`**: Add `where_display: str | None = Field(None, description="Game location with channel IDs resolved to display names")`
5. **`services/api/routes/games.py`**: In `_build_game_response`: after fetching channels (needed anyway for `_fetch_discord_names`), call `render_where_display(game.where, channels)` and populate `where_display` in `GameResponse`. Since `_fetch_discord_names` currently only grabs the _posting_ channel name (via `fetch_channel_name_safe` on `game.channel.channel_id`), we need to call `get_guild_channels` here — the result is Redis-cached so cheap.
6. **`services/api/services/games.py`**: Add same resolver call in `update_game` between field update and participant update, matching the `create_game` pattern exactly.

### Frontend changes

7. **`frontend/src/types/index.ts`**: Add `where_display?: string | null` to `GameSession`
8. **`frontend/src/components/GameCard.tsx` and `frontend/src/pages/GameDetails.tsx`**: Render `game.where_display ?? game.where` (fallback for backwards compatibility)
9. **`frontend/src/components/GameForm.tsx`**: Pre-populate `where` from `initialData?.where_display ?? initialData?.where` so edit form shows human-readable names
10. **`frontend/src/components/GameForm.tsx`**: Add internal `handleChannelSuggestionClick(originalInput, newChannelName)` that updates `formData.where` (replaces `originalInput` with `newChannelName`), then calls `onChannelValidationErrorClick`
11. **`frontend/src/pages/EditGame.tsx`**: Add `channelValidationErrors` state
12. **`frontend/src/pages/EditGame.tsx`**: Add channel error parsing to the 422 handler (same logic as `CreateGame.tsx`)
13. **`frontend/src/pages/EditGame.tsx`**: Pass `channelValidationErrors` and `onChannelValidationErrorClick` props to `GameForm`

### Tests to add/update

- `tests/unit/services/api/services/test_channel_resolver.py`: add tests for `<#id>` input (valid, invalid), emoji channel names, `render_where_display`
- `tests/unit/services/api/routes/test_games_helpers.py`: update `_build_game_response` tests to assert `where_display` is populated
- `frontend/src/components/__tests__/ChannelValidationErrors.test.tsx`: existing tests pass through; add test for chip click calling `onSuggestionClick` with correct args
- `frontend/src/components/__tests__/GameForm` (if exists) or new file: test that suggestion click updates `formData.where`

## Implementation Guidance

- **Objectives**: fix all three user-reported bugs; ensure `where` field displays correctly in web UI and edit form; make edit path behave identically to create path for channel resolution
- **Key Tasks**: see numbered list above (13 items across 7 files + tests)
- **Dependencies**: `render_where_display` must be implemented before `_build_game_response` change; `where_display` schema field must exist before frontend consumes it
- **Success Criteria**:
  - Entering `<#406497579061215235>` in Location is accepted silently if the ID is valid
  - Entering `#🍻tavern-generalchat` resolves correctly
  - Clicking a suggestion chip populates the Location field with the channel name
  - `GameDetails` and `GameCard` show `#🍻tavern-generalchat`, not `<#406497579061215235>`
  - Edit form pre-populates Location with the human-readable channel name
  - Editing and saving a game with a channel in Location resolves it correctly
