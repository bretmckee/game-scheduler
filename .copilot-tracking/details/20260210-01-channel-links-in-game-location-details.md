<!-- markdownlint-disable-file -->

# Task Details: Discord Channel Links in Game Location Field

## Research Reference

**Source Research**: #file:../research/20260210-01-channel-links-in-game-location-research.md

## Phase 1: Backend Channel Resolver Service

### Task 1.1: Create ChannelResolver service stub

Create new ChannelResolver service following ParticipantResolver pattern with stub implementation that raises NotImplementedError.

- **Files**:
  - services/api/services/channel_resolver.py (new file)
- **Success**:
  - ChannelResolver class created with **init** accepting DiscordAPIClient
  - resolve_channel_mentions method defined returning tuple[str, list[dict]]
  - Method raises NotImplementedError
  - Copyright header added
  - Module docstring explains purpose
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 338-450) - Complete implementation example
  - services/api/services/participant_resolver.py (Lines 59-73) - ParticipantResolver pattern
- **Dependencies**:
  - None

### Task 1.2: Write failing tests for ChannelResolver

Create comprehensive unit tests for ChannelResolver that expect NotImplementedError initially.

- **Files**:
  - tests/services/api/services/test_channel_resolver.py (new file)
- **Success**:
  - Test single channel match scenario
  - Test multiple channel match (disambiguation)
  - Test no channel match (not found with suggestions)
  - Test channel name with special characters
  - Test mixed content (text + channel mentions)
  - Test empty location text
  - All tests expect NotImplementedError and pass
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 338-430) - Resolution logic
  - tests/services/api/services/test_participant_resolver.py - Test pattern reference
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Implement channel mention parsing and resolution

Implement resolve_channel_mentions method with channel parsing, Discord API lookup, and error handling.

- **Files**:
  - services/api/services/channel_resolver.py
- **Success**:
  - Regex pattern `r'#([\w-]+)'` finds channel mentions
  - Calls discord_client.get_guild_channels() to fetch channels
  - Filters to text channels only (type == 0)
  - Single match: Replaces `#channel-name` with `<#channel_id>`
  - Multiple matches: Returns disambiguation error with suggestions
  - No match: Returns not found error with similar channel suggestions (fuzzy match)
  - Returns tuple of (resolved_text, validation_errors)
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 353-430) - Complete implementation
  - services/api/services/participant_resolver.py (Lines 147-200) - Validation error format
- **Dependencies**:
  - Task 1.2 completion

### Task 1.4: Update tests to verify actual behavior

Update all tests to verify actual resolution behavior instead of expecting NotImplementedError.

- **Files**:
  - tests/services/api/services/test_channel_resolver.py
- **Success**:
  - Tests verify correct `<#channel_id>` format in resolved text
  - Tests verify validation error structure matches ParticipantResolver format
  - Tests verify disambiguation includes all matching channels
  - Tests verify suggestions include similar channels (case-insensitive substring match)
  - All tests pass with actual implementation
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 400-430) - Error format
- **Dependencies**:
  - Task 1.3 completion

### Task 1.5: Refactor and add edge case tests

Refactor implementation for clarity and add comprehensive edge case tests.

- **Files**:
  - services/api/services/channel_resolver.py
  - tests/services/api/services/test_channel_resolver.py
- **Success**:
  - Code follows Python conventions (type hints, docstrings)
  - Extract helper methods for clarity if needed
  - Test multiple `#channel` mentions in one location
  - Test channel name at start, middle, and end of text
  - Test adjacent channel mentions (`#general #announcements`)
  - Test invalid Discord API response handling
  - Test empty guild channel list
  - All tests pass, code coverage >90%
- **Research References**:
  - #file:../../.github/instructions/python.instructions.md - Python standards
- **Dependencies**:
  - Task 1.4 completion

## Phase 2: Game Service Integration

### Task 2.1: Add channel resolution to GameService.create_game

Integrate ChannelResolver into game creation flow with proper error handling and dependency injection.

- **Files**:
  - services/api/services/games.py
  - services/api/services/channel_resolver.py (add to **init**.py exports if needed)
- **Success**:
  - ChannelResolver instantiated with discord_client in create_game
  - Channel resolution called when game_data.where is not None
  - Resolved location replaces game_data.where
  - ValidationError raised if channel_errors returned
  - Resolution happens before participant resolution (to fail fast on location issues)
  - Transaction semantics preserved (no DB changes if validation fails)
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 432-450) - Integration code
  - services/api/services/games.py (Lines 138-155) - Host resolution pattern
  - #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Transaction patterns
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Write integration tests for game creation with channel mentions

