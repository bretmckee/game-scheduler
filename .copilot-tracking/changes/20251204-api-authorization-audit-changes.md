<!-- markdownlint-disable-file -->

# Release Changes: REST API Authorization Audit and Security Fixes

**Related Plan**: 20251204-api-authorization-audit-plan.instructions.md
**Implementation Date**: 2025-12-04

## Summary

Comprehensive security audit and fixes for REST API authorization vulnerabilities. Centralizes authorization logic, enforces proper guild membership checks, and prevents information disclosure about guilds user isn't member of.

**Test Coverage**: 82% for services/api/dependencies/permissions.py (exceeds 80% minimum requirement)

## Changes

### Added

- services/api/dependencies/permissions.py - Added require_bot_manager dependency for centralized bot manager authorization
- services/api/dependencies/permissions.py - Added verify_guild_membership helper to check Discord guild membership
- services/api/dependencies/permissions.py - Added verify_template_access helper to enforce guild membership for template access
- services/api/dependencies/permissions.py - Added verify_game_access helper to enforce guild membership and player role restrictions for game access
- tests/services/api/dependencies/test_permissions.py - Added comprehensive unit tests for require_bot_manager dependency
- tests/services/api/dependencies/test_permissions.py - Added comprehensive unit tests for verify_guild_membership helper
- tests/services/api/dependencies/test_permissions.py - Added comprehensive unit tests for verify_template_access helper (404 for non-members)
- tests/services/api/dependencies/test_permissions.py - Added comprehensive unit tests for verify_game_access helper (404 for non-members, 403 for missing roles)

### Modified

### Removed

