<!-- markdownlint-disable-file -->

# Release Changes: Reduce Complexity Thresholds to Default Values

**Related Plan**: 20260116-default-complexity-thresholds-reduction-plan.instructions.md
**Implementation Date**: 2026-01-17

## Summary

Systematically refactor high-complexity functions to reduce cyclomatic complexity threshold from 17→10 and cognitive complexity threshold from 20→15 (tool default values), applying proven patterns from create_game() refactoring success.

## Changes

### Added

- [tests/services/api/routes/test_games_helpers.py](tests/services/api/routes/test_games_helpers.py) - Unit tests for extracted helper functions (_parse_update_form_data and _process_image_upload)
- [tests/services/api/services/test_update_game_fields_helpers.py](tests/services/api/services/test_update_game_fields_helpers.py) - Unit tests for _update_game_fields extracted helpers covering field updates, timezone handling, and schedule flags
- [tests/services/bot/formatters/test_game_message.py](tests/services/bot/formatters/test_game_message.py) - Added 17 unit tests for create_game_embed extracted helpers (TestGameMessageFormatterHelpers class) covering description truncation, URL generation, author configuration, game time fields, participant fields, and footer/links

### Modified

- [services/api/routes/games.py](services/api/routes/games.py) - Extracted _parse_update_form_data() and _process_image_upload() helpers, refactored update_game() to reduce complexity from C:14 to A:5
- [services/api/services/games.py](services/api/services/games.py) - Extracted _update_simple_text_fields(), _update_scheduled_at_field(), _update_schedule_affecting_fields(), and _update_remaining_fields() helpers, refactored _update_game_fields() to reduce complexity from C:13/Cog:16 to below thresholds; extracted _separate_existing_and_new_participants(), _remove_outdated_participants(), and _update_participant_positions() helpers, refactored _update_prefilled_participants() to reduce complexity from C:11/Cog:17 to A:2; extracted _capture_old_state(), _update_image_fields(), _process_game_update_schedules(), and _detect_and_notify_promotions() helpers, refactored update_game() to reduce complexity from C:13/Cog:17 to B:6
- [services/api/services/display_names.py](services/api/services/display_names.py) - Extracted _check_cache_for_users(), _fetch_and_cache_display_names_avatars(), and _create_fallback_user_data() helpers, refactored resolve_display_names_and_avatars() to reduce complexity from C:12/Cog:19 to below thresholds
- [services/api/services/games.py](services/api/services/games.py) - Phase 2: Extracted _verify_bot_manager_permission(), _resolve_and_validate_host_participant(), and _get_or_create_user_by_discord_id() helpers, refactored _resolve_game_host() to reduce cognitive complexity from Cog:21 to below threshold
- [services/bot/events/handlers.py](services/bot/events/handlers.py) - Phase 2: Extracted _validate_game_for_reminder(), _partition_and_filter_participants(), _send_participant_reminders(), and _send_host_reminder() helpers, refactored _handle_game_reminder() to reduce cognitive complexity from Cog:23 to below threshold; Phase 3: Extracted _fetch_join_notification_data(), _is_participant_confirmed(), _format_join_notification_message(), and _send_join_notification_dm() helpers, refactored _handle_join_notification() to reduce cognitive complexity from Cog:19 to Cog:8
- [services/api/services/participant_resolver.py](services/api/services/participant_resolver.py) - Extracted _resolve_discord_mention_format(), _resolve_user_friendly_mention(), and _create_placeholder_participant() helpers, refactored resolve_initial_participants() to reduce complexity from C:12/Cog:20 to B:7
- [services/bot/events/handlers.py](services/bot/events/handlers.py) - Extracted _update_message_for_player_removal(), _build_removal_dm_message(), and _notify_removed_player() helpers, refactored _handle_player_removed() to reduce complexity from C:12/Cog:18 to below thresholds
- [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Extracted _prepare_description_and_urls(), _configure_embed_author(), _add_game_time_fields(), _add_participant_fields(), and _add_footer_and_links() helpers, refactored create_game_embed() to reduce complexity from C:14/Cog:17 to below thresholds
- [services/retry/retry_daemon.py](services/retry/retry_daemon.py) - Extracted _check_dlq_depth(), _process_single_message(), _consume_and_process_messages(), and _update_health_tracking() helpers, refactored _process_dlq() to reduce cognitive complexity from Cog:39 to Cog:4 (90% reduction)
- [services/bot/commands/list_games.py](services/bot/commands/list_games.py) - Extracted _determine_fetch_strategy() and _fetch_games_by_strategy() helpers, refactored list_games_command() to reduce cognitive complexity from Cog:20 to below threshold
- [services/api/auth/roles.py](services/api/auth/roles.py) - Phase 4: Extracted _find_guild_data(), _has_administrator_permission(), and _has_any_requested_permission() helpers, refactored has_permissions() to reduce cognitive complexity from Cog:19 to Cog:5 (74% reduction)
- [scripts/verify_button_states.py](scripts/verify_button_states.py) - Extracted _print_game_info(), _calculate_expected_button_states(), _print_expected_button_states(), and _fetch_and_verify_discord_buttons() helpers, refactored verify_game_buttons() to reduce cognitive complexity from Cog:32 to Cog:4 (88% reduction)
- [tests/e2e/helpers/discord.py](tests/e2e/helpers/discord.py) - Extracted _build_field_map(), _verify_basic_embed_structure(), _verify_game_time_field(), _verify_optional_fields(), _find_participants_field(), _verify_participants_numbering(), _verify_waitlist_field(), and _verify_links_field() helpers, refactored verify_game_embed() to reduce cognitive complexity from Cog:37 to Cog:1 (97% reduction)
- [tests/services/api/services/test_display_names.py](tests/services/api/services/test_display_names.py) - Added 10 unit tests for extracted helper methods covering cache checking, Discord API fetching, and fallback data creation
- [tests/services/api/services/test_games.py](tests/services/api/services/test_games.py) - Added 15 unit tests for _update_prefilled_participants extracted helpers covering participant separation, removal, and position updates; added 13 unit tests for update_game extracted helpers covering state capture, image updates, schedule processing, and promotion detection
- [tests/services/api/services/test_participant_resolver.py](tests/services/api/services/test_participant_resolver.py) - Added 13 unit tests for extracted helper methods covering Discord mention format resolution, user-friendly mention search, and placeholder participant creation
- [tests/services/api/services/test_games.py](tests/services/api/services/test_games.py) - Phase 2: Added 9 unit tests for _resolve_game_host extracted helpers covering bot manager permission verification, host participant resolution/validation, and user retrieval/creation
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py) - Phase 2: Added 11 unit tests for _handle_game_reminder extracted helpers covering game validation, participant partitioning/filtering, reminder sending, and host notification; Phase 3: Added 10 unit tests for _handle_join_notification extracted helpers covering data fetching, waitlist status checking, message formatting, and DM sending
- [tests/services/api/auth/test_roles.py](tests/services/api/auth/test_roles.py) - Phase 4: Added TestHasPermissionsHelpers class with 12 unit tests for extracted helpers covering guild lookup, administrator permission checking, and specific permission matching
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py) - Added 9 unit tests for _handle_player_removed extracted helpers covering message updates, DM notification building, and player notification
- [tests/services/bot/formatters/test_game_message.py](tests/services/bot/formatters/test_game_message.py) - Added 17 unit tests for create_game_embed extracted helpers (TestGameMessageFormatterHelpers class) covering description truncation, URL generation, author configuration, game time fields, participant fields, and footer/links
- [tests/services/retry/test_retry_daemon.py](tests/services/retry/test_retry_daemon.py) - Added TestRetryDaemonHelpers test class with 13 unit tests for extracted helpers covering DLQ depth checking, single message processing (success/failure/validation), message consumption, and health tracking
- [pyproject.toml](pyproject.toml) - Phase 2: Lowered cyclomatic complexity threshold from 17 to 10 (default) after verifying all code complies

