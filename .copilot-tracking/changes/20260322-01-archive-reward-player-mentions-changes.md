<!-- markdownlint-disable-file -->

# Changes: Archive Player @mentions for Reward Games

## Overview

Tracks implementation progress for the feature that @mentions confirmed players in Discord
archive posts when a game has rewards set.

---

## Added

<!-- Newly created files -->

## Modified

### Phase 1: Write Failing Tests (TDD RED Phase)

- `tests/unit/bot/events/test_handlers_misc.py` — added four `@pytest.mark.xfail(strict=True)` unit tests covering: confirmed player mentioned in archive content, role-mention content ignored, no content when rewards not set, and no content when no confirmed players
- `tests/unit/services/bot/events/test_handlers.py` — marked `test_archive_game_announcement_posts_to_archive_channel` as `@pytest.mark.xfail` so the suite stays green when the production `content` assertion changes
- `tests/e2e/test_game_rewards.py` — added `@pytest.mark.xfail(strict=True)`, `discord_user_id` fixture, `initial_participants` to POST payload, and `assert f"<@{discord_user_id}>" in archive_message.content` assertion to `test_save_and_archive_archives_game_within_seconds`

### Phase 2: Implement Production Code (TDD GREEN Phase)

- `services/bot/events/handlers.py` — replaced role-mention content passthrough with player @mention logic in `_archive_game_announcement`: discards `_content` from `_create_game_announcement`, builds `content` from sorted `confirmed_real_user_ids` when `game.rewards` is set, falls back to `content=None` when rewards not set or no confirmed players

### Phase 3: Clean Up and Verify (TDD REFACTOR Phase)

- `tests/unit/bot/events/test_handlers_misc.py` — removed all four `@pytest.mark.xfail(strict=True)` decorators; all four tests now pass
- `tests/unit/services/bot/events/test_handlers.py` — removed `@pytest.mark.xfail` from `test_archive_game_announcement_posts_to_archive_channel` and updated assertion from `content="content"` to `content=None`
- `tests/e2e/test_game_rewards.py` — removed `@pytest.mark.xfail(strict=True)` from `test_save_and_archive_archives_game_within_seconds`

## Removed

<!-- Deleted files or removed sections -->
