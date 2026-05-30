<!-- markdownlint-disable-file -->

# Task Details: HOST_SELECTED_WITH_WAITLIST signup mode

## Research Reference

**Source Research**: #file:../research/20260530-01-host-selected-waitlist-research.md

---

## Phase 1: Enum Additions

### Task 1.1: Add HOST_SELECTED_WITH_WAITLIST to Python SignupMethod enum

Add new value with `display_name` and `description` properties following the existing pattern in
`shared/models/signup_method.py`.

```python
HOST_SELECTED_WITH_WAITLIST = "HOST_SELECTED_WITH_WAITLIST"
```

In the `display_name` property add a case for `HOST_SELECTED_WITH_WAITLIST` returning
`"Host Selected (with Waitlist)"`. In the `description` property return
`"Players can join a waitlist; the host promotes them to confirmed."`.

No Alembic migration is needed — `signup_method` is a free-form string column.

- **Files**:
  - `shared/models/signup_method.py` — add enum value + display_name/description cases
- **Success**:
  - `from shared.models.signup_method import SignupMethod; SignupMethod.HOST_SELECTED_WITH_WAITLIST` works
  - `uv run pytest tests/unit` passes (no existing tests broken)
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 5-14) — SignupMethod enum structure
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 95-100) — no migration needed
- **Dependencies**: none

### Task 1.2: Mirror enum in TypeScript

Add to `frontend/src/types/index.ts`:

```typescript
HOST_SELECTED_WITH_WAITLIST = 'HOST_SELECTED_WITH_WAITLIST',
```

Add a `SIGNUP_METHOD_INFO` entry for the new value with label
`"Host Selected (with Waitlist)"` and description
`"Players join a waitlist; the host promotes them to confirmed."`.

- **Files**:
  - `frontend/src/types/index.ts` — add enum value + SIGNUP_METHOD_INFO entry
- **Success**:
  - `cd frontend && npm run build` succeeds
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 70-75) — TypeScript mirror pattern
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 273-283) — frontend type additions
- **Dependencies**: Task 1.1

---

## Phase 2: Core Partition Logic + Demotion Detection (TDD)

### Task 2.1 (RED): Add signup_method stub and entered_waitlist stub + xfail tests

Add `signup_method` parameter to `partition_participants` in
`shared/utils/participant_sorting.py`:

```python
def partition_participants(
    participants: list["GameParticipant"],
    max_players: int | None = None,
    signup_method: SignupMethod = SignupMethod.SELF_SIGNUP,
) -> PartitionedParticipants:
```

The existing body is unchanged — the new `HOST_SELECTED_WITH_WAITLIST` branch raises
`NotImplementedError` as a stub. Insert it inside the existing conditional structure
(after the existing sorting, before the slice).

Add `entered_waitlist()` stub method to `PartitionedParticipants`:

```python
def entered_waitlist(self, previous: "PartitionedParticipants") -> set[str]:
    raise NotImplementedError("entered_waitlist not yet implemented")
```

Write xfail tests in `tests/unit/shared/utils/test_participant_sorting.py`:

- `test_partition_host_selected_waitlist_only_host_added_in_confirmed` — HOST_ADDED <= max
  fills confirmed; SELF_ADDED go to overflow
- `test_partition_host_selected_waitlist_excess_host_added_overflow` — HOST_ADDED > max_players;
  extras go to overflow before SELF_ADDED
- `test_partition_host_selected_waitlist_empty_host_added` — no HOST_ADDED; all SELF_ADDED
  in overflow
- `test_entered_waitlist_detects_confirmed_to_overflow_transition` — player present in
  previous.confirmed now in self.overflow
- `test_entered_waitlist_returns_empty_when_no_demotions` — no movement

All marked `@pytest.mark.xfail(reason="...", strict=True)`.

- **Files**:
  - `shared/utils/participant_sorting.py` — stub + param addition
  - `tests/unit/shared/utils/test_participant_sorting.py` — 5 new xfail tests
- **Success**:
  - `uv run pytest tests/unit/shared/utils/test_participant_sorting.py -v` shows new tests as `xfailed`
  - All existing tests in the file still pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 100-128) — partition logic spec
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 130-140) — entered_waitlist spec
- **Dependencies**: Phase 1 complete

