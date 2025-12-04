<!-- markdownlint-disable-file -->
# Task Research Notes: UI Cleanup

## Research Executed

### File Analysis
- frontend/src/pages/HomePage.tsx
  - Line 45: Button labeled "View My Guilds" (needs update to "View My Servers")
- frontend/src/pages/GuildListPage.tsx
  - Lines 1-120: Page uses "servers" in user-facing messages but file/component name contains "Guild"
  - Line 62: Message says "Synced X new server(s)" (already uses "server")
  - Line 67: Message says "All servers are already synced" (already uses "server")
  - Line 92: Message says "Failed to load servers" (already uses "server")
  - Line 113: Message says "No servers with bot configurations found" (already uses "server")
- frontend/src/pages/GuildDashboard.tsx
  - Line 126: Displays guild.guild_name (data field name is technical)
  - Line 121: "Back to Servers" button (already uses "Server")
  - Line 133: "Guild not found" message (should be "Server not found")
  - Line 135: "Back to Servers" button (already uses "Server")
- frontend/src/components/Layout.tsx
  - Line 48: Navigation button shows "My Servers" (already correct)

### Code Search Results
- "View My Guilds"
  - frontend/src/pages/HomePage.tsx (Line 45) - Primary button on home page after login
- "guild|Guild" pattern search
  - 100+ matches across frontend (showing maxResults limit)
  - Mix of technical field names (guild_id, guild_name) and user-facing text
  - Most user-facing text already updated to "Server" per Task 12.8

### Project Conventions
- Standards referenced: Task 12.8 already completed - change "Guild" to "Server" on web pages
- Implementation pattern: Keep technical names (guild_id, guildId, Guild interface) but change user-facing labels
- Previous work shows consistent pattern:
  - Internal code: uses "guild" (matches Discord API terminology)
  - User-facing text: uses "Server" (matches Discord UI terminology)
  - File/component names: kept as "Guild*" for consistency with codebase
  - Route paths: kept as "/guilds" for API consistency

## Key Discoveries

### Current State of Terminology

The codebase shows partial completion of Task 12.8 (Change "Guild" to "Server"):

**Already Updated (User-Facing Text)**:
- Most page messages and alerts use "server"
- Navigation buttons mostly use "Server"
- Sync messages use "server"
- Error messages mostly use "server"

**Still Using "Guild" (User-Facing)**:
1. HomePage.tsx - "View My Guilds" button (primary issue identified by user)
2. GuildDashboard.tsx - "Guild not found" error message

**Correctly Using "Guild" (Technical)**:
- TypeScript interfaces: `Guild`, `DiscordGuild`
- Component names: `GuildListPage`, `GuildDashboard`, `GuildConfig`
- API routes: `/api/v1/guilds`
- Database models: `GuildConfiguration`, `guild_id` fields
- Python backend: guild_id, guild_name fields

### Implementation Patterns

From previous Task 12.8 completion:

```tsx
// CORRECT: Technical field name (guild_id) but user-facing label uses "Server"
<Alert severity="info">
  No servers with bot configurations found.
</Alert>

// CORRECT: Navigation path uses /guilds but button text says "Server"
<Button onClick={() => navigate('/guilds')}>
  Back to Servers
</Button>

// CORRECT: Component displays guild.guild_name but context is clear
<Typography variant="h4">{guild.guild_name}</Typography>
```

### Discord Terminology Standards

From Discord's official documentation:
- **Discord API**: Uses "guild" consistently in all endpoints, objects, and fields
- **Discord UI**: Uses "Server" in user interface for end users
- **Best Practice**: Keep internal code aligned with API (guild), present as "Server" to users

## Recommended Approach

**Single Focused Change**: Update remaining user-facing "Guild" references to "Server"

### Files Requiring Changes

1. **frontend/src/pages/HomePage.tsx** (Line 45)
   - Change: `View My Guilds` → `View My Servers`
   - Context: Primary button shown to logged-in users on home page

2. **frontend/src/pages/GuildDashboard.tsx** (Line 133)
   - Change: `Guild not found` → `Server not found`
   - Context: Error message when server doesn't exist

### No Changes Required

- Keep all technical names: `Guild` interface, `GuildConfiguration`, `guild_id`, `guildId`
- Keep component names: `GuildListPage`, `GuildDashboard`, `GuildConfig`
- Keep route paths: `/guilds/:guildId`
- Keep API field names: `guild_id`, `guild_name`

## Implementation Guidance

- **Objectives**: Complete Task 12.8 by fixing remaining user-facing "Guild" text
- **Key Tasks**: 
  1. Update HomePage button label
  2. Update GuildDashboard error message
- **Dependencies**: None - purely UI text changes
- **Success Criteria**: 
  - No user-facing "Guild" text remains (except in technical contexts like URLs)
  - All user-visible labels, buttons, and messages say "Server"
  - Internal code structure unchanged

---

## Issue 2: Reorganize Home Screen and Navigation

### User Experience Change

**Current Flow:**
- HomePage (landing page with buttons)
- "My Games" button navigates to separate page
- Create game requires clicking through: Home → Servers → Server Dashboard → Create Game

**New Flow:**
- Remove current HomePage
- Make "My Games" the new home screen (default landing page)
- Remove "My Games" navigation button from header (since it's now the home)
- Streamline game creation: From My Games screen, create button should:
  - If user in only 1 server: Skip server selection, go directly to create game form
  - If user in multiple servers: Show server picker, then create game form

### Investigation Needed

1. **Routing Changes**
   - What's the current route structure?
   - Make `/` route show MyGames instead of HomePage
   - Update navigation logic in Layout/header

2. **Server Selection in Create Flow**
   - How to detect number of servers user has access to?
   - Where to add conditional logic for server selection?
   - Can we reuse existing GuildListPage component or need inline picker?

3. **Navigation Updates**
   - Remove "My Games" button from Layout header
   - Update any links/redirects that go to old HomePage
   - Ensure "Discord Game Scheduler" logo/title navigates to new home (My Games)

### Files to Analyze

- frontend/src/App.tsx - Route definitions
- frontend/src/pages/HomePage.tsx - Current home page (to be replaced)
- frontend/src/pages/MyGames.tsx - Will become new home page
- frontend/src/components/Layout.tsx - Header navigation buttons
- frontend/src/pages/CreateGame.tsx - Game creation flow to streamline
- frontend/src/pages/GuildListPage.tsx - Server selection component

### Clarification: Multi-Server Create Flow

When user clicks "Create Game" from My Games screen and has multiple servers:
1. Show server selection screen/dialog
2. After selecting server, navigate **directly to Create Game form** (not to server dashboard)
3. Skip the intermediate server dashboard page entirely in this flow

Current behavior likely goes: My Games → Select Server → Server Dashboard → Create Game
Desired behavior: My Games → Select Server → Create Game (skip dashboard)
