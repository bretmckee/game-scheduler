<!-- markdownlint-disable-file -->

# Release Changes: Ruff Linting Rules Expansion

**Related Plan**: 20260125-ruff-rules-expansion-plan.instructions.md
**Implementation Date**: 2026-01-25

## Summary

Incrementally expanding Ruff linting rules across 7 phases to address 878 violations, fixing all issues before enabling each rule category to maintain zero-violation baseline.

## Changes

### Added

### Modified

- services/init/database_users.py - Fixed SQL injection vulnerability (S608) by using sql.Identifier for safe SQL construction
- services/init/verify_schema.py - Fixed SQL injection vulnerability (S608) by using sql.Identifier for table names
- services/init/migrations.py - Fixed subprocess security issues (S603/S607) by using shutil.which() for absolute executable paths
- scripts/check_commit_duplicates.py - Fixed subprocess security issues (S603/S607) by using shutil.which() for absolute executable paths
- services/bot/bot.py - Replaced assert with explicit None check and RuntimeError in event publisher initialization
- shared/messaging/consumer.py - Replaced asserts with explicit None checks and RuntimeError in queue operations
- services/api/routes/auth.py - Converted Query and Depends parameters to use Annotated pattern for FAST002 compliance
- services/api/routes/channels.py - Added Annotated import and converted all FastAPI dependency parameters to Annotated pattern
- services/api/routes/export.py - Added Annotated import and converted export_game parameters to Annotated pattern
- services/api/routes/games.py - Converted all 14 route functions to use Annotated pattern with keyword-only parameters where needed
- services/api/routes/guilds.py - Added Annotated import and converted all 10 route functions to Annotated pattern
- services/api/routes/templates.py - Added Annotated import and converted all 6 template route functions to Annotated pattern
- tests/services/api/routes/test_templates.py - Updated 3 tests to pass mock_discord_client parameter after removing default values

### Removed
