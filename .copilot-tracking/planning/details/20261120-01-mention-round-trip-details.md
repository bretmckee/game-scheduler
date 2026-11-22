<!-- markdownlint-disable-file -->

# Task Details: Lossless @mention / #channel Round-Trip in Game Text Fields

## Research Reference

**Source Research**: .copilot-tracking/research/20261120-01-mention-round-trip-research.md (verified against HEAD `4c9a15a6`)

## Phase Ordering Rationale

Changing what the API returns in `description` / `signup_instructions` breaks every frontend reader in the same commit (research Lines 158). So every phase that only **tolerates** tokens lands first, and the server rendering switch lands last (Phase 7). Phases 1-6 are no-ops for today's token-free text, so each one commits cleanly on its own.

Applies `.github/instructions/test-driven-development.instructions.md`: new/changed unit-tested logic uses stub → xfail test → implement → remove xfail. Integration and e2e tests are written against implemented code (no xfail).

## Phase 1: Exact-Match Preference in Mention Resolution (server)

### Task 1.1: RED — xfail tests for the exact-match rule

Add tests to `tests/unit/services/api/services/test_participant_resolver.py` for `_resolve_user_friendly_mention` when the prefix search returns more than one member:

| Case                                                                    | Expected                                    |
| ----------------------------------------------------------------------- | ------------------------------------------- |
| One member whose username equals query (others only prefix-match)       | resolved to that member                     |
| Exact match on `nick` only                                              | resolved                                    |
| Exact match on `global_name` only                                       | resolved                                    |
| Query differs in case from the exact name                               | resolved (case-insensitive)                 |
| Two members exact-match (username of A == nick of B, the Kallisti case) | "Multiple matches found" + both suggestions |
| No exact match among many                                               | "Multiple matches found" (unchanged)        |

Mark the new tests `@pytest.mark.xfail(strict=True)`. They fail against today's code, so no stub is needed (bug-fix TDD workflow).

- **Files**:
  - tests/unit/services/api/services/test_participant_resolver.py - new tests near existing multiple-match tests (~712-768)
- **Success**: new tests report xfailed; existing tests still pass
- **Research References**:
  - research (Lines 26-29) - scan pattern and `_resolve_user_friendly_mention` 135-222
  - research (Lines 106) - exact-match rule definition
  - research (Lines 30-31) - prefix search returns username/nick/global_name matches
- **Dependencies**: none

### Task 1.2: GREEN — implement exact-match filter

In `services/api/services/participant_resolver.py` `_resolve_user_friendly_mention`, when matches > 1, filter for members where any of `username`, `nick`, `global_name` equals the query with `casefold()`. Exactly one → resolve it. Otherwise keep the existing suggestions response. Remove the xfail markers (no other test changes).

- **Files**:
  - services/api/services/participant_resolver.py - matches>1 branch (~160-207)
- **Success**: all participant_resolver tests pass; `uv run mypy shared/ services/` clean
- **Research References**: research (Lines 79, 106)
- **Dependencies**: Task 1.1

## Phase 2: Collapse `<@id|label>` / `<#id|label>` on Input (server)

### Task 2.1: RED — stub `collapse_mention_tokens` and xfail tests

Create a stub `collapse_mention_tokens(text: str | None) -> str | None` raising `NotImplementedError` in `services/api/services/channel_resolver.py` next to `render_text_for_display` (the existing token helpers live there). Add xfail tests:

- `<@123|Kallisti of the Ruby Rose>` → `<@123>`; `<@123|>` → `<@123>`
- `<#456|lfg>` → `<#456>`; `<#456|>` → `<#456>`
- Labels containing `@`, `(`, `|`, spaces, emoji → collapsed (regex `<@(\d+)\|[^>]*>`)
- Plain `<@123>`, `<#456>`, `@name`, `#name`, `:emoji:` unchanged; `None` → `None`
- After collapse, `ParticipantResolver`'s scan pattern never sees `@<digits>` and the channel scan never matches `id|name` as a channel name

- **Files**:
  - services/api/services/channel_resolver.py - stub + module-level compiled regexes
  - tests/unit/services/api/services/test_channel_resolver.py - new test class
- **Success**: new tests xfailed; suite otherwise green
- **Research References**:
  - research (Lines 81-87) - token format and parse regexes
  - research (Lines 22, 27) - why both scanners mis-handle uncollapsed tokens
  - research (Lines 105) - collapse step definition
- **Dependencies**: none

### Task 2.2: GREEN — implement and wire into create/update paths

Implement the function, remove xfail markers. Call it on `description` and `signup_instructions` **before** channel / mention / emoji resolution in:

