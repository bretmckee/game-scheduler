<!-- markdownlint-disable-file -->

# Task Details: Game Creation UI Consolidation

## Research Reference

**Source Research**: #file:../research/20251218-game-creation-ui-consolidation-research.md

## Phase 1: Routing Updates

### Task 1.1: Update App.tsx route configuration

Change the game creation route from guild-specific to unified path.

- **Files**:
  - [App.tsx](App.tsx) - Update route configuration (line 55)
- **Success**:
  - Route changed from `/guilds/:guildId/games/new` to `/games/new`
  - CreateGame component still renders correctly
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 451-453) - Current route configuration
- **Dependencies**:
  - None

### Task 1.2: Update MyGames navigation logic

Simplify navigation from "Create Game" button to use unified route.

- **Files**:
  - [frontend/src/pages/MyGames.tsx](frontend/src/pages/MyGames.tsx) - Remove conditional logic (lines 125-132)
- **Success**:
  - "Create Game" button navigates to `/games/new`
  - Server selection dialog usage removed
  - Simplified navigation flow preserved
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 83-95) - Current navigation implementation
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 585-586) - Simplification guidance
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: CreateGame Component Refactoring

### Task 2.1: Remove guildId URL parameter dependency

Remove URL parameter extraction and guild-specific routing logic.

- **Files**:
  - [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Remove useParams hook usage
- **Success**:
  - guildId no longer extracted from URL params
  - Component initializes without guildId dependency
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 18-24) - Current implementation
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 564-565) - Refactoring guidance
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Add guild selection state and loading logic

Implement state management for guilds list and selected guild.

- **Files**:
  - [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Add useState for guilds and selectedGuild
- **Success**:
  - Guilds loaded on component mount
  - selectedGuild state tracks user's choice
  - Auto-selection for single guild scenario
  - Template loading triggered by guild selection
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 83-95) - MyGames pattern for guild loading
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 566-568) - Implementation requirements
- **Dependencies**:
  - Task 2.1 completion
  - `/api/v1/guilds` endpoint availability

### Task 2.3: Implement server dropdown with auto-selection

Add server selection dropdown at top of form with smart auto-selection.

- **Files**:
  - [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Add server FormControl before template dropdown
- **Success**:
  - Server dropdown rendered with available guilds
  - Single guild users see pre-selected server (dropdown hidden or disabled)
  - Guild selection triggers template loading
  - Template dropdown appears after guild selection
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 172-195) - Template dropdown pattern
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 454-469) - MUI FormControl pattern
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 569-570) - Auto-selection requirements
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Apply GameDetails typography patterns

Update form field labels and headings to match GameDetails styling.

- **Files**:
  - [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Update Typography components
- **Success**:
  - "Game Details" section header uses Typography h6 variant
  - Field labels match GameDetails typography patterns
  - Consistent spacing applied (mb: 2 for sections)
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 260-351) - GameDetails layout patterns
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 571-572) - Typography requirements
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: GameForm Styling Updates

### Task 3.1: Update field typography to match GameDetails

Apply consistent typography sizing to form field labels.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Update TextField and Typography components
- **Success**:
  - Primary field labels use body1 variant with fontSize '1.1rem'
  - Helper text and secondary info use body2 variant
  - Typography consistency across all form fields
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 70-71) - Typography standards from December 2025 updates
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 576-577) - Styling requirements
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 590-591) - Primary field typography specs
- **Dependencies**:
  - None (can run in parallel with Phase 2)

### Task 3.2: Implement horizontal layout for Duration/Reminders

Change Duration and Reminders fields to horizontal flex layout.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Wrap Duration/Reminders in Box with flex
- **Success**:
  - Duration and Reminders fields displayed side-by-side
  - Box uses `display: 'flex'`, `gap: 3`, `flexWrap: 'wrap'`
  - Layout matches GameDetails pattern
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 304-313) - GameDetails horizontal layout example
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 578-579) - Layout requirements
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Update channel display format

