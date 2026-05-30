<!-- markdownlint-disable-file -->

# Task Research Notes: HOST_SELECTED_WITH_WAITLIST signup mode

## Research Executed

### File Analysis

- `shared/models/signup_method.py`
  - `SignupMethod` is a `StrEnum` with 3 values: `SELF_SIGNUP`, `HOST_SELECTED`, `ROLE_BASED`
  - Stored as a free-form string column in `game_sessions.signup_method` — no Alembic migration needed to add a new value
  - Has `display_name` and `description` properties

- `shared/models/participant.py`
  - `ParticipantType` IntEnum: `HOST_ADDED = 8000`, `ROLE_MATCHED = 16000`, `SELF_ADDED = 24000`
  - Sparse values intentional; comment: "Changes to these values must be mirrored in TypeScript"

- `shared/utils/participant_sorting.py`
  - `partition_participants(participants, max_players)` sorts by `(position_type, position, joined_at)` and slices at `max_players`
  - **Core problem**: function is signup-method-blind — SELF_ADDED players fill confirmed slots in the new mode
  - `PartitionedParticipants.cleared_waitlist(previous)` detects overflow→confirmed promotions
  - No symmetric demotion detection exists (gap in all existing modes)

- `services/api/services/games.py`
  - 4 call sites for `partition_participants` (lines 936, 1538, 1733, 1818)
  - `_update_prefilled_participants`: queries only HOST_ADDED participants; SELF_ADDED participant_ids sent from frontend are in `existing_participant_ids` but never in `current_participants`, so silently ignored
  - `_detect_and_notify_promotions`: computes new partition from `game.participants`, compares with old snapshot; only fires promotion DMs

- `services/api/routes/games.py`
  - 1 call site for `partition_participants` (line 1076)

- `shared/services/game_schedules.py`
  - 1 call site for `partition_participants` (line 71)

- `services/bot/views/game_view.py`
  - Join button disabled when `signup_method == HOST_SELECTED`; must also check for `HOST_SELECTED` specifically (not the new mode)

- `services/bot/events/handlers.py`
  - 4 call sites for `partition_participants` (lines 459, 658, 1249, 1299)
  - `_format_join_notification_message` dispatches `DMFormats.join_with_instructions` or `DMFormats.join_simple` based on `game.signup_instructions`; no signup_method awareness

- `shared/message_formats.py`
  - `DMFormats.join_simple`: `"✅ You've joined **{game_title}**!"`
  - `DMFormats.join_with_instructions`: `"✅ **You've joined {game_title}**\n\n📋 **Signup Instructions**\n..."`
  - `DMFormats.promotion`: `"✅ Good news! A spot opened up in **{game_title}**... You've been moved from the waitlist to confirmed participants!"`
  - No demotion DM format exists

- `frontend/src/types/index.ts`
  - `SignupMethod` TypeScript enum mirrors Python; comment: "Changes must be mirrored in Python enum"
  - `SIGNUP_METHOD_INFO` maps enum values to display config

- `frontend/src/components/GameForm.tsx`
  - Loads participants with `isReadOnly: p.position_type !== HOST_ADDED`, `isExplicitlyPositioned: p.position_type === HOST_ADDED`

- `frontend/src/components/EditableParticipantList.tsx`
  - Drag sets `isExplicitlyPositioned: true` on dragged item
  - `EditGame.tsx` filters: `.filter(p => p.mention.trim() && p.isExplicitlyPositioned)` before sending to API
  - A dragged SELF_ADDED participant gets `isExplicitlyPositioned: true` and its `participant_id` IS sent to the API — the backend currently ignores it

### Code Search Results

- `partition_participants` callers
  - 10 production call sites: `game_schedules.py` (1), `api/services/games.py` (4), `api/routes/games.py` (1), `bot/events/handlers.py` (4)
  - All 10 have a game object in scope; all have `game.signup_method` available

- `_update_prefilled_participants`
  - Queries `position_type == HOST_ADDED` only; SELF_ADDED participant IDs in payload are silently ignored

## Key Discoveries

### Project Structure

All signup-method logic is stored as a string column; new values require only enum addition, no migration.

Partition logic is the single choke point: every downstream view (bot embed, API response, notification detection) derives from `partition_participants`. Fixing it there fixes everything.

### Implementation Patterns

Existing `cleared_waitlist()` on `PartitionedParticipants` is the correct pattern to follow for demotion detection. The symmetric method belongs in the same class.

Frontend drag-and-drop already sends `participant_id` for dragged SELF_ADDED players. The backend simply needs to act on it (upsert) instead of ignore it.

### API and Schema Documentation

`_update_prefilled_participants` flow:

1. Query current HOST_ADDED participants for this game
2. Separate payload into `existing_participant_ids` (have a DB id) vs `mentions_with_positions` (new @mentions)
3. Remove HOST_ADDED participants not in `existing_participant_ids`
4. Update positions for existing HOST_ADDED participants
5. Resolve and create new @mention participants as HOST_ADDED

