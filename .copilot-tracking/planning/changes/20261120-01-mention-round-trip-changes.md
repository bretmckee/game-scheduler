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

## Phase 5: `mentionTokens` Util + `MentionText` Read-Only Rendering (frontend)

### Added

- frontend/src/utils/mentionTokens.ts — pure helpers for `<@id|label>` / `<#id|label>`:
  - `parseTokens(text)` → `text` / `user{id,label}` / `channel{id,label}` segments (regex
    `<([@#])(\d+)\|([^>]*)>`). An empty label becomes `label: null`. Bare `<@id>` and non-digit IDs
    stay plain text.
  - `toEditorText(text)` → `EditorTextState { raw, display, map, removedCount }`. `raw` is the
    collapsed original (`<@id>` / `<#id>`). `display` shows `@label` / `#label`. `map` keys are the
    editor forms, and a label shared by two different IDs maps to `null` (ambiguous, left unmapped).
    Departed members **and unknown channels** (empty labels) are dropped from `display` and counted
    in `removedCount`.
  - `fromEditorText(edited, state)` → returns `raw` verbatim when unedited with nothing removed.
    Otherwise it replaces known labels longest-first with their bare tokens. Ambiguous labels,
    damaged names and newly typed names are left as typed. A label whose last character is a word
    character does not match when another word character follows it (`@Kal` inside `@Kallisti`).
- frontend/src/utils/\_\_tests\_\_/mentionTokens.test.ts — 33 tests: parsing (segments, empty
  labels, labels with `(`, `@`, `|`, spaces and all-`@`, non-token look-alikes), editor
  conversion (identity, map, collapsed raw, removal count, ambiguity, same-ID repeats) and
  back-conversion (byte-identical unedited, token-free identity, edits, removals not restored,
  longest-first, prefix boundary, ambiguity, damaged/new names, parametrized full round trip).
  They were `it.fails` against throwing stubs in Task 5.1, and the modifier was removed in Task 5.2.
- frontend/src/components/MentionText.tsx — renders `parseTokens` segments. Users go through
  `MemberChip` (so departed → unknown-member chip). Channels render as a `#name` chip
  (`data-testid="channel-chip"`), and an empty channel label renders as a dashed, italic
  "unknown channel" chip (`data-testid="unknown-channel-chip"`, tooltip "Channel not found in this
  server"). The optional `maxLength` counts visible characters (mention = label + sigil). It cuts
  only text segments and drops a mention that doesn't fit whole. Token-free text truncates exactly
  as the old `truncateDescription` did (`substring(0, n).trim() + '...'`).
- frontend/src/components/\_\_tests\_\_/MentionText.test.tsx — 9 tests: token-free passthrough,
  empty/null, member and channel chips with no IDs exposed, departed member, unknown channel,
  legacy truncation parity, no truncation when the text fits, a mention dropped rather than split,
  and an ellipsis after a whole mention.

### Modified

- frontend/src/components/GameCard.tsx — removed `truncateDescription`. The description renders
  through `<MentionText maxLength={UI.DEFAULT_TRUNCATE_LENGTH}>` inside a `Typography
component="div"` so the chips nest validly.
- frontend/src/pages/GameDetails.tsx — description and signup instructions render through
  `MentionText`. Both `Typography` wrappers are now `component="div"`. The description's
  `paragraph` prop is replaced by `mb: 2`, which keeps the same 16px bottom margin.
- frontend/src/components/\_\_tests\_\_/GameCard.test.tsx, frontend/src/pages/\_\_tests\_\_/GameDetails.test.tsx —
  one new test each: token descriptions / signup instructions render chips (including the departed
  chip) and never raw `<@…` / `<#…`. Existing tests pass unchanged.

### Notes / deviations

- **Decision**: unknown channels (`<#id|>`) are removed in the editor like departed members and
  counted in the same `removedCount`, so hosts never see raw IDs. Phase 6's notice wording should
  cover both (e.g. "Removed N mention(s) of members or channels no longer in this server").
- `map` values are `string | null` rather than `string`, so ambiguity is encoded in the state
  itself. Phase 6's suggestion-click mapping should write through the same rule (a conflicting ID
  for an existing label → `null`).
- With today's server (no tokens yet), every read-only view renders exactly as before.

### Gates

- `cd frontend && npm run build`: OK
- `cd frontend && npx vitest --run`: 53 files, 608 tests passed
- `npm run lint`: clean (prettier fix applied to mentionTokens.test.ts)
- `uv run pytest tests/unit`: 2747 passed
- `uv run mypy shared/ services/`: clean

## Phase 6: Editor Wiring + Suggestion-Click Map (frontend)

### Added

