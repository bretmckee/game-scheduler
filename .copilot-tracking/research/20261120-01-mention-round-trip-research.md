<!-- markdownlint-disable-file -->

# Task Research Notes: Lossless @mention / #channel Round-Trip in Game Text Fields

## Research Executed

### Problem Report (user feedback, 2026-11)

- **2a**: Clicking the correct "Did you mean" chip for `@Kallisti` and saving loops forever: the server keeps reporting "Multiple matches found" for the same two members (`@kallisti (Kallisti of the Ruby Rose)`, `@lesbian.anscombe (kallisti)`).
- **2b**: After a game is posted/edited, mentions in the description that were entered as `<@255462938775781377>` or `@_xanthias_tag` come back in the edit form as the member's display name (e.g. `@Kallisti of the Ruby Rose`). Re-saving then fails, because display names with spaces or special characters can't be resolved.
- The two bugs compound. 2b turns `<@id>` into `@Kallisti of the Ruby Rose`; the scanner truncates that to `@Kallisti` (capital K in the screenshot); 2a then loops.

### File Analysis

- services/api/routes/games.py
  - Lines 1291-1320 `_render_text_fields`: replaces `<@id>`→`@display_name`, `<#id>`→`#name`, `<:e:id>`→`:e:` in description / signup_instructions.
  - Lines 1366-1375 `_build_game_response`: returns the **rendered** text in the plain `description` / `signup_instructions` fields. These are the only copies the client gets, so the IDs are lost.
  - Lines 1360-1365: `where` is the precedent for doing this correctly. It returns raw `where` plus a separate `where_display`.
  - Introduced by commit `670afdf1 feat: render <#id> and <@id> tokens in game description and signup_instructions`.
- services/api/services/channel_resolver.py
  - Lines 285-319 `_USER_MENTION_PATTERN`, `extract_user_mention_ids`, `render_text_for_display`: the token→name rendering used above.
  - Lines 77-81: the channel scan pattern `<#\s*\d+\s*>|<#\s*([^\s<>#]+)\s*>|(<?)#([^\s<>#]+)`. A `<#id|name>` token would match group 1 (`id|name`) as a channel name, so it must be collapsed before scanning.
  - Lines 83-135 `resolve_channel_mentions`: `#name` is resolved by exact, case-insensitive name (lines ~232-250). Duplicate names produce suggestions. `<#id>` tokens are validated against the guild's text channels (lines ~252-282).
- services/api/services/emoji_resolver.py
  - Lines 31-39: stored `<a?:name:id>` renders to `:name:`, and `:name:` resolves back on save. This already round-trips by name and is out of scope.
- services/api/services/participant_resolver.py
  - Line 76 `_resolved_or_mention_pattern = r"<@\d+>|(@\w+(?:\.\w+)*)"`. Bare `<@digits>` is skipped. Anything else after `@` is cut at the first non-`\w`/`.` character (so `@Kallisti of the Ruby Rose` becomes `@Kallisti`). `<@id|name>` would not match alternative 1, and `@id` digits would be scanned as a username, so it must be collapsed before scanning.
  - Lines 135-222 `_resolve_user_friendly_mention`: 0 matches → not found. 1 match → resolved. More than 1 → "Multiple matches found" with suggestions. **There is no exact-match preference.**
  - Lines 308-329 `resolve_mentions_in_text`: the free-text scan used for description / signup_instructions.
- shared/cache/projection.py
  - Lines 126-167 `search_members_by_prefix`: a ZRANGEBYLEX prefix search over a single set that holds username, global_name and nick (lowercased). Each member appears once in the results. `kallisti` is one member's username and the other member's nick/global_name, so both always match.
- services/api/services/display_names.py
  - Lines 178-203 `resolve_display_names` (priority nick > global_name > username). On a missing member it returns `"Unknown User"` (line ~132), and on an exception it returns `User#1234` (line ~176). Both are legal-looking text, not an unambiguous "departed" signal.
  - Line 290 `resolve_primary_names` (username first) exists, but the chosen design doesn't use it.
