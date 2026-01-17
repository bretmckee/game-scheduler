---
applyTo: ".copilot-tracking/changes/20260116-default-complexity-thresholds-reduction-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Reduce Complexity Thresholds to Default Values

## Overview

Systematically refactor high-complexity functions to enable reducing cyclomatic complexity threshold from 17→10 and cognitive complexity threshold from 20→15 (tool default values).

## Objectives

- Reduce cyclomatic complexity violations from 10 functions to 0
- Reduce cognitive complexity violations from 24 functions to 0
- Lower pyproject.toml thresholds to tool defaults (C901=10, complexipy=15)
- Apply proven refactoring patterns from create_game() success
- Maintain 100% test coverage with unit tests for all extracted methods

## Research Summary

### Project Files

- services/api/routes/games.py - Multiple high-complexity endpoints requiring refactoring
- services/api/services/games.py - GameService with systemic complexity issues across 5 methods
- services/bot/events/handlers.py - EventHandlers with 6 complex event handling methods
- pyproject.toml - Current thresholds (C901=17, complexipy=20) to be reduced to defaults (10, 15)

### External References

- #file:../research/20260116-default-complexity-thresholds-reduction-research.md - Complete analysis of 34 function violations with metrics
- #file:../../.copilot-tracking/changes/20260107-create-game-complexity-reduction-changes.md - Proven refactoring approach reducing complexity by 75-88%

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding standards and patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Documentation standards

## Implementation Checklist

### [ ] Phase 1: High-Priority Dual Violations (8 functions)

Target functions violating both cyclomatic (>10) and cognitive (>15) thresholds.

- [x] Task 1.1: Refactor routes/games.py `update_game` (C:14/Cog:20)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 25-40)

- [x] Task 1.2: Refactor services/display_names.py `resolve_display_names_and_avatars` (C:12/Cog:19)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 42-57)

- [x] Task 1.3: Refactor services/games.py `_update_game_fields` (C:13/Cog:16)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 59-74)

- [x] Task 1.4: Refactor services/games.py `_update_prefilled_participants` (C:11/Cog:17)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 76-91)

- [x] Task 1.5: Refactor services/games.py `update_game` (C:13/Cog:17)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 93-108)

- [x] Task 1.6: Refactor services/participant_resolver.py `resolve_initial_participants` (C:12/Cog:20)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 110-125)

- [x] Task 1.7: Refactor events/handlers.py `_handle_player_removed` (C:12/Cog:18)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 127-142)

- [x] Task 1.8: Refactor formatters/game_message.py `create_game_embed` (C:14/Cog:17)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 144-159)

- [ ] Task 1.9: Update pyproject.toml thresholds (17→12, 20→17) **DEFERRED**
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 161-170)
  - Note: Cannot lower thresholds while violations remain. Deferred to end of Phase 4.

### [x] Phase 2: Remaining Cyclomatic Violations - COMPLETE

Target functions only violating cyclomatic threshold to reach C901=10.

- [x] Task 2.1: No additional cyclomatic violations found (Phase 1 resolved all)
  - Verified: All code complies with C901≤10

- [x] Task 2.2: Updated pyproject.toml cyclomatic threshold (17→10)
  - Successfully lowered C901 threshold to default value

### [ ] Phase 3: High Cognitive Complexity (8 functions, 20-27)

Target functions with cognitive complexity 20-27.

- [x] Task 3.1: Refactored services/games.py `_resolve_game_host` (Cog:21→≤10)
  - Extracted 3 helper methods with 9 comprehensive unit tests
  - Successfully reduced cognitive complexity below threshold

- [x] Task 3.2: Refactored events/handlers.py `_handle_game_reminder` (Cog:23→≤10)
  - Extracted 4 helper methods with 11 comprehensive unit tests
  - Successfully reduced cognitive complexity below threshold

- [ ] Task 3.3: Refactor events/handlers.py `_handle_game_cancelled` (Cog:24)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 245-258)

- [ ] Task 3.4: Refactor services/games.py `_resolve_template_fields` (Cog:23)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 260-273)

- [ ] Task 3.5: Refactor events/handlers.py `_handle_join_notifications` (Cog:21)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 275-288)

- [ ] Task 3.6: Refactor commands/list_games.py `list_games_command` (Cog:20)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 290-303)

- [ ] Task 3.7: Verify Phase 1 functions if not yet at Cog≤17
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 305-312)

- [ ] Task 3.8: Update pyproject.toml cognitive threshold (maintain at 17)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 314-321)

### [ ] Phase 4: Medium Cognitive Complexity (6+ functions, 16-19)

Target remaining cognitive complexity violations to reach default threshold of 15.

- [ ] Task 4.1: Refactor services/roles.py `check_user_roles` (Cog:19)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 325-338)

- [ ] Task 4.2: Refactor data_access/database_users.py `create_database_users` (Cog:19)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 340-353)

- [ ] Task 4.3: Refactor events/handlers.py `_refresh_game_message` (Cog:18)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 355-368)

- [ ] Task 4.4: Refactor services/guild_service.py `sync_user_guilds` (Cog:18)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 370-383)

- [ ] Task 4.5: Refactor remaining functions with Cog:16-17
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 385-398)

- [ ] Task 4.6: Update pyproject.toml cognitive threshold (17→15)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 400-407)

### [ ] Phase 5: Extreme Outliers - Optional (3 utility functions)

Target test utilities and scripts with extreme cognitive complexity (30-39).

- [ ] Task 5.1: Refactor retry_daemon.py `_process_dlq` (Cog:39)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 411-424)

- [ ] Task 5.2: Refactor tests/e2e/shared/discord.py `seed_messages` (Cog:37)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 426-439)

- [ ] Task 5.3: Refactor scripts/verify_button_states.py `verify_game_buttons` (Cog:30)
  - Details: .copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md (Lines 441-454)

## Dependencies

- Existing comprehensive test suite
- Ruff linter with C901 (McCabe) rule
- Complexipy cognitive complexity tool
- SQLAlchemy async patterns
- Discord.py async patterns
- Python 3.11+ type hints

## Success Criteria

- Zero cyclomatic complexity violations at C901=10 threshold
- Zero cognitive complexity violations at complexipy=15 threshold
- pyproject.toml updated with default thresholds (10, 15)
- All existing integration tests passing
- Unit tests added for all extracted helper methods
- No behavior changes in refactored functionality
- Code follows Extract Method, Single Responsibility, and Guard Clause patterns
