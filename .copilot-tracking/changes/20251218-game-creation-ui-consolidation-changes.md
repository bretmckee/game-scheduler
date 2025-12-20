<!-- markdownlint-disable-file -->

# Release Changes: Game Creation UI Consolidation

**Related Plan**: 20251218-game-creation-ui-consolidation-plan.instructions.md
**Implementation Date**: 2025-12-20

## Summary

Consolidating game creation UI to align with GameCard and GameDetails visual patterns, implementing consistent typography, horizontal layouts, and simplified routing from guild-specific to unified `/games/new` route.

## Changes

### Added

- frontend/src/pages/__tests__/CreateGame.test.tsx - NEW FILE: Created comprehensive test suite with 8 tests covering loading state, server dropdown rendering with multiple guilds, auto-selection of single server with automatic template loading, template loading on server selection, warning display when no servers are available, template description display, GameForm rendering after template selection, and server selection change behavior with template refresh

### Modified

- frontend/src/App.tsx - Changed game creation route from `/guilds/:guildId/games/new` to `/games/new`
- frontend/src/pages/MyGames.tsx - Simplified navigation to use unified `/games/new` route and removed ServerSelectionDialog dependency
- frontend/src/pages/CreateGame.tsx - Removed guildId URL parameter dependency, added guild selection state management, implemented guild/template loading logic with auto-selection, added server dropdown with conditional rendering, applied GameDetails typography patterns with h4 page title and h6 section header, passed guildName prop to GameForm, added bot manager permission check, and passed canChangeChannel prop to GameForm
- frontend/src/pages/EditGame.tsx - Added guildName prop to GameForm for Discord location context display consistency
- frontend/src/components/GameForm.tsx - Updated field typography to match GameDetails (body1 at 1.1rem for primary fields), implemented horizontal layout for Duration/Reminders with gap: 3, updated channel display to show "# channel_name" format, added Discord location context display showing "guild_name # channel_name", updated signup instructions helper text for host-only visibility, applied consistent spacing patterns (mb: 1 for tight spacing, mb: 2 for section breaks), added guildName prop for location context, added canChangeChannel prop to conditionally show channel selection (bot managers) or read-only channel display (normal hosts)
- frontend/src/utils/permissions.ts - Added canUserManageBotSettings function to check bot manager permissions via guild config endpoint
- frontend/src/pages/__tests__/MyGames.test.tsx - Updated tests to expect new simplified /games/new routing, removed ServerSelectionDialog tests

### Removed
