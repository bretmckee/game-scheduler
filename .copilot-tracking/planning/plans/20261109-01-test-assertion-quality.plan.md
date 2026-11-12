---
applyTo: '.copilot-tracking/planning/changes/20261109-01-test-assertion-quality-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Test Assertion Quality (hollow provider assertions)

## Overview

Stop the test-assertion checker from forcing or accepting hollow `assert_called_once_with()` on dependency getters, clean up existing hollow sites, and document the checker's rules.

## Objectives

- Fix checker false positive (alias used inside another assertion or a comparison)
- Remove 6 provider getters from `no-arg-methods`; zero violations under `--all`
- Rewrite ~84 hollow sites and 8 marker sites; marker count 25 -> 19
- Document checker rules in unit-tests.instructions.md and the fix-patterns doc

## Research Summary

### Project Files

- scripts/check_test_assertions.py - checker (alias logic L160-207, allowlist exemption L398-427)
- pyproject.toml L246-247 - `no-arg-methods`
- tests/unit/scripts/test_check_test_assertions.py - checker tests (78)

### External References

- .copilot-tracking/research/20261109-01-test-assertion-quality-research.md - full findings and site lists

### Standards References

- .github/instructions/test-driven-development.instructions.md - TDD for Phases 1-2; retrofit guidance for Phases 3-5
- .github/instructions/unit-tests.instructions.md - assertion quality
- .github/instructions/quality-check-overrides.instructions.md - `APPROVED_WEAK_ASSERTIONS` gating

## Implementation Checklist

### [x] Phase 1: RED - checker xfail tests

- [x] Task 1.1: Add strict-xfail tests (assert-arg use ok, comparison use ok) plus guard test (bare `assert mock_x` violates)
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 15-28)

### [x] Phase 2: GREEN - checker fix

- [x] Task 2.1: Count alias use in assert-call args and assert comparisons; remove xfail
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 30-39)

### [x] Phase 3: Cleanup - largest provider files

- [x] Task 3.1: Rewrite hollow provider assertions in the five largest files
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 41-52)

### [x] Phase 4: Cleanup - remaining files and provider markers

- [x] Task 4.1: Rewrite remaining provider sites (16 other files)
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 54-63)

- [x] Task 4.2: Remove the 6 provider markers (incl. 6882f984 tests)
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 65-72)

### [x] Phase 5: Non-provider sites, getter-under-test markers, config trim

- [x] Task 5.1: Fix 2 hollow non-provider markers, 2 getter-under-test tests, test_api_main
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 76-88)

- [x] Task 5.2: Trim `no-arg-methods`, add provider regression test, `--all` clean
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 90-97)

### [x] Phase 6: Docs

- [x] Task 6.1: Update unit-tests.instructions.md and fix-test-assertion-violations.md
  - Details: .copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md (Lines 101-111)

## Dependencies

- `uv`, pytest, mypy, pre-commit `check-test-assertions` hook
- Plan should run after the game-time-change-notification plan, in its own PR

## Success Criteria

- Checker suite passes incl. new tests; `uv run python scripts/check_test_assertions.py --all` clean
- Marker count 25 -> 19; `uv run pytest tests/unit` and mypy pass at every phase
