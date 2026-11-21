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
