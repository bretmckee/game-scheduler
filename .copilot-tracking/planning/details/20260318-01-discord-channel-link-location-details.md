<!-- markdownlint-disable-file -->

# Task Details: Discord Channel Link Resolution in Game Location

## Research Reference

**Source Research**: #file:../research/20260318-01-discord-channel-link-location-research.md

## Phase 1: TDD - Write Failing Unit Tests

### Task 1.1: Add unit tests for URL cases in `test_channel_resolver.py`

Add new test cases covering all URL detection scenarios before implementing. Tests MUST fail before implementation.

- **Files**:
  - `tests/unit/services/api/services/test_channel_resolver.py` - add URL test cases
- **Success**:
  - Tests are discovered by pytest and fail (not pass) with unimplemented behavior
  - Covers: valid same-guild URL → `<#id>` substitution, wrong-guild URL → unchanged (no error), valid guild + channel not found → `not_found` error, valid guild + non-text channel → `not_found` error, discord URL coexisting with `#` reference in same string
- **Research References**:
  - #file:../research/20260318-01-discord-channel-link-location-research.md (Lines 1-55) - existing test patterns and fixture structure
- **Dependencies**:
  - None (test file already exists)

## Phase 2: Implement URL Resolution in Backend

### Task 2.1: Refactor channel fetch and add URL regex to `channel_resolver.py`

Add `_discord_channel_url_pattern` regex to `ChannelResolver.__init__` and refactor `resolve_channel_mentions` to fetch channels once unconditionally before both passes.

- **Files**:
  - `services/api/services/channel_resolver.py` - add regex, refactor fetch
- **Success**:
  - `_discord_channel_url_pattern` compiles at init time
  - Channel list fetched once before both URL and `#` passes
  - All existing tests still pass
- **Research References**:
  - #file:../research/20260318-01-discord-channel-link-location-research.md (Lines 75-115) - channel dict schema and recommended approach
- **Dependencies**:
  - Task 1.1 (failing tests must exist)

### Task 2.2: Add URL resolution loop to `resolve_channel_mentions`

Add URL detection pass before the existing `#channel-name` pass with the three-branch logic described in research.

- **Files**:
  - `services/api/services/channel_resolver.py` - add URL detection loop
- **Success**:
  - Valid same-guild URL in location replaced with `<#channel_id>`
  - Wrong-guild URL left unchanged, no error generated
  - Valid guild + channel not found → error with `type="not_found"`, `reason="This link is not a valid text channel in this server"`, `suggestions=[]`
  - All Phase 1 unit tests now pass (green)
- **Research References**:
  - #file:../research/20260318-01-discord-channel-link-location-research.md (Lines 75-115) - URL detection logic table
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Update Frontend Alert Title

### Task 3.1: Update `AlertTitle` in `ChannelValidationErrors.tsx`

Change the hardcoded title from "Could not resolve some #channel mentions" to "Location contains an invalid channel reference".

- **Files**:
  - `frontend/src/components/ChannelValidationErrors.tsx` - change AlertTitle text
- **Success**:
  - AlertTitle reads "Location contains an invalid channel reference"
  - No other component logic changed
- **Research References**:
  - #file:../research/20260318-01-discord-channel-link-location-research.md (Lines 95-105) - frontend change specification
- **Dependencies**:
  - Phase 2 completion (logical dependency only; can be done in parallel)

## Dependencies

- Python 3.13+, pytest, pytest-asyncio
- No new third-party libraries required

## Success Criteria

- Valid same-guild discord.com channel URL in location field → stored as `<#channel_id>`
- Wrong-guild discord.com URL → game created as-is (URL unchanged, no error)
- Valid guild + channel not found → HTTP 422 with `not_found` error blocking game creation
- Plain non-discord URLs → unchanged, no error
- Existing `#channel-name` behavior unchanged
- All unit tests pass; existing tests unmodified
- Frontend AlertTitle updated