Change channel display to show "# channel_name" format matching Discord convention.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Update channel Select MenuItem rendering
- **Success**:
  - Channel options display as "# channel_name"
  - Selected channel shows "# channel_name" format
  - Matches Discord visual convention
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 580-581) - Channel display requirements
- **Dependencies**:
  - None

### Task 3.4: Add location context display

Add read-only field showing "guild_name # channel_name" for server context.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Add Typography or TextField for location context
- **Success**:
  - Location context displays as "guild_name # channel_name"
  - Field is read-only or display-only
  - Positioned after "Where" field
  - Typography uses body1 variant at fontSize 1.1rem
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 319-322) - GameDetails location display
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 372-373) - guild_name field addition
- **Dependencies**:
  - Guild data available in GameForm props

### Task 3.5: Style signup instructions field

Update signup instructions field styling to match GameDetails boxed format.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Add helper text or styling note for signup instructions
- **Success**:
  - Signup instructions field includes note about host-only visibility
  - Optional: Preview box showing how it will appear (boxed with info.light background)
  - Field styling consistent with GameDetails display
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 325-332) - GameDetails signup instructions display
- **Dependencies**:
  - Task 3.4 completion

## Phase 4: Typography and Spacing Consistency

### Task 4.1: Standardize primary field typography

Ensure all primary form fields use consistent typography.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Audit and update all TextField labels
- **Success**:
  - Title, Description, When, Where, Max Players use body1 at 1.1rem
  - Duration, Reminders use body2
  - Section headers use h6 variant
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 590-593) - Typography specifications
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Apply consistent spacing patterns

Standardize margin and gap spacing across all form sections.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Update Box and Typography sx props
- **Success**:
  - Field spacing uses mb: 1 for tight spacing
  - Section breaks use mb: 2
  - Horizontal groups use gap: 2 (compact) or gap: 3 (standard)
  - Spacing matches GameDetails patterns
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 592-593) - Spacing specifications
- **Dependencies**:
  - Task 4.1 completion

## Phase 5: Testing Updates

### Task 5.1: Update CreateGame component tests

Modify tests to work with new unified routing.

- **Files**:
  - [frontend/src/pages/CreateGame.test.tsx](frontend/src/pages/CreateGame.test.tsx) - Update test setup and expectations
- **Success**:
  - Tests render CreateGame without guildId param
  - Server dropdown rendering tested
  - Auto-selection behavior tested
  - Template loading after guild selection tested
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 597-599) - Test update requirements
- **Dependencies**:
  - Phase 2 completion

### Task 5.2: Update MyGames component tests

Modify tests for simplified navigation logic.

- **Files**:
  - [frontend/src/pages/MyGames.test.tsx](frontend/src/pages/MyGames.test.tsx) - Update navigation test assertions
- **Success**:
  - Create game button navigation tested
  - Navigation to `/games/new` verified
  - Server selection dialog tests removed
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 597-599) - Test update requirements
- **Dependencies**:
  - Phase 1 Task 1.2 completion

### Task 5.3: Add visual consistency tests

Add tests to verify typography and layout match GameCard/GameDetails.

- **Files**:
  - [frontend/src/components/GameForm.test.tsx](frontend/src/components/GameForm.test.tsx) - Add style assertion tests
- **Success**:
  - Typography variants verified
  - Spacing patterns tested
  - Horizontal layouts verified
  - Channel format tested
- **Research References**:
  - #file:../research/20251218-game-creation-ui-consolidation-research.md (Lines 599) - Visual consistency testing
- **Dependencies**:
  - Phase 3 and Phase 4 completion

## Dependencies

- React Router v6
- Material-UI (MUI) v5+
- TypeScript 5.x
- Existing guilds and templates API endpoints

## Success Criteria

- All phases completed with passing tests
- Create game form visually consistent with GameCard and GameDetails
- Unified `/games/new` routing functional
- Auto-selection behavior preserved
- Form validation and submission unchanged
- No regressions in existing functionality
