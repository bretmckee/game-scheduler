<!-- markdownlint-disable-file -->

# Task Details: Validation on Submit with @ Display Enhancement

## Research Reference

**Source Research**: #file:../research/20251127-discord-validation-timing-options-research.md

## Phase 1: Frontend - Remove Real-time Validation

### Task 1.1: Simplify ParticipantInput interface

Remove validation-related fields from ParticipantInput interface in EditableParticipantList.tsx.

- **Files**:
  - frontend/src/components/EditableParticipantList.tsx (Lines 19-27)
- **Changes**:
  - Remove `isValid: boolean | null` field
  - Remove `validationError?: string` field
  - Keep only: id, mention, preFillPosition, isExplicitlyPositioned, isReadOnly
- **Success**:
  - Interface contains only essential participant data
  - No validation state in interface
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 229-254) - Submit-time validation implementation
- **Dependencies**: None

### Task 1.2: Remove validation state and timers from EditableParticipantList

Remove all validation-related state management from component.

- **Files**:
  - frontend/src/components/EditableParticipantList.tsx (Lines 39-49, 51-102)
- **Changes**:
  - Remove `validationTimers` state
  - Remove `validateMention` callback function
  - Remove validation timer cleanup useEffect
- **Success**:
  - No validation state in component
  - No API calls to validate-mention endpoint
  - Component only manages participant list state
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 229-254) - Remove real-time validation code
- **Dependencies**: Task 1.1 completion

### Task 1.3: Simplify handleMentionChange to only update mention text

Update handleMentionChange to only update the mention field without validation.

- **Files**:
  - frontend/src/components/EditableParticipantList.tsx (Lines 104-122)
- **Changes**:
  - Remove timer logic from handleMentionChange
  - Remove validation state clearing
  - Keep only: update mention text in participants array
- **Success**:
  - handleMentionChange only updates mention text
  - No debounce timers
  - No validation calls
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 229-254) - Simplified handler
- **Dependencies**: Task 1.2 completion

### Task 1.4: Remove validation visual indicators from TextField

Remove loading spinner, checkmark, and error icon from TextField InputProps.

- **Files**:
  - frontend/src/components/EditableParticipantList.tsx (Lines 260-283)
- **Changes**:
  - Remove CircularProgress, CheckCircleIcon, ErrorIcon imports
  - Remove InputAdornment logic with validation indicators
  - Remove error and helperText props related to validation
  - Keep helperText for isReadOnly status
- **Success**:
  - TextField has no validation indicators
  - Clean input field during typing
  - ReadOnly status still displayed
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 229-254) - Remove visual validation
- **Dependencies**: Task 1.3 completion

## Phase 2: Frontend - Add Disambiguation UI

### Task 2.1: Create DisambiguationChip component

Create reusable chip component for displaying user suggestions.

- **Files**:
  - frontend/src/components/DisambiguationChip.tsx (new file)
- **Implementation**:
  - Accept: username, displayName, onClick handler
  - Render: Clickable Chip with username and display name
  - Styling: Primary color, small size, clickable cursor
- **Success**:
  - Component renders suggestion chip
  - Click triggers callback with username
  - Visual feedback on hover
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 268-282) - Disambiguation UI component
- **Dependencies**: None

### Task 2.2: Create ValidationErrors component

Create component to display validation errors with disambiguation options.

- **Files**:
  - frontend/src/components/ValidationErrors.tsx (new file)
- **Implementation**:
  - Accept: ValidationError[] array, onSuggestionClick callback
  - Display: Alert with error messages and suggestion chips
  - Group: By input mention, show suggestions per error
  - Action: Call onSuggestionClick when chip clicked
- **Success**:
  - Displays all validation errors clearly
  - Shows suggestion chips for ambiguous mentions
  - Handles no-suggestions case (user not found)
  - Clicking suggestion triggers callback
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 284-302) - Backend response format
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 268-282) - Disambiguation UI
- **Dependencies**: Task 2.1 completion

### Task 2.3: Integrate ValidationErrors in CreateGame

Add ValidationErrors component to CreateGame page.

- **Files**:
  - frontend/src/pages/CreateGame.tsx (Lines 103-117)
- **Changes**:
  - Import ValidationErrors component
  - Display ValidationErrors above GameForm when validationErrors exists
  - Implement handleSuggestionClick to update form participants
  - Clear validation errors after suggestion applied
- **Success**:
  - Validation errors display after submit fails
  - Suggestion chips clickable
  - Clicking suggestion updates corresponding participant
  - Form data preserved
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 255-267) - Submit handling
- **Dependencies**: Task 2.2 completion

### Task 2.4: Integrate ValidationErrors in EditGame

Add ValidationErrors component to EditGame page.

- **Files**:
  - frontend/src/pages/EditGame.tsx
- **Changes**:
  - Add validationErrors state
  - Import ValidationErrors component
  - Catch 422 errors in handleSubmit
  - Display ValidationErrors above GameForm
  - Implement handleSuggestionClick
