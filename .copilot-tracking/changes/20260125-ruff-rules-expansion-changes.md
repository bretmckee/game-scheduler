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
- scripts/check_commit_duplicates.py - Removed unnecessary else after return statement (RET505)
- services/api/dependencies/permissions.py - Removed unnecessary variable assignments before return in can_manage_game and can_export_game (RET504)
- services/api/routes/templates.py - Removed superfluous else after raise in list_templates error handling (RET506)
- services/api/services/display_names.py - Removed empty TYPE_CHECKING block (TC005) and simplified nested if-else in _build_avatar_url (RET505)
- services/api/services/participant_resolver.py - Removed unnecessary assignment before return in _search_guild_members (RET504)
- services/bot/bot.py - Moved circular import forward declarations into proper TYPE_CHECKING block (TC001)
- services/bot/commands/decorators.py - Added explicit None returns to improve consistency (RET502)
- services/bot/events/handlers.py - Moved Callable import to TYPE_CHECKING block (TC003) and removed unnecessary assignment in _fetch_game_for_refresh (RET504)
- services/bot/utils/discord_format.py - Simplified nested if-else chain in format_duration (RET505)
- services/scheduler/generic_scheduler_daemon.py - Moved Session import to TYPE_CHECKING block (TC002)
- shared/cache/client.py - Removed unnecessary assignments before return in get and expire methods (RET504)
- shared/messaging/sync_publisher.py - Moved pika imports to TYPE_CHECKING block (TC002)
- shared/schemas/game.py - Moved ParticipantResponse to TYPE_CHECKING block and re-imported at module end for model_rebuild with noqa:TC001 (TC001)
- shared/utils/status_transitions.py - Replaced elif with if in get_next_status for cleaner flow (RET505)

### Removed
