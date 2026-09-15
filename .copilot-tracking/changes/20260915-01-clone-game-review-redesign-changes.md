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
