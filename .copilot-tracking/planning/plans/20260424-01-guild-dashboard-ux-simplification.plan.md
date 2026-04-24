---
applyTo: '.copilot-tracking/changes/20260424-01-guild-dashboard-ux-simplification-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Guild Dashboard UX Simplification

## Overview

Simplify GuildDashboard by removing its fake tab pattern, embedding BrowseGames directly, adding a "Create a Game" header button, and fixing the broken `/guilds/:guildId/games/new` route with guild pre-selection in CreateGame.

## Objectives

- Remove the non-functional tab/overview structure from GuildDashboard
- Embed BrowseGames as the immediate page body when a guild is selected
- Add a "Create a Game" button (conditional on permissions) to the GuildDashboard header
- Fix the broken `/guilds/:guildId/games/new` route in App.tsx
- Add optional `guildId` route param support to CreateGame for guild pre-selection

## Research Summary

### Project Files

- `frontend/src/pages/GuildDashboard.tsx` - current tab structure with broken fake navigation
- `frontend/src/pages/BrowseGames.tsx` - self-contained games list, already uses `:guildId` param
- `frontend/src/pages/CreateGame.tsx` - no route param support; uses BrowserRouter in tests
- `frontend/src/App.tsx` - missing `/guilds/:guildId/games/new` route
- `frontend/src/pages/__tests__/GuildDashboard.test.tsx` - tests for current tab structure
- `frontend/src/pages/__tests__/CreateGame.test.tsx` - uses BrowserRouter; needs MemoryRouter

### External References

- #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md - full analysis and implementation guidance

### Standards References

- #file:../../.github/instructions/test-driven-development.instructions.md - TDD RED/GREEN/REFACTOR workflow
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript conventions
- #file:../../.github/instructions/reactjs.instructions.md - React/MUI component patterns

## Implementation Checklist

### [ ] Phase 1: RED - Write Failing Tests

- [ ] Task 1.1: Write failing tests for GuildDashboard restructure
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 11-28)

- [ ] Task 1.2: Write failing tests for CreateGame guildId param
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 29-47)

### [ ] Phase 2: GREEN - Implement Production Code Changes

- [ ] Task 2.1: Refactor GuildDashboard.tsx
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 48-75)

- [ ] Task 2.2: Remove standalone heading from BrowseGames.tsx
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 76-89)

- [ ] Task 2.3: Update App.tsx routes
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 90-107)

- [ ] Task 2.4: Add guildId param support to CreateGame.tsx
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 108-139)

### [ ] Phase 3: REFACTOR - Remove xfail Markers and Verify

- [ ] Task 3.1: Remove test.fails markers and confirm full test pass
  - Details: .copilot-tracking/planning/details/20260424-01-guild-dashboard-ux-simplification-details.md (Lines 140-168)

## Dependencies

- No external dependencies; all changes within `frontend/src/`

## Success Criteria

- Guild dashboard immediately shows the games list on navigation (no tab click required)
- Guild name visible as the page heading; no duplicate heading from embedded BrowseGames
- "Create a Game" button navigates to CreateGame with the guild pre-selected
- Server picker suppressed in CreateGame when `guildId` is in the URL
- All existing and new frontend tests pass
