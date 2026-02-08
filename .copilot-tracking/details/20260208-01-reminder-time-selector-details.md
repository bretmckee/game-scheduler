<!-- markdownlint-disable-file -->

# Task Details: Reminder Time Selector Component

## Research Reference

**Source Research**: #file:../research/20260208-01-reminder-time-selector-research.md

## Phase 0: ReminderSelector Component with TDD

### Task 0.1: Create ReminderSelector component stub

Create new ReminderSelector component with stub implementation following TDD Red-Green-Refactor pattern.

- **Files**:
  - frontend/src/components/ReminderSelector.tsx - New component file
- **Success**:
  - File created with TypeScript interface defining props
  - Component stub throws `Error('not yet implemented')`
  - Props interface matches: `value: number[]`, `onChange: (minutes: number[]) => void`, `error?: boolean`, `helperText?: string`
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 78-86) - Component structure requirements
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 162-205) - Approach C implementation example
- **Dependencies**:
  - None (creating new component)

### Task 0.2: Write failing tests for ReminderSelector

Write comprehensive tests expecting proper behavior before implementation (RED phase).

- **Files**:
  - frontend/src/components/**tests**/ReminderSelector.test.tsx - New test file
- **Success**:
  - Tests written with actual expected behavior assertions
  - Test preset selection (5min, 30min, 1hr, 2hr, 1day)
  - Test chip display after selection
  - Test chip deletion functionality
  - Test custom mode activation
  - Test custom value addition
  - Test duplicate prevention
  - Tests fail correctly (stub throws error)
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 162-205) - Implementation example showing expected behaviors
  - frontend/src/components/**tests**/DurationSelector.test.tsx - Similar test patterns
- **Dependencies**:
  - Task 0.1 completion

### Task 0.3: Implement preset selection with dropdown

Implement basic Select dropdown with preset options (GREEN phase partial).

- **Files**:
  - frontend/src/components/ReminderSelector.tsx - Replace stub with Select implementation
- **Success**:
  - Remove `Error('not yet implemented')`
  - Add Select component with preset MenuItems
  - Implement onChange handler to add selected preset to value array
  - Values sort ascending automatically
  - Basic preset selection tests pass
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 88-91) - Preset values specification
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 162-205) - Complete implementation example
- **Dependencies**:
  - Task 0.2 completion

### Task 0.4: Add chip display with delete functionality

Add Chip components to display selected values with delete capability (GREEN phase continued).

- **Files**:
  - frontend/src/components/ReminderSelector.tsx - Add Chip display section
- **Success**:
  - Chips render for each value in array
  - Each chip shows appropriate label (preset label or "X minutes")
  - Delete button on chip removes value from array
  - Chip display tests pass
  - Chip deletion tests pass
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 162-205) - Chip implementation in Approach C
  - #fetch:https://mui.com/material-ui/react-chip/ - Chip component documentation
- **Dependencies**:
  - Task 0.3 completion

### Task 0.5: Add custom minute input mode

Implement custom minute entry with inline TextField (GREEN phase completed).

- **Files**:
  - frontend/src/components/ReminderSelector.tsx - Add custom mode UI and handlers
- **Success**:
  - "Custom..." MenuItem triggers custom mode
  - TextField and buttons appear for custom input
  - Custom value validates (1-10080 range, integer)
  - Add button adds validated value to array
  - Cancel button closes custom mode
  - Custom mode tests pass
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 93-98) - Custom input validation rules
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 162-205) - Custom mode implementation
- **Dependencies**:
  - Task 0.4 completion

### Task 0.6: Refactor and add edge case tests

Refactor for code quality and add comprehensive edge case coverage (REFACTOR phase).

- **Files**:
  - frontend/src/components/ReminderSelector.tsx - Refactor implementation
  - frontend/src/components/**tests**/ReminderSelector.test.tsx - Add edge case tests
- **Success**:
  - Duplicate prevention enforced (disable already-selected presets)
  - Empty array handling works correctly
  - Invalid custom input rejected properly
  - Out-of-range values rejected
  - Error prop displays correctly
  - Helper text displays appropriately
  - Full test suite passes with 100% coverage
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 93-98) - Validation requirements
- **Dependencies**:
  - Task 0.5 completion

## Phase 1: GameForm Integration with TDD

### Task 1.1: Update GameForm state for array-based reminders

Add new state field for array-based reminder management alongside existing string field.

- **Files**:
  - frontend/src/components/GameForm.tsx - Update FormData interface and state
- **Success**:
  - Add `reminderMinutesArray: number[]` to FormData interface
  - Initialize from `initialData.reminder_minutes` if present
  - Maintain `reminderMinutes` string field for backward compatibility
  - State correctly converts between array and string representations
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 100-116) - Integration example
  - frontend/src/components/GameForm.tsx (Lines 95, 153, 181) - Current state structure
- **Dependencies**:
  - Phase 0 completion

### Task 1.2: Write failing GameForm integration tests

Write tests for ReminderSelector integration in GameForm (RED phase).

- **Files**:
  - frontend/src/components/**tests**/GameForm.test.tsx - Add ReminderSelector integration tests
- **Success**:
  - Test ReminderSelector renders in form
  - Test selecting preset updates form state
  - Test deleting chip updates form state
  - Test custom value addition
  - Test form submission includes correct reminder_minutes array
  - Tests fail correctly (not yet integrated)
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 100-116) - Integration pattern
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Replace TextField with ReminderSelector

Replace existing reminder TextField with new ReminderSelector component (GREEN phase).

- **Files**:
  - frontend/src/components/GameForm.tsx - Replace TextField import and JSX
