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
- services/api/auth/roles.py - Added noqa:PLW0603 comment justifying singleton pattern for role verification service
- services/api/config.py - Added noqa:PLW0603 comment justifying singleton pattern for API configuration
- services/api/dependencies/discord.py - Added noqa:PLW0603 comment justifying singleton pattern for Discord API client
- services/bot/config.py - Added noqa:PLW0603 comment justifying singleton pattern for bot configuration
- services/bot/dependencies/discord_client.py - Added noqa:PLW0603 comment justifying singleton pattern for bot Discord client
- services/bot/events/publisher.py - Added noqa:PLW0603 comment justifying singleton pattern for bot event publisher
- services/retry/retry_daemon_wrapper.py - Added noqa:PLW0603 comment justifying global for signal handler communication
- services/scheduler/config.py - Added noqa:PLW0603 comment justifying singleton pattern for scheduler configuration
- services/scheduler/notification_daemon_wrapper.py - Added noqa:PLW0603 comment justifying global for signal handler communication
- services/scheduler/status_transition_daemon_wrapper.py - Added noqa:PLW0603 comment justifying global for signal handler communication
- shared/cache/client.py - Added noqa:PLW0603 comments justifying singleton patterns for Redis and sync Redis clients
- shared/discord/client.py - Added noqa:PLW0603 comment justifying singleton pattern for legacy Discord client
- shared/messaging/config.py - Added noqa:PLW0603 comments justifying singleton pattern for RabbitMQ connection pooling and cleanup
- shared/telemetry.py - Replaced 8 print statements with appropriate logger.info and logger.debug calls for telemetry initialization and flushing
- tests/shared/test_telemetry.py - Created comprehensive unit tests for telemetry module with 13 test cases covering init_telemetry, flush_telemetry, and get_tracer functions using proper mocking
- pyproject.toml - Added T20 (flake8-print) to select list for production code
- pyproject.toml - Added T201 to per-file-ignores for tests, scripts, and test_oauth.py to allow print statements in appropriate contexts
- shared/database_objects.py - Refactored 4 section header comments to avoid ERA001 false positives while maintaining purpose documentation
- services/api/services/games.py - Combined nested if statements using and operator for template signup method validation (SIM102)
- services/bot/bot.py - Combined nested if statements for button handler interaction type check (SIM102)
- shared/telemetry.py - Added noqa:PLC2701 comments for intentional OpenTelemetry private API imports (_log_exporter and _logs modules)
- scripts/check_commit_duplicates.py - Added explicit encoding='utf-8' to open() call (PLW1514)
- services/bot/formatters/game_message.py - Replaced try-except-pass with contextlib.suppress for status display error handling (SIM105)
- services/bot/handlers/utils.py - Replaced try-except-pass with contextlib.suppress for interaction defer error handling (SIM105)
- services/bot/main.py - Replaced try-except-pass with contextlib.suppress for KeyboardInterrupt handling (SIM105)
- services/init/migrations.py - Added explicit check=False to subprocess.run call (PLW1510)
- pyproject.toml - Added Phase 2 code quality rules to select list: RET, SIM, TC, PLE, PLW, PLC, ERA, A, DTZ, ICN, PT
- **Phase 3: Logging Performance Optimization (G004)** - Converted all 341 f-string logging statements to lazy % formatting across 50 production files for improved logging performance
- scripts/init_rabbitmq.py - Converted 6 logging f-strings to % formatting
- services/api/app.py - Converted logging f-strings to % formatting
- services/api/auth/oauth2.py - Converted logging f-strings to % formatting
- services/api/auth/roles.py - Converted logging f-strings to % formatting
- services/api/auth/tokens.py - Converted logging f-strings to % formatting
- services/api/database/queries.py - Converted logging f-strings to % formatting
- services/api/dependencies/permissions.py - Converted 6 logging f-strings to % formatting
- services/api/middleware/authorization.py - Converted 5 logging f-strings to % formatting
- services/api/middleware/error_handler.py - Converted logging f-strings to % formatting
- services/api/routes/auth.py - Converted logging f-strings to % formatting
- services/api/routes/games.py - Converted logging f-strings to % formatting
- services/api/routes/guilds.py - Converted logging f-strings to % formatting
- services/api/services/display_names.py - Converted logging f-strings to % formatting
- services/api/services/games.py - Converted logging f-strings to % formatting (including complex multiline logs)
- services/api/services/notification_schedule.py - Converted logging f-strings to % formatting
- services/api/services/participant_resolver.py - Converted logging f-strings to % formatting
- services/bot/auth/cache.py - Converted logging f-strings to % formatting
- services/bot/auth/role_checker.py - Converted logging f-strings to % formatting
- services/bot/bot.py - Converted logging f-strings to % formatting (including format specifiers)
- services/bot/events/handlers.py - Converted 23 logging f-strings to % formatting (largest file)
- services/bot/events/publisher.py - Converted logging f-strings to % formatting
- services/bot/handlers/button_handler.py - Converted logging f-strings to % formatting
- services/bot/handlers/join_game.py - Converted logging f-strings to % formatting
- services/bot/handlers/leave_game.py - Converted logging f-strings to % formatting
- services/bot/handlers/utils.py - Converted logging f-strings to % formatting
- services/bot/main.py - Converted logging f-strings to % formatting
- services/bot/utils/discord_format.py - Converted logging f-strings to % formatting
- services/init/database_users.py - Converted 14 logging f-strings to % formatting
- services/init/main.py - Converted logging f-strings to % formatting (including timestamp and duration with format specifiers)
- services/init/migrations.py - Converted logging f-strings to % formatting
- services/init/rabbitmq.py - Converted 2 logging f-strings to % formatting
- services/init/seed_e2e.py - Converted logging f-strings to % formatting
- services/init/verify_schema.py - Converted logging f-strings to % formatting
- services/init/wait_postgres.py - Converted logging f-strings to % formatting
- services/retry/retry_daemon.py - Converted logging f-strings to % formatting
- services/retry/retry_daemon_wrapper.py - Converted logging f-strings to % formatting
- services/scheduler/event_builders.py - Converted 2 logging f-strings to % formatting
- services/scheduler/generic_scheduler_daemon.py - Converted logging f-strings to % formatting (including float format specifiers)
- services/scheduler/notification_daemon_wrapper.py - Converted logging f-strings to % formatting
- services/scheduler/postgres_listener.py - Converted logging f-strings to % formatting
- services/scheduler/services/notification_service.py - Converted 3 logging f-strings to % formatting
- services/scheduler/status_transition_daemon_wrapper.py - Converted logging f-strings to % formatting
- shared/cache/client.py - Converted logging f-strings to % formatting
- shared/data_access/guild_isolation.py - Converted logging f-strings to % formatting
- shared/discord/client.py - Converted logging f-strings to % formatting
- shared/messaging/config.py - Converted logging f-strings to % formatting
- shared/messaging/consumer.py - Converted logging f-strings to % formatting
- shared/messaging/publisher.py - Converted logging f-strings to % formatting
- shared/messaging/sync_publisher.py - Converted logging f-strings to % formatting
- shared/telemetry.py - Converted logging f-strings to % formatting
- tests/services/bot/test_bot.py - Updated 3 tests to expect % formatting in logger.exception and logger.info calls
- tests/services/bot/test_main.py - Updated test to expect % formatting in environment logging
- tests/services/init/test_main.py - Updated 4 tests to verify % formatting in startup banner, phase logging, and completion banner
- tests/services/init/test_seed_e2e.py - Updated test to expect % formatting in guild entity creation logging
- tests/shared/discord/test_client.py - Updated 3 tests to verify % formatting in Discord API request/response logging
- pyproject.toml - G004 (logging-f-string) already in select list, verified zero violations
- services/scheduler/generic_scheduler_daemon.py - Fixed 3 format specifier conversions (:.1f → %.1f) for proper % formatting
- services/init/main.py - Fixed timestamp and duration logging with proper format specifiers
- services/init/verify_schema.py - Fixed quote handling in logging format string conversions
- services/bot/events/handlers.py - Fixed 4 E501 line-too-long violations by breaking long logging statements across multiple lines
- services/bot/handlers/leave_game.py - Fixed E501 line-too-long violation by breaking logging statement
- services/bot/utils/discord_format.py - Fixed E501 line-too-long violation in logging
- services/init/wait_postgres.py - Fixed E501 line-too-long violation in retry logging
- services/api/dependencies/permissions.py - Fixed 14 B008 noqa comment placement issues by moving comments from closing parens to Depends() lines
- pyproject.toml - Expanded test file lint ignores: added SIM117, PLR0915, S110, PLC1901, PLC0206, SIM102, SIM105, SIM108, PT011, PT018, DTZ001, ASYNC109 for pre-existing test patterns
- Auto-formatter applied formatting improvements to 35 test files (combined with statements, simplified nested structures)- scripts/check_commit_duplicates.py - Extracted 1 exception message to variable (EM101: git not found)
- services/api/auth/oauth2.py - Extracted 1 exception message to variable (EM101: invalid OAuth2 state)
- services/api/services/calendar_export.py - Extracted 2 exception messages to variables (EM102: game not found, EM101: permission denied)
- services/api/services/games.py - Extracted 23 exception messages to variables across create_game, update_game, cancel_game, join_game, and leave_game functions (13 EM101 + 10 EM102)
- services/api/services/template_service.py - Extracted 3 exception messages to variables (2 EM102: template not found + 1 EM101: cannot delete default)
- services/bot/bot.py - Extracted 1 exception message to variable (EM101: event publisher initialization failed)
- services/init/main.py - Extracted 1 exception message to variable (EM101: E2E seeding failed)
- services/retry/retry_daemon.py - Extracted 1 exception message to variable (EM101: publisher not initialized)
- services/scheduler/generic_scheduler_daemon.py - Extracted 4 exception messages to variables (EM101: daemon/database initialization checks)
- services/scheduler/postgres_listener.py - Extracted 3 exception messages to variables (EM101: connection state checks)
- shared/data_access/guild_queries.py - Extracted 26 exception messages to variables across guild isolation functions (20 EM101 + 6 EM102)
- shared/discord/client.py - Extracted 1 exception message to variable (EM102: invalid Discord token format)
- shared/messaging/consumer.py - Extracted 2 exception messages to variables (EM101: queue connection failures)
- shared/schemas/game.py - Extracted 3 exception messages to variables (EM102: validation failures)
- shared/utils/discord_tokens.py - Extracted 2 exception messages to variables (EM102: token parsing failures)
- pyproject.toml - Added EM (flake8-errmsg) to select list for Phase 4.1a
- .copilot-tracking/plans/20260125-ruff-rules-expansion-plan.instructions.md - Split Task 4.1 into 4.1a (EM complete) and 4.1b (RUF100 deferred to Phase 7 Task 7.3)
- .copilot-tracking/details/20260125-ruff-rules-expansion-details.md - Documented RUF100 deferral rationale and added Task 7.3 for manual cleanup after all rules enabled
- scripts/init_rabbitmq.py - Converted logger.error with exc_info=True to logger.exception for proper exception handling (G201)
- services/api/middleware/authorization.py - Converted logger.error with exc_info=True to logger.exception for request failure handling (G201)
- services/api/routes/guilds.py - Converted logger.error with exc_info=True to logger.exception in mention validation (G201)
- services/api/services/participant_resolver.py - Converted 3 logger.error with exc_info=True to logger.exception for guild member operations (G201)
- services/bot/events/handlers.py - Converted 17 logger.error with exc_info=True to logger.exception across event handlers (G201)
- services/bot/handlers/button_handler.py - Converted logger.error with exc_info=True to logger.exception for button interaction errors (G201)
- services/init/main.py - Converted logger.error with exc_info=True to logger.exception for initialization failures (G201)
- services/init/rabbitmq.py - Converted 2 logger.error with exc_info=True to logger.exception for RabbitMQ failures (G201)
- services/retry/retry_daemon.py - Converted 2 logger.error with exc_info=True to logger.exception for DLQ processing (G201)
- services/scheduler/services/notification_service.py - Converted logger.error with exc_info=True to logger.exception for notification failures (G201)
- shared/messaging/consumer.py - Converted logger.error with exc_info=True to logger.exception for message handler failures (G201)

### Deferred

- **RUF100 (unused noqa removal)** - Originally part of Task 4.1, deferred to Phase 7 Task 7.3
  - Reason: RUF100 has 100% false positive rate during incremental rule adoption
  - Reports all noqa comments as "non-enabled" when checking in isolation
  - Would remove 59 legitimate noqa comments (S404, S603, PLW0603, PLC0415, B008, PLC2701, S104)
  - Requires full rule context to work correctly
  - Will be manually reviewed in Phase 7 after all rules are enabled

### Removed
