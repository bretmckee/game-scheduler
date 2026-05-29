---
applyTo: '.copilot-tracking/changes/20260529-01-web-ui-game-creation-fixes-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Web UI Game Creation Fixes

## Overview

Fix four UX issues in game creation (GIF animation, @mention resolution, #channel
resolution, custom emoji resolution) and document one deprecated Discord pattern.

## Objectives

- GIF thumbnail/banner images animate in Discord announcements
- `@username` in `description` and `signup_instructions` resolves to a Discord mention
- `#channel-name` in `description` and `signup_instructions` resolves to a channel link
- `#123` (pure-integer hash token) passes through without error
- `:emoji_name:` in `description` and `signup_instructions` renders as a custom emoji
- `username#discriminator` documented as unsupported in the player guide

## Research Summary

### Project Files

- `services/api/routes/public.py` — image GET/HEAD routes with UUID path parameter that must accept extensions
- `services/bot/formatters/game_message.py` — URL builder for thumbnails/banners; needs MIME extension appending
- `services/bot/events/handlers.py` — passes `thumbnail_id`/`banner_image_id`; must also pass MIME types
- `shared/models/game.py` — `thumbnail` and `banner_image` relationships are `selectin`-loaded; MIME available
- `services/api/services/channel_resolver.py` — `resolve_channel_mentions()` needs integer passthrough
- `services/api/services/games.py` — resolution wiring; needs channel, @mention, and emoji resolvers on free-text fields
- `shared/discord/client.py` — cache-only client; needs `get_guild_emojis()` method
- `shared/cache/keys.py` — cache keys; needs `discord_guild_emojis` key

### External References

- #file:../research/20260529-01-web-ui-game-creation-fixes-research.md — full research with code patterns

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow
- #file:../../.github/instructions/unit-tests.instructions.md — assertion quality standards

## Implementation Checklist

### [ ] Phase 1: GIF Animation Fix

- [ ] Task 1.1: Change `image_id` path parameter from `UUID` to `str` in `public.py` (GET and HEAD)
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 13-38)

- [ ] Task 1.2: Add `_MIME_TO_EXT` map and update `format_game_announcement()` in `game_message.py`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 39-65)

- [ ] Task 1.3: Pass `thumbnail_mime_type` and `banner_image_mime_type` from loaded relationships in `handlers.py`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 66-91)

### [ ] Phase 2: #channel Integer Passthrough Fix

- [ ] Task 2.1: Add `channel_name.isdigit()` passthrough in `resolve_channel_mentions()` not-found branch
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 94-121)

- [ ] Task 2.2: Apply `resolve_channel_mentions()` to `description` and `signup_instructions` in `games.py`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 122-145)

### [ ] Phase 3: @mention Resolution in Free-Text Fields

- [ ] Task 3.1: Add `resolve_mentions_in_text()` method to `ParticipantResolver`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 148-176)

- [ ] Task 3.2: Apply `resolve_mentions_in_text()` to `description` and `signup_instructions` in `games.py`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 177-199)

### [ ] Phase 4: Custom Emoji Resolution

- [ ] Task 4.1: Add `discord_guild_emojis` cache key to `keys.py` and `FETCH_GUILD_EMOJIS` operation
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 202-225)

- [ ] Task 4.2: Add `get_guild_emojis()` cache-only method to `DiscordAPIClient`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 226-247)

- [ ] Task 4.3: Add `on_guild_emojis_update` bot event handler; populate emoji cache on `on_guild_available`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 248-274)

- [ ] Task 4.4: Create `services/api/services/emoji_resolver.py` with `EmojiResolver` class
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 275-303)

- [ ] Task 4.5: Wire `EmojiResolver` into `games.py` for `description` and `signup_instructions`
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 304-325)

### [ ] Phase 5: Documentation Update

- [ ] Task 5.1: Update `docs/PLAYER-GUIDE.md` to note `username#discriminator` is unsupported
  - Details: .copilot-tracking/planning/details/20260529-01-web-ui-game-creation-fixes-details.md (Lines 328-362)

## Dependencies

- Python 3.11+ (`re`, `uuid`, `typing` standard library)
- Existing `ChannelResolver` and `ParticipantResolver` classes
- Existing `DiscordAPIClient` with `_read_cache_only` pattern
- Redis cache infrastructure with TTL constants
- discord.py bot gateway with `on_guild_available` event

## Success Criteria

- GIF thumbnails animate in Discord announcements
- `@username` in description/signup_instructions resolves to `<@discord_id>`
- `#channel-name` in description/signup_instructions resolves to `<#channel_id>`
- `#123` in description/signup_instructions passes through without error
- `:emoji_name:` in description/signup_instructions renders as Discord custom emoji
- `username#discriminator` documented as unsupported in player guide
- Full test suite passes with no regressions
