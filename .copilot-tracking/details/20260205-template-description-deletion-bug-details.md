<!-- markdownlint-disable-file -->

# Task Details: Fix Template Description Deletion Bug

## Research Reference

**Source Research**: #file:../research/20260205-template-description-deletion-bug-research.md

## Phase 1: Backend Service Update

### Task 1.1: Update template_service.py to accept explicit null values

Modify the update_template method to distinguish between "field not provided" (omitted from updates dict) and "field set to None" (explicit null in updates dict).

- **Files**:
  - services/api/services/template_service.py - Change update logic in update_template method
- **Success**:
  - Method checks `if key in updates` instead of `if value is not None`
  - Explicit None values are applied to model attributes
  - Omitted fields remain unchanged
  - Method signature and return type unchanged
- **Research References**:
  - #file:../research/20260205-template-description-deletion-bug-research.md (Lines 61-76) - Backend implementation approach
- **Dependencies**:
  - None - isolated backend change

### Task 1.2: Add unit tests for explicit null handling

Add comprehensive unit tests verifying the updated null handling behavior.

- **Files**:
  - tests/services/api/services/test_template_service.py - Add new test cases
- **Success**:
  - Test clearing non-null field to null
  - Test updating field to new non-null value
  - Test omitting field preserves original value
  - Test clearing already-null field remains null
  - Tests cover description, where, and signup_instructions
  - All existing tests continue to pass
- **Research References**:
  - #file:../research/20260205-template-description-deletion-bug-research.md (Lines 94-104) - Testing strategy
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Frontend Form Update

### Task 2.1: Remove null-filtering logic from TemplateForm

Remove the code that strips null values from update requests, allowing explicit nulls to be sent to the backend.

- **Files**:
  - frontend/src/components/TemplateForm.tsx - Remove null-filtering loop (lines 174-180)
- **Success**:
  - Update request includes all form fields
  - Null values sent explicitly for cleared fields
  - Form continues to convert empty strings to null
  - No changes to form validation logic
  - Submit handler simplified by removing filtering loop
- **Research References**:
  - #file:../research/20260205-template-description-deletion-bug-research.md (Lines 61-76) - Frontend implementation approach
- **Dependencies**:
  - Phase 1 completion (backend must handle nulls correctly first)

### Task 2.2: Update frontend tests for null value handling

Update or add frontend tests to verify null value handling in template form submissions.

- **Files**:
  - frontend/src/components/__tests__/TemplateForm.test.tsx - Update existing tests or add new ones
- **Success**:
  - Tests verify null values are included in update requests
  - Tests verify empty string conversion to null
  - Tests verify non-empty values sent correctly
  - All existing form tests continue to pass
- **Research References**:
  - #file:../research/20260205-template-description-deletion-bug-research.md (Lines 94-104) - Testing strategy
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Integration Testing

### Task 3.1: Add integration tests for field clearing scenarios

Create integration tests that verify end-to-end field clearing through the API.

- **Files**:
  - tests/integration/test_template_updates.py - New integration test file or add to existing
- **Success**:
  - Test complete workflow: create template with description, update to clear it, verify null in DB
  - Test update existing description to new value
  - Test leave description unchanged
  - Test clear already-null field
  - Tests verify database state after updates
  - Tests use actual API endpoints and database
- **Research References**:
  - #file:../research/20260205-template-description-deletion-bug-research.md (Lines 94-104) - Testing strategy
  - #file:../../.github/instructions/integration-tests.instructions.md - Integration test patterns
- **Dependencies**:
  - Phases 1 and 2 completion

## Dependencies

- pytest for backend testing
- React Testing Library for frontend testing
- Integration test infrastructure already in place

## Success Criteria

- User can clear description field and see it removed from database
- User can update description to new value successfully
- Leaving description unchanged preserves original value
- All three behaviors work for description, where, and signup_instructions
- All existing tests pass
- New tests verify correct null handling
