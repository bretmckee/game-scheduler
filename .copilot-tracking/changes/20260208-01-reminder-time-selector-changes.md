<!-- markdownlint-disable-file -->

# Release Changes: Reminder Time Selector Component

**Related Plan**: 20260208-01-reminder-time-selector-plan.instructions.md
**Implementation Date**: 2026-02-08

## Summary

Implementation of ReminderSelector component to replace text-based comma-separated reminder input with intuitive Select + Chip multi-selector matching DurationSelector interaction pattern.

## Changes

### Added

- frontend/src/components/ReminderSelector.tsx - Created component stub with TypeScript interface and error throw
- frontend/src/components/**tests**/ReminderSelector.test.tsx - Created comprehensive test suite with 20 test cases covering all expected behaviors

### Modified

- frontend/src/components/ReminderSelector.tsx - Implemented preset selection with dropdown showing 5min, 30min, 1hr, 2hr, 1day options
- frontend/src/components/ReminderSelector.tsx - Added Chip display for selected values with delete functionality
- frontend/src/components/ReminderSelector.tsx - Implemented custom minute input mode with validation (1-10080 range, integers only, no duplicates)
- frontend/src/components/**tests**/ReminderSelector.test.tsx - Fixed test assertions to use within() helper for disambiguation and corrected empty dropdown expectation

### Removed