- services/api/services/games.py
  - Lines 600-665 `_resolve_free_text_fields_for_create`: channel resolution runs when `#` is present, then mention resolution when `@` is present, then emoji resolution.
  - Lines 2060-2095: the equivalent update-path resolution (`resolve_mentions_in_text` at line 2087).
  - Templates never resolve mentions, so they are out of scope.
- frontend/src/components/GameForm.tsx
  - Lines 306-307 and 339-340: description / signupInstructions are initialised from `initialData` (the rendered text).
  - Lines 637-653 `handleSuggestionClick`: participant rows correctly set `resolvedMention = <@discordId>`. Description and signup text are replaced with `@username` (`newUsername`), which re-triggers the ambiguous prefix search. **This is root cause 2a.**
  - Lines 168-185 `replaceMentionToken`; lines 623-635 `handleChannelSuggestionClick` (same pattern for channels, writes `#name`).
- frontend/src/components/ValidationErrors.tsx line 59: the chip passes `@${sugg.username}`. The suggestion carries `discordId`, `username` and `displayName`.
- frontend/src/pages/EditGame.tsx lines 213/218 and 369/372: description and signup_instructions are **always** sent on save, even when unchanged, so an unedited game still breaks.
- frontend/src/pages/CloneGame.tsx lines 226-229 and CreateGame.tsx lines 180-184: the same send path. Clone loads the source game's rendered text, so it has the 2b problem too.
- Read-only consumers: frontend/src/components/GameCard.tsx line 215 (`truncateDescription(game.description)`) and frontend/src/pages/GameDetails.tsx lines 271 and 360 (`game.description`, `game.signup_instructions`). These are the only frontend readers besides the forms.
- services/api/dependencies/permissions.py lines 74-80: `_check_guild_membership` returns False when the projection isn't fresh, so GET game / update fail before any rendering runs. **Whenever mentions are rendered, the projection is fresh**, so a missing member really has left the server. No per-feature staleness handling is needed. (The 404-vs-503 status on that path is a separate research task.)
- shared/models/user.py: the User model stores only `discord_id`. **By design no names are ever persisted for IDs** (this avoids stale data). The design must stay ID-only.

### Code Search Results

- `resolve_mentions_in_text|render_text_for_display|_render_text_fields`
  - Only call sites: routes/games.py 1311/1314/1367 and services/games.py 651/2087.
- `\.description` in frontend/src
  - GameForm, TemplateForm (template text, unaffected), GameCard, TemplateCard (unaffected), EditGame, GameDetails, CloneGame, CreateGame.

### External Research

