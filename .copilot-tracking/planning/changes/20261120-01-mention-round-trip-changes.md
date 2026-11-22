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

## Phase 3: `MemberRef` + `MemberChip` for Participants (frontend)

### Added

- frontend/src/types/memberRef.ts — `MemberRef = { id; label: string | null }` (`null` = departed)
  and the `toMemberRef` adapter (`null` for placeholders).
- frontend/src/components/MemberChip.tsx — `@label` chip (`data-testid="member-chip"`). For a
  null label it renders a dashed, italic "unknown member" chip with a PersonOff icon
  (`data-testid="unknown-member-chip"`, aria-label and tooltip "No longer in this server").
  This is separate from the existing suggestion `MentionChip.tsx`.
- frontend/src/types/\_\_tests\_\_/memberRef.test.ts, frontend/src/components/\_\_tests\_\_/MemberChip.test.tsx —
  adapter (member / departed / placeholder), present chip, punctuation-heavy label left
  unmodified, departed chip by test id / accessible name / tooltip (never "Unknown User", never
  the raw ID), and a real member named "Unknown User" rendering as a normal chip.
- frontend/src/utils/\_\_tests\_\_/formatParticipant.test.ts — new (the function had no tests).
- frontend/src/components/\_\_tests\_\_/ParticipantList.test.tsx — new (the component had no tests).
  Covers confirmed and waitlisted departed members, present members and placeholders.

### Modified

- frontend/src/utils/formatParticipant.ts — dropped the `<@id>` and "Unknown User" fallbacks.
  A missing name now yields `''`. Departed members have no text form and go through `MemberChip`.
- frontend/src/components/ParticipantList.tsx — Discord participants (confirmed and waitlist)
  render as `MemberChip`, and placeholders keep plain text. The primary slot is rendered as a `div`
  so the chip nests validly.
- frontend/src/components/GameCard.tsx — the host renders through `MemberChip`, which shows
  `@name`. A departed host now shows the unknown-member chip; before, the whole host line was hidden.
  The avatar falls back to `?`.
- frontend/src/components/EditableParticipantList.tsx — `ParticipantInput.member?: MemberRef`.
  Rows with `member.label === null` show the unknown-member chip with "Left the server (can
  reorder or remove)" instead of a text field. Drag, reorder and delete still work.
- frontend/src/components/GameForm.tsx — new `participantRowText` helper used by all three
  `buildParticipantList` branches. It sets `member` and keeps `@label` editor text for present
  members. Departed rows keep the bare `<@id>` as an internal, never-displayed `mention` /
  `originalMention`. That way EditGame still submits them as `participant_id` (not a replaced
  row), the row isn't dropped by the empty-mention filter, and Clone resubmits the same
  token as before.
- Tests: GameCard.test.tsx (host assertions now `@DungeonMaster` via the chip, plus a departed-host
  test), EditableParticipantList.test.tsx (departed row is a chip, not a textbox, and stays
  removable), GameForm.test.tsx (departed row shows the chip and never `<@222>`), and
  EditGame.test.tsx (a dragged departed row is sent as `participant_id`, and deleting it sends
  `removed_participant_ids: ["d1"]`).
- .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md — updated the Phase 5/6
  GameForm.tsx and GameCard.tsx line references after the insertions.

### Notes / deviations

- **Scope choice**: only _departed_ editor rows become chips. Present rows keep their text field
  (editable for host-added rows, disabled for joined rows). Host-added rows must stay editable,
  and existing EditGame tests and flows rely on display values like `@P1`.
- **Test correction (RED phase)**: the first draft of the EditGame "disturbed prefix" test
  dragged P2 above the departed row. It expected the departed row in the payload, which
  contradicts the documented rule that untouched rows below the highest explicit index are
  omitted. I changed the test to drag the departed row itself. The test still fails if a
  departed row's `mention` were empty.
- During RED, four existing EditGame tests failed because the new `it.fails` tests left an
  unconsumed `mockResolvedValueOnce` PUT. HEAD on its own passes (28/28). They pass again now
  that the new tests pass.
- With today's server, a member's `display_name` is never null, so the only visible change is
  chip styling. The departed chip takes effect when Phase 4 lands.

### Gates

- `cd frontend && npm run build`: OK
- `cd frontend && npx vitest --run`: 51 files, 564 tests passed
- `npm run lint`: clean (prettier fix applied to one test file)
- `uv run pytest tests/unit`: 2732 passed
- `uv run mypy shared/ services/`: clean

## Phase 4: Departed Participants Return `display_name: null` (server)

### Modified

- services/api/services/display_names.py — new `DisplayNameResolver.resolve_member_refs(guild_discord_id, ids)
-> dict[str, str | None]`, built on `member_projection.get_member`. A missing member maps to `None`
  (departed). Otherwise the label is nick > global_name > username, returned unmodified (no
  escaping). Projection errors propagate to the caller. `_fetch_and_cache_display_names_avatars`
  (and so `resolve_display_names_and_avatars`) now maps a missing member to
  `{"display_name": None, "avatar_url": None}` instead of `"Unknown User"`. The `User#last4`
  exception fallback is unchanged. `resolve_display_names`, `resolve_single` and
  `resolve_primary_names` are untouched (no caller in scope).
- services/api/routes/games.py — `_resolve_participant_display` return type widened to
  `tuple[str | None, str | None]` and documented. No logic change was needed: all three callers
  (join response, list_games host prefetch, `_resolve_display_data`) already pass the value
  straight into `ParticipantResponse.display_name`, which is `str | None`.
- tests/unit/services/api/services/test_display_names.py — replaced the `"Unknown User"` assertion
  test for the avatar path with `resolve_display_names_and_avatars` tests (departed → None, mixed
  present + departed). Added `resolve_member_refs` tests: label priority (parametrized,
  including a missing `nick` key, with call-argument verification), departed → None alongside a
  present member, labels with `>`, `|`, a token-like string, whitespace and a literal "Unknown User"
  returned unmodified, and empty IDs → `{}` with no lookups. These were strict xfail against the
  `NotImplementedError` stub / old fallback (verified failing on assertions with `--runxfail`).
  Task 4.2 removed the markers.
- tests/unit/services/api/routes/test_games_helpers.py — `_build_participant_responses`,
  `_build_host_response` and `_resolve_participant_display` pass `display_name: None` through with
  `discord_id` set. The participant fixtures keep a stored row name, so falling back to it would
  fail the test.
  - **Deviation**: the plan asked for these to be xfail, but today's builders already copy the
    value through, so strict xfail would XPASS. Like the Phase 1 two-exact-match guard, they are
    plain regression tests.

- .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md — Phase 7
  `_render_text_fields` line reference updated (~1295-1324) after the docstring insertion.

### Notes

- `resolve_member_refs` has no production caller yet. The Phase 7 token renderer will call it.
  The avatar path keeps its own loop because it needs the full member dict for `avatar_url`.
  It shares the same departed rule (`None`) and `_resolve_display_name` priority.
- The departed participant keeps their seat, and promotion is unchanged. The frontend (Phase 3)
  already renders `display_name: null` + `discord_id` as the unknown-member chip.

### Gates

- `uv run pytest tests/unit`: 2747 passed
- `uv run mypy shared/ services/`: clean
- `ruff check` / `ruff format --check` on touched files: clean
- No frontend, integration or e2e changes in this phase