### Task 2.2 (GREEN): Implement partition_participants new mode + entered_waitlist

Replace the `NotImplementedError` branch with actual logic:

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

Implement `entered_waitlist()`:

```python
def entered_waitlist(self, previous: "PartitionedParticipants") -> set[str]:
    return {
        discord_id
        for discord_id in previous.confirmed_real_user_ids
        if discord_id in self.overflow_real_user_ids
    }
```

Remove `xfail` markers from the 5 tests added in Task 2.1.

- **Files**:
  - `shared/utils/participant_sorting.py` — implement both functions
  - `tests/unit/shared/utils/test_participant_sorting.py` — remove xfail markers
- **Success**:
  - `uv run pytest tests/unit/shared/utils/test_participant_sorting.py -v` — all tests pass (none xfailed)
  - `uv run mypy shared/` — no errors
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 100-140) — full spec
- **Dependencies**: Task 2.1

---

## Phase 3: New DM Formats (TDD)

### Task 3.1 (RED): Stub join_waitlist and waitlist_demotion + xfail tests

Add stubs to `DMFormats` in `shared/message_formats.py`:

```python
@staticmethod
def join_waitlist(game_title: str, jump_url: str | None = None) -> str:
    raise NotImplementedError("join_waitlist not yet implemented")

@staticmethod
def waitlist_demotion(game_title: str, jump_url: str | None = None) -> str:
    raise NotImplementedError("waitlist_demotion not yet implemented")
```

Write xfail tests in `tests/unit/shared/test_message_formats.py`:

- `test_join_waitlist_contains_game_title`
- `test_join_waitlist_contains_waitlist_text` — output does not say "joined", does indicate waitlist
- `test_join_waitlist_with_jump_url_includes_link`
- `test_join_waitlist_without_jump_url_omits_link`
- `test_waitlist_demotion_contains_game_title`
- `test_waitlist_demotion_with_jump_url_includes_link`

All marked `@pytest.mark.xfail(reason="...", strict=True)`.

- **Files**:
  - `shared/message_formats.py` — 2 stubs
  - `tests/unit/shared/test_message_formats.py` — 6 xfail tests
- **Success**:
  - New tests show as `xfailed`; existing tests pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 142-157) — DM format spec
- **Dependencies**: Phase 2 complete

### Task 3.2 (GREEN): Implement join_waitlist and waitlist_demotion

```python
@staticmethod
def join_waitlist(game_title: str, jump_url: str | None = None) -> str:
    text = f"\U0001f3ab You're on the waitlist for **{game_title}**. The host will confirm participants."
    if jump_url:
        text += f"\n[View game in Discord]({jump_url})"
    return text

@staticmethod
def waitlist_demotion(game_title: str, jump_url: str | None = None) -> str:
    text = f"\u26a0\ufe0f A change by the host has moved you to the waitlist for **{game_title}**."
    if jump_url:
        text += f"\n[View game in Discord]({jump_url})"
    return text
```

Remove `xfail` markers from the 6 tests added in Task 3.1.

- **Files**:
  - `shared/message_formats.py` — implement 2 methods
  - `tests/unit/shared/test_message_formats.py` — remove xfail markers
- **Success**:
  - `uv run pytest tests/unit/shared/test_message_formats.py -v` — all tests pass
  - `uv run mypy shared/` — no errors
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 142-157)
- **Dependencies**: Task 3.1

---

## Phase 4: Backend Services — Callers + Upsert + Transitions (TDD)

### Task 4.1: Update all 10 partition_participants callers to pass signup_method

Add `signup_method=game.signup_method` to every call site. All callers already have
`game` in scope:

- `shared/services/game_schedules.py` line 71
- `services/api/services/games.py` lines 936, 1538, 1733, 1818
- `services/api/routes/games.py` line 1076
- `services/bot/events/handlers.py` lines 459, 658, 1249, 1299

- **Files**: 4 production files listed above
- **Success**:
  - `uv run pytest tests/unit` passes — no existing tests broken
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 88-93) — call site inventory
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 100-114) — param spec
- **Dependencies**: Phase 2 complete

### Task 4.2 (RED): \_update_prefilled_participants upsert stub + xfail test

