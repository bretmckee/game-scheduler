<!-- markdownlint-disable-file -->
# Task Details: UI Cleanup and Navigation Reorganization

## Research Reference

**Source Research**: #file:../research/20251203-ui-cleanup-research.md

## Phase 1: Complete Guild-to-Server Terminology

### Task 1.1: Update HomePage button label

Change "View My Guilds" to "View My Servers" on the home page primary button.

- **Files**:
  - frontend/src/pages/HomePage.tsx (Line 45) - Update button text prop
- **Success**:
  - Button displays "View My Servers"
  - No user-facing "Guild" text remains in HomePage
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 8-10) - HomePage button identification
  - #file:../research/20251203-ui-cleanup-research.md (Lines 39-45) - Discord terminology standards
- **Dependencies**:
  - None

### Task 1.2: Update GuildDashboard error message

Change "Guild not found" to "Server not found" in error message.

- **Files**:
  - frontend/src/pages/GuildDashboard.tsx (Line 133) - Update error message text
- **Success**:
  - Error message displays "Server not found"
  - Consistent with other server-related messages in component
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 18-20) - GuildDashboard error message location
- **Dependencies**:
  - None

## Phase 2: Reorganize Home Screen Navigation

### Task 2.1: Update App.tsx routing configuration

Make MyGames the default home route and remove HomePage route.

- **Files**:
  - frontend/src/App.tsx (Lines 18-73) - Update route configuration
    - Change Route at line 51 from `<Route path="/" element={<HomePage />} />` to `<Route path="/" element={<MyGames />} />`
    - Remove HomePage import (Line 24)
    - Move MyGames import to group with core pages
    - Wrap root route in ProtectedRoute since MyGames requires authentication
- **Success**:
  - Navigating to `/` shows MyGames page
  - HomePage no longer imported or used
  - Route protected with authentication
  - No TypeScript or build errors
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 83-89) - New navigation flow requirements
  - #file:../research/20251203-ui-cleanup-research.md (Lines 99-107) - Routing changes needed
- **Dependencies**:
  - Phase 1 completion recommended but not required

### Task 2.2: Remove HomePage component

Delete the HomePage.tsx file since it's no longer used.

- **Files**:
  - frontend/src/pages/HomePage.tsx - Delete entire file
- **Success**:
  - HomePage.tsx removed from filesystem
  - No orphaned component in codebase
  - Build succeeds without HomePage
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 83-85) - Remove current HomePage
- **Dependencies**:
  - Task 2.1 must be completed first

### Task 2.3: Update Layout navigation

Remove "My Games" button from header since it's now the home screen, update logo click to navigate home.

- **Files**:
  - frontend/src/components/Layout.tsx (Lines 48-52) - Remove "My Games" button
    - Remove the Button component with `onClick={() => navigate('/my-games')}`
    - Keep "My Servers" button
    - Logo click already navigates to `/` (correct behavior)
- **Success**:
  - Header shows "My Servers" and "Logout" buttons only
  - "My Games" button removed
  - Logo click navigates to home (My Games page)
  - Navigation layout clean and intuitive
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 109-113) - Navigation button updates
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Streamline Game Creation Flow

### Task 3.1: Update MyGames create button

Change "Create New Game" button to open server selection or go directly to create form.

- **Files**:
  - frontend/src/pages/MyGames.tsx (Lines 119-121) - Update button click handler
    - Change from `onClick={() => navigate('/guilds')}` to call new handler function
    - Add handler function to check server count and navigate appropriately
    - Add state for managing server selection dialog
- **Success**:
  - Button labeled "Create New Game"
  - Click triggers server count check
  - Navigation logic implemented but deferred to Task 3.2
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 89-92) - Streamlined create flow
  - #file:../research/20251203-ui-cleanup-research.md (Lines 131-134) - Multi-server flow clarification
- **Dependencies**:
  - None (can be implemented independently)

### Task 3.2: Implement server selection logic

Add logic to determine server count and navigate to appropriate destination.

- **Files**:
  - frontend/src/pages/MyGames.tsx - Add server fetching and navigation logic
    - Import Guild types and API client
    - Add state for guilds list
    - Fetch user's guilds on component mount
    - Create handleCreateGame function:
      - If 1 server: navigate to `/guilds/{guildId}/games/new`
      - If multiple servers: open server selection dialog
      - If 0 servers: show error alert
- **Success**:
  - Guilds fetched when component loads
  - Single server users navigate directly to create form
  - Multi-server users see server selection dialog
  - Zero server users see helpful error message
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 89-92) - Server selection logic
  - #file:../research/20251203-ui-cleanup-research.md (Lines 99-101) - Server detection requirements
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Create ServerSelectionDialog component

Build reusable dialog for selecting a server from user's available servers.

- **Files**:
  - frontend/src/components/ServerSelectionDialog.tsx - Create new component file
    - Accept props: open (boolean), onClose (function), guilds (array), onSelect (function)
    - Display MUI Dialog with list of servers
    - Each server as clickable list item
    - Call onSelect with selected guild when clicked
    - Include Cancel button
  - frontend/src/pages/MyGames.tsx - Import and use dialog
    - Add dialog component below main content
    - Pass state and handlers as props
    - Handle server selection by navigating to create form
- **Success**:
  - Dialog component renders server list
  - Server selection triggers navigation to create form
  - Dialog closes after selection
  - Cancel button closes dialog without action
  - Component follows MUI design patterns
  - TypeScript types defined correctly
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 102-104) - Server selection UI component
  - #file:../research/20251203-ui-cleanup-research.md (Lines 131-134) - Direct navigation to create form
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Testing and Verification

### Task 4.1: Verify navigation flows

Test all navigation paths through the application.

- **Files**:
  - N/A - Manual testing activity
- **Success**:
  - Login redirects to My Games (home)
  - Logo click navigates to My Games
  - "My Servers" button navigates to server list
  - Direct URL navigation works correctly
  - Back button behavior is intuitive
  - Logout returns to login page
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 83-98) - Overall navigation flow
- **Dependencies**:
  - Phase 2 completion

### Task 4.2: Test game creation paths

Verify game creation works correctly from all entry points.

- **Files**:
  - N/A - Manual testing activity
- **Success**:
  - Single server user: My Games → Create New Game → directly to form
  - Multi-server user: My Games → Create New Game → server selection → form
  - Server dashboard still has working create game button
  - Game creation form works identically from all paths
  - Created games appear in My Games list
- **Research References**:
  - #file:../research/20251203-ui-cleanup-research.md (Lines 89-92) - Streamlined creation flow
  - #file:../research/20251203-ui-cleanup-research.md (Lines 131-138) - Multi-server flow details
- **Dependencies**:
  - Phase 3 completion

## Dependencies

- React Router v6 for navigation
- Material-UI Dialog, List, ListItem components
- Existing API client for guild fetching
- Guild type definitions

## Success Criteria

- All terminology consistent (Server for user-facing, guild for technical)
- My Games is functional home screen
- Navigation simplified and intuitive
- Game creation streamlined with fewer clicks
- All flows tested and working
- No build errors or TypeScript issues
