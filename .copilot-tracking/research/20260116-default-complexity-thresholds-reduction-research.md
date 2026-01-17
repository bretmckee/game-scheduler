<!-- markdownlint-disable-file -->
# Task Research Notes: Reducing Complexity Thresholds to Default Values

## Research Executed

### Current Configuration Analysis
- pyproject.toml (lines 70-85)
  - Current cyclomatic complexity threshold: 17 (McCabe C901)
  - Current cognitive complexity threshold: 20 (complexipy)
- Default values from tool documentation:
  - Ruff C901 default: 10 (cyclomatic complexity)
  - Complexipy default: 15 (cognitive complexity)

### Cyclomatic Complexity Violations (C901)
Ran ruff check with default threshold of 10 to identify all violations.

**Total Violations Found**: 10 functions

1. services/api/routes/games.py:299 - `update_game` (14 > 10)
2. services/api/services/display_names.py:145 - `resolve_display_names_and_avatars` (12 > 10)
3. services/api/services/games.py:98 - `_resolve_game_host` (11 > 10)
4. services/api/services/games.py:679 - `_update_game_fields` (13 > 10)
5. services/api/services/games.py:759 - `_update_prefilled_participants` (11 > 10)
6. services/api/services/games.py:1001 - `update_game` (13 > 10)
7. services/api/services/participant_resolver.py:68 - `resolve_initial_participants` (12 > 10)
8. services/bot/events/handlers.py:355 - `_handle_game_reminder` (11 > 10)
9. services/bot/events/handlers.py:640 - `_handle_player_removed` (12 > 10)
10. services/bot/formatters/game_message.py:50 - `create_game_embed` (14 > 10)

### Cognitive Complexity Violations (complexipy)
Ran complexipy via pre-commit with default threshold of 15 to identify all violations.

**Functions with Cognitive Complexity > 15** (ordered by complexity):

| File | Function | Cognitive Complexity |
|------|----------|---------------------|
| services/retry/retry_daemon.py | RetryDaemon::_process_dlq | 39 |
| tests/e2e/shared/discord.py | DiscordTestHelper::seed_messages | 37 |
| scripts/verify_button_states.py | verify_game_buttons | 30 |
| services/api/services/display_names.py | DisplayNameResolve::resolve_display_names | 27 |
| services/bot/events/handlers.py | EventHandlers::_handle_game_updated | 26 |
| services/bot/events/handlers.py | EventHandlers::_handle_game_cancelled | 24 |
| services/api/services/games.py | GameService::_resolve_template_fields | 23 |
| services/bot/events/handlers.py | EventHandlers::_handle_join_notifications | 21 |
| services/api/services/participant_resolver.py | ParticipantResolver::resolve_initial_participants | 20 |
| services/api/routes/games.py | update_game | 20 |
| services/bot/commands/list_games.py | list_games_command | 20 |
| shared/data_access/database_users.py | create_database_users | 19 |
| services/api/services/display_names.py | DisplayNameResolver::resolve_display_names_and_avatars | 19 |
| services/api/services/roles.py | RoleVerificationService::check_user_roles | 19 |
| services/bot/events/handlers.py | EventHandlers::_refresh_game_message | 18 |
| services/bot/events/handlers.py | EventHandlers::_handle_player_removed | 18 |
| services/api/services/guild_service.py | sync_user_guilds | 18 |
| services/api/services/games.py | GameService::_update_prefilled_participants | 17 |
| services/api/services/games.py | GameService::update_game | 17 |
| services/bot/formatters/game_message.py | GameMessageFormatter::create_game_embed | 17 |
| services/api/services/games.py | GameService::_update_game_fields | 16 |
| services/api/routes/games.py | _build_game_response | 16 |
| tests/e2e/test_user_join.py | test_user_join_updates_message | 16 |

**Total functions with cognitive complexity 16-39**: 24 functions
**Total functions with cognitive complexity > 15**: ~24 functions needing refactoring

## Key Discoveries

### Priority Analysis

**Highest Priority** (both cyclomatic > 10 AND cognitive > 15):
1. services/api/routes/games.py:299 - `update_game` (cyclomatic: 14, cognitive: 20)
2. services/api/services/display_names.py:145 - `resolve_display_names_and_avatars` (cyclomatic: 12, cognitive: 19)
3. services/api/services/games.py:679 - `_update_game_fields` (cyclomatic: 13, cognitive: 16)
4. services/api/services/games.py:759 - `_update_prefilled_participants` (cyclomatic: 11, cognitive: 17)
5. services/api/services/games.py:1001 - `update_game` (cyclomatic: 13, cognitive: 17)
6. services/api/services/participant_resolver.py:68 - `resolve_initial_participants` (cyclomatic: 12, cognitive: 20)
7. services/bot/events/handlers.py:640 - `_handle_player_removed` (cyclomatic: 12, cognitive: 18)
8. services/bot/formatters/game_message.py:50 - `create_game_embed` (cyclomatic: 14, cognitive: 17)