In `services/api/services/games.py`, inside `_update_prefilled_participants`, after the
`existing_participant_ids` separation step, add a guarded stub that only executes when
`game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST`:

```python
if game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:
    raise NotImplementedError("SELF_ADDED upsert not yet implemented")
```

Write xfail test `test_update_prefilled_promotes_self_added_participants` in
`tests/unit/services/api/services/test_games.py`:

- Sets up a game with `signup_method == HOST_SELECTED_WITH_WAITLIST` and a SELF_ADDED
  participant whose `id` appears in `participant_data_list`
- Asserts `position_type` becomes `HOST_ADDED` and `position` is set correctly

- **Files**:
  - `services/api/services/games.py` — guarded NotImplementedError stub
  - `tests/unit/services/api/services/test_games.py` — 1 xfail test
- **Success**: new test shows as `xfailed`; existing tests pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 172-196) — upsert logic spec
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 29-41) — \_update_prefilled flow
- **Dependencies**: Task 4.1

### Task 4.3 (GREEN): Implement \_update_prefilled_participants upsert

Replace the stub with:

```python
if game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:
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

Remove xfail from task 4.2 test.

- **Files**:
  - `services/api/services/games.py`
  - `tests/unit/services/api/services/test_games.py`
- **Success**: `uv run pytest tests/unit/services/api/services/test_games.py -v` all pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 172-196)
- **Dependencies**: Task 4.2

### Task 4.4 (RED): \_detect_and_notify_transitions rename + demotion stub + xfail tests

Rename `_detect_and_notify_promotions` to `_detect_and_notify_transitions` and update both
call sites of the old name. Extend the method to detect demotions via `entered_waitlist()`,
with a `_notify_demoted_users` stub that raises `NotImplementedError`.

Write xfail tests:

- `test_detect_transitions_notifies_demoted_users` — `_notify_demoted_users` is called when
  a player moves from confirmed to overflow
- `test_detect_transitions_sends_demotion_dm` — `DMFormats.waitlist_demotion` is used inside
  `_notify_demoted_users`

- **Files**:
  - `services/api/services/games.py`
  - `tests/unit/services/api/services/test_games.py`
- **Success**: xfail tests show as expected failures; existing promotion tests pass (renamed method)
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 160-175) — transitions spec
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 130-140) — entered_waitlist usage
- **Dependencies**: Task 4.3

### Task 4.5 (GREEN): Implement \_notify_demoted_users

Implement `_notify_demoted_users` following the same DM-send pattern as
`_notify_promoted_users`, using `DMFormats.waitlist_demotion`.

Remove stubs and xfail markers.

- **Files**:
  - `services/api/services/games.py`
  - `tests/unit/services/api/services/test_games.py`
- **Success**: all services tests pass; `uv run mypy services/` clean
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 160-175)
- **Dependencies**: Task 4.4

### Task 4.6: Integration tests for Phase 4 functionality

Add integration tests to `tests/integration/test_game_signup_methods.py` after the
Phase 4 production code is working. These verify DB persistence and the full event
pipeline that unit mocks cannot confirm.

Three test cases:

- `test_host_selected_with_waitlist_signup_method_db_roundtrip` — create a game with
  `signup_method == HOST_SELECTED_WITH_WAITLIST`, read it back via the API, confirm the
  value survives the API → DB → event pipeline unchanged.
- `test_update_prefilled_upserts_self_added_participant` — set up a game with a
  SELF_ADDED participant, PUT the game with that participant's `participant_id` in the
  prefilled list, query the DB directly and assert `position_type` is now `HOST_ADDED`.
- `test_demotion_notification_published_when_participant_demoted` — verify the full
  API → DB → RabbitMQ chain: reduce `max_players` (or change `signup_method`) so a
  confirmed player moves to overflow, then assert a demotion event is published to the
  queue (mirrors the existing promotion notification integration test pattern).

- **Files**:
  - `tests/integration/test_game_signup_methods.py` — 3 new integration tests
- **Success**:
  - `scripts/run-integration-tests.sh tests/integration/test_game_signup_methods.py` passes
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 239-252) — integration test scope
- **Dependencies**: Tasks 4.1–4.5 complete (all Phase 4 production code working)

---

## Phase 5: Bot Changes (TDD)

### Task 5.1: Fix join button gate in game_view.py

Change the join button disable condition so `HOST_SELECTED_WITH_WAITLIST` does NOT disable
the button (players can join the waitlist). Only `HOST_SELECTED` disables:

```python
game.signup_method in (SignupMethod.HOST_SELECTED,)
```

Write a direct unit test (no xfail) verifying the button is enabled for
`HOST_SELECTED_WITH_WAITLIST`.

- **Files**:
  - `services/bot/views/game_view.py` — fix disable condition
  - corresponding unit test file — 1 new direct test
- **Success**: test passes; `uv run pytest tests/unit` clean
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 48-51) — game_view analysis
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 197-201) — bot join button spec
- **Dependencies**: Phase 4 complete

### Task 5.2 (RED): \_format_join_notification_message waitlist dispatch stub + xfail test

In `services/bot/events/handlers.py`, inside `_format_join_notification_message`, add a
guarded stub before the existing `join_simple`/`join_with_instructions` branching:

```python
if game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:
    raise NotImplementedError("join_waitlist DM dispatch not yet implemented")