- **Success**:
  - Import ReminderSelector component
  - Replace TextField at lines 620-630 with ReminderSelector
  - Wire to `reminderMinutesArray` state
  - Update onChange handler to sync both array and string
  - Component renders and functions correctly
  - Integration tests pass
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 100-116) - Integration code example
  - frontend/src/components/GameForm.tsx (Lines 620-630) - Current TextField to replace
- **Dependencies**:
  - Task 1.2 completion

### Task 1.4: Update validation for array-based input

Adapt validation to work with array instead of string input.

- **Files**:
  - frontend/src/components/GameForm.tsx - Update validateReminderField handler
  - frontend/src/utils/fieldValidation.ts - Add array-based validator if needed
- **Success**:
  - Validation works with number[] instead of string
  - Error states display correctly on ReminderSelector
  - Invalid custom inputs show appropriate errors
  - Validation tests pass
- **Research References**:
  - frontend/src/utils/fieldValidation.ts (Lines 50-80) - Current validation logic
- **Dependencies**:
  - Task 1.3 completion

### Task 1.5: Test backward compatibility with existing data

Verify existing games with comma-separated reminder data load correctly.

- **Files**:
  - frontend/src/components/**tests**/GameForm.test.tsx - Add backward compatibility tests
- **Success**:
  - Test loading game with existing `reminder_minutes: [60, 15]`
  - Verify values display as chips in ReminderSelector
  - Test editing and saving preserves data integrity
  - All backward compatibility tests pass
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 53-58) - Current workflow and data structure
- **Dependencies**:
  - Task 1.4 completion

## Phase 2: TemplateForm Integration with TDD

### Task 2.1: Add ReminderSelector to TemplateForm

Apply same integration pattern to TemplateForm for consistency.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Update state and replace TextField
- **Success**:
  - Add `reminderMinutesArray` to TemplateFormData interface
  - Import ReminderSelector component
  - Replace TextField with ReminderSelector
  - Wire to array-based state
  - Component renders correctly
- **Research References**:
  - frontend/src/components/GameForm.tsx - Reference completed integration
  - frontend/src/components/TemplateForm.tsx - Current structure
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Write TemplateForm integration tests

Add comprehensive tests for TemplateForm ReminderSelector usage.

- **Files**:
  - frontend/src/components/**tests**/TemplateForm.test.tsx - Add integration tests
- **Success**:
  - Test ReminderSelector renders
  - Test preset selection updates state
  - Test chip deletion
  - Test custom value addition
  - Test template saving with reminders
  - All tests pass
- **Research References**:
  - frontend/src/components/**tests**/GameForm.test.tsx - Reference test patterns
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Update TemplateForm validation handlers

Ensure validation works correctly with array-based reminders.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Update validation logic
- **Success**:
  - Validation adapted for array input
  - Error states display on ReminderSelector
  - Validation tests pass
  - No regression in other template fields
- **Research References**:
  - frontend/src/components/GameForm.tsx - Reference validation implementation
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Cleanup and Final Verification

### Task 3.1: Update EditGame page

Ensure EditGame page uses ReminderSelector correctly.

- **Files**:
  - frontend/src/pages/EditGame.tsx - Verify integration
- **Success**:
  - EditGame correctly loads and displays existing reminders
  - Editing reminders works correctly
  - Saving updates reminder_minutes properly
  - No regressions in edit functionality
- **Research References**:
  - frontend/src/pages/CreateGame.tsx - Reference create game patterns
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Remove deprecated comma-parsing logic

Clean up unused comma-separated parsing code while preserving backward compatibility.

- **Files**:
  - frontend/src/utils/fieldValidation.ts - Update validateReminderMinutes
  - frontend/src/components/GameForm.tsx - Remove string-based validation calls
  - frontend/src/components/TemplateForm.tsx - Remove string-based validation calls
- **Success**:
  - Keep comma-parsing in validateReminderMinutes for loading old data
  - Remove validation calls that expect string input
  - All tests still pass
  - No dead code remains except backward compatibility parsing
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 124-127) - Backward compatibility note
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Run full test suite and verify coverage

Execute complete test suite and verify coverage targets met.

- **Files**:
  - All test files
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - ReminderSelector has 100% coverage
  - GameForm reminder-related code has 100% coverage
  - TemplateForm reminder-related code has 100% coverage
  - No coverage regressions in other components
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 135-143) - Success criteria
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Manual QA testing

Perform end-to-end manual testing across all affected user workflows.

- **Files**:
  - N/A (manual testing)
- **Success**:
  - Create game with preset reminders works
  - Create game with custom reminder works
  - Multiple reminders can be added and removed
  - Edit game preserves and updates reminders correctly
  - Template creation with reminders works
  - Template editing with reminders works
  - Creating game from template includes reminders
  - Mobile interaction feels natural (touch targets appropriate)
  - Keyboard navigation works properly
  - Screen reader announces reminder selection/removal
- **Research References**:
  - #file:../research/20260208-01-reminder-time-selector-research.md (Lines 135-143) - Complete success criteria
- **Dependencies**:
  - Task 3.3 completion

## Dependencies

- MUI components (already installed)
- vitest and @testing-library/react (already configured)

## Success Criteria

- ReminderSelector component fully functional with tests
- GameForm uses ReminderSelector with array-based state
- TemplateForm uses ReminderSelector consistently
- All validation rules enforced (1-10080 minute range)
- Duplicate prevention works correctly
- Values automatically sort ascending
- Custom input validates properly
- All tests pass with 100% coverage for new code
- Existing games load correctly (backward compatibility)
- User experience consistent with DurationSelector
