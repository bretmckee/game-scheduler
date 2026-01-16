---
applyTo: ".copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Reducing Complexity of GameService::create_game()

## Overview

Refactor the 344-line `GameService::create_game()` method to reduce cyclomatic complexity from 24 to below 15 and cognitive complexity from 48 to below 20 through Extract Method pattern.

## Objectives

- Reduce cyclomatic complexity from 24 to below 15
- Reduce cognitive complexity from 48 to below 20
- Create focused, single-responsibility helper methods
- Maintain all existing functionality and error handling
- Enable progressive threshold reduction

## Research Summary

### Project Files

- services/api/services/games.py (lines 87-430) - Monolithic `create_game()` function, worst complexity offender in codebase

### External References

- #file:../research/20260107-create-game-complexity-reduction-research.md - Comprehensive complexity analysis and refactoring strategy
- Martin Fowler's "Refactoring" - Extract Method pattern
- Robert Martin's "Clean Code" - Single Responsibility Principle

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines
- #file:../../.github/instructions/coding-best-practices.instructions.md - General best practices

## Implementation Checklist

### [x] Phase 1: Test Harness Validation

- [x] Task 1.1: Review existing test coverage for `create_game()`
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 20-32)

- [x] Task 1.2: Run tests to establish baseline
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 34-42)

### [x] Phase 2: Host Resolution Extraction

- [x] Task 2.1: Create `_resolve_game_host()` method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 44-63)

- [x] Task 2.2: Update `create_game()` to call new method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 65-74)

- [x] Task 2.3: Verify tests pass and complexity reduced
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 76-84)

### [x] Phase 3: Template Field Resolution Extraction

- [x] Task 3.1: Create `_resolve_template_fields()` method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 86-103)

- [x] Task 3.2: Update `create_game()` to use resolved fields dictionary
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 105-113)

- [x] Task 3.3: Add unit tests for extracted method
  - Details: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 3, Task 3.3)

- [x] Task 3.4: Remove redundant integration tests
  - Details: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 3, Task 3.4)

- [x] Task 3.5: Verify tests pass and complexity reduced
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 115-123)

### [x] Phase 4: Participant Record Creation Extraction

- [x] Task 4.1: Create `_create_participant_records()` method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 125-141)

- [x] Task 4.2: Update `create_game()` to call new method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 143-150)

- [x] Task 4.3: Create unit tests for extracted method
  - Details: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 4, Task 4.3)

- [x] Task 4.4: Simplify redundant create_game tests
  - Details: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 4, Task 4.4)

- [x] Task 4.5: Verify tests pass
  - Details: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 4, Task 4.5)

### [x] Phase 5: Status Schedule Creation Extraction

- [x] Task 5.1: Create `_create_game_status_schedules()` method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 162-178)
  - Completed: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 5, Task 5.1)

- [x] Task 5.2: Update `create_game()` to call new method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 180-187)
  - Completed: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 5, Task 5.2)

- [x] Task 5.3: Add unit tests for extracted method
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 189-197)
  - Completed: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 5, Task 5.3)

- [x] Task 5.4: Remove redundant integration tests
  - Completed: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 5, Task 5.4)

- [x] Task 5.5: Verify tests pass and complexity reduced
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 189-197)
  - Completed: .copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md (Phase 5, Task 5.5)

### [x] Phase 6: Optional Further Refinements

- [x] Task 6.1: Consider additional extractions
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 199-213)

- [x] Task 6.2: Verify final complexity metrics
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 215-224)

### [x] Phase 7: Update Complexity Thresholds

- [x] Task 7.1: Update Ruff configuration with new thresholds
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 226-237)

- [x] Task 7.2: Verify all checks pass with new thresholds
  - Details: .copilot-tracking/details/20260107-create-game-complexity-reduction-details.md (Lines 239-246)

## Dependencies

- Existing test suite for `create_game()` in tests/services/api/test_games.py
- SQLAlchemy async session behavior
- Participant resolver service
- Role verification service
- Notification schedule service
- Ruff linting tool for complexity analysis

## Success Criteria

- All existing tests pass without modification
- Cyclomatic complexity reduced from 24 to below 15
- Cognitive complexity reduced from 48 to below 20
- All extracted methods have complexity below 10
- No changes to public API or behavior
- Code is more readable and maintainable
- Complexity thresholds updated to prevent regression
