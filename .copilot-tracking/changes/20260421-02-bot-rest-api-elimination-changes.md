---
applyTo: '.copilot-tracking/changes/20260421-02-bot-rest-api-elimination-changes.md'
---

<!-- markdownlint-disable-file -->

# Change Record: Bot REST API Elimination

## Overview

Eliminate all non-message REST calls from the Discord bot: replace `fetch_member`, `fetch_channel`, and `fetch_user` with in-memory gateway equivalents, and move guild sync out of `setup_hook` into `on_ready`.

## Added

_(none yet)_

## Modified

- `tests/unit/services/bot/auth/test_role_checker.py` — Task 1.1: replaced all 11 `mock_guild.fetch_member = AsyncMock(...)` setups with `mock_guild.get_member = MagicMock(...)` (synchronous); added `mock_guild.fetch_member.assert_not_called()` assertions to every permission-check test; updated three `_member_not_found` docstrings to reflect cache-miss rather than REST-miss semantics
- `services/bot/auth/role_checker.py` — Task 1.2: replaced `await guild.fetch_member(int(user_id))` with `guild.get_member(int(user_id))` (removed `await`, synchronous call) in `check_manage_guild_permission`, `check_manage_channels_permission`, and `check_administrator_permission`
- `tests/unit/services/bot/events/test_handlers.py` — Task 2.1: added `bot.fetch_channel = AsyncMock()` to `mock_bot` fixture; renamed `test_get_bot_channel_fetch_required` to `test_get_bot_channel_not_in_cache_returns_none` with `fetch_channel.assert_not_called()`; replaced three `_validate_channel_for_refresh` tests (removing discord_api patches, adding `fetch_channel.assert_not_called()` assertions); replaced `test_fetch_channel_and_message_channel_not_cached` and `test_fetch_channel_and_message_invalid_channel` to assert no `fetch_channel` call
- `services/bot/events/handlers.py` — Task 2.2: removed `discord_api.fetch_channel()` pre-check and `bot.fetch_channel()` fallback from `_validate_channel_for_refresh`; removed `bot.fetch_channel()` fallback from `_get_bot_channel`; removed `bot.fetch_channel()` try/except fallback from `_fetch_channel_and_message`; all three methods now use `bot.get_channel()` only
- `tests/unit/services/bot/events/test_handlers.py` — Task 3.1: added `bot.get_user = MagicMock()` to `mock_bot` fixture; updated `test_handle_send_notification_success` to use `get_user` instead of `fetch_user`/`discord_api.fetch_user`; updated `test_handle_send_notification_dm_disabled` to use `get_user`; added `test_handle_send_notification_user_not_in_cache`; updated `test_handle_clone_confirmation_sends_dm_with_view` to use `get_user` and assert `fetch_user.assert_not_called()`; added `test_handle_clone_confirmation_user_not_in_cache`; removed stale `get_discord_client` patches from `test_handle_game_created_success` and `test_validate_channel_for_refresh_does_not_call_discord_api`
- `services/bot/events/handlers.py` — Task 3.2: removed `discord_api.fetch_user()` pre-check and `bot.fetch_user()` call from `_send_dm`; replaced with `bot.get_user()` (synchronous) with None-guard log+return; removed `bot.fetch_user()` from `_handle_clone_confirmation`; replaced with `bot.get_user()` with None-guard log+return; removed now-unused `get_discord_client` import
- `tests/unit/services/bot/test_guild_sync.py` — Task 4.1/4.2: added `_make_gateway_guild` and `_make_gateway_channel` helper functions; added 4 tests for `sync_guilds_from_gateway` (creates new guilds, skips existing, no REST, filters channel types) and 3 tests for `sync_single_guild_from_gateway` (creates guild, skips existing, no REST); initially written with `xfail(strict=True)` markers and confirmed xfailed; markers removed after implementation
- `services/bot/guild_sync.py` — Task 4.1/4.2: added `_create_guild_with_gateway_channels` private helper that builds guild config and channel configs from `discord.Guild.channels` (no REST); added `sync_guilds_from_gateway(bot, db)` that iterates `bot.guilds` and creates configs for new guilds using gateway data; added `sync_single_guild_from_gateway(guild, db)` that creates config for a single event-supplied guild using gateway data
- `services/bot/bot.py` — Tasks 5.1/5.2/5.3: replaced `sync_all_bot_guilds(discord_client, db, token)` in `on_ready` with `sync_guilds_from_gateway(bot=self, db=db)` (after `_rebuild_redis_from_gateway()`); removed now-unused `get_discord_client` and `sync_all_bot_guilds` imports; replaced `sync_all_bot_guilds` call in `on_guild_join` with `sync_single_guild_from_gateway(guild=guild, db=db)` (no `get_discord_client` call needed); removed `bot.fetch_channel()` fallback in `_run_sweep_worker` — now logs a warning and skips the channel if `bot.get_channel()` returns None
- `tests/unit/services/bot/test_bot.py` — Tasks 5.1/5.2/5.3: removed stale `get_discord_client`, `get_db_session`, and `sync_all_bot_guilds` patches from `test_setup_hook_guild_sync_success`; updated all `on_guild_join` tests to patch `sync_single_guild_from_gateway` and assert `guild=guild, db=db` call signature; renamed `test_run_sweep_worker_calls_fetch_channel_when_get_channel_none` to `test_run_sweep_worker_skips_channel_when_not_in_gateway_cache` and rewrote to assert `fetch_channel` is NOT awaited and no publish occurs
- `tests/unit/bot/test_bot_ready.py` — Task 5.1: added `sync_guilds_from_gateway` and `get_db_session` patches to `on_ready_env` fixture so existing tests pass after new sync call; added `test_on_ready_calls_sync_guilds_from_gateway` delegation test

## Removed

_(none yet)_
