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
- shared/messaging/consumer.py - Fixed S110 by logging exception instead of silently passing in error handler fallback
- services/init/main.py - Fixed S108 by using tempfile.gettempdir() instead of hardcoded /tmp path
- tests/services/init/test_main.py - Updated 2 tests to mock tempfile.gettempdir() for marker file creation
- shared/messaging/config.py - Removed default password parameter, made it required to eliminate S107 security warning
- tests/shared/messaging/test_config.py - Updated 5 tests to explicitly provide password parameter
- pyproject.toml - Added S, ASYNC, FAST to select list; minimal ignore list (S101 only)
- pyproject.toml - Added per-file ignores for tests (S101, S106, S105, S108)
- scripts/check_commit_duplicates.py - Added inline noqa:S404 comment for intentional subprocess usage
- services/init/migrations.py - Added inline noqa:S404 comment for intentional subprocess usage
- services/api/config.py - Added inline noqa:S104 comment for intentional 0.0.0.0 binding

### Removed
