<!-- markdownlint-disable-file -->

# Task Research Notes: Participants Header Link Contrast (Visited Color)

## Research Executed

### File Analysis

- frontend/src/pages/GameDetails.tsx (lines 393-411)
  - Hosts (`canEdit`) see the header as a bare react-router `<RouterLink>` (renders a plain `<a>`) wrapped in `<Typography variant="h6" color="primary.main">`. The only inline style is `textDecoration: 'underline', textUnderlineOffset: 2`. No `color` is set on the `<a>` itself.
  - Line 42 imports `Link as RouterLink` from `react-router`; the MUI `Link` is already imported (used at line 64 for location URLs).
- frontend/src/theme.ts
  - Dark palette: `background.paper` `#2F3136`, `background.default` `#36393F`, `primary.main` `#5865F2`, `primary.light` `#7289DA`. No `MuiLink` override and no global `a`/`a:visited` rule.
- frontend/src/App.tsx (line 46)
  - `<CssBaseline />` is used. It does not reset anchor colors, so the browser's built-in link colors apply.
- frontend/src/pages/About.tsx (lines 102, 113, 155)
  - Existing convention: links use MUI `<Link color="primary">`.
- `frontend/src/pages/__tests__/GameDetails.participant_seats.test.tsx` (lines 128-149)
  - Tests look up the link with `getByRole('link', { name: /participants/i })` and assert its `href` and that clicking it navigates. They do not assert on color or style, so they stay valid with any of the fixes below.

### Code Search Results

- `RouterLink` / `component={RouterLink}` in frontend/src (non-test)
  - Only GameDetails.tsx:398 uses a bare RouterLink; no `component={RouterLink}` usages exist yet.
- `:visited|MuiLink|a:visited` in frontend/src
  - No matches; nothing in the project styles visited links.

### External Research

- Source: https://html.spec.whatwg.org/multipage/rendering.html#phrasing-content-3 — UA stylesheet
  - `:link { color: #0000EE; }` and `:visited { color: #551A8B; }` are set on the anchor itself, so they override any color the anchor would inherit from a parent `Typography`.
- Source: https://mui.com/material-ui/integrations/routing/#link — MUI Link with a router
  - The recommended pattern is `<Link component={RouterLink} to="...">`. MUI `Link` sets an explicit `color` on the anchor, so the browser's `:visited` color never applies.
- Source: https://www.w3.org/TR/WCAG21/#contrast-minimum — WCAG 1.4.3
  - Normal text needs a 4.5:1 contrast ratio. Text counts as large (3:1) only at ≥18.66px bold. The h6 here is 1rem/600, so the 4.5:1 rule applies.

### Project Conventions

- Standards referenced: .github/instructions/reactjs.instructions.md, typescript-5-es2022.instructions.md (by path only)
- Instructions followed: researcher-enhancements (no new dependency versions involved)

## Key Discoveries

### Root Cause

`color="primary.main"` on the Typography never reaches the text. The `<a>` gets the browser's default link colors instead: blue `#0000EE` before the first click and purple `#551A8B` after it. That color change is the behavior the user reported. Even before the first click, the default blue has very poor contrast on the dark theme.

### Contrast Ratios Against `background.paper` #2F3136 (computed with the WCAG relative-luminance formula)

| Foreground                       | Ratio | WCAG AA (4.5:1) |
| -------------------------------- | ----- | --------------- |
| UA unvisited `#0000EE` (current) | 1.38  | fail            |
| UA visited `#551A8B` (current)   | 1.18  | fail            |
| `primary.main` `#5865F2`         | 2.83  | fail            |
| `primary.light` `#7289DA`        | 3.91  | fail            |
| `text.primary` `#FFFFFF`         | 13.02 | pass            |

Takeaway: no color from the current blue palette reaches 4.5:1 on this background. Only the standard white text color passes.

### Alternatives Evaluated

1. **MUI `Link component={RouterLink}`, `color="inherit"`, `underline="always"` (recommended)**: the header keeps the same white as the other headings, stays recognizable as a link through the underline, the visited color is fixed, and it matches the MUI Link convention from About.tsx. It is a one-element change with no theme edits.
2. **Same as #1 but `color="primary.light"`**: keeps a blue "link" look, but at 3.91:1 it still fails AA.
3. **Global theme fix (`MuiLink` override or `CssBaseline` `a:visited` rule)**: broader than needed. It would not fix this element anyway unless it also became an MUI Link, because the bare `<a>` bypasses `MuiLink`.
4. **Keep the bare RouterLink and add `color: 'inherit'` to its inline style**: works, but it diverges from the project's MUI Link convention.

## Recommended Approach

In frontend/src/pages/GameDetails.tsx, replace the bare `<RouterLink>` with the MUI `Link` that is already imported. Remove `color="primary.main"` from the wrapping Typography:

```tsx
<Typography variant="h6" gutterBottom>
  <Link
    component={RouterLink}
    to={`/games/${gameId}/participant-seats`}
    color="inherit"
    underline="always"
    sx={{ textUnderlineOffset: 2 }}
  >
    Participants ({game.participant_count || 0}/{game.max_players || UI.DEFAULT_MAX_PLAYERS})
  </Link>
</Typography>
```

**Decision (2026-11-13):** The product owner confirmed white (`color="inherit"`) is correct. The header does not need to stay blue, so the `primary.light` option is rejected.

## Implementation Guidance

- **Objectives**: The header link color no longer changes after the first click, and its contrast reaches at least 4.5:1.
- **Key Tasks**: Edit GameDetails.tsx lines 396-405 as shown above. Optionally add a test assertion such as `expect(headerLink).toHaveClass('MuiLink-root')` so a later change can't silently go back to a bare `<a>`. TDD applies (TSX/Vitest).
- **Dependencies**: None. `@mui/material` ^7.3.6 and `react-router` ^7.1.1 are already installed, and the MUI `Link` is already imported.
- **Success Criteria**: The existing tests in GameDetails.participant_seats.test.tsx pass. In a browser, the header looks the same before and after a click and is underlined white on the dark paper background.
