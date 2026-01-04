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

### Removed
