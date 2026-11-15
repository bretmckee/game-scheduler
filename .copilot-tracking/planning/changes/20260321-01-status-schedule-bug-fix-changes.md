<!-- markdownlint-disable-file -->

# Changes: Status Schedule Not Updated for IN_PROGRESS and COMPLETED Games

## Summary

Bug fix ensuring status schedule rows are preserved and updated correctly when IN_PROGRESS or
COMPLETED games are edited via the API, and that changing `expected_duration_minutes` triggers
a schedule update.

## Added

- `tests/integration/test_status_schedule_updates.py` — five xfail integration tests covering the three bug scenarios (duration change, IN_PROGRESS schedule deletion, COMPLETED schedule deletion)

## Modified

- `services/api/services/games.py` (`_update_remaining_fields`) — set `status_schedule_needs_update = True` when `expected_duration_minutes` is updated (Task 2.1)
- `services/api/services/games.py` (`_update_status_schedules`) — replaced bare `else` with `elif` branches for IN_PROGRESS and COMPLETED, preserving their forward schedules (Task 2.2)
- `services/api/services/games.py` — added `_ensure_archived_schedule_if_configured()` helper that upserts an ARCHIVED schedule when `archive_delay_seconds` is set (Task 2.3)

## Removed

- `tests/integration/test_status_schedule_updates.py` — removed all five `@pytest.mark.xfail` markers after confirming all tests pass (Task 3.1)
