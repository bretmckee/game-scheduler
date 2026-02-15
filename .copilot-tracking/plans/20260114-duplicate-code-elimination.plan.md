---
applyTo: '.copilot-tracking/changes/20260114-duplicate-code-elimination-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Duplicate Code Elimination

## Overview

Reduce code duplication from 3.68% to under 2% by extracting common patterns into reusable functions and utilities across Python backend and TypeScript frontend.

## Objectives

- Eliminate ~90 lines of template response serialization duplication
- Eliminate ~80 lines of Discord API error handling duplication
- Eliminate ~40 lines of game embed formatting duplication
- Eliminate ~25 lines of TypeScript type definition duplication
- Eliminate ~35 lines of channel/message fetching duplication
- Maintain or improve test coverage
- Ensure no behavioral changes to existing functionality

## Research Summary

### Project Files

- services/api/routes/templates.py - 4 instances of TemplateResponse construction (31+ lines each)
- shared/discord/client.py - 6+ instances of HTTP error handling pattern (15-18 lines each)
- frontend/src/types/index.ts - Duplicate template type definitions
- services/bot/commands/list_games.py - Game list embed formatting
- services/bot/commands/my_games.py - Identical game list embed formatting
- services/bot/events/handlers.py - 2 instances of channel/message fetching

### External References

- #file:../research/20260114-duplicate-code-elimination-research.md - Comprehensive duplication analysis with code examples
- #file:../../.github/instructions/python.instructions.md - Python coding standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines
- #file:../../.github/instructions/reactjs.instructions.md - TypeScript/React standards

### Standards References

- DRY principle (Don't Repeat Yourself)
- Single Responsibility Principle
- Extract Method refactoring pattern
- TypeScript utility types (Partial, Omit)

## Implementation Checklist

### [ ] Phase 1: High-Impact Template Response Duplication

- [ ] Task 1.1: Create build_template_response helper function with unit tests
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 15-60)

- [ ] Task 1.2: Refactor GET /templates/{template_id} endpoint
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 62-73)

- [ ] Task 1.3: Refactor POST /templates endpoint
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 75-86)

- [ ] Task 1.4: Refactor PUT /templates/{template_id} endpoint
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 88-99)

- [ ] Task 1.5: Refactor POST /templates/{template_id}/set-default endpoint
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 101-112)

### [x] Phase 2: High-Impact Discord API Error Handling

- [x] Task 2.1: Create \_make_api_request base method with unit tests
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 114-175)

- [x] Task 2.2: Refactor exchange_code method
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 177-190)

- [x] Task 2.3: Refactor refresh_token method
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 192-205)

- [x] Task 2.4: Refactor fetch_guild method
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 207-220)

- [x] Task 2.5: Refactor fetch_user method
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 222-235)

- [x] Task 2.6: Refactor get_guild_member method
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 237-250)

### [x] Phase 3: Medium-Impact Game Embed Formatting

- [x] Task 3.1: Create build_game_list_embed function with unit tests
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 252-300)

- [x] Task 3.2: Refactor list_games command to use shared embed builder
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 302-315)

- [x] Task 3.3: Refactor my_games command to use shared embed builder
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 322-335)

- [x] Task 3.4: Add unit tests for build_game_list_embed
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 337-355)

### [x] Phase 4: Medium-Impact TypeScript Type Definitions

- [x] Task 4.1: Refactor Template interface to be single source of truth
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 357-380)

- [x] Task 4.2: Create TemplateUpdate utility type
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 382-395)

- [x] Task 4.3: Verify TypeScript compilation and type checking
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 397-408)

### [x] Phase 5: Medium-Impact Channel Message Fetching

- [x] Task 5.1: Create \_fetch_channel_and_message helper with unit tests
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 492-553)

- [x] Task 5.2: Refactor first event handler to use helper
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 555-569)

- [x] Task 5.3: Refactor second event handler to use helper
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 571-584)

### [x] Phase 6: Verification and Documentation

- [x] Task 6.1: Run jscpd to verify duplication reduction
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 502-515)

- [x] Task 6.2: Run full test suite to ensure no regressions
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 517-530)

- [x] Task 6.3: Update jscpd threshold configuration
  - Details: .copilot-tracking/details/20260114-duplicate-code-elimination-details.md (Lines 532-545)

## Dependencies

- Python 3.13 standard library
- TypeScript 5.x utility types
- Discord.py framework
- FastAPI framework
- jscpd duplicate code detector (already installed via npx)

## Success Criteria

- Code duplication reduced from 3.68% to under 2%
- All existing unit tests pass
- All integration tests pass
- No behavioral changes to API endpoints or bot commands
- Code coverage maintained or improved
- jscpd pre-commit hook passes with new threshold
- TypeScript compilation successful with no errors