- `_resolve_free_text_fields_for_create` (services/api/services/games.py ~600-665)
- the update-path resolution block (services/api/services/games.py ~2060-2095)

Add unit tests (in the existing games service test module that covers these paths) asserting that a token-form description reaches the resolvers already collapsed and is stored as bare `<@id>` / `<#id>`.

- **Files**:
  - services/api/services/channel_resolver.py - implementation
  - services/api/services/games.py - two call sites
  - tests/unit/services/api/services/ (existing games service tests) - wiring tests
- **Success**: unit + mypy gates green; no behaviour change for token-free input
- **Research References**: research (Lines 35-37, 105, 107)
- **Dependencies**: Task 2.1

## Phase 3: `MemberRef` + `MemberChip` for Participants (frontend)

### Task 3.1: RED — `MemberRef` type, adapter, `MemberChip` stub + tests

Create `frontend/src/types/memberRef.ts` (or add to `frontend/src/types/index.ts`) with `MemberRef = { id: string; label: string | null }` and `toMemberRef(p: { discord_id: string | null; display_name: string | null }): MemberRef | null` (null for placeholders). Create `frontend/src/components/MemberChip.tsx` stub. **Name note:** `MentionChip.tsx` already exists as the ValidationErrors suggestion chip — do not reuse or rename it.

Tests (mark with Vitest `it.fails` against the stub; remove the modifier in Task 3.2). The same RED convention applies to Tasks 5.1 and 6.x:

- adapter: member → `{id, label}`; departed (`discord_id` set, `display_name` null) → `{id, label: null}`; placeholder → `null`
- `MemberChip` with label renders `@label`; with `label: null` renders a visually distinct "unknown member" chip (tooltip "no longer in this server"), asserted by role/aria/test id, **not** by the text "Unknown User"
- a real member literally named "Unknown User" renders as a normal chip

- **Files**:
  - frontend/src/types/index.ts (or new memberRef.ts) - type + adapter
  - frontend/src/components/MemberChip.tsx - new
  - frontend/src/components/**tests**/MemberChip.test.tsx - new
- **Research References**: research (Lines 138-141, 149)
- **Dependencies**: none

### Task 3.2: GREEN — implement and render participants through `MemberChip`

Implement the adapter and chip. Route Discord participants in `ParticipantList.tsx` (~59, ~96), `GameCard.tsx` (host / participant display) and `GameForm.tsx` `buildParticipantList` (~198-251) rows through `MemberChip`. Placeholders keep plain text. `formatParticipantDisplay` (frontend/src/utils/formatParticipant.ts ~36-51) must stop producing `<@id>` / "Unknown User" for departed members. Either remove those branches or limit the function to placeholders. Update every caller and its tests in this task. In the editor, departed rows stay removable.

