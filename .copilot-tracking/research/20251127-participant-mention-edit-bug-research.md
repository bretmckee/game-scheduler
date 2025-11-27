<!-- markdownlint-disable-file -->

# Task Research Notes: Participant @mention Edit Bug

## Research Executed

### File Analysis

- `frontend/src/components/GameForm.tsx` (lines 160-170)
  - When loading participants for editing, converts discord_id to `<@discord_id>` format
  - This is Discord's internal mention format, not the user-friendly `@username` format
- `frontend/src/pages/EditGame.tsx` (lines 98-102)
  - Submits participant mentions directly from form without transformation
- `services/api/services/participant_resolver.py` (lines 45-170)
  - Only recognizes mentions starting with `@` (line 72)
  - Treats anything not starting with `@` as placeholder text (line 157-164)
- `services/api/services/games.py` (lines 415-454)
  - In `update_game`, removes all pre-filled participants and re-adds from form data
  - Calls `participant_resolver.resolve_initial_participants` with mentions from form

### Code Search Results

- Searched for mention format handling in frontend
  - Found `<@${p.discord_id}>` format used in GameForm.tsx line 160
- Searched for participant resolution in backend
  - Found `input_text.startswith("@")` check in participant_resolver.py line 72

## Key Discoveries

### Problem Root Cause

When a game is edited, the frontend populates the participant list with this logic:

```tsx
// GameForm.tsx line 160
mention: p.display_name || (p.discord_id ? `<@${p.discord_id}>` : ''),
```

For Discord users added by the host:

1. `p.display_name` is `null` (only placeholders have display_name)
2. `p.discord_id` exists (e.g., "123456789012345678")
3. The form populates with: `<@123456789012345678>`

When this is saved, the backend receives `<@123456789012345678>` and processes it:

```python
# participant_resolver.py lines 72-73
if input_text.startswith("@"):
    # Discord mention - validate and resolve
```

Since `<@123456789012345678>` does NOT start with `@`, it's treated as a placeholder string instead of a Discord user.

### Discord Mention Formats

- **User-friendly format**: `@username` - Used for searching guild members
- **Discord internal format**: `<@123456789012345678>` - Used in Discord messages
- **Backend expects**: `@username` for resolution
- **Frontend generates**: `<@discord_id>` when editing

### Current Participant Data Structure

From API response (built in `_build_game_response`), participants have:

- `discord_id`: Discord snowflake ID (string) - set for Discord users, null for placeholders
- `display_name`: User's current display name in guild - resolved from Discord API for Discord users, set for placeholders
- `pre_filled_position`: Position in list (null for joined users)

**Key Issue**: The API resolves `display_name` from Discord for display purposes, but this display name cannot be used as a mention input because:

1. Display names may contain spaces and special characters
2. Multiple users could have the same display name
3. The participant resolver expects `@username` format, not display names

### Backend Resolution Logic

```python
# participant_resolver.py
if input_text.startswith("@"):
    # Search guild members by username/display name
    mention_text = input_text[1:].lower()
    members = await self._search_guild_members(...)
else:
    # Treat as placeholder string
    valid_participants.append({
        "type": "placeholder",
        "display_name": input_text,
        "original_input": input_text,
    })
```

## Recommended Approach

### Solution 3: Accept Discord Mention Format in Backend (RECOMMENDED)

Modify participant_resolver to handle both `@username` and `<@discord_id>` formats.

**Why this is the best solution**:

1. **No database schema changes** - Quick to implement, no migration needed
2. **Works with current frontend** - No frontend changes required
3. **Actually more reliable** - Using discord_id is more accurate than username
   - Usernames can change, but discord_id is permanent
   - No ambiguity with similar usernames
   - No need to search and match - direct lookup by ID
4. **Better UX** - Frontend can display the resolved display name (already being fetched)

**Implementation**:

1. Update `participant_resolver.resolve_initial_participants` to detect `<@discord_id>` pattern
2. Extract discord_id from `<@discord_id>` format using regex
3. Validate the user exists in the guild (optional - can skip for speed)
4. Return discord user participant directly without search

**Code Changes**:

```python
# In participant_resolver.py, add pattern matching:
if input_text.startswith("<@") and input_text.endswith(">"):
    # Discord mention format: <@123456789012345678>
    discord_id = input_text[2:-1]  # Remove <@ and >
    if discord_id.isdigit():
        valid_participants.append({
            "type": "discord",
            "discord_id": discord_id,
            "original_input": input_text,
        })
        continue
elif input_text.startswith("@"):
    # User-friendly format - search by username
    # ... existing code ...
```

**Benefits**:

- Quick fix without database changes
- Works with current frontend code
- More reliable than username-based resolution
- Preserves user identity across username changes
- No additional API calls needed

**Considerations**:

- Frontend still shows `<@discord_id>` in edit form (not user-friendly)
- Should be combined with frontend improvement to show display names

### Solution 1: Store Original Mention with Participant

Store the original `@username` used during creation.

**Implementation**:

1. Add `original_mention` field to GameParticipant model
2. Store the `@username` used during initial creation
3. Return `original_mention` in API response
4. Frontend displays `original_mention` instead of generating `<@discord_id>`

**Benefits**:

- Preserves original user input
- Shows human-readable username in edit form
- Consistent mention format across create/edit

**Considerations**:

- Requires database migration to add field
- Username may become stale if user changes their Discord username
- Need to backfill field for existing participants
- More complex implementation

### Solution 2: Fetch Username in Frontend During Edit

Resolve discord_id to username when loading edit form.

**Implementation**:

1. Add API endpoint to fetch user details by discord_id
2. Call endpoint when loading GameForm in edit mode
3. Convert `discord_id` to `@username` before displaying
4. Submit as `@username` to maintain compatibility

**Benefits**:

- No database schema changes
- Shows current username (handles renames)
- Clean separation of concerns

**Considerations**:

- Additional API calls when loading edit form (one per participant)
- Potential rate limit concerns for games with many participants
- More complex frontend logic
- Network latency when loading edit form

## Implementation Guidance

### ✅ IMPLEMENTED: Phase 1 - Backend Fix

**Status**: Complete

**Changes Made**:

1. ✅ Updated `participant_resolver.py` to handle `<@discord_id>` format
2. ✅ Added regex pattern to extract discord_id from Discord mention format
3. ✅ Validation ensures extracted ID is numeric and 17-20 characters
4. ✅ Added comprehensive test coverage for both formats
5. ✅ Created integration tests for edit flow

**Files Modified**:

- `services/api/services/participant_resolver.py`

  - Added `import re` for regex pattern matching
  - Updated `resolve_initial_participants()` to detect and handle `<@discord_id>` format
  - Pattern: `^<@(\d{17,20})>$` matches valid Discord IDs

- `tests/services/api/services/test_participant_resolver.py`

  - Added `test_resolve_discord_mention_format()` - Tests `<@discord_id>` recognition
  - Added `test_resolve_mixed_mention_formats()` - Tests both formats together
  - Added `test_reject_invalid_discord_mention_format()` - Tests edge cases
  - Added `test_discord_mention_format_with_whitespace()` - Tests whitespace handling

- `tests/services/api/services/test_games_edit_participants.py` (new file)
  - Added `test_update_game_with_discord_mention_format()` - Integration test
  - Added `test_update_game_preserves_discord_users_not_placeholders()` - Regression test

**Test Results**:

- ✅ All 182 API tests passing
- ✅ 15 participant resolver tests passing
- ✅ 2 new integration tests passing
- ✅ No regressions in existing functionality

**Success Criteria Met**:

- ✅ Backend accepts both `@username` and `<@discord_id>` formats
- ✅ Discord users remain Discord users after game edit
- ✅ No regression in create flow
- ✅ Existing games can be edited without data loss

### Phase 2: Frontend Improvement (Follow-up - Not Implemented)

**Recommendation**: Store original mention (Solution 1) as a future enhancement for better UX.

**Why defer this**:

- Current fix resolves the critical bug
- Frontend still shows `<@discord_id>` but it works correctly
- Schema changes require more planning and migration
- Can be addressed in future iteration

**Future Enhancement**:

- Add `original_mention` field to GameParticipant model
- Store `@username` during creation for human-readable display
- Update frontend to show stored mention instead of generating `<@discord_id>`