```

Write xfail test `test_format_join_notification_dispatches_waitlist_dm` verifying
`DMFormats.join_waitlist` is called (not `join_simple` or `join_with_instructions`) when
`signup_method == HOST_SELECTED_WITH_WAITLIST`.

- **Files**:
  - `services/bot/events/handlers.py`
  - `tests/unit/services/bot/events/test_handlers.py`
- **Success**: xfail test shows as expected failure; existing handler tests pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 157-163) — dispatch spec
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 51-59) — handlers analysis
- **Dependencies**: Task 5.1

### Task 5.3 (GREEN): Implement waitlist join DM dispatch

Replace the stub with:

```python
if game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:
    return DMFormats.join_waitlist(game_title=game.title, jump_url=jump_url)
```

Remove stub and xfail marker.

- **Files**:
  - `services/bot/events/handlers.py`
  - `tests/unit/services/bot/events/test_handlers.py`
- **Success**: all bot handler tests pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 157-163)
- **Dependencies**: Task 5.2

### Task 5.4: E2E tests for Phase 5 functionality

Add e2e tests after the Phase 5 production code is working. These verify actual Discord
behavior that cannot be tested without a live bot.

Three test cases:

- `test_join_button_enabled_for_host_selected_with_waitlist` — add to
  `tests/e2e/test_signup_methods.py` alongside existing `SELF_SIGNUP`/`HOST_SELECTED`
  button-state cases; assert the Join button is present and enabled on the Discord
  message for a `HOST_SELECTED_WITH_WAITLIST` game.
- `test_join_dm_says_waitlist_for_host_selected_with_waitlist` — add to
  `tests/e2e/test_join_notification.py`; join a `HOST_SELECTED_WITH_WAITLIST` game and
  assert the DM received from Discord contains waitlist language (not "joined").
- `test_promotion_drag_delivers_promotion_dm` — covers the full chain:
  PUT game with a SELF_ADDED participant's `participant_id` in the prefilled list →
  DB upsert sets `position_type = HOST_ADDED` → `cleared_waitlist()` detects transition →
  promotion DM delivered in Discord. Add to `tests/e2e/test_join_notification.py` or a
  new `test_waitlist_promotion.py` file.

- **Files**:
  - `tests/e2e/test_signup_methods.py` — 1 new e2e test
  - `tests/e2e/test_join_notification.py` — 2 new e2e tests (or new `test_waitlist_promotion.py`)
- **Success**:
  - `scripts/run-e2e-tests.sh tests/e2e/test_signup_methods.py` passes
  - `scripts/run-e2e-tests.sh tests/e2e/test_join_notification.py` passes
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 253-267) — e2e test scope
- **Dependencies**: Tasks 5.1–5.3 complete; Task 4.6 integration tests passing

---

## Phase 6: Open Slot Placeholders — Bot (TDD)

### Task 6.1 (RED): Stub open slot padding in \_add_participant_fields + xfail tests

In `services/bot/game_message.py`, inside `_add_participant_fields`, add a stub that raises
`NotImplementedError` for the padding logic. The stub should only activate when
`max_players is not None` and `len(participant_ids) < max_players`.

Write xfail tests:

- `test_add_participant_fields_shows_open_slots_when_under_capacity` — game with 2 of 5
  confirmed slots shows 3 "open slot" entries in the rendered fields
- `test_add_participant_fields_no_open_slots_when_at_capacity` — full game shows no
  placeholder entries

- **Files**:
  - `services/bot/game_message.py` — stub
  - corresponding unit test file — 2 xfail tests
- **Success**: xfail tests show as expected failures; existing field tests pass
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 203-215) — open slot spec
- **Dependencies**: Phase 5 complete

### Task 6.2 (GREEN): Implement open slot padding

```python
if max_players is not None and len(participant_ids) < max_players:
    empty_slots = max_players - len(participant_ids)
    participant_ids = list(participant_ids) + ["open slot"] * empty_slots
