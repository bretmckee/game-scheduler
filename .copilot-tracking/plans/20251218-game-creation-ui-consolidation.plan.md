---
applyTo: '.copilot-tracking/changes/20251218-game-creation-ui-consolidation-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Game Creation UI Consolidation

## Overview

Consolidate game creation UI to align with GameCard and GameDetails visual patterns, implementing consistent typography, horizontal layouts, and simplified routing from guild-specific to unified `/games/new` route.

## Objectives

- Align create game page layout with GameCard and GameDetails visual hierarchy
- Implement consistent typography (body1 at 1.1rem for primary, body2 for secondary)
- Adopt horizontal flex layouts for Duration/Reminders matching GameDetails
- Simplify routing from `/guilds/:guildId/games/new` to `/games/new`
- Maintain auto-selection behavior for single server/template scenarios
- Show server context as "guild_name # channel_name" format throughout

## Research Summary

### Project Files

- [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Current implementation with guild-specific routing
- [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Pure form component needing styling updates
- [frontend/src/components/GameCard.tsx](frontend/src/components/GameCard.tsx) - Summary card with target visual patterns
- [frontend/src/pages/GameDetails.tsx](frontend/src/pages/GameDetails.tsx) - Details page with target typography and layout
- [frontend/src/pages/MyGames.tsx](frontend/src/pages/MyGames.tsx) - Entry point requiring navigation simplification
- [App.tsx](App.tsx) - Route configuration requiring update

### External References

- #file:../research/20251218-game-creation-ui-consolidation-research.md - Comprehensive UI consolidation research
- #file:../../.github/instructions/reactjs.instructions.md - React component composition standards
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript guidelines

### Standards References

- MUI design system for FormControl, Typography, and layout components
- React Router v6 for navigation patterns
- Functional components with hooks for state management

## Implementation Checklist

### [x] Phase 1: Routing Updates

- [x] Task 1.1: Update App.tsx route configuration
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 17-26)

- [x] Task 1.2: Update MyGames navigation logic
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 28-39)

### [x] Phase 2: CreateGame Component Refactoring

- [x] Task 2.1: Remove guildId URL parameter dependency
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 43-52)

- [x] Task 2.2: Add guild selection state and loading logic
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 54-67)

- [x] Task 2.3: Implement server dropdown with auto-selection
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 69-82)

- [x] Task 2.4: Apply GameDetails typography patterns
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 84-95)

### [x] Phase 3: GameForm Styling Updates

- [x] Task 3.1: Update field typography to match GameDetails
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 99-111)

- [x] Task 3.2: Implement horizontal layout for Duration/Reminders
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 113-124)

- [x] Task 3.3: Update channel display format
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 126-135)

- [x] Task 3.4: Add location context display
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 137-148)

- [x] Task 3.5: Style signup instructions field
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 150-159)

### [x] Phase 4: Typography and Spacing Consistency

- [x] Task 4.1: Standardize primary field typography
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 163-172)

- [x] Task 4.2: Apply consistent spacing patterns
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 174-183)

### [x] Phase 5: Testing Updates

- [x] Task 5.1: Update CreateGame component tests
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 187-197)

- [x] Task 5.2: Update MyGames component tests
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 199-208)

- [ ] Task 5.3: Add visual consistency tests
  - Details: .copilot-tracking/details/20251218-game-creation-ui-consolidation-details.md (Lines 210-219)

## Dependencies

- React Router v6 for navigation
- Material-UI (MUI) components: FormControl, Select, TextField, Typography, Box, Avatar
- Existing API endpoints: `/api/v1/guilds`, `/api/v1/guilds/{guildId}/templates`
- TypeScript 5.x with ES2022 target

## Success Criteria

- User can access game creation from `/games/new` unified route
- Server dropdown appears and auto-selects for single-server users
- Template dropdown loads after server selection with auto-selection
- Create game form matches GameCard and GameDetails typography (body1 at 1.1rem)
- Duration/Reminders displayed horizontally with gap: 3 like GameDetails
- Channel displays as "# channel_name" format
- Location context shows "guild_name # channel_name"
- All spacing patterns match GameDetails (mb: 1, mb: 2, gap: 2/3)
- Form validation and submission functionality preserved
- All existing tests pass with updated routing
- No loss of existing functionality
