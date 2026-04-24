<!-- markdownlint-disable-file -->

# Task Research Notes: Guild Dashboard UX Simplification

## Research Executed

### File Analysis

- `frontend/src/pages/GuildDashboard.tsx`
  - Has two tabs: "Overview" and "Games". The "Games" tab is fake — its `handleTabChange` calls `navigate(/guilds/${guildId}/games)` instead of switching a tab panel. Overview tab renders a "Quick Actions" card with two buttons.
  - "Create New Game" button navigates to `/guilds/${guildId}/games/new` — this route **does not exist** in App.tsx (bug: falls through to `<Navigate to="/" replace />`).
  - Already fetches and displays `guild.guild_name` as an `h4` heading. Guild name context is already present.
  - Already has conditional Settings and Templates buttons in the header (managers only) — no changes needed for those.

- `frontend/src/pages/BrowseGames.tsx`
  - Reads `guildId` from `useParams` — already compatible with being rendered inside GuildDashboard.
  - Opens with `<Typography variant="h4">Browse Games</Typography>` — this would duplicate the heading when embedded in GuildDashboard.
  - Contains channel + status filter dropdowns, game card list, SSE game updates via `useGameUpdates`.

- `frontend/src/pages/CreateGame.tsx`
  - Reads no route params — fetches all guilds itself, auto-selects when only one guild has templates.
  - Server picker dropdown is conditionally shown only when `availableGuilds.length > 1`.
  - Guild pre-selection is driven by `setSelectedGuild` state — no route integration today.
  - Route at `/games/new` (no guild context).

- `frontend/src/App.tsx`
  - Routes: `/guilds/:guildId` → `GuildDashboard`, `/guilds/:guildId/games` → `BrowseGames`, `/games/new` → `CreateGame`.
  - `/guilds/:guildId/games/new` does **not** exist — gap confirmed.
  - URL hierarchy: games live at `/games/:gameId`, not nested under guilds.

- `frontend/src/components/Layout.tsx`
  - AppBar always shows "Discord Game Scheduler" — no per-page context. No changes needed; the guild name on the page body (GuildDashboard `h4`) satisfies the "show current guild" requirement.

- `frontend/src/pages/__tests__/CreateGame.test.tsx`
  - Uses `BrowserRouter` (not `MemoryRouter` with route params). Adding `guildId` param support requires updating test setup to use `MemoryRouter` with a route.

- `frontend/src/pages/__tests__/BrowseGames.test.tsx`
  - Uses `MemoryRouter` + `Routes`/`Route` with `:guildId` param — already tests the embedded component correctly.

### Code Search Results

- `games/new` occurrences
  - `GuildDashboard.tsx:186` — navigates to `/guilds/${guildId}/games/new` (broken route)
  - `MyGames.tsx:149` — navigates to `/games/new` (correct, no guild context)
  - `App.tsx:65` — only `/games/new` route defined
  - Two test assertions in `MyGames.test.tsx` confirming `/games/new`

- `useParams` in CreateGame
  - Not used — only `useNavigate` imported from `react-router`

- Tab-related code in GuildDashboard
  - `tabValue` state, `handleTabChange`, `<Tabs>`, `<Tab>`, `<TabPanel>` component — all removable
  - `TabPanel` is defined locally in the file (not a shared component)

### Project Conventions

- Standards referenced: existing URL hierarchy (`/guilds/:guildId/config`, `/guilds/:guildId/templates`), MUI component patterns, `useParams` usage across pages
- Instructions followed: TDD applicable (TypeScript); surgical minimal changes

## Key Discoveries

### Project Structure

GuildDashboard is a thin wrapper that currently fakes a tab navigation pattern. It owns the guild fetch, guild name display, and manager permission checks. BrowseGames is a self-contained page that independently fetches games by guildId param. They are already decoupled in a way that makes Option C (GuildDashboard as shell, BrowseGames as embedded content) structurally clean.

### Implementation Patterns

The `availableGuilds.length > 1` conditional in CreateGame already suppresses the server picker for single-guild users. The same pattern applies when pre-selecting via route param: if `guildId` is in the URL, skip the picker entirely and call `setSelectedGuild` with the matching guild from the fetched list.