The upsert step (converting SELF_ADDED → HOST_ADDED) belongs after step 2: query for SELF_ADDED participants whose IDs appear in `existing_participant_ids`, update their `position_type` to `HOST_ADDED` and set new `position`.

## Recommended Approach

### 1. New `SignupMethod` enum value

Add `HOST_SELECTED_WITH_WAITLIST = "HOST_SELECTED_WITH_WAITLIST"` to `shared/models/signup_method.py` and mirror in `frontend/src/types/index.ts`.

### 2. `partition_participants` — required `signup_method` parameter

```python
def partition_participants(
    participants: list["GameParticipant"],
    max_players: int | None = None,
    signup_method: SignupMethod = SignupMethod.SELF_SIGNUP,
) -> PartitionedParticipants:
```

**No `None` default allowed** — a caller that forgets to pass `signup_method` in the new mode would silently return wrong data. Use `SELF_SIGNUP` as the default to preserve existing caller behavior (all existing modes behave identically).

Internal logic:

```python
if signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:
    host_added = [p for p in sorted_all if p.position_type == ParticipantType.HOST_ADDED]
    other = [p for p in sorted_all if p.position_type != ParticipantType.HOST_ADDED]
    confirmed = host_added[:max_players]
    overflow = host_added[max_players:] + other
else:
    confirmed = sorted_all[:max_players]
    overflow = sorted_all[max_players:]
```

Update all 10 production callers to pass `signup_method=game.signup_method` explicitly (even if default covers them, explicit is correct and self-documenting).

### 3. `PartitionedParticipants.entered_waitlist()` — symmetric demotion detection

```python
def entered_waitlist(self, previous: "PartitionedParticipants") -> set[str]:
    return {
        discord_id
        for discord_id in previous.confirmed_real_user_ids
        if discord_id in self.overflow_real_user_ids
    }
```

### 4. New DM formats in `shared/message_formats.py`

`DMFormats.join_waitlist(game_title, jump_url)`:

```
🎫 You're on the waitlist for **{game_title}**. The host will confirm participants.
[View game in Discord]({jump_url})
```

`DMFormats.waitlist_demotion(game_title, jump_url)`:

```
⚠️ A change by the host has moved you to the waitlist for **{game_title}**.
[View game in Discord]({jump_url})
```

### 5. `_format_join_notification_message` — dispatch waitlist DM

In `services/bot/events/handlers.py`, check `game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST` and dispatch `DMFormats.join_waitlist()` instead of `join_simple`/`join_with_instructions`.

### 6. `_detect_and_notify_promotions` → `_detect_and_notify_transitions`

Rename and extend to also detect demotions. Applies to ALL signup methods (not just the new one — this is a gap fix for existing modes):

```python
async def _detect_and_notify_transitions(self, game, old_partitioned):
    new_max_players = resolve_max_players(game.max_players)
    new_partitioned = partition_participants(game.participants, new_max_players, game.signup_method)
    promoted = new_partitioned.cleared_waitlist(old_partitioned)
    demoted = new_partitioned.entered_waitlist(old_partitioned)
    if promoted:
        await self._notify_promoted_users(game=game, promoted_discord_ids=promoted)
    if demoted:
        await self._notify_demoted_users(game=game, demoted_discord_ids=demoted)
```

### 7. Promotion via drag — upsert in `_update_prefilled_participants`

After separating `existing_participant_ids` from new mentions, additionally query for SELF_ADDED participants whose IDs are in `existing_participant_ids`:

```python
# Promote SELF_ADDED participants that appear in the existing_participant_ids list
self_added_to_promote = [
    p for p in game.participants
    if p.id in existing_participant_ids
    and p.position_type == ParticipantType.SELF_ADDED
]
for p in self_added_to_promote:
    position = next(
        d["position"] for d in participant_data_list
        if d.get("participant_id") == p.id
    )
    p.position_type = ParticipantType.HOST_ADDED
    p.position = position
```

This converts a SELF_ADDED waitlisted player to HOST_ADDED when the host drags them up in the edit form. The `cleared_waitlist()` detection in `_detect_and_notify_transitions` will automatically send the promotion DM.

### 8. Bot join button — enable for new mode

In `services/bot/views/game_view.py`, change the join button disable condition from:

```python
signup_method == SignupMethod.HOST_SELECTED
```

to:

```python
signup_method in (SignupMethod.HOST_SELECTED,)
```

(i.e., `HOST_SELECTED_WITH_WAITLIST` is NOT in the disabled set — players can join to the waitlist.)

### 9. Frontend — checkbox UI for new mode

In `frontend/src/components/GameForm.tsx`, when `signupMethod == SignupMethod.HOST_SELECTED`, show a checkbox "Players can join waitlist (host selects from queue)". Checking it sets `signupMethod = SignupMethod.HOST_SELECTED_WITH_WAITLIST`. Unchecking sets it back to `HOST_SELECTED`.

In `frontend/src/types/index.ts`, add:

```typescript
HOST_SELECTED_WITH_WAITLIST = 'HOST_SELECTED_WITH_WAITLIST',
```