**Cyclomatic Only** (cyclomatic > 10 but cognitive ≤ 15):
9. services/api/services/games.py:98 - `_resolve_game_host` (cyclomatic: 11, cognitive: ~10)
10. services/bot/events/handlers.py:355 - `_handle_game_reminder` (cyclomatic: 11, cognitive: ~11)

**Cognitive Only** (cognitive > 15 but cyclomatic ≤ 10):
11. services/retry/retry_daemon.py - `RetryDaemon::_process_dlq` (cognitive: 39)
12. tests/e2e/shared/discord.py - `DiscordTestHelper::seed_messages` (cognitive: 37)
13. scripts/verify_button_states.py - `verify_game_buttons` (cognitive: 30)
14. services/api/services/display_names.py - `DisplayNameResolve::resolve_display_names` (cognitive: 27)
15. services/bot/events/handlers.py - `EventHandlers::_handle_game_updated` (cognitive: 26)
16. services/bot/events/handlers.py - `EventHandlers::_handle_game_cancelled` (cognitive: 24)
17. services/api/services/games.py - `GameService::_resolve_template_fields` (cognitive: 23)
18. services/bot/events/handlers.py - `EventHandlers::_handle_join_notifications` (cognitive: 21)
19. services/bot/commands/list_games.py - `list_games_command` (cognitive: 20)
20. shared/data_access/database_users.py - `create_database_users` (cognitive: 19)
21. services/api/services/roles.py - `RoleVerificationService::check_user_roles` (cognitive: 19)
22. services/bot/events/handlers.py - `EventHandlers::_refresh_game_message` (cognitive: 18)
23. services/api/services/guild_service.py - `sync_user_guilds` (cognitive: 18)

### Patterns Identified

**GameService Cluster** (services/api/services/games.py):
- Multiple methods in same class need refactoring
- Suggests systemic complexity in game update logic
- Methods: `_resolve_game_host`, `_update_game_fields`, `_update_prefilled_participants`, `update_game`, `_resolve_template_fields`

**EventHandlers Cluster** (services/bot/events/handlers.py):
- Multiple event handling methods with high cognitive complexity
- Methods: `_handle_game_reminder`, `_handle_player_removed`, `_handle_game_updated`, `_handle_game_cancelled`, `_handle_join_notifications`, `_refresh_game_message`

**Display Name Resolution** (services/api/services/display_names.py):
- Two related methods with high complexity
- Methods: `resolve_display_names_and_avatars`, `resolve_display_names`

**Participant Resolution** (services/api/services/participant_resolver.py):
- `resolve_initial_participants` - high on both metrics

### Successful Pattern from Previous Work

The create_game() refactoring (completed 2026-01-15) provides proven approach:
- Original: 344 lines, cyclomatic 24, cognitive 48
- Final: 120 lines, cyclomatic 6, cognitive 6
- **Reduction: 65% fewer lines, 75% less cyclomatic, 88% less cognitive**

**Techniques Used:**
1. Extract Method pattern for distinct responsibilities
2. Helper methods with clear single responsibility
3. Parameter objects for related data (e.g., GameMediaAttachments)
4. Progressive extraction in phases
5. Comprehensive unit tests for each extracted method
6. Maintain full integration test coverage

## Recommended Approach

### Strategy: Phased Complexity Reduction

Reduce thresholds progressively to default values through targeted refactoring.

### Phase 1: High-Priority Dual Violations (Complexity 14-20)

Target functions violating both thresholds for maximum impact.

**Targets** (8 functions):
1. routes/games.py `update_game` (C:14/Cog:20)
2. services/display_names.py `resolve_display_names_and_avatars` (C:12/Cog:19)
3. services/games.py `_update_game_fields` (C:13/Cog:16)
4. services/games.py `_update_prefilled_participants` (C:11/Cog:17)
5. services/games.py `update_game` (C:13/Cog:17)
6. services/participant_resolver.py `resolve_initial_participants` (C:12/Cog:20)
7. events/handlers.py `_handle_player_removed` (C:12/Cog:18)
8. formatters/game_message.py `create_game_embed` (C:14/Cog:17)

**Expected Impact**: Reduce both metrics significantly, lowering thresholds from 17→12 and 20→17

### Phase 2: Remaining Cyclomatic Violations (Complexity 11)

Address functions only violating cyclomatic threshold.

**Targets** (2 functions):
9. services/games.py `_resolve_game_host` (C:11/Cog:~10)
10. events/handlers.py `_handle_game_reminder` (C:11/Cog:~11)

**Expected Impact**: Enable reduction to cyclomatic threshold of 10 (default)