### Complete Examples

```tsx
// CreateGame.tsx — reading optional guildId from route
const { guildId } = useParams<{ guildId?: string }>();

// After guilds are fetched, auto-select the guild from the URL param
if (guildId) {
  const preselected = allGuilds.find((g) => g.id === guildId);
  if (preselected && guildsWithAccess.has(preselected.id)) {
    setSelectedGuild(preselected);
  }
} else if (availableGuilds.length === 1 && availableGuilds[0]) {
  setSelectedGuild(availableGuilds[0]);
}
```

```tsx
// GuildDashboard.tsx — embed BrowseGames after removing tabs
import { BrowseGames } from './BrowseGames';

// In the return, replace <TabPanel> content with:
<BrowseGames />;
```

```tsx
// BrowseGames.tsx — remove standalone heading (GuildDashboard owns it)
// Remove:
// <Typography variant="h4" gutterBottom>Browse Games</Typography>
```

### API and Schema Documentation

No API changes required. All routes and backend endpoints are unchanged. This is a pure frontend restructure.

### Configuration Examples

```tsx
// App.tsx route changes
// Remove:
<Route path="/guilds/:guildId/games" element={<BrowseGames />} />

// Add:
<Route path="/guilds/:guildId/games/new" element={<CreateGame />} />
```

### Technical Requirements

- TDD applies: TypeScript/TSX files require test updates alongside implementation
- `CreateGame` tests use `BrowserRouter` — must switch to `MemoryRouter` with route params to test the new `guildId` param path
- `BrowseGames` tests already use `MemoryRouter` with `:guildId` — rendering inside GuildDashboard context is already covered
- No new dependencies; no backend changes

## Recommended Approach

**Option C: GuildDashboard as shell, BrowseGames as embedded content**

GuildDashboard strips its tab/overview structure and renders `<BrowseGames />` directly as its body. BrowseGames removes its own `h4` heading since GuildDashboard already displays `guild.guild_name`. A "Create a Game" button (conditional on `canCreateGames`) is added to the GuildDashboard header row alongside existing Settings/Templates buttons, navigating to `/guilds/${guildId}/games/new`. CreateGame gains optional `guildId` route param support, pre-selecting the guild and hiding the server picker when present.

This approach:

- Eliminates the broken fake-tab pattern
- Fixes the broken `/guilds/:guildId/games/new` navigation
- Surfaces guild context on the games view with zero additional API calls (GuildDashboard already fetches it)
- Keeps Settings/Templates/Create buttons cohesive in one header
- Follows the existing URL hierarchy for guild-scoped actions

## Implementation Guidance

- **Objectives**: Remove the Overview tab dead-end; show games immediately on guild selection; display guild name on the games view; fix the broken Create Game navigation; enable guild pre-selection in CreateGame when navigated from guild context
- **Key Tasks**:
  1. `GuildDashboard.tsx`: Remove `TabPanel`, `Tabs`, `Tab`, `tabValue`, `handleTabChange`, `Grid`, `Card`, `CardContent`; add `<BrowseGames />` in body; add "Create a Game" `Button` (conditional on `canCreateGames`) to header row; fix navigate target to `` `/guilds/${guildId}/games/new` ``
  2. `BrowseGames.tsx`: Remove `<Typography variant="h4">Browse Games</Typography>`
  3. `App.tsx`: Add `/guilds/:guildId/games/new` → `CreateGame` route; remove `/guilds/:guildId/games` route
  4. `CreateGame.tsx`: Add `useParams` to read optional `guildId`; when present, auto-select matching guild and suppress server picker
  5. Tests: Update `CreateGame.test.tsx` to use `MemoryRouter` + route for guildId param tests; add test covering guild pre-selection via route param
- **Dependencies**: None external; all changes are within `frontend/src/`
- **Success Criteria**: Selecting a server navigates directly to its games list; guild name is visible on that view; "Create a Game" button navigates to CreateGame with the guild pre-selected; no server picker shown when guildId is in the URL; all existing tests pass; new tests cover the guildId param path
