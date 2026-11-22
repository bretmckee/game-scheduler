<!-- markdownlint-disable-file -->

# Changes: Lossless @mention / #channel Round-Trip in Game Text Fields

## Summary

Make user and channel mentions in game description / signup instructions survive
repeated create/edit/clone saves.

---

## Phase 1: Exact-Match Preference in Mention Resolution (server)

### Modified

- services/api/services/participant_resolver.py — `_resolve_user_friendly_mention` now resolves
  directly when exactly one prefix-matched member has a username, nick or global_name equal to the
  query (casefold). The filter runs before the >10 suggestion-cap check.
- tests/unit/services/api/services/test_participant_resolver.py — added strict-xfail tests for the
  single-exact-match rule (username / nick / global_name / case-insensitive, parametrized) and for
  an exact match beating the >10 suggestion cap, plus a passing regression guard that two exact
  matches (the Kallisti case) still return "Multiple matches found"
  - **Outside plan**: changed `nick: "Alice"` → `"Alicia"` in the fixtures of the existing
    `test_resolve_multiple_matches` and `test_resolve_user_friendly_mention_multiple_matches`
    (and their displayName assertions). With query `@alice`, that nick is an exact match under
    the new rule, which would stop those tests from covering the "no exact match" path. The
    existing multiple-match test now serves as the plan's "no exact match among many" case.
  - **Outside plan**: added the suggestion-cap case. The plan doesn't say whether the exact
    filter runs before the >10 check, so the test pins down that it runs first.
  - The two-exact-match test isn't xfail because today's code already passes it.
  - Task 1.2 removed the xfail markers and left the assertions unchanged.

### Gates

- `uv run pytest tests/unit`: 2712 passed
- `uv run mypy shared/ services/`: clean
- No frontend, integration or e2e changes in this phase

## Phase 2: Collapse `<@id|label>` / `<#id|label>` on Input (server)

### Modified

- services/api/services/channel_resolver.py — added `collapse_mention_tokens(text)` plus the
  module-level `_LABELED_USER_TOKEN_PATTERN` (`<@(\d+)\|[^>]*>`) and
  `_LABELED_CHANNEL_TOKEN_PATTERN` (`<#(\d+)\|[^>]*>`). It rewrites labeled tokens to bare
  `<@id>` / `<#id>`, leaves all other text untouched and maps `None` → `None`.
- services/api/services/games.py — `_resolve_free_text_fields_for_create` collapses
  `description` and `signup_instructions` before any channel / mention / emoji resolution.
  The new `_collapse_mention_tokens_for_update` static method does the same for updated fields.
  `update_game` calls it right before `_resolve_channel_mentions_for_update`. Clone goes through
  `create_game`, so it is covered by the create path.
- tests/unit/services/api/services/test_channel_resolver.py — new `TestCollapseMentionTokens`
  class (labeled and empty-label tokens, labels containing `@`, `(`, `|`, spaces and emoji,
  several tokens in one text, unchanged token-free / bare / non-digit-ID text, `None`). Also two
  scanner-level tests: after collapse, the real `ParticipantResolver.resolve_mentions_in_text`
  sees no `@<digits>` candidate, and the real `ChannelResolver` validates `<#456>` by ID instead of
  reporting `456|lfg` as an unknown channel name. I checked that both scanners misbehave on
  uncollapsed text, so the tests can catch a regression.
- tests/unit/services/api/services/test_games_service.py — two wiring tests (create via
  `_resolve_free_text_fields_for_create`, update via `update_game`). They assert that the channel
  and mention resolvers receive collapsed text and that the stored fields are bare tokens.
  - **Outside plan (TDD)**: I wrote the wiring tests as strict xfail before wiring them and
    confirmed they failed on assertions, not on setup. Then I wired the call sites and removed
    the markers.
- .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md — updated the
  Phase 7 channel_resolver.py line references, which moved after the insertion.

### Gates

- `uv run pytest tests/unit`: 2732 passed
- `uv run mypy shared/ services/`: clean
- No frontend, integration or e2e changes in this phase
