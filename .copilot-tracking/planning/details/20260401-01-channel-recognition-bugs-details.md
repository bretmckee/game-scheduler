<!-- markdownlint-disable-file -->

# Task Details: Channel Recognition Bug Fixes

## Research Reference

**Source Research**: #file:../research/20260401-01-channel-recognition-bugs-research.md

## Phase 1: Channel Resolver Unit Tests and Fixes (TDD)

### Task 1.1: Write Failing Tests for Channel Resolver Changes

Add `@pytest.mark.xfail(strict=True, reason="Bug: ...")` tests to
`tests/unit/services/api/services/test_channel_resolver.py` covering:

- Emoji/Unicode channel name accepted by hashtag regex (e.g. `#🍻tavern-generalchat`)
- `<#406497579061215235>` with a valid guild channel ID produces no error
- `<#999999999999999999>` with an unknown ID produces a `not_found` error entry
- `render_where_display(None, [...])` returns `None`
- `render_where_display("<#123> and <#456>", [{id: "123", ...}, {id: "456", ...}])` returns `"#foo and #bar"`

- **Files**:
  - `tests/unit/services/api/services/test_channel_resolver.py` — add xfail tests
- **Success**:
  - `pytest tests/unit/services/api/services/test_channel_resolver.py` runs with all new tests reporting `xfail`
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 101-135) — Bug 1, Bug 2, Bug 3 descriptions and fix specs
- **Dependencies**:
  - None

### Task 1.2: Fix Hashtag Regex to Accept Emoji/Unicode (Bug 1 GREEN)

In `services/api/services/channel_resolver.py`, change the hashtag match
pattern from `#([\w-]+)` to `(?<!<)#([^\s<>]+)`. The negative lookbehind
`(?<!<)` prevents the `#` inside a stored `<#id>` token from being matched.

- **Files**:
  - `services/api/services/channel_resolver.py` — update regex pattern
- **Success**:
  - Task 1.1 xfail test for emoji channel name now passes; `xfail` marker removed
  - Existing resolver tests continue to pass
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 101-112) — Bug 1 fix specification
- **Dependencies**:
  - Task 1.1 (xfail test must exist and be confirmed failing before implementing)

### Task 1.3: Add `<#snowflake>` Input Handling (Bug 2 GREEN)

In `services/api/services/channel_resolver.py`, before the hashtag loop, add
a loop over `<#(\d+)>` matches: if the numeric ID is present in the guild
channel list, leave the text unchanged (no error); if not found, append a
`not_found` error to the result.

- **Files**:
  - `services/api/services/channel_resolver.py` — add `<#(\d+)>` handling loop
- **Success**:
  - Task 1.1 xfail tests for valid and invalid `<#id>` inputs now pass; `xfail` markers removed
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 112-123) — Bug 2 fix specification
- **Dependencies**:
  - Task 1.1

### Task 1.4: Add `render_where_display` Function (GREEN)

In `services/api/services/channel_resolver.py`, add module-level function
`render_where_display(where: str | None, channels: list[dict]) -> str | None`.
It should:

- Return `None` if `where` is `None`
- Replace each `<#id>` token with `#name` using the provided channel list
- Leave tokens unchanged if the channel ID is not present in the list

This is a new function; stub it with `raise NotImplementedError` before Task 1.1
tests are written, then implement to make tests pass.

- **Files**:
  - `services/api/services/channel_resolver.py` — add new function (stub then implement)
- **Success**:
  - Task 1.1 xfail tests for `render_where_display` now pass; `xfail` markers removed
  - All Task 1.1 failing tests are passing and `xfail` markers removed
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 136-164) — `where_display` approach and `render_where_display` spec
- **Dependencies**:
  - Task 1.1

## Phase 2: Backend Schema and API Response (TDD)

### Task 2.1: Write Failing Test for `where_display` in `_build_game_response`

In `tests/unit/services/api/routes/test_games_helpers.py`, add an `xfail` test
asserting that `_build_game_response` sets `where_display` to the human-readable
channel name when `game.where` contains a `<#id>` token.

- **Files**:
  - `tests/unit/services/api/routes/test_games_helpers.py` — add xfail test
