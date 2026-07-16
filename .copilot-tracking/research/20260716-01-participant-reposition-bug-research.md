<!-- markdownlint-disable-file -->

# Task Research Notes: Self-added participant repositioning silently fails to persist

## Research Executed

### File Analysis

- `frontend/src/components/EditableParticipantList.tsx`
  - `moveUp`/`moveDown`/`handleDrop` (lines 86-146) mark only the dragged participant `isExplicitlyPositioned: true`; the participant it swaps with "keeps its state" (comment on lines 91, 104, 131).
  - `addParticipant` (lines 69-78) appends a new blank entry at `preFillPosition = participants.length + 1` — the bottom of the whole displayed array, self-joined participants included.
- `frontend/src/pages/EditGame.tsx`
  - `handleSubmit` (lines 174-191) filters the payload to `p.mention.trim() && p.isExplicitlyPositioned`, so any self-joined participant that was never explicitly touched is dropped from the request entirely — the backend never even sees a reposition attempt for it.
- `frontend/src/components/GameForm.tsx`
  - `buildParticipantList` (lines 173-222): for `HOST_SELECTED_WITH_WAITLIST` (174-203), every `confirmed_participant` is unconditionally marked `isExplicitlyPositioned: true, isReadOnly: false` (line 180-181) regardless of its real `position_type`. For every other signup method (205-221), `isExplicitlyPositioned: p.position_type === ParticipantType.HOST_ADDED` — i.e. self-joined/role-matched participants start as _not_ explicitly positioned.
- `services/api/services/games.py`
  - `_update_prefilled_participants` (1437-1495) loads `current_participants` filtered to `position_type == ParticipantType.HOST_ADDED` only (1452-1459).
  - `_update_participant_positions` (1416-1435) only updates `p.position` for participants found in that (`HOST_ADDED`-only) `current_participants` list — a self-added participant's id is never matched, so the update is silently a no-op.
  - `if game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:` block (1467-1479) is the only code path that promotes a `SELF_ADDED` participant to `HOST_ADDED`.
  - `_add_new_mentions` (1496-1554) stores a freshly-typed participant's `position` as the raw `preFillPosition` sent by the frontend (the absolute index in the _whole_ displayed list, not relative to other host-added entries).
- `shared/utils/participant_sorting.py`
  - `sort_participants` (123-143): sort key is `(position_type, position, joined_at)` — `position` only breaks ties _within_ one `position_type`.
  - `partition_participants` (146-192): for `HOST_SELECTED_WITH_WAITLIST`, `confirmed = host_added[:max_players]` — a `SELF_ADDED`/`ROLE_MATCHED` participant can never be confirmed there regardless of `position`. For every other signup method, `confirmed = sorted_all[:max_players]` — a plain slice of the combined sort.
  - `resolve_role_position` (101-120): for `ROLE_BASED` games, `position` is not a placeholder — it's the real priority-role index (`(ROLE_MATCHED, index)`), so multiple role-matched participants intentionally share small `position` values as a meaningful tier, not an "unset" sentinel.
- `shared/models/participant.py`
  - `ParticipantType` (46-55): `HOST_ADDED = 8000`, `ROLE_MATCHED = 16000`, `SELF_ADDED = 24000`.
  - `GameParticipant.position_type`/`.position` (77-79): both `SmallInteger`, `position` `server_default=text("0")`.
- `shared/services/leave_game.py`
  - `leave_game_and_notify` (71-105): `if position_type == ParticipantType.HOST_ADDED and host_discord_id:` (102) sends the host a "host_added_dropout" DM. This is the one behavior that must not misfire for a participant who was merely swept into a reorder rather than genuinely added by the host.
- `services/bot/handlers/join_game.py` (182-197) and `services/api/routes/games.py` (170, 1060)
  - All self-added join paths default new participants to `(ParticipantType.SELF_ADDED, 0)`.

### Code Search Results

- `git blame -L 1465,1480 -- services/api/services/games.py`
  - The `HOST_SELECTED_WITH_WAITLIST`-gated promotion block is a pure addition from `45d556ed0` (2026-05-30) — there is no prior version of it to compare against; it added new capability, it didn't modify existing behavior.
- `git blame -L 1452,1460 -- services/api/services/games.py`
  - The `position_type == ParticipantType.HOST_ADDED` filter on `current_participants` traces to `b093cf15c` (2026-01-16), a pure complexity-reduction refactor (`git show b093cf15c^` has the identical filter beforehand).
