<!-- markdownlint-disable-file -->

# Release Changes: RLS Phase 2 - BYPASSRLS Bot User Implementation

**Related Plan**: 20260104-rls-phase2-bypassrls-bot-user-plan.instructions.md
**Implementation Date**: 2026-01-04

## Summary

Implement separate BYPASSRLS database user for bot and daemon services to eliminate unnecessary RLS overhead while maintaining API security. Bot and daemons will use `gamebot_bot` user (BYPASSRLS, non-superuser) while API continues using `gamebot_app` user (RLS enforced).

## Changes

### Added

### Modified

- services/init/database_users.py - Added gamebot_bot user creation with BYPASSRLS privilege and full table permissions
- config.template/env.template - Added POSTGRES_BOT_USER, POSTGRES_BOT_PASSWORD, and BOT_DATABASE_URL variables with documentation
- config/env.dev - Added bot user credentials (dev_bot_password_change_in_prod)
- config/env.staging - Added bot user credentials (staging_bot_password_change_me)
- config/env.prod - Added bot user credentials (prod_bot_password_change_in_prod)
- config/env.int - Added bot user credentials (integration_bot_password)
- config/env.e2e - Added bot user credentials (e2e_bot_password)
- compose.yaml - Updated init service to use ADMIN_DATABASE_URL for migrations and added POSTGRES_BOT_USER/PASSWORD env vars
- compose.yaml - Updated bot service to use BOT_DATABASE_URL (bypasses RLS)
- compose.yaml - Updated notification-daemon service to use BOT_DATABASE_URL (bypasses RLS)
- compose.yaml - Updated status-transition-daemon service to use BOT_DATABASE_URL (bypasses RLS)
- compose.int.yaml - Integration test service now receives BOT_DATABASE_URL, POSTGRES_BOT_USER/PASSWORD, and ADMIN_DATABASE_URL
- tests/integration/conftest.py - Use admin_db for fixture creation (bypasses RLS), fix docstrings, and ensure consistent session setup
- tests/integration/test_rls_api_enforcement.py - Set RLS context via set_config on session before querying
- tests/integration/test_rls_bot_bypass.py - Enabled bot bypass test via BOT_DATABASE_URL

### Removed

**Note**: Phase 3 tasks (remove guild context management from bot/daemon services) determined to be not applicable. Bot and daemon services never implemented guild context management code - they relied on explicit JOIN/WHERE conditions for guild filtering. No code removal needed since bot/daemons now bypass RLS using gamebot_bot user with BYPASSRLS privilege.