- **Files**:
  - frontend/src/components/MemberChip.tsx, ParticipantList.tsx, GameCard.tsx, GameForm.tsx
  - frontend/src/utils/formatParticipant.ts + frontend/src/utils/**tests** (its tests)
  - affected component tests (ParticipantList, GameCard, EditableParticipantList, GameForm)
- **Success**: `cd frontend && npm run build && npm run test` green. With today's server (which never sends null for members), rendering is unchanged apart from the chip styling.
- **Research References**: research (Lines 142, 149)
- **Dependencies**: Task 3.1

## Phase 4: Departed Participants Return `display_name: null` (server)

### Task 4.1: RED — `resolve_member_refs` stub + xfail tests

Add `resolve_member_refs(guild_discord_id: str, ids: list[str]) -> dict[str, str | None]` to `services/api/services/display_names.py` (stub). It is built on `member_projection.get_member`: `None` = departed, label = nick > global_name > username, unmodified. Xfail tests in `tests/unit/services/api/services/test_display_names.py`: priority order, departed → `None`, labels with `>` and `|` returned unmodified.

Add xfail tests that `resolve_display_names_and_avatars` maps a missing member to `{"display_name": None, "avatar_url": None}` (replacing the `"Unknown User"` assertion at ~224). Add xfail tests that `_build_participant_responses` / `_build_host_response` (tests/unit/services/api/routes/test_games_helpers.py) pass through `display_name: None` with `discord_id` set.

- **Files**:
  - services/api/services/display_names.py - stub
  - tests/unit/services/api/services/test_display_names.py, tests/unit/services/api/routes/test_games_helpers.py
- **Research References**: research (Lines 32-34, 108-123, 47)
- **Dependencies**: Phase 3 (the frontend must render null before the server sends it)

### Task 4.2: GREEN — implement and switch the participant/host path

Implement `resolve_member_refs`. Make `resolve_display_names_and_avatars` return `display_name: None` for a missing member (it is only called from services/api/routes/games.py lines ~189, ~614, ~1182; verify each caller tolerates `None`; `ParticipantResponse.display_name` is already `str | None`, shared/schemas/participant.py:40). Remove xfail markers. Update existing tests that asserted `"Unknown User"` for this function. Leave `resolve_display_names` / `resolve_primary_names` fallbacks alone unless a caller in scope uses them. The seat is not removed and promotion is unchanged.

- **Files**:
  - services/api/services/display_names.py
  - services/api/routes/games.py (only if a caller needs a `None` guard)
  - affected unit tests
- **Success**: unit + mypy green; frontend untouched
- **Research References**: research (Lines 108-123)
- **Dependencies**: Task 4.1

## Phase 5: `mentionTokens` Util + `MentionText` Read-Only Rendering (frontend)

### Task 5.1: RED — `mentionTokens.ts` stubs + failing tests

Create `frontend/src/utils/mentionTokens.ts` with stubs for `parseTokens`, `toEditorText`, `fromEditorText` (signatures per research Lines 127-134) and `frontend/src/utils/__tests__/mentionTokens.test.ts`:

- parse: text / user{id,label} / channel{id,label} segments; empty label → `label: null`; regexes `<@(\d+)\|([^>]*)>`, `<#(\d+)\|([^>]*)>`
- `toEditorText`: users → `@label`, channels → `#label`, departed removed with `removedCount`; token-free text is identity
- `fromEditorText`: unedited + no removals → byte-identical **collapsed** raw; edited → known labels mapped to `<@id>` / `<#id>`, longest label first; label shared by two IDs left as `@label`; damaged/unknown names left as typed
- full round trip for names with spaces, `(`, `@`, `|`, all-`@`, prefixes of other labels

- **Files**: frontend/src/utils/mentionTokens.ts, frontend/src/utils/**tests**/mentionTokens.test.ts
- **Research References**: research (Lines 81-98, 127-134, 149)
- **Dependencies**: none

### Task 5.2: GREEN — implement util

Implement the three functions until all tests pass.

- **Success**: frontend build + tests green
- **Dependencies**: Task 5.1

### Task 5.3: `MentionText` component and read-only views

Create `frontend/src/components/MentionText.tsx`. It renders `parseTokens` segments, with user tokens as `MemberChip` (Phase 3), channel tokens as a channel chip, and an empty channel label as an "unknown channel" chip. It takes an optional `maxLength` that truncates on segment boundaries (a token is never cut). Replace `truncateDescription(game.description, …)` in GameCard.tsx (~177-224) and the plain renders in GameDetails.tsx (~271, ~360). Tests: chips render, departed chip, truncation never splits a token, token-free text renders unchanged (so it is safe before Phase 7).

- **Files**:
  - frontend/src/components/MentionText.tsx + **tests**/MentionText.test.tsx (new)
  - frontend/src/components/GameCard.tsx, frontend/src/pages/GameDetails.tsx + their tests
- **Success**: frontend gates green; existing GameCard/GameDetails tests pass unchanged
- **Research References**: research (Lines 46, 137-141, 149)
- **Dependencies**: Tasks 3.2, 5.2

## Phase 6: Editor Wiring + Suggestion-Click Map (frontend)

### Task 6.1: GameForm editor state via `toEditorText` / `fromEditorText`

Initialise `description` / `signupInstructions` (GameForm.tsx ~330-331, ~363-364) through `toEditorText`, keeping `{map, raw, display, removedCount}` per field. Show the notice "Removed N mention(s) of members no longer in this server" when `removedCount > 0`. Apply `fromEditorText` in the submit payload builders for EditGame.tsx (~213/218, ~369/372), CloneGame.tsx (~226-229) and CreateGame.tsx (~180-184), either via the form's submit data or a shared helper so all three use one path.

- **Files**: frontend/src/components/GameForm.tsx, frontend/src/pages/EditGame.tsx, CloneGame.tsx, CreateGame.tsx + their tests
- **Success**: unedited token text round-trips byte-identical in payload tests; token-free text unchanged
- **Research References**: research (Lines 39-40, 44-45, 135)
- **Dependencies**: Phase 5

### Task 6.2: Suggestion click inserts display name and records the ID

Change `handleSuggestionClick` (GameForm.tsx ~661-677) for description/signup text: insert `@displayName` and add `@displayName → <@discordId>` to that field's map. Change `handleChannelSuggestionClick` (~647-659) the same way for `#name → <#id>`. Participant-row behaviour is unchanged. Adjust `ValidationErrors.tsx` (~59) if the callback needs the suggestion object instead of `@username`. Update GameForm.error-handling.test.tsx (~173-260) and ValidationErrors.test.tsx (~70). New test: chip pick, then submit sends `<@id>` (the 2a regression).