- frontend/src/components/\_\_tests\_\_/GameForm.mentions.test.tsx — editor/submit conversion tests:
  labels shown instead of tokens, an unedited submit sends the collapsed original, edits map known
  labels back, departed members and unknown channels are dropped with the removal notice (and are
  not resubmitted), token-free text passes through, `initialData` reset, and Save and Archive goes
  through the same conversion. Suggestion-pick tests: the 2a regression (pick → submit sends
  `<@id>` in both fields), the pick survives a later edit, the Kallisti same-display-name case
  (editor text unchanged, submit carries the picked ID), existing tokens stay intact when a pick
  lands in unedited text, and a duplicate-name channel pick sends the chosen `<#id>`.

### Modified

- frontend/src/components/GameForm.tsx — per-field `MentionFieldStates` (`EditorTextState` for
  description and signup instructions), built by `buildMentionFieldStates` on mount and on every
  `initialData` reset. The editor shows `display`. `toSubmitData` applies `fromEditorText` and
  feeds both `onSubmit` and `onSaveAndArchive`, so EditGame, CloneGame and CreateGame share one
  conversion path and their payload builders are unchanged. An info notice ("Removed N mention(s)
  of members or channels no longer in this server") shows above Description when either field
  dropped mentions. The suggestion handlers now take the picked ID and go through
  `applyMentionPick`: insert `@displayName` / `#name`, record `editorForm → <@id>` / `<#id>` in
  the field's map, and, while the field is otherwise unedited, rewrite `raw` / `display` too.
  Participant rows still get `@displayName` + `resolvedMention`, now always set from the
  passed ID.
- frontend/src/components/ValidationErrors.tsx, ChannelValidationErrors.tsx — `onSuggestionClick`
  gets a third argument, the picked suggestion's `discordId` / channel `id`. The page-level
  `onValidationErrorClick` / `onChannelValidationErrorClick` props keep their two-argument shape.
- frontend/src/components/\_\_tests\_\_/GameForm.error-handling.test.tsx — the three replacement
  tests now expect the display name (`@New Name`, `@Alice`, `@Foo Bar`) instead of `@username`.
- frontend/src/components/\_\_tests\_\_/ValidationErrors.test.tsx, ChannelValidationErrors.test.tsx —
  the callback assertions include the ID, and there is a new duplicate-channel-name test that passes
  the clicked chip's ID.
- frontend/src/pages/\_\_tests\_\_/EditGame.test.tsx, CloneGame.test.tsx — new payload tests: an
  unedited labeled-token description / signup sends `<@id>` / `<#id>` text (PUT and clone POST).
- All new and changed tests were written `it.fails` first. I confirmed each one failed on its
  assertion (not on setup) with a marker-stripped copy, then removed only the modifier.

### Notes / deviations

- **Outside plan**: the details didn't cover a pick in an unedited field. `fromEditorText` returns
  `raw` verbatim when the text equals `display`, so a pick that leaves the text unchanged (Kallisti:
  both members display as "Kallisti") or lands in unedited template/legacy text would have sent the
  unresolved name again and kept the loop going. `applyMentionPick` rewrites `raw` alongside
  `display` in that case. Covered by the Kallisti and "existing tokens intact" tests.
- **Decision**: a pick overrides any existing map entry for that label, including a `null`
  (ambiguous) one. A server prompt for a label only happens when the label was sent unmapped, so
  the host's explicit choice is the right resolution. Phase 5's note suggested the opposite;
  following it would have recreated the 2a loop.
- **Decision**: channel chips pass the channel ID rather than GameForm looking it up by name,
  because duplicate channel names would otherwise always resolve to the first suggestion. User
  chips pass the ID too, for symmetry.
- Notice wording covers channels as well as members, per the Phase 5 decision.
- `where` handling is unchanged.
- The character-count helpers measure the editor text, not the submitted text.
- One combined vitest run during RED had a single unrelated EditGame failure that didn't
  reproduce on rerun or in the full suite.

### Gates

- `cd frontend && npm run build`: OK
- `cd frontend && npx vitest --run`: 54 files, 625 tests passed
- `npm run lint`: clean; `prettier --check` on touched files: clean
- `uv run pytest tests/unit`: 2747 passed
- `uv run mypy shared/ services/`: clean
- No integration or e2e changes in this phase

## Phase 7: Switch Server Rendering to Token Form + Integration Round-Trip (server)

### Added

- tests/integration/test_games_mention_round_trip.py — the round-trip matrix through the real API,
  DB and Redis member projection. Each case applies the same text to description and signup
  instructions: create, check stored text, GET (assert the exact labeled form), then PUT the
  client-collapsed text and PUT the raw labeled text. Both PUTs must leave stored text
  byte-identical. Cases: `<@id>`, `@username`, `@nick with spaces` (2b), special-char username
  with a `( | @` label (Xanthias), a label containing `>`, a prefix of another name, two
  members with the same display name, a departed member (`<@id|>`), a hyphenated channel,
  duplicate channel names, custom emoji, and all of these mixed. Separate tests: the Kallisti
  flow (two exact hits → one 422 with both suggestions → the picked `<@id>` saves), exact
  username winning over longer prefix hits on a real projection, and a departed participant
  (GET gives `discord_id` set with `display_name` / `avatar_url` null; an unedited client PUT
  with no `participants` field keeps the row, its user and its position).

### Modified

- services/api/services/channel_resolver.py — new
  `render_mention_tokens(text, member_labels, channel_names)`, the inverse of
  `collapse_mention_tokens`. `<@id>` → `<@id|label>` and `<#id>` → `<#id|name>`,
  with `>` stripped from labels. An ID missing from its lookup (or a `None`
  label) gets the empty-label marker `<@id|>` / `<#id|>`. Added
  `_CHANNEL_MENTION_PATTERN`.
- services/api/routes/games.py — `_render_text_fields` now renders emoji first, then labeled
  tokens. Members come from `resolve_member_refs` (one lookup across both fields, sorted IDs),
  and channels come from the guild channel list.
  `resolve_display_names` is no longer used here. Title emoji rendering and `where` /
  `where_display` are unchanged.
- tests/unit/services/api/routes/test_games_helpers.py — `TestRenderTextFields` rewritten for the
  token form: both fields from one lookup, departed `<@id|>`, `>` stripped, labels with `|`, `@`,
  `(`, spaces, all-`@` and a literal "Unknown User" kept verbatim, `<#id|name>`, unknown channel
  `<#id|>`, emoji and tokens together, and no resolver call without user tokens. Strict xfail in
  Task 7.1; I verified with `--runxfail` that each failed on its assertion. Task 7.2 removed only
  the markers.
- tests/unit/services/api/services/test_channel_resolver.py — direct `render_mention_tokens`
  tests (None, token-free identity including non-digit look-alikes, live, departed, unknown
  channel, `>` stripping) written xfail against a `NotImplementedError` stub.
- tests/integration/test_games_field_display.py — the channel and user mention tests (renamed
  `..._renders_as_labeled_token`) assert the exact `<#id|name>` / `<@id|label>` description.
  Docstrings updated.

- services/api/dependencies/permissions.py — comment on the `is_bot_fresh` check in
  `_check_guild_membership` stating the freshness invariant ("missing" means "departed") and that
  relaxing it requires examining every caller of the projection read helpers. Added a one-line
  pointer at the same check in `verify_guild_membership`.
- shared/cache/ttl.py — comment on `DISCORD_GUILD_CHANNELS`: no expiry is an invariant
  (downstream code treats an absent channel as deleted).
- shared/discord/client.py — corrected the `get_guild_channels_safe` docstring. It is a cache-only
  read, and `[]` means a cache miss, not a Discord API failure. The old wording led to the
  reverted fallback.
- services/api/routes/games.py — the `_render_text_fields` docstring tells readers not to add a
  "leave tokens bare" fallback and points to `permissions.verify_guild_membership`.

### Removed

- services/api/services/channel_resolver.py — `render_text_for_display`. It had no callers
  left, and its tests in test_channel_resolver.py were deleted. `extract_user_mention_ids` and
  `_USER_MENTION_PATTERN` are kept because `_render_text_fields` still uses them to collect IDs.

### Notes / deviations

- **Reverted after review**: I first added a fallback that left tokens bare when lookup data was
  "unavailable" (no guild, a projection error, or an empty channel list). The user pointed out
  it can't happen. Request authorization already returns 503 when the bot projection is stale.
  The channel list is a cache-only read of that same gateway data (no REST fallback). A Redis
  failure fails auth before rendering, and `guild_id` is non-null. I removed the fallback and its
  4 unit tests. Lookup errors now propagate, and a missing ID always gets the empty label, as
  planned.
- **Outside plan**: emoji are rendered before mention tokens, so a member label is never
  touched by the emoji renderer.
- Pre-existing behaviour, unchanged: the free-text scanner captures only `@\w+(?:\.\w+)*`, so a
  typed `@Kallisti of the Ruby Rose` resolves `@Kallisti` and keeps the rest as text. The
  matrix's `nick_with_spaces` case types `@Kallisti`. The 2b fix is that the GET keeps the ID,
  so the editor never has to send the spaced name back.

### Gates

- `uv run pytest tests/unit`: 2756 passed
- `uv run mypy shared/ services/`: clean
- `ruff check` / `ruff format --check` and `scripts/check_test_assertions.py` on touched files: clean
- `scripts/run-integration-tests.sh |& tee output-integration.txt`: 396 passed (rebuilt after the
  fallback removal). An earlier run had a single 30s setup timeout in `test_rls_enforcement.py`.
  That run's wall clock was 7h55m, so the host had slept. The file passed on its own (7/7).
- No frontend files changed in this phase. Every reader of `description` /
  `signup_instructions` already goes through `MentionText` or the GameForm editor conversion.
