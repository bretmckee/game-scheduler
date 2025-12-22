<!-- markdownlint-disable-file -->

# Release Changes: E2E Test Strategy - Discord Message Validation

**Related Plan**: 20251222-e2e-test-strategy-plan.instructions.md
**Implementation Date**: 2025-12-22

## Summary

Implementation of true end-to-end testing that validates Discord bot behavior and message content, addressing the gap in current database-focused tests.

## Changes

### Added

- tests/e2e/helpers/__init__.py - Module initializer for E2E test helpers
- tests/e2e/helpers/discord.py - DiscordTestHelper class with connect/disconnect and async context manager support
- tests/e2e/test_game_announcement.py - E2E test file with environment fixtures for Discord message validation
- tests/e2e/test_00_environment.py - Environment validation test that runs first to verify E2E setup
- services/init/seed_e2e.py - E2E test data seeding module that populates guild/channel/user on init

### Modified

- tests/e2e/helpers/discord.py - Added message fetching methods: get_message(), get_recent_messages(), find_message_by_embed_title()
- tests/e2e/helpers/discord.py - Added DM verification methods: get_user_recent_dms(), find_game_reminder_dm()
- tests/e2e/helpers/discord.py - Added embed verification utilities: extract_embed_field_value(), verify_game_embed()
- tests/e2e/test_game_announcement.py - Added test_game_creation_posts_announcement_to_discord() to verify message posting
- tests/e2e/test_game_announcement.py - Enhanced test with embed content validation using verify_game_embed()
- compose.e2e.yaml - Updated command to run all E2E tests (tests/e2e/) instead of specific file
- compose.e2e.yaml - Added usage documentation for running specific tests with pytest arguments
- docker/test.Dockerfile - Updated CMD documentation to cover both integration and E2E test defaults
- scripts/run-e2e-tests.sh - Enhanced to forward pytest arguments like integration test script
- services/init/main.py - Added E2E seeding step after RabbitMQ initialization
- services/init/seed_e2e.py - Fixed import to use get_sync_db_session (not get_sync_session)
- services/init/seed_e2e.py - Fixed to use context manager pattern for database session
- compose.e2e.yaml - Added init service environment variables for TEST_ENVIRONMENT and Discord IDs
- tests/e2e/test_game_announcement.py - Replaced per-test fixtures with lookups to seeded data from init service
- tests/e2e/test_game_announcement.py - Simplified clean_test_data to only clean game records, not guild/channel/user

### Removed

- tests/e2e/test_game_notification_api_flow.py - Removed broken database-focused test that didn't validate Discord messages