- Source: https://docs.discord.com/developers/resources/user (redirected from discord.com/developers/docs/resources/user), section "Usernames and Nicknames"
  - "Usernames must be between 2 and 32 characters long."; "Nicknames must be between 1 and 32 characters long."
  - "Names can contain most valid unicode characters". Names are trimmed of leading/trailing whitespace.
  - Usernames cannot contain `@`, `#`, `:`, ` ``` `, or `discord`. Display names/nicks **can** contain `@`, `(`, `|`, `>`, spaces and so on.
  - Implication: **no name is ever empty**, so an empty label (`<@id|>`) can't collide with a real name. Labels may contain `>`, which must be stripped so the token boundary stays unambiguous.

### Project Conventions

- Standards referenced: .github/instructions/python.instructions.md, test-driven-development.instructions.md, unit-tests.instructions.md, integration-tests.instructions.md, test-execution.instructions.md, reactjs.instructions.md, typescript-5-es2022.instructions.md, fastapi-transaction-patterns.instructions.md.
- The API is first-party only (no third-party clients), so changing the meaning of `description` is acceptable.

## Key Discoveries

### Root Causes

| #   | Cause                                                                                                          | Location                                                              |
| --- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 2b  | API returns rendered (lossy) text in the only description/signup fields; the editor loads it and re-submits it | routes/games.py 1291-1375, GameForm.tsx 306-340, EditGame.tsx 213/369 |
| 2b  | Rendered display names don't survive the `@\w+(?:\.\w+)*` scanner                                              | participant_resolver.py 76                                            |
| 2a  | Suggestion chip writes `@username` (not the ID) into free text                                                 | GameForm.tsx 637-653, ValidationErrors.tsx 59                         |
| 2a  | Prefix search across username/nick/global_name has no exact-match preference                                   | participant_resolver.py 160-207, projection.py 126-167                |

### Token Format (decided)

- Live member: `<@123456789012345678|Kallisti of the Ruby Rose>`. The label is the display name (nick > global_name > username) with every `>` removed.
- Member who left (projection fresh, `get_member` is None): `<@123456789012345678|>`. The empty label is the structural "unknown member" marker.
- Channel: `<#123456789012345678|general-chat>` (label with `>` removed). An unknown channel ID gets `<#id|>`.
- Parse regexes (both sides): `<@(\d+)\|([^>]*)>` and `<#(\d+)\|([^>]*)>`. The ID is authoritative and the label is cosmetic.
- Custom emoji keep the existing `:name:` round trip (unchanged).

### Complete Examples

```text
Stored (DB / Discord post, unchanged):  Ask <@2554…781377> in <#9876…> before joining
API description (edit-ready + render):  Ask <@2554…781377|Kallisti of the Ruby Rose> in <#9876…|lfg> before joining
Editor textarea shows:                  Ask @Kallisti of the Ruby Rose in #lfg before joining
  hidden map: {"@Kallisti of the Ruby Rose": "<@2554…781377>", "#lfg": "<#9876…>"}, rawOriginal
Read-only views render:                 Ask [chip: @Kallisti of the Ruby Rose] in [chip: #lfg] before joining
Departed member, read-only:             Ask [greyed italic chip "unknown member", tooltip "no longer in this server"] …
```

## Recommended Approach

### Server (Python)

1. **Edit-ready rendering.** Replace `_render_text_fields`' user/channel rendering with token rendering that emits `<@id|label>` / `<#id|label>` (plus `<@id|>` / `<#id|>` for unknown IDs). Look members up through the projection directly so that "missing" means departed. Don't use `resolve_display_names`, whose `"Unknown User"` / `User#1234` fallbacks look like real names. The title emoji rendering stays as it is. **No `_display` fields.** `description` and `signup_instructions` carry the token form.
2. **Collapse on input.** Before channel, mention and emoji resolution in both the create path (services/games.py 600-665) and the update path (around 2060-2095), normalise `<@(\d+)\|[^>]*>`→`<@\1>` and `<#(\d+)\|[^>]*>`→`<#\1>`. This protects the scanners (see participant_resolver.py 76 and channel_resolver.py 77-81) from any token the client didn't collapse.
3. **Exact-match rule.** In `_resolve_user_friendly_mention`, when the prefix search returns more than one member, filter for members whose username, nick or global_name equals the query (case-insensitive). If exactly one remains, resolve it. Otherwise return "Multiple matches found" with suggestions as today. In the reported case `@kallisti` still prompts (two exact hits), but the chip pick then resolves by ID.
4. Stored text and the bot / Discord embed are unchanged: plain `<@id>` and `<#id>`. No names are persisted.
5. **Departed participants (same marker, participant lists).** Today `resolve_display_names_and_avatars` maps a missing member to `display_name: "Unknown User"` (services/api/services/display_names.py lines ~222-224). `_build_participant_responses` (routes/games.py ~1222-1245) returns that like a real name, and the frontend shows `@Unknown User`, which is a legal name and indistinguishable from a real member called that.
   - Change: for a Discord participant whose member lookup returns None, return `display_name: null` and `avatar_url: null`. **No new flag.** The structural rule is the same one the text tokens use:

     | Case            | `discord_id` | `display_name` |
     | --------------- | ------------ | -------------- |
     | Discord member  | set          | name           |
     | Departed member | set          | `null`         |
     | Placeholder     | `null`       | typed text     |

   - Participants stay **structured JSON, not tokens**. Tokens would lose characters (stripped `>`), can't represent placeholders, and would force every consumer to parse a string to get back fields the API already sends separately.
   - The departed participant **keeps their seat** (no removal or promotion; behaviour unchanged). Save round-trip is unaffected, because persisted rows are submitted by `participant_id` (frontend/src/pages/EditGame.tsx line ~93).
   - Host and confirmed/waitlist responses use the same rule. Check `_build_host_response` (routes/games.py ~1269-1280) for the same `"Unknown User"` path.
6. **Single server path for member resolution.** Add one helper, e.g. `resolve_member_refs(guild_discord_id, ids) -> dict[id, label | None]`, built on `member_projection.get_member` (`None` = departed; label = nick > global_name > username, unmodified).
   - Both the text-token renderer (step 1, which strips `>` when emitting the token) and the participant/host builders (step 5) call it, so the departed rule lives in one place.
   - Replace the `"Unknown User"` fallbacks in display_names.py for these callers.
   - The projection is guaranteed fresh at this point (see permissions.py 74-80), so `None` always means the member has left.

### Frontend (TypeScript)

1. **Shared util** (new, e.g. `frontend/src/utils/mentionTokens.ts`), pure functions:
   - `parseTokens(text)` → segments (text / user{id,label} / channel{id,label}).
   - `toEditorText(text)` → `{ display, map, raw }`. Users become `@label`, channels become `#label`. Departed members (empty label) are **removed**, and the function returns a `removedCount`.
   - `fromEditorText(edited, state)`:
     - Edited text equal to the initial `display` with no removals → return the collapsed raw original (byte-identical).
     - Otherwise replace each known `@label` / `#label` with its ID, longest label first.
     - A label shared by two different IDs is **not** mapped. It is left as plain `@label`, so the server prompts ("ambiguous, always ask").
     - Damaged or unknown names are left as typed, for the server to resolve.
2. **GameForm**: initialise description and signupInstructions through `toEditorText`, keep the state per field, and run `fromEditorText` in the submit path (EditGame, CloneGame, CreateGame payload builders). Show a notice when `removedCount > 0` ("Removed N mention(s) of members no longer in this server").
3. **Suggestion click** (GameForm.tsx 637-653, 623-635): insert `@displayName` / `#name` into the text **and** add `label → <@discordId>` / `<#id>` to the field's map. This fixes 2a without exposing IDs. The participant-row behaviour stays as it is.
4. **Read-only rendering**: a `MentionText` component renders segments, with user and channel tokens as styled chips and the empty label as a visually distinct "unknown member" / "unknown channel" chip (styling, not text, so it can't collide with a real name). Use it in GameDetails.tsx (271, 360) and GameCard.tsx (215). Truncation must operate on segments so it never cuts a token in half.
5. **Single frontend render path.**
   - Define one type, `MemberRef = { id: string; label: string | null }` (`label === null` means departed), and one `MemberChip` component that renders either a mention chip or the "unknown member" chip.
   - The text parser (step 1) produces `MemberRef`s from `<@id|label>`. Participants and the host become `MemberRef`s with a trivial adapter, `{ id: p.discord_id, label: p.display_name }`; there's nothing to parse.
   - Placeholders (`discord_id` null) keep rendering as plain text.
6. **Departed participants**: ParticipantList.tsx (lines ~59, ~96, via `formatParticipantDisplay`), GameCard and the GameForm participant rows (`buildParticipantList`, GameForm.tsx ~198-251) render participants with `discord_id` set and `display_name` null through `MemberChip` (the **same** "unknown member" chip as departed text mentions). In the editor the row stays read-only-labelled but removable, and the host can drop the participant manually. `formatParticipantDisplay` (frontend/src/utils/formatParticipant.ts) must no longer fall back to `<@id>` / "Unknown User" text for these participants.

### Testing Strategy

| Level       | Existing tests affected                                                                                                                                                                  | New tests needed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | What only this level proves                                       |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Unit (Py)   | test_participant_resolver.py 98, 712-768 (multiple matches); test_games_helpers.py ~901-915 (rendering); test_channel_resolver.py (scan patterns); test_member_projection.py 225-281     | Token render: live, departed (`\|>`), label containing `>`, `\|`, `@`, `(`, spaces, all-`@`; channel unknown ID. Collapse: `<@id\|…>`/`<#id\|…>` → bare before scan; the scanner never sees `@digits`. Exact match: single exact among many → resolved; two exact (username vs nick) → suggestions; exact on nick/global_name; case-insensitive                                                                                                                                                                                                                                                                                                                                                                            | Pure transform correctness and the exact-match rule in isolation  |
| Unit (TS)   | GameForm.error-handling.test.tsx 173-260 (chip replaces `@username`); GameCard.test.tsx; GameDetails.test.tsx; ValidationErrors.test.tsx 70; EditGame/CloneGame/CreateGame payload tests | mentionTokens util: parse/editor/back round trip for every name case; unedited → raw byte-identical; duplicate label → left unmapped; damaged label → left as typed; departed removal + count; longest-label-first. GameForm: chip inserts the display name and the submit sends `<@id>`; removal notice. MentionText: chips, departed chip, truncation on segment boundaries. MemberRef adapter (member / departed / placeholder). Participant list / card / form rows render the departed chip when `discord_id` is set and `display_name` is null, never the text "Unknown User"; a real member literally named "Unknown User" renders as a normal mention. `MemberChip` is used by both the text and participant paths | Editor UX contract and that the client payload is correct         |
| Integration | test_games_field_display.py 192, 271 (assert rendered `#name` / `@display_name`, must change to token form); test_games_crud.py mention tests                                            | Round-trip matrix through the real API + DB + Redis projection: create with `<@id>`, `@username`, `@nick with spaces`, special-char username, prefix-of-another-name, two members with the same display name, departed member, hyphenated channel, duplicate channel names, custom emoji. Then GET, then PUT the returned description collapsed client-style **unchanged**, and stored text must be byte-identical. Also PUT the raw token form (server-side collapse). Exact-match resolution against a real projection. Participant who left: GET returns `discord_id` set, `display_name: null`, `avatar_url: null`, and the seat is unchanged; an unedited PUT keeps the participant                                   | Server render ↔ collapse ↔ resolve agree end to end on real data  |
| E2E         | tests/e2e/test_channel_mentions.py 55; test_game_update.py                                                                                                                               | One flow: create a game with a mention of a member whose display name has spaces, edit an unrelated field, save, and assert the Discord embed still contains `<@id>` (the 2b regression). Ambiguous `@prefix` → pick a suggestion → save succeeds once (the 2a regression)                                                                                                                                                                                                                                                                                                                                                                                                                                                 | The real bot / Discord message keeps working mentions after edits |

## Implementation Guidance

- **Objectives**: mentions and channels survive any number of create/edit/clone saves unchanged; picking a suggestion always ends the prompt loop; hosts never see raw IDs; members who left are surfaced, not silently mangled; no names are persisted.
- **Key Tasks**: server token rendering + collapse + exact match; frontend mentionTokens util, GameForm wiring, suggestion-click map update, MentionText for read-only views; update affected tests; add the round-trip matrix.
- **Dependencies**: the Redis member projection (`get_member`, `search_members_by_prefix`); guild channel list (`get_guild_channels_safe`); the existing ValidationErrors / ChannelValidationErrors flow.
- **Phase-isolation note**: changing the `description` format (server) breaks GameCard, GameDetails and the forms (client) and the integration assertions in the same commit. Server rendering and frontend parsing must land together, or the server collapse step plus the frontend util must land first, with rendering switched last.
- **Out of scope (separate research)**: stale projection returns 404 instead of 503 on game access (permissions.py 74-80 vs 117-126).
- **Success Criteria**:
  - The reported Kallisti and Xanthias scenarios both save successfully after a single disambiguation at most.
  - Unedited re-save gives byte-identical stored text.
  - All unit, integration and e2e gates pass.
