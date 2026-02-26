<!-- markdownlint-disable-file -->

# Task Details: Remove Discord Webhooks and Use Gateway Events

## Research Reference

**Source Research**: #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md

## Phase 1: Remove Webhook Infrastructure

### Task 1.1: Delete webhook files

Delete all webhook-related files that are no longer needed since Discord gateway events are now non-privileged.

- **Files**:
  - Delete: `services/api/routes/webhooks.py` - HTTP webhook endpoint
  - Delete: `services/api/dependencies/discord_webhook.py` - Ed25519 signature validation
  - Delete: `tests/services/api/routes/test_webhooks.py` - Webhook endpoint tests
  - Delete: `tests/services/api/dependencies/test_discord_webhook.py` - Signature validation tests
  - Delete: `tests/integration/test_webhooks.py` - Integration tests
  - Delete: `docs/deployment/discord-webhook-setup.md` - Setup documentation
- **Success**:
  - All six files deleted
  - No import errors when running remaining code
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 16-34) - File analysis showing webhook infrastructure
- **Dependencies**:
  - None (first step)

### Task 1.2: Remove webhook router registration from API app

Remove webhook router from API application since the webhook endpoint is being deleted.

- **Files**:
  - `services/api/app.py` - Remove webhooks import and router registration
  - `services/api/dependencies/__init__.py` - Remove discord_webhook from exports
- **Success**:
  - API starts without importing webhooks module
  - No reference to webhooks router in app initialization
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 93-101) - Changes required section mentioning router removal
- **Dependencies**:
  - Task 1.1 completion (files must be deleted first)

### Task 1.3: Remove DISCORD_PUBLIC_KEY configuration

Remove Discord public key configuration since signature validation is no longer needed.

- **Files**:
  - `config/env.dev` - Remove DISCORD_PUBLIC_KEY
  - `config/env.int` - Remove DISCORD_PUBLIC_KEY
  - `config/env.e2e` - Remove DISCORD_PUBLIC_KEY
  - `config/env.staging` - Remove DISCORD_PUBLIC_KEY
  - `config/env.prod` - Remove DISCORD_PUBLIC_KEY
  - `config.template/env.template` - Remove DISCORD_PUBLIC_KEY
  - `services/api/config.py` - Remove discord_public_key field from APIConfig
- **Success**:
  - No references to DISCORD_PUBLIC_KEY in any config files
  - APIConfig loads without discord_public_key field
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 103-107) - Configuration removal requirements
- **Dependencies**:
  - Task 1.2 completion (no code references discord_public_key)

### Task 1.4: Remove PyNaCl dependency

Remove PyNaCl library since Ed25519 signature validation is no longer needed.

- **Files**:
  - `pyproject.toml` - Remove `pynacl~=1.5.0` from dependencies
- **Success**:
  - PyNaCl removed from dependencies list
  - `uv lock` runs successfully
  - No import errors for remaining code
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 109-111) - Dependency removal requirement
- **Dependencies**:
  - Task 1.1 completion (no code imports PyNaCl)

**Note**: This is a cleanup phase, not TDD. We're removing code that's being replaced by gateway events.

## Phase 2: Remove RabbitMQ Guild Sync Event

### Task 2.1: Remove GUILD_SYNC_REQUESTED event definition

Remove the RabbitMQ event that was used for webhook→bot communication.

- **Files**:
  - `shared/messaging/events.py` - Remove `GUILD_SYNC_REQUESTED = "guild.sync_requested"` constant
- **Success**:
  - GUILD_SYNC_REQUESTED constant removed
  - No references to this event in codebase
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 115-118) - Event removal requirement
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 72-76) - RabbitMQ usage analysis showing event is only used for webhook communication
- **Dependencies**:
  - Phase 1 completion (webhook that publishes event is removed)

### Task 2.2: Remove guild sync event handler from bot

Remove the RabbitMQ handler that consumed GUILD_SYNC_REQUESTED events.

- **Files**:
  - `services/bot/events/handlers.py` - Remove `_handle_guild_sync_requested()` method (lines 1080-1118)
  - `services/bot/events/handlers.py` - Remove `GUILD_SYNC_REQUESTED` from `_handlers` dict
  - `services/bot/events/handlers.py` - Remove from event subscriptions in `start_consuming()`
- **Success**:
  - Handler method removed
  - No registration of GUILD_SYNC_REQUESTED event
  - Bot starts and consumes other events successfully
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 120-125) - Handler removal requirements
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 30-32) - Handler code location
- **Dependencies**:
  - Task 2.1 completion (event constant removed)

### Task 2.3: Remove event handler tests

Remove tests for the GUILD_SYNC_REQUESTED event handler.

- **Files**:
  - `tests/services/bot/events/test_handlers.py` - Remove all `test_handle_guild_sync_requested_*` tests
