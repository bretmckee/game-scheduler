<!-- markdownlint-disable-file -->

# Changes: Guild Dashboard UX Simplification

## Summary

Simplify GuildDashboard by removing its fake tab pattern, embedding BrowseGames directly, adding a "Create a Game" header button, fixing the broken `/guilds/:guildId/games/new` route, and adding optional `guildId` route param support to CreateGame.

## Added

- `frontend/src/pages/__tests__/GuildDashboard.test.tsx` - new test file covering GuildDashboard restructure: no tabs rendered, BrowseGames embedded, and conditional "Create a Game" header button

## Modified

- `frontend/src/pages/GuildDashboard.tsx` - removed Tabs/Tab/TabPanel/Card/CardContent/Grid structure; embeds `<BrowseGames />` directly; adds conditional "Create a Game" button in the header when user has `canCreateGames`
- `frontend/src/pages/BrowseGames.tsx` - removed standalone `<Typography variant="h4">Browse Games</Typography>` heading (heading is now provided by GuildDashboard)
- `frontend/src/App.tsx` - replaced broken `/guilds/:guildId/games` route with `/guilds/:guildId/games/new` route pointing to `<CreateGame />`
- `frontend/src/pages/CreateGame.tsx` - added `useParams` import and `guildId` route param support; when `guildId` is present in URL, auto-selects the matching guild and hides the server picker
- `frontend/src/pages/__tests__/CreateGame.test.tsx` - added `describe('CreateGame with guildId route param')` block with tests covering guild auto-selection and server picker suppression via route param

## Removed

- Tab/overview pattern from GuildDashboard (no longer needed; games list is the immediate page body)
