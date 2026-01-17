<!-- markdownlint-disable-file -->

# Release Changes: Reduce Complexity Thresholds to Default Values

**Related Plan**: 20260116-default-complexity-thresholds-reduction-plan.instructions.md
**Implementation Date**: 2026-01-17

## Summary

Systematically refactor high-complexity functions to reduce cyclomatic complexity threshold from 17→10 and cognitive complexity threshold from 20→15 (tool default values), applying proven patterns from create_game() refactoring success.

## Changes

### Added

- [tests/services/api/routes/test_games_helpers.py](tests/services/api/routes/test_games_helpers.py) - Unit tests for extracted helper functions (_parse_update_form_data and _process_image_upload)

### Modified

- [services/api/routes/games.py](services/api/routes/games.py) - Extracted _parse_update_form_data() and _process_image_upload() helpers, refactored update_game() to reduce complexity from C:14 to A:5

### Removed