- **Success**:
  - All guild sync requested tests removed
  - Remaining handler tests still pass
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 127-129) - Test removal requirement
- **Dependencies**:
  - Task 2.2 completion (handler removed)

**Note**: This is a cleanup phase for RabbitMQ infrastructure that's being replaced by direct gateway event handling.

## Phase 3: Update Bot on_guild_join Event (TDD)

### Task 3.1: Create stub for enhanced on_guild_join (RED phase)

Create a stub implementation that raises NotImplementedError for the sync functionality.

- **Files**:
  - `services/bot/bot.py` - Update on_guild_join (lines 193-207) to include stub for sync
- **Success**:
  - Method exists with logging and sync stub
  - Stub raises NotImplementedError when sync is called
  - Bot can still handle event without crashing
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 133-156) - Target implementation showing required changes
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 16-20) - Current on_guild_join code
- **Dependencies**:
  - Phase 2 completion (RabbitMQ event removed)

### Task 3.2: Write tests for on_guild_join sync behavior (RED phase)

Write tests with REAL assertions marked as @pytest.mark.xfail expecting actual sync behavior.

- **Files**:
  - `tests/services/bot/test_bot.py` - Update test_on_guild_join_event with xfail markers
- **Success**:
  - Tests verify sync_all_bot_guilds is called with correct arguments
  - Tests verify database commit is called
  - Tests verify success logging occurs
  - Tests verify exception handling for sync failures
  - All tests marked with @pytest.mark.xfail and currently fail
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 133-156) - Target implementation details
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 205-212) - Test update requirements
- **Dependencies**:
  - Task 3.1 completion (stub exists)

### Task 3.3: Implement on_guild_join to call sync_all_bot_guilds (GREEN phase)

Implement the actual sync functionality and remove xfail markers only (DO NOT modify test assertions).

- **Files**:
  - `services/bot/bot.py` - Replace stub with real implementation calling sync_all_bot_guilds
  - `tests/services/bot/test_bot.py` - Remove @pytest.mark.xfail markers only
- **Success**:
  - on_guild_join calls sync_all_bot_guilds with discord_client, db, and bot_token
  - Database session commits after successful sync
  - Success logging includes guild name, ID, and sync results
  - Exception handling logs errors without crashing bot
  - All tests pass without xfail markers
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 133-156) - Complete implementation code
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 60-64) - sync_all_bot_guilds function details
- **Dependencies**:
  - Task 3.2 completion (tests written)

### Task 3.4: Refactor and add edge case tests (REFACTOR phase)

Refactor implementation for clarity and add comprehensive edge case tests.

- **Files**:
  - `services/bot/bot.py` - Refactor if needed for clarity
  - `tests/services/bot/test_bot.py` - Add edge case tests
- **Success**:
  - Tests cover: sync failure, database commit failure, empty sync results
  - Edge case tests verify proper error handling
  - All tests pass including edge cases
  - Code is clean and maintainable
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 133-156) - Implementation showing error handling
- **Dependencies**:
  - Task 3.3 completion (GREEN phase done)

## Phase 4: Simplify GUI Sync Endpoint with Rate Limiting (TDD)

### Task 4.1: Create stub for updated sync endpoint (RED phase)

Create a stub that returns 501 Not Implemented for the new sync implementation.

- **Files**:
  - `services/api/routes/guilds.py` - Update sync endpoint (lines 301-329) to stub with 501
  - `services/api/routes/guilds.py` - Add rate limiter import
- **Success**:
  - Endpoint exists with rate limiter decorator
  - Returns 501 Not Implemented
  - Rate limiter is configured (1/minute)
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 158-188) - Target implementation showing rate limiting and sync_all_bot_guilds usage
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 90-98) - Rate limiting infrastructure already exists
- **Dependencies**:
  - Phase 3 completion (bot-side sync working)

### Task 4.2: Write tests for sync endpoint with rate limiting (RED phase)

Write tests with REAL assertions marked as expected failures expecting actual sync behavior and rate limiting.

- **Files**:
  - `tests/services/api/routes/test_guilds.py` - Update sync endpoint tests with xfail markers
  - `tests/services/api/routes/test_guilds.py` - Add rate limiting tests with xfail markers
- **Success**:
  - Tests verify sync_all_bot_guilds is called with correct arguments
  - Tests verify response format matches schema
  - Tests verify rate limiting (429 on second request within minute)
  - Tests verify successful path returns correct data
  - All tests marked with expected failure markers
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 158-188) - Implementation showing expected behavior
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 215-219) - Test requirements
- **Dependencies**:
  - Task 4.1 completion (stub exists)

### Task 4.3: Implement sync endpoint with sync_all_bot_guilds and rate limiting (GREEN phase)