and corresponding `SIGNUP_METHOD_INFO` entry.

### 10. Open slot placeholders in bot embed and frontend (all game types)

Applies universally — not gated by `signup_method`. Any game with fewer confirmed participants than `max_players` shows placeholder entries for the empty slots.

**Bot (`_add_participant_fields` in `game_message.py`):**

The function already receives both `participant_ids` and `max_players`. Pad before formatting:

```python
empty_slots = max_players - len(participant_ids)
display_ids = participant_ids + ["open slot"] * empty_slots
```

`format_user_or_placeholder()` already renders non-numeric strings as plain text, so no changes needed there. The existing `"No participants yet"` fallback is replaced by this padded list.

**Frontend (participant display components):**

Compute `max_players - confirmed.length` and render that many read-only placeholder rows (e.g. italicised "open slot"). These rows are pure JSX — they are not part of the form state and are never submitted. When the host drags a waitlisted player into the confirmed section, `confirmed.length` increments by 1 and the placeholder count decrements by 1 automatically — no extra logic required.

## Test Coverage Plan

### Unit only

Pure logic with no external dependencies; fast, run in pre-commit.

| Feature                                                                                                                                                   | File                                                  |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `partition_participants` — `signup_method` param + HOST_ADDED-only logic; all edge cases (empty HOST_ADDED, excess HOST_ADDED > max_players, mixed types) | `tests/unit/shared/utils/test_participant_sorting.py` |
| `entered_waitlist()` symmetric demotion detection                                                                                                         | `tests/unit/shared/utils/test_participant_sorting.py` |
| `DMFormats.join_waitlist` and `DMFormats.waitlist_demotion` string formats                                                                                | `tests/unit/shared/test_message_formats.py`           |
| `_format_join_notification_message` dispatches waitlist DM for new mode                                                                                   | `tests/unit/services/bot/`                            |
| `_detect_and_notify_transitions` detection logic and DM dispatch (mocked `partition_participants`)                                                        | `tests/unit/services/api/services/`                   |

### Unit + Integration

Integration adds confidence that DB mutations and the API → RabbitMQ chain actually work.

| Feature                                                                 | Integration focus                                                                                                                   |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `_update_prefilled_participants` upsert (SELF_ADDED → HOST_ADDED)       | Verify `position_type` is actually written to DB; unit mocks cannot confirm the ORM mutation persists                               |
| Demotion notification when max_players reduced or signup method changed | Verify full API → DB → RabbitMQ chain: game update triggers demotion event published to queue; add to `test_game_signup_methods.py` |
| `HOST_SELECTED_WITH_WAITLIST` signup method DB round-trip               | Confirm value survives API → DB → event pipeline; add to `test_game_signup_methods.py`                                              |

### Unit + Integration + E2E

E2E adds verification of actual Discord behavior that cannot be tested without a live bot.

| Feature                                                                          | E2E focus                                                                                                                            |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Bot join button enabled for new mode                                             | Add to `test_signup_methods.py` alongside existing `SELF_SIGNUP`/`HOST_SELECTED` button-state cases; verifies actual Discord message |
| Join DM content says "waitlist" not "joined" for new mode                        | Add to `test_join_notification.py`; verifies DM content received from Discord                                                        |
| Promotion via drag end-to-end (SELF_ADDED → HOST_ADDED → promotion DM delivered) | Covers the full chain: PUT game with participant_id → DB upsert → cleared_waitlist → promotion DM in Discord                         |

## Implementation Guidance

- **Objectives**: Allow players to self-join a waitlist; host promotes by dragging in edit form; demoted players get notified
- **Key Tasks**:
  1. `SignupMethod` enum addition (Python + TypeScript)
  2. `partition_participants` — `signup_method` param + HOST_ADDED-only logic
  3. `entered_waitlist()` on `PartitionedParticipants`
  4. New DM formats: `join_waitlist`, `waitlist_demotion`
  5. Update all 10 `partition_participants` callers
  6. `_update_prefilled_participants` upsert for SELF_ADDED → HOST_ADDED
  7. `_detect_and_notify_transitions` (rename + extend)
  8. Bot join button gate fix
  9. `_format_join_notification_message` waitlist dispatch
  10. Frontend checkbox UI + type additions
  11. Open slot placeholders in `_add_participant_fields` (bot) and participant display components (frontend)
- **Dependencies**: No DB migration; no new tables; no RabbitMQ schema changes
- **Success Criteria**:
  - SELF_ADDED players land in overflow when `signup_method == HOST_SELECTED_WITH_WAITLIST`
  - Players who join receive waitlist DM, not confirmed DM
  - Host drags SELF_ADDED → save → player is now HOST_ADDED (confirmed), receives promotion DM
  - When any player moves from confirmed to overflow (any mode), they receive demotion DM
  - All 10 callers pass `signup_method` explicitly
  - Bot join button enabled for the new mode
  - Bot embed and web frontend show `open slot` entries for each unfilled confirmed slot in all game types; count decrements reactively as players are promoted
