---
applyTo: ".copilot-tracking/changes/20260115-create-game-further-reduction-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Further Reduction of create_game() Method

## Overview

Extract helper methods from create_game() to reduce length from 179 lines to ~60-75 lines while maintaining complexity under limits.

## Objectives

- Reduce create_game() method length to 60-75 lines
- Maintain cyclomatic complexity < 15 and cognitive complexity < 20
- Extract dependency loading into _load_game_dependencies()
- Extract game builder into _build_game_session() using GameMediaAttachments dataclass
- Extract schedule orchestration into _setup_game_schedules()
- Add comprehensive unit tests for all new helper methods
- Remove redundant tests for create_game() that are now covered by helper method tests

## Research Summary

### Project Files

- services/api/services/games.py (lines 333-511) - Current create_game() method at 179 lines, complexity 10

### External References

- #file:../research/20260115-create-game-further-reduction-research.md - Comprehensive analysis of refactoring opportunities

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards

## Implementation Checklist

### [ ] Phase A: Extract Dependency Loading and Game Builder

- [ ] Task A.1: Create GameMediaAttachments dataclass
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 15-35)

- [ ] Task A.2: Extract _load_game_dependencies() helper method
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 37-66)

- [ ] Task A.3: Add unit tests for _load_game_dependencies()
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 68-95)

- [ ] Task A.4: Extract _build_game_session() helper method
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 97-134)

- [ ] Task A.5: Add unit tests for _build_game_session()
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 136-162)

- [ ] Task A.6: Refactor create_game() to use new helper methods
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 164-192)

- [ ] Task A.7: Remove redundant create_game() tests
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 194-212)

### [ ] Phase B: Extract Schedule Orchestration

- [ ] Task B.1: Extract _setup_game_schedules() helper method
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 216-242)

- [ ] Task B.2: Add unit tests for _setup_game_schedules()
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 244-267)

- [ ] Task B.3: Refactor create_game() to use schedule helper
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 269-287)

### [ ] Phase C: Validation and Metrics

- [ ] Task C.1: Run complexity metrics verification
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 291-310)

- [ ] Task C.2: Verify all tests pass with full coverage
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 312-330)

- [ ] Task C.3: Run linter checks
  - Details: .copilot-tracking/details/20260115-create-game-further-reduction-details.md (Lines 332-350)

## Dependencies

- Python 3.11+
- SQLAlchemy ORM
- pytest for testing
- ruff linter with C901 (cyclomatic complexity) check
- complexipy for cognitive complexity metrics

## Success Criteria

- create_game() method reduced to 60-75 lines
- Cyclomatic complexity remains < 15
- Cognitive complexity remains < 20
- All existing functionality preserved
- All tests pass with maintained or improved coverage
- New helper methods have comprehensive unit tests
- Redundant tests removed without coverage loss
- Code follows project Python conventions
