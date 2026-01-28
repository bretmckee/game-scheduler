<!-- markdownlint-disable-file -->

# Release Changes: Unit Test Fixture Consolidation

**Related Plan**: 20260126-unit-test-fixture-consolidation-plan.instructions.md
**Implementation Date**: 2026-01-26

## Summary

Consolidating 59 duplicate test fixtures across 91 unit test files into shared conftest.py files to reduce maintenance burden and improve test consistency. **All phases complete**: Phase 1 consolidated game service cluster fixtures (35 fixtures → 8 shared), Phase 2 added 4 unit test mock fixtures to root conftest.py, Phase 3 verified fixture discovery and documented usage patterns. All 1027 unit tests passing with 74.79% coverage.

## Changes

### Added

- tests/services/api/services/conftest.py - Created shared fixture file with 8 fixtures for game service tests (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel, sample_user)

### Modified

- tests/services/api/services/test_games.py - Removed 8 duplicate fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel, sample_user), kept test-specific fixtures (mock_role_service, sample_template, sample_game_data)
- tests/services/api/services/test_games_promotion.py - Removed 7 duplicate fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel), kept test-specific fixtures (sample_host, sample_game)
- tests/services/api/services/test_games_edit_participants.py - Removed 8 duplicate fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel, sample_user), no test-specific fixtures needed
- tests/services/api/services/test_games_image_upload.py - Removed 9 duplicate fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service, sample_guild, sample_channel, sample_user, mock_role_service kept but also in test_games.py), kept test-specific fixture (sample_template)
- tests/services/api/services/test_update_game_fields_helpers.py - Removed 5 duplicate fixtures (mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver, game_service), no test-specific fixtures needed
- tests/conftest.py - Added 4 unit test mock fixtures at end of file (mock_db_unit, mock_discord_api_client, mock_current_user_unit, mock_role_service) with comprehensive documentation explaining differences from integration test fixtures
- tests/services/api/routes/test_guilds.py - Removed mock_current_user fixture, updated all test methods to use mock_current_user_unit from shared conftest.py
- tests/services/api/routes/test_templates.py - Removed mock_current_user fixture, updated all test methods to use mock_current_user_unit from shared conftest.py
- tests/services/api/dependencies/test_permissions_migration.py - Removed mock_role_service fixture, now uses shared version from conftest.py
- tests/services/api/dependencies/test_permissions.py - Removed mock_role_service fixture, now uses shared version from conftest.py
- tests/conftest.py - Updated mock_role_service to include has_any_role and has_permissions methods for compatibility with dependency tests
- Verified fixture discovery - pytest successfully collected 1027 tests with no warnings about fixture discovery or scope issues
- Verified test coverage - All 1027 unit tests pass with 74.79% coverage, no regressions from fixture consolidation
- tests/services/api/services/conftest.py - Added comprehensive module docstring documenting 8 shared fixtures, usage patterns, and examples
- tests/conftest.py - Enhanced module docstring with fixture organization guide, naming conventions, and unit vs integration test distinction
- tests/conftest.py - Added detailed documentation to unit test mock fixtures section with usage examples and override patterns

### Removed
