<!-- markdownlint-disable-file -->

# Changes: Clone Game Review/Edit-Before-Create Redesign

## Summary

Tracks implementation of the 10-phase clone-game redesign (GameForm-based review/edit-before-create
clone screen delegating to `create_game`). This file is updated as each phase completes.

## Phase 1: Fix `resolve_mentions_in_text`'s Regex To Skip Already-Resolved `<@id>` Tokens

Bug fix: `resolve_mentions_in_text`'s mention-token regex (`@\w+(?:\.\w+)*`) matched the `@<id>`
substring inside an already-resolved Discord mention token (`<@discord_id>`), causing it to be
re-parsed as an unresolved `@<id>` username and produce a spurious "User not found" validation
error. Fixed by adding a `(?<!<)` negative lookbehind, mirroring the identical exclusion already
used by `channel_resolver.py`'s `#`-mention regex (`(?<!<)#([^\s<>#]+)`). This is a prerequisite
for Phase 4's delegation, which will unconditionally re-run mention resolution against inherited
free-text fields that may already contain resolved mentions.

### Added

- `tests/unit/services/api/services/test_participant_resolver.py` — three new regression tests for
  `resolve_mentions_in_text` (Task 1.1):
  - `test_resolve_mentions_in_text_skips_already_resolved_mention` — RED case; written first with
    `@pytest.mark.xfail(strict=True)`, confirmed `XFAIL` before the fix, marker removed after
  - `test_resolve_mentions_in_text_mixed_resolved_and_unresolved` — RED case (mixed `<@111>` and
    `@bob` in one string); same xfail→remove cycle
  - `test_resolve_mentions_in_text_real_mention_still_resolved` — regression guard for
    already-correct behavior (plain `@alice` mention); written to pass immediately, no xfail

### Modified

- `services/api/services/participant_resolver.py` (`resolve_mentions_in_text`) — changed
  `tokens = re.findall(r"@\w+(?:\.\w+)*", text)` to
  `tokens = re.findall(r"(?<!<)@\w+(?:\.\w+)*", text)`; updated the surrounding comment and the
  method's docstring to document the exclusion (Task 1.1)

### Verification

- `uv run pytest tests/unit` — 2580 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

## Phase 2: Extend `CloneGameRequest` With Override Fields, `post_at`, and `participants`

Added 14 new optional fields to `CloneGameRequest` (13 nullable overrides plus `participants`,
which defaults to `[]` rather than `None`), copied verbatim from `GameCreateRequest`'s field
constraints (`shared/schemas/game.py`). These are pure schema additions — nothing reads them yet
(that starts in Phase 4's `clone_game` delegation). No `channel_id`, `rewards`,
`allowed_player_role_ids`, or `notify_role_ids` fields were added, per the details file's Design
Note 4 (none of these are overridable anywhere in the system today). No `signup_method` value
validator or `post_at < scheduled_at` validator was added to `CloneGameRequest` itself — both are
already enforced for free when `clone_game` constructs the delegated `GameCreateRequest` in
Phase 4.

### Added

- `tests/unit/schemas/test_clone_game_schema.py` — five new tests for the new fields (Task 2.2):
  - `test_clone_request_accepts_override_fields` — RED case; written first with
    `@pytest.mark.xfail(strict=True)`, confirmed `XFAIL` before the fields were added, marker
    removed after; constructs a `CloneGameRequest` with all 14 new fields set and asserts each
    stored value
  - `test_clone_request_override_fields_default_to_none_when_omitted` — RED case; same
    xfail→remove cycle; confirms the 13 nullable fields default to `None` when omitted
    (backward compatibility with every existing caller)
  - `test_clone_request_participants_defaults_to_empty_list` — RED case; same xfail→remove
    cycle; confirms `participants` defaults to `[]`, not `None`, when omitted
  - `test_clone_request_title_exceeds_max_length_is_rejected` — RED case; same xfail→remove
    cycle; regression guard that `title`'s `max_length=200` constraint (copied from
    `GameCreateRequest`) is actually enforced, not just a bare `str | None` type hint
  - `test_clone_request_max_players_out_of_range_is_rejected` — RED case; same xfail→remove
    cycle; same regression guard for `max_players`'s `ge=1, le=100` constraint

### Modified

- `services/api/schemas/clone_game.py` (`CloneGameRequest`) — added `title`, `description`,
  `signup_instructions`, `where`, `max_players`, `reminder_minutes`, `expected_duration_minutes`,
  `signup_method`, `participants`, `host`, `remind_host_rewards`, `reminders_as_dms`, `post_at`,
  `recur_rule` fields (Task 2.1)

### Verification

- `uv run pytest tests/unit/schemas/test_clone_game_schema.py -v` — 5 new tests confirmed
  `XFAIL` before the field additions, all 12 tests `PASSED` after (xfail markers removed)
- `uv run pytest tests/unit` — 2585 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

## Phase 3: Add `default_host_user_id` To `create_game`/`_resolve_game_host`

Added a new, optional `default_host_user_id: str | None = None` parameter to both
`_resolve_game_host` and `create_game`, threaded through unchanged. This decouples "who is
performing the request" (the bot-manager-permission-check subject, still `requester_user_id`/
`host_user_id`) from "who the game's host should default to when no `host` override is
specified" (previously always the requester). `clone_game` (Phase 4) will pass
`source_game.host_id` as `default_host_user_id` while still passing `current_user`'s ID as
`host_user_id`, so a bot-manager-only host override on a clone is still checked against the
cloning user, not the source game's host. Purely additive: when the new parameter is omitted
(both existing call sites — `services/api/routes/games.py`'s `create_game` route, and
`create_game`'s internal call to `_resolve_game_host`), behavior is byte-for-byte identical to
before, since `default_host_user_id` defaults to `None`, which falls back to
`requester_user_id`/`host_user_id` exactly as the old unconditional assignment did.

### Added

- `tests/unit/services/api/services/test_games_service.py` — two new tests for
  `_resolve_game_host` (Task 3.1):
  - `test_resolve_game_host_default_host_user_id_used_when_no_override` — RED case; written
    first with `@pytest.mark.xfail(strict=True)` (confirmed `XFAIL` against pre-Phase-3 code,
    since `_resolve_game_host` didn't accept the keyword yet), marker removed after the change;
    asserts that with no `host` override, the resolved host is `default_host_user_id`, not the
    requester
  - `test_resolve_game_host_default_host_user_id_does_not_change_permission_subject` — RED case;
    same xfail→remove cycle; with a `host` override set and `default_host_user_id` also passed,
    asserts the override still wins and `check_bot_manager_permission` was called with the
    requester's `discord_id` (not the default host's) — confirming the two identities stay
    decoupled

### Modified

- `services/api/services/games.py` — `_resolve_game_host` gained `default_host_user_id: str |
None = None`; `actual_host_user_id` now initializes from
  `default_host_user_id if default_host_user_id is not None else requester_user_id` instead of
  unconditionally from `requester_user_id`. `create_game` gained the same parameter (positioned
  after `host_user_id`) and forwards it to `_resolve_game_host`. Docstrings updated on both
  methods. No call sites changed — both existing calls use keyword arguments unaffected by the
  new parameter's position, or omit it and get identical behavior. Not yet wired to
  `clone_game` (Phase 4's job).

### Verification

- `uv run pytest tests/unit/services/api/services/test_games_service.py -k default_host_user_id -v`
  — 2 new tests confirmed `XFAIL` before the parameter was added, both `PASSED` after (xfail
  markers removed)
- `uv run pytest tests/unit` — 2587 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files
