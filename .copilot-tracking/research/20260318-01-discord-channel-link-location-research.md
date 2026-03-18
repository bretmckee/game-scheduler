<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Channel Link Resolution in Game Location

## Research Executed

### File Analysis

- `services/api/services/channel_resolver.py`
  - `ChannelResolver.resolve_channel_mentions()` is the single method handling all channel resolution
  - Fetches all guild channels from Discord API, filters to `type == 0` (text channels only)
  - Returns `(resolved_text, errors)` tuple; callers raise `ValidationError` on any errors
  - Already compiled regex `_channel_mention_pattern = re.compile(r"#([\w-]+)")`
  - No URL detection exists today — discord.com channel links pass through unmodified
- `services/api/services/games.py` lines 610–632
  - Calls `resolve_channel_mentions(resolved_fields["where"], guild_config.guild_id)`
  - On any errors, raises `resolver_module.ValidationError(invalid_mentions=channel_errors)` — blocking (game not created)
- `services/api/routes/games.py` lines 233–239
  - Catches `ValidationError`, returns HTTP 422 with `{"error": "invalid_mentions", "invalid_mentions": [...]}`
- `frontend/src/components/ChannelValidationErrors.tsx`
  - Renders all channel errors; title is hardcoded `"Could not resolve some #channel mentions"`
  - Renders `err.input` + `err.reason` for each error; suggestion chips use `onSuggestionClick`
  - `type` field is never checked — all errors render identically regardless of type value
- `frontend/src/pages/CreateGame.tsx` lines 51–66
  - `ChannelValidationError` interface: `{ type, input, reason, suggestions }`
  - `channelValidationErrors` state blocks re-submission until cleared
- `tests/unit/services/api/services/test_channel_resolver.py`
  - Fixtures: `mock_discord_client` (MagicMock of `DiscordAPIClient`), `resolver`
  - Pattern: `mock_discord_client.get_guild_channels = AsyncMock(return_value=[...])`
  - All tests are `@pytest.mark.asyncio` async functions
  - Covers: single match, ambiguous, not_found, empty text, plain text, multiple mentions

### Code Search Results

- `_channel_mention_pattern`
  - Defined only in `channel_resolver.py` — no other URL-pattern regex exists
- `get_guild_channels`
  - Called via `self.discord_client.get_guild_channels(guild_discord_id)` — returns list of channel dicts with `id`, `name`, `type` keys
- `"wrong_guild"` or `"discord.com/channels"`
  - Zero matches — no URL detection logic exists anywhere

### Project Conventions

- Standards referenced: Python 3.13+ type hints, ruff linting, pytest + `@pytest.mark.asyncio`
- TDD applies: both Python (channel_resolver) and TypeScript (ChannelValidationErrors) are in scope
- Instructions followed: `python.instructions.md`, `test-driven-development.instructions.md`, `self-explanatory-code-commenting.instructions.md`

## Key Discoveries

### Current Resolution Pipeline

```
User types location → resolve_channel_mentions() → ValidationError (blocking) → HTTP 422 → frontend shows ChannelValidationErrors
                                                  ↓ no errors
                                              game created with <#id> substitutions
```

### The Ambiguity Problem Being Solved

Discord allows two text channels with identical names. The existing `#channel-name` pattern returns `"ambiguous"` in that case. A discord.com channel URL unambiguously identifies a channel by its snowflake ID, solving this.

URL format: `https://discord.com/channels/{guild_id}/{channel_id}`

### Channel Dict Schema (from Discord API via `get_guild_channels`)

```python
{"id": "406583674453098496", "name": "general", "type": 0}  # type 0 = text channel
```

### Wrong-Guild URL Behavior

A user can already type any arbitrary URL (e.g. a Google Meet link) as a location today — the resolver returns immediately with no errors if there are no `#` pattern matches. Blocking a discord.com URL from another guild would be _more_ restrictive than the current baseline, which would be wrong.

**Decision**: Wrong-guild discord.com URLs pass through silently, identical to how any other plain URL is treated today. No error is returned and the game is created with the URL stored as-is.

## Recommended Approach

Extend `ChannelResolver.resolve_channel_mentions()` with a URL-detection pass that runs before the existing `#channel-name` pass. The URL regex runs first to avoid accidentally triggering the `#` name pattern on URLs that happen to use `#` fragments.

### Backend changes (`channel_resolver.py`)

Add compiled regex:

```python
self._discord_channel_url_pattern = re.compile(
    r"https://discord\.com/channels/(\d+)/(\d+)"
)
```

Detection logic (runs before existing `#` pass, using the already-fetched `text_channels` list):

| Condition                               | `type`        | `reason`                                                 | `suggestions` | Text replacement                      |
| --------------------------------------- | ------------- | -------------------------------------------------------- | ------------- | ------------------------------------- |
| guild_id in URL ≠ `guild_discord_id`    | — (no error)  | —                                                        | —             | URL left unchanged, game created      |
| channel_id not in fetched text_channels | `"not_found"` | `"This link is not a valid text channel in this server"` | `[]`          | URL left unchanged, game blocked      |
| Valid URL                               | —             | —                                                        | —             | Replace full URL with `<#channel_id>` |

### Frontend changes (`ChannelValidationErrors.tsx`)

Change `AlertTitle` from:

```
"Could not resolve some #channel mentions"
```

to:

```
"Location contains an invalid channel reference"
```

No other frontend changes are needed — the component already renders `err.input` and `err.reason` generically.

### Channel fetch ordering

The URL pass requires the channel list. Refactor `resolve_channel_mentions` to fetch channels once at the top (unconditionally, or after detecting either URL or `#` patterns are present) before running both passes.

## Implementation Guidance

- **Objectives**: Detect `discord.com/channels/{gid}/{cid}` URLs in the location field; validate guild match and channel existence; convert valid ones to `<#id>`; return typed errors for invalid ones; update the frontend alert title
- **Key Tasks**:
  1. Add `_discord_channel_url_pattern` regex to `ChannelResolver.__init__`
  2. Extract channel-fetch logic so it runs once for both URL and `#` passes
  3. Add URL resolution loop before the `#` mention loop
  4. Update `ChannelValidationErrors.tsx` `AlertTitle` text
  5. Add unit tests for all URL cases (TDD: write tests first)
- **Dependencies**: No new libraries. Discord channel list already fetched during `#` resolution — minor refactor to lift fetch before both passes.
- **Success Criteria**:
  - Valid same-guild channel URL in location → stored as `<#channel_id>` (disambiguates duplicate-name channels)
  - Wrong-guild URL → silently passed through unchanged; game created as-is (consistent with any other plain URL)
  - Valid guild, channel not a text channel or not found → blocking error `type: "not_found"`, reason: "This link is not a valid text channel in this server"
  - Plain URLs (non-discord.com) → passed through unchanged, no error
  - `#channel-name` resolution behavior unchanged
  - All unit tests pass; existing tests unmodified
  - Frontend title updated to "Location contains an invalid channel reference"
