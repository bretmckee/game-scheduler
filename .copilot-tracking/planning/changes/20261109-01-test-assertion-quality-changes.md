<!-- markdownlint-disable-file -->

# Release Changes: Test Assertion Quality (hollow provider assertions)

**Related Plan**: 20261109-01-test-assertion-quality.plan.md
**Implementation Date**: 2026-11-12

## Summary

Stop the test-assertion checker from forcing or accepting hollow `assert_called_once_with()` on dependency getters, clean up existing hollow sites, and document the checker's rules.

## Changes

### Added

- tests/unit/scripts/test_check_test_assertions.py - Tests that a patch alias used only inside another `assert_*` call's arguments, or as an operand of `==`/`!=`/`is`/`is not`/`in`/`not in` in an `assert`, counts as verified (written as strict xfail in Phase 1, xfail removed in Phase 2); guard test that bare `assert mock_x` is still a violation

### Modified

- scripts/check_test_assertions.py - `get_unasserted_named_mocks` now also accepts an alias referenced in `assert_*` call arguments (`_alias_used_in_assert_call_args`) or in an equality/identity/membership comparison inside `assert` (`_alias_used_in_assert_comparison`); bare truthiness checks still do not count

### Removed

## Notes

- `uv run python scripts/check_test_assertions.py --all` output is identical before and after the Phase 2 fix (clean under the current allowlist), so the fix introduced no new violations.
