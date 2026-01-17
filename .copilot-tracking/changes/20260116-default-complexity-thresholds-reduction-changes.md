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
- [services/api/services/participant_resolver.py](services/api/services/participant_resolver.py) - Extracted _resolve_discord_mention_format(), _resolve_user_friendly_mention(), and _create_placeholder_participant() helpers, refactored resolve_initial_participants() to reduce complexity from C:12/Cog:20 to B:7
- [services/bot/events/handlers.py](services/bot/events/handlers.py) - Extracted _update_message_for_player_removal(), _build_removal_dm_message(), and _notify_removed_player() helpers, refactored _handle_player_removed() to reduce complexity from C:12/Cog:18 to below thresholds
- [services/bot/formatters/game_message.py](services/bot/formatters/game_message.py) - Extracted _prepare_description_and_urls(), _configure_embed_author(), _add_game_time_fields(), _add_participant_fields(), and _add_footer_and_links() helpers, refactored create_game_embed() to reduce complexity from C:14/Cog:17 to below thresholds
- [services/retry/retry_daemon.py](services/retry/retry_daemon.py) - Extracted _check_dlq_depth(), _process_single_message(), _consume_and_process_messages(), and _update_health_tracking() helpers, refactored _process_dlq() to reduce cognitive complexity from Cog:39 to Cog:4 (90% reduction)
- [tests/e2e/helpers/discord.py](tests/e2e/helpers/discord.py) - Extracted _build_field_map(), _verify_basic_embed_structure(), _verify_game_time_field(), _verify_optional_fields(), _find_participants_field(), _verify_participants_numbering(), _verify_waitlist_field(), and _verify_links_field() helpers, refactored verify_game_embed() to reduce cognitive complexity from Cog:37 to Cog:1 (97% reduction)
- [tests/services/api/services/test_display_names.py](tests/services/api/services/test_display_names.py) - Added 10 unit tests for extracted helper methods covering cache checking, Discord API fetching, and fallback data creation
- [tests/services/api/services/test_games.py](tests/services/api/services/test_games.py) - Added 15 unit tests for _update_prefilled_participants extracted helpers covering participant separation, removal, and position updates; added 13 unit tests for update_game extracted helpers covering state capture, image updates, schedule processing, and promotion detection
- [tests/services/api/services/test_participant_resolver.py](tests/services/api/services/test_participant_resolver.py) - Added 13 unit tests for extracted helper methods covering Discord mention format resolution, user-friendly mention search, and placeholder participant creation
- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py) - Added 9 unit tests for _handle_player_removed extracted helpers covering message updates, DM notification building, and player notification
- [tests/services/bot/formatters/test_game_message.py](tests/services/bot/formatters/test_game_message.py) - Added 17 unit tests for create_game_embed extracted helpers (TestGameMessageFormatterHelpers class) covering description truncation, URL generation, author configuration, game time fields, participant fields, and footer/links
- [tests/services/retry/test_retry_daemon.py](tests/services/retry/test_retry_daemon.py) - Added TestRetryDaemonHelpers test class with 13 unit tests for extracted helpers covering DLQ depth checking, single message processing (success/failure/validation), message consumption, and health tracking

### Removed
