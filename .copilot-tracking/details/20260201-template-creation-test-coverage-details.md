<!-- markdownlint-disable-file -->

# Task Details: Template Creation Test Coverage

## Research Reference

**Source Research**: #file:../research/20260201-template-creation-test-coverage-research.md

## Phase 1: Create Test File and Happy Path

### Task 1.1: Create test file with basic structure and imports

Create new integration test file for template creation with standard structure.

- **Files**:
  - tests/integration/test_template_creation.py (new) - Template creation integration tests
- **Success**:
  - File includes copyright header
  - File includes module docstring explaining test purpose
  - Standard imports included (pytest, httpx, sqlalchemy.text)
  - Test constants defined (TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
  - pytestmark = pytest.mark.integration decorator set
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 112-146) - Integration test pattern
  - tests/integration/test_template_default_overrides.py (Lines 1-40) - Standard integration test structure
- **Dependencies**:
  - None

### Task 1.2: Implement happy path test for successful template creation

Test that template creation succeeds with valid data and proper authorization.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_via_api_success
- **Success**:
  - Test creates guild with bot_manager_roles
  - Test creates channel and user
  - Test creates authenticated session with bot manager role
  - Test POSTs to /api/v1/guilds/{guild_id}/templates with complete valid payload
  - Test verifies 201 Created response
  - Test verifies response JSON matches request data
  - Test queries database to confirm template persisted
  - Test verifies all fields stored correctly in database
  - Docstring explains regression prevention (API validation bypass)
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 148-244) - Complete test implementation pattern
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Authorization Tests

### Task 2.1: Test template creation without bot manager role (403 Forbidden)

Verify authorization enforcement when user lacks bot manager role.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_without_bot_manager_role
- **Success**:
  - Test creates guild WITHOUT bot_manager_roles for user
  - Test seeds cache without bot manager role
  - Test attempts to create template
  - Test verifies 403 Forbidden response
  - Test verifies template NOT created in database
  - Docstring explains authorization enforcement test
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 246-250) - Authorization test requirements
  - services/api/routes/templates.py (Lines 199-202) - Bot manager check
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Test template creation without authentication (401 Unauthorized)

Verify authentication requirement for template creation.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_without_authentication
- **Success**:
  - Test creates guild and channel
  - Test makes POST request WITHOUT session token cookie
  - Test verifies 401 Unauthorized response
  - Test verifies template NOT created in database
  - Docstring explains authentication requirement test
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 246-250) - Authorization test requirements
- **Dependencies**:
  - Phase 1 completion

## Phase 3: Validation Tests

### Task 3.1: Test missing required fields (422 Unprocessable Entity)

Verify Pydantic schema validation rejects incomplete requests.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_missing_required_fields
- **Success**:
  - Test creates valid authentication context
  - Test POSTs with missing 'name' field
  - Test verifies 422 Unprocessable Entity response
  - Test verifies error detail mentions missing field
  - Additional test case for missing 'channel_id'
  - Docstring explains validation enforcement
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 252-256) - Validation test requirements
  - shared/schemas/template.py (Lines 27-49) - TemplateCreateRequest schema
- **Dependencies**:
  - Phase 1 completion

### Task 3.2: Test invalid guild_id (404 Not Found)

Verify guild existence check before template creation.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_invalid_guild_id
- **Success**:
  - Test creates valid channel and authentication
  - Test POSTs with non-existent guild_id UUID
  - Test verifies 404 Not Found response
  - Test verifies template NOT created in database
  - Docstring explains guild validation
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 252-256) - Validation test requirements
  - services/api/routes/templates.py (Lines 196-198) - Guild existence check
- **Dependencies**:
  - Phase 1 completion

### Task 3.3: Test invalid channel_id (should fail validation or creation)

Verify channel validation before template creation.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_invalid_channel_id
- **Success**:
  - Test creates valid guild and authentication
  - Test POSTs with non-existent channel_id UUID
  - Test verifies appropriate error response (422 or 404)
  - Test verifies template NOT created in database
  - Docstring explains channel validation
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 252-256) - Validation test requirements
- **Dependencies**:
  - Phase 1 completion

## Phase 4: Edge Cases

### Task 4.1: Test creating default template (is_default=True)

Verify default template creation and flag handling.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_default_template
- **Success**:
  - Test creates template with is_default=True
  - Test verifies 201 Created response
  - Test verifies is_default flag set in database
  - Test verifies response includes is_default=true
  - Docstring explains default template handling
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 258-262) - Edge case requirements
  - services/api/services/template_service.py (Lines 142-169) - create_default_template method
- **Dependencies**:
  - Phase 1 completion

### Task 4.2: Test with null/empty optional fields

Verify optional fields can be omitted or set to null.

- **Files**:
  - tests/integration/test_template_creation.py - Add test_create_template_minimal_fields
- **Success**:
  - Test creates template with only required fields (guild_id, name, channel_id)
  - Test omits all optional fields
  - Test verifies 201 Created response
  - Test verifies database contains null/default values for optional fields
  - Docstring explains optional field handling
- **Research References**:
  - #file:../research/20260201-template-creation-test-coverage-research.md (Lines 258-262) - Edge case requirements
  - shared/schemas/template.py (Lines 27-57) - Optional field definitions
- **Dependencies**:
  - Phase 1 completion

## Dependencies

- Integration test infrastructure (PostgreSQL, RabbitMQ, Redis)
- Existing fixtures from tests/conftest.py
- Test helpers from tests/shared/auth_helpers.py

## Success Criteria

- All template creation code paths tested via API
- Authorization properly enforced and tested
- Validation properly enforced and tested
- Database persistence verified for all success cases
- All tests pass in integration test suite
- Tests run without Discord bot dependency
