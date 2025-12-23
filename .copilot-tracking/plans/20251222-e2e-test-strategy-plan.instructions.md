---
applyTo: ".copilot-tracking/changes/20251222-e2e-test-strategy-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: E2E Test Strategy - Discord Message Validation

## Overview

Implement true end-to-end testing that validates Discord bot behavior and message content, addressing the gap in current database-focused tests. **Prerequisite refactoring (Discord client token unification) is now COMPLETE and this work can proceed.**

## Objectives

- Verify game announcements appear in Discord channels with correct content
- Validate Discord message embeds, fields, and user mentions
- Test DM reminder delivery to participants
- Establish reusable patterns for Discord message validation
- Create helper utilities for Discord API interactions

## Status

**REFACTORING PREREQUISITE: ✅ COMPLETE**
- Discord client token unification refactored and committed (commit: 0d70d93)
- Automatic token type detection now available in `DiscordAPIClient._get_auth_header()`
- Unified `get_guilds()` method works with both bot and OAuth tokens
- All 791 unit tests passing, code quality verified
- **E2E work can now proceed without blocking issues**

## Research Summary

### Project Files

- tests/e2e/test_game_notification_api_flow.py - Database-focused tests without Discord validation
- tests/e2e/test_guild_template_api.py - Integration tests with mocked Discord responses
- services/bot/events/handlers.py - Discord event handlers and message posting logic
- services/bot/formatters/game_message.py - Game announcement embed formatting
- TESTING_E2E.md - E2E test environment documentation
- shared/discord/client.py - Unified Discord client with automatic token type detection (**REFACTORED**)

### External References

- #file:../research/20251222-e2e-test-strategy-research.md - Comprehensive E2E strategy analysis (updated with refactor completion)
- #file:../research/20251222-discord-client-token-unification-research.md - Token unification refactor details
- #fetch:https://discord.com/developers/docs/resources/message - Discord Message API documentation
- discord.py library - Message reading capabilities (fetch_message, embeds, content)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - Testing standards

## Implementation Checklist

### [x] Phase 1: E2E Infrastructure Setup

- [x] Task 1.1: Create DiscordTestHelper module
  - Create tests/e2e/helpers/discord.py with DiscordTestHelper class
  - Implement connect/disconnect lifecycle for discord.py bot client
  - Implement get_channel_message(channel_id, message_id) method
  - Implement get_user_recent_dms(user_id, limit=10) method
  - Implement verify_game_announcement(message, game_title, host_id) validation method
  - Add proper error handling and logging
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 11-25)

- [x] Task 1.2: Set up E2E fixtures in conftest.py
  - Create environment variable fixtures (discord_token, guild_id, channel_id, test_user_id)
  - Create database fixtures (db_engine, db_session) with proper connection pooling
  - Create http_client fixture (httpx.AsyncClient with base URL)
  - Create discord_helper fixture with automatic connect/disconnect
  - Set appropriate fixture scopes (session for db, function for http_client)
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 26-42)

- [x] Task 1.3: Verify E2E test environment
  - Validate env/env.e2e has required Discord credentials
  - Verify compose.e2e.yaml includes all required services
  - Test that fixtures connect successfully without errors
  - Document any additional setup steps needed
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 43-61)

### [x] Phase 2: Core Authentication

- [x] Task 2.1: Extract bot Discord ID from token
  - Extract Discord user ID from `DISCORD_ADMIN_BOT_TOKEN` by base64 decoding first segment
  - Implement utility function to parse bot token format with proper padding
  - Moved extraction logic to shared/utils/discord_tokens.py for reuse
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 62-74)

- [x] Task 2.2: Create authenticated_admin_client fixture
  - Create fixture in tests/e2e/conftest.py with function scope
  - Manually create Redis session using bot Discord ID and admin bot token
  - Set session_token cookie in HTTP client
  - Yield authenticated client for test use
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 75-87)

- [x] Task 2.3: Add synced_guild fixture
  - Create function-scoped fixture that verifies pre-seeded guild exists
  - Guild/channel already created by init service, no sync needed
  - Returns guild configuration info for use in game creation tests
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 88-102)
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 88-102)

### [x] Phase 3: Complete First Test - Game Announcement

- [x] Task 3.1: Update test to use authenticated client
  - Modify test_game_announcement.py to use authenticated_admin_client fixture
  - Replace plain http_client with authenticated_admin_client
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 103-115)

- [x] Task 3.2: Include template_id in game creation request
  - Add template_id field to game creation request body
  - Use test_template_id from synced_guild fixture
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 116-128)

- [x] Task 3.3: Verify Discord announcement message posted
  - Create game via API
  - Fetch message_id from database (game_sessions.message_id)
  - Use DiscordTestHelper to retrieve message from Discord channel
  - Verify message exists
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 129-142)

- [x] Task 3.4: Complete embed content validation
  - Validate embed title matches game title
  - Validate embed contains host mention
  - Validate embed contains player count (0/max_players)
  - Validate embed structure and fields
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 143-157)

### [ ] Phase 4: Remaining Test Scenarios

- [ ] Task 4.1: Game update → message refresh test
  - Create game and retrieve message_id
  - Update game (title/description) via API
  - Verify message_id unchanged
  - Fetch message from Discord and validate updated content
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 158-170)

- [ ] Task 4.2: User joins → participant list update test
  - Create game, retrieve message_id
  - Simulate join via API (add participant)
  - Fetch message and verify participant count updated
  - Validate player count incremented
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 171-183)

- [ ] Task 4.3: Game reminder → DM verification test
  - Create game with reminder_minutes=[5]
  - Wait for notification daemon to process
  - Use DiscordTestHelper.get_user_recent_dms() to fetch DMs
  - Verify test user receives DM with game details
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 184-198)

- [ ] Task 4.4: Game deletion → message removed test
  - Create game, retrieve message_id
  - Delete game via API
  - Verify Discord message deleted from channel
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 199-213)

### [ ] Phase 5: Documentation and CI/CD Integration

- [ ] Task 5.1: Update TESTING_E2E.md
  - Document new E2E test execution pattern
  - Include DiscordTestHelper usage examples
  - Include authentication fixture usage examples
  - Document guild sync requirement
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 214-226)

- [ ] Task 5.2: Document Discord test environment requirements
  - Admin bot token requirement
  - Test guild and channel setup
  - Test user creation steps
  - DiscordTestHelper configuration
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 227-239)

- [ ] Task 5.3: Configure CI/CD for E2E test execution
  - Document E2E test execution (likely manual-only)
  - Add conditional execution logic based on environment
  - Details: .copilot-tracking/details/20251222-e2e-test-strategy-details.md (Lines 240-254)

## Dependencies

- pytest-asyncio for async test support
- discord.py library (already installed)
- Test Discord guild, channel, bot token, and test user
- Running full stack via compose.e2e.yaml profile
- RabbitMQ for event messaging
- ✅ Discord client token unification (COMPLETE) - enables bot token use with all Discord API endpoints
- ✅ Automatic token type detection - simplifies authentication pattern for tests
- PostgreSQL for game session storage

## Success Criteria

- DiscordTestHelper module provides clean API for Discord operations
- test_game_creation_posts_announcement passes with message validation
- All priority E2E scenarios have passing tests
- Documentation updated with test execution instructions
- Pattern established for future E2E test development
- Clear path forward for implementing advanced test scenarios