- **Files**: frontend/src/components/GameForm.tsx, ValidationErrors.tsx, ChannelValidationErrors.tsx (if needed) + tests
- **Success**: frontend gates green
- **Research References**: research (Lines 41-43, 78, 136)
- **Dependencies**: Task 6.1

## Phase 7: Switch Server Rendering to Token Form + Integration Round-Trip (server)

### Task 7.1: RED — xfail token-render tests

In `tests/unit/services/api/routes/test_games_helpers.py` (~901-915), add xfail tests for the new `_render_text_fields` output: live member `<@id|label>`, departed `<@id|>`, `>` stripped from label, labels with `|`, `@`, `(`, spaces, all-`@`; channel `<#id|name>`, unknown channel `<#id|>`; title emoji rendering unchanged. Existing assertions for `@display_name` / `#name` become the xfail targets (rewrite them to the token form and mark them xfail).

- **Files**: tests/unit/services/api/routes/test_games_helpers.py
- **Research References**: research (Lines 15-19, 81-87, 104, 148)
- **Dependencies**: Phases 2, 4, 5, 6

### Task 7.2: GREEN — implement token rendering

Rewrite the user/channel part of `_render_text_fields` (services/api/routes/games.py ~1291-1320) to emit tokens. Use `resolve_member_refs` (Phase 4) for users and the guild channel list for channels. Do not use `resolve_display_names`. Keep `where` / `where_display` and the title emoji rendering as they are. Remove `render_text_for_display` / `extract_user_mention_ids` from channel_resolver.py (`_USER_MENTION_PATTERN` line ~285, functions ~307-338; keep `collapse_mention_tokens` and its patterns at ~287-304) only if they have no remaining callers, and update or delete their tests in this same task. Remove the xfail markers.

- **Files**: services/api/routes/games.py, services/api/services/channel_resolver.py (possible dead code), tests
- **Success**: unit + mypy green
- **Research References**: research (Lines 15-21, 104, 120-123)
- **Dependencies**: Task 7.1

### Task 7.3: Integration round-trip matrix

Update tests/integration/test_games_field_display.py (~192, ~271) to assert the token form. Add a round-trip matrix (in test_games_field_display.py or a new tests/integration/test_games_mention_round_trip.py) using the real API, DB and Redis projection. For each case: create, GET, then PUT the returned description collapsed client-style and unchanged, and assert stored text is byte-identical. Also PUT the raw token form (server collapse). Cases: `<@id>`, `@username`, `@nick with spaces`, special-char username, a prefix of another name, two members with the same display name, a departed member, a hyphenated channel, duplicate channel names, custom emoji. Also cover exact-match resolution on a real projection, and a departed participant (GET returns `display_name`/`avatar_url` null, seat unchanged; an unedited PUT keeps the participant). Run per `.github/instructions/test-execution.instructions.md`.

- **Files**: tests/integration/test_games_field_display.py, tests/integration/test_games_crud.py (mention tests), new round-trip test module
- **Success**: `scripts/run-integration-tests.sh |& tee output-integration.txt` green
- **Research References**: research (Lines 150)
- **Dependencies**: Task 7.2

## Phase 8: E2E Regressions

### Task 8.1: E2E tests for 2a and 2b

Add these to tests/e2e/test_game_update.py (or alongside tests/e2e/test_channel_mentions.py ~55). (1) Create a game mentioning a member whose display name has spaces, edit an unrelated field via the API using the client-style collapsed description, save, and assert the Discord embed still contains `<@id>`. (2) An ambiguous `@prefix` returns suggestions; resubmitting with the chosen `<@id>` succeeds on the first retry. Also update existing e2e assertions that depended on rendered text.

- **Files**: tests/e2e/test_game_update.py, tests/e2e/test_channel_mentions.py
- **Success**: `scripts/run-e2e-tests.sh |& tee output-e2e.txt` green
- **Research References**: research (Lines 151, 160-163)
- **Dependencies**: Phase 7

## Dependencies

- Redis member projection (`get_member`, `search_members_by_prefix`), guild channel list (`get_guild_channels_safe`)
- pytest, mypy, Vitest + React Testing Library, MUI `Chip`
- Integration/e2e harness scripts

## Success Criteria

- Kallisti and Xanthias scenarios save after at most one disambiguation
- An unedited re-save yields byte-identical stored text; the Discord embed keeps `<@id>`
- Departed members surface as an "unknown member" chip; no names are persisted
- All unit, mypy, frontend, integration and e2e gates pass
