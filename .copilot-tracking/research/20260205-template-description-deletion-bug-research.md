<!-- markdownlint-disable-file -->
# Task Research Notes: Template Description Deletion Bug

## Research Executed

### Code Analysis
- frontend/src/components/TemplateForm.tsx (Lines 159-183)
  - Update logic strips null values before sending to backend
  - Line 177: `if (value !== null) { updateData[key] = value; }`
  - This prevents explicitly clearing optional fields
- services/api/services/template_service.py (Lines 170-191)
  - Update service skips null values: `if value is not None: setattr(template, key, value)`
  - Cannot set fields to null/empty values
- services/api/routes/templates.py (Lines 247-251)
  - Uses `exclude_unset=True` on model_dump
  - Only passes fields explicitly set in request
- shared/schemas/template.py (Lines 69-95)
  - TemplateUpdateRequest defines all fields as optional: `str | None`
  - Schema supports null values but implementation rejects them

### User Scenario
1. User edits template with existing description: "Weekly D&D game"
2. User backspaces entire description field (field becomes empty string)
3. Form converts empty string to null: `description: description.trim() || null`
4. Frontend strips null from update request: null values removed from updateData
5. Backend receives request without description field
6. Database retains original description value
7. User sees unchanged description after update

## Key Discoveries

### Bug Root Cause
**Double-Filtering Anti-Pattern**: The codebase implements two layers of null-value filtering that prevent explicit field clearing:

1. **Frontend Layer** (TemplateForm.tsx:174-180): Removes null values from update payload
2. **Backend Layer** (template_service.py:188-189): Ignores null values in updates

**Result**: Impossible to explicitly clear optional string fields like `description`, `where`, `signup_instructions`

### Affected Fields
All optional text fields in template updates:
- `description`
- `where`
- `signup_instructions`

### Current Workaround
User must type a space or placeholder text; cannot truly empty the field.

## Recommended Approach

**Option 1: Explicit Empty String Protocol** (Minimal Change)
- Frontend: Send empty string `""` instead of `null` for cleared fields
- Backend: Accept empty strings and convert to null in database
- Change only frontend form logic (1 line change)
- Preserves existing backend null-filtering behavior
- Risk: Empty strings vs null inconsistency in data model

**Option 2: Explicit Null Updates Protocol** (Clean Semantics)
- Frontend: Send all modified fields, including explicit `null` for cleared fields
- Backend: Distinguish "not provided" (unset) from "set to null" (cleared)
- Use Pydantic's `exclude_unset=True` correctly
- Modify service to accept explicit nulls when field is present in request
- Requires backend changes but provides clearer semantics
- Aligns with REST PATCH conventions

**Option 3: Separate Clear Endpoints** (Most Explicit)
- Add dedicated clear operations: `PATCH /templates/{id}/clear-description`
- Maximum clarity but added API complexity
- Overkill for this use case

## Implementation Guidance

### Selected Approach: Option 2 (Explicit Null Updates)

**Objectives**:
- Allow users to clear optional text fields in template updates
- Maintain semantic distinction between "not updated" and "cleared"
- Follow REST/HTTP PATCH conventions properly

**Key Changes**:
1. **Frontend (TemplateForm.tsx)**:
   - Remove null-filtering logic (lines 174-180)
   - Send all form fields including explicit nulls for cleared values
   - Track which fields user has interacted with

2. **Backend (template_service.py)**:
   - Change update_template to accept explicit None when field is in updates dict
   - Use `key in updates` check instead of `value is not None`
   - This distinguishes "field not provided" from "field set to None"

3. **API Route (templates.py)**:
   - Continue using `exclude_unset=True` - this is correct
   - Only includes fields actually present in JSON request

**Success Criteria**:
- Clearing description field removes it from database (sets to null)
- Leaving description unchanged preserves original value
- Setting new description updates to new value
- All three scenarios work correctly for all optional text fields

**Testing Strategy**:
- Test clearing existing non-null description → becomes null
- Test updating existing description → updates correctly
- Test leaving description unchanged → preserves original
- Test clearing empty/null description → remains null
- Verify same behavior for `where` and `signup_instructions`

**Dependencies**: None - isolated change to update logic