- **Success**:
  - Same disambiguation UI as CreateGame
  - Error handling on update
  - Form data preserved on validation error
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 255-267) - Submit handling
- **Dependencies**: Task 2.2 completion

## Phase 3: Frontend - Enhance @ Display

### Task 3.1: Add @ prepending logic to ParticipantList display

Enhance ParticipantList to prepend @ to display names for visual consistency.

- **Files**:
  - frontend/src/components/ParticipantList.tsx (Lines 56-62, 78-86)
- **Changes**:
  - Create helper function to format participant display name
  - Prepend @ to display_name if it doesn't already start with @
  - Apply to both confirmed and waitlist participant displays
- **Success**:
  - Participant names display with @ prefix
  - No double @ if already present
  - Consistent @ display across all participants
- **Research References**:
  - User requirement for @ display enhancement
- **Dependencies**: None

### Task 3.2: Ensure @ handling in EditableParticipantList display

Verify EditableParticipantList properly handles @ in mentions during editing.

- **Files**:
  - frontend/src/components/EditableParticipantList.tsx (Lines 239-283)
- **Changes**:
  - Review TextField value binding
  - Ensure @ is preserved during editing
  - No automatic @ stripping or adding during typing
- **Success**:
  - User can type with or without @ prefix
  - @ preserved if user includes it
  - Backend handles resolution with or without @
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 15-40) - Current implementation
- **Dependencies**: None

## Phase 4: Backend - Enhance Validation Response

### Task 4.1: Verify validation error response format

Ensure backend returns proper validation error structure with suggestions.

- **Files**:
  - services/api/routes/games.py (Lines 77-88)
- **Verification**:
  - Check ValidationError exception format
  - Verify response includes: error, message, invalid_mentions, valid_participants
  - Confirm suggestions array format: discordId, username, displayName
- **Success**:
  - Response matches expected format
  - Suggestions properly structured
  - All required fields present
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 284-302) - Backend response format
- **Dependencies**: None

### Task 4.2: Ensure form_data preservation in error response

Verify form data is preserved in validation error response.

- **Files**:
  - services/api/routes/games.py (Lines 77-88)
- **Changes**:
  - Confirm form_data included in 422 response detail
  - Verify all game fields preserved
  - Check participant data included
- **Success**:
  - Frontend can restore form state from error response
  - No data loss on validation error
  - All fields available for correction
- **Research References**:
  - #file:../research/20251127-discord-validation-timing-options-research.md (Lines 229-254) - Form preservation
- **Dependencies**: Task 4.1 completion

## Phase 5: Testing and Validation

### Task 5.1: Test single valid mention submission

Verify game creation with one valid participant.

- **Test Steps**:
  1. Create game with single @mention
  2. Submit form
  3. Verify successful creation
  4. Verify no validation errors
- **Success**:
  - Game created successfully
  - Participant resolved correctly
  - No validation errors
- **Dependencies**: Phase 1-4 completion

### Task 5.2: Test multiple valid mentions submission

Verify game creation with multiple valid participants.

- **Test Steps**:
  1. Add 3+ valid @mentions
  2. Submit form
  3. Verify all participants resolved
  4. Check game detail page
- **Success**:
  - All participants created
  - Order preserved
  - @ displayed in participant list
- **Dependencies**: Phase 1-4 completion

### Task 5.3: Test invalid mention with disambiguation

Verify disambiguation UI for ambiguous mentions.

- **Test Steps**:
  1. Add mention matching multiple users (e.g., @john)
  2. Submit form
  3. Verify validation error displays
  4. Check suggestion chips appear
  5. Click suggestion
  6. Resubmit
- **Success**:
  - Validation error displays with suggestions
  - Chips clickable
  - Selection updates form
  - Second submit succeeds
- **Dependencies**: Phase 1-4 completion

### Task 5.4: Test mixed valid/invalid mentions

Verify handling of both valid and invalid mentions.

- **Test Steps**:
  1. Add 2 valid mentions, 1 invalid
  2. Submit form
  3. Verify error shows only invalid mention
  4. Verify valid mentions listed separately
  5. Correct invalid mention
  6. Resubmit
- **Success**:
  - Error shows only invalid mentions
  - Valid participants acknowledged
  - Form preserves all data
  - Correction enables success
- **Dependencies**: Phase 1-4 completion

### Task 5.5: Verify @ display enhancement

Verify @ symbol prepended to validated participants in display.

- **Test Steps**:
  1. Create game with participants
  2. Navigate to game detail page
  3. Verify participant names show @ prefix
  4. Edit game
  5. Verify @ handling in edit form
- **Success**:
  - All participant names display with @
  - No double @@ symbols
  - Consistent display across views
- **Dependencies**: Phase 3 completion

### Task 5.6: Verify no API calls during typing

Use browser DevTools to verify no validation calls during form entry.

- **Test Steps**:
  1. Open DevTools Network tab
  2. Start creating game
  3. Type in participant mention fields
  4. Observe network activity
  5. Verify no /validate-mention calls
- **Success**:
  - Zero API calls during typing
  - Only submit triggers validation
  - Network tab clean
- **Dependencies**: Phase 1 completion
