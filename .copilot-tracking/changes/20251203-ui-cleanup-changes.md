<!-- markdownlint-disable-file -->

# Release Changes: UI Cleanup and Navigation Reorganization

**Related Plan**: 20251203-ui-cleanup-plan.instructions.md
**Implementation Date**: 2025-12-03

## Summary

Complete terminology consistency by changing remaining "Guild" user-facing text to "Server" and reorganize navigation to make My Games the home screen with streamlined game creation flow.

## Changes

### Added

### Modified

- frontend/src/pages/HomePage.tsx - Updated "View My Guilds" button text to "View My Servers"
- frontend/src/pages/GuildDashboard.tsx - Changed "Guild not found" error message to "Server not found"
- frontend/src/App.tsx - Made MyGames the default home route at "/" and wrapped in ProtectedRoute, removed HomePage import
- frontend/src/components/Layout.tsx - Removed "My Games" navigation button since MyGames is now the home screen

### Removed

- frontend/src/pages/HomePage.tsx - Removed obsolete HomePage component since MyGames is now the home screen

