<!-- markdownlint-disable-file -->

# Release Changes: Participants Header Link Contrast (Visited Color)

**Related Plan**: 20261109-01-participants-header-link-contrast.plan.md
**Implementation Date**: 2026-11-13

## Summary

The host-only participants header on GameDetails now renders as an MUI Link with inherited (white) color and an always-on underline. It no longer picks up the browser's blue/purple `:link`/`:visited` colors.

## Changes

### Added

- `frontend/src/pages/__tests__/GameDetails.participant_seats.test.tsx` - Regression test asserting the host header link is an MUI Link (`MuiLink-root`, `MuiLink-underlineAlways`)

### Modified

- frontend/src/pages/GameDetails.tsx - Replaced the bare `RouterLink` in the host participants header with `Link component={RouterLink} color="inherit" underline="always"` and removed `color="primary.main"` from the wrapping Typography
- `frontend/src/pages/__tests__/GameDetails.participant_seats.test.tsx` - Removed the `.fails` marker from the regression test (assertions unchanged)

### Removed

- None