- `git show b48f9e2b -- services/api/services/games.py` (2025-12-24, "Refactor participant ordering to use position_type and position fields")
  - Mechanical rename only: `pre_filled_position.isnot(None)` → `position_type == ParticipantType.HOST_ADDED`, `pre_filled_position` → `position`. No semantic change.
  - `git show b093cf15c^:services/api/services/games.py` (i.e. the version predating the position_type refactor) already had the identical `pre_filled_position.isnot(None)` filter.
  - `git show 347ab423 -- services/api/services/games.py` ("Phase 8: Fix game completion status transitions") — the original implementation of `_update_prefilled_participants`, already scoped to `pre_filled_position.isnot(None)`.
  - `git log --oneline -S"ROLE_MATCHED" -- shared/models/participant.py shared/utils/participant_sorting.py` → `cd8b63ea`, `96395943` ("role-based scheduling phases") — `ROLE_MATCHED` predates the waitlist feature and is unrelated to it.

### Project Conventions

- Alembic migrations: revision-hash-prefixed filename + descriptive slug (e.g. `fd0d4f43e53a_add_message_id_index.py`), standard copyright header, `revision`/`down_revision` identifiers, `upgrade()`/`downgrade()` functions (see `alembic/versions/fd0d4f43e53a_add_message_id_index.py`).

## Key Discoveries

### This is not a regression from the waitlist feature

The user's working hypothesis was that reordering used to work and broke when `HOST_SELECTED_WITH_WAITLIST` was added. Git archaeology disproves this: the restriction "only `HOST_ADDED`/pre-filled participants can have their position updated by the edit form" has existed since the participant-editing feature's original implementation (`347ab423`), predating both the `position_type`/`position` field refactor (`b48f9e2b`, Dec 2025) and the waitlist feature (`45d556ed`, May 2026) by months. The waitlist feature only ever _added_ a new promotion path scoped to its own signup method — it never removed or narrowed an existing capability. Self-joined participants have never had their manual repositioning persisted, for any signup method except the one where it was explicitly built.

### Two independent problems compound the bug

1. **Backend silently ignores the update.** `_update_prefilled_participants`/`_update_participant_positions` only ever loads and updates rows whose `position_type == HOST_ADDED`. A self-added participant referenced in the edit payload (even with `isExplicitlyPositioned: true` and a correct new `position`) is never found by that query, so the position write is a silent no-op — no error surfaces to the host.
2. **Sorting is bucketed, not a flat sequence.** Because `position` only breaks ties _within_ a `position_type`, promoting a participant's numeric position alone does nothing across bucket boundaries — `HOST_ADDED` (8000) always outranks `SELF_ADDED` (24000) regardless of the position value.

### Naive fixes that were considered and rejected

- **Add a new `ParticipantType` value (e.g. `HOST_POSITIONED = HOST_ADDED + delta`).** Rejected: `sort_participants` uses raw `position_type` as the primary sort key, so a genuinely different integer value would group all `HOST_POSITIONED` entries as a separate clump from `HOST_ADDED` entries regardless of assigned `position`, breaking correct interleaving whenever a host both types in a new name and drags an existing participant in the same edit. Fixing that would require reworking the sort-priority logic in `participant_sorting.py`, which is the single shared ordering utility used by bot formatters, calendar export, and notification logic — too wide a blast radius for this fix.
- **Add a boolean "auto_promoted" flag alongside `position_type = HOST_ADDED`.** Works, but the user found it inelegant — an extra column purely to remember "why is this row HOST_ADDED" felt like unnecessary state.
- **Reposition self-added participants by setting `position` alone, leaving `position_type = SELF_ADDED`, without changing the default.** Rejected in its initial form: `position` defaults to `0` for every self-added participant (`join_game.py`, `games.py`), which is the _smallest_ possible value. Setting an explicit `position` (e.g. `1..7`) on a repositioned prefix while everything else stays at the default `0` causes every untouched self-added participant — and, more seriously, _every future Discord joiner from that point forward_ (also defaulted to `0`) — to sort **ahead of** the deliberately rearranged participants. This isn't just a one-time display glitch; it permanently breaks FCFS ordering for the game going forward.

### The fix that resolves all raised objections

Change the _default/sentinel_ value for a newly self-joined participant's `position` from `0` to the maximum value the `SmallInteger` column can hold (`32767`), instead of introducing a new type or a new column.

- Untouched self-added participants (in the same edit, or joining afterward) share the sentinel `32767` and fall back to `joined_at` for ordering among themselves — identical to today's plain-FCFS behavior when nobody has been explicitly repositioned.
- An explicitly-repositioned participant gets a real, small `position` value (matching their new display index), which now sorts _before_ the sentinel group instead of colliding with it — because `32767` is (in any realistic game) larger than any assigned display position, not smaller.
- Future joiners keep landing at the sentinel by default, so they always sort after everything the host has explicitly arranged — the leapfrog problem is fixed in both directions (existing untouched entries at save time, and all future joins).
- No `position_type` mutation occurs for this path, so `leave_game.py`'s `position_type == HOST_ADDED` dropout-notification check is naturally unaffected — a repositioned self-added participant never triggers the "host added this person" notification, because they were never promoted to that type. This makes the flag/new-type debate moot for the general case.