- **Success**:
  - New test reports `xfail`
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 165-183) — Step 5 from recommended backend changes and `_build_game_response` discovery
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Add `where_display` Field to `GameResponse`

In `shared/schemas/game.py`, add to `GameResponse`:

```python
where_display: str | None = Field(None, description="Game location with channel IDs resolved to display names")
```

- **Files**:
  - `shared/schemas/game.py` — add field to `GameResponse`
- **Success**:
  - `GameResponse` serializes with a `where_display` key
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 165-170) — Step 4 schema change
- **Dependencies**:
  - Phase 1 complete (for `render_where_display` to exist)

### Task 2.3: Populate `where_display` in `_build_game_response` (GREEN)

In `services/api/routes/games.py`, inside `_build_game_response`:

1. Call `get_guild_channels` for the game's guild via the global
   `DiscordAPIClient` singleton (Redis-cached; cheap to call).
2. Call `render_where_display(game.where, channels)` and assign the result to
   `where_display` in the `GameResponse` constructor.

The call pattern should mirror how `fetch_channel_name_safe` is already used
in the route helpers.

- **Files**:
  - `services/api/routes/games.py` — update `_build_game_response`
- **Success**:
  - Task 2.1 xfail test now passes; `xfail` marker removed
  - `GET /games/{id}` response includes `where_display: "#🍻tavern-generalchat"` when `where` is `<#id>`
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 38-46) — `_build_game_response` and `fetch_channel_name_safe` discovery
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 170-183) — Step 5 full specification
- **Dependencies**:
  - Tasks 2.1, 2.2 and Phase 1 complete

## Phase 3: Backend — Edit Path (TDD)

### Task 3.1: Write Failing Test for `update_game` Channel Resolution

In the unit test file for `games.py` (likely
`tests/unit/services/api/services/test_games.py`), add an `xfail` test that
calls `update_game` with a `where` value containing `#channel-name` and asserts
the stored value uses `<#id>` format.

- **Files**:
  - `tests/unit/services/api/services/test_games.py` — add xfail test
- **Success**:
  - New test reports `xfail`
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 18-24) — `update_game` edit path discovery
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 183-192) — Edit path gap and Step 6
- **Dependencies**:
  - Phase 1 complete

### Task 3.2: Add Resolver to `update_game` (GREEN)

In `services/api/services/games.py`, inside `update_game`, add the same
`resolve_channel_mentions` call that `create_game` uses: after
`_update_game_fields`, resolve `update_data.where` if present and raise `422`
on validation errors, matching the `create_game` pattern exactly.

- **Files**:
  - `services/api/services/games.py` — add resolver call to `update_game`
- **Success**:
  - Task 3.1 xfail test now passes; `xfail` marker removed
  - Editing a game with `#channel-name` in Location stores `<#id>` in DB
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 13-17) — `create_game` call site as the reference pattern
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 183-192) — Step 6 specification
- **Dependencies**:
  - Task 3.1 and Phase 1 complete

## Phase 4: Frontend — Types and Display

### Task 4.1: Add `where_display` to `GameSession` Type

In `frontend/src/types/index.ts`, add `where_display?: string | null` to the
`GameSession` interface.

- **Files**:
  - `frontend/src/types/index.ts` — update `GameSession`
- **Success**:
  - No TypeScript errors after adding `where_display` references in components
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 56-60) — `GameSession.where` type discovery and Step 7
- **Dependencies**:
  - Phase 2 complete (schema must exist before frontend consumes it)

### Task 4.2: Render `where_display` in `GameCard` and `GameDetails`

In `frontend/src/components/GameCard.tsx` (line 186) and
`frontend/src/pages/GameDetails.tsx` (line 313), replace `game.where` with
`game.where_display ?? game.where` so the human-readable channel name is shown
in all read-only views with a fallback for backwards compatibility.

- **Files**:
  - `frontend/src/components/GameCard.tsx` — update line 186
  - `frontend/src/pages/GameDetails.tsx` — update line 313
