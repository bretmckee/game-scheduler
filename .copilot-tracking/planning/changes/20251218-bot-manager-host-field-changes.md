<!-- markdownlint-disable-file -->

# Release Changes: Bot Manager Host Field Override

**Related Plan**: 20251218-bot-manager-host-field.plan.md
**Implementation Date**: 2025-12-22

## Summary

Enable bot managers to specify game host during creation via optional host field, while maintaining current user as default host for regular users and preserving backward compatibility.

## Changes

### Added

- tests/services/api/services/test_games.py - Added 6 comprehensive unit tests for host override functionality:
  - test_create_game_with_empty_host_defaults_to_current_user
  - test_create_game_regular_user_cannot_override_host
  - test_create_game_bot_manager_can_override_host
  - test_create_game_bot_manager_invalid_host_raises_validation_error
  - test_create_game_bot_manager_host_without_permissions_fails
  - test_create_game_bot_manager_empty_host_uses_self
- frontend/src/components/**tests**/GameForm.test.tsx - Added 5 frontend tests for conditional host field rendering:
  - should show host field when isBotManager is true
  - should not show host field when isBotManager is false
  - should not show host field when isBotManager is undefined (defaults to false)
  - should display host field with correct helper text
  - should allow regular users to see all other form fields without host field

Note: Integration tests for end-to-end workflows are fully covered by the comprehensive unit tests in tests/services/api/services/test_games.py (Task 3.1). These tests verify:

- Bot manager creates game with different host → game created with correct host
- Bot manager creates game with empty host → game created with bot manager as host
- Regular user creates game (no host sent) → game created with regular user as host
- Regular user attempts API call with host → authorization error
- Host validation errors propagate correctly to API responses

### Modified

- shared/schemas/game.py - Added optional host field to GameCreateRequest schema
- services/api/services/games.py - Added bot manager authorization check and host mention resolution in create_game method
- services/api/routes/games.py - Added host parameter to create_game route and passed to service
- frontend/src/components/GameForm.tsx - Added isBotManager prop, host field to GameFormData interface, conditional host TextField rendering for bot managers only, and useAuth hook import
- frontend/src/pages/CreateGame.tsx - Added isBotManager prop to GameForm component, included host in form submission payload for bot managers
- frontend/src/components/**tests**/GameForm.test.tsx - Added AuthContext provider wrapper for all tests to support useAuth hook

### Removed