### Phase 3: High Cognitive Complexity (20-27)

Target functions with cognitive complexity 20-27.

**Targets** (8 functions):
11. services/display_names.py `resolve_display_names` (Cog:27)
12. events/handlers.py `_handle_game_updated` (Cog:26)
13. events/handlers.py `_handle_game_cancelled` (Cog:24)
14. services/games.py `_resolve_template_fields` (Cog:23)
15. events/handlers.py `_handle_join_notifications` (Cog:21)
16. routes/games.py `update_game` (Cog:20) - if not completed in Phase 1
17. participant_resolver.py `resolve_initial_participants` (Cog:20) - if not completed in Phase 1
18. commands/list_games.py `list_games_command` (Cog:20)

**Expected Impact**: Enable reduction to cognitive threshold of 17

### Phase 4: Medium Cognitive Complexity (16-19)

Address remaining functions with cognitive complexity 16-19.

**Targets** (remaining ~6 functions):
- services/roles.py `check_user_roles` (Cog:19)
- data_access/database_users.py `create_database_users` (Cog:19)
- events/handlers.py `_refresh_game_message` (Cog:18)
- services/guild_service.py `sync_user_guilds` (Cog:18)
- And others in 16-17 range

**Expected Impact**: Enable reduction to cognitive threshold of 15 (default)

### Phase 5: Extreme Outliers (Optional)

Address test utilities and scripts with extreme cognitive complexity.

**Targets** (3 functions):
- retry_daemon.py `_process_dlq` (Cog:39)
- tests/e2e/shared/discord.py `seed_messages` (Cog:37)
- scripts/verify_button_states.py `verify_game_buttons` (Cog:30)

**Note**: These are utilities/test code, lower priority than production code.

## Implementation Guidance

### Refactoring Techniques

Based on successful create_game() refactoring:

1. **Extract Method Pattern**
   - Identify distinct responsibilities within method
   - Create focused helper methods
   - Single responsibility per method

2. **Parameter Objects**
   - Group related parameters into dataclasses
   - Example: MediaAttachments, ValidationContext
   - Reduces parameter count

3. **Guard Clauses**
   - Early returns to reduce nesting
   - Fail fast validation

4. **Strategy Pattern** (for high branching)
   - Replace complex conditionals with polymorphism
   - Useful for multi-path logic

5. **Builder Pattern** (for complex construction)
   - Staged object construction
   - Clear separation of configuration vs. creation

### Testing Strategy

1. **Preserve Integration Tests**
   - Keep existing tests unchanged
   - Verify no behavior changes

2. **Add Unit Tests for Extracted Methods**
   - Test each helper method independently
   - Cover edge cases and branches

3. **Progressive Validation**
   - Run tests after each extraction
   - Commit frequently

### Success Criteria

**Phase 1 Complete**:
- All 8 dual-violation functions reduced to C≤12, Cog≤17
- Update thresholds: cyclomatic 17→12, cognitive 20→17
- All tests passing

**Phase 2 Complete**:
- All cyclomatic violations resolved
- Update cyclomatic threshold: 12→10 (default)
- All tests passing

**Phase 3 Complete**:
- All cognitive 20-27 functions reduced to ≤17
- Update cognitive threshold: 17→17 (maintain)
- All tests passing

**Phase 4 Complete**:
- All cognitive violations resolved
- Update cognitive threshold: 17→15 (default)
- All tests passing
- **GOAL ACHIEVED**: Both thresholds at default values

**Phase 5 Complete** (optional):
- Test utilities and scripts refactored
- Further threshold reduction if desired

### Metrics Tracking

Track progress after each phase:
- Number of violations remaining
- Current max complexity in codebase
- Threshold values
- Test coverage maintained

### Dependencies

- Existing test suite coverage
- Python type hints for clarity
- SQLAlchemy async patterns
- Discord.py async patterns

### Alternative Approaches Considered

**Approach 1: Incremental Threshold Reduction Without Refactoring**
- Lower thresholds gradually, fixing only new violations
- **Rejected**: Doesn't address technical debt, allows degradation

**Approach 2: Big Bang Refactoring**
- Refactor all violations simultaneously
- **Rejected**: High risk, harder to validate, merge conflicts

**Approach 3: Focus Only on Cyclomatic or Cognitive**
- Address one metric at a time
- **Rejected**: Missing synergies, dual violations need both metrics

**Approach 4: Ignore Test/Script Violations**
- Only refactor production code
- **Considered**: Valid for Phase 5 optional work

## Next Steps

1. Create implementation plan for Phase 1 (8 dual-violation functions)
2. Prioritize by impact and risk
3. Begin with update_game() as it appeared twice in violations
4. Follow create_game() refactoring pattern
5. Document learnings for subsequent phases