`HOST_SELECTED_WITH_WAITLIST` is unaffected by (and doesn't need) this fix: `partition_participants` defines `confirmed = host_added[:max_players]` for that mode specifically, so only an actual `position_type` promotion can move a participant from waitlisted to confirmed there. Its existing `self_added_to_promote` block (`games.py:1467-1479`) stays exactly as-is.

### Open question: `ROLE_BASED` signup method

`resolve_role_position` assigns `ROLE_MATCHED` participants a _meaningful_ `position` (their priority-role index — e.g. `0`, `1`, `2`), not an arbitrary placeholder. That means the "swap the default to a large sentinel" fix, which relies on `0` being purely an "unset" marker, does not cleanly apply to the `ROLE_MATCHED` bucket — small position values there carry real information that a display-order pin could collide with. Reordering participants in a `ROLE_BASED` game is left as a follow-up question; it may need the promote-to-`HOST_ADDED` mechanic after all, scoped specifically to that signup method, rather than the sentinel-default approach used for plain `SELF_ADDED` participants.

## Recommended Approach

1. **Migration** (new Alembic revision, following the `alembic/versions/` convention): backfill existing rows via `UPDATE game_participants SET position = 32767 WHERE position_type != 8000 AND position = 0`. Reversible by the inverse `UPDATE ... SET position = 0 WHERE position_type != 8000 AND position = 32767`. Safe per the user: no real game will ever have anywhere near 32,767 participants, and `HOST_ADDED` (8000) rows are excluded from the predicate in both directions.
2. **Change the default for new self-added joins** from `(ParticipantType.SELF_ADDED, 0)` to `(ParticipantType.SELF_ADDED, 32767)` at every join site currently hardcoding `0` (`services/bot/handlers/join_game.py:197`, `services/api/routes/games.py:170`, `services/api/routes/games.py:1060`), and update the model's `server_default` (`shared/models/participant.py:79`) to match, so brand-new rows created outside these call sites (if any) get the same sentinel.
3. **Generalize the backend update path**: change `_update_prefilled_participants`/`_update_participant_positions` (`services/api/services/games.py`) so the position-update query matches on `participant_id` for _any_ participant in the game, not filtered to `position_type == HOST_ADDED` — while leaving `position_type` untouched for rows that aren't part of the `HOST_SELECTED_WITH_WAITLIST` promotion path.
4. **Frontend**: extend `EditGame.tsx`'s submission filter so that, in addition to the participant(s) the host literally dragged, every participant currently displayed _above_ the highest explicitly-touched index is included in the payload with its new display-order `position` — mirroring what `HOST_SELECTED_WITH_WAITLIST` already does today for its confirmed-participant prefix (`GameForm.tsx:175-183`), generalized to every signup method. Participants below that index are omitted entirely and keep whatever `position` (sentinel or explicit) they already had.
5. **Leave `HOST_SELECTED_WITH_WAITLIST`'s promotion logic unchanged** — it solves a different problem (moving someone into the `HOST_ADDED`-only confirmed set) that the sentinel fix does not and should not touch.
6. **Follow-up research needed before touching `ROLE_BASED` reordering** — flagged above; out of scope for the initial fix.

## Implementation Guidance

- **Objectives**: Persist host-initiated repositioning of already-joined (self-added) participants for all signup methods except the one where it's already solved (`HOST_SELECTED_WITH_WAITLIST`), without introducing spurious "host added this person" dropout notifications and without breaking FCFS ordering for future joiners.
- **Key Tasks**:
  - Alembic migration: backfill + default change for `position` on non-`HOST_ADDED` rows.
  - Update the three self-added/role-based-fallback join call sites and the model's `server_default`.
  - Generalize `_update_prefilled_participants`/`_update_participant_positions` to act on any referenced `participant_id`, regardless of `position_type`.
  - Extend the frontend payload-construction logic (`EditGame.tsx`) to include the full disturbed prefix, not just the literally-dragged participant.
  - Add/extend unit and integration tests: reposition a self-added participant in a `SELF_SIGNUP` game and confirm persistence across reload; confirm a subsequent new joiner still lands after the rearranged participants; confirm no `host_added_dropout` DM fires for a merely-repositioned (never `HOST_ADDED`) participant leaving; confirm `HOST_SELECTED_WITH_WAITLIST` behavior is unchanged.
- **Dependencies**: None blocking — this is backend + migration + frontend within the existing participant model; no new schema columns or `ParticipantType` values.
- **Success Criteria**: Dragging a self-joined participant in the edit UI persists across save/reload for `SELF_SIGNUP`/`HOST_SELECTED`; future Discord joins still append after any host-rearranged participants; no incorrect host notifications on drop for repositioned (not genuinely host-added) participants; `ROLE_BASED` behavior explicitly called out as unresolved rather than silently left broken.