### Removed

## Implementation Progress

### Phase 1: Dual-Violation Functions (C:17/Cog:20) ✓

- [x] **Task 1.1-1.8**: Refactored 8 dual-violation functions (COMPLETE)
- [x] **Task 1.9**: ~~Lower thresholds to C901=12, complexipy=17~~ **DEFERRED** - Cannot lower thresholds while violations remain. Will lower thresholds after ALL refactoring complete (end of Phase 4).

**Rationale**: Lowering thresholds mid-refactoring would cause pre-commit hooks to fail on remaining violations. Threshold reduction must occur AFTER all code complies.

### Phase 2: Remaining Cyclomatic Violations ✓

**Goal**: Fix remaining cyclomatic complexity violations to enable C901=10 threshold

- [x] **Task 2.1**: Verified no remaining C901 violations exist (Phase 1 resolved all)
- [x] **Task 2.2**: Lowered C901 threshold to 10 (default) in [pyproject.toml](pyproject.toml:83)
- **Result**: All code now complies with cyclomatic complexity ≤10

### Phase 3: High Cognitive Complexity (20-27) (In Progress)

**Goal**: Reduce high cognitive complexity functions below 20

- [x] **Task 3.1**: Refactored `_resolve_game_host` (services/api/services/games.py:98-206) - Cog: 21→≤10
  - Extracted `_verify_bot_manager_permission()` for permission validation
  - Extracted `_resolve_and_validate_host_participant()` for participant resolution
  - Extracted `_get_or_create_user_by_discord_id()` for user retrieval/creation
  - Added 9 unit tests in [tests/services/api/services/test_games.py](tests/services/api/services/test_games.py:3654-3894)
  - Successfully reduced cognitive complexity from 21→below threshold
