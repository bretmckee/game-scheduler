# Bug Discovery: Promotion Detection Ignores Placeholder Participants

**Date:** December 24, 2025
**Found During:** E2E Test Task 5.3 Implementation (Waitlist Promotion → DM Notification)
**Status:** 🔴 Bug Confirmed - Promotion DMs not sent when placeholders occupy confirmed slots

## Bug Description

The waitlist promotion detection in `services/api/services/games.py::_detect_and_notify_promotions()` fails to correctly identify promoted users when placeholder participants occupy confirmed slots.

### Root Cause

The promotion detection filters to only "real" participants (with `user_id`) but compares against `max_players` which applies to ALL participants including placeholders:

```python
# services/api/services/games.py, lines 810-816
old_all_participants = [p for p in game.participants if p.user_id and p.user]  # ❌ Filters out placeholders
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]  # ❌ Uses max_players designed for ALL participants
    if p.user is not None
}
```

### Scenario That Fails

**Initial State:**
- Game created with `max_players=1`
- Participants: `["Reserved", "<@discord_user_id>"]`
- Visual representation: Reserved (confirmed), test_user (overflow)
- Discord message correctly shows: "Participants (1/1)" with test_user in "Overflow" section

**What Promotion Detection Sees:**
- `old_all_participants` = [test_user] (placeholder filtered out)
- `old_sorted_participants[0:1]` = [test_user]
- `old_overflow_ids` = {} (**empty!** - test_user is within the slice)

**Promotion Trigger:**
- Remove "Reserved" placeholder OR increase `max_players` to 2
- Expected: test_user promoted, DM sent
- **Actual: No promotion detected, no DM sent**

## Evidence

### Test Output
```
✓ Created game with placeholder + test user (overflow)
✓ Initial message shows 1/1 with Reserved, test user in overflow
✓ Discord message shows 2/2 with test user promoted
[TEST] Found 10 DMs for user 1444075864064004097
[TEST] Looking for promotion DM with game_title='E2E Promotion (max_players increase)...'
[TEST] Looking for phrases: 'A spot opened up', 'moved from the waitlist'
AssertionError: Test user should have received promotion DM. Recent DMs: [...]
```

### Visual Discord State vs API State

**Discord Correctly Shows (via bot formatters):**
- Initial: "Participants (1/1)" - Reserved confirmed, test_user overflow
- After promotion: "Participants (2/2)" - Both confirmed

**API Promotion Detection Sees:**
- Initial: 1 real participant (test_user) with max_players=1 → position 0/1 → NOT overflow
- After: No promotion detected

## Impact

**Affected Scenarios:**
1. ✅ Real user → real user promotion (works - both counted)
2. ❌ Placeholder → real user (from overflow) promotion (**fails** - placeholder not counted)
3. ❌ Any scenario where placeholders occupy confirmed slots (**fails**)

**User Experience:**
- Users promoted from waitlist when placeholder is removed: **No DM sent**
- Users promoted when max_players increased with placeholders present: **No DM sent**
- Discord message updates correctly, but user never notified of promotion

## Design Inconsistency

The codebase has two different interpretations of participant positioning:

### Bot Formatters (Correct)
```python
# services/bot/formatters/game_message.py
all_participants = sort_participants([p for p in game.participants])  # Includes ALL
confirmed_participants = all_participants[:game.max_players]
overflow_participants = all_participants[game.max_players:]
```

### Promotion Detection (Incorrect)
```python
# services/api/services/games.py
old_all_participants = [p for p in game.participants if p.user_id and p.user]  # Only real users
old_overflow_ids = { ... for p in old_sorted_participants[old_max_players:] ... }
```

## Proposed Fix

### Option 1: Include All Participants in Promotion Detection

```python
# In update_game(), line 810
old_all_participants = game.participants  # Include ALL participants
old_sorted_participants = participant_sorting.sort_participants(old_all_participants)
old_overflow_ids = {
    p.user.discord_id
    for p in old_sorted_participants[old_max_players:]
    if p.user is not None and p.user.discord_id  # Filter HERE, not earlier
}
```

**Pros:**
- Matches bot formatter logic
- Correctly identifies overflow position accounting for placeholders
- Minimal code change

**Cons:**
- Must handle None user carefully in set comprehension

### Option 2: Track Placeholder Count Separately

```python
# Calculate how many placeholders occupy confirmed slots
old_sorted = participant_sorting.sort_participants(game.participants)
old_confirmed = old_sorted[:old_max_players]
placeholder_count_in_confirmed = sum(1 for p in old_confirmed if p.user_id is None)

# Adjust threshold for real users
real_user_threshold = old_max_players - placeholder_count_in_confirmed
old_real_participants = [p for p in old_sorted if p.user_id and p.user]
old_overflow_ids = {
    p.user.discord_id
    for p in old_real_participants[real_user_threshold:]
    if p.user
}
```

**Pros:**
- More explicit about the logic
- Easier to understand intent

**Cons:**
- More complex
- Easy to get wrong

## Recommended Fix

**Implement the complete architectural solution directly.** Since the architectural fix is planned for immediate implementation, skip the intermediate workaround and proceed with the centralized participant partitioning utility.

**Create a centralized participant partitioning utility** in `shared/utils/participant_sorting.py`:

```python
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.participant import GameParticipant

@dataclass
class PartitionedParticipants:
    """Result of partitioning participants into confirmed and overflow."""
    all_sorted: list["GameParticipant"]
    confirmed: list["GameParticipant"]
    overflow: list["GameParticipant"]
    confirmed_real_user_ids: set[str]  # Discord IDs of confirmed real users
    overflow_real_user_ids: set[str]   # Discord IDs of overflow real users

def partition_participants(
    participants: list["GameParticipant"],
    max_players: int | None = None,
) -> PartitionedParticipants:
    """
    Sort and partition participants into confirmed and overflow groups.

    Args:
        participants: List of all participants (including placeholders)
        max_players: Maximum confirmed participants (defaults to 10 if None)

    Returns:
        PartitionedParticipants with sorted lists and ID sets
    """
    max_players = max_players or 10
    sorted_all = sort_participants(participants)
    confirmed = sorted_all[:max_players]
    overflow = sorted_all[max_players:]

    confirmed_ids = {
        p.user.discord_id
        for p in confirmed
        if p.user and p.user.discord_id
    }
    overflow_ids = {
        p.user.discord_id
        for p in overflow
        if p.user and p.user.discord_id
    }

    return PartitionedParticipants(
        all_sorted=sorted_all,
        confirmed=confirmed,
        overflow=overflow,
        confirmed_real_user_ids=confirmed_ids,
        overflow_real_user_ids=overflow_ids,
    )
```

**Benefits:**
1. **Single source of truth** for participant ordering logic
2. **Consistent handling** of placeholders across all services
3. **Pre-computed sets** for efficient Discord ID lookups
4. **Type-safe** with dataclass structure
5. **Future-proof** for enhancements like priority tiers, reserved slots, etc.
6. **Eliminates code duplication** across 6+ locations in the codebase

**Implementation Approach:**
1. Add `PartitionedParticipants` dataclass and `partition_participants()` to `shared/utils/participant_sorting.py`
2. Add comprehensive unit tests for the new utility
3. Update promotion detection in `services/api/services/games.py` to use new utility (fixes bug)
4. Verify E2E test passes with fixed promotion detection
5. Gradually migrate other locations (bot handlers, API routes) to use new utility
6. Remove duplicated sorting/slicing logic once migration complete

## Files Requiring Changes

### Architectural Fix (Complete Implementation)
- **New:** `shared/utils/participant_sorting.py` - Add `PartitionedParticipants` dataclass and `partition_participants()` function
- **Update:** `services/api/services/games.py::update_game()` (lines 810-816) - Use `partition_participants()`
- **Update:** `services/api/services/games.py::_detect_and_notify_promotions()` (lines 1201-1204) - Use `partition_participants()`
- **Update:** `services/bot/events/handlers.py` (multiple locations) - Gradually migrate to `partition_participants()`
- **Update:** `services/api/routes/games.py` - Use `partition_participants()`
- **Tests:** Add comprehensive unit tests for `partition_participants()` with edge cases
- **Tests:** `tests/services/api/services/test_games_promotion.py` - Add tests for placeholder + real user promotion scenarios

## Related Code

- Bot formatters: `services/bot/formatters/game_message.py::format_game_participants()`
- Participant sorting: `shared/utils/participant_sorting.py::sort_participants()`
- Promotion notification: `services/api/services/games.py::_publish_promotion_notification()`

## Test Cases Needed

1. ✅ Real user promoted when real user removed (existing - works)
2. ❌ Real user promoted when placeholder removed (NEW - currently fails)
3. ❌ Real user promoted when max_players increased with placeholder present (NEW - currently fails)
4. ✅ Real user promoted when max_players increased (existing - should work if no placeholders)

## Code Duplication Audit

**Current Locations with Sort + Slice Pattern:**
1. `services/bot/events/handlers.py::_handle_game_reminder()` (lines 393-403)
2. `services/bot/events/handlers.py::_handle_join_notification()` (lines 511-513)
3. `services/bot/events/handlers.py::_handle_game_cancelled()` (lines 858-862)
4. `services/api/services/games.py::update_game()` (lines 810-816)
5. `services/api/services/games.py::_detect_and_notify_promotions()` (lines 1201-1204)
6. `services/api/routes/games.py::download_calendar()` (line 566)

**Each location independently:**
- Filters participants (sometimes excluding placeholders, sometimes not)
- Calls `sort_participants()`
- Slices by `max_players` to get confirmed/overflow
- Extracts Discord IDs for lookups

**Risk:** Future enhancements (e.g., priority tiers, reserved slots) require updating 6+ locations

## E2E Test Status

- **Test File:** `tests/e2e/test_waitlist_promotion.py`
- **Status:** ✅ Test correctly written, exposing real bug
- **Blocked:** Waiting for bug fix to promotion detection logic

## Future Enhancement Considerations

The user mentioned "future enhancements" that make centralized participant ordering more important. Possible scenarios:

1. **Priority Tiers** - VIP/supporter/regular participant levels
2. **Reserved Slots** - Specific participant positions for roles/requirements
3. **Conditional Overflow** - Different overflow rules for different game types
4. **Late Join Windows** - Participants can join after game starts but before cutoff
5. **Alternate Lists** - Separate confirmed/alternate/declined lists

All of these would require modifying the participant partitioning logic in multiple places without a centralized utility.
