<!-- markdownlint-disable-file -->

# Task Details: E2E Test Strategy - Discord Message Validation

## Research Reference

**Source Research**: #file:../research/20251222-e2e-test-strategy-research.md

## Phase 1: E2E Infrastructure Setup

### Task 1.1: Create DiscordTestHelper module

Implement a helper module to abstract Discord operations used by tests.

- **Files**:
  - tests/e2e/helpers/discord.py - Helper with connect/disconnect and message/DM utilities
- **Success**:
  - `DiscordTestHelper.connect()` logs in with bot token and can fetch channels/messages
  - `get_channel_message()` returns a `Message` object; `verify_game_announcement()` validates embed
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 340-392) - Helper module pattern and example
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 400-420) - Additional helper implementation details
- **Dependencies**:
  - discord.py installed and configured for bot token usage

### Task 1.2: Set up E2E fixtures in conftest.py

Create pytest fixtures for environment variables, database sessions, HTTP client, and Discord helper lifecycle.

- **Files**:
  - tests/e2e/conftest.py - Centralized fixtures
- **Success**:
  - Env fixtures provide `discord_token`, `discord_guild_id`, `discord_channel_id`, `discord_user_id`
  - `db_engine`/`db_session` fixtures pool connections correctly
  - `http_client` fixture targets API base URL and can call `/health`
  - `discord_helper` fixture auto-connects and disconnects the helper
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 560-580) - Fixture inventory and status
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 571-576) - Fixture scopes and patterns
- **Dependencies**:
  - Docker Compose e2e profile running services

### Task 1.3: Verify E2E test environment

Validate credentials, connectivity, and seeded data prior to scenario tests.

- **Files**:
  - env/env.e2e - Environment variables
  - compose.e2e.yaml - Required services and env passthrough
  - tests/e2e/test_00_environment.py - Basic environment sanity tests
- **Success**:
  - Bot token can login and reach guild/channel; `/health` responds
  - Seeded data exists (guild, channel, test user)
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 580-620) - Environment validation tests
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1-45) - Project files and compose profile overview
- **Dependencies**:
  - Init service seeding completed; Docker network ready

## Phase 2: Core Authentication

### Task 2.1: Extract bot Discord ID from token

Provide a utility to parse the bot token and derive the bot user ID by base64 decoding the first segment.

- **Files**:
  - tests/e2e/helpers/discord.py or a small util in tests/e2e/utils/tokens.py
- **Success**:
  - Function returns correct bot user ID for provided `DISCORD_TOKEN`
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1088-1105) - Immediate steps: ID extraction
- **Dependencies**:
  - Access to `DISCORD_TOKEN` from env

### Task 2.2: Create authenticated_admin_client fixture

Authenticate API client by storing a session using the bot token as the access token and setting the `session_token` cookie.

- **Files**:
  - tests/e2e/conftest.py - `authenticated_admin_client` fixture
- **Success**:
  - Fixture yields an HTTP client authorized for API calls; session established via `tokens.store_user_tokens()`
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1106-1125) - Session creation with bot token and cookie
- **Dependencies**:
  - Token unification implemented in `DiscordAPIClient` (already complete)

### Task 2.3: Add synced_guild fixture

Run `/api/v1/guilds/sync` using admin bot auth to ensure configs/templates exist for tests.

- **Files**:
  - tests/e2e/conftest.py - `synced_guild` fixture
- **Success**:
  - Returns IDs for guild/channel configurations and a default template
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1126-1145) - Guild sync fixture requirements
- **Dependencies**:
  - Authenticated client fixture

## Phase 3: Complete First Test - Game Announcement

### Task 3.1: Update test to use authenticated client

Switch the test to use `authenticated_admin_client` and rely on `synced_guild` outputs.

- **Files**:
  - tests/e2e/test_game_announcement.py - Main test scenario
- **Success**:
  - Test executes without auth errors and reaches game creation endpoint
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1146-1160) - First test steps and validation path
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Include template_id in game creation request

Use the default template ID from `synced_guild` to create a game.

- **Files**:
  - tests/e2e/test_game_announcement.py - Request body adjustments
- **Success**:
  - API responds 201; session record has non-null `message_id`
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1146-1160) - Template requirement for end-to-end
- **Dependencies**:
  - Synced guild fixture

### Task 3.3: Verify Discord announcement message posted

Fetch the message from the Discord channel and confirm existence.

- **Files**:
  - tests/e2e/helpers/discord.py - `get_channel_message()`
- **Success**:
  - Retrieved message matches `game_sessions.message_id`
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 340-380) - Helper function example
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1-25) - Message API reference link
- **Dependencies**:
  - Game created; DB has message_id

### Task 3.4: Complete embed content validation

Validate core embed structure: title, host mention, participant count, key fields.

- **Files**:
  - tests/e2e/helpers/discord.py - `verify_game_announcement()`
- **Success**:
  - Assertions pass for embed title, host ID mention, and count fields
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 380-392) - Embed verification pattern
- **Dependencies**:
  - Retrieved message

## Phase 4: Remaining Test Scenarios

