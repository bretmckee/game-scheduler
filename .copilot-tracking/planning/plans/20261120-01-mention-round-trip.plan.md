---
applyTo: '.copilot-tracking/planning/changes/20261120-01-mention-round-trip-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Lossless @mention / #channel Round-Trip in Game Text Fields

## Overview

Make user and channel mentions in game description / signup instructions survive any number of create/edit/clone saves. Do this by returning ID-carrying `<@id|label>` / `<#id|label>` tokens, collapsing them on input, preferring exact matches, and recording IDs on suggestion picks.

## Objectives

- Re-saving an unedited game leaves stored description/signup text byte-identical (fixes 2b)
- Picking a "Did you mean" suggestion ends the prompt loop on the next save (fixes 2a)
- A single exact name match among several prefix matches resolves without prompting
- Hosts never see raw IDs. Departed members show as a distinct "unknown member" chip in text and participant lists
- No names are persisted, and stored text and the Discord embed stay plain `<@id>` / `<#id>`

## Research Summary

### Project Files

- services/api/routes/games.py - `_render_text_fields`, `_build_game_response`, participant/host builders
- services/api/services/participant_resolver.py - mention scan pattern, `_resolve_user_friendly_mention`
- services/api/services/channel_resolver.py - channel scan pattern, current token rendering
- services/api/services/display_names.py - "Unknown User" fallbacks; new `resolve_member_refs`
- services/api/services/games.py - create/update free-text resolution paths
- frontend/src/components/GameForm.tsx - editor init, suggestion-click handlers, participant rows
- frontend/src/components/GameCard.tsx, frontend/src/pages/GameDetails.tsx - read-only renderers
- frontend/src/pages/EditGame.tsx, CloneGame.tsx, CreateGame.tsx - payload builders

### External References

- .copilot-tracking/research/20261120-01-mention-round-trip-research.md - root causes, token format, approach, testing matrix
- Source: https://docs.discord.com/developers/resources/user - name length/charset rules (no empty names; labels may contain `>`)

### Standards References

- .github/instructions/test-driven-development.instructions.md - RED/GREEN phase structure
- .github/instructions/python.instructions.md, unit-tests.instructions.md - Python code and tests
- .github/instructions/reactjs.instructions.md, typescript-5-es2022.instructions.md - frontend
- .github/instructions/integration-tests.instructions.md, test-execution.instructions.md - integration/e2e runs

## Implementation Checklist

Phases 1-6 tolerate tokens without the server emitting them. Phase 7 switches rendering last, so every phase commits cleanly.

### [x] Phase 1: Exact-match preference in mention resolution (server)

- [x] Task 1.1: RED — xfail tests for the exact-match rule
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 17-40)

- [x] Task 1.2: GREEN — implement exact-match filter
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 41-50)

### [x] Phase 2: Collapse `<@id|label>` / `<#id|label>` on input (server)

- [x] Task 2.1: RED — stub `collapse_mention_tokens` and xfail tests
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 53-72)

- [x] Task 2.2: GREEN — implement and wire into create/update paths
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 73-89)

### [x] Phase 3: `MemberRef` + `MemberChip` for participants (frontend)

- [x] Task 3.1: RED — `MemberRef` type, adapter, `MemberChip` stub + tests
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 92-108)

- [x] Task 3.2: GREEN — implement and render participants through `MemberChip`
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 109-120)

### [ ] Phase 4: Departed participants return `display_name: null` (server)

- [ ] Task 4.1: RED — `resolve_member_refs` stub + xfail tests
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 123-134)

- [ ] Task 4.2: GREEN — implement and switch the participant/host path
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 135-146)

### [ ] Phase 5: `mentionTokens` util + `MentionText` read-only rendering (frontend)

- [ ] Task 5.1: RED — `mentionTokens.ts` stubs + failing tests
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 149-161)

- [ ] Task 5.2: GREEN — implement util
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 162-168)

- [ ] Task 5.3: `MentionText` component and read-only views
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 169-179)

### [ ] Phase 6: Editor wiring + suggestion-click map (frontend)

- [ ] Task 6.1: GameForm editor state via `toEditorText` / `fromEditorText`
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 182-190)

- [ ] Task 6.2: Suggestion click inserts display name and records the ID
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 191-199)

### [ ] Phase 7: Switch server rendering to token form + integration round-trip (server)

- [ ] Task 7.1: RED — xfail token-render tests
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 202-209)

- [ ] Task 7.2: GREEN — implement token rendering
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 210-218)

- [ ] Task 7.3: Integration round-trip matrix
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 219-227)

### [ ] Phase 8: E2E regressions

- [ ] Task 8.1: E2E tests for 2a and 2b
  - Details: .copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md (Lines 230-238)

## Dependencies

- Redis member projection (`get_member`, `search_members_by_prefix`) and guild channel list (`get_guild_channels_safe`)
- uv / pytest / mypy; Node + Vitest + React Testing Library; MUI
- `scripts/run-integration-tests.sh`, `scripts/run-e2e-tests.sh`

## Success Criteria

- The reported Kallisti and Xanthias scenarios save successfully after at most one disambiguation
- Unedited re-save gives byte-identical stored text, and the Discord embed keeps `<@id>`
- Departed members render as the "unknown member" chip (text and participants), never the text "Unknown User"
- All gates green at every phase boundary: `uv run pytest tests/unit`, `uv run mypy shared/ services/`, frontend build + test, integration (Phase 7) and e2e (Phase 8)
