---
applyTo: '.copilot-tracking/changes/20260125-remaining-duplication-elimination-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remaining Code Duplication Elimination

## Overview

Eliminate high and medium priority code duplications identified by jscpd analysis, focusing on security-critical authorization code and repetitive response construction patterns.

## Objectives

- Consolidate 4 authorization permission check functions into unified helper
- Extract response construction helpers for guilds, channels, and templates
- Eliminate participant count query duplication in bot handlers
- Improve code maintainability and reduce inconsistency risk

## Research Summary

### Project Files

- services/api/dependencies/permissions.py - Authorization pattern duplication (4 clone pairs)
- services/api/routes/guilds.py - Guild response construction (2 clone pairs)
- services/api/routes/channels.py - Channel response construction (2 clone pairs)
- services/api/routes/templates.py - Template operations (3 clone pairs)
- services/bot/handlers/join_game.py - Participant counting logic
- services/bot/handlers/leave_game.py - Participant counting logic
- services/api/services/display_names.py - Display name fetching (1 clone pair)

### External References

- #file:../research/20260125-remaining-code-duplication-analysis-research.md - Complete duplication analysis with 22 clone pairs categorized by priority

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding standards
- #file:../../.github/instructions/coding-best-practices.instructions.md - DRY principles and refactoring guidance
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Code documentation standards

## Implementation Checklist

### [x] Phase 1: Quick Wins - Participant Count Query

- [x] Task 1.1: Extract participant count helper function and create unit tests
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 15-40)

- [x] Task 1.2: Update join_game.py to use helper
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 42-53)

- [x] Task 1.3: Update leave_game.py to use helper
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 55-66)

### [x] Phase 2: Response Construction Patterns

- [x] Task 2.1: Extract guild config response builder and create unit tests
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 68-105)

- [x] Task 2.2: Update guild routes to use response builder
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 107-119)

- [x] Task 2.3: Extract channel config response builder and create unit tests
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 121-160)

- [x] Task 2.4: Update channel routes to use response builder
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 162-174)

- [x] Task 2.5: Consolidate template permission checks
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 176-191)

### [x] Phase 3: Authorization Pattern Consolidation

- [x] Task 3.1: Create generic permission requirement helper and create unit tests
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 193-243)

- [x] Task 3.2: Refactor require_manage_guild to use helper
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 245-257)

- [x] Task 3.3: Refactor require_manage_channels to use helper
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 259-271)

- [x] Task 3.4: Refactor require_bot_manager to use helper
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 273-285)

### [x] Phase 4: Optional Improvements

- [x] Task 4.1: Extract display name resolution helper and create unit tests (optional)
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 287-303)

- [x] Task 4.2: Consolidate game error handling (optional)
  - Details: .copilot-tracking/details/20260125-remaining-duplication-elimination-details.md (Lines 305-319)

## Dependencies

- pytest for test execution
- jscpd for verification of duplication reduction
- Existing authorization and route infrastructure

## Success Criteria

- All high-priority authorization duplications eliminated (4 clone pairs reduced)
- All medium-priority response construction duplications eliminated (7 clone pairs reduced)
- Participant count query consolidated into single utility function
- All new helper functions have unit tests with good coverage
- All existing tests pass
- Authorization tests verify consistent behavior across permission checks
- jscpd reports reduced clone count from 22 to 12 (45% reduction achieved, exceeding target of 11 or fewer)