Create integration tests verifying game creation with channel mentions end-to-end.

- **Files**:
  - tests/services/api/services/test_games.py
- **Success**:
  - Test game creation with valid `#general` mention
  - Test game creation with invalid channel name returns ValidationError
  - Test game creation with multiple matching channels returns disambiguation
  - Test game creation with mixed text and channel mention
  - Test game creation with plain text location (no mentions) still works
  - Verify resolved location stored in database has `<#id>` format
  - Verify GameSession.where field contains resolved mention
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 338-450) - Expected behavior
  - tests/services/api/services/test_games.py - Existing test patterns
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Add error handling for validation failures

Ensure proper error responses for channel validation failures at API layer.

- **Files**:
  - services/api/routes/games.py (if needed - validation errors already handled)
  - tests/services/api/routes/test_games.py (add tests if needed)
- **Success**:
  - ValidationError from ChannelResolver propagates correctly to API response
  - HTTP 400 returned with structured error body
  - Error body includes `invalid_mentions` with channel validation errors
  - Error structure matches participant validation error format
  - Frontend can parse and display errors
- **Research References**:
  - services/api/services/participant_resolver.py (Lines 41-56) - ValidationError class
  - tests/services/api/routes/test_guilds.py (Lines 350+) - Validation error response tests
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Frontend Error Display

### Task 3.1: Update GameForm to display channel validation errors

Extend GameForm to display channel validation errors similar to participant validation errors.

- **Files**:
  - frontend/src/components/GameForm.tsx
- **Success**:
  - Location field displays validation errors for invalid channel mentions
  - Error message shows "Channel not found" or "Multiple channels found"
  - Suggestions displayed as clickable options (if using existing ValidationError component)
  - Error clears when user corrects input
  - Styling matches existing validation error display
- **Research References**:
  - frontend/src/pages/CreateGame.tsx (Lines 41-60) - ValidationError interface
  - frontend/src/components/GameForm.tsx - Existing error handling patterns
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Add helper text indicating channel mention support

Update location field helper text to inform users about channel mention feature.

- **Files**:
  - frontend/src/components/GameForm.tsx
- **Success**:
  - Helper text updated to: "Location of the game. Type #channel-name to link to a Discord channel"
  - Helper text visible even when no error
  - Text provides clear usage guidance
  - Maintains character limit warning if present
- **Research References**:
  - frontend/src/components/GameForm.tsx (Lines 600-625) - Current location field
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: End-to-End Testing

### Task 4.1: Add E2E test for channel mention in Discord embed

Create E2E test verifying channel mention displays as clickable link in Discord.

- **Files**:
  - tests/e2e/test_channel_mentions.py (new file)
- **Success**:
  - Test creates game via API with location containing `#channel-name`
  - Test fetches Discord message via bot
  - Test verifies Where field contains `<#channel_id>` format
  - Test verifies channel ID matches actual guild channel
  - Discord renders as clickable link (verified by format)
  - Test cleans up game and message
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 26-35) - Discord mention format
  - tests/e2e/helpers/discord.py - Discord test helper patterns
  - tests/e2e/test_00_environment.py (Lines 102-120) - Channel access verification
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Verify backward compatibility with plain text locations

Add tests confirming plain text locations work unchanged.

- **Files**:
  - tests/e2e/test_channel_mentions.py
  - tests/services/api/services/test_games.py
- **Success**:
  - Test creates game with location "Local Game Store, 123 Main St"
  - Test verifies location stored and displayed unchanged
  - Test verifies no validation errors for plain text
  - Test creates game with location containing "#" but not channel format
  - Existing E2E tests continue to pass
- **Research References**:
  - #file:../research/20260210-01-channel-links-in-game-location-research.md (Lines 260-270) - Storage strategy
- **Dependencies**:
  - Task 4.1 completion

## Dependencies

- Discord API client with get_guild_channels method
- ParticipantResolver ValidationError pattern
- FastAPI request/response cycle
- Material-UI TextField component
- discord.py for E2E tests

## Success Criteria

- ChannelResolver service implemented following TDD
- Game creation validates channel mentions before database commit
- ValidationError returned for invalid or ambiguous channels
- Discord embeds display `<#channel_id>` as clickable links
- Frontend displays clear error messages with suggestions
- Plain text locations continue to work without modification
- All unit tests pass (>90% coverage)
- All integration tests pass
- All E2E tests pass
- No regressions in existing functionality
