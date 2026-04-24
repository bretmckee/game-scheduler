<!-- markdownlint-disable-file -->

# Task Details: Guild Dashboard UX Simplification

## Research Reference

**Source Research**: #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md

## Phase 1: RED - Write Failing Tests

### Task 1.1: Write failing tests for GuildDashboard restructure

Add tests to `GuildDashboard.test.tsx` that assert the new structure:

- No `<Tabs>` or tab-related elements are rendered
- Games content (from `BrowseGames`) appears directly in the page body
- A "Create a Game" button appears in the header for users with `canCreateGames`

Mark new tests with `test.fails` in Vitest until implementation is complete (RED phase).

- **Files**:
  - `frontend/src/pages/__tests__/GuildDashboard.test.tsx` - add failing tests for new structure
- **Success**:
  - Tests run and fail (RED state confirmed) before any production code changes
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 1-30) - GuildDashboard current structure and tab analysis
- **Dependencies**:
  - None

### Task 1.2: Write failing tests for CreateGame guildId param

Update `CreateGame.test.tsx` to use `MemoryRouter` with a route (replacing `BrowserRouter`) so `useParams` can be tested. Add tests asserting:

- When `guildId` route param is present, the matching guild is auto-selected
- Server picker is hidden when `guildId` is present in the route

Mark new tests with `test.fails` until implementation is complete.

- **Files**:
  - `frontend/src/pages/__tests__/CreateGame.test.tsx` - switch to MemoryRouter with route; add failing guildId param tests
- **Success**:
  - New tests fail in RED state, confirming they detect the missing implementation
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 25-45) - CreateGame param support and test harness analysis
- **Dependencies**:
  - None

## Phase 2: GREEN - Implement Production Code Changes

### Task 2.1: Refactor GuildDashboard.tsx

Remove the fake-tab pattern and embed `<BrowseGames />` as the page body.

**Removals**:

- `tabValue` state, `handleTabChange`, `<Tabs>`, `<Tab>`, local `TabPanel` component
- "Quick Actions" `Grid`, `Card`, `CardContent` block
- Unused MUI imports after removal

**Additions**:

- `import { BrowseGames } from './BrowseGames'`
- "Create a Game" `Button` in the header row (rendered conditionally when `canCreateGames`), navigating to `/guilds/${guildId}/games/new`
- `<BrowseGames />` as the body below the header

This also fixes the broken navigation: the old "Create New Game" button in the Quick Actions card already targeted `/guilds/${guildId}/games/new` (which didn't exist); that route is added in Task 2.3.

- **Files**:
  - `frontend/src/pages/GuildDashboard.tsx` - remove tabs/overview; embed BrowseGames; add Create button
- **Success**:
  - Guild dashboard renders games list immediately on load without tab interaction
  - "Create a Game" button visible in header for managers/game-creators
  - No `<Tabs>`, `<Tab>`, or `<TabPanel>` in rendered output
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 1-30) - GuildDashboard structure and navigation gaps
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 120-165) - Implementation guidance and recommended approach
- **Dependencies**:
  - Task 2.3 adds the `/guilds/:guildId/games/new` route

### Task 2.2: Remove standalone heading from BrowseGames.tsx

Remove `<Typography variant="h4" gutterBottom>Browse Games</Typography>` from `BrowseGames.tsx`. GuildDashboard already displays `guild.guild_name` as the page heading; the standalone heading duplicates it when embedded.

- **Files**:
  - `frontend/src/pages/BrowseGames.tsx` - remove standalone h4 heading
- **Success**:
  - No duplicate heading when BrowseGames renders inside GuildDashboard
  - Filter dropdowns and game cards still render correctly
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 10-20) - BrowseGames heading identified for removal
- **Dependencies**:
  - None

### Task 2.3: Update App.tsx routes

- **Remove**: `<Route path="/guilds/:guildId/games" element={<BrowseGames />} />`
- **Add**: `<Route path="/guilds/:guildId/games/new" element={<CreateGame />} />`

Games are now served by GuildDashboard at `/guilds/:guildId`, making the separate `/guilds/:guildId/games` route redundant.

- **Files**:
  - `frontend/src/App.tsx` - remove redundant games route; add guild-scoped create route
- **Success**:
  - `/guilds/:guildId/games/new` renders `CreateGame` with the `guildId` param available
  - `/guilds/:guildId/games` no longer has a dedicated route
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 35-50) - App.tsx route gaps
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 100-115) - Route change examples
- **Dependencies**:
  - None

### Task 2.4: Add guildId param support to CreateGame.tsx

Add `useParams<{ guildId?: string }>()` to read an optional `guildId` from the route. After the guild list is fetched, apply the following selection logic:

```tsx
const { guildId } = useParams<{ guildId?: string }>();

// In the guild-fetch effect, replace the existing single-guild auto-select:
if (guildId) {
  const preselected = allGuilds.find((g) => g.id === guildId);
  if (preselected && guildsWithAccess.has(preselected.id)) {
    setSelectedGuild(preselected);
  }
} else if (availableGuilds.length === 1 && availableGuilds[0]) {
  setSelectedGuild(availableGuilds[0]);
}
```

Server picker visibility: suppress (hide) when `guildId` param is present, analogous to the existing `availableGuilds.length === 1` suppression.

- **Files**:
  - `frontend/src/pages/CreateGame.tsx` - add useParams; auto-select guild from route; suppress server picker
- **Success**:
  - Guild is pre-selected and server picker hidden when `guildId` is in the URL
  - Existing single-guild auto-select behavior is preserved when no param
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 55-85) - CreateGame param support implementation pattern
- **Dependencies**:
  - None

## Phase 3: REFACTOR - Remove xfail Markers and Verify

### Task 3.1: Remove test.fails markers and confirm full test pass

After all Phase 2 tasks are complete:

- Remove all `test.fails` / `it.todo` markers added in Phase 1
- Run `cd frontend && npm run test` to confirm all tests pass
- Verify no regressions in existing `GuildDashboard.test.tsx`, `BrowseGames.test.tsx`, `CreateGame.test.tsx`

- **Files**:
  - `frontend/src/pages/__tests__/GuildDashboard.test.tsx`
  - `frontend/src/pages/__tests__/CreateGame.test.tsx`
- **Success**:
  - All frontend tests pass with no `test.fails` or `it.todo` markers remaining
  - No regressions in any existing test file
- **Research References**:
  - #file:../research/20260424-01-guild-dashboard-ux-simplification-research.md (Lines 88-100) - Test setup analysis
- **Dependencies**:
  - All Phase 2 tasks complete

## Dependencies

- No external dependencies; all changes within `frontend/src/`

## Success Criteria

- Guild dashboard immediately shows the games list on navigation
- Guild name visible as the page heading (no duplicate heading in embedded BrowseGames)
- "Create a Game" button in header navigates to CreateGame with guild pre-selected
- Server picker suppressed when `guildId` is in the URL
- All existing and new frontend tests pass
