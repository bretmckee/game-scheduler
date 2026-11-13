<!-- markdownlint-disable-file -->

# Task Details: Participants Header Link Contrast (Visited Color)

## Research Reference

**Source Research**: .copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md

## Phase 1: Regression Test (RED)

### Task 1.1: Add a failing regression test asserting the header is an MUI Link

This is a bug fix, so follow "TDD for Bug Fixes" in `.github/instructions/test-driven-development.instructions.md`: no stub, but the test must first be shown to fail against the current bare `<RouterLink>`.

Add a new test to the existing `describe` block, next to the "renders an underlined link..." test, marked with Vitest's `it.fails` and a comment naming the bug:

```tsx
// Bug: bare RouterLink renders a plain <a>, so the browser's :link/:visited colors
// override the Typography color (blue -> purple after click, fails WCAG AA).
it.fails(
  'renders the host header link as an MUI Link that inherits the heading color',
  async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: gameFixture(true) } as never);

    renderGameDetails();

    const headerLink = await screen.findByRole('link', { name: /participants/i });
    expect(headerLink).toHaveClass('MuiLink-root');
    expect(headerLink).toHaveClass('MuiLink-underlineAlways');
    expect(headerLink).toHaveAttribute('href', '/games/game-1/participant-seats');
  }
);
```

- **Files**:
  - `frontend/src/pages/__tests__/GameDetails.participant_seats.test.tsx` - add the `it.fails` regression test (reuse existing `gameFixture` / `renderGameDetails` helpers)
- **Success**:
  - `cd frontend && npm run test -- GameDetails.participant_seats` shows the new test as an expected failure; all other tests pass
  - Temporarily removing `.fails` makes the test fail on the `MuiLink-root` assertion (proves it detects the bug); restore `.fails` before finishing
  - `cd frontend && npm run build` passes
- **Research References**:
  - .copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md (Lines 18-19) - existing tests and how they locate the link
  - .copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md (Lines 90) - suggested `MuiLink-root` class assertion; TDD applies
  - .github/instructions/test-driven-development.instructions.md (Lines 35-66) - bug-fix RED/GREEN workflow
  - .github/instructions/unit-tests.instructions.md - falsifiable assertions
- **Dependencies**:
  - None

## Phase 2: Fix the Header Link (GREEN)

### Task 2.1: Replace the bare RouterLink with MUI Link and remove the `.fails` marker

In the `canEdit` branch of the participants header, swap the bare `<RouterLink>` for the already-imported MUI `Link`, and drop `color="primary.main"` from the wrapping `Typography`. Keep the explanatory comment above the conditional and the non-host branch unchanged.

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

Then change `it.fails(` to `it(` on the Task 1.1 test and delete its "Bug:" comment. Do not change any assertion.

- **Files**:
  - frontend/src/pages/GameDetails.tsx - replace the `canEdit` header block (currently lines ~396-405); no import changes (`Link` from `@mui/material` at line 39 and `Link as RouterLink` from `react-router` at line 42 already exist)
  - `frontend/src/pages/__tests__/GameDetails.participant_seats.test.tsx` - remove `.fails` marker only
- **Success**:
  - All tests in GameDetails.participant_seats.test.tsx pass, including the existing href and navigation tests
  - `cd frontend && npm run build` and `cd frontend && npm run test` pass
  - Manual check (dark theme): header is underlined white (13.02:1 on `#2F3136`) and does not change color after clicking and navigating back
- **Research References**:
  - .copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md (Lines 44-58) - root cause and contrast ratios
  - .copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md (Lines 60-85) - alternatives and the recommended snippet
  - Source: https://mui.com/material-ui/integrations/routing/#link - `Link component={RouterLink}` pattern
- **Dependencies**:
  - Phase 1 completion

## Dependencies

- `@mui/material` ^7.3.6 and `react-router` ^7.1.1 (already installed)
- Vitest (`npm run test`) with `it.fails` support

## Success Criteria

- Host participants header renders as an MUI Link with inherited (white) color and an always-on underline
- Link color is identical before and after visiting the participant-seats page
- Contrast ≥ 4.5:1 on `background.paper`
- Frontend build and full frontend test suite pass at each phase boundary