### Task 4.1: Game update → message refresh test

Update game data and confirm the Discord message content changes while keeping the same `message_id`.

- **Files**:
  - tests/e2e/test_game_update.py
- **Success**:
  - Discord message reflects updated title/description
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1161-1173) - Scenario outlines
- **Dependencies**:
  - Initial game and message created

### Task 4.2: User joins → participant list update test

Simulate join via API and verify participant count increments in the announcement.

- **Files**:
  - tests/e2e/test_user_join.py
- **Success**:
  - Message shows increased participant count; test passes
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1161-1170) - Scenario outlines
- **Dependencies**:
  - Game announcement exists

### Task 4.3: Game reminder → DM verification test

Trigger reminder and confirm DM received by the test user.

- **Files**:
  - tests/e2e/helpers/discord.py - `get_user_dms()`
  - tests/e2e/test_game_reminder.py
- **Success**:
  - DM appears with correct content; within expected time window
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 340-380) - DM helper example
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1161-1170) - Scenario outlines
- **Dependencies**:
  - Notification daemon running; reminder scheduled

### Task 4.4: Game deletion → message removed test

Delete the game and verify the corresponding Discord message is removed.

- **Files**:
  - tests/e2e/test_game_deletion.py
- **Success**:
  - Message no longer retrievable; API returns 404 or helper detects absence
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 1166-1173) - Scenario outlines
- **Dependencies**:
  - Prior creation of game and message

## Phase 5: Documentation and CI/CD

### Task 5.1: Update TESTING_E2E.md

Document helper usage, fixture setup, and execution steps.

- **Files**:
  - TESTING_E2E.md
- **Success**:
  - Clear run instructions; environment requirements; troubleshooting section
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 20-45) - Project docs references
- **Dependencies**:
  - Helper and fixtures implemented

### Task 5.2: Document Discord test environment requirements

Summarize bot token, guild/channel setup, and test user provisioning.

- **Files**:
  - TESTING_E2E.md
- **Success**:
  - Environment checklist complete and accurate
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 560-600) - Env validation and compose setup
- **Dependencies**:
  - Verified environment

### Task 5.3: Configure CI/CD for E2E test execution

Add conditional execution or manual documentation for running E2E in CI.

- **Files**:
  - .github/workflows/e2e.yml (if applicable)
  - scripts/run-e2e-tests.sh
- **Success**:
  - CI can optionally run E2E or provide manual steps
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 26-45) - Compose and scripts overview
- **Dependencies**:
  - Stable test environment and scripts

## Dependencies

- discord.py and pytest-asyncio
- Docker Compose e2e profile
- Seeded test data via init service

## Success Criteria

- Helper and fixtures implemented and validated
- First end-to-end test passes with Discord message validation
- Remaining scenarios implemented with passing tests
Documentation updated; CI/CD notes added
  - Documents expected test execution time and timing considerations
  - Includes troubleshooting section for common issues
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 552-573) - Test execution environment requirements
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 575-596) - Timing and isolation considerations
- **Dependencies**:
  - Phase 3 completion (all E2E tests implemented)

### Task 4.2: Document Discord test environment requirements

Create comprehensive guide for setting up Discord test environment.

- **Files**:
  - TESTING_E2E.md - Expand "Discord Test Environment Setup" section
- **Success**:
  - Documents how to create test Discord guild
  - Explains bot permissions required (VIEW_CHANNEL, SEND_MESSAGES, EMBED_LINKS, etc.)
  - Provides instructions for adding bot to test guild
  - Lists steps to get Discord user ID for test accounts
  - Includes env/env.e2e configuration example
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 39-47) - TESTING_E2E.md current content
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 552-573) - Environment requirements
- **Dependencies**:
  - Phase 3 completion (test requirements validated)

### Task 4.3: Configure CI/CD for E2E test execution

Determine strategy for running E2E tests in CI/CD pipeline.

- **Files**:
  - .github/workflows/e2e-tests.yml - New workflow or update existing test workflow
  - README.md - Document CI/CD E2E test strategy
- **Success**:
  - Documents that E2E tests require external Discord resources
  - Recommends manual execution or conditional CI runs
  - If CI execution desired: GitHub secrets configured for TEST_DISCORD_TOKEN, etc.
  - Workflow includes conditional execution based on env var (ENABLE_E2E_TESTS)
  - Alternative: Skip Discord E2E tests in CI, run manually before releases
- **Research References**:
  - #file:../research/20251222-e2e-test-strategy-research.md (Lines 598-606) - CI/CD considerations
- **Dependencies**:
  - Phase 3 completion (E2E tests validated manually)
  - Project maintainer decision on CI/CD E2E strategy

## Dependencies

- pytest-asyncio for async test support
- discord.py library (already installed)
- Test Discord guild, channel, bot token, and test user
- Running full stack via compose.e2e.yaml profile

## Success Criteria

- All E2E tests pass when run against test Discord environment
- DiscordTestHelper module provides reusable API for Discord operations
- Documentation clearly explains test setup and execution
- Pattern established for adding future E2E test scenarios
- CI/CD strategy documented even if automated execution deferred
