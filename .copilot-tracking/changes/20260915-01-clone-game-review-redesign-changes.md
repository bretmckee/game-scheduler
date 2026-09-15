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