- **Success**:
  - `GameCard` and `GameDetails` display `#🍻tavern-generalchat` instead of `<#406497579061215235>`
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 62-68) — `GameCard` and `GameDetails` render discovery
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 192-199) — Steps 8
- **Dependencies**:
  - Task 4.1

### Task 4.3: Update `GameForm` Pre-populate and Suggestion Click Handler (Bug 3 GREEN)

In `frontend/src/components/GameForm.tsx`:

1. Change the `where` pre-population to use
   `initialData?.where_display ?? initialData?.where` so the edit form shows
   the human-readable channel name.
2. Add an internal `handleChannelSuggestionClick(originalInput: string, newChannelName: string)`
   function that replaces `originalInput` in `formData.where` with
   `newChannelName`, then calls `onChannelValidationErrorClick?.()`. This
   mirrors the existing `handleChannelSuggestionClick` for participants.

- **Files**:
  - `frontend/src/components/GameForm.tsx` — update pre-populate (near line 651) and add suggestion handler
- **Success**:
  - Edit form pre-populates with `#🍻tavern-generalchat` instead of `<#406497579061215235>`
  - Clicking a suggestion chip updates the Location field value (Bug 3 fixed)
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 68-79) — `GameForm` discovery (Bug 3 root cause)
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 123-135) — Bug 3 description
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 199-205) — Steps 9-10
- **Dependencies**:
  - Task 4.1

## Phase 5: Frontend — EditGame 422 Handling

### Task 5.1: Add `channelValidationErrors` State to `EditGame`

In `frontend/src/pages/EditGame.tsx`, add
`const [channelValidationErrors, setChannelValidationErrors] = useState<...>(null)`
matching the type and initial value used in `CreateGame.tsx`.

- **Files**:
  - `frontend/src/pages/EditGame.tsx` — add state declaration
- **Success**:
  - No TypeScript errors after adding the state
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 80-95) — `EditGame` and `CreateGame` discovery
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 205-215) — Steps 11-13
- **Dependencies**:
  - Phase 4 complete

### Task 5.2: Parse Channel Errors from 422 in `EditGame`

In `frontend/src/pages/EditGame.tsx`, update the 422 response handler to parse
`invalid_mentions` the same way `CreateGame.tsx` does: split by `type` field
into participant vs. channel errors, and call `setChannelValidationErrors` with
the channel error data.

- **Files**:
  - `frontend/src/pages/EditGame.tsx` — update 422 handler
- **Success**:
  - Submitting an invalid channel name when editing displays the same suggestion UI as when creating
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 80-95) — `EditGame` 422 gap discovery
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 205-215) — Step 12 and `CreateGame.tsx` pattern reference
- **Dependencies**:
  - Task 5.1

### Task 5.3: Pass Channel Validation Props to `GameForm` in `EditGame`

In `frontend/src/pages/EditGame.tsx`, add a `handleChannelSuggestionClick`
callback (clears `channelValidationErrors`) and pass
`channelValidationErrors={channelValidationErrors}` and
`onChannelValidationErrorClick={handleChannelSuggestionClick}` to `<GameForm>`,
matching the `CreateGame.tsx` pattern.

- **Files**:
  - `frontend/src/pages/EditGame.tsx` — update `GameForm` usage
- **Success**:
  - Clicking a suggestion chip while editing clears the validation UI and updates the Location field
- **Research References**:
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 80-95) — `EditGame` `GameForm` usage discovery
  - #file:../research/20260401-01-channel-recognition-bugs-research.md (Lines 205-215) — Step 13
- **Dependencies**:
  - Tasks 5.1, 5.2 and Task 4.3

## Dependencies

- Python 3.12+, FastAPI, pytest
- React 18+, TypeScript 5, Vitest

## Success Criteria

- `#🍻tavern-generalchat` in Location resolves correctly at both create and edit time
- `<#406497579061215235>` in Location is silently accepted when the ID is valid in the guild
- Clicking a suggestion chip populates the Location field with the channel name (Bug 3 fixed)
- `GameCard` and `GameDetails` render the human-readable channel name, not `<#id>` tokens
- Edit form pre-populates Location with the human-readable channel name
- All unit tests pass with `xfail` markers removed after each fix