Implement the actual endpoint functionality and remove expected failure markers only (DO NOT modify test assertions).

- **Files**:
  - `services/api/routes/guilds.py` - Replace 501 stub with real implementation
  - `services/api/routes/guilds.py` - Add imports for sync_all_bot_guilds and get_discord_client
  - `tests/services/api/routes/test_guilds.py` - Remove expected failure markers only
- **Success**:
  - Endpoint calls sync_all_bot_guilds with proper arguments
  - Database commits after successful sync
  - Returns GuildSyncResponse with correct format
  - Rate limiting works (429 on abuse)
  - All tests pass without expected failure markers
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 158-188) - Complete implementation code
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 60-64) - sync_all_bot_guilds details
- **Dependencies**:
  - Task 4.2 completion (tests written)

### Task 4.4: Refactor and add edge case tests (REFACTOR phase)

Refactor implementation for clarity and add comprehensive edge case tests.

- **Files**:
  - `services/api/routes/guilds.py` - Refactor if needed for clarity
  - `tests/services/api/routes/test_guilds.py` - Add edge case tests
- **Success**:
  - Tests cover: unauthorized access, sync failures, rate limit edge cases
  - Edge case tests verify proper error responses
  - All tests pass including edge cases
  - Code follows FastAPI best practices
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 100-101) - Project conventions reference
- **Dependencies**:
  - Task 4.3 completion (GREEN phase done)

## Phase 5: Remove Obsolete Functions

### Task 5.1: Analyze and remove sync_user_guilds and helpers

Remove sync_user_guilds function and its helper functions since we're using sync_all_bot_guilds everywhere.

- **Files**:
  - `services/api/services/guild_service.py` - Remove sync_user_guilds function
  - `services/api/services/guild_service.py` - Analyze and remove: \_compute_candidate_guild_ids, \_create_guild_with_channels_and_template, \_sync_guild_channels
  - `services/api/services/guild_service.py` - Keep refresh_guild_channels if it doesn't depend on removed helpers
- **Success**:
  - sync_user_guilds function removed
  - Helper functions removed if only used by sync_user_guilds
  - refresh_guild_channels remains functional if it exists
  - No import errors in codebase
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 190-199) - Function removal requirements
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 66-70) - sync_user_guilds vs sync_all_bot_guilds comparison
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 38-42) - guild_service.py file analysis
- **Dependencies**:
  - Phase 4 completion (sync endpoint no longer uses sync_user_guilds)

### Task 5.2: Update remaining tests to use sync_all_bot_guilds

Update any remaining tests that reference sync_user_guilds to use sync_all_bot_guilds instead.

- **Files**:
  - Search codebase for sync_user_guilds references
  - Update any remaining tests in `tests/services/api/services/test_guild_service.py`
- **Success**:
  - No references to sync_user_guilds in codebase
  - All tests pass with sync_all_bot_guilds usage
  - Test coverage maintained
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 190-199) - Removal requirements
- **Dependencies**:
  - Task 5.1 completion (function removed)

## Phase 6: Verification and Cleanup

### Task 6.1: Run full test suite and verify all tests pass

Run complete test suite to ensure no regressions.

- **Files**:
  - All test files
- **Success**:
  - `scripts/coverage-report.sh` passes with no failures
  - All unit tests pass
  - All integration tests pass
  - Code coverage maintained or improved
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 234-241) - Success criteria
- **Dependencies**:
  - Phase 5 completion (all code changes done)

### Task 6.2: Verify no remaining references to webhook infrastructure

Search codebase to ensure complete removal of webhook-related code.

- **Files**:
  - Search for: "webhook", "DISCORD_PUBLIC_KEY", "pynacl", "GUILD_SYNC_REQUESTED"
  - Verify no imports from deleted modules
- **Success**:
  - No references to webhooks.py or discord_webhook.py
  - No DISCORD_PUBLIC_KEY in any config files
  - No GUILD_SYNC_REQUESTED event references
  - No PyNaCl imports
  - Only expected references in documentation/comments about removal
- **Research References**:
  - #file:../research/20260226-01-remove-webhooks-use-gateway-events-research.md (Lines 93-129) - Complete list of items to remove
- **Dependencies**:
  - Task 6.1 completion (tests pass)

## Dependencies

- slowapi library for rate limiting
- Discord.py for gateway events
- sync_all_bot_guilds function in services/bot/guild_sync.py
- RabbitMQ messaging (only for cleanup, not new functionality)

## Success Criteria

- All webhook infrastructure removed (files, config, dependencies)
- RabbitMQ GUILD_SYNC_REQUESTED event removed
- Bot automatically syncs guilds on join via gateway event
- GUI sync endpoint simplified with rate limiting
- sync_user_guilds function removed
- All tests pass
- Architecture simplified with direct event handling
- No cross-service communication needed for guild events
