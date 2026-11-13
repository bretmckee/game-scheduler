---
applyTo: '.copilot-tracking/planning/changes/20261109-01-participants-header-link-contrast-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Participants Header Link Contrast (Visited Color)

## Overview

Make the host-only "Participants (x/y)" header link on GameDetails keep a stable, WCAG-AA-compliant color by rendering it as an MUI `Link` instead of a bare react-router `<a>`.

## Objectives

- Header link color no longer changes after the first click (no browser `:visited` purple)
- Header link contrast is ≥ 4.5:1 on `background.paper` `#2F3136` (white inherited from the heading, 13.02:1)
- A regression test prevents silently reverting to a bare `<a>`

## Research Summary

### Project Files

- frontend/src/pages/GameDetails.tsx - participants header `canEdit` branch using a bare `RouterLink`
- `frontend/src/pages/__tests__/GameDetails.participant_seats.test.tsx` - existing header link href/navigation tests
- frontend/src/pages/About.tsx - existing MUI `<Link color="primary">` convention
- frontend/src/theme.ts - dark palette; no `MuiLink` or `a:visited` overrides

### External References

- .copilot-tracking/research/20261109-01-participants-header-link-contrast-research.md - root cause, contrast table, recommended snippet
- Source: https://mui.com/material-ui/integrations/routing/#link - `Link component={RouterLink}` pattern
- Source: https://www.w3.org/TR/WCAG21/#contrast-minimum - 4.5:1 requirement for normal text

### Standards References

- .github/instructions/test-driven-development.instructions.md - bug-fix RED/GREEN workflow
- .github/instructions/unit-tests.instructions.md - falsifiable assertions
- .github/instructions/reactjs.instructions.md - React component conventions
- .github/instructions/typescript-5-es2022.instructions.md - TypeScript conventions

## Implementation Checklist

### [x] Phase 1: Regression Test (RED)

- [x] Task 1.1: Add an `it.fails` regression test asserting the host header is an MUI Link with `underline="always"`
  - Details: .copilot-tracking/planning/details/20261109-01-participants-header-link-contrast-details.md (Lines 11-48)

### [x] Phase 2: Fix the Header Link (GREEN)

- [x] Task 2.1: Replace the bare `RouterLink` with `Link component={RouterLink} color="inherit" underline="always"`, drop `color="primary.main"`, remove the `.fails` marker
  - Details: .copilot-tracking/planning/details/20261109-01-participants-header-link-contrast-details.md (Lines 51-84)

## Dependencies

- `@mui/material` ^7.3.6 and `react-router` ^7.1.1 (already installed; both `Link` imports already present)
- Vitest via `cd frontend && npm run test`

## Success Criteria

- `cd frontend && npm run build` and `cd frontend && npm run test` pass at each phase boundary
- All GameDetails.participant_seats tests pass with the regression test un-marked
- In the browser (dark theme) the header is underlined white and looks the same before and after a click