- [x] **Task 3.2**: Refactored `_handle_game_reminder` (services/bot/events/handlers.py:355-467) - Cog: 23→≤10
  - Extracted `_validate_game_for_reminder()` for game state validation
  - Extracted `_partition_and_filter_participants()` for participant processing
  - Extracted `_send_participant_reminders()` for batch DM sending
  - Extracted `_send_host_reminder()` for host notification
  - Added 11 unit tests in [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py:1179-1414)
  - Successfully reduced cognitive complexity from 23→below threshold
- [x] **Task 3.3**: Refactored `_handle_game_cancelled` (services/bot/events/handlers.py:780-848) - Cog: 24→≤10
  - Extracted `_validate_cancellation_event_data()` for event data validation
  - Extracted `_fetch_and_validate_channel()` for Discord channel fetching/validation
  - Extracted `_update_cancelled_game_message()` for message update logic
  - Added 12 unit tests in [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py:1449-1650)
  - Successfully reduced cognitive complexity from 24→below threshold
- [x] **Task 3.4**: Verified `_resolve_template_fields` (services/api/services/games.py:325-380) - Cog: 10 (Already compliant)
  - Function already refactored in prior create_game complexity reduction work (commit 3769f01)
  - Current cognitive complexity: 10 (well below threshold of 15)
  - Has 9 comprehensive unit tests covering all scenarios
  - No additional work needed - task already complete
- [x] **Task 3.5**: Refactored `_handle_join_notification` (services/bot/events/handlers.py:503-640) - Cog: 19→8
  - Extracted `_fetch_join_notification_data()` for game/participant lookup
  - Extracted `_is_participant_confirmed()` for waitlist status checking
  - Extracted `_format_join_notification_message()` for conditional message formatting
  - Extracted `_send_join_notification_dm()` for DM sending and logging
  - Added 10 unit tests in [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py:1018-1254)
  - Successfully reduced cognitive complexity from 19→8 (58% reduction)
- [x] **Task 3.6**: Refactored `list_games_command` (services/bot/commands/list_games.py:39-112) - Cog: 20→≤10
  - Extracted `_determine_fetch_strategy()` for command parameter-based strategy determination
  - Extracted `_fetch_games_by_strategy()` for strategy-based game fetching
  - Added 10 unit tests in [tests/services/bot/commands/test_list_games.py](tests/services/bot/commands/test_list_games.py:242-391)
  - Successfully reduced cognitive complexity from 20→below threshold

### Phase 4: Remaining Cognitive Violations (16-19) (In Progress)

**Goal**: Complete cognitive complexity reduction to enable complexipy=15 threshold

- [x] **Task 4.1**: Refactored `has_permissions` (services/api/auth/roles.py:95-142) - Cog: 19→5
  - Extracted `_find_guild_data()` for guild lookup in list
  - Extracted `_has_administrator_permission()` for admin permission checking
  - Extracted `_has_any_requested_permission()` for specific permission matching
  - Added 12 unit tests in [tests/services/api/auth/test_roles.py](tests/services/api/auth/test_roles.py:239-382) (TestHasPermissionsHelpers class)
  - Successfully reduced cognitive complexity from 19→5 (74% reduction)
  - All 26 unit tests passing with 100% coverage of extracted methods
- [ ] **Task 4.2**: Address remaining 6 cognitive complexity violations (Cog:16-20)
- [ ] **Task 4.3**: Lower BOTH thresholds to defaults (C901=10, complexipy=15) after verification