```

`format_user_or_placeholder()` already renders non-numeric strings as plain text — no
additional changes needed.

Remove stubs and xfail markers.

- **Files**:
  - `services/bot/game_message.py`
  - corresponding unit test file
- **Success**: `uv run pytest tests/unit` all pass; `uv run mypy services/` clean
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 203-215)
- **Dependencies**: Task 6.1

---

## Phase 7: Frontend Changes (TypeScript)

### Task 7.1: GameForm checkbox UI for HOST_SELECTED_WITH_WAITLIST (TDD)

In `frontend/src/components/GameForm.tsx`, when `signupMethod == SignupMethod.HOST_SELECTED`,
render a checkbox labelled "Players can join waitlist (host selects from queue)":

- Checked → set `signupMethod = SignupMethod.HOST_SELECTED_WITH_WAITLIST`
- Unchecked → set `signupMethod = SignupMethod.HOST_SELECTED`
- When `signupMethod == SignupMethod.HOST_SELECTED_WITH_WAITLIST`, the `HOST_SELECTED`
  radio option appears selected (checkbox is the sub-option)

Follow TDD: write `test.failing(...)` test first asserting the checkbox renders and toggles
correctly, then implement.

- **Files**:
  - `frontend/src/components/GameForm.tsx`
  - `frontend/src/components/GameForm.test.tsx` (or `__tests__/GameForm.test.tsx`)
- **Success**:
  - `cd frontend && npm run test` all pass
  - `cd frontend && npm run build` succeeds
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 258-283) — checkbox UI spec
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 76-86) — GameForm context
- **Dependencies**: Task 1.2, Phase 6 complete

### Task 7.2: Open slot placeholders in participant display components (TDD)

In `frontend/src/components/EditableParticipantList.tsx` and/or read-only participant display,
compute `max_players - confirmed.length` and render that many read-only rows with italicised
"open slot" text. These rows are pure JSX and are never submitted.

Follow TDD: write failing test first.

- **Files**:
  - `frontend/src/components/EditableParticipantList.tsx` and/or read-only display component
  - corresponding test file
- **Success**:
  - `cd frontend && npm run test` all pass
  - `cd frontend && npm run build` succeeds
- **Research References**:
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 203-215) — open slot spec
  - #file:../research/20260530-01-host-selected-waitlist-research.md (Lines 76-86) — component context
- **Dependencies**: Task 7.1

---

## Dependencies

- No Alembic migration required
- No new RabbitMQ message types
- Python 3.12+ (match/case, StrEnum)
- `uv` for dependency and virtual environment management
- `vitest` for frontend tests

## Success Criteria

- All 10 `partition_participants` callers pass `signup_method` explicitly
- SELF_ADDED players land in overflow under `HOST_SELECTED_WITH_WAITLIST`
- Players who join receive `join_waitlist` DM (not confirmed DM)
- Host drags SELF_ADDED player to confirmed position, saves, and player becomes HOST_ADDED
  and receives promotion DM
- Any player moving from confirmed to overflow (all modes) receives demotion DM
- Bot join button enabled for `HOST_SELECTED_WITH_WAITLIST`
- Bot embed shows "open slot" placeholders for unfilled confirmed slots (all game types)
- Frontend participant display shows open slot placeholder rows
- GameForm shows checkbox sub-option when HOST_SELECTED radio is selected
- `uv run pytest tests/unit` — all pass
- `uv run mypy shared/ services/` — no errors
- `cd frontend && npm run build && npm run test` — all pass
