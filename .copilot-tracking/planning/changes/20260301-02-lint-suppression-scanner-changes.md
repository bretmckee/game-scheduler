# Changes: Lint Suppression Scanner Pre-commit Hook

## Status: Complete

## Files Created / Modified

- `scripts/check_lint_suppressions.py` — New pre-commit hook script
- `tests/unit/scripts/__init__.py` — New (enables pytest discovery)
- `tests/unit/scripts/test_check_lint_suppressions.py` — New unit tests
- `.pre-commit-config.yaml` — New `check-lint-suppressions` hook entry after `jscpd-diff`
- `.github/instructions/quality-check-overrides.instructions.md` — Added missing lizard/complexipy patterns and `APPROVED_OVERRIDES` section

## Phase 1 Progress

### Task 1.1 — Stub created

`scripts/check_lint_suppressions.py` created with `BLOCKED_PATTERNS` and
`COUNTED_PATTERNS` module-level constants; `main()` raises `NotImplementedError`.

### Task 1.2 — xfail tests written

All tests in `tests/unit/scripts/test_check_lint_suppressions.py` written with
real assertions and `@pytest.mark.xfail(strict=True)` decorators covering:

- Each blocked pattern causes non-zero exit and prints `<file>:<line>:` output
- Each counted pattern fails when `APPROVED_OVERRIDES=0`
- `APPROVED_OVERRIDES=1` permits exactly one counted suppression
- `APPROVED_OVERRIDES=1` does NOT permit a bare (blocked) suppression
- Clean diff exits 0
- `+++` header lines are not counted
- `-` prefix (removed) lines are not counted

### Task 1.3 — Implemented, xfail removed

`main()` fully implemented using `git diff --cached --unified=0` via subprocess.
All previously-xfail tests now pass without modification to assertions.

### Task 1.4 — Refactored, edge case tests added

Implementation refactored for clarity. Additional edge case tests added and passing.

## Phase 2 Progress

### Task 2.1 — Hook registered in `.pre-commit-config.yaml`

New `check-lint-suppressions` hook added after `jscpd-diff` with `language: python`,
`pass_filenames: false`, and no `additional_dependencies`.
`pre-commit run check-lint-suppressions --all-files` exits 0 on a clean working tree.

### Task 2.2 — `quality-check-overrides.instructions.md` updated

Added four missing patterns to the Linter Suppression Comments list:
`# noqa: complexipy`, `#lizard forgives`, `#lizard forgives(metric)`, `#lizard forgive global`.
Added new `APPROVED_OVERRIDES Environment Variable` section documenting the gated pathway.
