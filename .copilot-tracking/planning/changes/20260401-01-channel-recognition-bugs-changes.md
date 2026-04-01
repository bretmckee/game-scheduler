# Changes: Channel Recognition Bug Fixes

## Status

Phase 1 complete.

## Added

- `services/api/services/channel_resolver.py` — Added module-level `render_where_display(where, channels)` function that replaces `<#id>` tokens with `#name` using a pre-fetched channel list
- `services/api/services/channel_resolver.py` — Added private `_check_snowflake_tokens` helper method to `ChannelResolver` that validates `<#id>` tokens against the guild channel list

## Modified

- `services/api/services/channel_resolver.py` — Changed `_channel_mention_pattern` regex from `#([\w-]+)` to `(?<!<)#([^\s<>]+)` to accept emoji/Unicode channel names (Bug 1 fix)
- `services/api/services/channel_resolver.py` — Added `_snowflake_token_pattern` and snowflake detection to `resolve_channel_mentions`; valid `<#id>` tokens pass through silently, invalid ones produce a `not_found` error (Bug 2 fix)
- `tests/unit/services/api/services/test_channel_resolver.py` — Added 5 regression tests: emoji channel name resolution, valid `<#id>` token accepted, unknown `<#id>` token error, `render_where_display` with `None`, and `render_where_display` token substitution; all written as `xfail` first then made passing

## Removed

None.

## Divergences from Plan

None.
