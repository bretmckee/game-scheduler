<!-- markdownlint-disable-file -->

# Release Changes: Test Assertion Quality (hollow provider assertions)

**Related Plan**: 20261109-01-test-assertion-quality.plan.md
**Implementation Date**: 2026-11-12

## Summary

Stop the test-assertion checker from forcing or accepting hollow `assert_called_once_with()` on dependency getters, clean up existing hollow sites, and document the checker's rules.

## Changes

### Added

- tests/unit/scripts/test_check_test_assertions.py - Tests that a patch alias used only inside another `assert_*` call's arguments, or as an operand of `==`/`!=`/`is`/`is not`/`in`/`not in` in an `assert`, counts as verified (written as strict xfail in Phase 1, xfail removed in Phase 2); guard test that bare `assert mock_x` is still a violation

### Modified

- scripts/check_test_assertions.py - `get_unasserted_named_mocks` now also accepts an alias referenced in `assert_*` call arguments (`_alias_used_in_assert_call_args`) or in an equality/identity/membership comparison inside `assert` (`_alias_used_in_assert_comparison`); bare truthiness checks still do not count
- tests/unit/services/api/routes/test_templates.py - Phase 3: 14 `get_role_service` patches now unnamed with `return_value=`; hollow getter assertions removed
- tests/unit/shared/discord/test_discord_api_client.py - Phase 3: 9 `get_redis_client` patches now unnamed; hollow getter assertions removed; the five 503 cache-miss tests and the emoji cache-hit test gained `mock_redis.get.assert_called_once_with(<cache key>)`, since the getter assertion had been their only evidence the cache was read
- tests/unit/services/bot/events/test_handlers_status_transition.py - Phase 3: 8 `get_db_session` patches now unnamed with the session fake built above the patch; `test_handle_status_transition_due_game_not_found` (whose only assertion was the hollow one) now asserts the game lookup and that no commit happened
- tests/unit/api/services/test_guild_service_channel_refresh.py - Phase 3: 7 `get_discord_client` patches now unnamed; hollow getter assertions removed
- tests/unit/services/bot/commands/test_my_games.py - Phase 3: 6 `get_db_session` patches now take a `session_cm` MagicMock whose `__aenter__` yields the session; hollow getter assertions removed
- Phase 4 (Task 4.1): 37 hollow provider assertions removed across 16 more files (test_oauth2, test_list_games, test_handlers_clone, test_handlers_refresh_message, test_api_main, test_app, test_handlers_player_removal, test_error_handler, test_auth_routes, test_handlers_misc, test_tokens, test_calendar_export, test_handlers_game_reminder, test_handlers_game_updated, test_handlers_recurrence_confirmation); fakes are built above the patch (`config = MagicMock()`, `session_cm = MagicMock()` with `__aenter__`/`__aexit__`) and passed via `return_value=`; `alias.return_value.x` references in assertions now reference the fake. test_tokens now patches `config.get_api_config` directly instead of the whole module. The three `6882f984` naive-datetime tests keep their real checks
- tests/unit/services/bot/events/test_handlers_join_notification.py - Phase 4 (Task 4.2): 4 `get_db_session` markers and hollow assertions removed; unnamed patch with `return_value=mock_db`
- tests/unit/services/bot/formatters/test_game_message.py - Phase 4 (Task 4.2): 2 `get_config` markers and hollow assertions removed; unnamed patch with `return_value=`
- tests/unit/services/bot/formatters/test_game_message.py, tests/unit/services/api/routes/test_channels.py - Phase 5 (Task 5.1): removed the two hollow non-provider markers (`GameMessageFormatter()` class patch now unnamed with `return_value=mock_formatter`; `mock_result.scalar_one` assertion dropped)
- tests/unit/services/api/test_app.py, tests/unit/services/bot/auth/test_cache.py - Phase 5 (Task 5.1): getter-under-test assertions kept with `# assert-not-weak:` markers giving the reason (`test_cache` changed from bare `assert_called_once()` to `assert_called_once_with()`)
- tests/unit/services/api/test_api_main.py - Phase 5 (Task 5.1): `test_main_uses_config_values` drops the empty `get_api_config` assertion; `uvicorn.Config` kwarg checks kept
- pyproject.toml - Phase 5 (Task 5.2): removed `get_config`, `get_api_config`, `get_redis_client`, `get_db_session`, `get_role_service` and `get_discord_client` from `[tool.check-test-assertions] no-arg-methods`
- tests/unit/scripts/test_check_test_assertions.py - Phase 5 (Task 5.2): parametrized regression test that an empty `assert_called_once_with()` on each patched provider is a violation (failed 6/6 before the trim and passes after it)

### Removed

## Notes

- `uv run python scripts/check_test_assertions.py --all` output is identical before and after the Phase 2 fix (clean under the current allowlist), so the fix introduced no new violations.
- After Phase 4, `# assert-not-weak` markers in tests/ number 19 (a raw grep for `assert-not-weak` shows 20, because one hit is a string literal in test_check_test_assertions.py). Under the trimmed allowlist, `--all` reports only the three Task 5.1 sites.
- After Phase 5, `uv run python scripts/check_test_assertions.py --all` is clean under the trimmed allowlist and the marker count is 19. The Phase 5 commit adds 2 markers, so it needs `APPROVED_WEAK_ASSERTIONS=2`.
