---
applyTo: '.copilot-tracking/changes/20260205-template-description-deletion-bug-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Fix Template Description Deletion Bug

## Overview

Fix double-filtering anti-pattern preventing users from clearing optional text fields (description, where, signup_instructions) in template updates.

## Objectives

- Allow users to explicitly clear optional text fields by deleting content
- Maintain semantic distinction between "field not updated" and "field cleared"
- Follow REST PATCH conventions for explicit null updates
- Ensure all optional text fields (description, where, signup_instructions) support clearing

## Research Summary

### Project Files

- frontend/src/components/TemplateForm.tsx - Frontend strips null values before sending updates
- services/api/services/template_service.py - Backend service ignores null values in updates
- services/api/routes/templates.py - API route using exclude_unset=True correctly
- shared/schemas/template.py - TemplateUpdateRequest schema supports optional fields

### External References

- #file:../research/20260205-template-description-deletion-bug-research.md - Complete bug analysis and solution design

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards

## Implementation Checklist

### [x] Phase 1: Backend Service Update

- [x] Task 1.1: Update template_service.py to accept explicit null values
  - Details: .copilot-tracking/details/20260205-template-description-deletion-bug-details.md (Lines 25-40)

- [x] Task 1.2: Add unit tests for explicit null handling
  - Details: .copilot-tracking/details/20260205-template-description-deletion-bug-details.md (Lines 42-58)

### [x] Phase 2: Frontend Form Update

- [x] Task 2.1: Remove null-filtering logic from TemplateForm
  - Details: .copilot-tracking/details/20260205-template-description-deletion-bug-details.md (Lines 60-74)

- [x] Task 2.2: Update frontend tests for null value handling
  - Details: .copilot-tracking/details/20260205-template-description-deletion-bug-details.md (Lines 77-92)

### [x] Phase 3: Integration Testing

- [x] Task 3.1: Add integration tests for field clearing scenarios
  - Details: .copilot-tracking/details/20260205-template-description-deletion-bug-details.md (Lines 94-115)

## Dependencies

- pytest (already installed)
- React Testing Library (already installed)
- Existing template test fixtures

## Success Criteria

- Clearing description field in UI removes value from database (sets to null)
- Leaving description unchanged preserves original value
- Setting new description updates to new value correctly
- All three scenarios work for description, where, and signup_instructions
- All existing template tests continue to pass
- New tests verify explicit null handling
